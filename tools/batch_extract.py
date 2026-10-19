#!/usr/bin/env python3
"""Low-token page-level PDF extraction for the private 408 question bank.

Run deterministic text extraction first, use offline OCR only on pages without
usable text, and CACHE every page. Output is unverified staging data, never a
complete questions.md/solutions.md. No language-model API calls are made.

Examples:
  python tools/batch_extract.py --scope mock --ocr off --limit-pages 30
  python tools/batch_extract.py --scope all --ocr auto --limit-pages 10
  python tools/batch_extract.py --scope all --ocr auto --limit-pages 0
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DEFAULT = Path(__file__).resolve().parent.parent

# `python -I` 不会把脚本目录放进 sys.path[0]，所以要显式加。
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ocr_runtime  # noqa: E402  （同目录，见该模块的 DLL 兼容说明）

RE_MARK = re.compile(r"[\^_]\{([^{}]*)\}")
# 上下标段的字符判据：用**黑名单 + 词字符**，不用「ASCII 白名单」。
# 原先要求整段只能是 `[A-Za-z0-9+\-]`，把一批**真上下标**整段拒了。实测全 18 卷被它
# 拒掉的候选**共 25 个、无一例外都是真上下标**（脚本 build/_scratch/probe/rejected_runs.py）：
#     `[x]_{补}`（2013 第2题、2025 第2题；「补」是汉字下标，连字母数字都没有）
#     `m_{i,j}` `m_{30,30}` `m_{6,6}` `m_{7,2}` `S_{x,y}`（下标里带逗号）
#     `2^{–128}` `2^{–127}` `2^{–126}`（2023 第14题；指数里的负号是 U+2013 短破折号）
#     `a_{n－1}` `a_{n–2}`（下标里带全角/短破折号）、`IR_{11～0}`（全角波浪号）
# 只拒「正文标点」与**圆括号**：这类字符出现在「小字号 + 抬/降」的连体段里，基本可以断定
# 这段不是上下标，而是被版面切碎的一句话。
# ⚠️ 圆括号必须留在黑名单里：2010 答案第 11 页那批扫描重排版的**数学变量** `T(a)`/`T(b)`
# 被排成小一号、基线略低的另一种字体，几何上与真下标无异，就是靠「段里有 `(`」挡掉的
# （判出的是 `(b`）。实测那 25 个真上下标**没有一个含圆括号**，所以挡住它不损失任何真标。
RE_SCRIPT_BAD = re.compile(r"[，。、；：？！“”‘’《》【】〔〕％()]")
# 段里至少一个词字符（字母/数字/汉字）。这条是拦箭头的——2010 答案卷第 11 页 CLOCK 算法的
# 箭头被抽成 `--`，字号更小、位置也抬高，单看几何与真上标无异，但里面没有词字符。
RE_HAS_WORD = re.compile(r"[A-Za-z0-9一-鿿]")
# 汉字只有在**数学语境**里才可能是上下标（`[x]_{补}` 的「补」是补码的意思，基字是 `]`）。
# 正文里的汉字被排成小一号是**字体伪影**：本批答案卷把「一」这个字位按 6.5pt 画在 10pt
# 正文中间（2009-answer p4 实测：`一` size=6.5 y=355.09，同行其余字符 size=10.0 y≈359.8，
# bbox 高 8.78 vs 13.49）——几何上与真上标**完全一样**，只靠几何分不开。
# 实测：放宽字符判据后共 1636 处标定，其中 **784 处是「一」**，全是
# 「每取^{一}个字」「第^{一}步」「任^{一}字块」这种散文。判据只能落在**邻字**上：
# 汉字的前/后紧挨着汉字，就是在散文里，不是上下标。
# 这条不损失真标：`[x]_{补}` 的「补」前是 `]`、后是 `=`，`C_{N-1}` 的 `凡`（OCR 把 N 认成凡）
# 前是 `C`、后是 `+`，两边都不是汉字。
RE_CJK = re.compile(r"[一-鿿]")
# 纯横线字形同样不作上下标。本批 PDF 用「一」这个字位代**连字符/减号**：
# `Reverse(O,p-1)`→`Reverse(O,p一1)`、`a2-3`→`a2一3`、`if(t->l)`→`if(t一>l)`、`n-1`→`n一1`；
# 而在散文里它又是真的「一」。**两种读法都不是上下标**，所以整段都是横线的一律不猜。
# 只拦「整段只有横线」的：`–128`（2023 第14题的 `2^{–128}`）带数字，必须留下。
RE_SCRIPT_DASH = re.compile(r"^[一\-–—－～~]+$")

SCRIPT_SIZE_RATIO = 0.8    # 小于正文字号这个比例才算「疑似上下标」
SCRIPT_SHIFT_EM = 0.06     # 基线抬/降超过 0.06em 才认（12pt 正文 ≈ 0.72pt）
# 定位用的锚长：先短后长，短锚撞车就换长锚自己解决（见 mark_scripts）。
ANCHOR_STEPS = (3, 6, 10, 16, 24)
SCRIPT_TAIL = 2            # 尾锚取几个非空白字符（只用来消歧，不用来否决）


def _line_units(line) -> list[dict]:
    """把一行的 span 拆成**逐字符**单元，顺手丢掉空白字符。

    为什么必须拆到字符、还必须丢掉空白
    ----------------------------------
    2022 答案卷第 4 页的 span `' 16'`（`2^16` 的上标）**开头带一个空格**：
    空格自己带着正文基线（`origin_y` 81.36）和一条从 68.81 拖到 83.51 的 bbox，
    把整段 span 的 `origin_y`/`bbox` 全污染了——照 span 取几何，真上标
    （数字的基线其实在 **76.09**）会被算成只比基字高 0.85pt，
    同一行里 `2^6` 判上标、`2^16` 判下标的自相矛盾就是这么来的。
    按字符取、剔掉空白之后，`2^16` 的 dy 是 -6.12，判据干净。

    → [{size, y(基线), lo, hi, ch}]，`lo`/`hi` 是该字符 bbox 的上下沿
    """
    units: list[dict] = []
    for span in line.get("spans", []):
        size = round(float(span.get("size", 0.0)), 2)
        for ch in span.get("chars", []):
            if ch["c"].isspace():
                continue
            box = ch["bbox"]
            units.append({"size": size, "y": float(ch["origin"][1]),
                          "lo": float(box[1]), "hi": float(box[3]), "ch": ch["c"]})
    return units


def collect_scripts(page) -> list[tuple[str, str, str, str, bool]]:
    """页面里所有「字号更小 + 基线抬/降」的字符段，按阅读顺序。

    判据来自实测：2012 第 14 题的上标 6.0pt vs 正文 12.0pt、基线差 6.0pt；
    2010 第 41 题 `Xp+1` 里 `p`/`+`/`1` 是连着的三个下标字符，要**并成一段**。

    正文字号取**本行字号的众数**（同数时取大的）：不能取最大字号——2010 答案卷第 11 页
    行尾那个全角句号 `。` 被报成 22pt，取最大则整行 10pt 正文全成了「小字」，
    真下标 `t1` 反而没得可判。

    **逐个字符先分类、再把同类相邻的并段**（不是先并段后分类）：
    同行的基线偏移是按字符算的，`t1` 后面紧跟着一个抬高的小号 `=`，
    先并段会把 `1=` 并成一段、整段被字符判据拒收，`t1` 就整条丢了。

    基准线取**紧邻的那一个正文单元**，不取整行均值——实测 2022 第 4 页有一行里
    混着落在上标高度的正文 span（`' = (2'`），整行均值被它拽偏。基字自己的基线
    才是物理上正确的参照。

    基字与上下标**可以不在同一行**（`carry`）
    ------------------------------------------
    PDF 把抬高的上标排成**独立的 line 对象**，于是「基字在上一行行尾、上下标在下一行行首」
    是常态，不是例外。实测 2009 全卷 11 个小字号字符只标出 1 个，漏掉的
    `2^{7}×`、`2^{8}B`、`2^{16}B`、`2^{24}B`、`2^{32}B`、`2^{5}×5/8` 全是这一类——
    只看本行的话它们前面一个字符都没有，`head` 为空就被丢了。
    所以跨行攒两样东西：`carry_head`（前文，当锚用）与 `carry_ref`（前一个正文单元的
    基线，当参照用）。

    ⚠️ 借来的锚**必须**被后文（`foot`）正面确认才算数：锚找错地方会**静默**把标记
    插进别的字里，比漏标危险得多。返回的第 5 个字段 `must_confirm` 就是这件事。

    返回 `(kind, 前文, 文本, 后文, 是否跨行)`。
    `mark_scripts` 会**从短到长**取它们的尾部/头部当锚：3 个字符的锚在
    `P1、P2、P3` 这种串里必然撞车，加长到 6/10 个就唯一了。
    """
    items: list[tuple[str, str, str, str, bool]] = []
    # 先摊平成「一页的行序列」，才能为跨行的上下标向后看一行取后文。
    rows: list[list[dict]] = []
    for block in page.get_text("rawdict", sort=True).get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            units = _line_units(line)
            if units:
                rows.append(units)

    carry_head = ""            # 前面各行末尾的字符（跨行取基字用）
    carry_ref: dict | None = None   # 前面各行最后一个正文单元（跨行取基线用）
    for li, units in enumerate(rows):
        sizes: dict[float, int] = {}
        for u in units:
            sizes[u["size"]] = sizes.get(u["size"], 0) + 1
        body = max(sizes.items(), key=lambda kv: (kv[1], kv[0]))[0]
        small = [u["size"] < SCRIPT_SIZE_RATIO * body for u in units]
        if any(small):
            kinds: list[str | None] = []
            for idx, unit in enumerate(units):
                if not small[idx]:
                    kinds.append(None)
                    continue
                # 基准：紧邻的前一个正文单元；没有就退到后一个；都没有就退到**上一行**的
                # 最后一个正文单元。跨行参照要额外卡一下距离——不同版块的上一行可能在
                # 页面的另一个角落，dy 会被算成一大截，凭空判出上下标。
                ref = None
                for k in range(idx - 1, -1, -1):
                    if not small[k]:
                        ref = units[k]
                        break
                if ref is None:
                    for k in range(idx + 1, len(units)):
                        if not small[k]:
                            ref = units[k]
                            break
                if ref is None and carry_ref is not None:
                    if abs(unit["y"] - carry_ref["y"]) <= 1.2 * carry_ref["size"]:
                        ref = carry_ref
                kind = None
                if ref is not None:
                    dy = unit["y"] - ref["y"]
                    shift = SCRIPT_SHIFT_EM * ref["size"]
                    if dy < -shift:
                        kind = "sup"
                    elif dy > shift:
                        kind = "sub"
                kinds.append(kind)
            i = 0
            while i < len(units):
                if kinds[i] is None:
                    i += 1
                    continue
                j = i
                while j + 1 < len(units) and kinds[j + 1] == kinds[i]:
                    j += 1                       # 同类的连成一段：n、-、1 → n-1
                text = "".join(u["ch"] for u in units[i:j + 1])
                first, i = i, j + 1
                if RE_SCRIPT_BAD.search(text) or not RE_HAS_WORD.search(text):
                    continue
                # 承接文本要**跨 span 往回/往前接着攒**：本批 PDF 里基字和上下标
                # 是两个独立 span（`P` 与 `1`），只看紧邻那一个 span 就只能拿到
                # 一个字符的锚，在 `P1、P2、P3` 里必然撞车。
                head = "".join(u["ch"] for u in units[:first])
                carried = False
                if not head:
                    head, carried = carry_head, bool(carry_head)
                head = head[-ANCHOR_STEPS[-1]:]
                if not head:
                    continue                     # 连上一行也没有前文 → 没有基字，不猜
                foot = "".join(u["ch"] for u in units[i:])[:SCRIPT_TAIL]
                # 跨行条目的后文常常只剩一个字符（行首就是上下标，本行后面只跟一个字），
                # 不够做确认。**只对跨行条目**往后借一行补足，免得行内条目的判据被改。
                if carried and len(foot) < SCRIPT_TAIL and li + 1 < len(rows):
                    foot = (foot + "".join(u["ch"] for u in rows[li + 1]))[:SCRIPT_TAIL]
                # 汉字判据、横线判据必须放在 head/foot **定稿之后**——两条都看邻字，
                # 而 head 可能是从上一行借的、foot 可能刚往后借了一行。
                if RE_CJK.search(text) and (RE_CJK.search(head[-1:]) or RE_CJK.search(foot[:1])):
                    continue
                if RE_SCRIPT_DASH.match(text):
                    continue
                items.append((kinds[first], head, text, foot, carried))
        # 更新跨行状态。锚要攒够 ANCHOR_STEPS[-1] 个字符；正文单元取本行最后一个
        # **不小**的字（整行都小就不动 carry_ref，免得参照被小字自己污染）。
        carry_head = (carry_head + "".join(u["ch"] for u in units))[-ANCHOR_STEPS[-1]:]
        sizes_last = [u for u in units if u["size"] >= SCRIPT_SIZE_RATIO * body]
        if sizes_last:
            carry_ref = sizes_last[-1]
    return items


def _skip_ws(text: str, pos: int) -> int:
    """把 `pos` 往前推到下一个非空白字符（纯文本模式会自己往里塞空格）。"""
    while pos < len(text) and text[pos].isspace():
        pos += 1
    return pos


def _follows(text: str, pos: int, tail: str) -> bool:
    """`text[pos:]` 是否就是 `tail`（允许中间夹空白）。"""
    for ch in tail:
        pos = _skip_ws(text, pos)
        if pos >= len(text) or text[pos] != ch:
            return False
        pos += 1
    return True


def _find_spaced(text: str, word: str, start: int) -> int | None:
    """找 `word`，**允许各字符之间夹空白**（纯文本模式会自己塞空格、也可能在此折行）。

    返回最后一个字符**之后**的下标（不是起点）：紧接着的那个位置才是「基字之后」。
    找不到返回 None。
    """
    i = start
    while True:
        i = text.find(word[0], i)
        if i < 0:
            return None
        j = i + 1
        for k in range(1, len(word)):
            j = _skip_ws(text, j)
            if j >= len(text) or text[j] != word[k]:
                break
            j += 1
        else:
            return j
        i += 1


def _collect_spots(text: str, anchor: str, word: str, start: int) -> list[int]:
    """所有「锚（可夹空白）紧接着上下标文本（**不许**夹空白）」的 `word` 起点。"""
    spots: list[int] = []
    at = start
    while True:
        end = _find_spaced(text, anchor, at)
        if end is None:
            return spots
        pos = _skip_ws(text, end)
        if text.startswith(word, pos):
            spots.append(pos)
            at = pos + len(word)
        else:
            at = end


def mark_scripts(plain: str, scripts: list[tuple[str, str, str, str, bool]]) -> tuple[str, list, list]:
    """把 `plain` 里属于上下标的那几段用 `^{…}` / `_{…}` 括起来。

    只**插标记**、不动一个字符，所以「去掉标记 == 原串」恒成立（函数结尾自检）。

    定位不靠「找上下标自己」（`1`、`2` 这类单个数字在正文里到处都是，必然找错），
    而是拿**基字尾若干字符 + 上下标文本**当锚（`X1`、`log2`、`Xn-1`、`2x27`），
    锚够长就不会撞车；命中后只把**尾部的上下标那几个字符**括起来。

    消歧顺序，一步不行就换下一步，最后仍定不下来才记 `ambiguous`：
      1. 取基字尾 3 字符，在候选里只命中一处 → 定了；
      2. 命中多处就**加长锚**（6/10/16/24）再来一遍——`P1、P2、P3` 这种串里
         3 字符必撞、10 字符就唯一了，比推给人看划算；
      3. 还是多处，就用**后锚**（下一个 span 的头部）在候选里挑；
      4. 都挑不出来，取阅读顺序上第一个并记 `ambiguous` 留痕，**不静默**。

    后锚**只用来挑、不用来否决**——实测「后锚对不上」的 26 处，键在整页里
    **全部只出现一次**，位置本来就唯一确定；对不上只是 span 切分与纯文本切分
    的差异（相邻 span 不是标点、`2⁷ -1` 里那个空格等）。

    锚与锚之间**允许夹空白**（纯文本模式会自己塞空格、也可能在此折行）：
    实际踩到的是 `A. V1`——span 里是 `A.` 紧跟 `V`，纯文本里多了个空格。

    起点从 `cursor` 前后一小段开始找（锚可能压到上一处已标记的尾巴），
    但**只认落在 `cursor` 之后的命中**——否则会静默跳到后面一个同名锚上。

    锚在纯文本里**向后找不到**就记进 `missed` 交给人工，**不许猜位置**。

    `must_confirm=True`（基字来自**上一行**，见 `collect_scripts` 的 `carry`）的条目**必须**
    被后文正面确认：跨行的锚是从另一行借来的，锚找错地方不会报错、只会**静默**把标记
    插进别的字里——那比漏标危险得多。确认不了就放弃，记进 `missed`。

    → (新串, 已标记明细, 放弃明细)
    """
    out: list[str] = []
    hit: list[dict] = []
    missed: list[dict] = []
    cursor = 0
    for kind, head, text, foot, must_confirm in scripts:
        lo = max(0, cursor - 4 * ANCHOR_STEPS[-1])
        picked: int | None = None
        how = ""

        def confirmed(p: int) -> bool:
            return (len(foot) >= SCRIPT_TAIL
                    and _follows(plain, p + len(text), foot[:SCRIPT_TAIL]))

        for step in ANCHOR_STEPS:
            anchor = head[-step:]
            spots = [p for p in _collect_spots(plain, anchor, text, lo) if p >= cursor]
            if must_confirm:
                spots = [p for p in spots if confirmed(p)]
            if not spots:
                break                       # 锚再长就找不着了 → 保留上一轮的结果
            if len(spots) == 1:
                picked = spots[0]
                how = "single" if step == ANCHOR_STEPS[0] else f"anchor{len(anchor)}"
                break
            matched = [p for p in spots if confirmed(p)]
            if len(matched) == 1:
                picked = matched[0]
                how = f"tail{len(anchor)}"
                break
            picked = spots[0]               # 先留着；下一轮用更长的锚再试
            how = f"ambiguous{len(anchor)}"
        if picked is None:
            missed.append({"kind": kind, "text": text, "anchor": head[-ANCHOR_STEPS[0]:],
                           "tail": foot[:SCRIPT_TAIL], "needs_confirm": must_confirm,
                           "why": (f"跨行基字 {head[-ANCHOR_STEPS[0]:] + text!r} 未被后文确认"
                                   if must_confirm else
                                   f"锚 {head[-ANCHOR_STEPS[0]:] + text!r} 在纯文本里向后找不到")})
            continue
        start = picked
        out.append(plain[cursor:start])
        out.append(("^{" if kind == "sup" else "_{") + plain[start:start + len(text)] + "}")
        hit.append({"kind": kind, "text": text, "head": head, "foot": foot,
                    "carried": must_confirm,
                    "context": plain[max(0, start - 12):start + len(text) + 8],
                    "resolved_by": how, "ambiguous": how.startswith("ambiguous")})
        cursor = start + len(text)
    out.append(plain[cursor:])
    marked = "".join(out)
    if RE_MARK.sub(r"\1", marked) != plain:
        raise AssertionError("标记破坏了原文（去标记后与原串不等）——拒绝写出这一页")
    return marked, hit, missed


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def setup_ocr():
    """Lazy import: there is no OCR model load for text PDFs.

    顺序不能颠倒：`rapidocr_onnxruntime` 一导入就会拉 `onnxruntime`，
    而本机 onnxruntime 的原生 DLL 需要先经 `ocr_runtime.ensure()` 处理，
    否则抛的是 "DLL load failed"，会被误读成「rapidocr 没装」。
    """
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("缺少 numpy，离线OCR不可用；只能用 --ocr off") from exc

    ocr_runtime.ensure()   # 失败时自带「缺哪个 DLL / 代际差多少」的说明

    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise RuntimeError(
            "rapidocr-onnxruntime 未安装：仅可使用 --ocr off，"
            "或者 pip install rapidocr-onnxruntime"
        ) from exc
    return np, RapidOCR()


def ocr_page(page, np, engine, dpi: int) -> tuple[str, float | None]:
    image = page.get_pixmap(dpi=dpi, alpha=False, colorspace="rgb")
    data = np.frombuffer(image.samples, dtype=np.uint8).reshape(
        image.height, image.width, image.n
    )
    result, _ = engine(data)
    result = result or []
    texts = [str(item[1]) for item in result if len(item) >= 2]
    scores = [float(item[2]) for item in result if len(item) >= 3]
    return "\n".join(texts), sum(scores) / len(scores) if scores else None


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    cli.add_argument("--scope", choices=["all", "exam", "mock"], default="all")
    cli.add_argument("--ocr", choices=["off", "auto"], default="off")
    cli.add_argument("--dpi", type=int, default=180)
    cli.add_argument("--min-chars", type=int, default=60)
    cli.add_argument("--limit-pages", type=int, default=12,
                     help="本次最多处理多少未缓存页；0=无限。默认12以控制CPU占用")
    args = cli.parse_args(argv)
    if args.dpi < 90 or args.dpi > 300:
        cli.error("--dpi 必须在90至300之间")
    if args.min_chars < 0 or args.limit_pages < 0:
        cli.error("字符阈值/页数限额不得为负")
    root = args.root.resolve()
    manifest_file = root / "index" / "sources-manifest.json"
    if not manifest_file.is_file():
        cli.error("缺少 index/sources-manifest.json，先执行 tools/inventory.py")
    files = json.loads(manifest_file.read_text(encoding="utf-8"))["files"]
    chosen = [r for r in files if r.get("ext") == ".pdf" and (
        args.scope == "all" or
        (args.scope == "exam" and r["path"].startswith("sources/exams/")) or
        (args.scope == "mock" and r["path"].startswith("sources/mock-2027/"))
    )]
    # ⚠️ 顺序要害：必须**先**把 OCR 运行时就位，**再** import pymupdf。
    # 反过来的话，pymupdf 会先把 System32 里 VS2015 那份 msvcp140.dll 钉进进程，
    # 之后 onnxruntime（VS2022 构建）撞上它直接段错误（exit 139、零输出）。
    # 详见 tools/ocr_runtime.py 顶部说明。
    if args.ocr == "auto":
        ocr_runtime.ensure()

    import pymupdf
    np = engine = None
    processed = cached = n_ocr = n_text = n_unreadable = 0
    n_marked = n_missed = 0
    root_out = root / "build" / "_scratch" / "408-raw-pages"
    for rec in chosen:
        rel = Path(rec["path"])
        src = (root / rel).resolve()
        if not src.is_relative_to(root / "sources") or not src.is_file():
            print(f"[skip] 来源不在授权目录内/不存在: {rel}", file=sys.stderr)
            continue
        sha = digest(src)
        if sha != rec["sha256"]:
            raise SystemExit(f"[stop] 来源sha256异常: {rel}（请勿改写底本）")
        out = root_out / rel.with_suffix("")
        out.mkdir(parents=True, exist_ok=True)
        with pymupdf.open(str(src)) as doc:
            for page_no, page in enumerate(doc, start=1):
                textfile = out / f"page-{page_no:03d}.txt"
                metafile = out / f"page-{page_no:03d}.json"
                settings = {"source_sha256": sha, "page": page_no,
                            "ocr_mode": args.ocr, "dpi": args.dpi,
                            "min_chars": args.min_chars,
                            "scripts": "v7"}   # 汉字/横线两条判据 → 旧缓存必须失效重取
                if metafile.exists() and textfile.exists():
                    try:
                        previous = json.loads(metafile.read_text(encoding="utf-8"))
                        if all(previous.get(k) == v for k, v in settings.items()):
                            cached += 1
                            continue
                    except (ValueError, OSError):
                        pass
                if args.limit_pages and processed >= args.limit_pages:
                    print(f"[limit] 本次处理 {processed} 页，剩余下次可断点续跑")
                    print(f"[summary] 新处理 {processed}，缓存命中 {cached}；"
                          f"文字层 {n_text}，OCR {n_ocr}，未读文字 {n_unreadable}；"
                          f"上下标已标 {n_marked}，放弃 {n_missed}")
                    return 0
                extracted = page.get_text("text", sort=True).strip()
                marked: list = []
                missed: list = []
                method, confidence = "text-layer", None
                if len(extracted) < args.min_chars:
                    if args.ocr == "auto":
                        if engine is None:
                            np, engine = setup_ocr()
                        extracted, confidence = ocr_page(page, np, engine, args.dpi)
                        method = "ocr-unverified"
                        n_ocr += 1
                    else:
                        method = "missing-text-needs-ocr"
                        n_unreadable += 1
                else:
                    n_text += 1
                    # 文字层才有 span 结构可判上下标；OCR 出来的没有，别假装有。
                    extracted, marked, missed = mark_scripts(extracted, collect_scripts(page))
                    n_marked += len(marked)
                    n_missed += len(missed)
                # Drafts remain isolated from student questions and teacher answers.
                textfile.write_text(extracted + "\n", encoding="utf-8", newline="\n")
                info = {**settings, "source_path": rel.as_posix(),
                        "source_page": page_no, "method": method,
                        "status": "unverified", "characters": len(extracted),
                        "confidence_mean": confidence,
                        "contains_images": bool(page.get_images(full=True)),
                        "scripts_marked": marked, "scripts_unmarked": missed,
                        "processed_at": datetime.now(timezone.utc).isoformat()}
                metafile.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8", newline="\n")
                processed += 1
                print(f"[page] {rel.name} p{page_no:02d} {method} {len(extracted)} chars")
    print(f"[summary] 新处理 {processed}，缓存命中 {cached}；"
          f"文字层 {n_text}，OCR {n_ocr}，未读文字 {n_unreadable}；"
          f"上下标已标 {n_marked}，放弃 {n_missed}")
    print("[note] 页面草稿未经过复核，不得计入47/47完成度")
    return 0


if __name__ == "__main__":
    sys.exit(main())
