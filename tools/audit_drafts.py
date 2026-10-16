#!/usr/bin/env python3
"""语义审计：对已生成的 questions.md / solutions.md 做逐题实质检查。

与 tools/qa_paper.py 的分工：qa_paper 查**结构**（题号集合、选项个数、图片存在、
答案泄漏），本脚本查**内容是否真的是内容**——空壳、占位、缺页、图归属、
公式/代码形态、来源页码。C1—C8 全绿 ≠ 内容正确，本脚本输出**高风险疑点**。

用法： tools/audit_drafts.py [--paper exams/2026] [--json index/draft-audit.json]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "build" / "_scratch" / "408-raw-pages"
Q_HEAD = re.compile(r"^### 第 (\d+) 题")
OPT = re.compile(r"^([ABCD])\.\s*(.*)$")
ANS_LINE = re.compile(r"答案[：:]\s*([ABCD]|（缺）)?")
PLACEHOLDER = re.compile(r"^(（?缺）?|待补|TODO|TBD|\.\.\.)$")


def parse_questions(path: Path) -> dict[int, dict]:
    out, cur = {}, None
    for ln in path.read_text(encoding="utf-8").splitlines():
        m = Q_HEAD.match(ln)
        if m:
            cur = int(m.group(1))
            out[cur] = {"stem": [], "opts": {}, "imgs": []}
            continue
        if cur is None:
            continue
        mo = OPT.match(ln)
        if mo and len(out[cur]["stem"]) >= 1:
            out[cur]["opts"][mo.group(1)] = mo.group(2).strip()
        elif ln.startswith("!["):
            mm = re.search(r"\((assets/[^)]+)\)", ln)
            if mm:
                out[cur]["imgs"].append(mm.group(1))
        elif ln.strip():
            out[cur]["stem"].append(ln.strip())
    for q in out.values():
        q["stem_text"] = " ".join(q["stem"]).strip()
    return out


def parse_solutions(path: Path) -> dict[int, dict]:
    out, cur = {}, None
    for ln in path.read_text(encoding="utf-8").splitlines():
        m = Q_HEAD.match(ln)
        if m:
            cur = int(m.group(1))
            out[cur] = {"head": ln, "body": []}
            continue
        if cur is not None and ln.strip():
            out[cur]["body"].append(ln.strip())
    for q in out.values():
        q["body_text"] = " ".join(q["body"])
        ma = re.search(r"答案[：:]\s*([ABCD])", q["head"] + " " + q["body_text"])
        q["answer"] = ma.group(1) if ma else None
    return out


def audit(paper_id: str) -> dict:
    pdir = ROOT / "papers" / paper_id
    qs = parse_questions(pdir / "questions.md")
    ss = parse_solutions(pdir / "solutions.md")
    rep: dict = {"paper": paper_id, "questions": len(qs), "solutions": len(ss), "issues": []}

    def flag(sev, q, kind, detail):
        rep["issues"].append({"severity": sev, "q": q, "kind": kind, "detail": detail})

    # 题号集合
    if set(qs) != set(range(1, 48)):
        flag("high", None, "qset", f"questions 题号集合异常: 缺 {sorted(set(range(1,48))-set(qs))}")
    if set(qs) != set(ss):
        flag("high", None, "qset-mismatch", "questions 与 solutions 题号集合不一致")

    empty_opt = 0
    for n in sorted(qs):
        q = qs[n]
        if not q["stem_text"] or PLACEHOLDER.match(q["stem_text"]):
            flag("high", n, "empty-stem", "题干为空或占位")
        if n <= 40:
            for k in "ABCD":
                v = q["opts"].get(k, "")
                if not v:
                    empty_opt += 1
                    flag("high", n, "empty-option", f"选项 {k} 为空")
                elif PLACEHOLDER.match(v):
                    flag("high", n, "placeholder-option", f"选项 {k} 是占位符: {v!r}")
        else:
            if len(q["stem_text"]) < 20:
                flag("medium", n, "thin-comp", "综合题正文过短，疑缺页")
        for img in q["imgs"]:
            if not (pdir / img).is_file():
                flag("high", n, "missing-image", f"图片不存在: {img}")

    for n in sorted(ss):
        s = ss[n]
        if n <= 40:
            if not s["answer"]:
                flag("high", n, "no-answer", "solutions 缺可解析答案字母")
        else:
            if len(s["body_text"]) < 40:
                flag("medium", n, "thin-solution", "综合题解析过短，疑 OCR 缺页")
            if "源中未定位到该题答案" in s["body_text"]:
                flag("high", n, "no-solution", "solutions 未定位到答案")

    # 泄漏（qa_paper 也有，这里给出具体命中行）
    qtext = (pdir / "questions.md").read_text(encoding="utf-8")
    for ln in qtext.splitlines():
        if "答案" in ln or "Key:" in ln or "<!-- ans" in ln:
            flag("high", None, "answer-leak", f"questions.md 命中泄漏关键词: {ln[:70]}")

    # 公式 / 代码形态
    rep["formula_inline"] = len(re.findall(r"(?<!\$)\$[^$\n]+\$(?!\$)", qtext))
    rep["formula_block"] = qtext.count("$$") // 2
    rep["code_fence"] = qtext.count("```") // 2
    rep["images"] = sum(len(q["imgs"]) for q in qs.values())

    # 图归属可疑（q36 页含 3 题）
    for n, q in qs.items():
        for img in q["imgs"]:
            if n in (36,):
                flag("medium", n, "image-ownership",
                     f"{img} 来自含 36/37/38 三题的页，归属未确认")
    sev = {"high": 0, "medium": 0}
    for i in rep["issues"]:
        sev[i["severity"]] += 1
    rep["counts"] = sev
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paper", default="exams/2026")
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)
    rep = audit(args.paper)
    print(f"[audit] {rep['paper']}  题 {rep['questions']}  解 {rep['solutions']}  "
          f"图 {rep['images']}  公式(行内/块) {rep['formula_inline']}/{rep['formula_block']}  "
          f"代码块 {rep['code_fence']}")
    print(f"[audit] 风险: high={rep['counts']['high']} medium={rep['counts']['medium']}")
    by_kind: dict[str, int] = {}
    for i in rep["issues"]:
        by_kind[i["kind"]] = by_kind.get(i["kind"], 0) + 1
    for k, v in sorted(by_kind.items(), key=lambda x: -x[1]):
        print(f"    {k}: {v}")
    hi = [i for i in rep["issues"] if i["severity"] == "high"]
    for i in hi[:8]:
        print(f"    ! q{i['q']} {i['kind']}: {i['detail'][:80]}")
    if args.json:
        (ROOT / args.json).write_text(json.dumps(rep, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
        print(f"[audit] 写入 {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
