#!/usr/bin/env python3
"""Validate the 408 educational knowledge graph (read-only, stdlib only).

This validates structure and provenance, NOT academic correctness of answers or
the accuracy of machine-suggested labels.
"""
from __future__ import annotations

import collections
import csv
import json
import pathlib
import re

BASE = pathlib.Path(__file__).resolve().parent
REPO = BASE.parents[2]
YEARS = set(range(2009, 2026))
REL_TYPES = {
    "prerequisite", "related", "same_mechanism",
    "cross_application", "cross_analogy",
}
METHODS = {"stem-reviewed", "keyword-candidate", "subject-range-only"}


def read_csv(name: str) -> list[dict[str, str]]:
    with (BASE / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def assert_acyclic(edges: list[dict[str, str]]) -> None:
    graph: dict[str, list[str]] = collections.defaultdict(list)
    for edge in edges:
        if edge["type"] == "prerequisite":
            graph[edge["from"]].append(edge["to"])
    color: dict[str, int] = {}

    def visit(node: str) -> None:
        if color.get(node) == 1:
            raise AssertionError(f"prerequisite graph has a cycle at {node}")
        if color.get(node) == 2:
            return
        color[node] = 1
        for successor in graph[node]:
            visit(successor)
        color[node] = 2

    for node in graph:
        visit(node)


def main() -> None:
    ont = json.loads((BASE / "concepts.json").read_text(encoding="utf-8"))
    subjects = ont["subjects"]
    assert {s["id"] for s in subjects} == {"DS", "CO", "OS", "CN"}
    chapters: dict[str, str] = {}
    concept: dict[str, str] = {}
    for subject in subjects:
        for ch in subject["chapters"]:
            assert ch["id"] not in chapters and ch["id"].startswith(subject["id"])
            chapters[ch["id"]] = subject["id"]
            for topic in ch["topics"]:
                assert topic["id"] not in concept and topic["id"].startswith(ch["id"] + ".")
                assert topic["name"].strip()
                concept[topic["id"]] = ch["id"]
    assert len(chapters) == 24 and len(concept) == 217, (len(chapters), len(concept))

    edges = read_csv("relations.csv")
    edge_keys = set()
    for e in edges:
        assert e["from"] in concept and e["to"] in concept and e["from"] != e["to"], e
        assert e["type"] in REL_TYPES and e["status"] == "editorial-hypothesis", e
        key = (e["from"], e["to"], e["type"])
        assert key not in edge_keys, e
        edge_keys.add(key)
    assert_acyclic(edges)

    questions = read_csv("exam-links.csv")
    seen = set()
    paper_text: dict[int, list[str]] = {}
    methods = collections.Counter()
    for q in questions:
        year, no = int(q["year"]), int(q["q_no"])
        assert year in YEARS and 1 <= no <= 47
        assert (year, no) not in seen
        seen.add((year, no))
        assert q["kind"] == ("choice" if no <= 40 else "comprehensive"), q
        assert q["method"] in METHODS
        methods[q["method"]] += 1
        assert q["subject"] in {"DS", "CO", "OS", "CN"}
        assert q["source_file"] == f"papers/exams/{year}/questions.md"
        primary = q["concept_id"]
        if primary:
            assert concept[primary] == q["chapter_id"] and chapters[q["chapter_id"]] == q["subject"], q
        else:
            assert not q["chapter_id"] and q["method"] == "subject-range-only", q
        secondary = q["secondary_concept_id"]
        if secondary:
            assert secondary in concept and secondary != primary, q
        if no > 40:
            assert q["method"] == "stem-reviewed" and primary
        else:
            assert q["method"] != "stem-reviewed"
        if year not in paper_text:
            paper_text[year] = (REPO / q["source_file"]).read_text(encoding="utf-8").splitlines()
        line = int(q["source_line"])
        assert 1 <= line <= len(paper_text[year]), q
        assert re.fullmatch(rf"###\s*第\s*{no}\s*题\s*", paper_text[year][line-1]), q
    assert len(seen) == 799 and all(sum(y == year for y, _ in seen) == 47 for year in YEARS)
    assert methods["stem-reviewed"] == 119
    assert methods["keyword-candidate"] == 505
    assert methods["subject-range-only"] == 175
    assert len(edges) == 115, len(edges)
    print(f"[408-kg] ok: {len(subjects)} subjects / {len(chapters)} chapters / {len(concept)} concepts / {len(edges)} relations")
    print(f"[408-kg] ok: {len(seen)} linked questions ({methods['stem-reviewed']} reviewed stems, {methods['keyword-candidate']} candidate tags, {methods['subject-range-only']} subject-only)")


if __name__ == "__main__":
    main()
