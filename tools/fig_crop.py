#!/usr/bin/env python3
"""把底本里的**图**裁成 PNG 放进 `papers/<paper>/assets/`，并写出归属清单。

为什么要裁真图
--------------
用户明确禁止用「请见 PDF 图片」占位、整页截图或空 stub 充数。
所以要判两件事：

1. **这块到底是图还是表？**
   图形簇范围内如果**有可读文字**（≥3 行），它是表格 —— 表格该走文字路线
   （`md_from_pages.py` 按坐标转 GFM 表），裁成图片反而是**降级**（不可编辑）。
   只有文字极少、纯粹靠线条/位图表达的，才裁图。

2. **这块属于哪道题？**
   两条线索，从强到弱：
     a. 就近的题注行 `题NN 图 / 题NN 表 / 题NN 题图`（题注可能在图的上方或下方）；
     b. 否则取**该页 y 之上最近的那个题号**；本页没有就沿用上一页正在写的题号。
   两条都对不上就**不裁**，写进报告等人工判，绝不硬塞给某道题。

输出
----
  papers/<paper>/assets/q<N>-fig.png      图（只裁图，不裁表）
  build/_scratch/408-objects/<paper>/figures.json   归属清单（gitignore 内）

用法：
  python -I tools/fig_crop.py --paper exams/2026
  python -I tools/fig_crop.py --paper exams/2026 --force   # 重裁覆盖
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
OBJ_ROOT = REPO / "build" / "_scratch" / "408-objects"

RE_QSTART = re.compile(r"^(\d{1,3})\s*[.．、]")
RE_CAPTION = re.compile(r"^题\s*(\d{1,3})\s*(图|表|题图)\s*$")
# 文字在这个数以下才当“图”看
MAX_TEXT_LINES = 2
# 题注允许离目标多远仍算“它标注的对象”（图下方/上方）
CAPTION_NEAR = 60.0


def paths_for(paper_id: str) -> str:
    kind, rest = paper_id.split("/", 1)
    if kind == "exams":
        return f"sources/exams/papers/{rest}.pdf"
    return f"sources/mock-2027/pdf/mock2027-set{rest.split('-')[1]}-paper.pdf"


def objs_of(paper_id: str) -> dict[int, dict]:
    folder = OBJ_ROOT / paper_id.replace("/", "-")
    if not folder.is_dir():
        raise SystemExit(f"[fig] 缺少坐标数据：{folder}（先跑 tools/page_objects.py）")
    out = {}
    for f in sorted(folder.glob("page-*.json")):
        out[int(f.stem.split("-")[1])] = json.loads(f.read_text(encoding="utf-8"))
    return out


def caption_owner(lines: list[dict], y0: float, y1: float) -> tuple[int, str] | None:
    """找标注这块区域的题注。"""
    best = None
    for line in lines:
        m = RE_CAPTION.match(line["text"].strip())
        if not m:
            continue
        cy = (line["bbox"][1] + line["bbox"][3]) / 2
        if cy < y0:                       # 题注在上方
            dist = y0 - cy
        elif cy > y1:                     # 题注在下方
            dist = cy - y1
        else:                             # 题注在框内
            dist = 0.0
        if dist > CAPTION_NEAR:
            continue
        if best is None or dist < best[0]:
            best = (dist, int(m.group(1)), "图" if m.group(2) == "题图" else m.group(2))
    return (best[1], best[2]) if best else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paper", required=True)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    paper_id = args.paper
    objs = objs_of(paper_id)
    src = REPO / paths_for(paper_id)
    if not src.is_file():
        raise SystemExit(f"[fig] 底本不存在：{src}")

    assets = REPO / "papers" / paper_id / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    import pymupdf
    figures: list[dict] = []
    notes: list[str] = []
    # 上一页结尾时“正在写”的题号：题43 的表落在第 8 页，而题43 起于第 7 页，
    # 本页又没有新题号，所以必须跨页沿用。
    carry_q: int | None = None

    with pymupdf.open(str(src)) as doc:
        for pno in sorted(objs):
            obj = objs[pno]
            page = doc[pno - 1]
            lines = obj["lines"]
            anchors = sorted(
                (l["bbox"][1], int(m.group(1))) for l in lines
                if (m := RE_QSTART.match(l["text"].strip())) and l["bbox"][0] < 130)

            def owner_above(y: float) -> int | None:
                """该 y 之上最近的那个题号；本页没有就用上一页沿用的。"""
                found = [no for ay, no in anchors if ay <= y]
                return found[-1] if found else carry_q

            candidates = [{"kind": "img", "bbox": im["bbox"], "px": im["px"],
                           "xref": im["xref"]} for im in obj["images"]]
            for cl in obj["clusters"]:
                candidates.append({"kind": "cluster", "bbox": cl["bbox"],
                                   "px": None, "xref": None})
            candidates.sort(key=lambda c: c["bbox"][1])

            for cand in candidates:
                box = cand["bbox"]
                inside = [l for l in lines
                          if box[1] - 2 <= (l["bbox"][1] + l["bbox"][3]) / 2 <= box[3] + 2
                          and box[0] - 2 <= l["bbox"][0] <= box[2] + 2]
                # 簇里有成块文字 → 是表格，交给文字路线，不裁图
                if cand["kind"] == "cluster" and len(inside) > MAX_TEXT_LINES:
                    notes.append(f"第 {pno} 页 bbox={box} 判为**表格**（含 {len(inside)} 行文字），"
                                 f"走 GFM 文字路线，不裁图")
                    continue

                cap = caption_owner(lines, box[1], box[3])
                if cap:
                    owner, _kind_cn = cap
                    how = "题注"
                else:
                    near = owner_above(box[1])
                    if near is None:
                        notes.append(f"第 {pno} 页 bbox={box} 归属不明，未裁（等人工判）")
                        continue
                    owner, how = near, "就近题号"

                name = f"q{owner}-fig.png"
                dst = assets / name
                if dst.exists() and not args.force:
                    figures.append({"q": owner, "file": f"assets/{name}",
                                    "ref": f"题 {owner} 图", "page": pno,
                                    "bbox": box, "owner_by": how, "reused": True})
                    continue

                if cand["xref"]:
                    info = doc.extract_image(cand["xref"])
                    data, ext = info["image"], info["ext"]
                    if ext != "png":
                        pix = pymupdf.Pixmap(data)
                        data = pix.tobytes("png")
                else:
                    # 纯矢量图：按区域渲染，2 倍分辨率够看清
                    clip = pymupdf.Rect(*box)
                    data = page.get_pixmap(clip=clip, matrix=pymupdf.Matrix(2, 2),
                                           alpha=False, colorspace="rgb").tobytes("png")
                dst.write_bytes(data)
                figures.append({"q": owner, "file": f"assets/{name}",
                                "ref": f"题 {owner} 图", "page": pno,
                                "bbox": box, "owner_by": how, "reused": False,
                                "bytes": len(data)})
                print(f"[fig] 第 {owner} 题 ← 第 {pno} 页 {cand['kind']} "
                      f"bbox={box}（{how}） → {name} {len(data) // 1024}KB")

            if anchors:
                carry_q = anchors[-1][1]

    out = OBJ_ROOT / paper_id.replace("/", "-") / "figures.json"
    out.write_text(json.dumps({"paper": paper_id, "figures": figures, "notes": notes},
                              ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"[fig] {paper_id}: 裁出 {sum(1 for f in figures if not f.get('reused'))} 张"
          f"（复用 {sum(1 for f in figures if f.get('reused'))}），"
          f"未决 {len([n for n in notes if '未裁' in n])} 处 → {out}")
    for note in notes:
        print(f"[fig][note] {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
