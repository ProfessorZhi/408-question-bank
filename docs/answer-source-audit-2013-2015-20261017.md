# 2013–2015 选择题答案回源审计（2026-10-17）

## 0. 作业环境核验

| 项目 | 实测值 |
|---|---|
| 主机名 | `FJ-NJ-SER-1009`（Dell A6000 主机，非东京/Windows） |
| GPU | `GPU 0: NVIDIA RTX A6000 (UUID: GPU-cee214cd-bb42-32a2-34bf-43edbcbe847d)`，单卡；本任务未使用 GPU |
| 主克隆 | `/home/fjd/workspaces/408-question-bank-dell/repo` |
| origin | `https://github.com/ProfessorZhi/408-question-bank.git` |
| 基线提交 | `97e1f17c0fd97c909467b5c3881b5fd36d706179`（mock-4 已核验提交） |
| 本任务 worktree | `/home/fjd/workspaces/408-question-bank-dell/worktrees/answers-2013-2015-20261017` |
| 本任务分支 | `work/408-answers-2013-2015-source-20261017` |

所有编辑仅发生在上述独立 worktree；未修改 `main`、其他 worktree、`index/coverage.md`
或跨年通用文件。原 PDF 只读。

## 1. 回源文件与页码

| 年份 | 源文件 | sha256（与 meta.yml 一致） | 页数 | 答案表所在页 |
|---|---|---|---|---|
| 2013 | `sources/exams/answers/2013-answer.pdf` | `1a3b76ceeccbf3494b850f1608c1ee17d4999518961c037a3061af30023f8311` | 11 | PDF 第 1 页 |
| 2014 | `sources/exams/answers/2014-answer.pdf` | `400d22d3c21feae19a8f691c256902a3f745bb9f4fc227464ec55d94c35ffdc6` | 14 | PDF 第 1 页 |
| 2015 | `sources/exams/answers/2015-answer.pdf` | `54ff1b454f7421365f0cb744aff2f28b8825b99de0d5b8ed1e9c716de3587b47` | 8 | PDF 第 1 页 |

三份 PDF **都有文本层**，但答案表的文本层阅读顺序不可用：例如 2013 首页文本层抽成
`D 2. C 10. D 18. C 26. B 34.`，题号与字母交错；若按出现顺序拼接字母会得到错误映射。
因此本条 lane 的答案一律来自**版面定位 + 首页渲染图逐格视觉核对**，不采用顺序 OCR。

## 2. 答案表结构与题号映射方式

三份答案 PDF 第 1 页「一、单项选择题」均为标准 **8 列 × 5 行**表：

- 列：第 1 列题号 1, 9, 17, 25, 33；第 2 列 2, 10, 18, 26, 34；……第 8 列 8, 16, 24, 32, 40。
- 行：每列自上而下 5 个题号，步长为 8。
- 映射：题号 `n` 所在列 = `((n-1) mod 8) + 1`，所在行 = `((n-1) // 8) + 1`；
  字母取该题号右侧同一行的答案格。
- 列扫描顺序（跨列）才是文本层中出现的 `CACAA`、`DCBCD` 等 5 字母串的真实含义：
  每个 5 字母串是该列自上而下的 5 个答案，**不是**某一行的横向 5 题。

复核手段：

1. `pymupdf` 取第 1 页 word/char 级坐标，按 x 聚列、按 y 聚行；
2. 将第 1 页答案表区域以 4× 渲染为 PNG，逐格人眼核对；
3. 用解析文中的 `N. 解析 … 选X` 对 2014/2015 做独立抽查。

## 3. 逐年答案（源 PDF 第 1 页，逐格视觉核对）

### 2013（40/40）

| 题 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| 答案 | D | C | D | B | A | C | C | D |
| 题 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
| 答案 | C | A | C | C | A | A | C | A |
| 题 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 |
| 答案 | D | C | B | B | B | D | A | A |
| 题 | 25 | 26 | 27 | 28 | 29 | 30 | 31 | 32 |
| 答案 | C | A | C | B | D | B | B | B |
| 题 | 33 | 34 | 35 | 36 | 37 | 38 | 39 | 40 |
| 答案 | B | A | D | B | A | B | B | A |

### 2014（40/40）

| 题 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| 答案 | C | B | A | D | C | D | D | D |
| 题 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
| 答案 | D | B | C | D | C | A | A | D |
| 题 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 |
| 答案 | A | C | C | C | D | B | A | B |
| 题 | 25 | 26 | 27 | 28 | 29 | 30 | 31 | 32 |
| 答案 | D | A | A | C | B | A | C | D |
| 题 | 33 | 34 | 35 | 36 | 37 | 38 | 39 | 40 |
| 答案 | C | B | D | C | B | A | B | D |

### 2015（40/40）

| 题 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| 答案 | A | B | D | D | D | C | A | C |
| 题 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
| 答案 | C | C | A | A | B | D | C | B |
| 题 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 |
| 答案 | B | D | C | B | B | D | B | C |
| 题 | 25 | 26 | 27 | 28 | 29 | 30 | 31 | 32 |
| 答案 | D | B | A | A | B | C | C | C |
| 题 | 33 | 34 | 35 | 36 | 37 | 38 | 39 | 40 |
| 答案 | D | A | B | B | A | C | A | C |

## 4. 与既有答案的冲突检查

回填前各年仅有 5 条答案（均为上表第 1 列的 5 题）：

| 年份 | 既有答案 | 与源表比对 |
|---|---|---|
| 2013 | 1=D, 9=C, 17=D, 25=C, 33=B | 全部一致，未覆盖 |
| 2014 | 1=C, 9=D, 17=A, 25=D, 33=C | 全部一致，未覆盖 |
| 2015 | 1=A, 9=C, 17=B, 25=D, 33=D | 全部一致，未覆盖 |

**未发现既有答案与源表冲突**，因此没有需要修正的 OCR 错位条目。

独立交叉核对：

- 2014 解析文中可定位到 37 处 `选X`，与源表逐题一致（其中 Q27 的 `选A`
  被多栏 OCR 顺序错误归到相邻题段，属解析文分段噪声，不是答案冲突；Q27 源表与解析原文均为 A）。
- 2015 解析文中可定位的显式 `选X`（Q5=D、Q38=C）与源表一致。

## 5. 剩余缺口与不确定项

1. **综合应用题 Q41–Q47 未转录。** 源 PDF 中确有解答：
   - 2013：Q41 p6；Q42/Q43 p8；Q44/Q45 p9；Q46/Q47 p10。
   - 2014：Q41 p7；Q42 p9；Q43/Q44 p11；Q45 p12；Q46/Q47 p13。
   - 2015：Q41/Q42 p6；Q43–Q45 p7；Q46/Q47 p8。
   这些是完整解答而非单字母答案，且本轮任务限定 40 道选择题，故仅把 meta 中
   Q41–Q47 的状态从 `blocked` 纠正为 `pending` 并标注页码，未回填内容。
2. **底本性不确定。** 三份答案 PDF 是第三方汇编扫描件，不是考试院官方答案：
   2013 底本第 3 页带「淘宝店铺：光速考研工作室」水印；2014/2015 未见可提取水印文字。
   因此即使答案表清晰可读，也**不把状态改成 `proofread`**，全部保持 `needs-review`。
3. **文本层不可作为映射依据。** 本报告已说明答案表的文本层顺序错乱；
   任何后续自动化处理都必须按坐标/版面重建列，禁止顺序拼接。
4. **未校对题干/选项。** `questions.md` 仍是 OCR 初稿，本 lane 未做逐题题干校对，
   不因答案已回填而宣称 proofread。

## 6. 校验结果（目标年份，未写全库 coverage）

| 工具 | 命令 | 结果 |
|---|---|---|
| `tools/validate_meta.py`（venv-compare） | `validate_meta.py` | 22 份 meta.yml，不合规 0 份 |
| `tools/qa_paper.py` | `qa_paper.py papers/exams/2013` | choice 40/40, comp 7/7, total 47/47，阻断 0 |
| `tools/qa_paper.py` | `qa_paper.py papers/exams/2014` | 47/47，阻断 0；**既有** C4 警告：Q37 选项 A 为空/缺 B（见下） |
| `tools/qa_paper.py` | `qa_paper.py papers/exams/2015` | 47/47，阻断 0 |
| `tools/audit_drafts.py` | `--paper exams/2013` | high=0 medium=0 |
| `tools/audit_drafts.py` | `--paper exams/2014` | high=1（existing `empty-option` q37），medium=0 |
| `tools/audit_drafts.py` | `--paper exams/2015` | high=0 medium=0 |

2014 Q37 的 high 风险是**既有 questions.md OCR 缺陷**，与本次答案回填无关：
当前文本为「站点 / A. / B. C 通过CDMA 共享链路，/ C. 110 / D. 111」，
选项 A 为空且 B 标签与正文粘连。本 lane 只回源答案，不改题干/选项，故仅记录，
不宣称该卷 proofread；建议由题干校对 lane 对照 `sources/exams/papers/2014.pdf` 修复。

## 7. 可复现命令（只读源 PDF）

```bash
# 坐标级检查（venv 内有 pymupdf）
/home/fjd/workspaces/408-question-bank-dell/venv/bin/python - <<'PY'
import pymupdf
p="sources/exams/answers/2013-answer.pdf"
d=pymupdf.open(p); pg=d[0]
for w in pg.get_text("words"):
    print(w[:4], w[4])
PY

# 首页答案表区域 4× 渲染
/home/fjd/workspaces/408-question-bank-dell/venv/bin/python - <<'PY'
import pymupdf
d=pymupdf.open("sources/exams/answers/2013-answer.pdf")
pix=d[0].get_pixmap(matrix=pymupdf.Matrix(4,4), clip=pymupdf.Rect(30,160,560,285))
pix.save("/tmp/2013-key.png")
PY
```
