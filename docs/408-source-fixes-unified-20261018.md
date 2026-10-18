# 408 来源修复安全汇总分支（2026-10-18）

> **性质声明：本分支只是把已推送的、按年份来源校核的提交线性汇总，仍是机器/人工转录草稿集合；
> 不是官方答案，也不是可出版成品。** 2022/2023 的独立 QA 仍在进行，**未签核**；
> 受影响卷 `proofread` 均为 0；C10 独立学术验算未做。

## 1. 环境与基线

| 项 | 值 |
|---|---|
| hostname | `FJ-NJ-SER-1009`（Dell A6000；未用 GPU） |
| 仓库 | `/home/fjd/workspaces/408-question-bank-dell/repo`（私有 `ProfessorZhi/408-question-bank`） |
| **基线 main** | `b69c6d80ef04febe1358ae95c87fadf5dc3d7043`（`git ls-remote` 实测） |
| 本分支/worktree | `work/408-source-fixes-unified-20261018` / `worktrees/408-source-fixes-unified-20261018` |
| 预检 | 20 核；load `0.52/0.41/0.30`；MemAvailable ≈ 8.1 GiB；PSI cpu/io/mem avg10 全 0.00；`/` 余 278G |
| 预检备注 | `build/_scratch/logs/batch.lock` 为 1.7 天前 0 字节陈旧文件、无进程持有；未发现 408 工作区内活动写入进程 |

本分支**精确从 `b69c6d8` 建立**；未改 main、未创建/更新任何 PR、未动其他 Agent worktree 或源 PDF。

## 2. 六条来源提交映射

| 年份/卷 | 来源分支 | 来源 SHA | 来源提交 | 本分支提交 |
|---|---|---|---|---|
| 2022 | `work/408-exams-2022-comp-source-review-20261018` | `4ad7876ed4b2458aba37db52c8fe1c349a9edfd6` | `4ad7876` | `63f1cbd140f5f166c6cedf423e5648e607858157` |
| 2023 | `work/408-exams-2023-comp-source-review-20261018` | `8f292632261c9cdd567f449e809912f8c3dbf4ac` | `8f29263` | `f162e315bd352e4ea07bf6c5fdeaebda52479baf` |
| 2024 | `work/408-exams-2024-comp-source-review-20261018` | `f2ca76d069c932200dbda5520a58bac7ece1ab22` | `f2ca76d` | `66b4e76ba97713a9153451709e4d480f70f4040d` |
| 2025 | `work/408-exams-2025-2026-comp-source-review-20261018` | `440a265b61a2b3321da197dcc4047943b1dbd171` | `2d2af12` | `6dca8806aa29a4e8761f41de36e6148373455049` |
| 2026 | 同上 | 同上 | `440a265` | `dbd35fb039074584849eed91e3602467de8148de` |
| 模拟卷 3 选择详解 | `work/408-mock3-choice-solutions-review-20261018` | `5801fb34aef4ee84d171603b06debfc667cac1db` | `5801fb3` | `042b7e5a208858b7e324fdd7d99f6e94c20cd1cb` |

- 六次 cherry-pick **全部无冲突**（exit 0），按来源时间顺序线性保留。
- **结果树逐文件等价**：2022/2023/2024/2025/2026/set-3 分别与其来源分支 `git diff` 为空。
- 未整体 merge 任何旧候选；未触碰 `papers/mock-2027/set-4/**`、`index/coverage.md`、`tools/`、
  `sources/`、2009/2010/2017 questions（另有 owner）、`HANDOFF.md`、main、PR #7/#8。

## 3. 各卷修复范围

| 卷 | 本轮改动 | 说明 |
|---|---|---|
| 2022 | `solutions.md`、`meta.yml`、来源文档 | Q41–47 解析按源 PDF 恢复；选择题 Q1–40 未动 |
| 2023 | `solutions.md`、`meta.yml`、来源文档 | Q41–47 按源答案页重录；选择题未动 |
| 2024 | `solutions.md`、`meta.yml`、来源文档 | Q41–47 重录（水印/表格/代码修复）；选择题未动 |
| 2025 | `solutions.md`、`meta.yml`、来源文档 | Q41–47 重录；选择题未动 |
| 2026 | `solutions.md`、`meta.yml`、来源文档 | Q41–47 重录；选择题未动 |
| 模拟卷 3 | `solutions.md`、`meta.yml`、3 张解析图、来源文档 | Q1–40 解析补入；**题面、pages、figures 未动**；Q41–47 未动 |

## 4. 不变量

| 检查 | 结果 |
|---|---|
| 22 卷选择题答案 | 22 × 40 = **880 字母**，逐卷解析得 40/40 |
| 受影响 6 卷 Q1–40 字母 | 与基线 `b69c6d8` **逐题 0 差异** |
| 2022–2026 Q41–47 | 仅来源转录更新；均保持 `needs-review`，`proofread=0` |
| 模拟卷 3 Q42 | 与 main **逐字节相同**（sha256 一致）；算法瑕疵原样保留，未在本任务修改 |
| set-4 | 相对基线 **0 改动** |
| `index/coverage.md` | 与 `b69c6d8` **字节相同**（sha256 `40cab04a…`）；仍为过时的 840/880，**按任务禁止修改，未尝试修复** |

## 5. 机器校验（实测）

| 命令 | 结果 / exit |
|---|---|
| `tools/qa_paper.py --all`（**不带** `--write-coverage`） | 22 卷全部 `choice=40/40 comp=7/7 total=47/47`；阻断 **0**；exit **0** |
| `tools/validate_meta.py --dir papers` | 22 份，不合规 **0**；exit **0** |
| 图片/Markdown 相对链接/孤立资产 | 44 个链接 0 缺失；44 张资产全部被引用、PNG 全部可解码 |
| `git diff --check` | 干净；exit **0** |
| C4 图内选项 | 2009/2010/2017/set-1 各 1 题由 `options_in_figure` 登记，按既有口径认可，未误报缺选项 |

## 6. QA 状态与未决事项

- **2022 / 2023：QA_PENDING。** 独立只读 QA session 仍在运行/未签核；本分支只汇总来源修复，
  **不宣布 QA PASS**。
- **模拟卷 3 来源疑点**（来源文档已记录，未改）：
  - Q3 源文第 (1)–(4) 行均印作 `nextval[1]`，与表格下标 0–3 不一致；正文、meta、来源文档三处标注“按原印抄录、待复核”。
  - Q42 中序后继算法仍有内容级缺陷（从 `node` 而非 `node->right` 起找最左结点；条件 2 只处理直接父结点）；
    **本任务明确不修**，仅在本文与既有记录中登记。
  - Q20 指令字面模糊；Q41 顶点无编号；表格/结构部分以图片保留。
- **2024/2025/2026**：水印、表格、代码与上标已按源页修复；源卷自身异文按 `qa-policy §6` 保留。
- **C10 未做**；`proofread` 全为 0；不得宣布内容正确或可出版。

## 7. 复现

```bash
cd /home/fjd/workspaces/408-question-bank-dell/worktrees/408-source-fixes-unified-20261018
git log --oneline -7
python3 tools/qa_paper.py --all
python3 tools/validate_meta.py --dir papers
git diff --check
git diff --exit-code b69c6d8 -- index/coverage.md
```
