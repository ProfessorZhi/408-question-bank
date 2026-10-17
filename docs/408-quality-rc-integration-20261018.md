# 408 题库 Quality RC 集成报告（2026-10-18）

> **性质声明：本 RC 是机器转录 + 页图人工核对的草稿集合，不是官方答案，也不是可出版成品。**
> 受影响卷的 `proofread` 均为 **0**；C10（数值题独立验算）**未做**。
> 机器结构 QA 全绿只表示题号/选项/答案/图片可解析，**不表示题干、算法或计算全部正确**。

## 1. 基线与环境

| 项 | 值 |
|---|---|
| hostname | `FJ-NJ-SER-1009` |
| GPU | `NVIDIA RTX A6000`（仅确认存在，未运行 GPU 作业） |
| 仓库 | `/home/fjd/workspaces/408-question-bank-dell/repo`（私有 `ProfessorZhi/408-question-bank`） |
| 当前 main | `6c9f11876d2d3b9e8c7638437f977577bd35bbf8` |
| PR #8 head / RC 起点 | `6bfa64be27ec7f15206b16ca6e4b1c9f54656181` |
| 旧 main（2024/25/26 分支起点） | `36a1989849b66c7ea9d28b5be6c7a3ff29b0dadb` |
| RC 分支/worktree | `work/408-quality-rc-20261018` / `worktrees/408-quality-rc-20261018` |
| 资源 | 20 核 load 0.46；available 约 9.8 GiB；PSI avg10=0.00；全程 `nice -n 15` |

RC 精确从 `6bfa64b` 建立；未改 main、未更新 Draft PR #8、未动任何来源 worktree。

## 2. 来源分支与合入提交

| 来源分支 | 远端 SHA | merge-base | 来源提交（顺序） | RC 提交（顺序） |
|---|---|---|---|---|
| `work/408-mock3-choice-solutions-review-20261018` | `5801fb34aef4ee84d171603b06debfc667cac1db` | `6c9f118` | `5801fb3` | `fa3076e0ce0246b3e11a02a03357a394bb77f675` |
| `work/408-exams-2024-comp-source-review-20261018` | `f2ca76d069c932200dbda5520a58bac7ece1ab22` | `36a1989` | `f2ca76d` | `c475e2c4ba9f470bbf6aaf0d1d9c0a68277c10d3` |
| `work/408-exams-2025-2026-comp-source-review-20261018` | `440a265b61a2b3321da197dcc4047943b1dbd171` | `36a1989` | `2d2af12` → `440a265` | `6148bd1037a4dba26bdb746b5429b6ccfab3a523` → `5713ba5f899d293b5f2b6d0ad758f03822065268` |

- 四条 cherry-pick **全部无冲突**。
- **结果树逐文件等价性已验证**：
  - set-3：`git diff origin/work/408-mock3-choice-solutions-review-20261018 -- papers/mock-2027/set-3 docs/mock3-choice-solutions-review-20261018.md` → 空
  - 2024：`git diff origin/work/408-exams-2024-comp-source-review-20261018 -- papers/exams/2024 docs/exams-2024-comp-source-review-20261018.md` → 空
  - 2025/26：`git diff origin/work/408-exams-2025-2026-comp-source-review-20261018 -- papers/exams/2025 papers/exams/2026 docs/exams-2025-2026-comp-source-review-20261018.md` → 空
- 三个来源分支的修改路径互不重叠，且与 PR #8 的 set-4 内容不重叠；**未改动任何 questions.md**。

## 3. 文件清单（相对 `6bfa64b`）

```
新增 docs/mock3-choice-solutions-review-20261018.md
新增 docs/exams-2024-comp-source-review-20261018.md
新增 docs/exams-2025-2026-comp-source-review-20261018.md
新增 papers/mock-2027/set-3/assets/q3-kmp-process.png
新增 papers/mock-2027/set-3/assets/q6-sol-aoe.png
新增 papers/mock-2027/set-3/assets/q22-io-interface.png
修改 papers/mock-2027/set-3/meta.yml
修改 papers/mock-2027/set-3/solutions.md
修改 papers/exams/2024/meta.yml
修改 papers/exams/2024/solutions.md
修改 papers/exams/2025/meta.yml
修改 papers/exams/2025/solutions.md
修改 papers/exams/2026/meta.yml
修改 papers/exams/2026/solutions.md
```

未改：main、set-3 `pages/`、`solution-pages/`、`pages.yml`、`figures.yml`、`solution-pages.yml`、
set-3 既有 7 张题图、set-4 全部内容、任何历年 Q1–40 字母、`index/coverage.md`。

## 4. 不变量核验

### 4.1 选择题答案 40/40 不变

对 `mock-2027/set-3`、`exams/2024`、`exams/2025`、`exams/2026` 逐题脚本比对 `6bfa64b` 与 HEAD：

```
set-3: base=40 head=40 choice_diffs={}
2024 : base=40 head=40 choice_diffs={}
2025 : base=40 head=40 choice_diffs={}
2026 : base=40 head=40 choice_diffs={}
ALL_40_UNCHANGED
```

### 4.2 结构覆盖

- 全库 **22 卷**：`choice=40/40`、`comp=7/7`、`total=47/47` → 选择题答案 **880/880**。
- 2024/2025/2026 各 7 道综合题均有实质正文（约 4.5k–5.7k 字符），非空壳。
- set-3 Q1–Q40 解析逐题有实质文字（最短 Q17 为 59 字符，仍是完整结论，无占位符）。

## 5. 机器 QA

| 检查 | 结果 |
|---|---|
| `qa_paper.py --all --write-coverage` | ✅ 22 卷全部 47/47；阻断 **0**；880/880；`index/coverage.md` 无变化 |
| `validate_meta.py --dir papers` | ✅ 22 份，不合规 **0** |
| `audit_drafts.py`（set-3/set-4/2024/2025/2026） | high=**0**；2024/2026/set-3/set-4 medium=0；2025/2026 各 **1 medium**（Q36 `image-ownership`，**先于本次集成、Q36 与其资产均未改动**，见 `docs/exams-2025-2026-comp-source-review-20261018.md`） |
| 相对链接/图片/孤立资产 | 39 个链接 0 缺失；38 张资产全部被引用、PNG 全部有效 |
| `git diff --check` | ✅ 干净 |
| 源 PDF 哈希 | 2024/2025/2026 答案 PDF 的 sha256 与各自 meta 一致 |

## 6. 内容抽检

- **set-3 Q3**：`nextval` 表已录入；源文第 (1)–(4) 行均印作 `nextval[1]`，与表格下标 0–3 不一致。
  已在正文、meta Q3 notes 与来源文档**三处标注「按原印抄录、未改、待复核」**。
- **set-3 Q4**：仅含树的双亲指针结论，**未串入 Q46 的页框/位示图内容**。
- **set-3 Q20**：补入 5 段流水线逐周期表（IF/ID/EX/M/WB），与「加入 3 条 nop」结论一致。
- **set-3 Q42**：与 `6bfa64b` **逐字节相同**（sha256 段比对 `same=True`），本任务未改。
- **2024 Q41–47**：按源页重录；例 Q43 恢复 `2^5`/`log_2 32` 上标，Q46 两张伪代码表按左右两列还原；
  水印仅出现在「已去除」的说明注释中，正文无广告串。
- **2025 Q41–47 / 2026 Q41–47**：各 7 题均有实质解析；2025 斜向水印已剔除；
  2026 Q41 代码块按缩进判定嵌套，meta 明记「底本花括号印成细竖线」。

## 7. 状态与人工闸门

| 卷 | 状态分布 | proofread |
|---|---|---|
| set-3 | 46 `needs-review` + 1 `ocr-uncertain`（Q41，解析起于仍为 OCR 的第 5 页） | **0** |
| set-4 | 47 `needs-review` | **0** |
| 2024 | 40 `ocr-uncertain` + 7 `needs-review` | **0** |
| 2025 | 40 `ocr-uncertain` + 7 `needs-review` | **0** |
| 2026 | 40 `ocr-uncertain` + 7 `needs-review` | **0** |

C10 独立验算未做；未宣称官方正确性或可出版。

## 8. 剩余风险（必须在验收时保留）

1. **set-4 Q1 代码缺左花括号**：底本不可辨，明确未补；参数名由调用点反证。
2. **set-3 Q42 中序后继算法仍有内容级缺陷**：当前实现从 `node` 而非 `node->right` 起找最左结点，
   且条件 2 只处理直接父结点情形，不能覆盖沿祖先回溯。**本任务明确不修**（远程修改派发曾遭安全拦截，
   不得借本任务绕过）；只在本文与相关记录中登记。
3. **2026 Q41 代码花括号**：底本把 `{` 印成细竖线，嵌套按缩进推断，属人工判断而非逐字读出。
4. **C10 未做**：2024/25/26 综合题的机器码、地址、同步正确性、2025/26 算法结论均未独立验算。
5. **2025/2026 Q36 图片归属**：`audit_drafts.py` 报 medium（`q36-fig.png` 来自含 36/37/38 三题的页），
   属既有问题；本次只改 Q41–47，未处理。
6. **源文异文照抄未改**：set-3 Q3 `nextval[1]`；2024 Q43 全角冒号区间等；2025/2026 十六进制空格分组；
   均按 `qa-policy §6` 保留。
7. **综合题解析仍为转写稿**：2024/25/26 只保证「与源页一致」，不保证命题方答案本身正确。

## 9. 复现

```bash
cd /home/fjd/workspaces/408-question-bank-dell/worktrees/408-quality-rc-20261018
git log --oneline -5
python3 tools/qa_paper.py --all --write-coverage
python3 tools/validate_meta.py --dir papers
git diff --check
```
