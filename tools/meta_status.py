#!/usr/bin/env python3
"""按**实际转写来源**回填 meta.yml 的逐题状态。

纪律（比功能重要）
------------------
1. **本工具永远不会写出 `proofread`。** 逐题状态机见 docs/qa-policy.md，
   `proofread` 的含义是「有人拿底本逐字比过」。机器没有比过，就没有资格写。
   批量刷 `proofread` 制造绿灯，是 docs/qa-policy.md 点名的**造假**。
2. 状态只由**可复算的事实**决定：这道题的题目来自文字层、人工逐页转录还是 OCR，
   答案来自哪边。不做任何「看起来已经对了吧」的推断。
3. 只改 `questions:` 里那一行 `- {"no": N, ...}`，文件其余部分（注释、来源块、
   errata、review）**逐字节保持原样**——所以用外科式文本替换，不做 YAML 往返。

「人工逐页转录」怎么算进来
--------------------------
扫描卷（`mock-2027/set-2` 起）的正文不是 OCR 草稿，而是人对着页图逐页抄的：
登记在 `papers/<id>/pages.yml` + `pages/page-NNN.txt`（题目侧）与
`solution-pages.yml` + `solution-pages/page-NNN.txt`（答案侧）。
这两份登记由 `md_from_pages.load_page_overrides` / `md_solutions.load_solution_overrides`
校验（登记与文件必须一一对应，否则硬报错退出），本工具**直接复用**它俩，
不自己再读一遍 YAML —— 免得两处判据漂移。
逐题的页范围来自产物里的注释（`questions.md` 的 `<!-- 底本第 N 页 -->`、
`solutions.md` 的 `<!-- 底本第 N 页；来源：… -->`），所以「这题是人工抄的」是
**能从产物复算出来的事实**，不是谁记得。

状态取值
--------
  needs-review   题目与答案都取自文字层或人工逐页转录，但**尚未人工对照底本**。
  ocr-uncertain  至少一侧来自扫描件 OCR；文字可能有形近误识。

用法：
  python -I tools/meta_status.py --paper exams/2026            # 只看会改成什么
  python -I tools/meta_status.py --paper exams/2026 --write
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
RAW = REPO / "build" / "_scratch" / "408-raw-pages"

RE_QROW = re.compile(r'^(\s*- \{)"no": (\d+)(.*)\}\s*$')
RE_QFIELD = re.compile(r'status:\s*([A-Za-z-]+)')
RE_QTOPIC = re.compile(r'topic:\s*([^,}]+)')
RE_QNOTES = re.compile(r'notes:\s*"([^"]*)"')
# 产物里的页范围注释：题目卷是 `<!-- 底本第 7 页 -->`，答案卷多一段来源
# `<!-- 底本第 5—7 页；来源：… -->`。两种都吃。
RE_SPAN = re.compile(r"^<!--\s*底本第\s*(\d+)(?:—(\d+))?\s*页")
RE_QHEAD = re.compile(r"^###\s*第\s*(\d{1,2})\s*题")

TOOL = "pymupdf 1.28.2 + rapidocr-onnxruntime 1.4.4"
DATE = "2026-10-16"

QUALITY_NOTE = {
    "text-layer": "文字层",
    "ocr-unverified": "OCR",
    "manual": "人工逐页转录",
    "mixed": "人工逐页转录＋OCR（同一题跨页、两边来源不同）",
}

# 本工具**自己**会写出的 notes 形状。凡是与它不等、又非空的 notes，都当人工写的，
# 一律原样保留（见下面 `keep_human`）。形状从 `QUALITY_NOTE` 现算，加一档就必须同步
# 加进这里，否则人工写的判断会被误当通用文案覆盖掉。
_LABELS = "|".join(re.escape(v) for v in QUALITY_NOTE.values())
RE_GENERIC_NOTE = re.compile(
    rf"^(?:题(?:{_LABELS})(?:／答(?:{_LABELS}))?；未人工对照底本"
    r"|尚未切出（待人工补齐）)$")


def page_methods(src_rel: str) -> dict[int, str]:
    folder = RAW / Path(src_rel).with_suffix("")
    out: dict[int, str] = {}
    for f in sorted(folder.glob("page-*.json")):
        info = json.loads(f.read_text(encoding="utf-8"))
        out[int(f.stem.split("-")[1])] = info["method"]
    return out


def doc_span(path: Path) -> dict[int, tuple[int, int]]:
    """从产物里的 `<!-- 底本第 N 页 -->` 反推每题占的页范围（题目卷/答案卷同一套写法）。"""
    spans: dict[int, tuple[int, int]] = {}
    if not path.is_file():
        return spans
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = RE_QHEAD.match(line)
        if m:
            current = int(m.group(1))
            continue
        m = RE_SPAN.match(line)
        if m and current is not None:
            lo = int(m.group(1))
            spans[current] = (lo, int(m.group(2)) if m.group(2) else lo)
    return spans


def hand_pages(paper_id: str) -> tuple[set[int], set[int]]:
    """→ (题目侧人工逐页转录的页码, 答案侧人工逐页转录的页码)。

    复用产物工具自己的登记校验（`md_from_pages.md_solutions` 那两个 loader）：
    登记了却没有 page-NNN.txt、或有文件却没登记，都会在那里硬报错——
    本工具不再写第二套判据。
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from md_from_pages import load_page_overrides
        from md_solutions import load_solution_overrides
    finally:
        sys.path.pop(0)
    return (set(load_page_overrides(paper_id)),
            set(load_solution_overrides(paper_id)))


def sources_for(paper_id: str) -> tuple[str, str]:
    kind, rest = paper_id.split("/", 1)
    if kind == "exams":
        return (f"sources/exams/papers/{rest}.pdf",
                f"sources/exams/answers/{rest}-answer.pdf")
    n = rest.split("-")[1]
    return (f"sources/mock-2027/pdf/mock2027-set{n}-paper.pdf",
            f"sources/mock-2027/pdf/mock2027-set{n}-solution.pdf")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paper", required=True)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--date", help=f"写进 extraction.date（默认 {DATE}）")
    args = ap.parse_args(argv)

    paper_id = args.paper
    paper_dir = REPO / "papers" / paper_id
    meta = paper_dir / "meta.yml"
    if not meta.is_file():
        raise SystemExit(f"[meta] 缺少 {meta}（先跑 tools/bootstrap_meta.py）")

    paper_rel, ans_rel = sources_for(paper_id)
    qpages = page_methods(paper_rel)
    apages = page_methods(ans_rel)
    qhand, ahand = hand_pages(paper_id)
    spans = doc_span(paper_dir / "questions.md")
    aspan = doc_span(paper_dir / "solutions.md")
    if not qpages:
        raise SystemExit(f"[meta] 缺少逐页草稿：{paper_rel}（先跑 tools/batch_extract.py）")

    def method_in(methods: dict[int, str], span: tuple[int, int],
                  hand: set[int]) -> str:
        """这道题那几页分别是什么来源；一题跨了两种来源就记 `mixed`。

        `hand` 优先于 OCR 草稿：某页既然有人逐字抄过，`page-*.json` 里那句
        `ocr-unverified` 就只是**历史**（那份草稿还在，但已经不是产物的来源了）。
        """
        kinds = {("manual" if p in hand else methods.get(p, "text-layer"))
                 for p in range(span[0], span[1] + 1)}
        if kinds == {"manual"}:
            return "manual"
        if "missing-text-needs-ocr" in kinds:
            return "missing-text-needs-ocr"
        if "ocr-unverified" in kinds:
            return "mixed" if "manual" in kinds else "ocr-unverified"
        return "mixed" if "manual" in kinds else "text-layer"

    lines = meta.read_text(encoding="utf-8").splitlines(keepends=True)
    changed = 0
    tally: dict[str, int] = {}
    methods_seen: set[str] = set()
    # 「没有 OCR 参与」的两档：文字层与人工逐页转录。只有两边都在这一档里，
    # 这题才不是 ocr-uncertain。
    CLEAN = {"text-layer", "manual"}

    for i, line in enumerate(lines):
        m = RE_QROW.match(line.rstrip("\n"))
        if not m:
            continue
        no = int(m.group(2))
        old = RE_QFIELD.search(m.group(3))
        if not old:
            continue
        span = spans.get(no)
        if span is None:
            status, confidence, note = "pending", "null", "尚未切出（待人工补齐）"
        else:
            qm = method_in(qpages, span, qhand)
            # 答案侧逐题页范围取自 solutions.md 的注释；拿不到（旧卷没有这行注释）
            # 就退回**整本判**：整本都有人工转录才算 manual，否则按 OCR。
            # 判不准时偏向保守（标成 ocr-uncertain）——漏标成「没问题」比多标一笔坏处大得多。
            asp = aspan.get(no)
            if asp is not None:
                am = method_in(apages, asp, ahand)
            elif ahand and all(p in ahand for p in apages):
                am = "manual"
            elif apages and all(v == "text-layer" for v in apages.values()) and not ahand:
                am = "text-layer"
            else:
                am = "ocr-unverified"
            methods_seen.update({qm, am})
            if qm in CLEAN and am in CLEAN:
                status, confidence = "needs-review", "medium"
            else:
                status, confidence = "ocr-uncertain", "low"
            note = (f"题{QUALITY_NOTE.get(qm, qm)}"
                    + (f"／答{QUALITY_NOTE.get(am, am)}" if ans_rel else "")
                    + "；未人工对照底本")
        # ── 保住人工写的东西 ────────────────────────────────────────────────
        # 本行是**整行重建**的，早先连 `topic` 和 `notes` 一起覆盖。于是：
        #   ① 有人按勘误在 notes 里写了「M4 只落实一半」「M8 未落实」，重跑一次就没了；
        #   ② 工具因此**不幂等**：第一遍写的是通用文案，第二遍比对的是被人工改过的行，
        #      每次重跑都改 1 行，`changed` 计数永远不为 0，也就永远看不出「没变化」。
        # 判据取「是不是工具自己那两句」——是就照旧重写（方法变了要跟着更新），
        # 不是就原样留着。这样既幂等，又不会把人工备注吃掉。
        cur = RE_QNOTES.search(m.group(3) or "")
        if cur and cur.group(1).strip() and not RE_GENERIC_NOTE.match(cur.group(1).strip()):
            note = cur.group(1)
        cur_t = RE_QTOPIC.search(m.group(3) or "")
        topic = "未知"
        if cur_t and cur_t.group(1).strip() and cur_t.group(1).strip() != "未知":
            topic = cur_t.group(1).strip()
        notes_field = 'notes: "' + note.replace('"', "'") + '"'
        new = (f'  - {{"no": {no}, status: {status}, confidence: {confidence}, '
               f'topic: {topic}, {notes_field}}}'
               + ("\n" if line.endswith("\n") else ""))
        tally[status] = tally.get(status, 0) + 1
        if new != line:
            changed += 1
            lines[i] = new

    # extraction 块也照实填
    text = "".join(lines)
    method = ("text-layer" if methods_seen == {"text-layer"}
              else "manual" if methods_seen == {"manual"}
              else "ocr" if methods_seen == {"ocr-unverified"}
              else "mixed")
    text = re.sub(r"(^\s*method:\s*)\S+", lambda m: m.group(1) + method,
                  text, count=1, flags=re.M)
    text = re.sub(r'(^\s*tool:\s*)\S.*$', lambda m: m.group(1) + f'"{TOOL}"',
                  text, count=1, flags=re.M)
    text = re.sub(r"(^\s*date:\s*)\S+", lambda m: m.group(1) + (args.date or DATE),
                  text, count=1, flags=re.M)

    print(f"[meta] {paper_id}: 状态分布 {tally}；extraction.method={method}；"
          f"改动 {changed} 行")
    if "proofread" in tally:
        raise SystemExit("[meta] 内部错误：本工具不该写出 proofread，请检查")
    if not args.write:
        print("[meta] 未加 --write，未落盘")
        return 0
    meta.write_text(text, encoding="utf-8", newline="\n")
    print(f"[meta] 写出 {meta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
