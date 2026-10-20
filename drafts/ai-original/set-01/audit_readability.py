#!/usr/bin/env python3
"""Compare Set 01 paper reading burden with 2024/2025 source Markdown.

Counts are editorial/proxy metrics, NOT measured reading time or difficulty.
The historical Markdown may contain OCR and missing-picture anomalies.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
HEADER = re.compile(r"^###\s*第\s*(\d+)\s*题\s*$", re.M)
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
COMMENT = re.compile(r"<!--.*?-->", re.S)
CJK = re.compile(r"[\u4e00-\u9fff]")
ANSWER = re.compile(r"\*\*答案：([ABCD])。\*\*")


def paper(path: Path):
    source = path.read_text(encoding="utf-8")
    entries = list(HEADER.finditer(source))
    assert [int(m.group(1)) for m in entries] == list(range(1, 48)), path
    records = []
    for i, m in enumerate(entries):
        body = COMMENT.sub("", source[m.end(): entries[i + 1].start() if i + 1 < len(entries) else len(source)])
        body_without_image = IMAGE.sub("", body)
        records.append({
            "q": int(m.group(1)),
            "nonwhitespace": len(re.sub(r"\s", "", body)),
            "nonwhitespace_without_image_markup": len(re.sub(r"\s", "", body_without_image)),
            "cjk_without_image_markup": len(CJK.findall(body_without_image)),
            "figure_references": len(IMAGE.findall(body)),
        })
    return records


def aggregate(items):
    def sums(key): return sum(x[key] for x in items)
    return {
        "questions": len(items),
        "raw_nonwhitespace": sums("nonwhitespace"),
        "without_image_markup": sums("nonwhitespace_without_image_markup"),
        "cjk_without_image_markup": sums("cjk_without_image_markup"),
        "embedded_image_references": sums("figure_references"),
        "per_question_avg_nonwhitespace": round(sums("nonwhitespace") / len(items), 1),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    sources = {
        "2024": REPO / "papers/exams/2024/questions.md",
        "2025": REPO / "papers/exams/2025/questions.md",
        "set01": HERE / "questions.md",
    }
    records = {key: paper(path) for key, path in sources.items()}
    summaries = {
        label: {
            "choice": aggregate(values[:40]),
            "comprehensive": aggregate(values[40:]),
        }
        for label, values in records.items()
    }
    raw = {x: summaries[x]["choice"]["raw_nonwhitespace"] for x in summaries}
    cn = {x: summaries[x]["choice"]["cjk_without_image_markup"] for x in summaries}
    ai_choices = records["set01"][:40]
    short = sorted(ai_choices, key=lambda r: r["nonwhitespace"], reverse=True)[:8]

    solutions = (HERE / "solutions.md").read_text(encoding="utf-8")
    matches = list(HEADER.finditer(solutions))
    answer_letters = []
    for i, m in enumerate(matches[:40]):
        segment = solutions[m.end(): matches[i + 1].start()]
        letter = ANSWER.search(segment)
        assert letter, f"Q{m.group(1)} missing answer"
        answer_letters.append(letter.group(1))
    counts = {letter: answer_letters.count(letter) for letter in "ABCD"}
    assert sum(counts.values()) == 40

    report = {
        "method": "Markdown text proxy, whitespace excluded; image link syntax excluded from comparable visible proxy; not actual print layout",
        "notes": [
            "2024/2025 Markdown may contain OCR issues and missing diagrams",
            "CJK counts exclude Latin text, formulas and code; lower counts do not prove lower conceptual load",
            "Comparison by item title parsing; this script does not validate academic answers",
        ],
        "yearly": summaries,
        "set01_top8_longest_choices": short,
        "choice_answer_letters": counts,
        "set01_relative_to_2025": {
            "mc_nonwhitespace_ratio": round(raw["set01"] / raw["2025"], 3),
            "mc_cjk_ratio": round(cn["set01"] / cn["2025"], 3),
        },
    }
    for label, v in summaries.items():
        print(f"[readability] {label} MC: {v['choice']['raw_nonwhitespace']} nonwhitespace; {v['choice']['cjk_without_image_markup']} Chinese chars")
        print(f"[readability] {label} comprehensive: {v['comprehensive']['cjk_without_image_markup']} Chinese chars")
    print(f"[readability] Set 01 choices vs 2025: {report['set01_relative_to_2025']}")
    print(f"[readability] Set 01 answer letter distribution: {counts}")
    print("[readability] This is a diagnostic, NOT evidence of empirical exam difficulty equivalence.")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
