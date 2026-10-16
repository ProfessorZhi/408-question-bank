#!/usr/bin/env python3
"""按**块坐标**抽取每页的文本行 / 位图 / 矢量图形簇，落成 JSON 供排版用。

为什么不能靠纯文本猜
--------------------
`page.get_text("text")` 出来的是**阅读顺序的一串字符**，丢掉了 x/y。
于是：
  · 表格的列边界没了 → 用空格猜列数，稍不留神就把一行拆错；
  · 图的位置没了 → 没法知道「题44 图」到底该插在哪道题里；
  · 代码的缩进没了 → 代码块只能靠 `{`/`;` 猜。

本工具保留坐标，后面 `md_from_pages.py` 才能：
  · 用图形簇的 bbox 圈出表格区域，再按 x 聚列 → 真 GFM 表；
  · 用位图的 bbox 裁图，并按 y 顺序归属到最近的上方题号；
  · 用行 bbox 判断代码块的起止。

产出（gitignore 内，不入库）：
  build/_scratch/408-objects/<paper>/page-XXX.json

用法：
  python -I tools/page_objects.py --paper exams/2026
  python -I tools/page_objects.py --paper exams/2026 --force
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
OUT_ROOT = REPO / "build" / "_scratch" / "408-objects"

# 图形簇：bbox 间隙小于这个值就连成一簇（pt）
CLUSTER_GAP = 10.0
# 少于这么多条线的簇不算表格（单条下划线、着重号横线都会被滤掉）
CLUSTER_MIN_ITEMS = 6
# 太小的簇不算表（避免把着重号/下划线当成表）
CLUSTER_MIN_AREA = 1500.0


def paths_for(paper_id: str) -> str:
    kind, rest = paper_id.split("/", 1)
    if kind == "exams":
        return f"sources/exams/papers/{rest}.pdf"
    return f"sources/mock-2027/pdf/mock2027-set{rest.split('-')[1]}-paper.pdf"


def _union(a, b):
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _gap(a, b) -> float:
    """两个 bbox 的分离度：相交则为 0，否则为最近边距。"""
    dx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
    dy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    return (dx * dx + dy * dy) ** 0.5


def cluster_rects(rects: list, gap: float = CLUSTER_GAP) -> list[dict]:
    """把 bbox 列表按邻近关系聚簇（并查集，O(n²)——单页条数很少）。"""
    n = len(rects)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            if _gap(rects[i], rects[j]) <= gap:
                pi, pj = find(i), find(j)
                if pi != pj:
                    parent[pi] = pj

    groups: dict[int, list] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    out = []
    for members in groups.values():
        box = rects[members[0]]
        for i in members[1:]:
            box = _union(box, rects[i])
        area = (box[2] - box[0]) * (box[3] - box[1])
        out.append({"bbox": [round(v, 1) for v in box],
                    "items": len(members), "area": round(area, 1)})
    return sorted(out, key=lambda c: (c["bbox"][1], c["bbox"][0]))


def page_lines(page) -> list[dict]:
    """带 bbox 的“行”，保证阅读顺序（先 y 后 x）。"""
    data = page.get_text("dict")
    lines = []
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
            if not spans:
                continue
            text = "".join(s["text"] for s in spans)
            box = spans[0]["bbox"]
            for s in spans[1:]:
                box = _union(box, s["bbox"])
            lines.append({
                "text": text,
                "bbox": [round(v, 1) for v in box],
                "size": round(max(s["size"] for s in spans), 2),
                "flags": spans[0].get("flags", 0),
                "spans": [{"text": s["text"],
                           "bbox": [round(v, 1) for v in s["bbox"]],
                           "size": round(s["size"], 2),
                           "flags": s.get("flags", 0)} for s in spans],
            })
    lines.sort(key=lambda l: (round(l["bbox"][1], 1), l["bbox"][0]))
    return lines


def draw_rects(page) -> list:
    rects = []
    for d in page.get_drawings():
        r = d.get("rect")
        if r is None:
            continue
        box = (r.x0, r.y0, r.x1, r.y1)
        if (box[2] - box[0]) < 0.5 and (box[3] - box[1]) < 0.5:
            continue                      # 退化点（着重号的圆点等）不计
        rects.append(box)
    return rects


def page_json(page, pno: int) -> dict:
    images = []
    for info in page.get_image_info(xrefs=True):
        box = info["bbox"]
        images.append({
            "bbox": [round(v, 1) for v in box],
            "px": [info.get("width"), info.get("height")],
            "xref": info.get("xref", 0),
        })
    clusters = [c for c in cluster_rects(draw_rects(page))
                if c["items"] >= CLUSTER_MIN_ITEMS and c["area"] >= CLUSTER_MIN_AREA]
    return {"page": pno, "size": [round(page.rect.width, 1), round(page.rect.height, 1)],
            "images": images, "clusters": clusters, "lines": page_lines(page)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paper", required=True)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--pages", default="", help="只处理这些页，如 4,8-12")
    args = ap.parse_args(argv)

    rel = paths_for(args.paper)
    src = REPO / rel
    if not src.is_file():
        raise SystemExit(f"[obj] 底本不存在：{src}")

    want: set[int] | None = None
    if args.pages:
        want = set()
        for part in args.pages.split(","):
            if "-" in part:
                a, b = part.split("-")
                want.update(range(int(a), int(b) + 1))
            else:
                want.add(int(part))

    import pymupdf
    out_dir = OUT_ROOT / args.paper.replace("/", "-")
    out_dir.mkdir(parents=True, exist_ok=True)
    written = skipped = 0
    with pymupdf.open(str(src)) as doc:
        for pno in range(1, doc.page_count + 1):
            if want is not None and pno not in want:
                continue
            dst = out_dir / f"page-{pno:03d}.json"
            if dst.exists() and not args.force:
                skipped += 1
                continue
            payload = page_json(doc[pno - 1], pno)
            dst.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                           encoding="utf-8", newline="\n")
            written += 1
            print(f"[obj] p{pno:02d} 行{len(payload['lines'])} "
                  f"图{len(payload['images'])} 簇{len(payload['clusters'])}")
    print(f"[obj] {args.paper}: 写 {written} 页，跳过 {skipped} 页 → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
