#!/usr/bin/env python3
"""Check the direction-only, unmerged 408 AI Original Set 01 proposal.

A passing check proves structural integrity, not academic correctness,
novelty, or calibrated difficulty.
"""
from __future__ import annotations

import collections
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
MARKS = {41: 13, 42: 10, 43: 12, 44: 11, 45: 7, 46: 8, 47: 9}
SUBJECT_POINTS = {"DS": 45, "CO": 45, "OS": 35, "CN": 25}
FIGURES = {5, 8, 19, 36, 38, 42, 43, 47}


def expected_subject(n: int) -> str:
    if n <= 11 or n in (41, 42):
        return "DS"
    if n <= 22 or n in (43, 44):
        return "CO"
    if n <= 32 or n in (45, 46):
        return "OS"
    return "CN"


def main() -> None:
    plan = json.loads((HERE / "item-plan.json").read_text(encoding="utf-8"))
    assert plan["schema"] == "ai-exam-direction-v0.1"
    assert plan["exam_id"] == "ai-original/set-01"
    assert plan["status"] == "direction-only-not-questions"
    fmt = plan["format"]
    assert (fmt["minutes"], fmt["points"]) == (180, 150)
    assert (fmt["choice_count"], fmt["comprehensive_count"]) == (40, 7)
    assert fmt["subject_points"] == SUBJECT_POINTS

    rows = plan["items"]
    assert len(rows) == 47
    total = collections.Counter()
    difficulty = collections.Counter()
    figures = set()
    minutes = 0.0

    for n, r in enumerate(rows, 1):
        assert r["no"] == n
        subject = expected_subject(n)
        assert r["subject"] == subject, (n, subject)
        kind = "choice" if n <= 40 else "comprehensive"
        assert r["kind"] == kind
        assert r["points"] == (2 if n <= 40 else MARKS[n])
        assert r["primary_concept"].startswith(subject) and re.fullmatch(
            r"(DS|CO|OS|CN)\d{2}\.\d{2}", r["primary_concept"]
        )
        assert r["primary_concept_name"].strip()
        assert all(re.fullmatch(r"(DS|CO|OS|CN)\d{2}\.\d{2}", x)
                   for x in r["supporting_concepts"])
        assert r["cognitive_operation"].strip()
        assert r["scenario_seed"].strip()
        assert r["originality_design"].strip()
        assert r["misconception_to_diagnose"].strip()
        assert re.fullmatch(r"20\d{2}Q\d{2}", r["calibration_anchor"])
        assert r["editorial_state"] == "direction-only"
        assert r["question_written"] is False
        assert r["answer_verified"] is False
        assert r["figure_verified"] is False
        assert r["estimated_minutes"] > 0
        minutes += r["estimated_minutes"]
        total[subject] += r["points"]
        if n <= 40:
            assert r["difficulty_target"] in {"E", "M", "H"}
            difficulty[r["difficulty_target"]] += 1
        else:
            assert r["difficulty_target"] in {"M", "HM"}
        if r["figure_approach"] == "svg":
            figures.add(n)

    assert dict(total) == SUBJECT_POINTS, total
    assert dict(difficulty) == {"E": 11, "M": 23, "H": 6}, difficulty
    assert figures == FIGURES, figures
    assert abs(minutes - 164.8) < 1e-8, minutes
    assert abs(plan["difficulty_time_proposal"]["review_minutes"] - 15.2) < 1e-8

    for name in ("questions.md", "solutions.md"):
        text = (HERE / name).read_text(encoding="utf-8")
        assert not re.search(r"^###\s*第\s*\d+\s*题", text, re.MULTILINE), name
        assert "0/47" in text or "尚无" in text or "暂无" in text, name

    review = (HERE / "review.md").read_text(encoding="utf-8")
    review_rows = re.findall(r"^\|\s*Q\d{2}\s*\|", review, re.MULTILINE)
    assert len(review_rows) == 47, len(review_rows)
    for n in FIGURES:
        assert f"Q{n:02}" in (HERE / "figure-plan.md").read_text(encoding="utf-8")
    print("[ai-408-draft] OK: 47 direction-only slots, 150 pts, 180 min, subject 45/45/35/25")
    print("[ai-408-draft] OK: 11 basic + 23 medium + 6 higher MC, 8 planned SVGs")
    print("[ai-408-draft] OK: zero claimed finished problems or answers (academic validation not attempted)")


if __name__ == "__main__":
    main()
