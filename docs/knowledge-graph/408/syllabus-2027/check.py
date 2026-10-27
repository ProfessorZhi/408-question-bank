#!/usr/bin/env python3
"""Read-only consistency checks for 2027 public-outline / Wangdao mappings.

Academic scope judgments, publisher metadata authenticity, and item quality are
NOT established by this script. It checks internal IDs and editorial traceability.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
GRAPH = HERE.parent
SUBJECTS = ("DS", "CO", "OS", "CN")
WEIGHTS = {"DS": 45, "CO": 45, "OS": 35, "CN": 25}
EXPECTED_SECTIONS = {"DS": 37, "CO": 33, "OS": 24, "CN": 33}
EXPECTED_TARGETS = {"DS": 113, "CO": 113, "OS": 87, "CN": 113}
SOURCE_TIERS = {
    "book-extension",
    "outline-explicit-finer-granularity",
    "mixed-editorial-detail",
}


def table(name: str) -> list[dict[str, str]]:
    with (HERE / name).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    ontology = json.loads((GRAPH / "concepts.json").read_text(encoding="utf-8"))
    assert {s["id"] for s in ontology["subjects"]} == set(SUBJECTS)

    chapters: dict[str, str] = {}
    nodes: dict[str, dict[str, str]] = {}
    for subject in ontology["subjects"]:
        sid = subject["id"]
        for chapter in subject["chapters"]:
            cid = chapter["id"]
            assert cid not in chapters
            chapters[cid] = sid
            for node in chapter["topics"]:
                nid = node["id"]
                assert nid not in nodes
                nodes[nid] = {"chapter_id": cid, "subject": sid, "name": node["name"]}

    assert len(chapters) == 24
    assert len(nodes) == 217

    mapped: dict[str, set[str]] = defaultdict(set)
    section_ref: dict[str, dict[str, str]] = {}
    section_totals: Counter[str] = Counter()
    target_totals: Counter[str] = Counter()

    for sid in SUBJECTS:
        syllabus = json.loads((HERE / f"{sid}.json").read_text(encoding="utf-8"))
        assert syllabus["version"] == "2027" and syllabus["subject"] == sid
        assert syllabus["weight"] == WEIGHTS[sid]
        assert syllabus["official_metadata_url"].startswith("https://www.hep.com.cn/")
        assert syllabus["syllabus_evidence"].startswith("https://")
        assert syllabus["wangdao_publisher_url"].startswith("https://")
        assert re.fullmatch(r"\d{13}", syllabus["wangdao_isbn"])
        assert (HERE / f"{sid}.md").is_file()

        markdown = (HERE / f"{sid}.md").read_text(encoding="utf-8")
        for section in syllabus["sections"]:
            secid = section["id"]
            cid = section["chapter_id"]
            assert re.fullmatch(rf"{sid}\d{{2}}-S\d{{2}}", secid), secid
            assert secid not in section_ref and chapters.get(cid) == sid, secid
            assert section["alignment"] == "syllabus-area-editorial-decomposition"
            assert section["title"].strip() and f"### {section['title']}" in markdown
            assert section["learning_targets"] and all(
                isinstance(t, str) and t.strip() for t in section["learning_targets"]
            )
            assert section["concept_ids"] and len(section["concept_ids"]) == len(set(section["concept_ids"]))
            for nid in section["concept_ids"]:
                assert nid in nodes and nodes[nid]["subject"] == sid, (secid, nid)
                mapped[nid].add(secid)
            section_ref[secid] = {"subject": sid, "chapter_id": cid}
            section_totals[sid] += 1
            target_totals[sid] += len(section["learning_targets"])

        assert section_totals[sid] == EXPECTED_SECTIONS[sid]
        assert target_totals[sid] == EXPECTED_TARGETS[sid]
        assert syllabus["book_extras"] and all(
            ext["status"].strip() and ext["note"].strip()
            for ext in syllabus["book_extras"]
        )

    crosswalk = table("concept-crosswalk.csv")
    assert len(crosswalk) == 217
    seen = set()
    for line in crosswalk:
        nid = line["concept_id"]
        assert nid in nodes and nid not in seen, nid
        seen.add(nid)
        assert line["subject"] == nodes[nid]["subject"]
        assert line["chapter"] == nodes[nid]["chapter_id"]
        assert line["name"] == nodes[nid]["name"]
        asserted = set(filter(None, line["section_ids"].split(";")))
        assert asserted == mapped.get(nid, set()), nid
        assert line["review_status"] == "expert-review-pending-official-fulltext"

    unmapped = set(nodes) - set(mapped)
    assert unmapped == {"DS05.10"}, unmapped

    proposals = json.loads((HERE / "gap-proposals.json").read_text(encoding="utf-8"))
    assert proposals["year"] == 2027
    assert len(proposals["items"]) == 18
    pids: set[str] = set()
    for p in proposals["items"]:
        assert p["id"] not in pids and re.fullmatch(r"P\d{3}", p["id"])
        pids.add(p["id"])
        assert p["chapter_id"] in chapters
        assert p["scope_tier"] in SOURCE_TIERS
        assert p["promotion_status"] == "proposed-not-added-to-217-node-ontology"
        assert p["title"].strip() and p["evidence"].strip() and p["reason"].strip()

    book_map = {
        sid: json.loads((HERE / f"{sid}.json").read_text(encoding="utf-8"))["wangdao_publisher_url"]
        for sid in SUBJECTS
    }
    chapter_links = table("chapter-crosswalk.csv")
    assert len(chapter_links) == 24
    cid_seen = set()
    for row in chapter_links:
        cid = row["chapter_id"]
        assert cid in chapters and cid not in cid_seen
        cid_seen.add(cid)
        assert chapters[cid] == row["subject_id"]
        assert row["wangdao_publisher_url"] == book_map[row["subject_id"]]
        assert row["public_outline_url"] == "https://zhenti.beokayy.club/outline"
        assert row["review_status"] == "editorial-mapping-not-official-verified"
        assert row["public_outline_area"].strip() and row["wangdao_book_area"].strip()

    assert (HERE / "README.md").is_file()
    assert (HERE / "source-audit.md").is_file()
    print("[408-syllabus] ok: 4 subjects / 24 chapters / 127 editorial study units / 426 learning targets")
    print("[408-syllabus] ok: 217 concept crosswalk (216 linked; 1 historical extension DS05.10)")
    print("[408-syllabus] ok: 18 labeled gap proposals / 24 chapter references")
    print("[408-syllabus] warning: source-outline detail is third-party transcription; official full text not independently verified")


if __name__ == "__main__":
    main()
