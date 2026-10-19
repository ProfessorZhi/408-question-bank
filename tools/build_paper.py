#!/usr/bin/env python3
"""从 questions.md / solutions.md 构建可直接使用的学生卷和教师卷。

默认 --all 只构建 README 承诺的 v1 范围：2009-2025 真题 + 2027 四套模拟卷
（21 卷、42 个输出）。2026 真题须显式加 --include-2026。

构建严格校验题号及图片路径；任何失败都返回非零退出码。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qa_paper import RE_ANSWER, RE_FENCE, RE_LEAK, RE_QHEAD  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
RE_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
RE_IMG_LINK = re.compile(r"(!\[[^\]]*\]\()([^\s)]+)([^)]*\))")
EXPECTED_NUMBERS = set(range(1, 48))


class BuildError(ValueError):
    """试卷缺件或生成校验失败。"""


def read(path: Path) -> str:
    if not path.is_file():
        raise BuildError(f"文件不存在：{path}")
    return path.read_text(encoding="utf-8")


def _blank_preserving_lines(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", " ", match.group(0))


def masked_headings(text: str) -> str:
    """仅用于查找标题；掩码保持原始字符偏移，不改动要输出的正文。"""
    result = RE_FENCE.sub(_blank_preserving_lines, text)
    return RE_HTML_COMMENT.sub(_blank_preserving_lines, result)


def sections(text: str) -> dict[int, str]:
    """按真正的题号标题分段，保留围栏代码和原有 Markdown。"""
    marks = list(RE_QHEAD.finditer(masked_headings(text)))
    found: dict[int, str] = {}
    for i, m in enumerate(marks):
        n = int(m.group(1))
        if n in found:
            raise BuildError(f"重复的第 {n} 题标题")
        stop = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        found[n] = text[m.end():stop]
    return found


def require_complete(parts: dict[int, str], name: str) -> None:
    present = set(parts)
    if present != EXPECTED_NUMBERS:
        missing = sorted(EXPECTED_NUMBERS - present)
        extra = sorted(present - EXPECTED_NUMBERS)
        raise BuildError(f"{name} 不是 47 题：缺 {missing}，多 {extra}")
    blank = [n for n, body in parts.items()
             if not body.strip() or "本题未从底本切出" in body]
    if blank:
        raise BuildError(f"{name} 有空题或转录占位：{sorted(blank)}")


def header(paper_dir: Path, kind: str) -> str:
    name = paper_dir.relative_to(REPO).as_posix()
    title = {"student": "学生卷（无答案）", "teacher": "教师卷（含答案与解析）"}[kind]
    inputs = "questions.md" if kind == "student" else "questions.md + solutions.md"
    return (f"# {name} · {title}\n\n"
            f"> 由 tools/build_paper.py 生成，请勿手工编辑。\n"
            f"> 来源：{name}/{inputs}\n\n")


def rewrite_images(text: str, paper_dir: Path, out_dir: Path) -> str:
    """重新基于最终输出位置定位本地图片，阻止缺图和外链。"""
    fences = [(m.start(), m.end()) for m in RE_FENCE.finditer(text)]

    def replace(match: re.Match[str]) -> str:
        if any(a <= match.start() < b for a, b in fences):
            return match.group(0)  # 示例代码块里的 Markdown 不能修改
        raw = match.group(2)
        if raw.startswith(("/", "\\")) or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", raw):
            raise BuildError(f"禁止绝对路径或外链图片：{raw}")
        target = (paper_dir / raw).resolve()
        if not target.is_file():
            raise BuildError(f"图片不存在：{raw}（{paper_dir}）")
        relative = Path(os.path.relpath(target, out_dir.resolve())).as_posix()
        return match.group(1) + relative + match.group(3)

    return RE_IMG_LINK.sub(replace, text)


def build(paper_dir: Path, kind: str, out_dir: Path | None = None) -> str:
    if kind not in ("student", "teacher"):
        raise BuildError(f"未知构建类型：{kind}")
    target_dir = out_dir if out_dir is not None else REPO / "build"
    qtext = read(paper_dir / "questions.md")
    qs = sections(qtext)
    require_complete(qs, "questions.md")

    if kind == "student":
        body = RE_HTML_COMMENT.sub("", qtext)
        leaks = RE_LEAK.findall(body)
        if leaks:
            raise BuildError(f"学生卷有疑似答案泄漏：{leaks[:5]}")
        result = header(paper_dir, kind) + body.lstrip()
    else:
        ss = sections(read(paper_dir / "solutions.md"))
        require_complete(ss, "solutions.md")
        no_key = [n for n in range(1, 41) if not RE_ANSWER.search(ss[n])]
        if no_key:
            raise BuildError(f"解析中缺少选择题答案字母：{no_key}")
        out = [header(paper_dir, kind)]
        for n in range(1, 48):
            out.append(f"### 第 {n} 题\n{qs[n].strip()}\n\n"
                       f"**解析**\n{ss[n].strip()}\n\n---\n")
        result = "\n".join(out)
    return rewrite_images(result, paper_dir, target_dir)


def v1_targets(include_2026: bool = False) -> list[Path]:
    """显式列出 v1 卷，避免 --all 悄悄扩大范围。"""
    years = range(2009, 2027 if include_2026 else 2026)
    return ([REPO / "papers" / "exams" / str(y) for y in years]
            + [REPO / "papers" / "mock-2027" / f"set-{n}"
               for n in range(1, 5)])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paper", nargs="?", help="单卷目录")
    ap.add_argument("--all", action="store_true", help="构建 v1 21 卷")
    ap.add_argument("--include-2026", action="store_true",
                    help="配合 --all 额外构建 2026 真题（共 22 卷）")
    ap.add_argument("--student", action="store_true")
    ap.add_argument("--teacher", action="store_true")
    ap.add_argument("--both", action="store_true")
    ap.add_argument("-o", "--out", default="build")
    args = ap.parse_args(argv)

    if args.all and args.paper:
        ap.error("--all 不接受单卷目录")
    if args.include_2026 and not args.all:
        ap.error("--include-2026 只能配合 --all")
    kinds = (["student", "teacher"] if args.both else
             [k for k, enabled in (("student", args.student), ("teacher", args.teacher))
              if enabled])
    if not kinds:
        ap.error("至少指定 --student / --teacher / --both")
    if args.all:
        targets = v1_targets(include_2026=args.include_2026)
    else:
        if not args.paper:
            ap.error("需要卷目录或 --all")
        targets = [(REPO / args.paper).resolve()]

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = REPO / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    built, failed = 0, 0

    for paper_dir in targets:
        for kind in kinds:
            try:
                content = build(paper_dir, kind, out_dir)
                filename = paper_dir.relative_to(REPO).as_posix().replace("/", "-")
                output = out_dir / f"{filename}-{kind}.md"
                output.write_text(content, encoding="utf-8", newline="\n")
                built += 1
                print(f"[build] {output}（{len(content):,} 字符）")
            except (BuildError, OSError, ValueError) as exc:
                failed += 1
                print(f"[build] ⛔ {paper_dir} / {kind}: {exc}", file=sys.stderr)

    expected = len(targets) * len(kinds)
    print(f"[build] 成功 {built}/{expected} 份，失败 {failed} 份。")
    return 0 if built == expected and failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
