#!/usr/bin/env python3
"""单卷 / 全量质检。

检查项（编号与 docs/qa-policy.md §2 对齐）：

  C1  选择题题号集合 == {1..40}
  C2  综合题题号集合 == {41..47}
  C3  合计 == 47
  C4  每道选择题恰有 A/B/C/D 四个选项
  C5  questions.md 题号集合 == solutions.md 题号集合
  C6  每道选择题在 solutions 里有可解析的答案字母
  C7  questions.md 引用的每个图片文件存在          ← 阻断
  C8  questions.md 不含答案泄漏                    ← 阻断
  C9  逐题 status 是否为 proofread（报告，不阻断）

设计立场：C1—C6 在转录中途必然红，因此**只报告不阻断**；
C7/C8 属于「已经错了」，**阻断**。详见 docs/qa-policy.md §7。

用法：
  python tools/qa_paper.py papers/exams/2009
  python tools/qa_paper.py --all
  python tools/qa_paper.py --all --json index/qa-report.json --write-coverage
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # Windows 控制台默认 GBK，打不出 emoji/中文符号
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parent.parent

CHOICE_RANGE = set(range(1, 41))
COMPREHENSIVE_RANGE = set(range(41, 48))

# 题号标题：### 第 12 题 / ## 第12题 / ### 第 12 题　答案：B
RE_QHEAD = re.compile(r"^#{2,4}\s*第\s*(\d{1,2})\s*题", re.M)
# 选项行：行首（可带列表符）单个 A-D 加大写句点/顿号/全角句点
RE_OPTION = re.compile(r"^\s*(?:[-*+]\s*)?([A-D])\s*[.、．]\s*\S", re.M)
# 答案：答案：B / 答案: B / **答案**：B
RE_ANSWER = re.compile(r"答案\s*[*）)]*\s*[：:]\s*[*\s]*([A-D])\b")
# 图片引用
RE_IMG = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
# 答案泄漏
RE_LEAK = re.compile(r"(正确答案|参考答案|答案\s*[：:]\s*[A-D]\b|^\s*Key\s*[:：]\s*[A-D]\b)",
                     re.M | re.I)

RE_FENCE = re.compile(r"```.*?```", re.S)
# 「这一段没切出来」的占位标记（由 md_from_pages 写出）。见 stats["stubs"] 处的说明。
RE_STUB = re.compile(r"本题未从底本切出")


def strip_fences(text: str) -> str:
    """去掉围栏代码块，避免代码里的 'A.' 被当成选项、'答案：' 被当成泄漏。"""
    return RE_FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def split_by_question(text: str) -> dict[int, str]:
    """按 `### 第 N 题` 切分，返回 {题号: 该题正文}。"""
    out: dict[int, str] = {}
    marks = list(RE_QHEAD.finditer(text))
    for i, m in enumerate(marks):
        no = int(m.group(1))
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end]
        # 同号重复出现时合并，交由后续检查报出
        out[no] = out.get(no, "") + body
    return out


def option_rows_declared(paper_dir: Path) -> tuple[set[int], list[str]]:
    """读 meta.yml 的 `options_in_figure` —— 「这题的四个选项画在图里」的人工登记。

    → ({题号}, [问题])。登记项可以是 `4`，也可以是 `{"no": 4, figure: …, …}`
    （推荐后者，能顺带记下核对的是哪张图）。**问题一律往上抛、不静默吞掉**：
    读不出来的登记按「没有登记」处理（宁可照旧报 C4），但必须让写的人知道。

    ⚠️ **YAML 1.1 把裸 `no` 当布尔**：`- no: 4` 解析出来是 `{False: 4}`，不是 `{"no": 4}`。
    这里**不猜**那个 `False` 是不是题号（猜错了就是拿错题号去豁免），只把这种写法
    报成问题，请写的人给键加引号（`- "no": 4`）。
    """
    meta = paper_dir / "meta.yml"
    if not meta.is_file():
        return set(), []
    try:
        import yaml  # noqa: PLC0415
        m = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return set(), [f"options_in_figure 读不了：meta.yml 解析失败（{type(exc).__name__}）"]
    if not m.get("options_in_figure"):
        return set(), []
    out: set[int] = set()
    problems: list[str] = []
    for i, e in enumerate(m["options_in_figure"], start=1):
        if not isinstance(e, dict):
            try:
                out.add(int(e))          # 简写：直接写题号
            except (TypeError, ValueError):
                problems.append(f"第 {i} 项 {e!r} 不是题号也不是映射，已忽略")
            continue
        if False in e:
            problems.append(f"第 {i} 项的键被 YAML 解析成布尔 False（裸 `no` 的经典坑），"
                            f"已忽略；请写成 `- \"no\": {e[False]}`")
            continue
        for key in ("no", "n", "number"):
            if key in e:
                try:
                    out.add(int(e[key]))
                except (TypeError, ValueError):
                    problems.append(f"第 {i} 项 {key}={e[key]!r} 不是整数，已忽略")
                break
        else:
            problems.append(f"第 {i} 项没有 `no`/`n`/`number` 键，已忽略")
    return out, problems


def check_paper(paper_dir: Path) -> dict:
    qfile = paper_dir / "questions.md"
    sfile = paper_dir / "solutions.md"
    res: dict = {
        "paper": paper_dir.relative_to(REPO).as_posix() if paper_dir.is_relative_to(REPO)
                 else str(paper_dir),
        "has_questions": qfile.is_file(),
        "has_solutions": sfile.is_file(),
        "errors": [],      # 阻断
        "warnings": [],    # 报告
        "notes": [],       # 说明（不影响判定：如「选项在图内」这类已登记的例外）
        "stats": {},
    }
    if not qfile.is_file():
        res["warnings"].append("C1-C8: questions.md 不存在（本卷尚未开始转录）")
        return res

    qtext = qfile.read_text(encoding="utf-8")
    qbody = strip_fences(qtext)
    qs = split_by_question(qbody)

    stext = sfile.read_text(encoding="utf-8") if sfile.is_file() else ""
    ss = split_by_question(strip_fences(stext))

    # ── 空 stub 不算题 ──────────────────────────────────────────────────────
    # `md_from_pages.one()` 在底本切不出那一段时，写的是
    #   `> ⛔ 本题未从底本切出，待人工补齐（见转写报告）。`
    # 早先只数 `### 第 N 题` 在不在，于是**它也算一道题**。后果是：
    # C1/C2/C3 全绿、coverage.md 报 47/47、阻断项 —，而那一卷可能 42 道题里
    # 一个字都没有——docs/qa-policy.md 开头明写「不允许以空 stub 计入完整」，
    # 这张表恰恰在替空 stub 记绿灯（2027 模拟卷 set-2/3/4：42/41/43 个）。
    # 所以按**有无正文**计数，并把 stub 数单列出来，让人看得见缺口在哪。
    stubs = {n for n, body in qs.items() if RE_STUB.search(body)}
    real = {n: b for n, b in qs.items() if n not in stubs}
    if stubs:
        res["warnings"].append("C0 空 stub 共 %d 题（本题未从底本切出，不计入题数）：%s"
                               % (len(stubs), sorted(stubs)[:12]))
    choice = {n for n in real if n in CHOICE_RANGE}
    comp = {n for n in real if n in COMPREHENSIVE_RANGE}
    out_of_range = set(real) - CHOICE_RANGE - COMPREHENSIVE_RANGE

    res["stats"].update(q_choice=len(choice), q_comp=len(comp),
                        q_total=len(real), s_total=len(ss),
                        stubs=len(stubs),
                        out_of_range=sorted(out_of_range))

    # C1 / C2 / C3
    if choice != CHOICE_RANGE:
        miss = sorted(CHOICE_RANGE - choice)
        extra = sorted(choice - CHOICE_RANGE)
        res["warnings"].append(f"C1 选择题不齐：缺 {miss or '无'} / 越界 {extra or '无'}")
    if comp != COMPREHENSIVE_RANGE:
        miss = sorted(COMPREHENSIVE_RANGE - comp)
        extra = sorted(comp - COMPREHENSIVE_RANGE)
        res["warnings"].append(f"C2 综合题不齐：缺 {miss or '无'} / 越界 {extra or '无'}")
    if len(qs) != 47:
        res["warnings"].append(f"C3 合计 {len(qs)}/47")

    # C4 选择题四选项
    # 有一类题**没有文字选项，选项本身就画在题图里**（2009 第 4 题的四个二叉树、
    # 2017 第 8 题的四个判定树：图里各自带 `A.` `B.` `C.` `D.` 标注）。
    # 这类题按「选项不齐」报会**误导**（读的人以为是缺陷），所以单列一类；
    # 但**不许自动放行**——必须在 meta.yml 里逐题登记 `options_in_figure`，
    # 登记本身就代表「有人看过那张图、确认四选项在里面」。登记与事实不符时照样报：
    #   · 已经切出文字选项 → 登记过期； · 该题根本没有图 → 登记是错的。
    declared, decl_problems = option_rows_declared(paper_dir)
    if decl_problems:
        res["warnings"].append("C4 meta.yml options_in_figure 有问题："
                               + "；".join(decl_problems[:4])
                               + (" …" if len(decl_problems) > 4 else ""))
    bad4, in_fig, stale = [], [], []
    for n in sorted(choice):
        letters = {m.group(1) for m in RE_OPTION.finditer(qs[n])}
        if letters == {"A", "B", "C", "D"}:
            if n in declared:
                stale.append(f"{n}(已切出 {''.join(sorted(letters))})")
            continue
        if n in declared:
            if not RE_IMG.search(qs[n]):
                stale.append(f"{n}(登记称选项在图内，但该题没有插图)")
            else:
                in_fig.append(n)
            continue
        bad4.append(f"{n}({''.join(sorted(letters)) or '无'})")
    if bad4:
        res["warnings"].append(f"C4 选项不齐共 {len(bad4)} 题：{', '.join(bad4[:12])}"
                               + (" …" if len(bad4) > 12 else ""))
    if in_fig:
        res["notes"].append(
            f"C4 选项在图内共 {len(in_fig)} 题：{in_fig}（meta.yml options_in_figure 已登记；"
            f"四个选项画在题图里，需人眼核对）")
    if stale:
        res["warnings"].append(
            f"C4 meta.yml options_in_figure 登记已与事实不符，请更新：{', '.join(stale[:12])}"
            + (" …" if len(stale) > 12 else ""))

    # C5 题号双向一致
    if ss:
        only_q = sorted(set(qs) - set(ss))
        only_s = sorted(set(ss) - set(qs))
        if only_q or only_s:
            res["warnings"].append(
                f"C5 题号不匹配：仅题干有 {only_q or '无'}；仅解析有 {only_s or '无'}")
    elif qs:
        res["warnings"].append("C5 solutions.md 缺失或为空，无法比对")

    # C6 选择题答案可解析
    no_ans = [n for n in sorted(choice) if n in ss and not RE_ANSWER.search(ss[n])]
    if ss:
        if no_ans:
            res["warnings"].append(
                f"C6 解析中缺答案字母共 {len(no_ans)} 题：{no_ans[:12]}"
                + (" …" if len(no_ans) > 12 else ""))
        res["stats"]["answers_parsed"] = len(choice) - len(no_ans)

    # C7 图片存在 —— 阻断
    missing_img = []
    for raw in RE_IMG.findall(qtext):
        if raw.startswith(("http://", "https://", "data:")):
            res["errors"].append(f"C7 外链图片（禁止）：{raw}")
            continue
        target = (paper_dir / raw).resolve()
        if not target.is_file():
            missing_img.append(raw)
    if missing_img:
        res["errors"].append(f"C7 图片缺失 {len(missing_img)} 个：{missing_img[:8]}")

    # C8 答案泄漏 —— 阻断
    leaks = [ln.strip() for ln in RE_LEAK.findall(strip_fences(qtext))]
    if leaks:
        res["errors"].append(f"C8 questions.md 疑似含答案 {len(leaks)} 处：{leaks[:5]}")

    # C9 校对状态
    meta = paper_dir / "meta.yml"
    if meta.is_file():
        try:
            import yaml  # noqa: PLC0415
            m = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
            sts = [q.get("status") for q in (m.get("questions") or [])]
            done = sum(1 for s in sts if s == "proofread")
            res["stats"]["proofread"] = f"{done}/{len(sts)}"
        except Exception as exc:
            res["warnings"].append(f"C9 meta.yml 解析失败：{type(exc).__name__}")
    else:
        res["stats"]["proofread"] = "无 meta.yml"

    res["blocking"] = bool(res["errors"])
    return res


def discover() -> list[Path]:
    dirs = []
    for base in (REPO / "papers").glob("*"):
        if base.is_dir():
            for d in base.iterdir():
                if d.is_dir() and not d.name.startswith("_"):
                    dirs.append(d)
    return sorted(dirs)


def write_coverage(reports: list[dict]) -> Path:
    out = REPO / "index" / "coverage.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 逐卷完成度（生成物，勿手改）",
        "",
        "> 由 `tools/qa_paper.py --all --write-coverage` 生成。",
        "> 空闲的卷显示「尚未开始转录」是**预期**状态，不是故障。",
        "",
        "| 卷 | 选择题 | 综合题 | 合计 | 有答案 | 阻断项 | 告警 |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in reports:
        s = r.get("stats", {})
        blk = "⛔ " + "; ".join(r["errors"]) if r.get("errors") else "—"
        # 「告警」这一列是**必需的**，否则这张表会把骨架报成绿灯：
        # C1/C2/C3 只数**题号在不在**，一道题只要有 `### 第 N 题` 就算数。
        # 于是「题号齐全但一个选项都没切出来」的 OCR 骨架会显示成 47/47、阻断项 —，
        # 看的人会以为这卷完成了。2027 模拟卷 set-2/3/4 当前正是这个状态
        # （C4 报「选项不齐 39/34/37 题」、C5 报「solutions.md 缺失」）。
        warn = "；".join(w.split("：")[0] for w in r.get("warnings", [])) or "—"
        lines.append(
            f"| `{r['paper']}` | {s.get('q_choice', 0)}/40 | {s.get('q_comp', 0)}/7 "
            f"| {s.get('q_total', 0)}/47 | {s.get('answers_parsed', 0)}/40 | {blk} | {warn} |")
    lines += ["", "## 尚未开始的卷", ""]
    notstarted = [r["paper"] for r in reports if not r.get("has_questions")]
    lines.append("、".join(f"`{p}`" for p in notstarted) if notstarted else "（无）")
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paper", nargs="?", help="卷目录，如 papers/exams/2009")
    ap.add_argument("--all", action="store_true", help="扫描 papers/ 下全部卷")
    ap.add_argument("--json", dest="json_out", help="把结果写到 JSON")
    ap.add_argument("--write-coverage", action="store_true",
                    help="写出 index/coverage.md（需配合 --all）")
    args = ap.parse_args(argv)

    if args.all:
        targets = discover()
        if not targets:
            print("[qa] papers/ 下还没有任何卷目录 —— 属预期（P1 只建骨架）。")
            return 0
    elif args.paper:
        targets = [ (REPO / args.paper) if not Path(args.paper).is_absolute()
                    else Path(args.paper) ]
    else:
        ap.error("需要给一个卷目录，或用 --all")

    reports = [check_paper(d) for d in targets]
    n_block = sum(1 for r in reports if r.get("blocking"))

    for r in reports:
        flag = "⛔" if r.get("blocking") else ("⚠️" if r["warnings"] else "✅")
        s = r.get("stats", {})
        print(f"{flag} {r['paper']}  "
              f"choice={s.get('q_choice', 0)}/40 comp={s.get('q_comp', 0)}/7 "
              f"total={s.get('q_total', 0)}/47")
        for w in r["warnings"]:
            print(f"    ⚠️  {w}")
        for e in r["errors"]:
            print(f"    ⛔  {e}")
        for note in r.get("notes", []):
            print(f"    ℹ️  {note}")

    print(f"\n[qa] {len(reports)} 卷，阻断 {n_block} 卷。"
          f"（未达 47/47 属转录进度，非阻断）")

    if args.json_out:
        p = Path(args.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8", newline="\n")
        print(f"[qa] JSON → {p}")
    if args.write_coverage:
        print(f"[qa] coverage → {write_coverage(reports)}")

    return 1 if n_block else 0


if __name__ == "__main__":
    sys.exit(main())
