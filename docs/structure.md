# 数据组织规范

## 1. 为什么这样组织

参考上游 `DongDong20050214/408-Exam-Markdown`（**无许可，仅借鉴组织方式，不复制内容**）
的三个要点：

1. **原卷 / 分类 / 索引 三层分离** —— 原卷保真，分类便于复习，索引便于检索。
2. **索引视图是生成物** —— 不手写，由脚本从原卷重建，避免与正文不一致。
3. **图片按卷归档** —— `images/<year>/`，不散落、不外链。

我们在此之上补两件上游没做好的事：

4. **题析物理分离**（上游把答案和题目放一起，学生卷没法直接出）。
5. **每题一个可机检的状态字段**（上游的答案质量失控，正是因为缺这个）。

---

## 2. 目录约定

```
papers/exams/<year>/
├── meta.yml          # 卷元数据 + 逐题状态（机器读）
├── questions.md      # 学生卷：题干 + 选项（人读，无答案）
├── solutions.md      # 教师卷：答案 + 解析（人读）
└── assets/           # 本卷图片，本地化
    ├── q16-fig1.png
    └── q43-trace.png
```

`papers/mock-2027/set-<n>/` 同构。

**为什么 `assets/` 放在卷目录下而不是全局 `assets/`**：图片与卷同生命周期，
卷归档/移出时图片跟着走。全局 `assets/` 只放跨卷共用的图（如公共电路模板）。

---

## 3. 题号是唯一主键

- 选择题：`1`—`40`
- 综合题：`41`—`47`
- 合计 **47**。

**一切关联都用题号**，不用标题文字。质检脚本按题号集合做双向校验：
`questions.md` 的题号集合 必须 `==` `solutions.md` 的题号集合 == `{1..47}`。

这样即使题干文字被编辑，关联也不会断。

---

## 4. 文件格式

### 4.1 `questions.md`

```markdown
<!-- paper: exams/2009 | kind: questions | status: needs-review -->
# 2009 年全国硕士研究生招生考试 计算机学科专业基础综合

> 来源：`sources/exams/papers/2009.pdf`（见 docs/provenance.md S1）
> ⚠️ 本文件为转录稿，尚未逐题对照原文。状态见 meta.yml。

## 一、单项选择题（1—40 题，每题 2 分，共 80 分）

### 第 1 题

题干文字……公式用 LaTeX：$O(n\log n)$。

A. 选项一
B. 选项二
C. 选项三
D. 选项四

### 第 2 题
……

## 二、综合应用题（41—47 题，共 70 分）

### 第 41 题
……
```

**硬规则**
- **禁止任何形式的答案**：不能出现 `答案`、`Key:`、`<!-- ans: B -->`、折叠块。
  CI 会扫这些关键词。
- 题号标题格式固定为 `### 第 N 题`（脚本按此正则抽取）。
- 选项行格式固定为 `A. ` / `B. ` / `C. ` / `D. `（行首，可有序列表前缀）。
- 图片一律 `![说明](assets/xxx.png)` 相对路径。
- 公式用 `$...$`（行内）/ `$$...$$`（块）。不用图片代替可打字的公式。

### 4.2 `solutions.md`

```markdown
<!-- paper: exams/2009 | kind: solutions | status: needs-review -->
# 2009 年 408 真题 · 答案与解析

## 单项选择题

### 第 1 题　答案：B

**解析**：……

**易错点**：……

## 综合应用题

### 第 41 题

**答案**：……

**解析（分步）**：……
```

**硬规则**
- 每个 `### 第 N 题` 下必须有一行能匹配 `答案[：:]` （选择题）或 `**答案**` 。
- 题号集合必须与 `questions.md` 完全一致。

### 4.3 `meta.yml`

```yaml
paper_id: exams/2009
title: 2009 年全国硕士研究生招生考试 计算机学科专业基础综合
year: 2009
kind: exam            # exam | mock
sources:
  - role: paper
    path: sources/exams/papers/2009.pdf
    sha256: "…"
    upstream: https://github.com/neville-studio/408-exam-paper
    upstream_commit: 44302e5bc425ed63d48186ec4ab3c342fac051eb
    license: MIT (see docs/rights-and-licenses.md §1)
    confidence: medium   # high | medium | low —— 底本是重排版，非官方扫描
  - role: answer
    path: sources/exams/answers/2009-answer.pdf
    sha256: "…"
    confidence: medium
extraction:
  method: text-layer     # text-layer | ocr | manual
  tool: pymupdf 1.28.2
  date: 2026-10-16
counts:
  choice: 40
  comprehensive: 7
  total: 47
questions:
  # ⚠️ 键名 no 必须加引号：YAML 1.1 把未加引号的 `no` 解析成布尔 False，题号会静默丢失
  - {"no": 1, status: needs-review, confidence: medium, notes: ""}
  # … 1..47
review:
  proofread_by: []
  proofread_at: null
  qa: null               # 由 tools/qa_paper.py 回填
```

**逐题 `status` 取值**见 [`qa-policy.md`](qa-policy.md)。

---

## 5. 生成物（`index/` 与 `build/`）

| 路径 | 内容 | 生成者 |
|---|---|---|
| `index/sources-manifest.json` | 每个 PDF 的 sha256 / 页数 / 文本层字符数 / 图片数 | `tools/inventory.py` |
| `index/coverage.md` | 逐卷完成度、未达 47/47 的缺口明细 | `tools/qa_paper.py --all` |
| `build/<paper>-student.md` | 学生卷（无答案） | `tools/build_paper.py --student` |
| `build/<paper>-teacher.md` | 教师卷（含答案与解析） | `tools/build_paper.py --teacher` |

**生成物必须可重现**：删除 `index/`、`build/` 后重跑脚本应得到一致结果。
所以 `index/`、`build/` 里**不手工编辑**。

---

## 6. 命名规则

- 目录/文件：`小写 + 连字符`（ASCII），避免中文文件名进入脚本路径。
- 卷目录：`exams/2009`、`mock-2027/set-1`。
- 图片：`q<N>-<slug>.png`，如 `q16-fig1.png`、`q43-page-table.png`。
- 中文只出现在**文件内容**里，不出现在**路径**里。

> 理由：路径里的中文在 Windows + Git Bash + Python 三者间反复出现编码事故
> （本次任务已实测到 zip 文件名 mojibake）。内容用中文没有这个问题。
