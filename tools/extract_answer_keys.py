#!/usr/bin/env python3
"""按**几何坐标**抽取选择题答案 key（针对「页码表」版式）。

背景：2009–2021 的答案底本把答案排成多列网格（如 2009 每行 8 组：
`1. B   2. C   …   8. D`）。纯文本抽取会把字母串与题号分离，
导致 432 条 `no-answer`。本脚本改用 `page.get_text("dict")` 的
span 包围盒，按**同一行 + 题号右侧最近的字母**配对，不靠字符顺序推测。

判定原则：只有 1..40 全部唯一配对成功才输出；否则报 insufficient 并保持 blocked。

用法：
    tools/extract_answer_keys.py --year 2009
    tools/extract_answer_keys.py --years 2009,2010 --json build/_scratch/answer-keys.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NUM_SPAN = re.compile(r"^\s*(\d{1,2})\s*[.．、]\s*$")
LET_SPAN = re.compile(r"^\s*([ABCD])\s*$")
PAIR_SPAN = re.compile(r"^\s*(\d{1,2})\s*[.．、]\s*([ABCD])\s*$")


def spans_of_page(pdf: Path, page_no: int):
    import pymupdf
    doc = pymupdf.open(str(pdf))
    try:
        pg = doc[page_no - 1]
        out = []
        for blk in pg.get_text("dict")["blocks"]:
            if blk.get("type") != 0:
                continue
            for ln in blk["lines"]:
                for sp in ln["spans"]:
                    t = sp["text"]
                    if t.strip():
                        out.append((sp["bbox"], t))
        return out, pg.rect
    finally:
        doc.close()


def extract(pdf: Path, page_no: int = 1) -> tuple[dict[int, str], str]:
    """返回 ({no: letter}, 状态说明)。"""
    spans, _ = spans_of_page(pdf, page_no)
    if not spans:
        return {}, "no-spans"

    pairs: list[tuple[float, float, int, str]] = []   # (y, x, no, letter)
    singles: list[tuple[float, float, str]] = []      # (y, x, 'A'..'D')

    for (x0, y0, x1, y1), t in spans:
        yc, xc = (y0 + y1) / 2, x0
        m = PAIR_SPAN.match(t)
        if m:
            pairs.append((yc, xc, int(m.group(1)), m.group(2)))
            continue
        m = NUM_SPAN.match(t)
        if m and 1 <= int(m.group(1)) <= 40:
            pairs.append((yc, xc, int(m.group(1)), ""))
            continue
        m = LET_SPAN.match(t)
        if m:
            singles.append((yc, xc, m.group(1)))

    if not pairs:
        return {}, "no-number-spans"

    # 行容差：用题号 span 高度的量级（约 13pt），取半高
    TOL = 7.0
    key: dict[int, str] = {}
    used: set[int] = set()
    for yc, xc, no, letter in pairs:
        if letter:
            key.setdefault(no, letter)
            continue
        # 同行、位于题号右侧、最近的字母
        best = None
        for i, (sy, sx, sl) in enumerate(singles):
            if i in used or abs(sy - yc) > TOL or sx < xc:
                continue
            if best is None or sx < best[1]:
                best = (i, sx, sl)
        if best:
            used.add(best[0])
            key.setdefault(no, best[2])

    status = "ok" if set(key) == set(range(1, 41)) else f"insufficient({len(key)}/40)"
    return key, status


# ---------------------------------------------------------------- 版式B：列主序字母 run
COL_TOL = 12.0


def _cluster(xs: list[float], tol: float = COL_TOL) -> list[float]:
    out: list[list[float]] = []
    for x in sorted(xs):
        if out and x - out[-1][-1] <= tol:
            out[-1].append(x)
        else:
            out.append([x])
    return [sum(g) / len(g) for g in out]


def extract_columnar(pdf: Path, page_no: int = 1) -> tuple[dict[int, str], str]:
    """版式B：题号各自成 span 排成若干列，字母按列合并成 run（列主序）。

    硬校验：每个 run 的长度必须等于其所在列的题号个数；否则拒绝（返回 insufficient）。
    """
    import pymupdf
    doc = pymupdf.open(str(pdf))
    try:
        pg = doc[page_no - 1]
        items = []
        for blk in pg.get_text("dict")["blocks"]:
            if blk.get("type") != 0:
                continue
            for ln in blk["lines"]:
                for sp in ln["spans"]:
                    t = sp["text"].strip()
                    if t:
                        items.append((sp["bbox"][0], sp["bbox"][1], sp["bbox"][3], t))
    finally:
        doc.close()

    nums = [(x, y0, y1, t) for x, y0, y1, t in items
            if re.fullmatch(r"\d{1,2}\.", t) and 1 <= int(t[:-1]) <= 40]
    runs = [(x, y0, t) for x, y0, y1, t in items if re.fullmatch(r"[ABCD]{2,}", t)]
    lones = [(x, y0, t) for x, y0, y1, t in items if re.fullmatch(r"[ABCD]", t)]
    if not nums or not runs:
        return {}, "no-columnar-layout"

    # 只保留「答案表」题号：右侧 15..40pt 内有字母（或字母 run）与之同行。
    # 这样可以排除 "1. 解析：" 这类正文编号。
    letterish = [(x, y0, t) for x, y0, t in
                 [(x, y0, t) for x, y0, t in lones] + [(x, y0, t) for x, y0, t in runs]]
    table_nums = []
    for x, y0, y1, t in nums:
        yc = (y0 + y1) / 2
        if any(abs(yy - yc) <= 20 and 12 <= (lx - x) <= 45
               for lx, yy, _ in letterish):
            table_nums.append((x, y0, y1, t))
    nums = table_nums
    if not nums:
        return {}, "no-table-numbers"
    colx = _cluster([x for x, _, _, _ in nums])
    # 每列题号，按 y 升序
    cols: list[list[str]] = [[] for _ in colx]
    for x, y0, y1, t in sorted(nums, key=lambda r: (r[1], r[0])):
        i = min(range(len(colx)), key=lambda k: abs(colx[k] - x))
        cols[i].append(t[:-1])

    warn = []
    # 列 1（最左）通常是独立字母
    key: dict[int, str] = {}
    start = 0
    first_lone = [t for x, y, t in sorted(lones, key=lambda r: (r[1], r[0]))
                  if abs(x - (colx[0] + 25)) <= 14]
    if len(first_lone) == len(cols[0]):
        for no, ch in zip(cols[0], first_lone):
            key[int(no)] = ch
        start = 1
    else:
        warn.append(f"列1独立字母数 {len(first_lone)} != 题号数 {len(cols[0])}")

    runs_sorted = sorted(runs, key=lambda r: r[0])
    targets = cols[start:]
    if len(runs_sorted) != len(targets):
        return key, f"run数 {len(runs_sorted)} != 待填列数 {len(targets)}"
    for run, col in zip(runs_sorted, targets):
        if len(run[2]) != len(col):
            return key, f"run长度 {len(run[2])} != 列题号数 {len(col)} @x={run[0]:.0f}"
        for no, ch in zip(col, run[2]):
            key[int(no)] = ch

    ok = set(key) == set(range(1, 41))
    if not ok:
        return key, f"insufficient({len(key)}/40)"
    return key, "ok" + ("; " + "; ".join(warn) if warn else "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int)
    ap.add_argument("--years", help="逗号分隔")
    ap.add_argument("--json", default="build/_scratch/answer-keys.json")
    args = ap.parse_args(argv)
    years = ([args.year] if args.year else
             [int(x) for x in args.years.split(",")] if args.years else list(range(2009, 2027)))

    report, agg = {}, {}
    for y in years:
        pdf = ROOT / f"sources/exams/answers/{y}-answer.pdf"
        if not pdf.is_file():
            print(f"{y}: 缺文件"); continue
        key, status = extract(pdf)
        if status != "ok":
            key2, status2 = extract_columnar(pdf)
            if status2.startswith("ok"):
                key, status = key2, status2
            else:
                status = f"{status} | columnar:{status2}"
        report[y] = {"status": status, "count": len(key), "key": key}
        if status == "ok":
            agg[y] = key
        print(f"{y}: {status}  {' '.join(f'{n}{key[n]}' for n in sorted(key)[:12])}…"
              if key else f"{y}: {status}")
    Path(ROOT / args.json).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / args.json).write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
    print(f"[keys] 完整 {sum(1 for v in report.values() if v['status']=='ok')}/{len(report)} 卷"
          f" → {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
