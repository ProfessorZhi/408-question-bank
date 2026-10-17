# 2022 年真题综合题 Q41–Q47 源 PDF 校核记录（2026-10-18）

## 0. 环境与基线

| 项目 | 实测 |
|---|---|
| 主机名 | `FJ-NJ-SER-1009` |
| GPU | `NVIDIA RTX A6000`（UUID `GPU-cee214cd-…`）；未使用 GPU |
| 仓库 | `/home/fjd/workspaces/408-question-bank-dell/repo` |
| origin | `https://github.com/ProfessorZhi/408-question-bank.git`（私有） |
| 基线 SHA | `b69c6d80ef04febe1358ae95c87fadf5dc3d7043`（远端 `refs/heads/main` 实测一致） |
| 本任务 worktree | `worktrees/exams-2022-comp-source-review-20261018` |
| 本任务分支 | `work/408-exams-2022-comp-source-review-20261018` |

资源：20 核，load `0.99/0.42/0.19`，MemAvailable 约 8.1 GiB，swap 2.8/8 GiB，
PSI cpu/memory/io 的 avg10 均为 0.00；全程 `nice -n 15`，单线程文本层读取，
仅对 6 个关键区域做局部 4× 渲染，未做全卷 OCR/重型渲染，未触碰其他 worktree。

## 1. 源文件与页面

- 只读源：`sources/exams/answers/2022-answer.pdf`（10 页，自带文字层）。
- Q41–Q47 所在页：Q41 p6–p7；Q42 p7–p8；Q43 p8；Q44 p8–p9；Q45 p9；Q46 p9；Q47 p10。
- 注意：p7、p9 是超大扫描页（约 2121×3086），按缩放条带读取；p6/p8/p10 为正常页。
- 文字层存在大量形近误识，故以文字层为底、页图逐式核对；未使用其他候选分支的解析正文。

## 2. 逐题修复（前 → 后，源页）

本次实修 **Q41–Q47 共 7 题**；逐题如下。

### Q41（p6–p7）

| 修复前（OCR） | 修复后（页图） |
|---|---|
| `SqBiTNode[O]` | `SqBiTNode[0]` |
| `SqBiTNode[2i+l]` | `SqBiTNode[2i+1]` |
| `SqBiTNode[ （七1) /2)` | `SqBiTNode[(i-1)/2]` |
| `非define true 1` / `七ypedef int-bool;` | `#define true 1` / `typedef int bool;` |
| 代码缺括号、`bt.SqBiTNodʉrkJ!=ʊl` | 恢复为 `bt.SqBiTNode[k]!=-1`，补齐两段完整代码 |

两段答案均恢复：答案 1 的中序递归判定；答案 2 的 pmax/pmin 自底向上扫描。
代码缩进统一为 4 空格（源页为等宽排版，逻辑与字符未改）。

### Q42（p7–p8）

| 修复前 | 修复后 |
|---|---|
| `数组A[O],_,A[9]` | `数组 A[0]~A[9]` |
| `最大数M心（` | `最大数 MAX` |
| `0(1)` | `O(1)` |

答案 1（10 元素数组插入）与答案 2（10 元素大根堆）均按页图恢复。

**源文异文（保留待复核）**：答案 2 正文写“以 SqBiTNode[2i+2] 为根的子树中的最小值（保存在 pmin[2i+1] 中）”。
按上下文右子树应为 `pmin[2i+2]`，但源页确实印作 `pmin[2i+1]`；本次按原印保留，并在正文加注。

### Q43（p8）

| 修复前 | 修复后 |
|---|---|
| `SF=F1so` | `SF=F15` |
| `OF=A 15 B15 ·F15+A15·B15. E5` | `OF=\overline{A15}·\overline{B15}·F15 + A15·B15·\overline{F15}` |
| 减法 `OF=兀:·B15·F15+ A15· B15 .Fl5` | `OF=\overline{A15}·B15·F15 + A15·\overline{B15}·\overline{F15}` |
| `(DPCout,M应` / `@Read` / `@:MDRout, IRin` | `① PCout, MARin` / `② Read` / `③ MDRout, IRin` |

已按页图恢复加/减溢出公式的每个上划线与下标，控制信号三步及 1+5+1=7 个时钟周期。

### Q44（p8–p9）

| 修复前 | 修复后 |
|---|---|
| `「log_{2} 20000l` | `⌈log2 20000⌉=15` |
| `log式4x2)` | `log2(4×2)=3` |
| `「log_{2} 5001` | `⌈log2 500⌉=9` |
| `60X 10^{3} /7200 叭8.33ms` | `60×10³/7200≈8.33ms` |
| `5 + 8.33/2 + 8.33/500 还9.18ms` | `5+8.33/2+8.33/500≈9.18ms` |

DMA 次数 `512B/64bit=64` 与周期挪用说明按页图保留。

### Q45（p9）

- 目录表恢复为 GFM 两列表：`course → 2`、`doc → 10`。
- `course]`/`course!` 等 OCR 误识按页图改为 `course1`、`course2`。
- 第 (3) 问读 2 个磁盘块的路径、第 (4) 问 6MB/4KB=1536 块及
  `10+1024<1536<10+1024+1024×1024` 的不等式均按页图恢复。

### Q46（p9）

| 修复前 | 修复后 |
|---|---|
| `Semaphore SAc = O` | `Semaphore S_AC = 0` |
| `Semaphore ScE = O` | `Semaphore S_CE = 0` |
| 两栏代码被读成单列散行 | 恢复为 T1/T2 两栏代码表 |

T1：`A; signal(S_AC); wait(S_CE); E; F;`
T2：`B; wait(S_AC); C; signal(S_CE); D;`

### Q47（p10）

| 修复前 | 修复后 |
|---|---|
| `IOOBaseT` / `lOOBaseT` | `100BaseT` |
| `lOOMbps` | `100Mbps` |
| `CSMNCD` | `CSMA/CD` |
| `l.51µs` | `1.51μs` |
| `D/(2xI0 8m/s)` | `D/(2×10^8m/s)` |
| `路由器EO` | `路由器 E0` |
| `00-...-El / -C1 / -Dl` | `00-11-11-11-11-E1 / -C1 / -D1` |

最短帧长公式与 `D=210m` 按页图恢复。

## 3. 未改动项与断言

- `solutions.md` 的 Q1–Q40 答案字母逐字节不变：
  基线 `BDBCDDBDDADABACACBDACCDACBCDADBABCBDBCDB` = 当前同串（40/40）。
- `questions.md`、`index/coverage.md`、sources PDF、main/PR、其他年份/卷均未改动。
- Q41–Q47 仍为 `needs-review`，`proofread` 计数 **0**；未做 C10 独立验算，
  未宣称公式/答案已独立验证。

## 4. 剩余不确定项

1. **Q42 源文 `pmin[2i+1]`**：按右子树语义可能应为 `pmin[2i+2]`，但源页如此印刷；
   已保留并标注，未擅自改写。
2. **Q41 代码缩进/空格**：按页图恢复逻辑与字符，缩进按 4 空格规范化；源页的等宽空格
   不作为字符级证据。
3. **Q43 上划线公式**：以 LaTeX `\overline{}` 复现页图；未独立推导每个溢出条件。
4. **Q44/Q45 数值**：15/3/9 位、8.33ms、9.18ms、1536 块等均按源文录入，未独立验算。
5. **p7/p9 超大扫描页**：按缩放条带读取，个别字形仍偏糊；不能确认处按原印保留，
   未凭常识补参数。

## 5. 校验

| 工具 | 结果 |
|---|---|
| `qa_paper.py papers/exams/2022` | `choice=40/40 comp=7/7 total=47/47`，阻断 0 |
| `validate_meta.py` | 22 份 meta.yml，不合规 0 |
| Markdown 图链 | 8/8 存在 |
| `git diff --check` | 通过 |
| Q1–Q40 答案字节断言 | 40/40 与基线一致 |
| `proofread` 计数 | 0 |

## 6. 变更文件

- `papers/exams/2022/solutions.md`（仅 Q41–Q47 段）
- `papers/exams/2022/meta.yml`（仅 Q41–Q47 notes）
- `docs/exams-2022-comp-source-review-20261018.md`（本文档）
