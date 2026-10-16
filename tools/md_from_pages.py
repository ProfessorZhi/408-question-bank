#!/usr/bin/env python3
"""把 build/_scratch/408-raw-pages/ 的逐页草稿，转成 questions.md / solutions.md。

立场
----
这是**机械转写**，不是「理解后重写」。凡是机器没有把握的地方，一律：
  · 原样保留文字
  · 在 build/_scratch/reports/<paper>-transcribe.md 里列出来
  · 该题状态记为 needs-review / ocr-uncertain
绝不猜测、绝不把缺的字符「补得像真的」。

规范化（逐条可复算）
--------------------
N1 去页脚：含 `第 N 页（共 M 页）` 的整行丢弃，并按空行处理。
N2 着重号还原：源 PDF 用 n 个全角句点 `．` 表示 n 个字的着重号。
   已用**几何证据**确认：`．` 的基线比同行正文低约 4.6pt（点在被强调字下方），
   且点数 == 被强调字数（`错误．．`=2、`不可能．．．`=3、`不属于．．．`=3）。
   还原成 `**被强调的字**`。每次替换都写进报告，可逐条审计。
N3 标点前空白：删掉紧挨中文标点（含 `．`）前的空白，这是排版产物。
N4 续行合并：普通段落内折行直接拼接；仅当两侧都是 ASCII 词字符时补一个空格。

逐段分类（决定怎么排版，不改字）
--------------------------------
`text`    普通段落 → 合并成一行，走 N2/N3/N4。
`code`    代码段 → 围栏块，保留原始换行与缩进（不合并、不折叠空白）。
`table`   表格段 → 围栏块，保留原始列宽。**不擅自改成 GFM 表**：
          列边界要靠字形的 x 坐标才判得准，用空格猜会把行拆错。
`verbatim` 其它需要保形的段（如题图题注行）→ 围栏块。

不做的（刻意）
--------------
· **不猜上下标**。实测源 PDF 里 `p2`/`p1` 与正文同字号同基线（`flags` 无上标位），
  是上游重排版本就压平了，不是我们提取丢的。此类一律原样保留并在报告里点名。
· 不把答案写进 questions.md（C8 阻断项）。
· 不给综合题编造答案文字。

用法：
  python -I tools/md_from_pages.py --paper exams/2026            # 只出报告
  python -I tools/md_from_pages.py --paper exams/2026 --write    # 落盘
  python -I tools/md_from_pages.py --paper exams/2026 --force    # 覆盖已存在文件
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parent.parent
PAGES = REPO / "build" / "_scratch" / "408-raw-pages"
REPORTS = REPO / "build" / "_scratch" / "reports"

CHOICE = list(range(1, 41))
COMPREHENSIVE = list(range(41, 48))
EXPECTED = CHOICE + COMPREHENSIVE

RE_FOOTER = re.compile(r"第\s*\d+\s*页\s*[（(]\s*共\s*\d+\s*页\s*[)）]")
RE_EMPHASIS = re.compile(r"\s*．+")
RE_CJK = re.compile(r"[一-鿿㐀-䶿]")
RE_SPACE_BEFORE_PUNCT = re.compile(r"[ \t]+([，。、；：？！）》」』】．])")
RE_MANY_SPACES = re.compile(r"[ \t]{2,}")
RE_QSTART = re.compile(r"^(\d{1,3})\s*[.．、]\s*(.*)$", re.S)
RE_SECTION = re.compile(r"^[一二三四五六七八九十]+\s*、\S")
RE_SCORE = re.compile(r"（\s*本题\s*(\d+(?:\.\d+)?)\s*分\s*）")
RE_FIGREF = re.compile(r"题\s*(\d{1,2})\s*([图表])")
# 题号标题（图表标题单独成行，必须断段，否则会被吸进上一句）
# 允许结尾带分图号 `（a）`：2025 第44题的两张图题注就是「题44 图（a）」「题44 图（b）」，
# 只认「题44 图」会把它们当正文留在题干里（实测题干里出现了「如题44 图题44 图（a）」）。
RE_CAPTION = re.compile(r"^题\s*(\d{1,3})\s*(?:题)?([图表])\s*(?:[（(][a-zA-Z][)）])?\s*$")
# 「像题注」的独立行：题NN 图/表（可选分图号）、表1、图2-1 等。
# 只有这种行才配当表格标题；否则一律用中性占位，**不许**拿题干残句当标题
# （2025 实测会写出 `**的是。**`、`**代码如下。**` 这种把句子截断的假标题）。
RE_CAP_LIKE = re.compile(r"^(?:题\s*)?\d{0,3}\s*[-—－]?\s*\d{0,3}\s*[图表]\s*\d{0,3}"
                         r"\s*(?:[（(][a-zA-Z][)）])?$")
# 小题编号：（1）（2）
RE_SUBQ = re.compile(r"^[（(]\s*\d{1,2}\s*[)）]")
# 罗马数字序号项：I. II. III. IV.
RE_ROMAN = re.compile(r"^[IVX]{1,4}\s*[.、．]\s")
# 形如 `F1：…` / `I1：…` / `R1：…` 的带标号条目，也要各自成段（2026 第36题的 F1~F4）
RE_TAGGED = re.compile(r"^[A-Z]{1,3}\d{0,3}\s*[：:]\s*\S")
# 代码特征
RE_CODE_LINE = re.compile(r"(#include|\btypedef\b|\bstruct\b|//|/\*|;\s*$|\{\s*$|\}\s*$)")
RE_CODE_ANY = re.compile(r"^\s*(-|\+|\*|/\*)")
# 选项标记
# 分隔符只认「行首或任意空白」。早先要求「行首 / 两个以上空格」，于是把
#   2025 第31题 `…（FAT） D. 文件控制块（FCB）`（单空格）
#   2024 第39题 `A. 0001 … B. 0001 … C. 1110 … D. 1110 …`（数字后单空格）
#   2023 第18题 `A.仅I、II B.仅I、IV C. 仅II、III D. 仅I、II、IV`（字母后单空格）
# 全判成「选项切不干净」。放宽到任意空白是安全的：调用方还要求这四处标记
# **按 A→B→C→D 顺序出现、且切完恰好 4 段**，正文里偶然冒出的一个「A.」凑不齐四连。
_OPT_SEP = r"(?:^|\s)"
RE_OPT_MARK = re.compile(_OPT_SEP + r"([A-D])\s*[.、．]\s*")
# 前瞻里**不能**要求标点后面还有空白：`A.仅I、II`（2023 第18题）标点后就紧跟正文，
# 一旦要求 `\s`，整条选项行切不出来；而上面的 RE_OPT_MARK 用的是 `\s*`，
# 两处不一致会让「标记找得到、切不出四段」这种最难查的失败出现。
RE_SPLIT_OPT = re.compile(_OPT_SEP + r"(?=[A-D]\s*[.、．])")
RE_OPT_LINE_START = re.compile(r"^[A-D]\s*[.、．]\s")
# 表格里的一个“格子”；以选项/罗马序号开头的行不是表格行（那是选项区）
RE_OPT_CELL = re.compile(r"^(?:[A-D]|[IVX]{1,4})\s*[.、．]\s")
RE_QANCHOR = re.compile(r"^(\d{1,3})\s*[.．、]")
# 上/下标标记（`batch_extract.py` 插进逐页草稿正文的那层外壳）。
# ⚠️ 本工具的文字有**两个来源**，口径不同：
#   · 正文流 —— 来自 `build/_scratch/408-raw-pages/` 的草稿，**带**上下标标记；
#   · 表格/题注 —— 来自 `build/_scratch/408-objects/`（`page_objects.py` 直读 PDF），**不带**标记。
# 凡是把两边做「同一段文字吗」的比对，都必须先剥掉标记，否则同一行会被判成两段不同的话。
# 实测代价：2016 第30题的代码行 `//进程P1 //进程P2` 因此**没被从题干里剔掉**，
# 于是同一行在正文（围栏块）和表格首行里各出现一遍（2011/2012/2016/2017/2018/2026 共 6 卷受害）。
RE_MARK = re.compile(r"[\^_]\{([^{}]*)\}")


def strip_marks(text: str) -> str:
    """剥掉上下标标记的外壳，只留字符本身。标记是**注释层**，不参与文本同一性判断。"""
    return RE_MARK.sub(r"\1", text)


OBJ_ROOT = REPO / "build" / "_scratch" / "408-objects"
ROW_TOL = 3.0          # 同一行的 y 容差（pt）
MAX_TABLE_LINES = 2    # 图形簇内文字超过这个数 → 是表格而非插图


def _is_cjk(ch: str) -> bool:
    return bool(RE_CJK.fullmatch(ch))


def restore_emphasis(text: str, log: list) -> str:
    """N2：n 个 `．` → 前 n 个汉字的 `**强调**`。"""
    out, pos = [], 0
    for m in RE_EMPHASIS.finditer(text):
        n = m.group(0).count("．")
        head = text[:m.start()]
        run = []
        for ch in reversed(head):
            if _is_cjk(ch) and len(run) < n:
                run.append(ch)
            else:
                break
        if len(run) < n:
            log.append(f"N2 跳过：前导汉字不足 {n} 个 → …{head[-14:]}{m.group(0)!r}")
            continue
        word = "".join(reversed(run))
        out.append(text[pos:m.start() - n])
        out.append(f"**{word}**")
        pos = m.end()
        log.append(f"N2 着重号：{word} → **{word}**")
    out.append(text[pos:])
    return "".join(out)


def inline_text(text: str, log: list) -> str:
    text = restore_emphasis(text, log)
    text = RE_SPACE_BEFORE_PUNCT.sub(r"\1", text)
    return RE_MANY_SPACES.sub(" ", text).strip()


def join_lines(lines: list[str]) -> str:
    """N4：段落内折行合并（不改字，只决定要不要补空格）。"""
    parts: list[str] = []
    for raw in lines:
        piece = raw.strip()
        if not piece:
            continue
        if parts:
            # 判「要不要补空格」只看**字符本身**，戴着标记看会把行尾的 `}` 当成非字母数字
            # （`…序列P_{1}` 的末字符是 `}`），补空格的条件就永远不成立。
            prev = strip_marks(parts[-1])
            head = strip_marks(piece)
            if prev and head and prev[-1].isascii() and prev[-1].isalnum() \
                    and head[0].isascii() and (head[0].isalnum() or head[0] == "("):
                parts.append(" ")
        parts.append(piece)
    return "".join(parts)


def read_lines(rel: str) -> list[tuple[int, str]]:
    """逐页草稿 → (页码, 原始行)；页脚行替换为空行。"""
    folder = PAGES / Path(rel).with_suffix("")
    if not folder.is_dir():
        raise SystemExit(f"[md] 找不到逐页草稿：{folder}（先跑 tools/batch_extract.py）")
    rows: list[tuple[int, str]] = []
    for f in sorted(folder.glob("page-*.txt")):
        pno = int(f.stem.split("-")[1])
        for line in f.read_text(encoding="utf-8").splitlines():
            rows.append((pno, "" if RE_FOOTER.search(line) else line))
    return rows


def force_break(stripped: str) -> bool:
    """这一行是否必须自成一段（否则会被上下句吸掉）。"""
    view = strip_marks(stripped)
    if RE_OPT_LINE_START.match(view):
        return True
    if RE_CAPTION.match(view):
        return True
    if RE_SUBQ.match(view) or RE_ROMAN.match(view):
        return True
    if RE_TAGGED.match(view):
        return True
    if RE_CODE_LINE.search(view):
        return True
    # 表格行：去掉首尾空白后仍有 ≥2 处连续多空格
    return len(RE_MANY_SPACES.findall(view)) >= 2


def is_codeish(para: dict) -> bool:
    """这一段像不像代码（宽松判据，只用来决定「相邻两段要不要并成一块」）。

    刻意比 `classify_paragraph` 松：`{  int data;` 这类单行也要算，否则代码会被
    拆成一段一行。判错成代码的代价只是多一对围栏，判错成正文的代价是缩进丢失。
    """
    return any(RE_CODE_LINE.search(strip_marks(ln.strip()))
               for ln in para["lines"] if ln.strip())


def classify_paragraph(lines: list[str]) -> str:
    text = strip_marks("\n".join(lines))
    stripped = [strip_marks(ln.strip()) for ln in lines if ln.strip()]
    if not stripped:
        return "text"
    code_hits = sum(1 for ln in stripped if RE_CODE_LINE.search(ln))
    if code_hits >= 2 or ("{" in text and "}" in text and code_hits >= 1):
        return "code"
    if any(RE_CAPTION.match(ln) for ln in stripped):
        return "table" if len(stripped) > 1 else "verbatim"
    table_rows = sum(1 for ln in stripped if len(RE_MANY_SPACES.findall(ln)) >= 2)
    if table_rows >= 2:
        return "table"
    return "text"


def _cjk_ratio(text: str) -> float:
    body = re.sub(r"\s+", "", strip_marks(text))
    return len(RE_CJK.findall(body)) / len(body) if body else 0.0


def paragraphs_of(lines: list[str]) -> list[dict]:
    paras: list[list[str]] = []
    buf: list[str] = []
    code_mode = False
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            if buf:
                paras.append(buf); buf = []
            code_mode = False
            continue
        stripped = line.strip()
        hint = bool(RE_CODE_LINE.search(strip_marks(stripped)))
        # 代码块的**出口**：出现一整行高汉字占比、又没有代码特征的正文。
        # 题41 的代码后面紧跟着「对于给定的非空二叉搜索树T（root 为…）…」，
        # 中间既没有空行也没有任何可切标记，不这么判就会把题干并进代码围栏。
        if code_mode and not hint and _cjk_ratio(stripped) >= 0.5:
            if buf:
                paras.append(buf); buf = []
            code_mode = False
        if hint:
            code_mode = True
        if force_break(stripped) and buf:
            paras.append(buf); buf = []
        buf.append(line)
    if buf:
        paras.append(buf)

    out: list[dict] = []
    for lines_ in paras:
        item = {"lines": lines_, "kind": classify_paragraph(lines_)}
        # 代码的每一行都命中 force_break，于是被切成一段一行；这里把**连续的**
        # 代码段并回一块，否则围栏会变成一堆只有一行的代码块。
        if out and is_codeish(out[-1]) and is_codeish(item):
            out[-1]["lines"].extend(lines_)
            out[-1]["kind"] = "code"
            continue
        out.append(item)
    for item in out:
        item["raw"] = "\n".join(ln.rstrip() for ln in item["lines"] if ln.strip())
    return out


def extract_options(joined: str) -> tuple[str, dict[str, str], int] | None:
    """切出 (stem, {A..D}, 选项区起点)。只认 A→B→C→D 顺序出现、且切完恰好 4 段的那一处。

    返回起点偏移量是**必需**的：调用方要靠它在段落序列里找到分界，
    不能拿 `stem_raw` 的长度去数换行——选项段前的空白本身含换行，
    数换行会把选项段自己算进题干（2026 第1题就是这么重复出一份选项的）。
    """
    marks = list(RE_OPT_MARK.finditer(joined))
    for i in range(len(marks) - 3):
        if [m.group(1) for m in marks[i:i + 4]] != ["A", "B", "C", "D"]:
            continue
        # 起点取**字母本身**的位置，不取前面那个空白——空白属于上一段，
        # 拿它当起点会让调用方把选项段误判成题干的一部分。
        start = marks[i].start(1)
        region = joined[start:].lstrip("\n")
        pieces = [p for p in RE_SPLIT_OPT.split(region) if p.strip()]
        if len(pieces) != 4:
            continue
        opts: dict[str, str] = {}
        ok = True
        for want, piece in zip("ABCD", pieces):
            m = re.match(r"([A-D])\s*[.、．]\s*(.*)", piece.strip(), re.S)
            if not m or m.group(1) != want:
                ok = False
                break
            opts[want] = m.group(2).strip()
        if ok:
            return joined[:start].strip(), opts, start
    return split_glued_options(joined)


# 「四个选项挤在同一行、且字母紧贴上一段文字」的版式：
#     2011 第 10 题 `A. 顺序存储B. 散列存储C. 链式存储D. 索引存储`
# 字母 B/C/D 前面**一个空白都没有**，`_OPT_SEP` 要求「行首或空白」，于是只认得出 A。
# 实测整批 18 卷只有这一处（脚本 `build/_scratch/probe` 里的普查：其余各卷均为 0 处），
# 所以判据收得很紧，宁可不认也不许误切正文：
#   1. A 标记必须在该行**行首**；
#   2. 该行内 A→B→C→D 依次出现，且**没有别的** A–D 标记、没有跨行；
#   3. 四段文字都非空。
RE_GLUED_LINE = re.compile(r"^A\s*[.、．]\s*(?P<body>.*)$")
RE_GLUED_MARK = re.compile(r"([A-D])\s*[.、．]\s*")


def split_glued_options(joined: str) -> tuple[str, dict[str, str], int] | None:
    """兜底：整行连排的选项行。认不出就返回 None（调用方照旧报「切不干净」）。"""
    lines = joined.split("\n")
    pos = 0
    for li, line in enumerate(lines):
        indent = len(line) - len(line.lstrip())
        m = RE_GLUED_LINE.match(line[indent:])
        if m:
            body = m.group("body")
            marks = list(RE_GLUED_MARK.finditer(body))
            if [x.group(1) for x in marks] == ["B", "C", "D"]:
                bounds = [(0, marks[0].start())]
                bounds += [(a.end(), b.start()) for a, b in zip(marks, marks[1:])]
                bounds += [(marks[-1].end(), len(body))]
                pieces = [body[a:b].strip() for a, b in bounds]
                if all(pieces):
                    return ("\n".join(lines[:li]).strip(), dict(zip("ABCD", pieces)),
                            pos + indent)
        pos += len(line) + 1
    return None


def render_blocks(paras: list[dict], log: list) -> str:
    out: list[str] = []
    for para in paras:
        kind = para["kind"]
        if kind == "text":
            out.append(inline_text(join_lines(para["lines"]), log))
            out.append("")
            continue
        fence = {"code": "c", "table": "text", "verbatim": "text"}[kind]
        out.append(f"```{fence}")
        out.extend(ln.rstrip() for ln in para["lines"] if ln.strip())
        out.append("```")
        out.append("")
    return "\n".join(out).strip()


def segment(rows: list[tuple[int, str]], log: list, drop=None) -> dict:
    """按行切题：题号必须**严格等于下一个期望号**才认，防止正文里的「1.」误切。

    `drop` 给出已由坐标搬走（进表格/进图片题注）的行，避免同一份内容出现两遍。
    """
    segs: dict[int, dict] = {}
    cursor = 0
    cur: dict | None = None
    used: set[tuple[int, str]] = set()
    stats = {"hit": 0, "residue": 0}

    def is_dropped(pno: int, line: str) -> bool:
        if not drop:
            return False
        exact, sorted_map = drop
        key = norm_key(line)
        if not key:
            return False
        if key in exact.get(pno, ()):
            stats["hit"] += 1
            used.add((pno, key))
            return True
        if len(key) >= 10 and "".join(sorted(key)) in sorted_map.get(pno, ()):
            stats["hit"] += 1
            return True
        return False

    for pno, line in rows:
        stripped = line.strip()
        m = RE_QSTART.match(stripped)
        if m and cursor < len(EXPECTED) and int(m.group(1)) == EXPECTED[cursor]:
            no = int(m.group(1))
            cur = {"no": no, "lines": [m.group(2)], "pages": [pno]}
            segs[no] = cur
            cursor += 1
            continue
        if cur is not None:
            if RE_SECTION.match(stripped):
                continue
            # 先走剔除核账（有副作用：把「计划剔且确实命中」记进 used），
            # 再判题注行——顺序反了会让 collect_tables 登记过的题注行永远算「没找到」，
            # 平白把「残留」计数抬上去，报告就失真了。
            hit = is_dropped(pno, line)
            # 独立成行的题注（「题44 图（b）」「表1」…）不是正文，不能留在题干里
            # ——它已经由表格/插图的标题承担了内容。整行**恰好**是题注才剔，
            # 句中提到「如题43 表所示」不受影响。
            if RE_CAP_LIKE.match(stripped):
                log.append(f"第 {pno} 页剔题注行「{stripped}」")
                continue
            if hit:
                continue
            cur["lines"].append(line)

    # 计划要剔的行里，有哪些**没在文本流里出现**？出现不了就是两边的行切法不一致，
    # 说明表格文字可能还残留在题干里——必须报出来，不能悄悄放过。
    if drop:
        exact = drop[0]
        for pno, keys in exact.items():
            for key in keys:
                if (pno, key) not in used:
                    stats["residue"] += 1

    fig_refs: list[tuple[int, str, int]] = []
    tables: list[int] = []
    for no, seg in segs.items():
        paras = paragraphs_of(seg["lines"])
        seg["paras"] = paras
        joined = "\n".join(p["raw"] for p in paras)
        got = extract_options(joined)
        if got:
            _stem_raw, raw_opts, start = got
            # 题干 = **包含**选项起点那一段之前的段。按段落偏移切，不数换行。
            # ⚠️ 判据必须是「哪一段包含 start」，不能数「偏移量 < start 的段数」：
            # `A.` 前面那个空格本身落在选项段内部，会让选项段被算进题干
            # （2021 第 39 题因此把整行选项又打印了一遍）。
            offsets, pos = [], 0
            for para in paras:
                offsets.append(pos)
                pos += len(para["raw"]) + 1
            k = 0
            for i, off in enumerate(offsets):
                if off <= start:
                    k = i
                else:
                    break
            stem_paras = paras[:k]
            # 选项若与题干挤在同一段（整行形如「…的是。A. x B. y C. z D. w」），
            # 就把这一段在选项起点处截断，别整段丢掉。
            head = joined[offsets[k]:start].strip() if k < len(paras) else ""
            if head:
                stem_paras = stem_paras + [{"lines": [head], "kind": "text", "raw": head}]
            seg["paras"] = stem_paras
            seg["stem"] = render_blocks(stem_paras, log)
            seg["options"] = {k: inline_text(v, log) for k, v in raw_opts.items()}
        else:
            seg["stem"] = render_blocks(paras, log)
            seg["options"] = None
        if any(p["kind"] == "table" for p in paras):
            tables.append(no)
        m_score = RE_SCORE.search(seg["stem"])
        seg["score"] = m_score.group(1) if m_score else None
        seg["page_span"] = (min(seg["pages"]), max(seg["pages"]))
        for mm in RE_FIGREF.finditer(seg["stem"]):
            fig_refs.append((no, mm.group(2), int(mm.group(1))))

    return {"segments": segs, "fig_refs": sorted(set(fig_refs)), "tables": tables,
            "missing": [n for n in EXPECTED if n not in segs], "drop_stats": stats}


# ---------------------------------------------------------------- 坐标对象

def load_objects(paper_id: str) -> dict[int, dict]:
    """读 tools/page_objects.py 的产出；没跑过就返回空（退化为纯文本转换）。"""
    folder = OBJ_ROOT / paper_id.replace("/", "-")
    if not folder.is_dir():
        return {}
    out = {}
    for f in sorted(folder.glob("page-*.json")):
        out[int(f.stem.split("-")[1])] = json.loads(f.read_text(encoding="utf-8"))
    return out


def load_figures(paper_id: str) -> dict[int, list[dict]]:
    f = OBJ_ROOT / paper_id.replace("/", "-") / "figures.json"
    if not f.is_file():
        return {}
    data = json.loads(f.read_text(encoding="utf-8"))
    out: dict[int, list[dict]] = {}
    for fig in data.get("figures", []):
        out.setdefault(fig["q"], []).append(fig)
    return out


def norm_key(text: str) -> str:
    """文本同一性的**唯一**判据：先剥标记，再去掉全部空白。

    剥标记这一步是必需的，不是保险：本函数的两侧分别是「带标记的草稿正文」和
    「不带标记的坐标层文字」，不剥就永远比不中（见 RE_MARK 处的说明）。
    """
    return re.sub(r"\s+", "", strip_marks(text))


def group_rows(lines: list[dict]) -> list[dict]:
    """把带坐标的行按 y 归成“表格行”：同一行可能有多个格子（多个 line 记录）。"""
    rows: list[dict] = []
    for line in sorted(lines, key=lambda l: (l["bbox"][1], l["bbox"][0])):
        placed = None
        for row in reversed(rows[-3:]):
            if abs(line["bbox"][1] - row["y"]) <= ROW_TOL:
                placed = row
                break
        if placed is None:
            rows.append({"y": line["bbox"][1], "cells": [line],
                         "bbox": list(line["bbox"])})
        else:
            placed["cells"].append(line)
            box = placed["bbox"]
            placed["bbox"] = [min(box[0], line["bbox"][0]), min(box[1], line["bbox"][1]),
                              max(box[2], line["bbox"][2]), max(box[3], line["bbox"][3])]
    rows.sort(key=lambda r: r["y"])
    # 同一行里按 x 从左到右排。**必须**补这一步：行是按 y 建起来的，谁先谁后
    # 取决于 y 的小数差（表头「CPU 执行时间」比同行其它格高 0.4pt），
    # 不排就会把最后一列渲染到第一列去。
    for row in rows:
        row["cells"].sort(key=lambda c: c["bbox"][0])
    return rows


def is_table_row(row: dict) -> bool:
    cells = row["cells"]
    if len(cells) < 2:
        return False
    if any(RE_OPT_CELL.match(c["text"].strip()) for c in cells):
        return False                       # 选项行 / 罗马序号行不是表格行
    # 代码行也不是表格行。源码里「注释在右、代码在左」两段 y 只差 0.3pt，
    # 会被 y 容差并成一行两格，看着就像表格。
    return not any(RE_CODE_LINE.search(c["text"].strip()) for c in cells)


def page_regions(obj: dict) -> list[dict]:
    """一页上的表格候选区：连续多格行，或图形簇里夹着成块文字。"""
    rows = group_rows(obj["lines"])
    regions: list[dict] = []

    run: list[dict] = []
    for row in rows:
        if is_table_row(row):
            run.append(row)
        else:
            if len(run) >= 2:
                regions.append({"rows": run, "why": f"{len(run)} 行多格连排"})
            run = []
    if len(run) >= 2:
        regions.append({"rows": run, "why": f"{len(run)} 行多格连排"})

    for cluster in obj.get("clusters", []):
        y0, y1 = cluster["bbox"][1], cluster["bbox"][3]
        # 容差只给 1pt。给到 2pt 就会把紧贴表框下方的那行正文也吞进来
        # （2026 题43：表框 y1=135.8，正文「其中，op1 为…」在 137.6，
        #  于是那行正文被塞成表格的最后一行空行）。
        idx = [i for i, r in enumerate(rows) if y0 - 1 <= r["y"] <= y1 + 1]
        # 选项行**不是表格内容**，它只是正好落进了图形框里：2017 第 1 题的代码块
        # 框把紧跟着的那行「A. O(log n)  B. O(n^(1/2))  C. O(n)  D. O(n log n)」
        # 也框了进来，按表格渲染 → 四个选项被摊成四格，`O(n` 和 `1/2)` 还被拆开，
        # 而正文流里就再也找不到选项（QA 报 C4「选项不齐」）。
        # 把这一行剔出候选区，它回到正文流里才切得出 A/B/C/D。
        idx = [i for i in idx
               if not any(RE_OPT_CELL.match(c["text"].strip()) for c in rows[i]["cells"])]
        if not idx:
            continue
        # 判「表还是图」：文字成堆 → 表。单行也可能是表（如 2026 题28 的地址格式图，
        # 就是一行五个格子），所以「行里有 ≥2 个格子」也算表。
        has_multi = any(len(rows[i]["cells"]) >= 2 for i in idx)
        if len(idx) <= MAX_TABLE_LINES and not has_multi:
            continue
        lo, hi = idx[0], idx[-1]
        # 表头常常落在矢量框之外（框只画数据区），所以向上/下把紧邻的多格行并进来
        while lo - 1 >= 0 and is_table_row(rows[lo - 1]) and rows[lo]["y"] - rows[lo - 1]["y"] < 20:
            lo -= 1
        while hi + 1 < len(rows) and is_table_row(rows[hi + 1]) and rows[hi + 1]["y"] - rows[hi]["y"] < 20:
            hi += 1
        regions.append({"rows": rows[lo:hi + 1],
                        "why": f"图形簇 {cluster['items']} 条线 / area={cluster['area']:.0f}"})

    return dedupe_regions(regions)


def dedupe_regions(regions: list[dict]) -> list[dict]:
    """同一张表会被「多格连排」和「图形簇」各抓一次 —— 只留一份。

    判据是 y 区间重叠超过 60%。同等条件下留行数多的那份（信息更全）；
    行数一样则留「多格连排」那份（它的行是按文字边界切的，比矢量框更贴合）。
    """
    kept: list[dict] = []
    for region in sorted(regions, key=lambda r: -len(r["rows"])):
        top, bottom = region["rows"][0]["y"], region["rows"][-1]["y"]
        dup = False
        for other in kept:
            o_top, o_bot = other["rows"][0]["y"], other["rows"][-1]["y"]
            span = max(bottom, o_bot) - min(top, o_top)
            cover = min(bottom, o_bot) - max(top, o_top)
            if span > 0 and cover / span > 0.6:
                dup = True
                break
        if not dup:
            kept.append(region)
    return sorted(kept, key=lambda r: r["rows"][0]["y"])


def _overlap(a: tuple, b: tuple) -> float:
    return min(a[1], b[1]) - max(a[0], b[0])


def build_gfm(rows: list[dict]) -> list[list[str]]:
    """按 x 区间把格子落进列。

    列边界取自**格子最多的那一行**（通常就是表头）。用「最大横向重叠」判定归属，
    而不是「最近的 x 起点」——因为像「功能说明」这种长格子的起点和它的数据列
    差得很远，按起点会被塞进隔壁列。
    """
    grid = [[{"text": c["text"].strip(), "x0": c["bbox"][0], "x1": c["bbox"][2]}
             for c in r["cells"]] for r in rows]
    width = max(len(r) for r in grid)
    anchor = next(r for r in grid if len(r) == width)
    cols = [(c["x0"], c["x1"]) for c in anchor]

    out: list[list[str]] = []
    for row in grid:
        line = [""] * width
        for cell in row:
            best, best_ov = 0, -1e9
            for i, col in enumerate(cols):
                ov = _overlap((cell["x0"], cell["x1"]), col)
                if ov > best_ov:
                    best, best_ov = i, ov
            line[best] = f"{line[best]} {cell['text']}".strip() if line[best] else cell["text"]
        out.append(line)
    return out


def spans_to_text(line: dict, size: float) -> str:
    """无列结构时按 x 间距近似还原空白（等宽块用）。

    空格宽度按 0.5em 估（本卷正文 12pt，数字/字母为半宽）。不做「精确列对齐」
    的承诺——列宽要靠字形宽度才算得准，这里的产出是**保内容不保像素**。
    """
    unit = max(3.0, size * 0.5)
    out: list[str] = []
    prev_x1 = None
    for span in line["spans"]:
        text = span["text"]
        if prev_x1 is not None and text[:1] not in (" ", "") and text[:1].strip():
            gap = span["bbox"][0] - prev_x1
            n = int(round(gap / unit))
            if n > 0 and out and not out[-1].endswith(" "):
                out.append(" " * n)
        out.append(text)
        prev_x1 = span["bbox"][2]
    return "".join(out).rstrip()


def assign_owners(objs: dict[int, dict]):
    """逐页算题号锚点，返回 owner_of(pno, y)。

    规则：该 y 之上最近的新题号；本页没有就沿用上一页结尾时正在写的那道题
    （题43 起于第 7 页、它的表在第 8 页，必须跨页沿用，否则会挂错题）。
    """
    anchors: dict[int, list[tuple[float, int]]] = {}
    carry: dict[int, int | None] = {}
    last: int | None = None
    for pno in sorted(objs):
        found = sorted((l["bbox"][1], int(m.group(1))) for l in objs[pno]["lines"]
                       if (m := RE_QANCHOR.match(l["text"].strip())) and l["bbox"][0] < 130)
        anchors[pno] = found
        carry[pno] = last
        if found:
            last = found[-1][1]

    def owner_of(pno: int, y: float) -> int | None:
        above = [no for ay, no in anchors.get(pno, []) if ay <= y]
        return above[-1] if above else carry.get(pno)

    return owner_of


def collect_tables(objs: dict[int, dict], figs: dict[int, list[dict]]):
    """→ (tables_by_q, drop, stats)

    drop 是「已用坐标搬走、要从文本流里剔掉」的行：{页码: {去空白后的文本}}。
    重复剔除靠字符集兜底（同一页、同一批字符），避免 sort 顺序不同导致漏剔而
    在题干里留下表格残渣。
    """
    owner_of = assign_owners(objs)
    tables: dict[int, list[dict]] = {}
    drop_exact: dict[int, set[str]] = {}
    drop_sorted: dict[int, set[str]] = {}
    stats = {"regions": 0, "gfm": 0, "mono": 0, "orphan": 0, "dropped": 0, "residue": 0,
             "fig_covered": 0}

    # 同一块内容既被裁成图、又被判成表 —— **留图、弃表**。
    # 2027 模拟卷把**行内公式**画成矢量路径（没有文本层），它同时满足「图形簇」
    # 和「行里有 ≥2 个格子」两条判据：Q13 的 `1e10 = 1.001…×2³³` 因此既出了一张
    # `q13-fig.png`，又出了一张只有一行的伪表；Q3 的四个选项公式亦然，还会在正文里
    # 留下一段空的 `A.／B.／C.／D.` 骨架。判据是**纵向完全落在一张已裁图的 bbox 内**
    # （同页、±2pt 容差），此时图就是这段内容最忠实的表示。
    fig_boxes: dict[int, list[tuple]] = {}
    for _flist in figs.values():
        for _f in _flist:
            _b = _f.get("bbox")
            if _b:
                fig_boxes.setdefault(_f["page"], []).append(tuple(_b))

    def mark(pno: int, keys: list[str]) -> None:
        for key in keys:
            if not key:
                continue
            drop_exact.setdefault(pno, set()).add(key)
            if len(key) >= 10:
                drop_sorted.setdefault(pno, set()).add("".join(sorted(key)))

    for pno in sorted(objs):
        obj = objs[pno]
        rows = group_rows(obj["lines"])
        for region in page_regions(obj):
            stats["regions"] += 1
            region_rows = region["rows"]
            _top = region_rows[0]["bbox"][1]
            _bot = region_rows[-1]["bbox"][3]
            if any(_b[1] - 2 <= _top and _bot <= _b[3] + 2
                   for _b in fig_boxes.get(pno, [])):
                stats["fig_covered"] += 1
                continue
            owner = None
            cap_line = None
            first_y = region_rows[0]["y"]
            for row in rows:
                if row["y"] >= first_y:
                    break
                if len(row["cells"]) == 1 and first_y - row["y"] < 22:
                    text = row["cells"][0]["text"].strip()
                    m = RE_CAPTION.match(text)
                    if m:
                        owner = int(m.group(1))
                        cap_line = text
                    elif RE_CAP_LIKE.match(text):
                        cap_line = text
                    # 其它短行**不**当题注：那多半是题干被表格截断后的下半句，
                    # 拿来当标题会把句子劈成两半（见 RE_CAP_LIKE 处的说明）。
            if owner is None:
                owner = owner_of(pno, first_y)
            if owner is None:
                stats["orphan"] += 1
                continue

            keys = [norm_key(" ".join(c["text"] for c in r["cells"])) for r in region_rows]
            body: list[str]
            grid = build_gfm(region_rows)
            if max(len(r["cells"]) for r in region_rows) >= 2:
                stats["gfm"] += 1
                body = ["| " + " | ".join(c.replace("|", "\\|") for c in grid[0]) + " |",
                        "|" + "---|" * len(grid[0])]
                body += ["| " + " | ".join(c.replace("|", "\\|") for c in r) + " |"
                         for r in grid[1:]]
                kind = "gfm"
            else:
                stats["mono"] += 1
                body = []
                for row in region_rows:
                    for cell in row["cells"]:
                        body.append(spans_to_text(cell, cell["size"]))
                        keys.append(norm_key(cell["text"]))
                kind = "mono"

            if cap_line:
                keys.append(norm_key(cap_line))
            mark(pno, keys)
            tables.setdefault(owner, []).append({"page": pno, "kind": kind,
                                                 "caption": cap_line, "body": body,
                                                 "why": region["why"]})

    for figlist in figs.values():
        for f in figlist:
            if f.get("owner_by") != "题注":
                continue
            # 题注行「题NN 图」已由图片 alt 承担，正文里剔掉。
            # ⚠️ 页号要用 f["page"]——figs 的字典键是**题号**不是页号，
            # 拿键当页号会把剔除记到「第 46 页」这种根本不存在的页上，静默失效。
            mark(f["page"], [norm_key(f"题{f['q']}图"), norm_key(f"题{f['q']}题图")])

    return tables, (drop_exact, drop_sorted), stats


def render_questions(paper_id: str, title: str, src_path: str, data: dict) -> str:
    segs = data["segments"]
    head = [
        f"<!-- paper: {paper_id} | kind: questions | status: needs-review -->",
        f"# {title}",
        "",
        f"> 来源：`{src_path}`（见 docs/provenance.md S1）",
        "> ⚠️ 本文件为**机械转写稿**，尚未逐题对照原文。逐题状态见 `meta.yml`，",
        "> 转写存疑点见 `build/_scratch/reports/`。",
        "",
        "## 一、单项选择题（1—40 题，每小题 2 分，共 80 分）",
        "",
    ]
    body: list[str] = []

    def one(no: int, with_options: bool) -> None:
        seg = segs.get(no)
        body.append(f"### 第 {no} 题")
        body.append("")
        if not seg:
            body.extend(["> ⛔ 本题未从底本切出，待人工补齐（见转写报告）。", ""])
            return
        lo, hi = seg["page_span"]
        span = f"底本第 {lo} 页" if lo == hi else f"底本第 {lo}—{hi} 页"
        body.extend([f"<!-- {span} -->", ""])
        body.append(seg["stem"])
        body.append("")

        # 图与表按底本先后插入，位置取「题干之后、选项之前」；
        # 注意有些卷子把图排在选项**之后**，这里统一提到选项前更好读，
        # 原位置记在注释里，不假装和底本版式一致。
        items = [(t["page"], 0, "table", t) for t in data["tables_by_q"].get(no, [])]
        items += [(f["page"], 1, "fig", f) for f in data["figs_by_q"].get(no, [])]
        for page, _tie, kind, item in sorted(items, key=lambda x: (x[0], x[1])):
            if kind == "table":
                # 无题注时用中性说法，且按形态区分：等宽块常常是代码/位域表，
                # 一律叫「表格」会误导读者（2025 第44题那块其实是机器级代码）。
                fallback = (f"底本第 {page} 页表格（原底本未给题注）"
                            if item["kind"] == "gfm"
                            else f"底本第 {page} 页独立排版块（无列结构，按等宽保形；"
                                 "原底本未给题注）")
                cap = item["caption"] or fallback
                body.append(f"**{cap}**")
                body.append("")
                if item["kind"] == "mono":
                    # 无列结构（如「题43 表」的指令表），靠 x 间距还原的空格**必须**放进
                    # 围栏块——裸文本行会被 Markdown 折叠成一个空格，版面直接毁掉。
                    body.append("```text")
                    body.extend(item["body"])
                    body.append("```")
                else:
                    body.extend(item["body"])
                body.append("")
            else:
                body.extend([f"<!-- 图见底本第 {page} 页；归属依据：{item.get('owner_by')} -->",
                             f"![题 {no} 图]({item['file']})", ""])

        if not with_options:
            return
        if seg.get("options"):
            for letter in "ABCD":
                body.append(f"{letter}. {seg['options'][letter]}")
            body.append("")
        else:
            body.extend(["> ⚠️ 未能可靠切出 A/B/C/D 四个选项；原文见上方，待人工整理。", ""])

    for no in CHOICE:
        one(no, True)
    body.extend(["## 二、综合应用题（41—47 题，共 70 分）", ""])
    for no in COMPREHENSIVE:
        one(no, False)
    return "\n".join(head + body).rstrip() + "\n"


def slug(paper_id: str) -> str:
    return paper_id.replace("/", "-")


def paths_for(paper_id: str) -> tuple[str, str]:
    kind, rest = paper_id.split("/", 1)
    if kind == "exams":
        return (f"sources/exams/papers/{rest}.pdf",
                f"sources/exams/answers/{rest}-answer.pdf")
    n = rest.split("-")[1]
    return (f"sources/mock-2027/pdf/mock2027-set{n}-paper.pdf",
            f"sources/mock-2027/pdf/mock2027-set{n}-solution.pdf")


def title_for(paper_id: str) -> str:
    kind, rest = paper_id.split("/", 1)
    if kind == "exams":
        return f"{rest} 年全国硕士研究生招生考试 计算机学科专业基础综合"
    return f"2027 考研 408 模拟卷 {rest.split('-')[1]}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paper", required=True, help="如 exams/2026 或 mock-2027/set-1")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    paper_id = args.paper
    paper_rel, _ans_rel = paths_for(paper_id)
    objs = load_objects(paper_id)
    figs_by_q = load_figures(paper_id)
    tables_by_q, drop, tstats = collect_tables(objs, figs_by_q)
    log: list[str] = []
    rows = read_lines(paper_rel)
    data = segment(rows, log, drop)
    data["tables_by_q"] = tables_by_q
    data["figs_by_q"] = figs_by_q
    segs = data["segments"]

    no_opts = [n for n in CHOICE if n in segs and not segs[n].get("options")]
    kinds: dict[str, int] = {}
    for seg in segs.values():
        for para in seg["paras"]:
            kinds[para["kind"]] = kinds.get(para["kind"], 0) + 1

    REPORTS.mkdir(parents=True, exist_ok=True)
    report = [
        f"# {paper_id} 转写报告（机器生成，勿手改）",
        "",
        f"- 有效行数：{len(rows)}",
        f"- 切出题号：{len(segs)}/47（选择 {sum(1 for n in segs if n <= 40)}/40，"
        f"综合 {sum(1 for n in segs if n >= 41)}/7）",
        f"- 未切出的题号：{data['missing'] or '无'}",
        f"- 选项切不干净的题：{no_opts or '无'}",
        f"- 段落类型统计：{kinds}",
        "",
        "## 图表引用（**需要裁图进 assets/**）",
        "",
    ]
    if data["fig_refs"]:
        for q, kind_cn, ref in data["fig_refs"]:
            lo, hi = segs[q]["page_span"]
            report.append(f"- 第 {q} 题 → 「题 {ref} {kind_cn}」（底本第 {lo}—{hi} 页）")
    else:
        report.append("- （无）")
    report += ["", "## 表格（坐标块：真 GFM 或等宽保形）", "",
               f"- 坐标区 {tstats['regions']} 处 → GFM {tstats['gfm']}、等宽 {tstats['mono']}、"
               f"归属不明 {tstats['orphan']}", ""]
    if tables_by_q:
        for q in sorted(tables_by_q):
            for t in tables_by_q[q]:
                note = "GFM 表" if t["kind"] == "gfm" else "等宽保形（无列结构，只保内容不保像素）"
                report.append(f"- 第 {q} 题（底本第 {t['page']} 页，{t['why']}）：{note}"
                              + (f"，题注「{t['caption']}」" if t["caption"] else ""))
    else:
        report.append("- （无）")
    report += ["", "## 图（已裁进 assets/ 并带相对链接）", ""]
    if figs_by_q:
        for q in sorted(figs_by_q):
            for f in figs_by_q[q]:
                report.append(f"- 第 {q} 题：`{f['file']}`（底本第 {f['page']} 页，"
                              f"归属依据={f.get('owner_by')}）")
    else:
        report.append("- （无）")
    report += ["", "## 剔除核账（表格/题注文字是否真的从题干里拿走了）", "",
               f"- 计划剔除并**确实命中**：{data['drop_stats']['hit']} 行",
               f"- 计划剔除但**文本流里没找到**：{data['drop_stats']['residue']} 行"
               "（>0 说明两边的行切法不一致，表格文字可能残留在题干，需人工看）"]
    report += ["", "## 规范化留痕", ""]
    seen: dict[str, int] = {}
    for line in log:
        seen[line] = seen.get(line, 0) + 1
    report += [f"- {ln}" + (f"　×{c}" if c > 1 else "") for ln, c in seen.items()] \
        or ["- （无）"]
    report.append("")

    rep_path = REPORTS / f"{slug(paper_id)}-transcribe.md"
    rep_path.write_text("\n".join(report), encoding="utf-8", newline="\n")

    print(f"[md] {paper_id}: 行 {len(rows)}，切出 {len(segs)}/47；"
          f"选项不干净 {len(no_opts)} 题；图表 {len(data['fig_refs'])} 处；"
          f"表格段题 {data['tables'] or '无'}；段落类型 {kinds}")
    if not args.write:
        print("[md] 未加 --write，仅出报告")
        return 0

    target = REPO / "papers" / paper_id
    qfile = target / "questions.md"
    if qfile.exists() and not args.force:
        print(f"[md] {qfile} 已存在；未加 --force，未覆盖")
        return 0
    target.mkdir(parents=True, exist_ok=True)
    qfile.write_text(render_questions(paper_id, title_for(paper_id), paper_rel, data),
                     encoding="utf-8", newline="\n")
    print(f"[md] 写出 {qfile}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
