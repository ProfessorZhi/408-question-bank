# Mock 3/4 集成候选分支说明（2026-10-17）

> 结论：候选分支已把 mock-2027/set-3、set-4 缺失的 `solutions.md` 与解答配图补齐，
> 全库 22 卷选择题答案覆盖达到 **880/880**（22 × 40），机器结构 QA 全绿、0 阻断。
> **全部逐题状态仍为 `needs-review`，不是 `proofread`；本题库不代表官方答案，也未做全面人工校对。**

## 1. 作业环境

| 项 | 实测 |
|---|---|
| hostname | `FJ-NJ-SER-1009` |
| GPU | `NVIDIA RTX A6000`（仅确认存在，未运行 GPU 作业） |
| 仓库 | `/home/fjd/workspaces/408-question-bank-dell/repo` |
| origin | `https://github.com/ProfessorZhi/408-question-bank.git` |
| 候选 worktree | `/home/fjd/workspaces/408-question-bank-dell/worktrees/mock34-integration-20261017` |
| 候选分支 | `work/408-mock34-integration-candidate-20261017` |
| 基线 | `origin/main` = `36a1989849b66c7ea9d28b5be6c7a3ff29b0dadb` |
| 来源分支 | `work/408-mock4-dell-source-review-20261017` = `97e1f17c0fd97c909467b5c3881b5fd36d706179` |

worktree 由 `git worktree add -b … origin/main` 新建；创建前确认目标路径与分支均不存在。
未修改 main、未改任何 sources PDF、未动其他 Agent 的 worktree。

## 2. 差异审阅与集成决定

### 2.1 审阅范围

逐卷比较了 `origin/main` 与来源分支的 `questions.md`、`solutions.md`、`meta.yml`、`assets/`：

| 卷 | main | 来源分支 |
|---|---|---|
| set-3 | questions 47/47；**无 solutions**；**无 assets**；meta 为空骨架（全 pending） | questions 47/47 + solutions 47/47 + 9 张题图 |
| set-4 | questions 47/47；**无 solutions**；**无 assets**；meta 为空骨架（全 pending） | questions 47/47 + solutions 47/47 + 7 张图（含 2 张解答配图） |

### 2.2 集成决定

按任务约束「仅补缺失的 solutions 与所引用解答资产；替换 main 题干/选项须逐项证明无回归」：

- ✅ **迁入** set-3、set-4 的 `solutions.md`。
- ✅ **迁入** set-4 解答正文实际引用的 2 张图：`q45-ans-graph.png`、`q46-ans-fig.png`。
- ✅ 更新 meta：41–47 由 `pending` → `needs-review`，补来源说明；未升级 `proofread`。
- ❌ **未替换** main 的 `questions.md`（理由与残差见 §5）。main 的题图/题面未动。
- ❌ 未迁入来源分支的 `draft-*.md`、recovered-lines、来源分支专属 docs。

## 3. 答案回源核验（本次独立复核）

不是照搬来源分支结论：直接渲染两份源解析 PDF 第 1 页，逐条比对 40 个字母。

| 卷 | 源 PDF | sha256 | 页数 | 文本层 | PDF 第1页表 vs solutions |
|---|---|---|---|---|---|
| set-3 | `sources/mock-2027/pdf/mock2027-set3-solution.pdf` | `afa5c823…` | 9 | 无（`pdftotext` 1 字节） | **40/40 一致** |
| set-4 | `sources/mock-2027/pdf/mock2027-set4-solution.pdf` | `252050eb…` | 8 | 无（`pdftotext` 1 字节） | **40/40 一致** |

两份试卷 PDF 的 sha256 也与 meta 一致（set-3 `dd9ec7a2…`，set-4 `a2413641…`）。
渲染方式：`pdftoppm -r 150`，目视读取，未使用字母串拼接 OCR。

答案表原始值：

```
set-3: 01B 02C 03B 04C 05D 06A 07D 08D 09D 10B
       11B 12D 13B 14C 15D 16D 17D 18C 19C 20C
       21B 22D 23D 24A 25C 26A 27D 28D 29B 30B
       31C 32D 33C 34B 35B 36A 37D 38A 39B 40A
set-4: 01B 02A 03A 04D 05C 06C 07A 08C 09B 10A
       11B 12D 13B 14A 15A 16A 17B 18C 19D 20A
       21B 22C 23B 24C 25C 26D 27B 28D 29D 30A
       31B 32D 33B 34C 35D 36C 37A 38C 39A 40D
```

## 4. 可复核 QA 结果

全部在候选 worktree 内执行，未使用 `--write-coverage` 之外的写操作：

| 命令 | 结果 |
|---|---|
| `python3 tools/qa_paper.py papers/mock-2027/set-3` | ✅ choice 40/40，comp 7/7，total 47/47，阻断 0 |
| `python3 tools/qa_paper.py papers/mock-2027/set-4` | ✅ choice 40/40，comp 7/7，total 47/47，阻断 0 |
| `python3 tools/qa_paper.py --all --write-coverage` | ✅ 22 卷全部 47/47；阻断 0；`index/coverage.md` 中 set-3/4 由 `0/40` → `40/40` |
| `python3 tools/validate_meta.py --dir papers` | ✅ 22 份 meta.yml，不合规 0 |
| `tools/audit_drafts.py --paper mock-2027/set-3` | high=0，medium=0 |
| `tools/audit_drafts.py --paper mock-2027/set-4` | high=0，medium=0 |
| 相对链接检查（22 卷全部 `*.md`） | 23 个本地链接，0 缺失 |
| `git diff --check` | 干净 |

说明：`audit_drafts.py` 不在 `origin/main` 的 `tools/` 中（仅在来源分支），本次临时从
`97e1f17` 复制运行，运行后已删除，未进入提交。

**880/880 的构成**：18 套历年真题 × 40 + mock set-1/2 × 40 + mock set-3/4 × 40 = 880。

## 5. 残差与内容缺陷清单（未解决，需后续处理）

1. **main 的 mock3/4 `questions.md` 是低质量机器 OCR 稿。** 本次按「不得无证据替换」原则保留，
   但已确认存在实质性错误，不能当作已校对文本使用。代表性例子：
   - set-3 Q2：`下列关于找的说法误的是`（应为「栈」「错误的是」）。
   - set-3 Q3：主串 OCR 为 `aabaacaadanfa`，来源分支按源页图录为 `aabaacasdafa`；字符差异会影响 KMP 比较次数。
   - set-3 Q31：main 写「100**ms**」，而选项全部是 **ns** 量级（1000/1050/1095/1140 ns），源页图为「100**ns**」。这是**使题目不自洽**的单位错误。
   - set-3 Q6/Q9/Q11 等：图权值、关键字、句首标点明显乱码。
   - set-4 Q1/Q2/Q10 等：代码、链表结点结构、选项成片乱码。
   - 结论：**建议另开 questions-promotion lane**，以来源分支的逐题源页核验稿为基线，对 94 道题逐项对照源 PDF 后再替换；本候选分支不做无证据替换。
2. **答案与 main 题面可能不完全对应。** 答案字母来自源卷答案表（与源卷题面配套），
   main 题面若因 OCR 变义（如 set-3 Q31），读者按 main 题面计算可能与答案不符。这是残差 1 的直接后果。
3. **综合题 41–47 的解析是 OCR 转写稿。** 来源分支按源页渲染图重录，但计算与结论未独立验算
   （人工闸门 C10 未做）；本次仅保证文件存在、结构完整、链接可解析。
4. **未迁入题图。** main 的 `questions.md` 不引用任何图片，故本次只迁入解答正文引用的
   `q45-ans-graph.png`、`q46-ans-fig.png`；来源分支的 9+5 张题图留在来源分支，待题面替换时一并评估。
5. **未做 `proofread`。** 22 卷所有题目状态均为 `needs-review` 或更早状态；`audit_drafts.py`
   不报高风险只说明「不像空壳/占位」，不证明内容正确。
6. **不是官方答案。** 以上均为对用户私有模拟卷源 PDF 的转录与结构核验，未与命题方确认。

## 6. 复现命令

```bash
cd /home/fjd/workspaces/408-question-bank-dell/worktrees/mock34-integration-20261017
python3 tools/qa_paper.py papers/mock-2027/set-3
python3 tools/qa_paper.py papers/mock-2027/set-4
python3 tools/qa_paper.py --all --write-coverage
python3 tools/validate_meta.py --dir papers
git diff --check
```
