#!/usr/bin/env python3
"""CPU-only 渲染 + RapidOCR 单页试点（草稿性质，不是正式转录）。

用途：把**扫描件** PDF 的某一页渲染成位图后做 OCR，量一下延迟/内存/置信度。
本脚本只产出 **草稿**，必须人工校对；不得直接写入 papers/ 或当作已校对结果。

依赖（隔离 venv 内）：pypdfium2(渲染) + rapidocr-onnxruntime(识别，模型随包离线)。
全程 CPU、单进程；调用方应加持 nice/OMP_NUM_THREADS=1。

用法：
    tools/ocr_cpu_pilot.py <in.pdf> -p 1 --scale 2 -o build/_scratch/ocr/page1.txt
"""
from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path


def render_png(pdf_path: Path, page_no: int, scale: float, png_out: Path) -> tuple[int, int]:
    """把第 page_no 页（1-based）渲染为 PNG。返回像素尺寸。"""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        page = doc[page_no - 1]
        img = page.render(scale=scale).to_pil()
        png_out.parent.mkdir(parents=True, exist_ok=True)
        img.save(png_out)
        return img.size
    finally:
        doc.close()


def ocr_png(png_path: Path) -> tuple[list[tuple[str, float]], float]:
    """对 PNG 做 OCR。返回 ([(text, score)], 引擎自报耗时秒)。"""
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR()
    t0 = time.perf_counter()
    result, elapse = engine(str(png_path))
    wall = time.perf_counter() - t0
    lines: list[tuple[str, float]] = []
    for item in result or []:
        # rapidocr 每项形如 [box, text, score]
        text, score = item[1], float(item[2])
        lines.append((text, score))
    return lines, wall


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf", type=Path, help="输入 PDF（只读，不会被修改）")
    ap.add_argument("-p", "--page", type=int, default=1, help="页码，1-based")
    ap.add_argument("--scale", type=float, default=2.0, help="渲染倍率（2 ≈ 144dpi）")
    ap.add_argument("-o", "--out", type=Path, required=True, help="OCR 文本输出路径")
    ap.add_argument("--scratch", type=Path, default=None, help="PNG 落地目录（默认与 -o 同目录）")
    args = ap.parse_args(argv)

    if not args.pdf.is_file():
        print(f"找不到 PDF: {args.pdf}", file=sys.stderr)
        return 2

    png = (args.scratch or args.out.parent) / f"{args.pdf.stem}-p{args.page}.png"

    t_render = time.perf_counter()
    size = render_png(args.pdf, args.page, args.scale, png)
    render_s = time.perf_counter() - t_render

    lines, ocr_s = ocr_png(png)
    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(t for t, _ in lines) + "\n", encoding="utf-8")

    chars = sum(len(t) for t, _ in lines)
    scores = [s for _, s in lines]
    stats = {
        "pdf": str(args.pdf),
        "page": args.page,
        "render_scale": args.scale,
        "png": str(png),
        "png_size_px": list(size),
        "render_seconds": round(render_s, 3),
        "ocr_seconds": round(ocr_s, 3),
        "peak_rss_mb": round(rss_mb, 1),
        "lines": len(lines),
        "chars": chars,
        "mean_score": round(sum(scores) / len(scores), 4) if scores else None,
        "min_score": round(min(scores), 4) if scores else None,
        "low_conf_lines": sum(1 for s in scores if s < 0.6),
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))

    warn = sorted([(s, t) for t, s in lines])[:5]
    if warn:
        print("\n-- 低置信样本（草稿，需人工校对）--")
        for s, t in warn:
            print(f"  {s:.3f}  {t[:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
