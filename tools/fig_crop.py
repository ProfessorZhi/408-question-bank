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


def png_size(path: Path) -> tuple[int, int] | None:
    """只读 PNG 头（IHDR）拿像素宽高 —— 用来核对「盘上这张图到底是不是这次要的那张」。

    为什么要核：`figures.json` 和 `assets/*.png` 是两次写入，中间失败/换规则时会对不上；
    光比 bbox（清单里写的）会漏掉「清单是新的、图是旧的」。
    """
    import struct
    try:
        with path.open("rb") as fh:
            head = fh.read(33)
        if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
            return None
        return struct.unpack(">II", head[16:24])
    except Exception:
        return None


def group_slices(images: list[dict], anchors: list[tuple[float, int]],
                 gap: float = 2.0, xtol: float = 2.0) -> list[dict]:
    """把**同一张图被拆成多条位图**的情况并回一张。

    2018 第 44 题的「题44 图」（CPU 存储访问过程框图）在 PDF 里是 **11 条**
    4903×213 的横条位图叠出来的：x 范围完全一样（54.0—553.0），y 首尾相接。
    按「一框一图」处理的话，同名文件会被覆盖 → 前 10 条**内容直接丢掉**，
    questions.md 里只嵌到最上面那一窄条。
    所以 x 范围相同、y 相接、且**两条之间没有夹着别的题号行**的位图并成一组，
    按合并后的外框**重新渲染**一张 PNG（多条位图拼的图取不出单个 xref，只能渲染）。

    「中间不许夹题号行」这条是保险：两题的图正好上下相接时不能并成一张。
    """
    out: list[dict] = []
    for im in sorted(images, key=lambda im: (im["bbox"][1], im["bbox"][0])):
        b = list(im["bbox"])
        if out:
            g = out[-1]
            gb = g["bbox"]
            same_x = abs(b[0] - gb[0]) <= xtol and abs(b[2] - gb[2]) <= xtol
            touching = 0.0 <= b[1] - gb[3] <= gap
            crosses = any(gb[3] <= ay <= b[1] for ay, _no in anchors)
            if same_x and touching and not crosses:
                g["bbox"] = [min(gb[0], b[0]), gb[1], max(gb[2], b[2]), max(gb[3], b[3])]
                g["parts"] += 1
                continue
        out.append({"kind": "img", "bbox": b, "px": im["px"], "xref": im["xref"], "parts": 1})
    for g in out:
        if g["parts"] > 1:
            g["kind"] = "img-slices"     # 多条位图拼的：按区域重渲染
            g["xref"] = None
    return out


def owner_overlap(anchors: list[tuple[float, int]], box: list[float],
                  page_h: float) -> tuple[int, float] | None:
    """图落进哪道题的**纵向跨度**里最多。

    为什么要这一条：「就近题号」取的是**图的上边缘**之上的题号，而右侧「如右图所示」那种图
    的上边缘常常高于它自己那道题的题号行 —— 2009 第 3 题的二叉树图 bbox 上边缘 y=238.8，
    第 3 题题号行 y=249.7，于是整张图被判给了**第 2 题**（第 3 题反而没图）。
    改成「谁跟这张图的重叠最高就归谁」，同一份数据下第 2 题重叠 10.9pt、第 3 题重叠 81.5pt，
    结论就正过来了。返回值带重叠高度，供报告说明归属依据。
    """
    if not anchors:
        return None
    spans = []
    for i, (ay, no) in enumerate(anchors):
        end = anchors[i + 1][0] if i + 1 < len(anchors) else page_h
        spans.append((ay, end, no))
    y0, y1 = box[1], box[3]
    best: tuple[float, int] | None = None
    for a, b, no in spans:
        ov = min(b, y1) - max(a, y0)
        if ov <= 0:
            continue
        if best is None or ov > best[0] + 1e-9:
            best = (ov, no)
    return best


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
    # 上一轮裁过的清单：**「文件已存在」不等于「文件是对的」**。
    # 2018 第 44 题那张图，上一轮只裁到最上面一条横条（同名文件），这一轮并成整张后
    # 若还按「文件在就复用」，就会把旧的那条窄图当成成品交出去。
    # 所以复用要求**几何完全一致**（同页、同 bbox、同拼条数），否则重裁。
    prev: dict[str, tuple] = {}
    prev_file = OBJ_ROOT / paper_id.replace("/", "-") / "figures.json"
    if prev_file.is_file():
        try:
            for f in json.loads(prev_file.read_text(encoding="utf-8"))["figures"]:
                prev[f["file"]] = (f.get("page"), tuple(round(v, 1) for v in f["bbox"]),
                                   f.get("parts", 1))
        except Exception:                     # 清单坏了就当没有，重裁一遍即可
            prev = {}
    # 上一页结尾时“正在写”的题号：题43 的表落在第 8 页，而题43 起于第 7 页，
    # 本页又没有新题号，所以必须跨页沿用。
    carry_q: int | None = None
    # 同一道题可以有多张图（2009 第 44 题：数据通路结构图 + 指令格式表，都是位图）。
    # 文件名按「该题第几张」编号，重复的那张不许再叫 q44-fig.png ——
    # 否则第二张会被当成「文件已存在」直接复用，**内容悄悄丢了**，questions.md 里还出现两条同链接。
    seq: dict[int, int] = {}
    # 题号必须**接得上**：`RE_QSTART` 只管「数字+顿号」，正文换行后的续行照样会中招。
    # 2021 第 40 题题干折行成 `501、封装200B 数据的段…`（x=54，和题号同一起始位置），
    # 于是图被归给了「第 501 题」，真图 q40 反而没嵌进 questions.md。
    expect_q = 1

    with pymupdf.open(str(src)) as doc:
        for pno in sorted(objs):
            obj = objs[pno]
            page = doc[pno - 1]
            lines = obj["lines"]
            anchors = []
            for l in sorted(lines, key=lambda l: l["bbox"][1]):
                m = RE_QSTART.match(l["text"].strip())
                if not m or l["bbox"][0] >= 130:
                    continue
                no = int(m.group(1))
                # 允许跳号 1—2 个（个别题号 OCR 丢了），但绝不允许「501」这种脱轨值。
                if expect_q <= no <= expect_q + 2:
                    anchors.append((l["bbox"][1], no))
                    expect_q = no + 1
                else:
                    notes.append(f"第 {pno} 页剔除伪题号锚点「{l['text'].strip()[:40]}」"
                                 f"（期望 {expect_q}±2，实得 {no}）")

            def owner_above(y: float) -> int | None:
                """该 y 之上最近的那个题号；本页没有就用上一页沿用的。"""
                found = [no for ay, no in anchors if ay <= y]
                return found[-1] if found else carry_q

            candidates = group_slices(obj["images"], anchors)
            for g in candidates:
                if g["parts"] > 1:
                    notes.append(f"第 {pno} 页 bbox={g['bbox']} 由 {g['parts']} 条位图横条拼成"
                                 f"（同一张图被切碎），已并回一张")
            for cl in obj["clusters"]:
                candidates.append({"kind": "cluster", "bbox": cl["bbox"],
                                   "px": None, "xref": None, "parts": 1})
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
                    ov = owner_overlap(anchors, box, obj["size"][1])
                    if ov:
                        owner, how = ov[1], f"跨度重叠{ov[0]:.0f}pt"
                    else:
                        near = owner_above(box[1])
                        if near is None:
                            notes.append(f"第 {pno} 页 bbox={box} 归属不明，未裁（等人工判）")
                            continue
                        owner, how = near, "就近题号（本页无重叠）"

                idx = seq.get(owner, 0)
                seq[owner] = idx + 1
                name = f"q{owner}-fig.png" if idx == 0 else f"q{owner}-fig{idx + 1}.png"
                dst = assets / name
                ref = f"题 {owner} 图" + (f"（第 {idx + 1} 张）" if idx else "")
                same_geom = prev.get(f"assets/{name}") == (
                    pno, tuple(round(v, 1) for v in box), cand["parts"])
                # 还要核盘上那份图的**长宽比**跟这次的外框对不对得上
                # （清单一致、图是旧的这种情况前面就踩过）——差得远就重裁。
                if same_geom and dst.exists():
                    wh = png_size(dst)
                    want = (box[2] - box[0]) / max(box[3] - box[1], 1e-6)
                    same_geom = wh is not None and abs(wh[0] / wh[1] - want) <= 0.03 * want
                    if not same_geom:
                        notes.append(f"第 {pno} 页 {name}：盘上那张图的长宽比与本次外框不符"
                                     f"（{wh if wh else '读不出尺寸'} vs 外框比 {want:.2f}），重裁")
                if dst.exists() and same_geom and not args.force:
                    figures.append({"q": owner, "file": f"assets/{name}",
                                    "ref": ref, "page": pno,
                                    "bbox": box, "owner_by": how, "reused": True,
                                    "parts": cand["parts"]})
                    continue

                if cand["xref"]:
                    info = doc.extract_image(cand["xref"])
                    data, ext = info["image"], info["ext"]
                    if ext != "png":
                        pix = pymupdf.Pixmap(data)
                        data = pix.tobytes("png")
                else:
                    # 纯矢量图 / 多条位图拼的图：按区域渲染，2 倍分辨率够看清
                    clip = pymupdf.Rect(*box)
                    data = page.get_pixmap(clip=clip, matrix=pymupdf.Matrix(2, 2),
                                           alpha=False, colorspace="rgb").tobytes("png")
                dst.write_bytes(data)
                figures.append({"q": owner, "file": f"assets/{name}",
                                "ref": ref, "page": pno,
                                "bbox": box, "owner_by": how, "reused": False,
                                "parts": cand["parts"], "bytes": len(data)})
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
