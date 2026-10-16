#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""answer_grid_ocr.py —— 用**渲染 + 离线 OCR** 读答案卷卷首那张答案表。

与 `tools/answer_grid.py` 的分工
--------------------------------
| 工具 | 读什么 | 适用 |
|---|---|---|
| `answer_grid.py` | 文字层里的 A–D 行（按 x 聚 8 列） | 文字层里**有**一张列式答案表 |
| 本工具 | 把卷首那一条带**渲染成位图再 OCR**，认「题号 + 字母」对 | 文字层里那张表**残缺/根本没有**（2009、2014、2019、2021、2024—2026） |

为什么非要多这一路
------------------
2009/2014 的答案表在文字层里**第 8 列整列缺失**（2009 只聚出 7 列 35 个字母，2014 第 8 列只剩 `'DD'`）；
而**渲染出来的页面上，那 40 个「题号 + 字母」明明都在**——缺的是文字层，不是内容。
所以这一路读的是**页面像素**，与前一路互为独立证据。

硬门槛（不猜、不补）
--------------------
1. 表是若干行的「题号 + 字母」（**版面各年不同**：2009—2023 是 8 列 × 5 行，
   2024 起是 5 列 × 8 行，题号与字母还在同一框里）；
2. 题号 1…40 各出现**恰好一次**，每个题号配上**恰好一个** A–D 字母，
   且必须能取到**连续若干行**（4—10 行）使题号并集恰好是 1…40；
3. 同一个题号被配到两个不同字母 → **冲突**，该窗口作废并点名；
4. 题号没认出来的落单字母**不塞给上一题**（宁可少认一个）；
5. 凑不齐也**不编**：落盘时 `complete: false`，只当独立佐证用，不当权威。

输出
----
    build/_scratch/answer-grid-ocr/<stem>.json
        {"paper": …, "answers": {题号: 字母}, "source": "ocr-render",
         "page": …, "rows": […], "conf": {题号: 置信度}}

用法
----
    python -I tools/answer_grid_ocr.py --paper exams/2009 --write
    python -I tools/answer_grid_ocr.py --all
    python -I tools/answer_grid_ocr.py --all --write --cross
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# `python -I` 不把脚本目录放进 sys.path[0]，这里显式加，才能 import 同目录的 ocr_runtime。
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ocr_runtime  # noqa: E402  （DLL 兼容层，必须在 import pymupdf/onnxruntime 之前就位）

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

OUT_ROOT = REPO / "build" / "_scratch" / "answer-grid-ocr"
TEXT_GRID_ROOT = REPO / "build" / "_scratch" / "answer-grid"

# 卷首那条带的四边都得**往外放**，每一边都是被实测切到过才挪的：
#   · y0：2023 的表从 y≈142 就开始（第一行 1—8 题），按 150 截会把**整个第一行**切掉；
#   · y1：2024 的 8 行表排到 y≈344，2026 的最后一行（36—40）在 y≈384、框底≈394，
#         按 390 截会把那一行的**下半截**切掉（OCR 直接丢框 → 末尾 5 题全缺）；
#   · x0：2019 的表左边缘在 x≈30（第一列的题号 1./9./17./25. 都在 x≈32—41），
#         按 36 截会把这几个题号切掉 → 每行第一题全缺；
#   · x1：2022 第 8 列靠右（x≈550），按 486 截会切掉。
# 带子放宽的代价只是多几个噪声行：判定是「**某 4—10 个连续行**的题号并集恰为 1…40」，
# 解析流那一行（`1.【参考答案】D`）被并进来也不碍事——它和表里读到的字母同源。
BAND = (18.0, 120.0, 580.0, 410.0)
ZOOM = 4.0                     # 4 倍 ≈ 288dpi，实测 RapidOCR 在 10pt 字号上够用
ZOOM_LADDER = (4.0, 6.0)       # 4 倍读不齐就上 6 倍再认一遍（只多花时间，不会改出内容）
ROW_TOL = 5.0                  # y 相差多少以内算同一行
NUM_LIMIT = 40

# 「题号」：开头是 1—2 位数字，紧跟一个分隔符（`. 。 ． 、 ,` 或空），其余是杂讯。
RE_HEAD_NUM = re.compile(r"^(\d{1,2})\s*[.。．、,，:：]")
# 「字母」：整行只有一个 A–D，两侧只许有**标点/空白**杂讯（`C`、`C。`、`(B)`）。
# ⚠️ 不能写成「除 A–D 外没有别的**字母**」：汉字 `isalpha()` 也是真，
# 解析流里的 `故选 B。` 就会被当成一个答案格，把答案表之外的字母混进来。
_PUNCT = r"[\s.。．、,，;；:：()（）\[\]【】\-—–]"
RE_ONLY_LETTER = re.compile(rf"^{_PUNCT}{{0,3}}([A-D]){_PUNCT}{{0,3}}$")


def classify(text: str) -> tuple[str, int | None, str | None]:
    """→ (kind, 题号, 字母)；kind ∈ {'num','letter','both','noise'}。"""
    t = text.strip()
    head = RE_HEAD_NUM.match(t)
    if head:
        no = int(head.group(1))
        rest = t[head.end():]
        letters = [c for c in rest if "A" <= c <= "D"]
        # 数字后面直接跟字母才算「题号 + 字母」（`32. A`）；`34.1` 里那个 `1` 是杂讯，不算字母。
        letters = [c for c in letters if c in "ABCD"]
        # `rest` 里若还夹着别的字母（小写/其他），一律判噪声
        others = [c for c in rest if c.isalpha() and not ("A" <= c <= "D")]
        if len(letters) == 1 and not others:
            return "both", no, letters[0]
        if not letters and not others:
            return "num", no, None
        return "noise", None, None
    m = RE_ONLY_LETTER.match(t)
    if m:
        return "letter", None, m.group(1)
    return "noise", None, None


def ocr_boxes(engine, page, rect, zoom: float = ZOOM
              ) -> list[tuple[float, float, float, float, str, float]]:
    import numpy as np
    import pymupdf

    clip = pymupdf.Rect(*rect)
    pix = page.get_pixmap(clip=clip, matrix=pymupdf.Matrix(zoom, zoom),
                          alpha=False, colorspace="rgb")
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    result, _ = engine(img)
    out = []
    for item in (result or []):
        box, text, score = item[0], str(item[1]), float(item[2]) if len(item) > 2 else 0.0
        x0 = min(p[0] for p in box) / zoom + clip.x0
        y0 = min(p[1] for p in box) / zoom + clip.y0
        x1 = max(p[0] for p in box) / zoom + clip.x0
        y1 = max(p[1] for p in box) / zoom + clip.y0
        out.append((x0, y0, x1, y1, text, score))
    return out


def cluster_rows(boxes) -> tuple[list[list[dict]], list[str]]:
    """→ (按 y 聚好的行, 说明)。只保留「题号/字母」形状的框。"""
    notes: list[str] = []
    items = []
    for x0, y0, x1, y1, text, score in boxes:
        kind, no, ch = classify(text)
        if kind == "noise":
            continue
        if no is not None and not (1 <= no <= NUM_LIMIT):
            continue
        items.append({"kind": kind, "no": no, "ch": ch, "x0": x0, "x1": x1,
                      "yc": (y0 + y1) / 2, "text": text, "score": score})
    if not items:
        return [], ["OCR 框里没有「题号」或「字母」形状的东西"]
    items.sort(key=lambda d: d["yc"])
    rows: list[list[dict]] = []
    for it in items:
        if rows and it["yc"] - rows[-1][-1]["yc"] <= ROW_TOL:
            rows[-1].append(it)
        else:
            rows.append([it])
    return rows, notes


def read_all_rows(boxes) -> tuple[dict[int, tuple[str, float]], list[str]]:
    """窄带专用：一条里就那么几行，**所有**行一起读，不做「4—10 行窗口」搜索。

    为什么必须分开：`pairs_from_boxes` 硬要 4—10 行（它面对的是整页，得有窗口才不被
    杂讯带偏），而逐行窄带**只有一行**，于是永远凑不出窗口、永远返回空 ——
    这条窄带读到的 5 个字母就这么被丢掉了（2024 第 17 题正是这样漏的）。
    """
    rows, notes = cluster_rows(boxes)
    if not rows:
        return {}, notes
    pairs, wnotes, _hard = _read_window(rows)
    return pairs, notes + wnotes


def pairs_from_boxes(boxes) -> tuple[dict[int, tuple[str, float]], list[str], bool]:
    """把 OCR 框拼成 {题号: (字母, 置信度)}。

    版面各年不一：2009—2023 是 **8 列 × 5 行**，2024 起是 **5 列 × 8 行**
    （题号和字母还在同一个框里，如 `17. D`）。所以窗口不写死 5 行，
    改成「**连续的若干行，其题号并集恰为 1…40**」——凑得齐才算数。
    凑不齐也不丢：返回**拿到多少算多少**，由调用方决定怎么用（第三项 complete=False）。
    """
    rows, notes = cluster_rows(boxes)

    best: tuple[dict[int, tuple[str, float]], list[str]] | None = None
    for start in range(len(rows)):
        for end in range(start + 4, min(len(rows), start + 10) + 1):
            window = rows[start:end]
            pairs, wnotes, hard = _read_window(window)
            if hard:
                continue                      # 同号两字母这类结构性问题，跳过这个窗口
            if set(pairs) == set(range(1, NUM_LIMIT + 1)):
                return pairs, notes + wnotes, True
            if best is None or len(pairs) > len(best[0]):
                best = (pairs, notes + wnotes)
    if best is None:
        return {}, notes + ["没有任何 4—10 行窗口能读成「题号 + 字母」对"], False
    pairs, wnotes = best
    missing = sorted(set(range(1, NUM_LIMIT + 1)) - set(pairs))
    wnotes.append(f"整表没凑齐 1…{NUM_LIMIT}，只读到 {len(pairs)} 个；缺 {missing[:12]}"
                  f"{'…' if len(missing) > 12 else ''}")
    return pairs, wnotes, False


def _read_window(window: list[list[dict]]) -> tuple[dict, list[str], bool]:
    """把若干行读成 {题号: (字母, 置信度)}。第三项 True 表示遇到**结构性冲突**（整窗作废）。"""
    pairs: dict[int, tuple[str, float]] = {}
    notes: list[str] = []
    hard = False
    for row in window:
        cur: int | None = None
        for it in sorted(row, key=lambda d: (d["x0"], d["kind"] == "letter")):
            if it["kind"] in ("num", "both"):
                cur = it["no"]
                if it["kind"] == "both":
                    hard = _assign(pairs, notes, cur, it["ch"], it["score"], it["text"]) or hard
            elif it["kind"] == "letter":
                if cur is None:
                    notes.append(f"y≈{it['yc']:.0f} 处有孤立字母 {it['text']!r}（左侧没有题号），忽略")
                    continue
                if cur in pairs:
                    # 题号已经有字母了，右边又冒出一个字母：多半是**那个字母的题号没被识别出来**
                    # （2024 第 17 题就是这样）。宁可少认一个，也不把它塞给上一题。
                    if pairs[cur][0] != it["ch"]:
                        notes.append(f"第 {cur} 题右边多出一个字母 {it['ch']}（{it['text']!r}），"
                                     f"疑似其自身题号未被识别，已忽略")
                    continue
                _assign(pairs, notes, cur, it["ch"], it["score"], it["text"])
    return pairs, notes, hard


def _assign(pairs, notes, no, ch, score, text) -> bool:
    """→ 是否遇到**结构性冲突**（同一题号被两次读成不同字母）。"""
    if no is None or ch is None:
        return False
    if no in pairs and pairs[no][0] != ch:
        notes.append(f"第 {no} 题有两个不同字母：{pairs[no][0]}（先前）/ {ch}（{text!r}），拒收")
        return True
    if no not in pairs or score > pairs[no][1]:
        pairs[no] = (ch, score)
    return False


def probe(engine, pdf: Path, max_pages: int = 3
          ) -> tuple[dict[int, str], dict, list[str], bool]:
    """→ ({题号: 字母}, 元信息, 说明, 是否凑齐 40)。

    同一页上**换几种裁法各认一遍**，再按「同题号同字母才收」合并：
      · 整条带（4 倍、6 倍）—— 默认；
      · 整条带横切成 3 条**有重叠**的窄带 —— 窄条会被识别器放大得更多，
        实测 2024 第 17 题那一格就是这样才读出来的（整条带上被水印笔画盖成 `17.℃`）。
    这些裁法读的是**同一份像素**，不算互相独立的证据，只算「同一路读法多试几次」；
    所以真正的独立证据仍只有两路（文字层表 / 页面 OCR），JSON 里逐题记 `from` 便于追责。
    """
    import pymupdf

    notes: list[str] = []
    best: tuple[dict, dict, list[str], bool] = ({}, {}, [], False)
    with pymupdf.open(str(pdf)) as doc:
        for pno in range(min(max_pages, doc.page_count)):
            passes: list[tuple[str, dict[int, tuple[str, float]]]] = []
            for zoom in ZOOM_LADDER:
                # a) 整条带：一次拿全表，也是「行位置」的来源
                boxes = ocr_boxes(engine, doc[pno], BAND, zoom)
                raw, why, complete = pairs_from_boxes(boxes)
                if complete:
                    return ({no: ch for no, (ch, _s) in raw.items()},
                            {"page": pno + 1, "zoom": zoom,
                             "conf": {no: round(sc, 3) for no, (_c, sc) in raw.items()},
                             "from": {no: [f"整条带·{zoom:g}×"] for no in raw}},
                            notes, True)
                if raw:
                    passes.append((f"整条带·{zoom:g}×", raw))
                else:
                    notes.append(f"第 {pno + 1} 页（整条带·{zoom:g}×）：" + "；".join(why))

                # b) 逐行窄带 + c) 三段重叠窄带：都只用来**补整条带漏掉的那几格**
                extra = [(f"第{i}行", r, True) for i, r in enumerate(row_strips(boxes), start=1)]
                extra += [(f"窄带{i}", r, False)
                          for i, r in enumerate(strip_bands(BAND), start=1)]
                for label, rect, one_row in extra:
                    rboxes = ocr_boxes(engine, doc[pno], rect, zoom)
                    if one_row:      # 逐行窄带：就一行，用「全读」而不是窗口搜索
                        rraw, rwhy = read_all_rows(rboxes)
                    else:
                        rraw, rwhy, _c = pairs_from_boxes(rboxes)
                    if rraw:
                        passes.append((f"{label}·{zoom:g}×", rraw))
                    elif not one_row:
                        notes.append(f"第 {pno + 1} 页（{label}·{zoom:g}×）：" + "；".join(rwhy))

                merged, mnotes, _ = merge_passes(passes)
                if len(merged) > len(best[0]):
                    info = {"page": pno + 1, "zoom": zoom,
                            "conf": {no: round(sc, 3) for no, (_c, sc, _l) in merged.items()},
                            "from": {no: labels for no, (_c, _s, labels) in merged.items()}}
                    best = ({no: ch for no, (ch, _c, _l) in merged.items()}, info,
                            notes + mnotes, False)
    if best[0]:
        return best[0], best[1], best[2], False
    return {}, {}, notes, False


def strip_bands(band, parts: int = 3, overlap: float = 0.25):
    """把整条带横切成 `parts` 条**有重叠**的窄带（重叠是为了不让任何一行正好落在切口上）。"""
    x0, y0, x1, y1 = band
    h = (y1 - y0) / parts
    ov = h * overlap
    for i in range(parts):
        yield (x0, max(y0, y0 + i * h - ov), x1, min(y1, y0 + (i + 1) * h + ov))


def row_strips(boxes, half: float = 15.0, max_rows: int = 10):
    """按整条带读到的框**逐行**切窄带（行中心 ±`half` 磅）。

    行位置直接取「整条带那一遍认出来的框」的 y 中心聚类 —— 不另猜版面，
    也不依赖各年 5 行 / 8 行的差别。窄带会被识别器放大得更多，
    整条带上被水印压糊的那一格（2024 第 17 题）在这里常能读出来。
    """
    ys = sorted((b[1] + b[3]) / 2 for b in boxes)
    rows: list[list[float]] = []
    for y in ys:
        if rows and y - rows[-1][-1] <= ROW_TOL:
            rows[-1].append(y)
        else:
            rows.append([y])
    x0, y0, x1, y1 = BAND
    for row in rows[:max_rows]:
        yc = sum(row) / len(row)
        yield (x0, max(y0, yc - half), x1, min(y1, yc + half))


def merge_passes(passes: list[tuple[str, dict[int, tuple[str, float]]]]
                 ) -> tuple[dict[int, tuple[str, float, list[str]]], list[str], bool]:
    """把若干次「同一页、不同裁法」的读数合并成 {题号: (字母, 最高置信度, [来源标签])}。

    硬规则：**同一题号被读成两个不同字母 → 该题留空并点名**（不取多数、不取高置信度）。
    只被一种裁法读到的题号照样收——但 `from` 里只有那一种裁法，人工一眼能看出这条证据薄。
    """
    votes: dict[int, dict[str, list[tuple[str, float]]]] = {}
    for label, raw in passes:
        for no, (ch, conf) in raw.items():
            votes.setdefault(no, {}).setdefault(ch, []).append((label, conf))
    merged: dict[int, tuple[str, float, list[str]]] = {}
    notes: list[str] = []
    for no in sorted(votes):
        cand = votes[no]
        if len(cand) > 1:
            notes.append(f"第 {no} 题在不同裁法下读成不同字母："
                         + "、".join(f"{ch}（{'/'.join(l for l, _c in v)}）"
                                     for ch, v in sorted(cand.items()))
                         + "，留空待人工核对")
            continue
        ch, lst = next(iter(cand.items()))
        merged[no] = (ch, max(c for _l, c in lst), [l for l, _c in lst])
    return merged, notes, set(merged) == set(range(1, NUM_LIMIT + 1))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paper")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--cross", action="store_true",
                    help="与 tools/answer_grid.py 的文字层结果逐题对照")
    args = ap.parse_args(argv)

    if args.all:
        pdfs = sorted((REPO / "sources" / "exams" / "answers").glob("*-answer.pdf"))
    elif args.paper:
        y = args.paper.split("/", 1)[1]
        pdfs = [REPO / "sources" / "exams" / "answers" / f"{y}-answer.pdf"]
    else:
        raise SystemExit("需要 --paper exams/YYYY 或 --all")

    ocr_runtime.ensure()
    import numpy  # noqa: F401  （确认 numpy 在位，报错比 onnxruntime 崩得更早更清楚）
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    bad = 0
    for pdf in pdfs:
        if not pdf.is_file():
            print(f"[grid-ocr] 缺底本：{pdf}")
            bad += 1
            continue
        got, info, notes, complete = probe(engine, pdf)
        seq = "".join(got.get(i, "?") for i in range(1, 41))
        ok = complete
        tag = "✅" if ok else ("⚠️" if got else "⛔")
        print(f"{tag} {pdf.name}  {seq}")
        for n in notes:
            print(f"    · {n}")
        if not ok:
            bad += 1
            # 读不齐也落盘：**局部结果照样能当作独立佐证**去核解析流取到的字母，
            # 但 JSON 里 `complete: false` 写死，调用方不许把它当权威。
        lows = sorted((c, no) for no, c in info["conf"].items() if c < 0.9)
        if lows:
            print(f"    · 置信度 <0.9 的 {len(lows)} 个："
                  + "、".join(f"第{no}题 {c:.2f}" for c, no in lows[:10]))
        ref = TEXT_GRID_ROOT / f"{pdf.stem}.json"
        if args.cross and ref.is_file():
            other = json.loads(ref.read_text(encoding="utf-8"))["answers"]
            common = [no for no in sorted(other, key=int) if int(no) in got]
            diff = [no for no in common if other[no] != got[int(no)]]
            if diff:
                print(f"    ⚠️ 与文字层表重叠 {len(common)} 格中不一致 {len(diff)} 题："
                      + "、".join(f"第{no}题 文字层{other[no]}/OCR{got[int(no)]}" for no in diff))
            else:
                print(f"    ✔ 与文字层表重叠的 {len(common)} 格全部一致")
        if args.write and got:
            dst = OUT_ROOT / f"{pdf.stem}.json"
            payload = {"paper": pdf.stem, "source": "ocr-render", "complete": ok,
                       "page": info.get("page"), "zoom": info.get("zoom"),
                       "answers": got, "conf": info.get("conf"),
                       "from": info.get("from"), "band": list(BAND)}
            dst.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"    → {dst}")
    print(f"[grid-ocr] {len(pdfs)} 卷，读不出整表 {bad} 卷")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
