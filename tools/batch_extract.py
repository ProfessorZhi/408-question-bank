#!/usr/bin/env python3
"""Low-token page-level PDF extraction for the private 408 question bank.

Run deterministic text extraction first, use offline OCR only on pages without
usable text, and CACHE every page. Output is unverified staging data, never a
complete questions.md/solutions.md. No language-model API calls are made.

Examples:
  python tools/batch_extract.py --scope mock --ocr off --limit-pages 30
  python tools/batch_extract.py --scope all --ocr auto --limit-pages 10
  python tools/batch_extract.py --scope all --ocr auto --limit-pages 0
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DEFAULT = Path(__file__).resolve().parent.parent

# `python -I` 不会把脚本目录放进 sys.path[0]，所以要显式加。
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ocr_runtime  # noqa: E402  （同目录，见该模块的 DLL 兼容说明）


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def setup_ocr():
    """Lazy import: there is no OCR model load for text PDFs.

    顺序不能颠倒：`rapidocr_onnxruntime` 一导入就会拉 `onnxruntime`，
    而本机 onnxruntime 的原生 DLL 需要先经 `ocr_runtime.ensure()` 处理，
    否则抛的是 "DLL load failed"，会被误读成「rapidocr 没装」。
    """
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("缺少 numpy，离线OCR不可用；只能用 --ocr off") from exc

    ocr_runtime.ensure()   # 失败时自带「缺哪个 DLL / 代际差多少」的说明

    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise RuntimeError(
            "rapidocr-onnxruntime 未安装：仅可使用 --ocr off，"
            "或者 pip install rapidocr-onnxruntime"
        ) from exc
    return np, RapidOCR()


def ocr_page(page, np, engine, dpi: int) -> tuple[str, float | None]:
    image = page.get_pixmap(dpi=dpi, alpha=False, colorspace="rgb")
    data = np.frombuffer(image.samples, dtype=np.uint8).reshape(
        image.height, image.width, image.n
    )
    result, _ = engine(data)
    result = result or []
    texts = [str(item[1]) for item in result if len(item) >= 2]
    scores = [float(item[2]) for item in result if len(item) >= 3]
    return "\n".join(texts), sum(scores) / len(scores) if scores else None


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    cli.add_argument("--scope", choices=["all", "exam", "mock"], default="all")
    cli.add_argument("--ocr", choices=["off", "auto"], default="off")
    cli.add_argument("--dpi", type=int, default=180)
    cli.add_argument("--min-chars", type=int, default=60)
    cli.add_argument("--limit-pages", type=int, default=12,
                     help="本次最多处理多少未缓存页；0=无限。默认12以控制CPU占用")
    args = cli.parse_args(argv)
    if args.dpi < 90 or args.dpi > 300:
        cli.error("--dpi 必须在90至300之间")
    if args.min_chars < 0 or args.limit_pages < 0:
        cli.error("字符阈值/页数限额不得为负")
    root = args.root.resolve()
    manifest_file = root / "index" / "sources-manifest.json"
    if not manifest_file.is_file():
        cli.error("缺少 index/sources-manifest.json，先执行 tools/inventory.py")
    files = json.loads(manifest_file.read_text(encoding="utf-8"))["files"]
    chosen = [r for r in files if r.get("ext") == ".pdf" and (
        args.scope == "all" or
        (args.scope == "exam" and r["path"].startswith("sources/exams/")) or
        (args.scope == "mock" and r["path"].startswith("sources/mock-2027/"))
    )]
    # ⚠️ 顺序要害：必须**先**把 OCR 运行时就位，**再** import pymupdf。
    # 反过来的话，pymupdf 会先把 System32 里 VS2015 那份 msvcp140.dll 钉进进程，
    # 之后 onnxruntime（VS2022 构建）撞上它直接段错误（exit 139、零输出）。
    # 详见 tools/ocr_runtime.py 顶部说明。
    if args.ocr == "auto":
        ocr_runtime.ensure()

    import pymupdf
    np = engine = None
    processed = cached = n_ocr = n_text = n_unreadable = 0
    root_out = root / "build" / "_scratch" / "408-raw-pages"
    for rec in chosen:
        rel = Path(rec["path"])
        src = (root / rel).resolve()
        if not src.is_relative_to(root / "sources") or not src.is_file():
            print(f"[skip] 来源不在授权目录内/不存在: {rel}", file=sys.stderr)
            continue
        sha = digest(src)
        if sha != rec["sha256"]:
            raise SystemExit(f"[stop] 来源sha256异常: {rel}（请勿改写底本）")
        out = root_out / rel.with_suffix("")
        out.mkdir(parents=True, exist_ok=True)
        with pymupdf.open(str(src)) as doc:
            for page_no, page in enumerate(doc, start=1):
                textfile = out / f"page-{page_no:03d}.txt"
                metafile = out / f"page-{page_no:03d}.json"
                settings = {"source_sha256": sha, "page": page_no,
                            "ocr_mode": args.ocr, "dpi": args.dpi,
                            "min_chars": args.min_chars}
                if metafile.exists() and textfile.exists():
                    try:
                        previous = json.loads(metafile.read_text(encoding="utf-8"))
                        if all(previous.get(k) == v for k, v in settings.items()):
                            cached += 1
                            continue
                    except (ValueError, OSError):
                        pass
                if args.limit_pages and processed >= args.limit_pages:
                    print(f"[limit] 本次处理 {processed} 页，剩余下次可断点续跑")
                    print(f"[summary] 新处理 {processed}，缓存命中 {cached}；"
                          f"文字层 {n_text}，OCR {n_ocr}，未读文字 {n_unreadable}")
                    return 0
                extracted = page.get_text("text", sort=True).strip()
                method, confidence = "text-layer", None
                if len(extracted) < args.min_chars:
                    if args.ocr == "auto":
                        if engine is None:
                            np, engine = setup_ocr()
                        extracted, confidence = ocr_page(page, np, engine, args.dpi)
                        method = "ocr-unverified"
                        n_ocr += 1
                    else:
                        method = "missing-text-needs-ocr"
                        n_unreadable += 1
                else:
                    n_text += 1
                # Drafts remain isolated from student questions and teacher answers.
                textfile.write_text(extracted + "\n", encoding="utf-8", newline="\n")
                info = {**settings, "source_path": rel.as_posix(),
                        "source_page": page_no, "method": method,
                        "status": "unverified", "characters": len(extracted),
                        "confidence_mean": confidence,
                        "contains_images": bool(page.get_images(full=True)),
                        "processed_at": datetime.now(timezone.utc).isoformat()}
                metafile.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8", newline="\n")
                processed += 1
                print(f"[page] {rel.name} p{page_no:02d} {method} {len(extracted)} chars")
    print(f"[summary] 新处理 {processed}，缓存命中 {cached}；"
          f"文字层 {n_text}，OCR {n_ocr}，未读文字 {n_unreadable}")
    print("[note] 页面草稿未经过复核，不得计入47/47完成度")
    return 0


if __name__ == "__main__":
    sys.exit(main())
