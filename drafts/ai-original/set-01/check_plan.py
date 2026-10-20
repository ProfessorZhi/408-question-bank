#!/usr/bin/env python3
"""Validate the complete Set01 manifest; not an academic or difficulty certificate."""
from pathlib import Path
from collections import Counter
import json,re
BASE=Path(__file__).resolve().parent

def subject(n):
    if n<=11 or n in (41,42):return 'DS'
    if n<=22 or n in (43,44):return 'CO'
    if n<=32 or n in (45,46):return 'OS'
    return 'CN'

def split_sections(text):
    ms=list(re.finditer(r'^### 第\s*(\d+)\s*题\s*$',text,re.M))
    return {int(m.group(1)):text[m.end():ms[i+1].start() if i+1<len(ms)else len(text)]for i,m in enumerate(ms)}

def main():
    manifest=json.loads((BASE/'item-plan.json').read_text(encoding='utf-8'))
    assert manifest['schema']=='ai-exam-authoring-v1'
    assert manifest['status']=='complete-draft-author-checked'
    assert manifest['format']=={'minutes':180,'points':150,'choice_count':40,'comprehensive_count':7,'subject_points':{'DS':45,'CO':45,'OS':35,'CN':25}}
    state=manifest['common_item_state']
    assert state['question_written'] and state['solution_written'] and state['author_reasoning_complete']
    assert state['editorial_state']=='drafted' and not state['independent_review'] and not state['pilot_calibrated']
    items=manifest['items'];assert [q['no']for q in items]==list(range(1,48))
    qtext=(BASE/'questions.md').read_text(encoding='utf-8');stext=(BASE/'solutions.md').read_text(encoding='utf-8')
    qs=split_sections(qtext);ss=split_sections(stext)
    assert list(qs)==list(range(1,48)) and list(ss)==list(range(1,48))
    marks={41:13,42:10,43:12,44:11,45:7,46:8,47:9}
    totals=Counter();modes=Counter();figs=[]
    for q in items:
        n=q['no'];assert q['subject']==subject(n)
        assert q['points']==(2 if n<=40 else marks[n]);totals[q['subject']]+=q['points']
        assert re.fullmatch(r'(DS|CO|OS|CN)\d{2}\.\d{2}',q['primary_concept'])
        assert q['primary_concept'].startswith(q['subject']) and q['topic'].strip()
        modes[q['check_mode']]+=1
        actual=re.findall(r'!\[[^\]]*\]\(([^)]+)\)',qs[n])
        assert actual==q['figures'],(n,actual,q['figures'])
        for f in actual:assert (BASE/f).is_file();figs.append(f)
        if n<=40:
            assert re.findall(r'^([ABCD])\.\s',qs[n],re.M)==list('ABCD'),n
            assert re.search(r'\*\*答案：[ABCD]。\*\*',ss[n]),n
        else:assert '评分细则' in ss[n],n
    assert totals=={'DS':45,'CO':45,'OS':35,'CN':25}
    assert modes=={'computational-cross-check':41,'editorial-only':6}
    assert [q['no']for q in items if q['check_mode']=='editorial-only']==[20,22,23,24,29,32]
    assert len(set(figs))==len(figs)==manifest['figure_status']['student_svg_count']==14
    assert not any(f in figs for f in manifest['figure_status']['teacher_only'])
    assert len(list((BASE/'assets').glob('*.svg')))==15
    assert not re.search(r'(?:正确答案|参考答案|答案\s*[:：]\s*[ABCD])',qtext)
    for name in ['reference_q41.c','render_figures.py','verify_paper.py','verification.md','research-and-sources.md','review.md','README.md']:
        assert (BASE/name).is_file(),name
    print('[ai-set-01] PASS: 47 complete questions, 160 choices, 47 explanations, 150 points')
    print('[ai-set-01] PASS: 14 student SVG + 1 teacher-only SVG; authored, not independently approved')
    print('[ai-set-01] Scope: 41 computational / 6 editorial-only; no pilot calibration')
if __name__=='__main__':main()
