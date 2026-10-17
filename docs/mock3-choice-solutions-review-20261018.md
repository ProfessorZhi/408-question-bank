# Mock 2027 Set-3 选择题解析回源录入记录（2026-10-18）

## 0. 环境与基线

| 项目 | 实测 |
|---|---|
| 主机名 | `FJ-NJ-SER-1009` |
| GPU | `NVIDIA RTX A6000`（UUID `GPU-cee214cd-…`）；未使用 GPU |
| 仓库 | `/home/fjd/workspaces/408-question-bank-dell/repo` |
| origin | `https://github.com/ProfessorZhi/408-question-bank.git`（私有） |
| 基线 SHA | `6c9f11876d2d3b9e8c7638437f977577bd35bbf8`（= 当前 `origin/main`） |
| 本任务 worktree | `worktrees/mock3-choice-solutions-review-20261018` |
| 本任务分支 | `work/408-mock3-choice-solutions-review-20261018` |

资源：20 核，load `0.38/0.35/0.32`，可用内存约 9.3 GiB；全程 `nice -n 15`，
只读源 PDF、只按页局部渲染，未跑批量 OCR，未使用 GPU，未触碰其他 worktree。

## 1. 源文件与范围

- 只读源：`sources/mock-2027/pdf/mock2027-set3-solution.pdf`（9 页扫描件，无文本层）。
- 选择题解析位于 **p1–p5**；p6–p9 是综合题，未触碰。
- 只修改 `papers/mock-2027/set-3/solutions.md` 的 Q1–Q40 正文、`meta.yml` 的 Q1–Q40 notes，
  以及新增本卷 `assets/` 中 3 张解析配图；Q41–Q47、questions.md、main、其他卷/年份均未改动。

## 2. 录入方式

按页 4× 渲染后人工逐题读取，逐题确认题号、答案字母与解析段落；题号与解析页配对如下：

| 题号 | 解析页 |
|---|---|
| Q1–Q3 | p1（Q3 跨 p1–p2） |
| Q4–Q13 | p2 |
| Q14–Q22 | p3 |
| Q23–Q34 | p4（Q34 跨 p4–p5） |
| Q35–Q40 | p5 |

每 10 题做一次配对检查（Q1–10 / Q11–20 / Q21–30 / Q31–40），40 个标题、40 个答案、
40 段 `【解析】` 均齐备；答案串
`BCBCDADDDBBDBCDDDCCCBDDACADDBBCDCBBADABA` 与 main 原 40/40 及卷首答案表完全一致。

## 3. 重点复核项

### Q4：确认是双亲表示树的 n-1，不是 Q46 页框表

源解析 p2 原文：

> 每个指向双亲的指针都对应树中的一个分支，含有 n 个结点的树中最少有 n-1 个分支。

已写入 Q4。程序化检查 Q4 正文含 `n-1`，且不含“页框”字样。旧候选把 Q46 页框表混入 Q4
的问题未复现。

### Q11 / Q17：确认有真正文

- Q11（p2）：完整转录五趟排序过程与“再需一趟无交换排序”的结论，共 272 字符。
- Q17（p3）：源文只有一句“一条机器指令对应一个微程序，微程序由微指令序列构成。”，
  按原样录入（62 字符），未因短而补写。

### Q20：流水段表按原图逐格复核

源解析 p3 的 5 段流水线表（IF/ID/EX/M/WB，列 1–10）逐格转录为 GFM 表：

| 指令 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| I1 | IF | ID | EX | M | WB |  |  |  |  |  |
| I2 |  | IF | ID | EX | M | WB |  |  |  |  |
| nop |  |  | IF | ID | EX | M | WB |  |  |  |
| nop |  |  |  | IF | ID | EX | M | WB |  |  |
| nop |  |  |  |  | IF | ID | EX | M | WB |  |
| I3 |  |  |  |  |  | IF | ID | EX | M | WB |

结论“需要在第 3 条指令前加入 3 条 nop”与表一致。

### Q3：nextval 表与源文异文

nextval 表按 p1 原表转录：

| 下标 j | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 模式串 | a | a | d | a |
| nextval | -1 | -1 | 1 | -1 |

匹配过程按 p1–p2 原文录入，合计 `3+1+3+1+4=12` 次，与答案 B 一致。

**源文异文（未改）**：源解析第 (1)–(4) 行均印作 `nextval[1]`，与上方表格下标 0–3
不一致。已在 Q3 正文就地标注“按原印抄录，未改，待复核”，并在 `meta.yml` Q3 notes 记录。
未凭推导改成 `nextval[j]` 或 `nextval[0..3]`。

### 配图（只放本卷 assets，标来源页）

| 文件 | 来源 | 用途 |
|---|---|---|
| `assets/q3-kmp-process.png` | 解析 p1 | nextval 表 + 5 步匹配示意 |
| `assets/q6-sol-aoe.png` | 解析 p2 | 删除非关键边后的 AOE 网（叉号） |
| `assets/q22-io-interface.png` | 解析 p4 | I/O 接口功能与基本结构 |

均为局部裁切，未使用整页截图；Q22 原解析“如下图所示”因此不再悬空。

## 4. 状态与限制

- Q1–Q40 的 `meta.yml` 状态由 `ocr-uncertain` 改为 `needs-review`（已人工对照页图录入，
  但未逐题验算/未 proofread）；**`proofread` 数量为 0**。
- 未做 C10 独立验算；解析只按源文录入，不宣称数学/算法结论已独立验证。
- Q3 的 `nextval[1]` 源文异文保留待复核。
- Q6 的解析图是“删除非关键边后”的标注图，未在正文另行推导每条 ve 值。
- 扫描件个别字形（如 Q3 首个 S 字符、Q20 指令字面）仍有轻微模糊；以页图可辨为准，
  不自行补字。

## 5. 校验

| 工具 | 结果 |
|---|---|
| `qa_paper.py papers/mock-2027/set-3` | `choice=40/40 comp=7/7 total=47/47`，阻断 0 |
| `validate_meta.py` | 22 份 meta.yml，不合规 0 |
| 相对图片引用 | 4/4 存在（含未改动的 Q41 图） |
| `git diff --check` | 通过 |
| 题号/页码配对 | 4 个十题段全部通过；40 答案与源表一致 |

## 6. 变更文件

- `papers/mock-2027/set-3/solutions.md`（Q1–Q40 正文；Q41–Q47 未动）
- `papers/mock-2027/set-3/meta.yml`（Q1–Q40 notes/status）
- `papers/mock-2027/set-3/assets/q3-kmp-process.png`
- `papers/mock-2027/set-3/assets/q6-sol-aoe.png`
- `papers/mock-2027/set-3/assets/q22-io-interface.png`
- `docs/mock3-choice-solutions-review-20261018.md`（本文档）
