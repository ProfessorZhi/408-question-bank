# 2018–2019 真题选择题答案回源审计（2026-10-17）

本轮只做一件事：把 **2018、2019 两年 40 道选择题的答案**从本地原始 PDF 回填进
`papers/exams/<year>/solutions.md` 与 `meta.yml`。两年此前均为 **0/40**。
题干/选项未逐题校对，因此两年**一律停留 `needs-review`，不标 `proofread`**。

---

## 0. 作业环境核验（只读）

| 项 | 值 |
|---|---|
| hostname | `FJ-NJ-SER-1009` |
| GPU 证据 | `nvidia-smi -L` → `GPU 0: NVIDIA RTX A6000 (UUID: GPU-cee214cd-bb42-32a2-34bf-43edbcbe847d)`；本任务**未使用 GPU** |
| 主仓库 | `/home/fjd/workspaces/408-question-bank-dell/repo` |
| origin | `https://github.com/ProfessorZhi/408-question-bank.git` |
| 基线提交 | `97e1f17c0fd97c909467b5c3881b5fd36d706179`（"fix(mock-4): complete Q45/Q46/Q47…"） |
| 私有 worktree | `/home/fjd/workspaces/408-question-bank-dell/worktrees/answers-2018-2019-20261017` |
| 私有分支 | `work/408-answers-2018-2019-source-20261017` |
| 写入范围 | 仅 `papers/exams/2018/`、`papers/exams/2019/`、本文档 |

未触碰 `main`、未触碰他人 worktree、未改 `index/coverage.md`、未跑 `--write-coverage`、
未修改任何原 PDF（全程 `pdftotext`/`pdftoppm` 读取）。

---

## 1. 源文件

| 年份 | 路径 | sha256 | 页数 | 文本层 |
|---|---|---|---|---|
| 2018 | `sources/exams/answers/2018-answer.pdf` | `411bf95ad1c23407c4d3fa6ee1de8467524146b9ea795ffff153d6af3598b507` | 9 | 有（Adobe Paper Capture，含 OCR 错字） |
| 2019 | `sources/exams/answers/2019-answer.pdf` | `a50bd04914b55d0400655a03e5fa5f02b37ac1821107827ecaf6ab09b71b3fd6` | 12 | **无**（`pdftotext` 全文仅 12 字节，纯图像） |

两处 sha256 与各自 `meta.yml` 的 `sources[role=answer].sha256` **逐字节一致**。
两份 PDF 都来自 `neville-studio/408-exam-paper`（`docs/provenance.md` S1），属**重排/扫描底本**，
不是官方原卷；2019 扫描页带第三方店铺水印。

---

## 2. 2018：答案表是二维表，文本层顺序不可用

### 2.1 版式

`2018-answer.pdf` **物理第 1 页**「一、单项选择题」下的答案表为 **8 列 × 5 行**：

- 题号按行排布：第 1 行 1–8，第 2 行 9–16，第 3 行 17–24，第 4 行 25–32，第 5 行 33–40；
- 每题的答案字母写在该题号**右侧**。

### 2.2 文本层错位（关键陷阱）

`pdftotext` 把 40 个字母识别成**同一行 8 组、每组 5 个**，且**第 5 列题号整体被 OCR 成乱码
「5n 江泗扛」**（该乱码的坐标 x≈264–277，正好是第 5 列题号 5/13/21/29/37 的位置）。

无 `-layout` 时的文本出现顺序是：

```
AAACD  ADDDD  ACBDD  BCCBBCDBAC  CACAC  BBDCD  DACDB
```

**若按出现顺序拼成 40 个字母，第 1 题会得到 `A`（实际是 `B`），整卷 40 题全错。**
这正是任务里点名禁止的「顺序拼 OCR 字母」。

### 2.3 本次做法：按坐标聚类 + 目视核对

用 `pdftotext -bbox-layout` 取每个词的 `xMin/xMax`，按 x 聚成 8 列，得到：

| 题号列 | 该列的题号（上→下） | 文本层字母组 | 列内顺序 |
|---|---|---|---|
| 1 | 1, 9, 17, 25, 33 | `BCCBB` | B C C B B |
| 2 | 2, 10, 18, 26, 34 | `CDBAC` | C D B A C |
| 3 | 3, 11, 19, 27, 35 | `AAACD` | A A A C D |
| 4 | 4, 12, 20, 28, 36 | `ADDDD` | A D D D D |
| 5 | 5, 13, 21, 29, 37 | `ACBDD` | A C B D D |
| 6 | 6, 14, 22, 30, 38 | `CACAC` | C A C A C |
| 7 | 7, 15, 23, 31, 39 | `DACDB` | D A C D B |
| 8 | 8, 16, 24, 32, 40 | `BBDCD` | B B D C D |

同时把第 1 页渲染成 **300 dpi** 位图，分两段裁切逐格目视。两种读法 **40/40 完全一致**。

### 2.4 解析正文交叉验证

解析段落共 40 段（`N. 解析`，页码见 §4）。其中 **17 段**在正文里直接写明了答案字母
（「故选 X」「答案选 X」「答案为 X」），与答案表**逐题吻合**：

| 题号 | 解析内字母 | 表格 |
|---|---|---|
| 1 | B | B ✓ |
| 3 | A | A ✓ |
| 5 | A | A ✓ |
| 10 | D | D ✓ |
| 15 | A | A ✓ |
| 17 | C | C ✓ |
| 18 | B | B ✓ |
| 20 | D | D ✓ |
| 23 | C | C ✓ |
| 24 | D | D ✓ |
| 27 | C | C ✓ |
| 30 | A | A ✓ |
| 31 | D | D ✓ |
| 36 | D | D ✓ |
| 37 | D | D ✓ |
| 39 | B | B ✓ |
| 40 | D | D ✓ |

据此 2018 的 **40/40** 写入。逐题状态 `needs-review`、`confidence: medium`。

---

## 3. 2019：无文本层，纯目视

`2019-answer.pdf` 没有文本层（`pdftotext` 输出 12 字节），因此**无法用坐标法**；
也没有做批量 OCR（任务禁止 CPU 重型 OCR）。

做法：

1. 把**物理第 1 页**渲染成 150 dpi 整页，通读「一、单项选择题」表；
2. 再以 **300 dpi** 重新渲染，裁切为「第 1–4 行」与「第 5 行」两段逐格确认；
3. 两次读取 **40/40 一致**；
4. 第 1 页解析正文的「1. …因此选 B」「2. …因此选 B」「3. …答案选 C」与表格一致。

版式与 2018 相同：**8 列 × 5 行**，按行即 1–8、9–16、17–24、25–32、33–40。

---

## 4. 四个 40 题映射与页码

### 4.1 答案表

| 年份 | 答案表所在 | 读法 |
|---|---|---|
| 2018 | PDF **第 1 页** | 8 列 × 5 行，**按行** 1–8 / 9–16 / 17–24 / 25–32 / 33–40 |
| 2019 | PDF **第 1 页** | 同上 |

### 4.2 解析段落页码（2018，文本层可查）

| 题号 | 页 |
|---|---|
| 1–5 | 1 |
| 6–12 | 2 |
| 13–22 | 3 |
| 23–30 | 4 |
| 31–37 | 5 |
| 38–41 | 6 |
| 42–43 | 7 |
| 44–46 | 8 |
| 47 | 9 |

### 4.3 最终答案（与 `solutions.md` 逐字一致）

**2018**

```
1 B   2 C   3 A   4 A   5 A   6 C   7 D   8 B
9 C  10 D  11 A  12 D  13 C  14 A  15 A  16 B
17 C 18 B  19 A  20 D  21 B  22 C  23 C  24 D
25 B 26 A  27 C  28 D  29 D  30 A  31 D  32 C
33 B 34 C  35 D  36 D  37 D  38 C  39 B  40 D
```

**2019**

```
1 B   2 B   3 C   4 A   5 C   6 A   7 D   8 C
9 B  10 D  11 B  12 C  13 A  14 D  15 D  16 D
17 B 18 C  19 B  20 C  21 A  22 D  23 B  24 C
25 C 26 B  27 C  28 B  29 C  30 B  31 A  32 C
33 C 34 A  35 B  36 B  37 B  38 C  39 D  40 B
```

---

## 5. 剩余缺口与不确定项

1. **综合题 41–47 未转录（源里有）**。两份答案 PDF 都含「二、综合应用题」完整解答，
   此前 `solutions.md` 里的「源中未定位到该答案」是**不准确**的，本轮已改为如实指向页码：
   - 2018：41 第 6 页；42–43 第 7 页；44–46 第 8 页；47 第 9 页。
   - 2019：41 第 9 页；42 第 9–10 页；43 第 10 页；44–45 第 11 页；46–47 第 12 页。
   `meta.yml` 中 41–47 由 `blocked` 改为 `pending`（材料不缺，只是还没转录）。
2. **题干/选项未逐题校对**，所以两年都停在 `needs-review`。
3. **2018 第 38 题选项为空**（`questions.md` 只有 `A.` `B.` `C.` `D.` 四个空标签）。
   `audit_drafts.py --paper exams/2018` 报 `high=4`（四个空选项），`qa_paper.py` 报 C4
   「38(AC)」。这是**本轮之前就存在**的转录缺陷，修它需要重新对照试卷 PDF 逐词转录选项，
   不属于「答案回填」范围，故本轮**未改** `questions.md`，在此登记。
4. **底本性质**：两份答案 PDF 是第三方重排/扫描件（`docs/provenance.md` S1），2019 页脚带
   第三方店铺水印。答案表本身清晰无歧义，但**不等于官方权威源**；`confidence` 记 `medium`。
5. **未做批量 OCR，未用 GPU**；除 `pdftotext`/`pdftoppm` 外无其他转换步骤。

---

## 6. 校验结果

```
$ python3 tools/qa_paper.py papers/exams/2018
⚠️ papers/exams/2018  choice=40/40 comp=7/7 total=47/47
    ⚠️  C4 选项不齐共 1 题：38(AC)        ← 既有缺陷，见 §5.3
[qa] 1 卷，阻断 0 卷。

$ python3 tools/qa_paper.py papers/exams/2019
✅ papers/exams/2019  choice=40/40 comp=7/7 total=47/47
[qa] 1 卷，阻断 0 卷。

$ python3 tools/validate_meta.py
[validate] 22 份 meta.yml，不合规 0 份。

$ python3 tools/audit_drafts.py --paper exams/2018
[audit] exams/2018  题 47  解 47  图 16  公式(行内/块) 0/0  代码块 0
[audit] 风险: high=4 medium=0
    empty-option: 4   ← q38，见 §5.3

$ python3 tools/audit_drafts.py --paper exams/2019
[audit] exams/2019  题 47  解 47  图 4  公式(行内/块) 6/0  代码块 3
[audit] 风险: high=0 medium=0
```

**统计：2018 实补 40 条，2019 实补 40 条，合计 80 条。**

> 工具备注：`validate_meta.py --dir papers/exams` 按 `--dir/*/*/meta.yml` 取文件，
> 多传一级目录会得到「0 份」，属该工具 `--help` 示例与实际 glob 深度不一致；
> 用默认 `papers` 即可覆盖全部 22 份。
