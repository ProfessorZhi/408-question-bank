# 408 题库与 main 25f1217 的收敛报告（2026-10-18）

> **性质声明：本分支是机器转录 + 页图人工核对的草稿集合，不是官方答案，也不是可出版成品。**
> 受影响卷 `proofread` 均为 **0**；C10（数值题独立验算）**未做**。
> 机器结构 QA 全绿只表示题号/选项/答案/图片可解析，**不表示题干、算法或计算全部正确**。

## 1. 环境与精确基线

| 项 | 值 |
|---|---|
| hostname | `FJ-NJ-SER-1009` |
| GPU | `NVIDIA RTX A6000`（未运行 GPU 作业） |
| 仓库 | `/home/fjd/workspaces/408-question-bank-dell/repo`（私有 `ProfessorZhi/408-question-bank`） |
| **新 main** | `25f12172e8f74dffe2e4b12b4a696fe87388bba0` |
| 上一版 main | `6c9f11876d2d3b9e8c7638437f977577bd35bbf8` |
| **PR #8 head** | `446c78e427dde1b0c2a7618d39ef3d5927402a91` |
| 本分支/worktree | `work/408-reconciled-main25f-20261018` / `worktrees/408-reconciled-main25f-20261018` |
| 资源 | 20 核 load 0.16；available 约 9.4 GiB；PSI cpu/io/mem avg10=0.00；全程 `nice -n 15` |

本分支**精确从 `25f1217` 建立**；未改 main、未改 PR #8、未动任何来源 worktree。

## 2. 新 main 的变化

`25f1217` 仅新增/修改 set-4：

- 新增：`pages/page-002..010.txt`（9 页人工转录）、`pages.yml`、`figures.yml`、
  `assets/{q9,q37,q41,q44,q46,q47}-fig.png`（6 张局部题图）。
- 修改：`questions.md`（按源页第 2—10 页重写）、`recovered-lines.yml`。
- **未**改：set-3、2024/2025/2026、解答、`sources/`。

## 3. 集成方法与来源 SHA

### 3.1 直接 cherry-pick 的四个审校提交

| 来源分支 | 来源 SHA | 来源提交 | 本分支提交 |
|---|---|---|---|
| `work/408-mock3-choice-solutions-review-20261018` | `5801fb34aef4ee84d171603b06debfc667cac1db` | `5801fb3` | `240d6901e285bd81aae68e27da952398898889d4` |
| `work/408-exams-2024-comp-source-review-20261018` | `f2ca76d069c932200dbda5520a58bac7ece1ab22` | `f2ca76d` | `24e4be40842dc00d23526192e67e1517a82f454c` |
| `work/408-exams-2025-2026-comp-source-review-20261018` | `440a265b61a2b3321da197dcc4047943b1dbd171` | `2d2af12` | `ab3ec1a37d6c006358b31242f6ecaaace2352ab4` |
| 同上 | 同上 | `440a265` | `40b8f585dac6409d2a51e5140bfeda93cc249bac` |

四次 cherry-pick 均无冲突；结果树与各来源分支**逐文件 diff 为空**。

### 3.2 set-4：保留 main 证据，补入 PR8 解答

| 文件 | 决策 | 依据 |
|---|---|---|
| `questions.md` | **保留 main `25f1217`** | 按源页第 2—10 页人工逐页转录，`pages.yml`/`figures.yml` 有逐页/逐图证据；Q9 图与边方向有自洽校验 |
| `pages/`、`pages.yml`、`figures.yml` | **保留 main** | 原始来源映射，禁止覆盖 |
| `assets/{q9,q37,q41,q44,q46,q47}-fig.png` | **保留 main** | `figures.yml` 登记的坐标与墨迹带证据；6 张均被引用 |
| `solutions.md` | 取自 PR8 `446c78e` | main 无解答；40 个字母与源答案表第 1 页逐条一致 |
| `meta.yml` | 取自 PR8 后更新 | 47 条 `needs-review`；更新题干来源、Q1/Q9 notes、asset 名、review.qa |
| `assets/q45-ans-graph.png`、`q46-ans-fig.png` | 取自 PR8 | 解答配图，仅被 `solutions.md` 引用 |
| `docs/mock4-source-remediation-20261017.md` | 取自 PR8 | set-4 修复证据与边界记录 |

**题面内容零改动**：脚本剥离 HTML 注释与 `>` 注释块后，逐题比对 `25f1217` 与本分支
`questions.md`，**47/47 题正文完全一致**（`question-content diffs: []`）。仅补充了 PR8 的
7 条源卷疑点/不可辨说明（Q1 花括号、Q4 `M2+M2`、Q39「TCP建立」、Q42 `G`/`M`、
Q43「且则」、Q45「5类」、Q47「所下图」+ 孤立路由器图标），并更正了文件头的旧「机械转写稿」描述。

### 3.3 未纳入

- **未纳入**正在独立 QA 的模拟卷 4 详解 SHA `d1b5cf97c528fa4450b2a028f4eefc08a8b4ca69`：
  该内容尚未验收，本分支不包含其任何内容。待 QA 通过后，可按 §8 的线性 cherry-pick 计划处理。
- 未纳入 PR8 的 `docs/408-quality-rc-integration-20261018.md`（其 set-4 决策已被本报告取代）；
  未纳入 `docs/mock34-reconciled-main-20261018.md`（旧基线记录，避免与新基线混淆）。
  其余修复文档均已随四个提交带入。

## 4. 不变量

| 检查 | 结果 |
|---|---|
| set-3 选择题答案 | 40/40，与 `25f1217` 逐题一致（0 差异） |
| set-4 选择题答案 | 40/40，与 PR8 `446c78e` 逐题一致（0 差异） |
| 2024/2025/2026 选择题答案 | 各 40/40，与 `25f1217` 逐题一致（0 差异） |
| set-4 题干/选项 | 47/47 与 `25f1217` 正文完全一致 |
| main 的 set-4 证据 | `pages/`、`pages.yml`、`figures.yml`、6 张题图 sha256 全部未变 |
| main 的 set-3 证据 | `pages/`、`solution-pages/`、`figures.yml`、题图未改（本次未触碰） |

## 5. 机器 QA（本分支实测）

| 检查 | 结果 |
|---|---|
| `qa_paper.py --all --write-coverage` | ✅ 22 卷全部 `choice=40/40 comp=7/7 total=47/47`；阻断 **0**；答案覆盖 **880/880** |
| `validate_meta.py --dir papers` | ✅ 22 份，不合规 **0** |
| `audit_drafts.py` set-3/set-4/2024/2025/2026 | high=**0**；set-3/set-4/2024 medium=0；2025/2026 各 **1 medium**（Q36 `image-ownership`，**既有问题、Q36 及资产未改动**） |
| 相对链接/图片/孤立资产 | 39 个链接 0 缺失；38 张资产全部被引用、PNG 全部可解码 |
| `git diff --check` | ✅ 干净 |
| `index/coverage.md` | 仅 set-4 一行：`0/40` → `40/40` |

## 6. 源 PDF 抽样回溯

| 卷 | 抽检页 | 结果 |
|---|---|---|
| set-4 | p2（Q1） | 源页 Q1 程序段字迹偏淡，首行行尾左花括号确实不可辨 ✅（未猜补） |
| set-4 | p3（Q9） | 八顶点有向图存在，与 `figures.yml` 描述及 `q9-fig.png` 对应 ✅ |
| set-4 答案卷 | 第 1 页 | 40 个字母已与 `solutions.md` 逐条比对一致（PR8 阶段复核，本次文件哈希未变） |
| set-3 | 既有 `pages.yml`/`figures.yml` | 未改；本次仅新增 Q1–40 解析与 3 张解析图 |

## 7. 状态与剩余风险

| 卷 | 状态 | proofread |
|---|---|---|
| set-3 | 46 `needs-review` + 1 `ocr-uncertain`（Q41） | 0 |
| set-4 | 47 `needs-review` | 0 |
| 2024/2025/2026 | 各 40 `ocr-uncertain` + 7 `needs-review` | 0 |

**剩余风险（须在验收时保留）**

1. **set-4 Q1 代码缺左花括号**：源图不可辨，明确未补；参数名由调用点反证。
2. **set-3 Q42 中序后继算法仍有内容级缺陷**：从 `node` 而非 `node->right` 起找最左结点，
   条件 2 只处理直接父结点；**本任务不修**，仅登记。
3. **2026 Q41 代码花括号**：底本把 `{` 印成细竖线，嵌套按缩进推断。
4. **C10 未做**：2024/25/26 综合题、set-4 Q41–47 均未独立验算。
5. **2025/2026 Q36 图片归属**：`audit_drafts.py` 既有 medium（`q36-fig.png` 跨 36/37/38 页），未处理。
6. **源卷异文照抄未改**：set-3 Q3 `nextval[1]`；set-4 Q4/Q39/Q42/Q43/Q45/Q47 六处；
   2024/25/26 各自的十六进制分组、全角冒号等。
7. **set-4 40 道选择题详解仍为占位/未验收**：本分支的 `solutions.md` 1–40 条仍以答案字母与
   来源说明为主，未包含正在 QA 的 `d1b5cf97` 详解内容。

## 8. 待 QA 通过的 d1b5cf97 线性集成计划（仅计划，未提交内容）

1. 等独立 QA 对 `d1b5cf97c528fa4450b2a028f4eefc08a8b4ca69` 出具通过结论。
2. 核查其真实 base：若其父提交不是本分支（或其后续 RC），先确认文件集仅涉及 set-4 详解，
   且不触碰 main、其他卷、`pages/`/`figures.yml`。
3. 在本分支之上**线性 cherry-pick 该提交**（不 merge、不 force、不直接改 PR #8）。
4. 重新运行：`qa_paper.py --all --write-coverage`、`validate_meta.py --dir papers`、
   链接/资产检查、`git diff --check`，并确认 set-4 40 个答案不变、`proofread` 仍为 0。
5. 结构 PASS 后再由主控决定是否更新 PR #8。

## 9. 复现

```bash
cd /home/fjd/workspaces/408-question-bank-dell/worktrees/408-reconciled-main25f-20261018
git log --oneline -6
python3 tools/qa_paper.py --all --write-coverage
python3 tools/validate_meta.py --dir papers
git diff --check
```
