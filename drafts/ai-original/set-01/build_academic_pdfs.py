#!/usr/bin/env python3
"""Editorial A4 preview of Set01: formulas, options, vectors; answers remain isolated."""
from __future__ import annotations
import re
import subprocess
import tempfile
from pathlib import Path
import cairosvg
import fitz

ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/"previews-academic"
OUTPUT.mkdir(exist_ok=True)
RE_Q=re.compile(r"^### 第\s*(\d+)\s*题\s*$",re.M)
SCORES={41:13,42:10,43:12,44:11,45:7,46:8,47:9}

def question_pdf(md):
    md=md.split("## 一、单项选择题",1)[1]
    md=md[md.index("### 第 1 题"):]
    md=md.replace("## 二、综合应用题（第41–47题，共70分）",
                  "\\clearpage\n\n\\ExamSection{二、综合应用题}{第 41—47 题，共 70 分}")
    def q_repl(m):
        n=int(m[1])
        return rf"\ExamQ{{{n}}}" if n<=40 else rf"\BigQ{{{n}}}{{{SCORES[n]}}}"
    md=RE_Q.sub(q_repl,md)
    md=re.sub(r"(\\BigQ\{\d+\}\{\d+\})\s*\n\s*\n\s*（\d+分）",r"\1\n\n",md)
    assert sum(1 for i in range(1,41) if rf"\ExamQ{{{i}}}" in md)==40
    assert sum(1 for i in range(41,48) if rf"\BigQ{{{i}}}{{{SCORES[i]}}}" in md)==7
    return ("\\StudentCover\n\n\\ExamSection{一、单项选择题}"
            "{第 1—40 题，每题 2 分，共 80 分}\n\n"+md)

def teacher_pdf(md):
    answers={int(n):k for n,k in re.findall(
        r"^### 第\s*(\d+)\s*题\s*\n\n\*\*答案：([ABCD])。\*\*",md,re.M)}
    assert len(answers)==40 and set(answers)==set(range(1,41))
    md=md.split("## 逐题解析",1)[1]
    md=re.sub(r"^\*\*(?:验证范围|命题增量|命题增量与考纲边界)：\*\*[^\n]+\n*",
              "",md,flags=re.M)
    md=re.sub(r"^(### 第\s*\d+\s*题\s*)\n\n\*\*答案：[ABCD]。\*\*\s*",
              r"\1\n\n",md,flags=re.M)
    md=md.replace("### 第 41 题",
       "\\TeacherSection{三、综合应用题解析与评分}\n\n### 第 41 题")
    def q_repl(m):
        n=int(m[1])
        return (rf"\TeacherItem{{{n}}}{{{answers[n]}}}" if n<=40
                else rf"\TeacherBig{{{n}}}{{{SCORES[n]}}}")
    md=RE_Q.sub(q_repl,md)
    def grid():
        lines=[
          r"\begin{tabularx}{\linewidth}{@{}>{\sffamily\bfseries}l*{10}{>{\centering\arraybackslash\sffamily}X}@{}}",
          r"\toprule"]
        for base in (1,11,21,31):
            nums=" & ".join(f"{n:02}" for n in range(base,base+10))
            keys=" & ".join(r"\textbf{"+answers[n]+"}" for n in range(base,base+10))
            lines.extend(["题号 & "+nums+r" \\","答案 & "+keys+r" \\"])
            if base!=31: lines.append(r"\midrule")
        lines.extend([r"\bottomrule",r"\end{tabularx}"])
        return "\n".join(lines)
    assert sum(1 for i in range(1,41) if rf"\TeacherItem{{{i}}}{{{answers[i]}}}" in md)==40
    return ("\\TeacherCover\n\n\\TeacherSection{一、选择题答案速查}\n\n"
            "\\AnswerGrid{\n"+grid()+"\n}\n\n"
            "\\TeacherSection{二、选择题逐题解析}\n\n"+md)

def build(kind,filename):
    source=(ROOT/kind).read_text(encoding="utf-8")
    text=question_pdf(source) if kind=="questions.md" else teacher_pdf(source)
    with tempfile.TemporaryDirectory(prefix="ai408-academic-") as d:
        work=Path(d)
        (work/"assets").mkdir()
        refs=set(re.findall(r"!\[[^\]]*\]\((assets/[^)]+\.svg)\)",text))
        assert len(refs)==(14 if kind=="questions.md" else 1),refs
        for ref in refs:
            svg=ROOT/ref
            assert svg.is_file(),svg
            cairosvg.svg2pdf(url=str(svg),write_to=str(work/ref.replace(".svg",".pdf")))
        text=re.sub(r"(assets/[^)\s]+)\.svg",r"\1.pdf",text)
        (work/"content.md").write_text(text,encoding="utf-8")
        output=OUTPUT/filename
        cmd=["pandoc","content.md",
             "-f","markdown+tex_math_dollars+tex_math_single_backslash+pipe_tables+raw_tex",
             "--lua-filter="+str(ROOT/"academic-filter.lua"),
             "--pdf-engine=xelatex",
             "-H",str(ROOT/"pdf-academic-header.tex"),
             "-V","geometry:a4paper",
             "-V","geometry:top=22mm","-V","geometry:bottom=20mm",
             "-V","geometry:left=21mm","-V","geometry:right=21mm",
             "-V","fontsize=10pt","-V","linestretch=1.1",
             "-V","mainfont=Noto Serif CJK SC","-M","lang=zh-CN",
             "-o",str(output)]
        print("[build]",kind,"=>",filename,flush=True)
        subprocess.run(cmd,cwd=work,check=True)
    doc=fitz.open(output)
    txt="\n".join(page.get_text() for page in doc)
    assert 6<=len(doc)<=65,(filename,len(doc))
    assert "\ufffd" not in txt,"PDF has replacement glyphs"
    if kind=="questions.md":
        assert "一、单项选择题" in txt and "二、综合应用题" in txt
        assert "选择题答案速查" not in txt and "参考答案与详细解析" not in txt
    else:
        assert "选择题答案速查" in txt and "评分细则" in txt
    for n in (1,2,19,39,40,41,42,43,44,45,46,47):
        assert re.search(r"(?:^|\n)"+str(n)+r"\.|第\s*"+str(n)+r"\s*题",txt),(filename,n)
    assert output.stat().st_size>30000
    print("[verified]",filename,len(doc),"A4 pages",output.stat().st_size,"bytes",flush=True)
    doc.close()

if __name__=="__main__":
    build("questions.md","Set01_Student_Academic.pdf")
    build("solutions.md","Set01_Solutions_Academic.pdf")
