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

# 页眉页脚：`附录／87`、`88／2027年…考试大纲`、独立成行的页码
RE_FOOTER = re.compile(r"^(?:附录\s*[／/]\s*\d+|\d+\s*[／/]\s*20\d\d\s*年.*大纲|"
                       r"20\d\d\s*年全国硕士研究生招生考试\s*$|"
                       r"计算机学科专业基础(?:试题)?参考答案\s*$|"
                       r"\d{1,3}\s*)$")
RE_CHOICE = re.compile(r"^(\d{1,2})\s*[.．、]\s*([A-D])?\s*$")
RE_ONLY_LETTER = re.compile(r"^([A-D])\s*[.．、]?\s*$")
# 综合题小标题，各年写法不一：2024 用【答案要点】，2023/2022 用【解析】。
RE_COMP_HEAD = re.compile(r"^(\d{1,2})\s*[.．、]\s*"
                          r"【(?:答案要点|解析|参考答案|答案)】\s*(.*)$")
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
RE_PAIR = re.compile(r"(\d{1,2})\s*[.．、]\s*([A-D])(?![A-Za-z])")
RE_PAIR_LEFTOVER = re.compile(r"^[A-D\s]*$")
# 「题号 + 一个短记号」但记号不是 A–D：多半是字体映射坏了
# （2024 第17题抽出来是 `17.℃`、第32题是 `32.C°`）。只报告，不猜。
RE_CHOICE_ODD = re.compile(r"^(\d{1,2})\s*[.．、]\s*(\S{1,3})\s*$")

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
        for line in f.read_text(encoding="utf-8").splitlines():
            rows.append((pno, "" if RE_FOOTER.match(line.strip()) else line))
    return rows


def parse_choices(rows: list[tuple[int, str]], log: list) -> dict[int, tuple[str, int]]:
    """→ {题号: (字母, 页码)}。

    分层取，按可靠性从高到低，**低层只补高层没拿到的题号**：
      1. 逐题标注（2023 的 `1.【参考答案】D` / 2022 的 `01. B。【解析】`）——最可靠；
      2. 单行一条（2024 的 `1. D`）；
      3. 并排答案行（2023/2022 顶部的 `1． D  2． C …`）。
    同一题号出现**互相矛盾**的字母时，一律丢弃并在 log 里点名——不猜、不取多数。
    """
    layers: list[dict[int, tuple[str, int]]] = [{}, {}, {}]
    conflicts: dict[int, set[str]] = {}
    pending: int | None = None

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
    for no in sorted(conflicts):
        out.pop(no, None)
        log.append(f"第 {no} 题的答案在不同来源里互相矛盾（{''.join(sorted(conflicts[no]))}），"
                   f"已留空待人工核对")
    dup = [no for no in range(1, 41)
           if sum(1 for l in layers if no in l) > 1]
    if dup:
        log.append(f"以下题号在多个来源里都取到答案（已取最可靠的一层）：{dup}")
    return out


def parse_comprehensive(rows: list[tuple[int, str]]) -> dict[int, dict]:
    segs: dict[int, dict] = {}
    cur: dict | None = None
    seen: dict[int, list[int]] = {}
    for pno, line in rows:
        m = RE_COMP_HEAD.match(line.strip())
        if m and int(m.group(1)) in COMPREHENSIVE:
            no = int(m.group(1))
            seen.setdefault(no, []).append(pno)
            if no in segs:
                # 底本里同一题出现多次（2024 第42/43题在第3、4页各印了一遍）。
                # 只取**首次**，后面那次整段丢弃——两遍的内容未必逐字相同，
                # 合并只会把重复内容灌进正文。页码差异记进报告。
                cur = None
                continue
            cur = {"lines": ([m.group(2)] if m.group(2).strip() else []), "pages": [pno]}
            segs[no] = cur
            continue
        if cur is not None and line.strip():
            cur["lines"].append(line.strip())
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
    rel = paths_for(paper_id)
    log: list[str] = []
    rows = read_rows(rel)
    choices = parse_choices(rows, log)
    comp = parse_comprehensive(rows)
    artifacts = scan_artifacts(comp)

    missing_choice = [n for n in CHOICE if n not in choices]
    missing_comp = [n for n in COMPREHENSIVE if n not in comp]
    methods = {}
    folder = PAGES / Path(rel).with_suffix("")
    import json
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
            out += [f"<!-- 底本第 {choices[no][1]} 页 -->", "",
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
        out += [f"<!-- {span}；OCR 初稿，未逐字核对 -->", "", "【答案要点】", ""]
        out += join_cjk(seg["lines"])
        out += [""]
    target.mkdir(parents=True, exist_ok=True)
    sfile.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"[sol] 写出 {sfile}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
