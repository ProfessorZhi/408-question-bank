# Mock 3/4 最终集成报告（2026-10-18）

> **性质声明：本候选分支是机器转录 + 源页图人工核对的草稿集合，不是官方答案，也不是可出版成品。**
> set-3/set-4 各 47 题状态均为 `needs-review`；`proofread` 计数 **0/47 / 0/47**；
> 人工闸门 C10（数值题独立验算）**未完成**。机器结构 QA 全绿只表示题号/选项/图片/答案可解析，
> **不表示题干或计算全部正确**。

## 1. 作业环境

| 项 | 实测 |
|---|---|
| hostname | `FJ-NJ-SER-1009` |
| GPU | `NVIDIA RTX A6000`（仅确认存在，未运行 GPU 作业） |
| 仓库 | `/home/fjd/workspaces/408-question-bank-dell/repo` |
| origin | `https://github.com/ProfessorZhi/408-question-bank.git`（私有） |
| 集成 worktree | `worktrees/mock34-final-integration-20261018` |
| 集成分支 | `work/408-mock34-final-integration-20261018` |
| 集成起点 | `9c3000f98de0d9ed9495359bb583fa433f83a169` |
| 资源 | 20 核，load 0.09；可用内存约 10 GiB；PSI cpu/io/mem avg10 均为 0.00；全程 `nice -n 15` |

## 2. 真实来源与合并记录

### 2.1 来源分支（远端已核验）

| 分支 | 远端 SHA | 相对 9c3000f | 提交（时间顺序） |
|---|---|---|---|
| `work/408-mock3-questions-source-fix-20261017` | `e08bdfe914e0d90b62712c47f364e948fb3f2399` | ahead 2 | `03d0e35f657f13b2a018a02557ce18f799361ba7` → `e08bdfe914e0d90b62712c47f364e948fb3f2399` |
| `work/408-mock4-questions-source-fix-20261017` | `34463f43b2d9ed72bcaf066a193037bb893ee190` | ahead 2 | `4bbae14871971967eab4abc7cb02f1e70b892ec5` → `34463f43b2d9ed72bcaf066a193037bb893ee190` |

两分支的 merge-base 均为 `9c3000f`，与任务给定一致。

### 2.2 集成提交（本分支线性 cherry-pick）

| 本分支提交 | 来源提交 | 内容 |
|---|---|---|
| `9573a538adde4f4e65039302b277bea74256ccc3` | `03d0e35` | set-3 解析 P0：Q41 染色图、Q46 补完、页脚污染清理 |
| `0f85c673a449438a60a89be60ebb6faa53db97e4` | `e08bdfe` | set-3 题面按源页 p2–p10 重写 + 8 张局部裁图 |
| `82d27ff8c7affcde7f5f81cec31992febc9e8039` | `4bbae14` | set-4 题面重写 + Q1/Q9 P0 + 6 张裁图 |
| `56fab68f786a9316695f4bdc21956cd4693b52ec` | `34463f4` | set-4 学生卷清理、meta 同步、修复记录 |

- 四次 cherry-pick **均无冲突**；文件集不相交（set-3 vs set-4，文档各自独立）。
- **结果树逐文件等价性已验证**：
  - `git diff origin/work/408-mock3-questions-source-fix-20261017 -- papers/mock-2027/set-3 docs/mock3-source-remediation-20261017.md` → 空
  - `git diff origin/work/408-mock4-questions-source-fix-20261017 -- papers/mock-2027/set-4 docs/mock4-source-remediation-20261017.md` → 空
- 未修改 main、未直接更新 PR #7、未解除 Draft、未强推、未动任何来源 worktree。
- 未合并 `work/408-historical-answer-repair-20261017`（起点不同，可能回退 main 历史答案）。

## 3. P0 已修（有源页证据）

### set-3
| 项 | 修复 | 证据 |
|---|---|---|
| Q31 单位 | `100ms` → `100ns` | 源题面 p5；选项均为 ns 量级，改后题意自洽 |
| Q41 两图 | 题面补 `assets/q41-graphs.png`；解析补 `assets/q41-solution-coloring.png` | 源题面 p7、解析 p6；原「如下图所示」不再悬空 |
| Q46 解析 | 补齐访问序列、4 页框模拟表、页表与 (3) 结论 | 源解析 p8；原稿截断在 `0、0、1、5、0、` |
| 页脚污染 | 删除 Q41–Q47 中 `27考研408模拟卷3·解析·N` 等混入行 | 源解析页；`grep -c '27考研408'` = 0 |
| 题面乱码 | 全卷按源页 p2–p10 重写 | 逐题对照 150 dpi 页图 |
| Q3 KMP | 主串改为 `aabaacaadaafa` | 题面 p2 + 解析 p1 双重确认 |

### set-4
| 项 | 修复 | 证据 |
|---|---|---|
| Q1 程序段 | 从乱码/缺失恢复为可读 C 代码 | 试题 p2 原生 1488×2103 图，局部 5–6× 放大 |
| Q9 有向图 | 新增 `assets/q9-fig1.png`（八顶点 T/R/V/S/W/Y/E/P） | 试题 p3；移除指向仓库外附件的悬空说明 |
| 章节位置 | 「二、综合应用题」由 Q40 前移到 Q40 后 | 结构修正 |
| Q18 寄存器 | `$S0…` → 小写 `$s0…$s4`，修复未配对 `$` | 试题 p5 5× 放大 |
| 裁图 | 6 张按题局部裁图 | 均远小于整页 |

## 4. P0 / 风险**未修**（必须保留的事实）

1. **set-4 Q1 左花括号缺失（明确未补）**：代码块首行 `int fun(int *arr, int m, int n)` 行尾的 `{` 在底本中不可辨；题下已注明「未擅自补入」。当前代码块因此少一个左括号，需人工看原卷确认。
2. **set-4 Q1 参数名非逐字读出**：`arr, m, n` 由正文两处调用点反证，不是逐字辨识；建议人工复核。
3. **set-3 Q20 指令字面模糊**：`lw R2,50,16` 在源页较糊，保留了可见字面与源语义，未改写。
4. **set-3 Q41 顶点无编号**：源图本身无顶点标签，解析只能按「左图/右图」描述，未臆造逐顶点表。
5. **表格/结构以图片保留**：set-3 Q44/Q45/Q46 的表与结构、set-4 的题图均为图片，不是可检索文本。
6. **综合题 41–47 解析为 OCR 转写**：按源页图重录/补完，但**未独立验算**（C10 未做）。
7. **源卷自身疑点按 qa-policy §6 保留原文，未擅自改正**：set-4 Q4 `M₂+M₂`、Q39「TCP建立」重复、Q42 `G`/`M` 不一致、Q43「且则」、Q45「5类」只列 4 类、Q47 笔误与孤立路由器图标。
8. **`recovered-lines.yml` 已过时但未删除**：
   - set-3：4 条；set-4：5 条；原为 main 版 OCR 草稿的漏行补录（RapidOCR 180dpi）。
   - 题面整体重写后，锚点/前缀大多已不存在；本次**仅加时效说明注释**，YAML 数据逐条保持不变（机器比对 `new == old`）。
   - 保留目的为溯源；**不得当作当前有效登记**，也不建议在未归档前删除。
9. **`proofread` = 0，C10 未完成**：本候选不宣称任何题已完成全文校对或计算复核。

## 5. 机器 QA（本候选实测）

| 检查 | 命令 | 结果 |
|---|---|---|
| 全库结构 QA | `python3 tools/qa_paper.py --all --write-coverage` | ✅ 22 卷全部 `choice=40/40 comp=7/7 total=47/47`；阻断 **0**；选择题答案覆盖 **880/880** |
| meta schema | `python3 tools/validate_meta.py --dir papers` | ✅ 22 份，不合规 **0** |
| 语义审计 | `tools/audit_drafts.py --paper mock-2027/set-3` / `set-4` | high=**0**，medium=**0**（该工具不在本基线 `tools/`，临时复制自来源分支运行后已删除） |
| 图片/相对链接 | 自写只读检查 | 17 个链接全部存在；16 张 PNG 全部可解码且均被引用 |
| 空白/冲突 | `git diff --check` | ✅ 干净 |
| coverage 文件 | `git diff index/coverage.md` | 无变化（9c3000f 时已为 set-3/4 40/40） |

## 6. 逐题抽检（本候选实际内容）

- **set-3 Q31**：`100ns` ✅（注释亦标明源图为 100ns）。
- **set-3 Q41**：题面引用 `assets/q41-graphs.png`；解析引用 `assets/q41-solution-coloring.png` ✅ 两图均在。
- **set-3 Q46**：解析 27 行，含访问序列、4 行页框表、页表与 (3) 结论 ✅ 已补完。
- **set-4 Q9**：题干引用 `assets/q9-fig1.png` ✅ 有图。
- **set-4 Q1**：代码已恢复；**首行行尾缺 `{`，且题注明确说明不可辨、未补** ✅ 与已知遗留一致。
- **状态**：set-3 / set-4 均 47 条 `status: needs-review`，无 `status: proofread`。

## 7. 复现

```bash
cd /home/fjd/workspaces/408-question-bank-dell/worktrees/mock34-final-integration-20261018
git log --oneline -5
python3 tools/qa_paper.py papers/mock-2027/set-3
python3 tools/qa_paper.py papers/mock-2027/set-4
python3 tools/qa_paper.py --all --write-coverage
python3 tools/validate_meta.py --dir papers
git diff --check
```
