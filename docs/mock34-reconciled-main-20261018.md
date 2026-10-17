# Mock 3/4 与最新 main 收敛报告（2026-10-18）

> **性质声明：本分支是机器转录 + 页图人工核对的草稿集合，不是官方答案，也不是可出版成品。**
> set-3 为 `41 ocr-uncertain / 6 needs-review`（沿用 main 的保守状态），set-4 为 `47 needs-review`；
> 两卷 `proofread` 均为 **0**；C10（数值题独立验算）**未完成**。
> 机器结构 QA 全绿只表示题号/选项/答案/图片可解析，**不表示题干或计算全部正确**。

## 1. 基线与环境

| 项 | 值 |
|---|---|
| hostname | `FJ-NJ-SER-1009` |
| GPU | `NVIDIA RTX A6000`（仅确认存在，未运行 GPU 作业） |
| 仓库 | `/home/fjd/workspaces/408-question-bank-dell/repo`（origin 私有 `ProfessorZhi/408-question-bank`） |
| **新 main 基线** | `6c9f11876d2d3b9e8c7638437f977577bd35bbf8` |
| **旧统一候选基线** | `3adf3d1110e67b08ec01d4804263853ba3a4dc80` |
| 本分支/worktree | `work/408-mock34-reconciled-main-20261018` / `worktrees/mock34-reconciled-main-20261018` |
| 资源 | 20 核 load 0.34；available 约 9.5 GiB；PSI cpu/io/mem avg10=0.00；全程 `nice -n 15` |

## 2. 分叉事实

- 新 main `6c9f118` 新增 set-3 全卷落盘：`pages/`、`solution-pages/`、`pages.yml`、`figures.yml`、
  `solution-pages.yml`、7 张题图，以及重写的 questions/solutions/meta。
- `3adf3d1` 相对新 main：**ahead 6 / behind 1**。因此**不能**对 main 直接快进，也未做整体 merge。
- 本分支从新 main 精确建立，只做**逐文件选取**。

## 3. 逐文件决策

### 3.1 set-3：全部保留 main（不采纳旧候选）

| 文件 | 决策 | 依据 |
|---|---|---|
| `questions.md` | 保留 main | 按源页 p2–p10 人工逐页转录；Q3 字符串已为 `aabaacaadaafa`，Q20 指令序列完整，Q44 三表已转 GFM 表（旧候选是图片） |
| `solutions.md` | 保留 main | 40/40 答案；Q41 含答案侧染色图；Q46 已完整（访问序列 + 4 页框表 + 页表）；页脚无 `27考研408` 污染 |
| `meta.yml` | 保留 main | 逐题来源 notes、`answer_crosscheck`、known_gaps 均更完整；状态 41 `ocr-uncertain` + 6 `needs-review` |
| `assets/q6/q38/q41/q41-ans/q45/q46/q47-*.png` | 保留 main | `figures.yml` 逐张登记坐标与墨迹带证据；7 张全部被引用 |
| `pages/`、`solution-pages/`、`pages.yml`、`figures.yml`、`solution-pages.yml` | 保留 main | 这是新 main 的源证据，禁止回退 |
| 旧候选 set-3 的 questions/solutions/meta/assets/docs | **不采纳** | 旧候选 set-3 与 main 是两套独立转录；main 证据更全且已含同类 P0 修复。旧候选资产名不同（如 `q6-aoe.png`），叠加会造成孤立资产 |

**答案字母一致性**：逐题脚本比对 main 与 `3adf3d1` 的 set-3 答案，**40/40 完全相同，0 差异**。

### 3.2 set-4：采纳旧候选（main 仍是空骨架 + OCR 乱码）

| 文件 | 决策 | 依据 |
|---|---|---|
| `questions.md` | 取自 `3adf3d1` | main 仍是乱码 OCR（Q1 `Imtuinear 11(m=n)…`）；旧候选按源页重写，修 Q1 程序段、Q9 缺图 |
| `solutions.md` | 取自 `3adf3d1` | main **无此文件**；旧候选 47 节、40 个答案 |
| `meta.yml` | 取自 `3adf3d1` | 47 条 `needs-review`，逐题 notes 描述实际状态 |
| `assets/`（8 张） | 取自 `3adf3d1` | Q1/Q9/Q37/Q41/Q44/Q46/Q47 题图 + Q45/Q46 解答图 |
| `docs/mock4-source-remediation-20261017.md` | 取自 `3adf3d1` | 记录 Q1/Q9 取证、重录边界与源卷疑点 |
| `recovered-lines.yml` | 保留 main + 加时效注释 | 数据 5 条逐条不变；仅说明其对应的旧 OCR 稿已被替换 |
| 旧候选 set-4 `recovered-lines.yml` | **不采纳** | 以 main 文件为数据源，避免无谓替换 |

所有取自 `3adf3d1` 的文件均做 sha256 逐一比对：**13/13 与源提交完全一致**。
set-3 的 questions/solutions/meta/7 张图/pages/solution-pages 均与 main `6c9f118` **逐文件 sha256 一致**。

## 4. 资产与链接

| 卷 | 资产数 | 全部被引用 | PNG 可解码 | 相对链接 |
|---|---|---|---|---|
| set-3 | 7 | ✅ | ✅ | 全部解析 |
| set-4 | 8 | ✅ | ✅ | 全部解析 |
| 合计 | 15 | ✅ | ✅ | 16 个链接，0 缺失 |

- 同名文件检查：两卷资产名不同（set-3 `q6-fig.png` 等；set-4 `q9-fig1.png` 等），无跨卷同名冲突；
  卷内每个资产都被对应 Markdown 引用，无孤立文件。
- `figures.yml`（set-3）登记的 7 处坐标与 7 张实际资产一一对应。

## 5. 原 PDF 来源回溯（本次抽检）

| 源 PDF | sha256 vs meta | 抽检页 | 结果 |
|---|---|---|---|
| `mock2027-set3-paper.pdf` | ✅ 一致 | p5 | Q31 源页明确为 **100ns**，选项 1000/1050/1095/1140ns ✅ |
| `mock2027-set3-paper.pdf` | ✅ 一致 | p7 | Q41 确有两幅无向图、顶点无标号 ✅ |
| `mock2027-set3-solution.pdf` | ✅ 一致 | — | meta 已记录答案表 + 解析流双通道互校 |
| `mock2027-set4-paper.pdf` | ✅ 一致 | p3 | Q9 确为八顶点有向图（T/R/V/S/W/Y/E/P）✅ |
| `mock2027-set4-solution.pdf` | ✅ 一致 | — | 40 个答案字母此前已与第 1 页答案表逐条比对（40/40） |

## 6. 机器 QA（本候选实测）

| 检查 | 结果 |
|---|---|
| `qa_paper.py --all --write-coverage` | ✅ 22 卷全部 `choice=40/40 comp=7/7 total=47/47`；阻断 **0**；答案覆盖 **880/880** |
| `validate_meta.py --dir papers` | ✅ 22 份，不合规 **0** |
| `audit_drafts.py --paper mock-2027/set-3` / `set-4` | high=**0**，medium=**0**（工具不在本基线，临时复制运行后已删除） |
| 图片/相对链接/孤立资产 | ✅ 15/15 资产被引用、PNG 全部有效；16 链接 0 缺失 |
| `git diff --check` | ✅ 干净 |
| `index/coverage.md` | 仅 set-4 一行：`0/40` → `40/40`（set-3 在 main 已是 40/40） |

## 7. 状态与人工闸门

- **set-3**：41 `ocr-uncertain` + 6 `needs-review`（main 按其实际来源复算，见 meta `known_gaps`）。
- **set-4**：47 `needs-review`。
- **两卷 `status: proofread` 均为 0**；`review.proofread_by` 为空。
- **C10 独立验算未做**：40 道选择题只与源答案表/解析流比对；综合题解析按源页转写，未重算。

## 8. 剩余人工疑点（未解决）

### set-3（main 已登记，本次未改）
1. Q20 指令字面模糊（`lw R2,50,16`），保留可见字面与源语义。
2. Q41 两图顶点无编号，解析只按左右图描述，未臆造顶点名。
3. Q44/Q45/Q46 的表格/结构部分以图片保留（Q44 三表已转 GFM）。
4. 源卷自身疑点照抄未改：Q41「两种情况」列三条、Q45「二级简介索引」、Q46 `256b` 小写、Q47 重复「DHCP 发送报文」。
5. 答案侧第 1–5 页仍是 OCR 草稿（选择题只取字母；Q41 解析散文未逐字核对）。

### set-4（旧候选已登记，本次未改）
1. **Q1 签名行行尾左花括号不可辨，未补入**（代码块因此缺 `{`）。
2. Q1 参数名 `arr/m/n` 由两处调用点反证，非逐字读出。
3. Q41–Q47 解析为 OCR 转写，未独立验算。
4. 源卷疑点照抄未改：Q4 `M₂+M₂`、Q39「TCP建立」重复、Q42 `G`/`M`、Q43「且则」、Q45「5类」只列 4 类、Q47 笔误与孤立路由器图标。

### 来源证据时效
- `papers/mock-2027/set-3/recovered-lines.yml`：main 已注明人工逐页转录后**条目全部下线（当前 0 条）**，文件保留用于记录历史。
- `papers/mock-2027/set-4/recovered-lines.yml`：现存 5 条，指向旧 OCR 稿；本次仅加时效说明注释，**数据逐条未变**（YAML 解析比对 `new == old`）。

## 9. 未采纳的旧候选内容

- `3adf3d1` 的 **set-3** questions/solutions/meta/assets 与 `docs/mock3-source-remediation-20261017.md`：
  与 main 的新 set-3 是两套独立转录；main 版本证据更全、含同类 P0 修复，故不叠加。
- `3adf3d1` 的 `docs/mock34-final-integration-20261018.md`：历史集成报告，不适用于本次新基线。

## 10. 复现

```bash
cd /home/fjd/workspaces/408-question-bank-dell/worktrees/mock34-reconciled-main-20261018
git log --oneline -3
python3 tools/qa_paper.py papers/mock-2027/set-3
python3 tools/qa_paper.py papers/mock-2027/set-4
python3 tools/qa_paper.py --all --write-coverage
python3 tools/validate_meta.py --dir papers
git diff --check
```
