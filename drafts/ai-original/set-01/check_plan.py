#!/usr/bin/env python3
"""Validate the editorial blueprint for AI Original Set 01 (standard library only).

This does NOT assess original question correctness, exam difficulty or originality.
Run from repo root: python drafts/ai-original/set-01/check_plan.py
"""
from __future__ import annotations

import collections
import json
import math
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
EXPECTED_SUBJECTS = {"DS": 45, "CO": 45, "OS": 35, "CN": 25}
EXPECTED_COUNTS = {"DS": 13, "CO": 13, "OS": 12, "CN": 9}
EXPECTED_BIG = {41: 13, 42: 10, 43: 12, 44: 11, 45: 7, 46: 8, 47: 9}
REQUIRED_FILES = (
    "README.md", "blueprint.md", "item-plan.json", "calibration-2024-2025.md",
    "figure-plan.md", "quality-gates.md", "critical-audit.md", "questions.md",
    "solutions.md", "review.md", "specs/README.md", "assets/README.md",
)
FIGURES = [5, 8, 19, 36, 38, 42, 43, 47]
TIERS = {"E", "M", "H", "HM"}


def subject_for_question(n: int) -> str:
    if 1 <= n <= 11 or 41 <= n <= 42:
        return "DS"
    if 12 <= n <= 22 or 43 <= n <= 44:
        return "CO"
    if 23 <= n <= 32 or 45 <= n <= 46:
        return "OS"
    if 33 <= n <= 40 or n == 47:
        return "CN"
    raise AssertionError(f"invalid question number {n}")


def numbered_rows(markdown: str, pattern: str) -> list[int]:
    return [int(match.group(1)) for match in re.finditer(pattern, markdown, re.M)]


def main() -> None:
    assert all((HERE / name).is_file() for name in REQUIRED_FILES), "missing draft deliverable"
    data = json.loads((HERE / "item-plan.json").read_text(encoding="utf-8"))
    assert data["schema"] == "ai-exam-direction-v0.1"
    assert data["exam_id"] == "ai-original/set-01"
    assert data["status"] in {"direction-only-not-questions", "authoring", "review-in-progress"}
    assert data["format"]["minutes"] == 180
    assert data["format"]["points"] == 150
    assert data["format"]["choice_count"] == 40
    assert data["format"]["comprehensive_count"] == 7
    assert data["format"]["subject_points"] == EXPECTED_SUBJECTS
    assert data["knowledge_graph_dependency"]["pr"] == 26

    items = data["items"]
    assert len(items) == 47
    assert [q["no"] for q in items] == list(range(1, 48)), "47 question slots out of order"
    subject_counts = collections.Counter()
    subject_points = collections.Counter()
    choice_tiers = collections.Counter()
    count_written = 0
    total_minutes = 0.0
    fig_numbers = []

    for question in items:
        no = question["no"]
        subject = subject_for_question(no)
        kind = "choice" if no <= 40 else "comprehensive"
        expected_points = 2 if no <= 40 else EXPECTED_BIG[no]
        assert question["kind"] == kind, no
        assert question["subject"] == subject, no
        assert question["points"] == expected_points, no
        assert question["editorial_state"] in {
            "direction-only", "drafted", "independent-check-passed",
            "editorial-approved", "pilot-calibrated"
        }, no
        assert question["difficulty_target"] in TIERS
        if no <= 40:
            choice_tiers[question["difficulty_target"]] += 1
            assert question["difficulty_target"] in {"E", "M", "H"}
        assert re.fullmatch(r"(DS|CO|OS|CN)\d{2}\.\d{2}", question["primary_concept"]), no
        assert question["primary_concept"].startswith(subject), no
        assert question["primary_concept_name"].strip()
        assert all(re.fullmatch(r"(DS|CO|OS|CN)\d{2}\.\d{2}", x) for x in question["supporting_concepts"]), no
        assert len(question["supporting_concepts"]) == len(set(question["supporting_concepts"])), no
        assert question["primary_concept"] not in question["supporting_concepts"], no
        assert all(question[k].strip() for k in (
            "cognitive_operation", "scenario_seed", "originality_design", "misconception_to_diagnose",
        )), no
        assert question["figure_approach"] in {"none", "svg", "code", "table", "reuse-q43"}, no
        assert re.fullmatch(r"20(?:0[9]|1\d|2[0-5])Q(?:0?[1-9]|[1-3]\d|4[0-7])", question["calibration_anchor"]), no
        assert type(question["question_written"]) is bool
        assert type(question["answer_verified"]) is bool
        assert type(question["figure_verified"]) is bool
        assert question["answer_verified"] is False or question["question_written"], no
        assert question["figure_verified"] is False or question["figure_approach"] in {"svg", "reuse-q43"}, no
        if question["figure_approach"] == "svg":
            fig_numbers.append(no)
        subject_counts[subject] += 1
        subject_points[subject] += expected_points
        count_written += int(question["question_written"])
        assert question["estimated_minutes"] > 0
        total_minutes += question["estimated_minutes"]

    assert subject_counts == EXPECTED_COUNTS, subject_counts
    assert subject_points == EXPECTED_SUBJECTS, subject_points
    assert choice_tiers == {"E": 11, "M": 23, "H": 6}, choice_tiers
    assert fig_numbers == FIGURES, fig_numbers
    assert items[43]["figure_approach"] == "reuse-q43"  # Q44
    assert math.isclose(total_minutes + data["difficulty_time_proposal"]["review_minutes"], 180, abs_tol=1e-6)
    choice_minutes = sum(q["estimated_minutes"] for q in items if q["kind"] == "choice")
    big_minutes = total_minutes - choice_minutes
    assert math.isclose(choice_minutes, data["difficulty_time_proposal"]["choice_minutes"], abs_tol=1e-6)
    assert math.isclose(big_minutes, data["difficulty_time_proposal"]["comprehensive_minutes"], abs_tol=1e-6)

    blueprint = (HERE / "blueprint.md").read_text(encoding="utf-8")
    blueprint_rows = numbered_rows(blueprint, r"^\|\s*(\d{2})\s*\|\s*\x60(?:DS|CO|OS|CN)\d{2}\.\d{2}\x60")
    assert sorted(blueprint_rows) == list(range(1, 48)), "blueprint missing or duplicated question rows"
    review = (HERE / "review.md").read_text(encoding="utf-8")
    review_rows = numbered_rows(review, r"^\|\s*Q(\d{2})\s*\|")
    assert review_rows == list(range(1, 48)), "review has missing/duplicate question slots"
    figure = (HERE / "figure-plan.md").read_text(encoding="utf-8")
    figure_rows = numbered_rows(figure, r"^\|\s*Q(\d{2})\s*\|")
    assert figure_rows == FIGURES, "figure-plan does not match JSON source"

    question_text = (HERE / "questions.md").read_text(encoding="utf-8")
    answer_text = (HERE / "solutions.md").read_text(encoding="utf-8")
    authored_numbers = numbered_rows(question_text, r"^### 第\s*(\d+)\s*题")
    solution_numbers = numbered_rows(answer_text, r"^### 第\s*(\d+)\s*题")
    assert len(authored_numbers) == len(set(authored_numbers))
    assert len(solution_numbers) == len(set(solution_numbers))
    assert all(q in range(1, 48) for q in authored_numbers + solution_numbers)
    assert sorted(authored_numbers) == sorted(q["no"] for q in items if q["question_written"])
    assert set(solution_numbers).issubset(set(authored_numbers))
    if data["status"] == "direction-only-not-questions":
        assert count_written == 0 and not solution_numbers
        assert all(q["editorial_state"] == "direction-only" for q in items)
        assert not any(q["answer_verified"] or q["figure_verified"] for q in items)

    print("[ai-set-01] ok: 47 planned slots = 40 choice / 7 comprehensive; 150 points")
    print(f"[ai-set-01] ok: subject budgets {dict(subject_points)}; difficulty {dict(choice_tiers)}")
    print(f"[ai-set-01] ok: 8 planned SVGs; {count_written}/47 questions written; {len(solution_numbers)}/47 solution headings")
    print("[ai-set-01] note: structural check only; 10/10 quality and exam-equivalent difficulty NOT verified")


if __name__ == "__main__":
    main()
