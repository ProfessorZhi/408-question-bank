#!/usr/bin/env python3
"""为每卷生成 papers/<id>/meta.yml 骨架（幂等，已存在则跳过）。

来源与 sha256 取自 index/sources-manifest.json（先跑 tools/inventory.py）。
逐题状态一律 `pending` —— **本脚本不判断、不猜测任何内容**，
它只把「有哪些卷、每卷的底本是谁」落成结构化数据。

用法：
  python tools/inventory.py
  python tools/bootstrap_meta.py
  python tools/bootstrap_meta.py --force     # 覆盖已存在的 meta.yml（慎用）
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
EXAM_YEARS = list(range(2009, 2026))          # 2009—2025
MOCK_SETS = [1, 2, 3, 4]

NEVILLE = "https://github.com/neville-studio/408-exam-paper"
NEVILLE_SHA = "44302e5bc425ed63d48186ec4ab3c342fac051eb"


def manifest_index() -> dict[str, dict]:
    p = REPO / "index" / "sources-manifest.json"
    if not p.is_file():
        raise SystemExit("[bootstrap] 先跑 python tools/inventory.py")
    data = json.loads(p.read_text(encoding="utf-8"))
    return {r["path"]: r for r in data["files"]}


def role_of(path: str) -> str:
    """按文件用途判角色。注意 mock 卷路径里没有 'papers/' 段。"""
    name = path.rsplit("/", 1)[-1]
    if name.endswith("-paper.pdf") or "/papers/" in path:
        return "paper"
    if name.endswith(("-answer.pdf", "-solution.pdf")):
        return "answer"
    return "reference"


def yaml_block(rec: dict | None, path: str, *, conf: str, upstream: str | None,
               commit: str | None, license_: str) -> str:
    sha = rec["sha256"] if rec else "0" * 64
    probe = (rec or {}).get("probe", "unknown")
    note = ""
    if rec and (rec.get("text_chars") or 0) < 200:
        note = "，无文本层需 OCR"
        conf = "low"
    lines = [
        f"  - role: {role_of(path)}",
        f"    path: {path}",
        f'    sha256: "{sha}"',
        f"    upstream: {upstream if upstream else 'null'}",
        f"    upstream_commit: {commit if commit else 'null'}",
        f"    license: \"{license_}\"",
        f"    confidence: {conf}   # probe={probe}{note}",
    ]
    return "\n".join(lines)


def emit(paper_id: str, kind: str, title: str, year: int | None,
         srcs: list[str], idx: dict[str, dict]) -> str:
    blocks = []
    role_meta = []
    for path in srcs:
        rec = idx.get(path)
        if "exams/" in path:
            role_meta.append((path, "medium", NEVILLE, NEVILLE_SHA,
                              "MIT (covers upstream typesetting only; see docs/rights-and-licenses.md §1)"))
        else:
            role_meta.append((path, "low", None, None,
                              "user-provided; all rights reserved by owner; private study use"))
    for path, conf, up, commit, lic in role_meta:
        blocks.append(yaml_block(idx.get(path), path, conf=conf,
                                 upstream=up, commit=commit, license_=lic))

    # 注意：键名 no 必须加引号。YAML 1.1 里未加引号的 `no` 会被解析成布尔 False，
    # 生成 {"no": 1} 之外还会静默丢掉题号——这个坑已被 schema 校验抓到一次。
    qlist = "\n".join(
        f'  - {{"no": {n}, status: pending, confidence: null, topic: 未知, notes: ""}}'
        for n in range(1, 48))

    return f"""# 生成物骨架 —— 由 tools/bootstrap_meta.py 生成后**人工维护**。
# 逐题状态机见 docs/qa-policy.md；schema 见 schema/paper-meta.schema.json。
paper_id: {paper_id}
title: {title}
year: {year if year else 'null'}
kind: {kind}
sources:
{chr(10).join(blocks)}
extraction:
  method: pending        # text-layer | ocr | manual | mixed
  tool: null
  date: null
counts:
  choice: 40
  comprehensive: 7
  total: 47
questions:
{qlist}
errata: []
review:
  proofread_by: []
  proofread_at: null
  qa: null
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    idx = manifest_index()
    made = skipped = 0

    for y in EXAM_YEARS:
        d = REPO / "papers" / "exams" / str(y)
        d.mkdir(parents=True, exist_ok=True)
        f = d / "meta.yml"
        if f.exists() and not args.force:
            skipped += 1
            continue
        f.write_text(emit(f"exams/{y}", "exam",
                          f"{y} 年全国硕士研究生招生考试 计算机学科专业基础综合",
                          y,
                          [f"sources/exams/papers/{y}.pdf",
                           f"sources/exams/answers/{y}-answer.pdf"], idx),
                     encoding="utf-8", newline="\n")
        made += 1

    for n in MOCK_SETS:
        d = REPO / "papers" / "mock-2027" / f"set-{n}"
        d.mkdir(parents=True, exist_ok=True)
        f = d / "meta.yml"
        if f.exists() and not args.force:
            skipped += 1
            continue
        f.write_text(emit(f"mock-2027/set-{n}", "mock",
                          f"2027 考研 408 模拟卷 {n}", None,
                          [f"sources/mock-2027/pdf/mock2027-set{n}-paper.pdf",
                           f"sources/mock-2027/pdf/mock2027-set{n}-solution.pdf"], idx),
                     encoding="utf-8", newline="\n")
        made += 1

    print(f"[bootstrap] 新建 {made} 份 meta.yml，跳过已存在 {skipped} 份。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
