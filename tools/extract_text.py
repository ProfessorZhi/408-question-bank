#!/usr/bin/env python3
"""PDF 文本层提取（OCR 仅作回退）。

先试文本层：本任务实测 2027 模拟卷 PDF 带真实文本层（卷1 试题 10,145 字符），
所以主路径是直接抽文字，**不需要** OCR。

文本层为空或明显残缺时才走 OCR（本机有 rapidocr-onnxruntime，离线可用）。

约定：输出只写到 build/_scratch/ 或显式 -o 指定处，**不直接写 papers/**。
转录是人的判断，不是脚本的输出。

用法：
  python tools/extract_text.py sources/mock-2027/pdf/mock2027-set1-paper.pdf
  python tools/extract_text.py <pdf> -o build/_scratch/set1-paper.txt --per-page
  python tools/extract_text.py <pdf> --ocr --dpi 200 -o build/_scratch/x.txt
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # Windows 控制台默认 GBK
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parent.parent


def load_pdf(path: Path):
    try:
        import pymupdf
        return pymupdf
    except Exception:
        try:
            import fitz as pymupdf  # noqa: PLC0415
            return pymupdf
        except Exception as exc:
            raise SystemExit(f"[extract] 需要 pymupdf：{exc}") from exc


def extract_text_layer(pdf, path: Path, per_page: bool) -> str:
    doc = pdf.open(str(path))
    try:
        if per_page:
            parts = []
            for i, page in enumerate(doc, 1):
                parts.append(f"\n===== page {i} =====\n{page.get_text()}")
            return "".join(parts)
        return "".join(page.get_text() for page in doc)
    finally:
        doc.close()


def extract_ocr(pdf, path: Path, dpi: int, langs: str) -> str:
    try:
        import numpy as np  # noqa: PLC0415
        from rapidocr_onnxruntime import RapidOCR  # noqa: PLC0415
    except Exception as exc:
        raise SystemExit(f"[extract] OCR 回退不可用：{exc}") from exc
    engine = RapidOCR()
    doc = pdf.open(str(path))
    parts = []
    try:
        for i, page in enumerate(doc, 1):
            pix = page.get_pixmap(dpi=dpi)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n)
            result, _ = engine(img)
            parts.append(f"\n===== page {i} (OCR) =====\n"
                         + "\n".join(line[1] for line in (result or [])))
    finally:
        doc.close()
    return "".join(parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("-o", "--out")
    ap.add_argument("--per-page", action="store_true", help="按页加分隔标记")
    ap.add_argument("--ocr", action="store_true", help="强制 OCR（跳过文本层）")
    ap.add_argument("--dpi", type=int, default=200, help="OCR 渲染 DPI，默认 200")
    args = ap.parse_args(argv)

    pdf = load_pdf(Path(args.pdf))
    src = Path(args.pdf)
    if not src.is_file():
        raise SystemExit(f"[extract] 文件不存在：{src}")

    if args.ocr:
        text, how = extract_ocr(pdf, src, args.dpi, "ch"), "ocr"
    else:
        text = extract_text_layer(pdf, src, args.per_page)
        how = "text-layer"
        if len(text.strip()) < 200:
            print("[extract] ⚠️ 文本层近乎为空 —— 该 PDF 可能是扫描件，"
                  "加 --ocr 重跑。本次输出保留为空，不自动切换。", file=sys.stderr)

    out = Path(args.out) if args.out else (REPO / "build" / "_scratch"
                                           / (src.stem + f".{how}.txt"))
    if not out.is_absolute():
        out = REPO / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"[extract] {how}: {len(text):,} 字符 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
