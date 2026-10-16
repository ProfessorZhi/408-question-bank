# HANDOFF｜Windows 端 408 转录工具链（2026-10-16）

在 FJPCOS（Windows 10，device:work-fj）上跑通的转录工具链与踩过的坑，固化在此。
工作分支 `main`（`ddcdc48` 之后）。**22 卷全量转换尚未完成**，目前只交付了试点卷
`exams/2026`。

---

## 1. 这次实际做到了什么

| 项 | 状态 |
|---|---|
| 逐页提取（文字层 + 离线 OCR） | 全 22 卷共 **483** 页；已落盘 **457** 页草稿（文字层 387 + OCR 70），余 26 页待 OCR |
| `exams/2026` 题目 | `papers/exams/2026/questions.md`，**47/47** 题切出，选项 0 处不干净 |
| `exams/2026` 答案 | `papers/exams/2026/solutions.md`，40 个选择题答案按题号严格递增取出 + 7 道综合题（**OCR 初稿**，带 ⚠️） |
| `exams/2026` 插图 | **5 张真图**裁入 `assets/`（q36/q37/q44/q46/q47，非占位符） |
| `exams/2026` 表格 | 6 处坐标块 → **6 张 GFM 表**；其中「题43 表」无可靠列边界，走等宽保形（已加围栏块） |
| 本机 QA | ✅ `choice=40/40 comp=7/7 total=47/47`，**阻断 0 卷**（C1—C8 全过） |
| 其余 21 卷 + 4 套模拟卷 | **未转 MD**（逐页草稿在 `build/_scratch/`，转换未做） |
| 2027 套 1 勘误 | **未录入**（清单见 issue/记忆，待补） |

状态诚实性：`meta.yml` 里 2026 卷 47 题全部是 `ocr-uncertain`（答案侧来自扫描件 OCR），
**没有任何一题被标成 `proofread`**——按 `docs/qa-policy.md`，没逐字对照过底本就不许标。

### 尚未补齐的提取
`mock2027-set3-solution`(8 页)、`set4-paper`(10 页)、`set4-solution`(8 页) 共 **26 页**
仍是 `missing-text-needs-ocr`，需要 OCR 补跑（`tools/batch_extract.py --scope mock --ocr auto`）。

---

## 2. 工具链

| 文件 | 职责 |
|---|---|
| `tools/ocr_runtime.py` | **新增**。让 onnxruntime 在本机可加载的兼容层，见 §3 |
| `tools/batch_extract.py` | **改**。OCR 运行时必须在 `import pymupdf` **之前**就位（§3） |
| `tools/page_objects.py` | **新增**。按块坐标抽每页的「行 / 位图 / 矢量簇」→ JSON |
| `tools/fig_crop.py` | **新增**。判「图 vs 表」并裁真图进 `assets/`，带归属依据 |
| `tools/md_from_pages.py` | **新增**。逐页草稿 + 坐标 → `questions.md`（规范化 + 表格 + 图） |
| `tools/md_solutions.py` | **新增**。答案卷草稿 → `solutions.md`（选择题严格递增取号；综合题 OCR 初稿 + 形近误识点名） |
| `tools/meta_status.py` | **新增**。按**实际来源**回填逐题状态；**永不写 `proofread`** |
| `tools/qa_paper.py`、`docs/*`、`schema/*` | 既有，未改；QA 契约以它们为准 |

### 复现顺序（严格照此顺序）
```bash
python -I tools/inventory.py                 # 生成 index/sources-manifest.json
python -I tools/bootstrap_meta.py            # 生成各卷 meta.yml 骨架
python -I tools/batch_extract.py --scope all --ocr auto --limit-pages 0
python -I tools/page_objects.py --paper exams/2026 --force
python -I tools/fig_crop.py     --paper exams/2026
python -I tools/md_from_pages.py   --paper exams/2026 --write --force
python -I tools/md_solutions.py    --paper exams/2026 --write --force
python -I tools/meta_status.py     --paper exams/2026 --write
python -I tools/qa_paper.py papers/exams/2026      # 本机跑，禁止动 GitHub Actions
```
全部脚本用 `python -I`；`batch_extract.py` 自带 `sys.path.insert` 处理 `-I` 的影响。

---

## 3. 本机环境要害（别再重复诊断）

`C:\Windows\System32` 里的 MSVC 运行时是 **VS2015 代**（`msvcp140.dll` = 14.0.0.23026），
且**整机缺 `msvcp140_1.dll`**；而 `onnxruntime 1.30.0` 是 **VS2022 构建**。
表现是 `ImportError: DLL load failed while importing onnxruntime_pybind11_state`，
极易被误读成「rapidocr 没装」——`pip list` 明明有 1.4.4。

更要命的一条：**`import pymupdf` 会把 System32 那份旧 `msvcp140.dll` 按基名钉进进程**，
之后任何 `AddDllDirectory` 都顶替不掉，onnxruntime 撞上去是**段错误**（exit 139、零输出），
不是抛异常。所以 `batch_extract.py` 里 `ocr_runtime.ensure()` 必须在 `import pymupdf` 之前。

`ocr_runtime.py` 的做法：从本机**既有应用目录**（Blender 等）取一份成套的 14.0.4x 运行时，
复制进 `build/_scratch/ocr-dll/`（已 gitignore），只对本进程 `os.add_dll_directory`。
不需要管理员、不改系统、不改 Python 安装；复制做了 sha256 幂等 + 重试（本机有杀软会短暂锁文件）。
`os.add_dll_directory` 的句柄必须常驻，否则 GC 回收后目录从搜索路径消失。

其他本机坑：控制台是 GBK，所有脚本开头 `sys.stdout.reconfigure(encoding="utf-8")`；
Git Bash 的 PATH 不做 MSYS 转换，每条命令要先 `export PATH=...`。

---

## 4. 转换契约（改动时别破坏）

- **`questions.md` 绝不含答案**（连 YAML 里都不行）；答案是 `solutions.md`，按同一题号。
- 题号切分**严格等于下一个期望号**才认（防止正文里的 `1.` 误切）。
- 选项只接受 **A→B→C→D 顺序出现且切完恰好 4 段**的那一处；否则报 ⚠️ 交人工。
- YAML 的 `no` 键**必须加引号**：YAML 1.1 会把它解析成布尔 False 并静默丢题号。
- 着重号：源 PDF 用 n 个全角 `．` 表示 n 个字的着重号（已用几何证据确认：`．` 基线低约 4.6pt）。
  还原为 `**字**`，每次替换都写进报告可审计。
- 表格：矢量簇内文字多 → 是表，走坐标转 GFM；纯线条/位图 → 才裁图。
  表格和插图**都要从题干文本流里剔除**，避免同一内容出现两遍（报告里有「剔除核账」计数）。
- 无列结构的「等宽保形」表**必须包在 ```text 围栏里**：裸行会被 Markdown 折叠空格，版面直接毁掉。
- **只从文字层取答案**；答案卷是扫描件时，综合题文字一律标注为 OCR 初稿并点名可疑处，**不补成"像真的"**。

---

## 5. 已知缺口（诚实清单，别当成已完成）

1. **`solutions.md` 只做了 2026 一卷**；其余 21 卷 + mock set1–4 都没有。
2. **只转了 2026 一卷**；其余 21 卷 + mock set1–4 只有逐页草稿（26 页还缺 OCR）。
3. `exams/2026` 的「剔除核账」显示 **13 行计划剔除但文本流里没找到** —— 两边的行切法不完全一致，
   表格文字可能仍有残留在题干，需人工看一眼。
4. `exams/2026` 第 43 题的第 2 张表（I1～I4 位域表）走的是**等宽保形**而非 GFM：
   它的每一行只有一个文字块，没有可靠列边界。**只保内容不保像素**，不假装列对齐
   （已放进围栏块，至少不会被折叠坏）。
5. 源 PDF 里 `p2`/`p1` 之类的下标是**上游重排版就压平的**（同字号、同基线、无上标 flag），
   不是提取丢的。此类一律原样保留、在报告里点名，**不许猜**。
6. 2026 卷的 `meta.yml` 逐题状态是 `ocr-uncertain`（低置信），**不要**批量改成 `proofread`：
   `docs/qa-policy.md` 明确写了那等于造假。
7. 2027 套 1 的勘误（16 题选 B、第 41 题示例、第 42 题插入 74、第 7 题图/选项、第 31/44/47 题）
   **尚未录进 `papers/mock-2027/`**；mock 卷的 MD 也还没产出。

---

## 6. 后台进程

- 上一轮 OCR（PID 33912）已核实命令行与属主（`FJZ\Vince.Huang`）、cwd 在本仓库，已停止。
- `fleet_mcp.node.connector`（PID 14488）**不是**本任务，未动。
