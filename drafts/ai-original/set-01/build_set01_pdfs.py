#!/usr/bin/env python3
"""Build A4 PDFs from unchanged Set 01 Markdown and SVG artwork."""
from __future__ import annotations
import re
import subprocess
import tempfile
from pathlib import Path
import cairosvg
import fitz

ROOT = Path(__file__).resolve().parent
DEST = ROOT / "previews"
DEST.mkdir(exist_ok=True)

def make_pdf(kind: str, name: str):
    text = (ROOT / kind).read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="ai408-pdf-") as td:
        work = Path(td)
        (work / "assets").mkdir()
        for svg in sorted((ROOT / "assets").glob("*.svg")):
            cairosvg.svg2pdf(url=str(svg), write_to=str(work / "assets" / (svg.stem + ".pdf")))
        figures = re.findall(r'!\[[^\]]*\]\((assets/[^)]+\.svg)\)', text)
        assert len(figures) == (14 if kind == "questions.md" else 1), (kind, figures)
        for fig in figures:
            assert (work / fig.replace(".svg", ".pdf")).exists(), fig
        text = re.sub(r'(assets/[^)\s]+)\.svg', r'\1.pdf', text)
        if kind == "questions.md":
            text = text.replace("## 二、综合应用题（第41–47题，共70分）",
                                "\\newpage\n\n## 二、综合应用题（第41–47题，共70分）")
        else:
            text = text.replace("## 逐题解析", "\\newpage\n\n## 逐题解析")
        source = work / kind
        source.write_text(text, encoding="utf-8")
        output = DEST / name
        cmd = [
            "pandoc", source.name,
            "--from=markdown+tex_math_dollars+tex_math_single_backslash+pipe_tables+fenced_code_blocks+raw_tex",
            "--pdf-engine=xelatex", "--resource-path=.", "--no-highlight",
            "-H", str(ROOT / "pdf-header.tex"),
            "-V", "mainfont=Noto Serif CJK SC", "-V", "fontsize=10pt",
            "-V", "linestretch=1.12", "-V", "geometry:a4paper",
            "-V", "geometry:top=20mm", "-V", "geometry:bottom=19mm",
            "-V", "geometry:left=19mm", "-V", "geometry:right=19mm",
            "-M", "lang=zh-CN", "-o", str(output),
        ]
        print("Rendering", kind, "to", output.name, flush=True)
        subprocess.run(cmd, cwd=work, check=True)
    doc = fitz.open(output)
    assert 5 <= len(doc) <= 90, (output.name, len(doc))
    txt = "\n".join(page.get_text() for page in doc)
    assert "\ufffd" not in txt, "Unexpected replacement glyph"
    for n in [1, 19, 40, 41, 42, 43, 44, 45, 46, 47]:
        assert re.search(rf"第\s*{n}\s*题", txt), (output.name, n)
    if kind == "questions.md":
        assert "选择题答案表" not in txt and "参考解答" not in txt
    else:
        assert "选择题答案表" in txt and "评分细则" in txt
    assert output.stat().st_size > 30000
    print("VERIFIED", output.name, len(doc), "A4 pages", output.stat().st_size, "bytes", flush=True)
    doc.close()

if __name__ == "__main__":
    make_pdf("questions.md", "Set01_Student_Paper.pdf")
    make_pdf("solutions.md", "Set01_Answers_Explanations.pdf")
