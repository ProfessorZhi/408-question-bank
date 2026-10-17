#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""answer_grid_visual.py —— **人工直读**答案表：把卷首那条带渲染成图，人眼逐格读。

为什么还要第三路
----------------
前两路（`answer_grid.py` 读文字层 / `answer_grid_ocr.py` 读页面像素）在 2009—2018
这批卷子上都奏效，但有一批卷子**两路都用不上或只剩一路**：

  · 2019/2021/2024/2025/2026 的答案卷**整本都是扫描件**（全文档文字层 0 字符），
    文字层那路天生无从下手，只剩 OCR 单通道；
  · 2009/2014 的文字层里夹着扫描自带的 `HiddenHorzOCR` 噪声层（把表读成 `CBAAB 4.`
    这种 5 字母碎片），按 x 聚列的读法直接拒收 → 也只剩 OCR 单通道；
  · 2013 第 18 题在 OCR 的几种裁法下读成 C/D 两个不同字母，被合并规则丢弃，
    于是那一格只剩文字层单通道。

用户对扫描件的要求是「先保留页图和 OCR 初稿，然后**人工/多通道核验**」——
本工具就是那个「人工」通道，并且把它做成**可复现、可追责**的：

  · 裁带坐标、缩放倍率**写死在本文件里**（就是当时读的那张图）；
  · `--render` 能按同样的参数把那张图重新渲染出来，任何人都能自己再读一遍；
  · 落盘 JSON 里带渲染图的 sha256 —— 图和读数对不上时能被发现。

读数本身是**人眼读出来的**（不是脚本算的），所以：
  · 只做**形状校验**（必须 40 个字符、只能是 A–D），绝不"补全"或"纠错"；
  · 读数与裁带一一对应；换裁带必须重新读、重新登记，不许沿用旧读数。

用法
----
    python -I tools/answer_grid_visual.py --render            # 重新渲染并落盘证据
    python -I tools/answer_grid_visual.py --check exams/2013  # 只校验某一卷的形状
    python -I tools/answer_grid_visual.py --check mock-2027/set-2

读数对象（key）
---------------
  · 真题 `2019`              → `sources/exams/answers/2019-answer.pdf`
  · 模拟卷 `mock-2027/set-2` → `sources/mock-2027/pdf/mock2027-set2-solution.pdf`
落盘名 `build/_scratch/answer-visual/<stem>.json`（真题 `2019-answer.json`、
模拟卷 `mock2027-set2-solution.json`），`tools/md_solutions.py` 的 `load_grid` 按这个名字取。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parent.parent
OUT_ROOT = REPO / "build" / "_scratch" / "answer-visual"

# ── 裁带：**读的时候用的就是这些坐标**（磅）。页面尺寸一并登记，页面变了就不许沿用。──
# 2024/2025/2026 是同版式（595.32×841.92），用同一条绝对带；其余按各自页宽给出。
BANDS: dict[str, tuple[tuple[float, float, float, float], tuple[float, float], float]] = {
    # 年份: (裁带 x0,y0,x1,y1), (页宽, 页高), 缩放
    "2009": ((15.6, 100.7, 516.5, 447.5), (519.1, 745.9), 3.4),
    "2010": ((53.7, 155.3, 501.5, 266.4), (519.95, 746.40), 4.0),
    "2011": ((45.0, 140.0, 500.0, 232.0), (516.70, 742.55), 5.0),
    "2012": ((42.3, 188.5, 456.3, 300.2), (517.20, 744.00), 4.0),
    "2013": ((15.5, 74.4, 512.9, 409.2), (515.5, 744.0), 3.6),
    "2014": ((15.5, 100.6, 514.6, 447.1), (517.2, 745.1), 3.4),
    "2019": ((14.1, 95.5, 468.5, 424.2), (470.88, 707.04), 3.4),
    "2021": ((15.5, 98.4, 513.3, 437.1), (515.88, 728.52), 3.4),
    "2024": ((14.0, 112.0, 588.0, 418.0), (595.32, 841.92), 3.0),
    "2025": ((14.0, 112.0, 588.0, 418.0), (595.32, 841.92), 3.0),
    "2026": ((14.0, 112.0, 588.0, 418.0), (595.32, 841.92), 3.0),
    # 2027 模拟卷（整本扫描件，和 2019/2024—2026 一样只剩直读这一路）。
    # 版式与真题不同：这张表是 **10 列 × 4 行**、题号与字母同框，行优先读
    # （01—10 / 11—20 / 21—30 / 31—40），表格下方紧接着就是逐题解析。
    # 页面是 515.88×728.52（与 2021 卷同尺寸）。
    "mock-2027/set-2": ((40.0, 115.0, 516.0, 220.0), (515.88, 728.52), 4.0),
}

# ── 读数：人眼逐格读出，按「行优先、每行从左到右」拼成 40 个字母。──
# 登记时每一卷都同时记下「当时看到的行结构」，方便日后再看时核对分格有没有错位。
VISUAL_READS: dict[str, tuple[str, list[str]]] = {
    # 8 列 × 5 行
    "2009": ("BCDBCBADABCDDCDCAADBDADDCACBAABABBCADDCA",
             ["BCDBCBAD", "ABCDDCDC", "AADBDADD", "CACBAABA", "BBCADDCA"]),
    # 2010/2011/2012 的**文字层与 OCR 两路本来就一致**；2026-10-17 补读这三卷，
    # 图的是另一件事：核对「格子→题号」的映射本身有没有错位（两路产物是同一套版式
    # 常数算出来的，在映射这一维上并不独立）。三卷直读结果与两路产物**逐位相同**。
    "2010": ("DCDCBACBBDADBBDADBADADACBADBBCCBCCDCBDAA",
             ["DCDCBACB", "BDADBBDA", "DBADADAC", "BADBBCCB", "CCDCBDAA"]),
    "2011": ("ABBCCDACDABDABDACDCCDCBADBDDACBCABBDDCCB",
             ["ABBCCDAC", "DABDABDA", "CDCCDCBA", "DBDDACBC", "ABBDDCCB"]),
    "2012": ("BAABCCCADADDBDDACCCDDBCBBADABCABBCABCADD",
             ["BAABCCCA", "DADDBDDA", "CCCDDBCB", "BADABCAB", "BCABCADD"]),
    "2013": ("DCDBACCDCACCAACADCBBBDAACACBDBBBBADBABBA",
             ["DCDBACCD", "CACCAACA", "DCBBBDAA", "CACBDBBB", "BADBABBA"]),
    "2014": ("CBADCDDDDBCDCAADACCCDBABDAACBACDCBDCBABD",
             ["CBADCDDD", "DBCDCAAD", "ACCCDBAB", "DAACBACD", "CBDCBABD"]),
    "2019": ("BBCACADCBDBCADDDBCBCADBCCBCBCBACCABBBCDB",
             ["BBCACADC", "BDBCADDD", "BCBCADBC", "CBCBCBAC", "CABBBCDB"]),
    "2021": ("DDBCBDACACBDDACADCCABABBCCDCBACCBABBDBDC",
             ["DDBCBDAC", "ACBDDACA", "DCCABABB", "CCDCBACC", "BABBDBDC"]),
    # 5 列 × 8 行（2024 起的版式，题号与字母同框）
    "2024": ("DAABDADABCDBBCDDCBCBACAADAABACCCBCDBDDCD",
             ["DAABD", "ADABC", "DBBCD", "DCBCB", "ACAAD", "AABAC", "CCBCD", "BDDCD"]),
    "2025": ("BDDBDCCCADADDDCBCBAABADCCBDCCACBBCCCBABA",
             ["BDDBD", "CCCAD", "ADDDC", "BCBAA", "BADCC", "BDCCA", "CBBCC", "CBABA"]),
    "2026": ("ADCBDDBDBAACABADACAADCCDDACCDBDDBDBBBACD",
             ["ADCBD", "DBDBA", "ACABA", "DACAA", "DCCDD", "ACCDB", "DDBDB", "BBACD"]),
    # 2027 模拟卷（10 列 × 4 行）
    # 2026-10-17 读 set-2：裁带图 `build/_scratch/answer-visual/mock2027-set2-solution-band.png`
    # （x40—516 / y115—220 @ 4.0×，页 515.88×728.52）逐格读出。
    # 与逐题解析流那一路**逐位相同**（见 `build/_scratch/reports/mock-2027-set-2-solutions.md`），
    # 也回填了只有单路命中的第 18 题（解析流单路给 D，本表直读亦为 D）。
    "mock-2027/set-2": ("DDBCDDDACAACABBCCDDCBBCACDDDBCACDBBCDDBB",
                        ["DDBCDDDACA", "ACABBCCDDC", "BBCACDDDBC", "ACDBBCDDBB"]),
}


def validate(year: str) -> list[str]:
    """形状校验：40 个字符、只能 A–D、且与分行登记自洽。"""
    errs: list[str] = []
    s, rows = VISUAL_READS[year]
    if len(s) != 40:
        errs.append(f"{year}: 读数是 {len(s)} 个字母（应为 40）")
    bad = sorted({c for c in s if c not in "ABCD"})
    if bad:
        errs.append(f"{year}: 读数里有非 A–D 字符 {bad}")
    if "".join(rows) != s:
        errs.append(f"{year}: 分行登记与整串不一致（{''.join(rows)!r} ≠ {s!r}）")
    if not all(r and set(r) <= set("ABCD") for r in rows):
        errs.append(f"{year}: 有行含非 A–D 字符")
    return errs


def source_pdf(key: str) -> Path:
    """读数对象（key）→ 底本 PDF。

    key 两种写法：
      · `2019`            —— 真题卷，读 `sources/exams/answers/2019-answer.pdf`；
      · `mock-2027/set-2` —— 2027 模拟卷，读 `sources/mock-2027/pdf/mock2027-set2-solution.pdf`。
    模拟卷的答案卷**整本是扫描件**（文字层 0 字符），与 2019/2024—2026 一样只剩
    「人工直读」这一路，所以并到同一个工具里、同一套证据格式。
    """
    if "/" in key:
        kind, rest = key.split("/", 1)
        if kind != "mock-2027":
            raise SystemExit(f"[visual] 不认识的读数对象：{key}")
        return (REPO / "sources" / "mock-2027" / "pdf"
                / f"mock2027-set{rest.split('-')[1]}-solution.pdf")
    return REPO / "sources" / "exams" / "answers" / f"{key}-answer.pdf"


def out_stem(key: str) -> str:
    """读数对象的输出来源名：真题 `2019-answer` / 模拟卷 `mock2027-set2-solution`。

    `tools/md_solutions.py` 的 `load_grid` 按这个名字去 `answer-visual/` 里找
    `<stem>.json`，所以两边必须**逐字一致**（改这里要同步改那边）。
    """
    if "/" in key:
        _kind, rest = key.split("/", 1)          # rest = `set-2`（不能拿整串 split('-')：
        return f"mock2027-set{rest.split('-')[1]}-solution"   # `mock-2027/set-2` 会切出 `2027/set`）
    return f"{key}-answer"


def render(key: str, force: bool = False) -> tuple[Path, str]:
    """按登记的裁带重新渲染那张图 → (图路径, sha256)。已有且参数一致就直接复用。"""
    import pymupdf

    band, (pw, ph), zoom = BANDS[key]
    pdf = source_pdf(key)
    if not pdf.is_file():
        raise SystemExit(f"[visual] 缺底本：{pdf}")
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    # 真题的图名一直是 `<年>-band.png`（历史证据文件就叫这个名，不改），模拟卷用 stem
    shot = OUT_ROOT / ((f"{out_stem(key)}-band.png") if "/" in key else f"{key}-band.png")
    with pymupdf.open(str(pdf)) as doc:
        page = doc[0]
        # 页面尺寸对不上 → 登记的裁带就不是这张图上的位置，宁可报错也不许沿用
        if abs(page.rect.width - pw) > 0.6 or abs(page.rect.height - ph) > 0.6:
            raise SystemExit(f"[visual] {key} 第 1 页尺寸变成了 "
                             f"{page.rect.width:.1f}×{page.rect.height:.1f}，"
                             f"登记的是 {pw}×{ph}；裁定要重读，不许沿用旧读数")
        if force or not shot.is_file():
            pix = page.get_pixmap(clip=pymupdf.Rect(*band),
                                  matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            pix.save(str(shot))
    return shot, hashlib.sha256(shot.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--render", action="store_true", help="重新渲染裁带图并落盘证据 JSON")
    ap.add_argument("--check", metavar="exams/YYYY", help="只校验某一卷的读数形状")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    bad = 0
    for year in sorted(VISUAL_READS):
        for e in validate(year):
            print(f"⛔ {e}")
            bad += 1
    if bad:
        return 1

    if args.check:
        # `--check exams/2013`（真题）或 `--check mock-2027/set-2`（模拟卷）
        key = args.check if args.check.startswith("mock-") else args.check.split("/", 1)[1]
        s, rows = VISUAL_READS[key]
        print(f"✅ {key}: {len(s)}/40 个字母，分行 {len(rows)} 行、共 {len(''.join(rows))} 字符")
        return 0

    if not args.render:
        print(f"[visual] {len(VISUAL_READS)} 卷读数形状合法："
              + "、".join(sorted(VISUAL_READS)))
        return 0

    for key in sorted(VISUAL_READS):
        s, rows = VISUAL_READS[key]
        shot, sha = render(key, force=args.force)
        band, (pw, ph), zoom = BANDS[key]
        dst = OUT_ROOT / f"{out_stem(key)}.json"
        dst.write_text(json.dumps({
            "paper": out_stem(key), "source": "human-visual",
            "page": 1, "answers": {str(i + 1): c for i, c in enumerate(s)},
            "rows": rows,
            "evidence": {"image": f"build/_scratch/answer-visual/{shot.name}",
                         "image_sha256": sha, "band": list(band),
                         "page_size": [pw, ph], "zoom": zoom},
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"✅ {key}: {s}  ← {shot.name} (sha256 {sha[:12]}…)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
