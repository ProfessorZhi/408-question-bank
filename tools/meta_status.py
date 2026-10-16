#!/usr/bin/env python3
"""按**实际转写来源**回填 meta.yml 的逐题状态。

纪律（比功能重要）
------------------
1. **本工具永远不会写出 `proofread`。** 逐题状态机见 docs/qa-policy.md，
   `proofread` 的含义是「有人拿底本逐字比过」。机器没有比过，就没有资格写。
   批量刷 `proofread` 制造绿灯，是 docs/qa-policy.md 点名的**造假**。
2. 状态只由**可复算的事实**决定：这道题的题目来自文字层还是 OCR、答案来自哪边。
   不做任何「看起来已经对了吧」的推断。
3. 只改 `questions:` 里那一行 `- {"no": N, ...}`，文件其余部分（注释、来源块、
   errata、review）**逐字节保持原样**——所以用外科式文本替换，不做 YAML 往返。

状态取值
--------
  needs-review   题目与答案都取自文字层，但**尚未人工对照底本**。
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

TOOL = "pymupdf 1.28.2 + rapidocr-onnxruntime 1.4.4"
DATE = "2026-10-16"

QUALITY_NOTE = {
    "text-layer": "文字层",
    "ocr-unverified": "OCR",
}


def page_methods(src_rel: str) -> dict[int, str]:
    folder = RAW / Path(src_rel).with_suffix("")
    out: dict[int, str] = {}
    for f in sorted(folder.glob("page-*.json")):
        info = json.loads(f.read_text(encoding="utf-8"))
        out[int(f.stem.split("-")[1])] = info["method"]
    return out


def question_span(paper_dir: Path) -> dict[int, tuple[int, int]]:
    """从 questions.md 的 `<!-- 底本第 N 页 -->` 反推每题占的页范围。"""
    qfile = paper_dir / "questions.md"
    spans: dict[int, tuple[int, int]] = {}
    if not qfile.is_file():
        return spans
    current = None
    for line in qfile.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^###\s*第\s*(\d{1,2})\s*题", line)
        if m:
            current = int(m.group(1))
            continue
        m = re.match(r"^<!--\s*底本第\s*(\d+)(?:—(\d+))?\s*页", line)
        if m and current is not None:
            lo = int(m.group(1))
            spans[current] = (lo, int(m.group(2)) if m.group(2) else lo)
    return spans


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
    args = ap.parse_args(argv)

    paper_id = args.paper
    paper_dir = REPO / "papers" / paper_id
    meta = paper_dir / "meta.yml"
    if not meta.is_file():
        raise SystemExit(f"[meta] 缺少 {meta}（先跑 tools/bootstrap_meta.py）")

    paper_rel, ans_rel = sources_for(paper_id)
    qpages = page_methods(paper_rel)
    apages = page_methods(ans_rel)
    spans = question_span(paper_dir)
    if not qpages:
        raise SystemExit(f"[meta] 缺少逐页草稿：{paper_rel}（先跑 tools/batch_extract.py）")

    def method_in(methods: dict[int, str], span: tuple[int, int]) -> str:
        kinds = {methods.get(p, "text-layer") for p in range(span[0], span[1] + 1)}
        if "ocr-unverified" in kinds:
            return "ocr-unverified"
        if "missing-text-needs-ocr" in kinds:
            return "missing-text-needs-ocr"
        return "text-layer"

    lines = meta.read_text(encoding="utf-8").splitlines(keepends=True)
    changed = 0
    tally: dict[str, int] = {}
    methods_seen: set[str] = set()

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
            qm = method_in(qpages, span)
            # 答案卷整本几乎总是同一种来源（扫描件或文字层），逐题页映射这里拿不到，
            # 就按整本判。判不准时**偏向保守**（标成 ocr-uncertain），
            # 漏标成「没问题」比多标一笔坏处大得多。
            am = "text-layer" if apages and all(
                v == "text-layer" for v in apages.values()) else "ocr-unverified"
            methods_seen.update({qm, am})
            if qm == "text-layer" and am == "text-layer":
                status, confidence = "needs-review", "medium"
            else:
                status, confidence = "ocr-uncertain", "low"
            note = (f"题{QUALITY_NOTE.get(qm, qm)}"
                    + (f"／答{QUALITY_NOTE.get(am, am)}" if ans_rel else "")
                    + "；未人工对照底本")
        notes_field = f'notes: "{note}"'
        new = (f'  - {{"no": {no}, status: {status}, confidence: {confidence}, '
               f'topic: 未知, {notes_field}}}'
               + ("\n" if line.endswith("\n") else ""))
        tally[status] = tally.get(status, 0) + 1
        if new != line:
            changed += 1
            lines[i] = new

    # extraction 块也照实填
    text = "".join(lines)
    method = ("text-layer" if methods_seen == {"text-layer"}
              else "ocr" if methods_seen == {"ocr-unverified"}
              else "mixed")
    text = re.sub(r"(^\s*method:\s*)\S+", lambda m: m.group(1) + method,
                  text, count=1, flags=re.M)
    text = re.sub(r'(^\s*tool:\s*)\S.*$', lambda m: m.group(1) + f'"{TOOL}"',
                  text, count=1, flags=re.M)
    text = re.sub(r"(^\s*date:\s*)\S+", lambda m: m.group(1) + DATE,
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
