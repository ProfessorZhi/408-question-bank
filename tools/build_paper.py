#!/usr/bin/env python3
"""从 questions.md / solutions.md 生成学生卷与教师卷。

- 学生卷：只有题干与选项；**强制剔除**任何答案痕迹（并做一次反向自检）。
- 教师卷：题干 + 同号解析，逐题相邻，便于讲评。

用法：
  python tools/build_paper.py papers/mock-2027/set-1 --student -o build/
  python tools/build_paper.py papers/mock-2027/set-1 --teacher -o build/
  python tools/build_paper.py --all --both -o build/
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qa_paper import RE_QHEAD, split_by_question, strip_fences  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
RE_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
RE_LEAK = re.compile(r"(正确答案|参考答案|答案\s*[：:]\s*[A-D]\b)", re.M | re.I)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def header(paper_dir: Path, kind: str) -> str:
    name = paper_dir.relative_to(REPO).as_posix()
    title = {"student": "学生卷（无答案）", "teacher": "教师卷（含答案与解析）"}[kind]
    return (f"# {name} · {title}\n\n"
            f"> 由 `tools/build_paper.py` 生成，请勿手工编辑。\n"
            f"> 源：`{name}/questions.md`"
            + ("、`solutions.md`\n\n" if kind == "teacher" else "\n\n"))


def build(paper_dir: Path, kind: str) -> str:
    qtext = read(paper_dir / "questions.md")
    if not qtext:
        raise SystemExit(f"[build] 缺少 {paper_dir}/questions.md")

    if kind == "student":
        body = RE_HTML_COMMENT.sub("", qtext)
        leaks = RE_LEAK.findall(strip_fences(body))
        if leaks:
            raise SystemExit(
                f"[build] ⛔ 学生卷检出答案痕迹 {len(leaks)} 处，已中止：{leaks[:5]}\n"
                f"        请先修 questions.md（见 docs/qa-policy.md C8）。")
        return header(paper_dir, kind) + body.lstrip()

    # teacher：按题号把解析插到对应题干之后
    stext = read(paper_dir / "solutions.md")
    qs = split_by_question(strip_fences(qtext))
    ss = split_by_question(strip_fences(stext))
    if not ss:
        raise SystemExit(f"[build] 缺少 {paper_dir}/solutions.md，无法生成教师卷")

    out = [header(paper_dir, kind)]
    order = sorted(set(qs) | set(ss))
    missing = [n for n in order if n not in ss]
    for n in order:
        if n in qs:
            out.append(f"### 第 {n} 题\n{qs[n].strip()}\n")
        if n in ss:
            out.append(f"\n**解析**\n{ss[n].strip()}\n")
        out.append("\n---\n")
    if missing:
        out.append(f"\n> ⚠️ 以下题号缺解析：{missing}\n")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paper", nargs="?", help="卷目录")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--student", action="store_true")
    ap.add_argument("--teacher", action="store_true")
    ap.add_argument("--both", action="store_true")
    ap.add_argument("-o", "--out", default="build")
    args = ap.parse_args(argv)

    kinds = []
    if args.student:
        kinds.append("student")
    if args.teacher:
        kinds.append("teacher")
    if args.both:
        kinds = ["student", "teacher"]
    if not kinds:
        ap.error("至少给一个 --student / --teacher / --both")

    if args.all:
        targets = []
        for base in (REPO / "papers").glob("*"):
            if base.is_dir():
                targets += [d for d in base.iterdir()
                            if d.is_dir() and not d.name.startswith("_")]
    else:
        if not args.paper:
            ap.error("需要卷目录，或用 --all")
        targets = [REPO / args.paper]

    outdir = Path(args.out)
    if not outdir.is_absolute():
        outdir = REPO / outdir
    outdir.mkdir(parents=True, exist_ok=True)

    built = 0
    for d in sorted(targets):
        for k in kinds:
            try:
                text = build(d, k)
            except SystemExit as exc:
                print(str(exc))
                continue
            name = d.relative_to(REPO).as_posix().replace("/", "-")
            dst = outdir / f"{name}-{k}.md"
            dst.write_text(text, encoding="utf-8", newline="\n")
            print(f"[build] {dst}  ({len(text):,} 字符)")
            built += 1
    print(f"[build] 共 {built} 份。")
    return 0 if built else 1


if __name__ == "__main__":
    sys.exit(main())
