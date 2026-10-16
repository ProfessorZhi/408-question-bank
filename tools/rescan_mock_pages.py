#!/usr/bin/env python3
"""纯扫描模拟卷：多倍率 OCR 并集，最大化题号检出率（只读源 PDF）。

背景：mock-2027 set-2/3/4 为纯扫描件，单次 RapidOCR 会漏检部分加粗题号
（实测 set-2 由 40/47 提升到 45/47）。本脚本对同一页做 scale 2/3/4 三档识别，
取并集，输出每题号**实际被识别到**的页码与行首文本作为证据。

⚠️ 本脚本**只做检测与取证，不生成题目**。任何题号只有在输出里
`seen=True` 时才可用；缺失的题号必须由源页图人工确认后另行登记，
**不得按序号顺序推断补足**（见 docs/qa-policy.md、docs/transcription-status-dell.md）。

用法：
    tools/rescan_mock_pages.py --set 2
    tools/rescan_mock_pages.py --sets 2,3,4 --json build/_scratch/mockscan/hits.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NUM_LINE = re.compile(r"^\s*(\d{1,2})\s*[.．、]\s*(\S.*)$")


def scan(pdf: Path, scales=(2, 3, 4)) -> dict:
    import pypdfium2 as pdfium
    from rapidocr_onnxruntime import RapidOCR

    eng = RapidOCR()
    doc = pdfium.PdfDocument(str(pdf))
    hits: dict[int, dict] = {}
    tmp = ROOT / "build" / "_scratch" / "_rescan.png"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    try:
        for scale in scales:
            for p in range(len(doc)):
                img = doc[p].render(scale=scale).to_pil()
                img.save(tmp)
                res, _ = eng(str(tmp))
                for item in res or []:
                    m = NUM_LINE.match(str(item[1]))
                    if not m:
                        continue
                    no = int(m.group(1))
                    if not 1 <= no <= 47:
                        continue
                    rec = hits.setdefault(no, {"pages": set(), "scales": set(), "head": ""})
                    rec["pages"].add(p + 1)
                    rec["scales"].add(scale)
                    if not rec["head"]:
                        rec["head"] = str(item[1])[:70]
    finally:
        doc.close()
    out = {str(k): {"pages": sorted(v["pages"]), "scales": sorted(v["scales"]),
                    "head": v["head"]} for k, v in hits.items()}
    out["_missing"] = [k for k in range(1, 48) if k not in hits]
    out["_coverage"] = f"{len(hits)}/47"
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", type=int)
    ap.add_argument("--sets", help="逗号分隔，如 2,3,4")
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    sets = [args.set] if args.set else (
        [int(x) for x in args.sets.split(",")] if args.sets else [2, 3, 4])

    allrep = {}
    for s in sets:
        pdf = ROOT / f"sources/mock-2027/pdf/mock2027-set{s}-paper.pdf"
        if not pdf.is_file():
            print(f"set{s}: 缺文件"); continue
        rep = scan(pdf)
        allrep[str(s)] = rep
        print(f"set{s}: {rep['_coverage']}  未检出题号 {rep['_missing']}")
        for no in rep["_missing"]:
            print(f"    Q{no}: 未被任何倍率识别 → 需源页图人工确认，不得按序号推断")
    if args.json:
        p = ROOT / args.json
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(allrep, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[rescan] → {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
