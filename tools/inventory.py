#!/usr/bin/env python3
"""扫描 sources/ 下的 PDF，生成来源清单 index/sources-manifest.json。

用途：
  - 给每个 PDF 记 sha256（sources/ 只增不改，哈希漂移即为异常）
  - 记页数 / 文本层字符数 / 内嵌图片数 —— 决定转录走文本层还是 OCR
  - 体量统计，供评估仓库大小

用法：
  python tools/inventory.py
  python tools/inventory.py --include-incoming    # 额外登记 sources/_incoming/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # Windows 控制台默认 GBK
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parent.parent


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def probe_pdf(path: Path) -> dict:
    """页数 / 文本层字符数 / 内嵌图片数。缺 pymupdf 时降级为只报大小。"""
    info: dict = {"pages": None, "text_chars": None, "images": None, "probe": "unavailable"}
    try:
        import pymupdf  # noqa: PLC0415
    except Exception:
        try:
            import fitz as pymupdf  # noqa: PLC0415
        except Exception:
            return info
    try:
        doc = pymupdf.open(str(path))
    except Exception as exc:  # 损坏 / 加密 / 非 PDF
        info["probe"] = f"open-failed: {type(exc).__name__}"
        return info
    try:
        chars = 0
        imgs = 0
        for page in doc:
            chars += len(page.get_text())
            imgs += len(page.get_images(full=True))
        info.update(pages=doc.page_count, text_chars=chars, images=imgs,
                    probe="text-layer" if chars > 200 else "no-text-layer (OCR needed)")
    finally:
        doc.close()
    return info


def scan(root: Path, base: Path) -> list[dict]:
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(base).as_posix()
        rec = {
            "path": rel,
            "bytes": p.stat().st_size,
            "sha256": sha256_of(p),
            "ext": p.suffix.lower(),
        }
        if p.suffix.lower() == ".pdf":
            rec.update(probe_pdf(p))
        out.append(rec)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--include-incoming", action="store_true",
                    help="同时登记 sources/_incoming/（默认排除，避免未确认材料混入清单）")
    ap.add_argument("-o", "--out", default=str(REPO / "index" / "sources-manifest.json"))
    args = ap.parse_args(argv)

    roots = [REPO / "sources"]
    records: list[dict] = []
    for r in roots:
        if r.exists():
            records.extend(scan(r, REPO))

    manifest = {
        "generated_by": "tools/inventory.py",
        "repo": str(REPO),
        "count": len(records),
        "total_bytes": sum(r["bytes"] for r in records),
        "note": "sources/ 只增不改；sha256 用于检测意外改写。",
        "files": records,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")

    pdfs = [r for r in records if r["ext"] == ".pdf"]
    print(f"[inventory] {len(records)} 个文件（其中 PDF {len(pdfs)} 个），"
          f"合计 {manifest['total_bytes'] / 1048576:.1f} MiB")
    print(f"[inventory] 写出 {out}")
    for r in pdfs:
        tp = r.get("probe", "?")
        print(f"  {r['bytes']:>9,}  pages={r.get('pages')!s:>4}  "
              f"chars={r.get('text_chars')!s:>7}  imgs={r.get('images')!s:>4}  "
              f"{tp:<28} {r['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
