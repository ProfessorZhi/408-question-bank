#!/usr/bin/env python3
"""按**人工登记**的区域把扫描卷的插图裁进 `papers/<id>/assets/`，并写出归属清单。

为什么扫描卷不能复用 `fig_crop.py`
-----------------------------------
`fig_crop.py` 判图靠坐标层的「位图对象 / 图形簇」+ 文字层里的题注行（`题NN 图`）。
扫描卷这两样都没有：整页就是**一张**位图（`408-objects/mock-2027-set-2/page-002.json`
里 `lines=0, clusters=0, images=1`），文字是 OCR 出来的、题注行也不存在。
于是 `fig_crop.py` 在扫描卷上只会把**整页**裁成一张图——那正是用户点名的
「整页截图」充数，明确禁止。

所以扫描卷走**人工登记**这条路：把每张图在页面上的 y 区间（可选 x 区间）
由「页图直读」定下来，逐条登记到 `papers/<id>/figures.yml`，本工具只负责照登记渲染。
登记的每条都要写 `source`（凭什么说这块是第 N 题的图）。

输出
----
  papers/<id>/assets/q<N>-fig.png（同题多图时 q<N>-fig2.png …）
  build/_scratch/408-objects/<paper>/figures.json   ← `md_from_pages.load_figures` 读它

⚠️ 对扫描卷，本工具是 `figures.json` 的**唯一**作者。别在该卷上再跑 `fig_crop.py`，
否则整页截图会把这里登记的图覆盖掉。

用法：
  python -I tools/crop_figures.py --paper mock-2027/set-2
  python -I tools/crop_figures.py --paper mock-2027/set-2 --dry-run   # 只看会裁什么
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parent.parent
OBJ_ROOT = REPO / "build" / "_scratch" / "408-objects"
# 渲染倍率：与 fig_crop 的矢量分支一致（2×）。这些图里有 4×4 矩阵、位域表，
# 2× 在屏幕上够读；再高只是把 PNG 撑大。
ZOOM = 2.0
# 左右留的固定边距（pt）：登记的是**图的外框**，页边距一律不裁进来。
X0, X1 = 40.0, 555.0


def paths_for(paper_id: str) -> str:
    kind, rest = paper_id.split("/", 1)
    if kind == "exams":
        return f"sources/exams/papers/{rest}.pdf"
    return f"sources/mock-2027/pdf/mock2027-set{rest.split('-')[1]}-paper.pdf"


def load_registry(paper_id: str) -> list[dict]:
    path = REPO / "papers" / paper_id / "figures.yml"
    if not path.is_file():
        return []
    import yaml
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        raise SystemExit(f"[crop] {path} 的顶层必须是清单，实际是 {type(data).__name__}")
    for i, e in enumerate(data):
        if not isinstance(e, dict):
            raise SystemExit(f"[crop] {path} 第 {i + 1} 条不是映射")
        for k in ("q", "page", "y0", "y1", "source"):
            if k not in e:
                raise SystemExit(f"[crop] {path} 第 {i + 1} 条缺字段 {k}")
        if not isinstance(e["q"], int) or not 1 <= e["q"] <= 47:
            raise SystemExit(f"[crop] {path} 第 {i + 1} 条的 q 必须在 1—47，实际 {e['q']!r}")
        if not isinstance(e["page"], int) or e["page"] < 1:
            raise SystemExit(f"[crop] {path} 第 {i + 1} 条的 page 必须是正整数，实际 {e['page']!r}")
        y0, y1 = float(e["y0"]), float(e["y1"])
        if not 0 <= y0 < y1:
            raise SystemExit(f"[crop] {path} 第 {i + 1} 条要求 0 ≤ y0 < y1，实际 {y0} / {y1}")
        if not str(e["source"]).strip():
            raise SystemExit(f"[crop] {path} 第 {i + 1} 条的 source 不能是空话")
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paper", required=True)
    ap.add_argument("--dry-run", action="store_true", help="只打印会裁什么，不写盘")
    args = ap.parse_args(argv)

    paper_id = args.paper
    entries = load_registry(paper_id)
    src = REPO / paths_for(paper_id)
    if not src.is_file():
        raise SystemExit(f"[crop] 底本不存在：{src}")
    assets = REPO / "papers" / paper_id / "assets"

    import pymupdf

    figures: list[dict] = []
    seq: dict[int, int] = {}
    with pymupdf.open(str(src)) as doc:
        for e in entries:
            q, pno = int(e["q"]), int(e["page"])
            x0 = float(e.get("x0", X0))
            x1 = float(e.get("x1", X1))
            y0, y1 = float(e["y0"]), float(e["y1"])
            if pno > doc.page_count:
                raise SystemExit(f"[crop] 第 {q} 题登记在第 {pno} 页，底本只有 {doc.page_count} 页")
            page = doc[pno - 1]
            rect = page.rect
            clip = pymupdf.Rect(max(0.0, x0), max(0.0, y0),
                                min(rect.width, x1), min(rect.height, y1))
            if clip.is_empty:
                raise SystemExit(f"[crop] 第 {q} 题登记的区域是空的：{clip}")
            idx = seq.get(q, 0)
            seq[q] = idx + 1
            name = f"q{q}-fig.png" if idx == 0 else f"q{q}-fig{idx + 1}.png"
            ref = f"题 {q} 图" + (f"（第 {idx + 1} 张）" if idx else "")
            bbox = [round(clip.x0, 1), round(clip.y0, 1), round(clip.x1, 1), round(clip.y1, 1)]
            if args.dry_run:
                print(f"[crop] 会裁 第 {q} 题 ← 第 {pno} 页 {bbox} → assets/{name}")
                figures.append({"q": q, "file": f"assets/{name}", "ref": ref, "page": pno,
                                "bbox": bbox, "owner_by": "人工登记 figures.yml",
                                "parts": 1, "dry_run": True})
                continue
            pix = page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), clip=clip, alpha=False)
            assets.mkdir(parents=True, exist_ok=True)
            data = pix.tobytes("png")
            (assets / name).write_bytes(data)
            figures.append({"q": q, "file": f"assets/{name}", "ref": ref, "page": pno,
                            "bbox": bbox, "owner_by": "人工登记 figures.yml",
                            "parts": 1, "bytes": len(data),
                            "source": str(e["source"])})
            print(f"[crop] 第 {q} 题 ← 第 {pno} 页 {bbox}（{pix.width}x{pix.height}）"
                  f" → assets/{name} {len(data) // 1024}KB")

    if args.dry_run:
        print(f"[crop] dry-run：登记 {len(figures)} 张，未写盘")
        return 0

    out = OBJ_ROOT / paper_id.replace("/", "-") / "figures.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"paper": paper_id, "figures": figures,
                               "notes": ["来源：papers/%s/figures.yml（人工登记，扫描卷）" % paper_id]},
                              ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    qs = sorted({f["q"] for f in figures})
    print(f"[crop] {paper_id}: 登记 {len(figures)} 张，覆盖题号 {qs} → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
