#!/usr/bin/env python3
"""逐卷生成 questions.md / solutions.md 草稿（幂等、可断点、可 --dry-run）。

数据来源：`build/_scratch/408-raw-pages/`（tools/batch_extract.py 的逐页缓存）。
  - 有文字层的页 → 直接用
  - 扫描页 → 用其 OCR 结果（method=ocr-unverified）
本脚本**只读缓存**，不改 PDF、不联网、不对整卷重跑 OCR。
唯一的例外是选择题答案 key：若缓存 OCR 漏了字母，会对**那一页**做一次
定向高倍率重识别（见 `recover_key`），并把该事实写进 notes。

产物一律 needs-review / ocr-uncertain，**绝不**写 proofread
（proofread 需人工逐题对照证据，见 docs/qa-policy.md §1）。

用法：
    tools/build_drafts.py --paper exams/2026
    tools/build_drafts.py --all [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "build" / "_scratch" / "408-raw-pages"

# 题号：1-47，后接分隔符且后面还有内容。排除 "0.0.0.0/0"、小数、页码。
Q_RE = re.compile(r"^\s*(\d{1,2})\s*[．.、]\s*(?=\S)")
OPT_RE = re.compile(r"(?<![A-Za-z0-9])([ABCD])\s*[．.、]\s*")
KEY_RE = re.compile(r"^\s*(\d{1,2})\s*[．.、]\s*([ABCD])\s*$")
Q_LEAD = re.compile(r"^\s*\d{1,2}\s*[．.、]\s*")
KEY_MISS_RE = re.compile(r"^\s*(\d{1,2})\s*[．.、]\s*$")          # 只有题号、丢了字母
ANS_Q_RE = re.compile(r"^\s*(4[1-7])\s*[．.、]\s*【答案要点】")
LEAK_WORDS = ("答案", "Key:", "<!-- ans")


# ---------------------------------------------------------------- 读取缓存
def load_pages(src_rel: str) -> list[tuple[int, str, str]]:
    d = CACHE / Path(src_rel).with_suffix("")
    if not d.is_dir():
        return []
    out = []
    for j in sorted(d.glob("page-*.json")):
        meta = json.loads(j.read_text(encoding="utf-8"))
        txt = j.with_suffix(".txt")
        out.append((meta["page"], txt.read_text(encoding="utf-8") if txt.exists() else "",
                    meta.get("method", "?")))
    return out


def segment_questions(pages) -> dict[int, dict]:
    """按原文题号切段；题号取自原文，绝不重编号。"""
    qs: dict[int, dict] = {}
    cur = None
    for page_no, text, method in pages:
        for line in text.splitlines():
            m = Q_RE.match(line)
            no = int(m.group(1)) if m else None
            if no is not None and 1 <= no <= 47:
                cur = no
                if no not in qs:
                    qs[no] = {"no": no, "page": page_no, "method": method, "lines": []}
                elif qs[no]["page"] != page_no:
                    qs[no].setdefault("cont_pages", []).append(page_no)
                qs[no]["lines"].append(line.strip())
                continue
            if cur is not None and cur in qs:
                qs[cur]["lines"].append(line.rstrip())
    for q in qs.values():
        q["text"] = "\n".join(q["lines"]).strip()
    return qs


def split_options(text: str) -> tuple[str, dict[str, str]]:
    """拆 (stem, {A..D})。选项可能一行 4 个 / 2+2 / 每行一个。"""
    text = Q_LEAD.sub("", text, count=1)          # 去掉题干开头重复的题号
    first = OPT_RE.search(text)
    if not first:
        return text.strip(), {}
    stem = text[: first.start()].strip()
    rest = text[first.start():]
    marks = list(OPT_RE.finditer(rest))
    opts: dict[str, str] = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(rest)
        letter = m.group(1)
        val = re.sub(r"\s*\n\s*", " ", rest[m.end():end]).strip()
        if letter not in opts:
            opts[letter] = val
    return stem, opts


# ---------------------------------------------------------------- 答案 key
def load_key(pages) -> tuple[dict, list, list]:
    """返回 (key, 缺字母的题号, 告警)。key 只取第 1 页。"""
    key, missing, warn = {}, [], []
    if not pages:
        return key, missing, ["答案底本无缓存"]
    page_no, text, method = pages[0]
    for line in text.splitlines():
        m = KEY_RE.match(line)
        if m and 1 <= int(m.group(1)) <= 40:
            key.setdefault(int(m.group(1)), m.group(2))
            continue
        m2 = KEY_MISS_RE.match(line)
        if m2 and 1 <= int(m2.group(1)) <= 40 and int(m2.group(1)) not in key:
            missing.append(int(m2.group(1)))
    if method != "text-layer":
        warn.append(f"key 来自 OCR(page1 method={method})")
    return key, sorted(missing), warn


def recover_key(pdf_rel: str, page_no: int, want: list[int]) -> tuple[dict, str]:
    """定向高倍率重识别**单页**，找回缺失的答案字母。返回 ({no:letter}, 说明)。"""
    if not want:
        return {}, ""
    try:
        import pypdfium2 as pdfium
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as e:
        return {}, f"无法定向重识别（缺依赖 {e}）"
    doc = pdfium.PdfDocument(str(ROOT / pdf_rel))
    try:
        img = doc[page_no - 1].render(scale=4).to_pil()
    finally:
        doc.close()
    tmp = ROOT / "build" / "_scratch" / "_keyrecover.png"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    img.save(tmp)
    result, _ = RapidOCR()(str(tmp))
    got = {}
    for item in result or []:
        m = KEY_RE.match(str(item[1]).strip())
        if m and int(m.group(1)) in want:
            got[int(m.group(1))] = m.group(2)
    return got, f"定向 scale=4 重识别 p{page_no} 找回 {sorted(got)}"


def segment_answers(pages) -> dict[int, dict]:
    """从答案 PDF 切出 41-47 的解析。末尾题延续到最后一页。"""
    out: dict[int, dict] = {}
    cur = None
    for page_no, text, method in pages:
        for line in text.splitlines():
            m = ANS_Q_RE.match(line)
            if m:
                cur = int(m.group(1))
                out[cur] = {"page": page_no, "method": method, "lines": []}
            if cur is not None:
                out[cur]["lines"].append(line.rstrip())
    for q in out.values():
        q["text"] = "\n".join(q["lines"]).strip()
    return out


# ---------------------------------------------------------------- 图片
def extract_images(pdf_rel: str, qs: dict) -> tuple[dict[int, list[str]], list[str]]:
    """按题归属导出内嵌位图到 assets/。返回 ({qno: [文件名]}, 告警)。"""
    import pymupdf
    page2q: dict[int, list[int]] = {}
    for n, q in qs.items():
        page2q.setdefault(q["page"], []).append(n)
    assets_dir = None
    found: dict[int, list[str]] = {}
    warn: list[str] = []
    doc = pymupdf.open(str(ROOT / pdf_rel))
    try:
        for page_no in sorted(page2q):
            imgs = doc[page_no - 1].get_images(full=True)
            if not imgs:
                continue
            cands = page2q[page_no]
            target = cands[0]
            if len(cands) > 1:
                warn.append(f"p{page_no} 含多题 {cands}，图归属未确认，暂挂 q{target}")
            assets_dir = assets_dir or (ROOT / "papers" / _PDIR[0] / "assets")
            for i, info in enumerate(imgs, 1):
                xref = info[0]
                pix = pymupdf.Pixmap(doc, xref)
                if pix.n - pix.alpha >= 4:            # CMYK → RGB
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                name = f"q{target}-fig{i}.png"
                pix.save(str(assets_dir / name))
                found.setdefault(target, []).append(name)
    finally:
        doc.close()
    return found, warn


# ---------------------------------------------------------------- 生成
_PDIR: list[str] = [""]

# 代码行判定：出现 C 家族关键字，或以 ; { } 结尾且缩进
CODE_KW = re.compile(
    r"\b(typedef|struct|union|enum|int|void|char|float|double|long|short|unsigned|"
    r"return|while|for|if|else|switch|case|break|continue|printf|scanf|malloc|free|"
    r"sizeof|NULL|main)\b")
MATH_O = re.compile(r"(?<!\$)O\(((?:[^()\n]|\([^()\n]*\)){1,40})\)")


def _is_code(ln: str) -> bool:
    s = ln.strip()
    if not s:
        return False
    if CODE_KW.search(s) and (len(ln) - len(ln.lstrip())) >= 2:
        return True
    return bool(re.search(r"[;{}]\s*$", s)) and (len(ln) - len(ln.lstrip())) >= 2


def embellish(text: str) -> str:
    """保守增强：给能确认的代码加围栏、给明确的 O(...) 加行内公式。
    只做**无歧义**的转换；拿不准的一律原样保留。"""
    lines = text.splitlines()
    out, i = [], 0
    while i < len(lines):
        if _is_code(lines[i]):
            j = i
            while j < len(lines) and (not lines[j].strip() or _is_code(lines[j])):
                j += 1
            block = [ln for ln in lines[i:j] if ln.strip()]
            if len(block) >= 2:
                out.append("```c")
                out.extend(block)
                out.append("```")
                i = j
                continue
        out.append(lines[i])
        i += 1
    res = "\n".join(out)
    res = MATH_O.sub(lambda m: f"$O({m.group(1)})$", res)
    return res


def render_questions(meta, qs, found, warn) -> str:
    L = [f"<!-- paper: {meta['paper_id']} | kind: questions | status: needs-review -->",
         f"# {meta['title']}", "",
         f"> 来源：`{meta['sources'][0]['path']}`（见 docs/provenance.md）",
         "> ⚠️ 本文件为机器转录草稿，**尚未逐题对照原文**。状态见 meta.yml。",
         "> 学生卷：仅含题干与选项。", ""]
    choice = sorted(n for n in qs if n <= 40)
    comp = sorted(n for n in qs if n >= 41)
    if choice:
        L += ["## 一、单项选择题（1—40 题，每题 2 分，共 80 分）", ""]
    for n in choice:
        stem, opts = split_options(qs[n]["text"])
        L += [f"### 第 {n} 题", "", embellish(stem), ""]
        for k in ("A", "B", "C", "D"):
            if k in opts:
                L.append(f"{k}. {embellish(opts[k])}")
            else:
                L.append(f"{k}. ")          # 缺项留空壳便于 QA 抓出 C4
        L.append("")
        for img in found.get(n, []):
            L += [f"![第 {n} 题图](assets/{img})", ""]
    if comp:
        L += ["## 二、综合应用题（41—47 题，共 70 分）", ""]
    for n in comp:
        L += [f"### 第 {n} 题", "", embellish(Q_LEAD.sub("", qs[n]["text"], count=1)), ""]
        for img in found.get(n, []):
            L += [f"![第 {n} 题图](assets/{img})", ""]
    return "\n".join(L).rstrip() + "\n"


def render_solutions(meta, key, ans, qs, key_note) -> str:
    L = [f"<!-- paper: {meta['paper_id']} | kind: solutions | status: needs-review -->",
         f"# {meta['title']} · 答案与解析", "",
         f"> 来源：`{meta['sources'][1]['path'] if len(meta['sources']) > 1 else '?'}`"
         f"（扫描件 OCR，未人工校对）",
         "> ⚠️ 机器转录草稿，状态见 meta.yml。", ""]
    if key_note:
        L += [f"> 🔎 答案 key 处理：{key_note}", ""]
    L += ["## 单项选择题", ""]
    for n in range(1, 41):
        a = key.get(n)
        L.append(f"### 第 {n} 题　答案：{a if a else '（缺）'}")
        L.append("")
        if not a:
            L += ["**解析**：（答案字母在源 OCR 中缺失，需人工核对原页）", ""]
    L += ["", "## 综合应用题", ""]
    for n in range(41, 48):
        blk = ans.get(n)
        L += [f"### 第 {n} 题", ""]
        if blk:
            L += [f"**答案**（源 p{blk['page']}，OCR 未校对）：", "", blk["text"], ""]
        else:
            L += ["**答案**：（源中未定位到该题答案）", ""]
    return "\n".join(L).rstrip() + "\n"


def build(paper_id: str, dry: bool, do_images: bool = True) -> bool:
    import yaml
    pdir = ROOT / "papers" / paper_id
    meta_path = pdir / "meta.yml"
    if not meta_path.is_file():
        print(f"[skip] 无 meta.yml: {paper_id}")
        return True
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    srcs = {s["role"]: s for s in meta.get("sources", [])}
    if "paper" not in srcs:
        print(f"[skip] {paper_id}: meta 缺 role=paper")
        return True

    qs = segment_questions(load_pages(srcs["paper"]["path"]))
    if not qs:
        print(f"[skip] {paper_id}: 试卷无缓存页")
        return True

    key, miss, warn = ({}, [], [])
    ans, key_note = {}, ""
    if "answer" in srcs:
        apages = load_pages(srcs["answer"]["path"])
        key, miss, warn = load_key(apages)
        ans = segment_answers(apages)

    # 题号完整性
    absent = [n for n in range(1, 48) if n not in qs]
    no_opts = [n for n in sorted(qs) if n <= 40 and not split_options(qs[n]["text"])[1]]
    print(f"[{paper_id}] 题号 {len(qs)}/47  答案key {len(key)}/40  缺字母 {miss or '无'}  "
          f"综合解析 {len(ans)}/7  缺号 {absent or '无'}  选项不全 {no_opts or '无'}")
    for w in warn:
        print(f"    warn: {w}")
    if dry:
        return True

    _PDIR[0] = paper_id
    (pdir / "assets").mkdir(parents=True, exist_ok=True)

    # 定向补救答案 key（只重识别那一页）
    if miss:
        got, note = recover_key(srcs["answer"]["path"], 1, miss)
        key.update(got)
        key_note = f"{note}；仍缺 {sorted(set(miss) - set(got)) or '无'}"
        print(f"    recover: {note}")

    found, iwarn = ({}, [])
    if do_images:
        try:
            found, iwarn = extract_images(srcs["paper"]["path"], qs)
        except Exception as e:                                   # noqa: BLE001
            iwarn.append(f"图片提取失败: {e}")
    for w in iwarn:
        print(f"    warn: {w}")

    (pdir / "questions.md").write_text(
        render_questions(meta, qs, found, warn + iwarn), encoding="utf-8")
    (pdir / "solutions.md").write_text(
        render_solutions(meta, key, ans, qs, key_note), encoding="utf-8")

    # 回写 meta.yml 的逐题状态
    lines = meta_path.read_text(encoding="utf-8").splitlines()
    out = []
    for ln in lines:
        m = re.match(r'^(\s*- \{)"no": (\d+), status: (\w+)(.*)$', ln)
        if m and int(m.group(2)) in qs:
            no = int(m.group(2))
            if no <= 40:
                st = "needs-review" if key.get(no) else "needs-review"
                note = "" if key.get(no) else "答案字母缺失，待人工核对原页"
            else:
                st = "ocr-uncertain" if no in ans else "blocked"
                note = "解析来自扫描件 OCR，未对照" if no in ans else "源中未定位到答案"
            topic = "未知"
            out.append(f'{m.group(1)}"no": {no}, status: {st}, confidence: null, '
                       f'topic: {topic}, notes: "{note}"}}')
        else:
            out.append(ln)
    meta_path.write_text("\n".join(out) + "\n", encoding="utf-8")

    print(f"    wrote {paper_id}/questions.md "
          f"({(pdir / 'questions.md').stat().st_size} B), solutions.md "
          f"({(pdir / 'solutions.md').stat().st_size} B), 图 {sum(len(v) for v in found.values())} 张")
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paper")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-images", action="store_true")
    args = ap.parse_args(argv)
    if args.all:
        ids = sorted(str(p.parent.relative_to(ROOT / "papers"))
                     for p in (ROOT / "papers").rglob("meta.yml"))
    elif args.paper:
        ids = [args.paper]
    else:
        ap.error("需要 --paper 或 --all")
    ok = True
    for i in ids:
        try:
            ok &= build(i, args.dry_run, not args.no_images)
        except Exception as e:                                    # noqa: BLE001
            print(f"[error] {i}: {type(e).__name__}: {e}", file=sys.stderr)
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
