#!/usr/bin/env python3
"""答案卷逐页草稿 → `papers/<id>/solutions.md`。

与题目卷不同，答案卷只有两条线：
  · 选择题：1—40 的答案字母，按题号**严格递增**取出；
  · 综合题：以 `NN.【答案要点】` 切段。

诚实性（这是本工具的重点）
--------------------------
2026 起答案卷多为**扫描件**（无文本层），文字来自离线 OCR，属**初稿**：
  · 选择题答案按 1→40 严格递增，缺号/重号/顺序不符一律报错，**绝不猜**；
  · 综合题的 OCR 有明显形近误识——实测 2026 有 `pminl`（应为 `pmin1`）、
    `BTreeroot`（应为 `BTree root`）、`elseif`（应为 `else if`）、
    `mso`（应为 `ms`）、`IR,-4` / `IRu-`（上下标被压平）。
    这些**一律原样保留并逐条列出**，由人工按底本页码核对。
    不「补成像真的」——那会让错误看起来像正确答案，比留白更糟。

用法：
  python -I tools/md_solutions.py --paper exams/2026            # 只出报告
  python -I tools/md_solutions.py --paper exams/2026 --write    # 落盘
  python -I tools/md_solutions.py --paper exams/2026 --write --force
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
# 卷首答案表的三路读法（读到几路算几路），见 tools/answer_grid*.py：
#   答案表 OCR（tools/answer_grid_ocr.py）      —— 读**页面像素**，扫描卷只有它有
#   答案表 文字层（tools/answer_grid.py）        —— 读文字层里那张列式表
#   答案表 人工直读（tools/answer_grid_visual.py）—— 人眼读渲染出来的裁带图
# 三路都做了硬门槛（必须凑齐 1—40 且每号一个字母）。**多路一致才认**；
# 不一致的题号一律留空并点名，不取多数、不取"看着更可靠"的那一方。
GRID_ROOTS = [("答案表·OCR渲染", REPO / "build" / "_scratch" / "answer-grid-ocr"),
              ("答案表·文字层", REPO / "build" / "_scratch" / "answer-grid"),
              ("答案表·人工直读", REPO / "build" / "_scratch" / "answer-visual")]

CHOICE = list(range(1, 41))
COMPREHENSIVE = list(range(41, 48))

# 页眉页脚：`附录／87`、`88／2027年…考试大纲`、独立成行的页码
RE_FOOTER = re.compile(r"^(?:附录\s*[／/]\s*\d+|\d+\s*[／/]\s*20\d\d\s*年.*大纲|"
                       r"20\d\d\s*年全国硕士研究生招生考试\s*$|"
                       r"计算机学科专业基础(?:试题)?参考答案\s*$|"
                       # 页码两侧带装饰点：`• 037 •`、`·017·`（2020/2021 答案卷）。
                       # 这类不管出现在哪都当页脚，装饰点是强证据。
                       r"[•·・]\s*\d{1,3}\s*[•·・])$")
# 光秃秃的页码（无装饰点）。**不能见着就删**——表格里的一列数也长这样，
# 所以只在本页首尾两行非空行的位置上才认，见 read_rows()。
RE_PAGE_NUM = re.compile(r"^\d{1,3}$")
RE_CHOICE = re.compile(r"^(\d{1,2})\s*[.．、•·・]\s*([A-D])?\s*$")
RE_ONLY_LETTER = re.compile(r"^([A-D])\s*[.．、]?\s*$")
# 综合题小标题，各年写法不一，必须都认：
#   2024        `42.【答案要点】`
#   2023/2022/2021 `41.【解析】`
#   2009—2019   `41. 解答：`        —— 没有方括号（11 年 × 7 题 = 77 处）
#   2020 第41/46题 `41• 【解析】`     —— 题号后面是实心圆点而不是句点
# 裸词形式必须带冒号才认，免得把正文里的「…见 41 题解析」之类吃进来。
_COMP_WORD = r"(?:答案要点|解析|参考答案|答案|解答)"
RE_COMP_HEAD = re.compile(r"^(\d{1,2})\s*[.．、•·・]\s*"
                          r"(?:【" + _COMP_WORD + r"】"
                          r"|" + _COMP_WORD + r"\s*[：:])\s*(.*)$")
# 同上的写法但**整个题号都没了**（2024 第 41 题就是这样），只作兜底识别，见 parse_comprehensive。
RE_COMP_HEAD_NONUM = re.compile(r"^(?:【" + _COMP_WORD + r"】|" + _COMP_WORD + r"\s*[：:])\s*$")
# 章标题。**不能**见到章标题就停：2023 的答案卷开头就是「一、单项选择题」，
# 无条件 break 会把整卷答案切掉。只有「非单项选择题」的章标题才代表进入下一节。
RE_ANY_SECTION = re.compile(r"^[一二三四五六七八九]+\s*、\s*(\S+)")
RE_SECTION = RE_ANY_SECTION

# 答案卷的三种共同格式（历年不一致，都要认）：
#   A 型（2023）：`1.【参考答案】D`  —— 逐题标注，最可靠
#   B 型（2022）：`01. B。【解析】…`  —— 答案解析连排，答案紧跟题号
#   C 型（2024）：`1. D` / `2.A` 单独成行
RE_KEY_A = re.compile(r"^(\d{1,2})\s*[.．、]\s*【参考答案】\s*([A-D])(?![A-Za-z])")
RE_KEY_B = re.compile(r"^(\d{1,2})\s*[.．、]\s*([A-D])\s*[。．]\s*【解析】")
# 一行里并排多组「题号 + 字母」：`1． D   2． C   3． A …`（2023 顶部答案表；
# 2022 的答案表也长这样，只是被文本层打乱）。整行**除去配对后只剩空白或零散字母**
# 才算答案行——否则正文里的「如图1 所示」之类会被当成答案。
RE_PAIR = re.compile(r"(\d{1,2})\s*[.．、•·・]\s*([A-D])(?![A-Za-z])")
RE_PAIR_LEFTOVER = re.compile(r"^[A-D\s]*$")
# 「题号 + 一个短记号」但记号不是 A–D：多半是字体映射坏了
# （2024 第17题抽出来是 `17.℃`、第32题是 `32.C°`）。只报告，不猜。
# 但**中文词不算**：2009—2018 的解析流里每道题都有一行 `1. 解析：`，
# 那会被上面这条吃成「疑似字体映射损坏」，一页刷出几十条假告警，把真告警淹掉。
RE_CHOICE_ODD = re.compile(r"^(\d{1,2})\s*[.．、]\s*([^\s一-鿿]{1,3})\s*$")

# ── 2027 模拟卷专用的两种答案写法（真题答案卷没有这两种，见 mock 开关）───────────
# 卷首「答案速查」把 5 题并成一段**区间**：`1-5：ACDCD  6-10：CBCDA …`（全角/半角冒号混用）。
# 一行里可以并排好几段，所以要 finditer 而不是 match。区间宽度与字母数必须相等，
# 不等就整段跳过并点名——宁可留空，也不能把 `1-5` 的 5 个字母错位贴到别的题上。
RE_KEY_RANGE = re.compile(r"(\d{1,2})\s*[-–－~]\s*(\d{1,2})\s*[：:]\s*([A-D]{1,8})(?![A-Za-z])")
# 解析流里答案跟在**上一行的题干**后面：`答案：A。【解析】…`（分隔符「。」可有可无）。
# 它自己不带题号，所以要和最近一次见到的题头行配。
RE_ANSWER_MARK = re.compile(r"^答案\s*[：:]\s*([A-D])(?![A-Za-z])")
RE_QNUM_HEAD = re.compile(r"^(\d{1,2})\s*[.．、]\s*(\S.*)$")
# 综合题的**带题干**小标题：`41. （13分）大数加法…`。模拟卷把 41—47 的题目原文与完整解答
# 重印在解析卷末（set1 在第 21—26 页），而卷首第 1—2 页另有一份简短的评分要点。
# 后者不带 `（N分）`，所以这条只认得下完整解答那一份。
RE_COMP_HEAD_MOCK = re.compile(r"^(\d{1,2})\s*[.．、]\s*（\s*\d+\s*分\s*）")

# OCR 形近误识的机械侦察（只为提示人工，不自动改写）
ARTIFACT_PATTERNS = [
    ("l/1 混淆", re.compile(r"(?:[A-Za-z]l\d|\d l|[A-Za-z]l(?=[^a-z]|$))")),
    ("缺空格粘连", re.compile(r"\b(?:typedef|return|else|int|struct|while|for|void)"
                              r"(?:if|for|int|struct|root|data)\b")),
    ("半角括号混用", re.compile(r"[(].*[（]|[）].*[)]")),
    ("单位 ms 误识", re.compile(r"\bm(?:so|S|s0)\b|\bms o\b")),
    ("上下标压平", re.compile(r"IR[,\-]\d|IR[uv-][\-−]?")),
    ("多余/缺失标点", re.compile(r"，\s*$|\belseif\b")),
]


def paths_for(paper_id: str) -> str:
    kind, rest = paper_id.split("/", 1)
    if kind == "exams":
        return f"sources/exams/answers/{rest}-answer.pdf"
    return f"sources/mock-2027/pdf/mock2027-set{rest.split('-')[1]}-solution.pdf"


def read_rows(rel: str) -> list[tuple[int, str]]:
    folder = PAGES / Path(rel).with_suffix("")
    if not folder.is_dir():
        raise SystemExit(f"[sol] 找不到逐页草稿：{folder}")
    rows: list[tuple[int, str]] = []
    for f in sorted(folder.glob("page-*.txt")):
        pno = int(f.stem.split("-")[1])
        lines = f.read_text(encoding="utf-8").splitlines()
        # 独立成行的纯数字既可能是页脚页码，也可能是表格里的一列数
        # （2024 第42题哈希表那列 0/3/4/5/…/18 就曾被当成页码整列删掉）。
        # 判据用位置：只有出现在**本页首尾两行非空行**里的纯数字才当页码。
        idx = [i for i, l in enumerate(lines) if l.strip()]
        edge = set(idx[:2]) | set(idx[-2:])
        for i, line in enumerate(lines):
            s = line.strip()
            if RE_FOOTER.match(s) or (i in edge and RE_PAGE_NUM.match(s)):
                rows.append((pno, ""))
            else:
                rows.append((pno, line))
    return rows


def load_grid(paper_id: str, log: list) -> dict[int, tuple[str, int]]:
    """读卷首答案表的读法（OCR 渲染 / 文字层），→ {题号: (字母, 页码)}。

    两种读法**互为独立证据**：一致才认；不一致的题号一律留空并点名（不取多数、不取"更可靠"的）。
    只有一种读法时直接采信——它自己已过了「必须凑齐 1…40、每号恰好一个字母」的硬门槛。
    """
    kind, rest = paper_id.split("/", 1)
    if kind != "exams":
        return {}
    stem = f"{rest}-answer"
    per: dict[str, dict] = {}
    pages: dict[str, int] = {}
    for name, root in GRID_ROOTS:
        f = root / f"{stem}.json"
        if not f.is_file():
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        per[name] = {int(k): v for k, v in data["answers"].items()}
        pages[name] = int(data.get("page") or 1)
    out: dict[int, tuple[str, int]] = {}
    for no in range(1, 41):
        vals = {name: d[no] for name, d in per.items() if no in d}
        if len(set(vals.values())) > 1:
            log.append(f"第 {no} 题的答案表读法互相矛盾（"
                       + "、".join(f"{n}={v}" for n, v in vals.items())
                       + "），已留空待人工核对")
            continue
        if vals:
            name = next(iter(vals))
            out[no] = (next(iter(vals.values())), pages[name])
    return out


def parse_choices(rows: list[tuple[int, str]], log: list,
                  grid: dict[int, tuple[str, int]] | None = None,
                  mock: bool = False
                  ) -> dict[int, tuple[str, int]]:
    """→ {题号: (字母, 页码)}。

    分层取，按可靠性从高到低，**低层只补高层没拿到的题号**：
      0. 卷首答案表（OCR 渲染 / 文字层两种读法，见 load_grid）；
      1. 逐题标注（2023 的 `1.【参考答案】D` / 2022 的 `01. B。【解析】`）——最可靠；
      2. 单行一条（2024 的 `1. D`）；
      3. 并排答案行（2023/2022 顶部的 `1． D  2． C …`）。
    同一题号出现**互相矛盾**的字母时，一律丢弃并在 log 里点名——不猜、不取多数。

    `mock=True` 时额外认 2027 模拟卷的两种写法（区间速查 → 第 2 层，`答案：X` → 第 1 层），
    两者照旧互校。真题卷不走这条路，行为一字不改。
    """
    layers: list[dict[int, tuple[str, int]]] = [dict(grid or {}), {}, {}, {}]
    conflicts: dict[int, set[str]] = {}
    pending: int | None = None
    cur_q: int | None = None       # mock 专用：最近一次见到的题头行题号（给 `答案：X` 配题）

    def put(layer: int, no: int, letter: str, pno: int) -> None:
        if not 1 <= no <= 40:
            return
        prev = layers[layer].get(no)
        if prev and prev[0] != letter:
            conflicts.setdefault(no, set()).update({prev[0], letter})
            layers[layer].pop(no, None)
            return
        layers[layer][no] = (letter, pno)

    for pno, line in rows:
        stripped = line.strip()
        sec = RE_ANY_SECTION.match(stripped)
        if sec and not sec.group(1).startswith("单项选择"):
            break                       # 选择题区结束（「二、简答题」之类）
        mh = RE_COMP_HEAD.match(stripped)
        if mh and int(mh.group(1)) >= 41:
            break                       # 已经进入综合题区，后面不会再有选择题答案
        if mock:
            # 区间速查 + `答案：X` 两路。**先收速查**（它带题号，是自足的），
            # 再靠题头行追踪题号去认 `答案：X`（它自己不带题号）。
            hit = False
            for mr in RE_KEY_RANGE.finditer(stripped):
                a, b, letters = int(mr.group(1)), int(mr.group(2)), mr.group(3)
                if b - a + 1 != len(letters):
                    log.append(f"第 {pno} 页速查 `{mr.group(0)}`：区间含 {b - a + 1} 题却有 "
                               f"{len(letters)} 个字母，**整段跳过**（宁可留空，不猜错位）")
                    continue
                for k, ch in enumerate(letters):
                    put(2, a + k, ch, pno)
                hit = True
            mq = RE_QNUM_HEAD.match(stripped)
            if mq and 1 <= int(mq.group(1)) <= 40:
                cur_q = int(mq.group(1))
            ma = RE_ANSWER_MARK.match(stripped)
            if ma:
                if cur_q is None:
                    log.append(f"第 {pno} 页见到 `答案：{ma.group(1)}` 但此前没有题头行，"
                               f"无法定题号，已丢弃")
                else:
                    put(1, cur_q, ma.group(1), pno)
                hit = True
            if hit:
                continue
        m = RE_KEY_A.match(stripped) or RE_KEY_B.match(stripped)
        if m:
            put(0, int(m.group(1)), m.group(2), pno)
            continue
        m = RE_CHOICE.match(stripped)
        if m:
            no = int(m.group(1))
            if not 1 <= no <= 40:
                continue
            letter = m.group(2)
            if letter is None:
                pending = no            # 形如 `22.`，字母被挤到下一行
                continue
            put(1, no, letter, pno)
            pending = None
            continue
        if pending is not None:
            only = RE_ONLY_LETTER.match(stripped)
            if only:
                put(1, pending, only.group(1), pno)
                pending = None
                continue
        mo = RE_CHOICE_ODD.match(stripped)
        if mo and 1 <= int(mo.group(1)) <= 40:
            log.append(f"第 {pno} 页「第 {mo.group(1)} 题」的答案记号不是 A–D 而是 "
                       f"`{mo.group(2)}`（疑似字体映射损坏），已留空待人工核对")
        # 并排答案行：先剔掉所有配对，看剩下的是不是只有空白/零散字母
        pairs = list(RE_PAIR.finditer(stripped))
        if len(pairs) >= 2:
            leftover = RE_PAIR.sub("", stripped)
            if RE_PAIR_LEFTOVER.match(leftover):
                for pm in pairs:
                    put(2, int(pm.group(1)), pm.group(2), pno)
                if leftover.strip():
                    log.append(f"第 {pno} 页答案行有 {len(leftover.split())} 个落单字母，"
                               f"未认领（可能是文本层错位）：`{stripped[:60]}`")
    if pending is not None:
        log.append(f"第 {pending} 题的答案字母未找到（未切出），已留空")

    out: dict[int, tuple[str, int]] = {}
    for layer in layers:
        for no, val in layer.items():
            out.setdefault(no, val)
    # 跨层一致性：同一题号在**任何两处来源**给出不同字母，就留空并点名。
    # 2026-10-16 实测：答案表两路 + 解析流在 2012/2020/2021/2022/2023 上零冲突，
    # 所以这条规则不会误伤，只会把真正对不上的地方暴露出来。
    for no in range(1, 41):
        seen = {l[no][0] for l in layers if no in l}
        if len(seen) > 1:
            out.pop(no, None)
            log.append(f"第 {no} 题在不同来源里互相矛盾"
                       f"（{''.join(sorted(seen))}），已留空待人工核对")
    for no in sorted(conflicts):
        if no in out:
            out.pop(no, None)
            log.append(f"第 {no} 题的答案在同一来源内自相矛盾"
                       f"（{''.join(sorted(conflicts[no]))}），已留空待人工核对")
    agree = [no for no in range(1, 41) if sum(1 for l in layers if no in l) > 1]
    if agree:
        log.append(f"以下 {len(agree)} 个题号在多个来源里都取到且**完全一致**：{agree}")
    return out


def parse_comprehensive(rows: list[tuple[int, str]], log: list | None = None,
                        mock: bool = False) -> dict[int, dict]:
    segs: dict[int, dict] = {}
    cur: dict | None = None
    seen: dict[int, list[int]] = {}
    in_comp = False          # 已经进了「综合应用题」区
    for pno, line in rows:
        stripped = line.strip()
        if "综合" in stripped and "应用" in stripped:
            in_comp = True
        # mock：只认带题干的 `NN. （N分）` 头（见 RE_COMP_HEAD_MOCK 处的说明）。
        # 卷首那份不带 `（N分）` 的简短评分要点因此不会被当成题头，
        # 免得把「完整解答」判成重复而丢掉。
        m = RE_COMP_HEAD_MOCK.match(stripped) if mock else RE_COMP_HEAD.match(stripped)
        if m and int(m.group(1)) in COMPREHENSIVE:
            in_comp = True
            no = int(m.group(1))
            seen.setdefault(no, []).append(pno)
            if no in segs:
                # 底本里同一题出现多次（2024 第42/43题在第3、4页各印了一遍）。
                # 只取**首次**，后面那次整段丢弃——两遍的内容未必逐字相同，
                # 合并只会把重复内容灌进正文。页码差异记进报告。
                cur = None
                continue
            head_rest = m.group(2) if not mock else stripped[m.end():]
            cur = {"lines": ([head_rest] if head_rest.strip() else []), "pages": [pno]}
            segs[no] = cur
            continue
        # **没有题号**的 `【答案要点】`：2024 底本第 1 页印的是 `41.【答案要点】`，
        # 但 OCR 只认出了 `【答案要点】`，题号整个丢了（渲染图上一目了然，是 OCR 漏字）。
        # 只在「已进综合题区 + 当前没有正在写的题 + 题号确实还缺」时才按顺序归位，
        # 并且**在报告里点名这是靠位次补的**，交人工复核。
        # mock 不走这条兜底：它的题头本来就**带题干**，靠位次瞎归位只会灌进错内容。
        if (not mock and in_comp and cur is None and log is not None
                and RE_COMP_HEAD_NONUM.match(stripped)):
            pend = [n for n in COMPREHENSIVE if n not in segs]
            if pend:
                no = pend[0]
                seen.setdefault(no, []).append(pno)
                cur = {"lines": [], "pages": [pno], "no_head": True}
                segs[no] = cur
                log.append(f"第 {pno} 页的 `{stripped}` **没有题号**，按综合题顺序归为第 {no} 题"
                           f"（底本该行题号在渲染图上清楚可见，是 OCR 漏了；`no_head` 已标记）")
                continue
        if cur is not None and stripped:
            cur["lines"].append(stripped)
            cur["pages"].append(pno)
    for seg in segs.values():
        seg["span"] = (min(seg["pages"]), max(seg["pages"]))
    for no, pages in seen.items():
        if no in segs and len(pages) > 1:
            segs[no]["dup_pages"] = pages[1:]
    return segs


def join_cjk(lines: list[str]) -> list[str]:
    """把 OCR 的硬折行合并成段落：上一行以汉字/逗号结尾且本行以汉字开头时接上。"""
    out: list[str] = []
    for line in lines:
        if out and re.search(r"[一-鿿，、；：]$", out[-1]) and re.match(r"^[一-鿿]", line):
            out[-1] = out[-1] + line
        else:
            out.append(line)
    return out


def scan_artifacts(segs: dict[int, dict]) -> list[tuple[int, str, str, int]]:
    found = []
    for no in sorted(segs):
        for line in segs[no]["lines"]:
            for name, pattern in ARTIFACT_PATTERNS:
                if pattern.search(line):
                    found.append((no, name, line.strip()[:70], segs[no]["span"][0]))
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paper", required=True)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    paper_id = args.paper
    mock = paper_id.startswith("mock")
    rel = paths_for(paper_id)
    log: list[str] = []
    rows = read_rows(rel)
    grid = load_grid(paper_id, log)
    choices = parse_choices(rows, log, grid, mock=mock)
    comp = parse_comprehensive(rows, log, mock=mock)
    artifacts = scan_artifacts(comp)
    if mock:
        log.append("模拟卷另有底本第 1—2 页的「答案速查 + 41—47 简短评分要点」一份；"
                   "本工具只取题末**带题干**的完整解答（见 RE_COMP_HEAD_MOCK），不合并两份")

    # 逐题来源：按层优先级回填，写进 solutions.md 的注释里，便于人工按来源核对。
    flow_only = parse_choices(rows, [], mock=mock)   # 只看解析流，用来判断某题是不是「表 + 解析」双源
    src: dict[int, str] = {}
    for no in choices:
        where = []
        if no in grid:
            where.append("答案表")
        if no in flow_only and flow_only[no][0] == choices[no][0]:
            where.append("解析流")
        src[no] = "·".join(where) or "解析流"

    missing_choice = [n for n in CHOICE if n not in choices]
    missing_comp = [n for n in COMPREHENSIVE if n not in comp]
    methods = {}
    folder = PAGES / Path(rel).with_suffix("")
    confs = []
    for f in folder.glob("page-*.json"):
        info = json.loads(f.read_text(encoding="utf-8"))
        methods[info["method"]] = methods.get(info["method"], 0) + 1
        if info.get("confidence_mean"):
            confs.append(info["confidence_mean"])

    REPORTS.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {paper_id} 答案卷转写报告（机器生成，勿手改）",
        "",
        f"- 底本：`{rel}`",
        f"- 逐页方法：{methods}",
        f"- OCR 平均置信度：{sum(confs) / len(confs):.3f}（{len(confs)} 页）" if confs else "- 文字层提取，无 OCR 置信度",
        f"- 选择题答案：{len(choices)}/40；缺号：{missing_choice or '无'}",
        f"- 其中来自卷首答案表：{len([n for n in choices if n in grid])} 题"
        f"（双源一致的 {len([n for n in choices if n in grid and n in flow_only and flow_only[n][0] == choices[n][0]])} 题）",
        f"- 综合题答案：{len(comp)}/7；缺号：{missing_comp or '无'}",
        "",
        "## 选择题答案（按题号严格递增取出）",
        "",
    ]
    lines.append("　".join(f"{n}.{choices[n][0]}" for n in CHOICE if n in choices) or "（无）")
    lines += ["", "## 综合题 OCR 可疑处（**未自动改写**，需人工按页码核对）", ""]
    if artifacts:
        for no, name, text, page in artifacts:
            lines.append(f"- 第 {no} 题（底本第 {page} 页）[{name}] `{text}`")
    else:
        lines.append("- （机械侦察未命中）")
    lines += ["", "## 综合题分段（页范围）", ""]
    for no in sorted(comp):
        lo, hi = comp[no]["span"]
        note = ""
        if comp[no].get("dup_pages"):
            note = f"；底本在 {comp[no]['dup_pages']} 页又印了一遍，只取首次"
        if comp[no].get("no_head"):
            note += "；⚠️ 底本该处无题号，按综合题位次归位（待人工复核）"
        lines.append(f"- 第 {no} 题：底本第 {lo}—{hi} 页，{len(comp[no]['lines'])} 行{note}")
    lines.append("")
    if log:
        lines += ["## 解析告警", ""] + [f"- {x}" for x in log] + [""]

    rep = REPORTS / f"{paper_id.replace('/', '-')}-solutions.md"
    rep.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"[sol] {paper_id}: 选择 {len(choices)}/40，综合 {len(comp)}/7，"
          f"OCR 可疑 {len(artifacts)} 处 → {rep}")

    if not args.write:
        print("[sol] 未加 --write，仅出报告")
        return 0

    target = REPO / "papers" / paper_id
    sfile = target / "solutions.md"
    if sfile.exists() and not args.force:
        print(f"[sol] {sfile} 已存在；未加 --force，未覆盖")
        return 0

    kind, rest = paper_id.split("/", 1)
    title = (f"{rest} 年全国硕士研究生招生考试 计算机学科专业基础综合 参考答案"
             if kind == "exams" else f"2027 考研 408 模拟卷 {rest.split('-')[1]} 参考答案")
    got_n = len(choices)
    honest = (f"> 选择题答案：已从底本切出 {got_n}/40 题。"
              if got_n == 40 else
              f"> ⛔ 选择题答案只切出 {got_n}/40 题；缺失的题号见下方各题的 ⛔ 标记，"
              f"**没有**用任何方式补全。")
    out = [
        f"<!-- paper: {paper_id} | kind: solutions | status: needs-review -->",
        f"# {title}",
        "",
        f"> 来源：`{rel}`。转写记录见 `build/_scratch/reports/"
        f"{paper_id.replace('/', '-')}-solutions.md`。",
        honest,
        (f"> 选择题答案来自卷首答案表（`tools/answer_grid_ocr.py` 读页面像素 + "
         f"`tools/answer_grid.py` 读文字层，两路互校）与逐题解析流，"
         f"逐题来源见各题上方注释。"
         if grid else
         "> 选择题答案来自逐题解析流（该卷卷首答案表未能整表读出）。"),
        "> 综合题文字若来自扫描件则为 **OCR 初稿**，存在形近误识"
        "（如 `pminl`/`BTreeroot`/`elseif`），**未擅自改写**，",
        "> 核对前请勿当作定论。逐题状态见 `meta.yml`。",
        "",
        "## 一、单项选择题（1—40 题，每小题 2 分，共 80 分）",
        "",
    ]
    for no in CHOICE:
        out += [f"### 第 {no} 题", ""]
        if no in choices:
            out += [f"<!-- 底本第 {choices[no][1]} 页；来源：{src[no]} -->", "",
                    f"答案：{choices[no][0]}", ""]
        else:
            out += ["> ⛔ 答案未从底本切出，待人工补齐。", ""]
    out += ["## 二、综合应用题（41—47 题，共 70 分）", ""]
    for no in COMPREHENSIVE:
        out += [f"### 第 {no} 题", ""]
        seg = comp.get(no)
        if not seg:
            out += ["> ⛔ 答案未从底本切出，待人工补齐。", ""]
            continue
        lo, hi = seg["span"]
        span = f"底本第 {lo} 页" if lo == hi else f"底本第 {lo}—{hi} 页"
        caveat = "；⚠️ 底本该处**题号缺失**（OCR 漏字），本段题号系按综合题位次补的，待人工复核" \
            if seg.get("no_head") else ""
        out += [f"<!-- {span}；OCR 初稿，未逐字核对{caveat} -->", "", "【答案要点】", ""]
        out += join_cjk(seg["lines"])
        out += [""]
    target.mkdir(parents=True, exist_ok=True)
    sfile.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"[sol] 写出 {sfile}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
