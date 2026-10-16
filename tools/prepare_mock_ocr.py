#!/usr/bin/env python3
"""纯扫描模拟卷：页级 OCR 文本重建 + 图像核验题界修补。

问题：mock-2027 set-2/3/4 是纯扫描件，RapidOCR 会漏检部分**加粗题号**
（正文在、题号不在）。直接按 OCR 文本分段会少题、甚至把子问当成大题。

做法：
  1. 对每页做 scale 2/3/4 多倍率识别，把检测框按 (y, x) 归并成行文本；
  2. 读取 `index/image-verified-numbers.json`，对每个**已由源页图确认**的
     缺失题号，用其 anchor（题干首句）在重建文本中定位，在该行前插入 `NN. `；
  3. 输出到 `build/_scratch/mockocr/<paper>/page-XXX.txt`（**不覆盖**原缓存）。

硬约束：
  - 只有当 anchor 能在重建文本中**唯一追溯**时才插入题号；否则记为 unresolved。
  - **绝不**凭空补一个空标题行；**绝不**按序号顺序推断。
  - 本脚本只重建题界与文字，不产生答案。

用法：
    tools/prepare_mock_ocr.py --paper mock-2027/set-2
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "_scratch" / "mockocr"
VERIFIED = ROOT / "index" / "image-verified-numbers.json"

ROW_TOL = 12.0          # 同一行的 y 容差（scale=3 像素）


def _rows(boxes) -> list[str]:
    """把检测框按 y 归并成行，行内按 x 排序，返回行文本。"""
    items = []
    for box, text in boxes:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        items.append((min(ys), min(xs), str(text).strip()))
    items.sort(key=lambda r: (r[0], r[1]))
    lines: list[list] = []
    for y, x, t in items:
        if lines and y - lines[-1][0] <= ROW_TOL:
            lines[-1][1].append((x, t))
        else:
            lines.append([y, [(x, t)]])
    return ["  ".join(t for _, t in sorted(seg)) for _, seg in lines]


def ocr_page(doc, pno: int, scales=(2, 3, 4)) -> list[str]:
    """pno 为 0 起页索引；用 pypdfium2 渲染。"""
    from rapidocr_onnxruntime import RapidOCR
    eng = RapidOCR()
    best: list[str] = []
    for s in scales:
        img = doc[pno].render(scale=s).to_pil()
        tmp = OUT / "_page.png"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        img.save(tmp)
        res, _ = eng(str(tmp))
        rows = _rows([(i[0], i[1]) for i in (res or [])])
        if len("".join(rows)) > len("".join(best)):
            best = rows
    return best


NUM_SEP = re.compile(r"^(\s*)(\d{1,2})\s*[.．、。，,;；:：]\s*")
LEAD_OK = re.compile(r"^\s*\d{1,2}\s*[.．、。，,;；:：]")


def normalize_numbers(rows: list[str]) -> list[str]:
    """把 OCR 误用的题号分隔符（, 。 ， ; 等）统一为 `.`，便于下游按题号分段。

    只改**行首题号后的分隔符**，不动正文里的标点。
    """
    out = []
    for ln in rows:
        m = NUM_SEP.match(ln)
        if m and 1 <= int(m.group(2)) <= 47:
            ln = f"{int(m.group(2)):02d}. " + ln[m.end():].lstrip()
        out.append(ln)
    return out


def apply_numbers(rows: list[str], spec: dict) -> tuple[list[str], list[str]]:
    """在 anchor 行前插入已核验的题号。返回 (新行, 未解决列表)。"""
    out, unresolved = list(rows), []
    for no, rec in sorted(spec.items(), key=lambda kv: int(kv[0])):
        if not str(no).isdigit():
            continue
        anchor = rec["anchor"]
        hits = [i for i, ln in enumerate(out) if anchor in ln]
        if len(hits) != 1:
            unresolved.append(f"Q{no}: anchor 命中 {len(hits)} 次（需唯一）")
            continue
        i = hits[0]
        if LEAD_OK.match(out[i]):
            continue                      # 该行已有题号，无需插入
        out[i] = f"{int(no):02d}. " + out[i].lstrip()
    return out, unresolved


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paper", required=True, help="如 mock-2027/set-2")
    ap.add_argument("--scales", default="2,3,4")
    ap.add_argument("--pages", help="仅处理这些页（逗号分隔，1 起）")
    args = ap.parse_args(argv)

    import pypdfium2 as pdfium
    import yaml
    meta = yaml.safe_load((ROOT / "papers" / args.paper / "meta.yml").read_text(encoding="utf-8"))
    src = next(s for s in meta["sources"] if s["role"] == "paper")["path"]
    pdf = ROOT / src

    spec_all = {}
    if VERIFIED.is_file():
        spec_all = json.loads(VERIFIED.read_text(encoding="utf-8")).get(args.paper, {})
    spec = {k: v for k, v in spec_all.items() if k.isdigit()}

    stem = Path(src).stem
    outdir = OUT / stem
    (OUT / "by-paper" / args.paper.replace("/", "__")).mkdir(parents=True, exist_ok=True)
    outdir.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(pdf))
    scales = tuple(int(x) for x in args.scales.split(","))
    report = {"paper": args.paper, "pages": {}, "unresolved": []}
    try:
        want = ([int(x) for x in args.pages.split(",")] if args.pages
                else list(range(1, len(doc) + 1)))
        for pno in want:
            rows = normalize_numbers(ocr_page(doc, pno - 1, scales))
            page_spec = {k: v for k, v in spec.items()
                         if int(v.get("page", 0)) == pno}
            rows, unres = apply_numbers(rows, page_spec)
            report["unresolved"] += unres
            (outdir / f"page-{pno:03d}.txt").write_text("\n".join(rows) + "\n",
                                                        encoding="utf-8")
            report["pages"][str(pno)] = {"lines": len(rows), "patched": len(page_spec) - len(unres)}
            print(f"  p{pno}: {len(rows)} 行, 插入题号 {len(page_spec) - len(unres)}/{len(page_spec)}")
    finally:
        doc.close()
    for u in report["unresolved"]:
        print(f"  [unresolved] {u}")
    (outdir / "_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    print(f"[prepare] → {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
