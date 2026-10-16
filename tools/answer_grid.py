#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""answer_grid.py —— 用**坐标**读答案卷卷首那张 8 列 × 5 行的答案表。

为什么非要有这个工具
--------------------
`tools/md_solutions.py` 走的是逐题「解析」正文（`1.【参考答案】D` / `01. B。【解析】` …）。
2009—2018 这批答案卷的解析正文里**根本不写答案字母**（只有「故选 B。」这种时有时无的句子），
答案只印在卷首那张表里。而纯文本层的读法把那张表读成一锅粥：

    2018：'BCCBBCDBACAAACDADDDDACBDDCACACDACDBBBDCD 1.  2.  …  5  n  江  泗  扛'
            ↑ 8 段各 5 个字母被拼成一条长串，第 5 列的题号 13/21/29/37 被 OCR 成 5/n/江/泗

有了坐标就不是猜：
  · 表是 8 列 × 5 行，**列优先**：第 c 列自上而下是第 c、c+8、c+16、c+24、c+32 题；
  · 于是**连题号都不用认**（那些被 OCR 认坏的 5/n/江/泗 就不构成障碍），
    只要把 40 个 A–D 字母按 x 聚成 8 列、列内按 y 排序即可。
硬门槛：必须**恰好** 8 列、每列**恰好** 5 个字母，否则一律不输出（不猜、不补）。

用法
----
    python -I tools/answer_grid.py --paper exams/2018 [--write]
    python -I tools/answer_grid.py --all
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
OUT_ROOT = REPO / "build" / "_scratch" / "answer-grid"

COLS, ROWS = 8, 5
COL_GAP = 15.0          # x0 相差超过这个值就算新的一列
# 网格里的一行可能长成：`BBCBA`、`B`（第 1 列的字母被单独切出来）、
# `CBAAB 4.`（字母段和题号被并成一行，2009 就是这样）。行里**不能有别的东西**，
# 否则不许从里面抠字母——正文里的「A 的操作顺序」不能被当成一行答案。
RE_GRID_LINE = re.compile(r"^(?:\d{1,3}\s*[.．、]?\s*)?([A-D]{1,8})"
                          r"(?:\s*\d{1,3}\s*[.．、]?)?$")
# 卷首答案表之后紧跟的就是逐题解析；用它当「表格带」的下边界。
RE_FLOW_START = re.compile(r"^\d{1,2}\s*[.．、]\s*(?:【\s*(?:解析|参考答案|答案要点|解答|答案)\s*】"
                           r"|(?:解析|参考答案|答案要点|解答|答案))")


def lines_of(page) -> list[tuple[float, float, float, str]]:
    """→ [(y0, x0, x1, text)]，按阅读无关的原始顺序。"""
    out = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            text = "".join(s["text"] for s in line["spans"]).strip()
            if text:
                out.append((line["bbox"][1], line["bbox"][0], line["bbox"][2], text))
    return out


def grid_of_page(page) -> tuple[dict[int, tuple[str, tuple]], list[str]]:
    """→ ({题号: (字母, bbox)}, 说明列表)。读不出整张表就返回空 dict。"""
    notes: list[str] = []
    rows = lines_of(page)
    # 答案表必须在逐题解析**之前**：找第一行形如「1. 解析：」的 y。
    # 没有这行（新版答案卷改用「数据链路层」之类章标题、或整页就是扫描图）时
    # 退化为「整页找」，但那时**必须**仍然凑出严格的 8 列 × 5 字母才认。
    flow_y = min((y for y, _x0, _x1, t in rows if RE_FLOW_START.match(t)), default=None)

    letters: list[tuple[float, float, str]] = []
    for y, x0, _x1, text in rows:
        if flow_y is not None and y >= flow_y:
            continue
        m = RE_GRID_LINE.match(text)
        if not m:
            continue
        # 一行可能是 `BBCBA` 这样的**一段**（同列 5 个字母被抽成一行），
        # 也可能只是单个字母（第 1 列的字母贴在题号右侧，被单独切出来）。
        # 两种都拆成「一个字母一条」，同一段里按原顺序、共用同一个 y——
        # 列内按 y 排序时 Python 的稳定排序会保住段内次序。
        for ch in m.group(1):
            letters.append((y, x0, ch))

    if not letters:
        return {}, ["本页上边界之内没有纯 A–D 的行"]

    # 按 x 聚列
    letters.sort(key=lambda t: (t[1], t[0]))
    cols: list[list[tuple[float, float, str]]] = []
    for item in letters:
        if cols and item[1] - cols[-1][-1][1] <= COL_GAP:
            cols[-1].append(item)
        else:
            cols.append([item])

    if len(cols) != COLS:
        return {}, [f"按 x 聚出 {len(cols)} 列（应为 {COLS} 列），拒收："
                    + "、".join(f"{c[0][1]:.0f}pt:{''.join(t[2] for t in c)}" for c in cols)]

    answers: dict[int, tuple[str, tuple]] = {}
    for ci, col in enumerate(cols, start=1):
        col.sort(key=lambda t: t[0])
        seq = "".join(t[2] for t in col)
        if len(seq) != ROWS:
            return {}, [f"第 {ci} 列（x≈{col[0][1]:.0f}pt）有 {len(seq)} 个字母（应为 {ROWS} 个）："
                        f"{seq!r}，拒收"]
        for ri, ch in enumerate(seq):
            no = ri * COLS + ci
            answers[no] = (ch, (round(col[ri][1], 1), round(col[ri][0], 1)))
    return answers, notes


def probe(pdf: Path, max_pages: int = 4) -> tuple[dict[int, str], list[str], int]:
    """→ ({题号: 字母}, 说明, 命中页码)。读不出整表时页码是 0。"""
    import pymupdf
    notes: list[str] = []
    with pymupdf.open(str(pdf)) as doc:
        for pno in range(min(max_pages, doc.page_count)):
            got, why = grid_of_page(doc[pno])
            if got:
                return {no: ch for no, (ch, _b) in got.items()}, notes, pno + 1
            notes.append(f"第 {pno + 1} 页：" + "；".join(why))
    return {}, notes, 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paper")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)

    if args.all:
        pdfs = sorted((REPO / "sources" / "exams" / "answers").glob("*-answer.pdf"))
    elif args.paper:
        y = args.paper.split("/", 1)[1]
        pdfs = [REPO / "sources" / "exams" / "answers" / f"{y}-answer.pdf"]
    else:
        raise SystemExit("需要 --paper exams/YYYY 或 --all")

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    bad = 0
    for pdf in pdfs:
        if not pdf.is_file():
            print(f"[grid] 缺底本：{pdf}")
            bad += 1
            continue
        got, notes, page = probe(pdf)
        seq = "".join(got.get(i, "?") for i in range(1, 41))
        ok = len(got) == 40
        tag = "✅" if ok else "⛔"
        print(f"{tag} {pdf.name}  {seq}")
        for n in notes:
            print(f"    · {n}")
        if not ok:
            bad += 1
            continue
        if args.write:
            dst = OUT_ROOT / f"{pdf.stem}.json"
            dst.write_text(json.dumps({"paper": pdf.stem, "source": "text-layer",
                                       "page": page, "answers": got},
                                      ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"    → {dst}")
    print(f"[grid] {len(pdfs)} 卷，读不出整表 {bad} 卷")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
