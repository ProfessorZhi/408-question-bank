# 2016–2017 选择题答案独立回源审计（2026-10-17）

## 0. 环境、基线与资源

| 项目 | 实测 |
|---|---|
| 主机名 | `FJ-NJ-SER-1009` |
| GPU | `GPU 0: NVIDIA RTX A6000 (UUID: GPU-cee214cd-bb42-32a2-34bf-43edbcbe847d)`；本任务未使用 GPU |
| 主克隆 | `/home/fjd/workspaces/408-question-bank-dell/repo` |
| origin | `https://github.com/ProfessorZhi/408-question-bank.git`（私有） |
| 审计基线 | `origin/main` = `36a1989849b66c7ea9d28b5be6c7a3ff29b0dadb` |
| 本任务 worktree | `/home/fjd/workspaces/408-question-bank-dell/worktrees/answers-2016-2017-20261017` |
| 本任务分支 | `work/408-answers-2016-2017-independent-audit-20261017` |

资源检查：20 核，load average `0.16 / 0.25 / 0.41`，可用内存约 12 GiB，磁盘无积压；
全程 `nice -n 15`，只做首页局部渲染与坐标读取，未跑 OCR 批处理，未触碰 2010/2011/2024
运行 Agent、mock34 集成与独立 QA 的工作树。

注意：本地主克隆当时停在 `work/dell-408-transcription-20261016`（`8d29a9a`），
不是 main；本审计显式以 `origin/main` 为比较基线，worktree 也由 `origin/main` 建立。

## 1. 回源文件

| 年份 | 源文件 | sha256（与 meta.yml 一致） | 页数 | 答案表页 |
|---|---|---|---|---|
| 2016 | `sources/exams/answers/2016-answer.pdf` | `93c5cb3465c1141cfd023b17e2616f4392d97f74ff39443b1fc36b10c19c235f` | 12 | PDF 第 1 页 |
| 2017 | `sources/exams/answers/2017-answer.pdf` | `6799d0c083d9a32f499e4ee6c77be9b93cbd24d769a070ae98fd1637d67b00b2` | 10 | PDF 第 1 页 |

两卷均由 `neville-studio/408-exam-paper` 上游提供（meta 记录 upstream commit
`44302e5bc425ed63d48186ec4ab3c342fac051eb`）。底本为第三方汇编扫描件，
文本层水印关键词扫描未见「淘宝/光速/工作室」字样；但**未**据此推断其为官方答案。

## 2. 表格重建方法（不使用 text-layer 扁平顺序）

两卷第 1 页答案表均为 **8 列 × 5 行**：

- 第 1 列题号 1, 9, 17, 25, 33；第 2 列 2, 10, 18, 26, 34；……第 8 列 8, 16, 24, 32, 40。
- 题号 `n`：列 = `((n-1) mod 8) + 1`，行 = `((n-1) // 8) + 1`。
- 文本层按**列优先**输出，整列 5 个答案会被抽成 `DABAC`、`CBBDD` 这类 5 字母串；
  直接顺序拼接会错位。2016 文本层还出现 `....`、`.l975`、`31l23`、`CDB`、`BD`
  等破损串，不能作为唯一依据。

证据链采用三路：

1. **视觉**：第 1 页答案表区域 4× 渲染（`/tmp/a1617/2016-key.png`、`2017-key.png`），逐格人眼读取。
2. **文本层列分组**：按 x 坐标聚列、y 坐标聚行，核对每列 5 字母串。
3. **解析文**：按 `N. 解析` 分段，抽取 `选X` / `X正确` 做独立抽查。

## 3. 源表逐题答案

### 2016（40/40，视觉逐格核对）

| 题 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| 答案 | D | D | C | B | C | D | B | B |
| 题 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
| 答案 | B | A | D | C | D | A | C | C |
| 题 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 |
| 答案 | C | B | B | A | A | A | A | B |
| 题 | 25 | 26 | 27 | 28 | 29 | 30 | 31 | 32 |
| 答案 | C | A | B | D | A | C | D | A |
| 题 | 33 | 34 | 35 | 36 | 37 | 38 | 39 | 40 |
| 答案 | C | C | D | B | B | D | C | C |

按题号顺序串：`DDCBCDBBBADCDACCCBBAAAABCABDACDACCDBBDCC`

文本层列串可读部分：第 2 列 `DABAC`、第 5 列 `CDAAB`、第 6 列 `DAACD`、
第 7 列 `BCADC`、第 8 列 `BCBAC`，均与视觉表一致；第 3 列（应为 `CDBBD`）
与第 4 列（应为 `BCADB`）文本层破损，故以图像为准。

### 2017（40/40，视觉逐格核对）

| 题 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| 答案 | B | C | A | B | B | D | B | A |
| 题 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
| 答案 | B | B | D | C | C | A | D | A |
| 题 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 |
| 答案 | C | B | A | D | D | B | D | C |
| 题 | 25 | 26 | 27 | 28 | 29 | 30 | 31 | 32 |
| 答案 | B | D | B | D | B | D | B | B |
| 题 | 33 | 34 | 35 | 36 | 37 | 38 | 39 | 40 |
| 答案 | A | D | B | A | D | C | A | C |

按题号顺序串：`BCABBDBABBDCCADACBADDBDCBDBDBDBBADBADCAC`

文本层 7 个列串全部可读且与视觉表一致：
`CBBDD` / `ADABB` / `BCDDA` / `BCDBD` / `DABDC` / `BDDBA` / `AACBC`。

## 4. 与 `origin/main` 的逐题比较

| 年份 | origin/main | 源表重建 | 差异题号 |
|---|---|---|---|
| 2016 | `DDCBCDBBBADCDACCCBBAAAABCABDACDACCDBBDCC` | `DDCBCDBBBADCDACCCBBAAAABCABDACDACCDBBDCC` | **无（0/40）** |
| 2017 | `BCABBDBABBDCCADACBADDBDCBDBDBDBBADBADCAC` | `BCABBDBABBDCCADACBADDBDCBDBDBDBBADBADCAC` | **无（0/40）** |

结论：`origin/main` 的 2016/2017 选择题答案与底本首页二维答案表**逐题一致**，
无需修复；本分支因此**只新增本文档**，未改动任何 year 文件、meta 或 questions.md。
旧 mock4 分支的 2016 3/40、2017 5/40 仅作为背景，未用于本次比对。

## 5. 解析文交叉核对

### 2017

解析文可定位到 22 处显式「选X」，全部与源表一致：
Q11 D、Q12 C、Q13 C、Q14 A、Q15 D、Q16 A、Q17 C、Q19 A、Q20 D、Q21 D、
Q26 D、Q28 D、Q29 B、Q30 D、Q32 B、Q33 A、Q34 D、Q35 B、Q37 D、Q38 C、
Q39 A、Q40 C。**冲突 0**。

### 2016

2016 解析文没有「选X」句式，改用「X正确 / 选项X正确」抽查，命中 10 题：
Q20、Q21、Q26、Q27、Q28、Q31、Q32、Q35、Q38、Q39。

其中 Q20/Q21/Q31/Q32 初次抽取时与源表表面不一致，逐题复核后确认是
**「下列叙述中错误的是」题型**，解析里的「X正确」是在排除正确陈述，答案取错误项：

| 题 | 题型 | 解析原文要点 | 源表 | 判定 |
|---|---|---|---|---|
| 20 | 错误的是 | D 正确、B 正确、A 错误 | A | 一致；表面冲突系抽取逻辑误取最后一项「正确」 |
| 21 | 错误的是 | A 错误、B/C/D 正确 | A | 一致；同上 |
| 31 | 错误的是 | A/B/C 正确、D 错误 | D | 一致；同上 |
| 32 | 错误的是 | A 错误、B 正确、C/D 正确 | A | 一致；同上 |

其余 6 题（Q26、Q27、Q28、Q35、Q38、Q39）的「X正确」与源表直接一致。
**最终冲突 0**。该案例说明：解析文的简单关键词抽取不能替代二维表定位，尤其对
「选错误项」题型。

## 6. 状态与剩余缺口

- `papers/exams/2016/meta.yml`、`2017/meta.yml`：各 47 题全部 `needs-review`，
  `proofread` 数量 **0**；本次未改动，保持原状。
- 综合题 Q41–Q47 不在本次选择题审计范围内，未转录、未判定。源 PDF 中确有解答：
  - 2016：Q41 p8；Q42/Q43 p9；Q44/Q45/Q46 p11；Q47 p12。
  - 2017：Q41 p6；Q42/Q43 p7；Q44/Q45 p8；Q46/Q47 p9。
- `questions.md` 仍是 OCR 初稿，本次未做题干/选项校对；不因答案一致而宣称 proofread。
- 底本为第三方汇编扫描件，答案表可视但非官方答案；置信度仍按 `needs-review` 处理。

## 7. 工具校验

| 工具 | 命令 | 结果 |
|---|---|---|
| `tools/qa_paper.py` | `qa_paper.py papers/exams/2016` | `choice=40/40 comp=7/7 total=47/47`，阻断 0 |
| `tools/qa_paper.py` | `qa_paper.py papers/exams/2017` | `choice=40/40 comp=7/7 total=47/47`，阻断 0；C4 仅提示 Q8 选项在图内（meta 已登记 `options_in_figure`，非阻断） |
| `tools/validate_meta.py` | `validate_meta.py`（默认扫描 `papers/`） | 22 份 meta.yml，不合规 0 份 |
| `git diff --check` | — | 通过；工作区仅新增本文档 |

说明：`origin/main` 当前没有 `tools/audit_drafts.py`（该工具在本次基线的 `tools/`
清单中不存在），因此未运行，也未伪造其结果。
