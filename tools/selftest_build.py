#!/usr/bin/env python3
"""构建器回归测试和 v1 42 份生成物验收（无外部测试框架依赖）。

运行:
  python tools/selftest_build.py
  python tools/selftest_build.py --verify-built /tmp/408-v1-build
"""
from __future__ import annotations

import argparse
import contextlib
import io
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_paper as bp  # noqa: E402


def make_paper(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "assets").mkdir(exist_ok=True)
    (path / "assets" / "q2.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (path / "assets" / "q41.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    fence = chr(96) * 3
    q = ["# 自测题目\n"]
    s = ["# 自测解析\n"]
    for n in range(1, 48):
        qpart = f"### 第 {n} 题\n\n题干 {n}。\n"
        if n <= 40:
            qpart += "\nA. 甲\nB. 乙\nC. 丙\nD. 丁\n"
        if n == 1:
            qpart += ("\n" + fence + "c\nint f(void) { return 42; }\n"
                      "### 第 99 题\n" + fence + "\n")
        if n == 2:
            qpart += "\n![题图](assets/q2.png)\n"
        q.append(qpart)
        spart = f"### 第 {n} 题\n\n"
        if n <= 40:
            spart += "答案：A\n"
        if n == 41:
            spart += "\n![解析图](assets/q41.png)\n"
        if n == 42:
            spart += ("\n" + fence + "c\nint solve(void) { return 7; }\n"
                      "### 第 99 题\n" + fence + "\n")
        spart += "解析正文。\n"
        s.append(spart)
    (path / "questions.md").write_text("\n".join(q), encoding="utf-8")
    (path / "solutions.md").write_text("\n".join(s), encoding="utf-8")


def check_image_links(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    fences = [(m.start(), m.end()) for m in bp.RE_FENCE.finditer(text)]
    for m in bp.RE_IMG_LINK.finditer(text):
        if any(a <= m.start() < b for a, b in fences):
            continue
        target = (path.parent / m.group(2)).resolve()
        assert target.is_file(), f"{path.name}: 图片路径失效：{m.group(2)}"


def verify_generated(out_dir: Path, *, include_2026: bool = False) -> None:
    target_names = {
        f"{p.relative_to(bp.REPO).as_posix().replace('/', '-')}-{kind}.md"
        for p in bp.v1_targets(include_2026=include_2026)
        for kind in ("student", "teacher")
    }
    got = {p.name for p in out_dir.glob("*.md")}
    assert got == target_names, (
        f"构建文件集不一致：应有 {len(target_names)} 份；"
        f"缺 {sorted(target_names - got)}；多 {sorted(got - target_names)}"
    )
    for path in out_dir.glob("*.md"):
        body = path.read_text(encoding="utf-8")
        nums = [int(m.group(1))
                for m in bp.RE_QHEAD.finditer(bp.masked_headings(body))]
        assert nums == list(range(1, 48)), f"{path.name}: 题号不完整或不连续"
        check_image_links(path)
        if path.name.endswith("-student.md"):
            assert not bp.RE_LEAK.search(bp.RE_HTML_COMMENT.sub("", body)), (
                f"{path.name}: 发现疑似答案泄漏"
            )
        else:
            assert body.count("**解析**") == 47, f"{path.name}: 解析条目不足 47"
    print(f"[build-selftest] 已验收 {len(got)} 份，题号、答案分离和图片路径均通过")


def must_fail(call, description: str) -> None:
    try:
        call()
    except bp.BuildError:
        return
    raise AssertionError(f"本应失败却成功：{description}")


def selftest() -> None:
    with tempfile.TemporaryDirectory(prefix="408-build-selftest-") as tmp:
        root = Path(tmp)
        old_repo = bp.REPO
        bp.REPO = root
        try:
            for target in bp.v1_targets(include_2026=True):
                make_paper(target)
            paper = root / "papers" / "exams" / "2009"
            out = root / "output-v1"
            student = bp.build(paper, "student", out)
            teacher = bp.build(paper, "teacher", out)
            fence = chr(96) * 3
            assert fence + "c" in student, "学生卷丢失 C 程序"
            assert "int f(void)" in student, "学生卷代码内容丢失"
            assert "int solve(void)" in teacher, "教师卷解析中的代码内容丢失"
            assert "### 第 99 题" in teacher, "教师卷代码块被误修改"
            assert len(bp.sections(teacher)) == 47, "代码中的假题号被误识别"
            assert "答案：A" in teacher and "答案：A" not in student
            assert "../papers/exams/2009/assets/q2.png" in student
            assert "../papers/exams/2009/assets/q41.png" in teacher

            with contextlib.redirect_stdout(io.StringIO()):
                assert bp.main(["--all", "--both", "-o", str(out)]) == 0
            verify_generated(out)

            extra = root / "output-with-2026"
            with contextlib.redirect_stdout(io.StringIO()):
                assert bp.main(["--all", "--both", "--include-2026",
                                "-o", str(extra)]) == 0
            verify_generated(extra, include_2026=True)

            qfile = paper / "questions.md"
            original_q = qfile.read_text(encoding="utf-8")
            qfile.write_text(original_q + "\n正确答案：B\n", encoding="utf-8")
            must_fail(lambda: bp.build(paper, "student", out), "答案泄漏")
            qfile.write_text(original_q.replace("### 第 47 题", "### 第 48 题"),
                             encoding="utf-8")
            must_fail(lambda: bp.build(paper, "student", out), "题号缺失/越界")
            qfile.write_text(original_q, encoding="utf-8")
            (paper / "assets" / "q2.png").unlink()
            must_fail(lambda: bp.build(paper, "student", out), "缺少题图")

            missing = root / "papers" / "exams" / "2010" / "solutions.md"
            missing.unlink()
            with (contextlib.redirect_stdout(io.StringIO()),
                  contextlib.redirect_stderr(io.StringIO())):
                code = bp.main(["--all", "--both", "-o", str(root / "partial")])
            assert code == 1, "部分失败必须使整批返回失败"
        finally:
            bp.REPO = old_repo
    print("[build-selftest] 回归样本通过：代码围栏、图片、范围、泄漏与失败传播")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-built", type=Path, help="验收真实生成目录")
    ap.add_argument("--include-2026", action="store_true",
                    help="验收时一并包含额外的 2026 卷")
    args = ap.parse_args()
    try:
        if args.verify_built:
            verify_generated(args.verify_built, include_2026=args.include_2026)
        else:
            selftest()
    except (AssertionError, bp.BuildError, OSError) as exc:
        print(f"[build-selftest] FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
