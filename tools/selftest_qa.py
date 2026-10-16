#!/usr/bin/env python3
"""自测：证明 qa_paper.py 真的会「翻绿」也会「翻红」。

为什么要有这个文件：
  自写的检查脚本最容易出的问题不是「不报错」，而是**两个方向都会骗人**——
  要么对缺陷装看不见（假绿），要么对正常内容误报（假红）。
  所以不能只看它在真仓库上「显示了什么」，必须先造出**已知答案的对照样本**，
  确认判定跟着事实走。

本脚本在临时目录里造 5 个卷，每个都有明确的期望结论：

  case A  完整 47 题 + 四个选项齐全 + 答案齐全 + 图片存在   → 无阻断、无 C1-C6 告警
  case B  少第 40 题                                      → C1/C3 告警
  case C  questions.md 引用不存在的图片                     → C7 **阻断**
  case D  questions.md 泄漏「正确答案：B」                   → C8 **阻断**
  case E  选择题缺 D 选项                                   → C4 告警

任一条与期望不符即退出码 1。

用法：python tools/selftest_qa.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

for _s in (sys.stdout, sys.stderr):  # Windows 控制台默认 GBK，打不出 emoji/中文符号
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from qa_paper import check_paper  # noqa: E402

OPTS = "A. 甲\nB. 乙\nC. 丙\nD. 丁\n"


def make_questions(nos: list[int], *, leak: bool = False,
                   img: str | None = None, drop_D_on: int | None = None) -> str:
    parts = ["<!-- paper: selftest | kind: questions | status: needs-review -->",
             "# 自测卷\n", "## 一、单项选择题\n"]
    for n in nos:
        body = f"### 第 {n} 题\n\n题干 {n}。\n\n"
        if n <= 40:
            body += OPTS.replace("D. 丁\n", "") if n == drop_D_on else OPTS
        if n == 1 and leak:
            body += "\n正确答案：B\n"
        if n == 2 and img:
            body += f"\n![图]({img})\n"
        parts.append(body)
    return "\n".join(parts)


def make_solutions(nos: list[int]) -> str:
    parts = ["<!-- paper: selftest | kind: solutions -->", "# 自测卷 解析\n"]
    for n in nos:
        ans = f"\n答案：{'ABCD'[(n - 1) % 4]}\n" if n <= 40 else ""
        parts.append(f"### 第 {n} 题\n{ans}\n解析正文。\n")
    return "\n".join(parts)


def write_paper(d: Path, nos_q: list[int], nos_s: list[int], **kw) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    (d / "questions.md").write_text(make_questions(nos_q, **kw), encoding="utf-8")
    (d / "solutions.md").write_text(make_solutions(nos_s), encoding="utf-8")
    return d


ALL = list(range(1, 48))
CASES: list[tuple[str, str, dict, list[int], list[int]]] = [
    # 名字, 说明, 造卷参数, 题号(题干), 题号(解析)
    ("A_complete", "完整 47 题（图片存在）", {"img": "assets/ok.png"}, ALL, ALL),
    ("B_missing40", "少第 40 题", {}, [n for n in ALL if n != 40],
     [n for n in ALL if n != 40]),
    ("C_badimg", "引用不存在的图片", {"img": "assets/nope.png"}, ALL, ALL),
    ("D_leak", "题干里泄漏答案", {"leak": True}, ALL, ALL),
    ("E_noD", "第 5 题缺 D 选项", {"drop_D_on": 5}, ALL, ALL),
]


def expected(case: str, r: dict) -> list[str]:
    """返回该 case 下『应当出现』的判定特征。"""
    warns = " | ".join(r["warnings"])
    errs = " | ".join(r["errors"])
    if case == "A_complete":
        bad = []
        if r["errors"]:
            bad.append(f"期望无阻断，实际有：{errs}")
        for tag in ("C1", "C2", "C3", "C4", "C5", "C6"):
            if tag in warns:
                bad.append(f"期望无 {tag} 告警，实际有：{warns}")
        return bad
    if case == "B_missing40":
        return [] if ("C1" in warns and "C3" in warns) else \
            [f"期望 C1+C3 告警，实际：{warns or '（无告警）'}"]
    if case == "C_badimg":
        return [] if ("C7" in errs and r.get("blocking")) else \
            [f"期望 C7 阻断，实际 errors={errs or '（无）'} blocking={r.get('blocking')}"]
    if case == "D_leak":
        return [] if ("C8" in errs and r.get("blocking")) else \
            [f"期望 C8 阻断，实际 errors={errs or '（无）'} blocking={r.get('blocking')}"]
    if case == "E_noD":
        return [] if "C4" in warns else [f"期望 C4 告警，实际：{warns or '（无告警）'}"]
    return ["未知 case"]


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="qa-selftest-") as tmp:
        root = Path(tmp)
        for name, desc, kw, q_nos, s_nos in CASES:
            d = write_paper(root / name, q_nos, s_nos, **kw)
            if name == "A_complete":
                (d / "assets").mkdir(exist_ok=True)
                (d / "assets" / "ok.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            r = check_paper(d)
            bad = expected(name, r)
            mark = "✅" if not bad else "❌"
            print(f"{mark} case {name:14s} {desc}")
            print(f"     errors={r['errors']}")
            print(f"     warnings={r['warnings']}")
            failures += [f"{name}: {b}" for b in bad]

    print()
    if failures:
        print("❌ 自测未通过：")
        for f in failures:
            print("   -", f)
        return 1
    print("✅ 5/5 对照样本判定与期望一致（能翻红也能翻绿）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
