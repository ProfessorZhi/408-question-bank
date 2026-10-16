# PDF→Markdown 解析器横向实测（Dell, CPU-only, 2026-10-16）

> 5 个工具 × 5 个单页样本的**实跑**对照。所有数字来自本机实跑，
> 未跑的一律标 `not tested`，不编造分数。
> 自动指标只是 proxy，**无人工真值，不声称任何输出"已准确"**。

## 0. 结论速览（按任务分支）

| 任务 | 胜出 | 理由 |
|---|---|---|
| **数字（有文字层）PDF** | `pdftotext -layout`（极简/速度）<br>`pymupdf4llm 0.3.4`（要 Markdown 结构） | 两者题干都**完整不被拆**；pdftotext 最快最省；pymupdf4llm 额外给 Markdown 结构与图片提取 |
| **扫描 PDF** | **`RapidOCR`** | 5 个工具里**唯一**真正产出文字的；其余 4 个输出为 0 |
| **图片/图表** | `pymupdf4llm 0.3.4`（`write_images=True`） | 唯一能把内嵌图导出为本地文件并给引用的 |
| **公式** | ❌ 全线不达标 | OCR 把 `O(1)` 错成 `0(1)`；文字层工具靠源码字形，仅大小写侥幸正确 |
| **MarkItDown** | ❌ **淘汰** | 把正常题干误判成表格切碎；图片全丢；扫描页 0 输出 |

## 1. 环境与门槛

主机 FJ-NJ-SER-1009（Dell Precision 5820），Ubuntu 26.04，用户 `fjd`。
跑前 load 0.23–2.48、MemAvailable 17 GiB（门槛 load<8 / ≥4 GiB 通过）。
**全程 CPU-only**；A6000 显存约 48/49 GB 被 Strata 占用，**未触碰 GPU**。

| venv | 用途 | 关键版本 |
|---|---|---|
| `venv`（既有，未改动） | 生产 OCR 环境 | `pymupdf 1.28.2`、`rapidocr-onnxruntime 1.2.3`、`markitdown 0.1.8` |
| `venv-compare`（**本次新建**） | 仅放对照工具 | `pymupdf4llm 0.3.4` + `pymupdf 1.28.2` + `tabulate 0.10.0` |

安装全部 `--only-binary=:all:`，**零源码编译**，未动系统 Python。`venv-compare` 79 MB。

> **关于 pymupdf4llm 版本**：PyPI 上并存 `0.3.4`（旧独立线末版）与 `1.27.x/1.28.x`
> （与 PyMuPDF 同号，功能已并入 PyMuPDF 主包）。本次按"功能完整的旧版"选 **0.3.4**
> 并实测确认**非空转换 API** 可用（`pymupdf4llm.to_markdown(doc, ...) -> str`）。

## 2. 样本（每个工具严格同一份单页 PDF，均由原 PDF 切出）

| # | 样本 | 特征 |
|---|---|---|
| s1 | `2026.pdf` p1 | 选择题 / 中文 / 4 选项 |
| s2 | `2026.pdf` p8 | **第43题 指令位域表**（MarkItDown 曾把题干拆成 11 列） |
| s3 | `2026.pdf` p11 | 含内嵌图 |
| s4 | `mock2027-set2-paper.pdf` p2 | **纯扫描**，已知 OCR 有 `O(1)→0(1)` 错 |
| s5 | `2026-answer.pdf` p2 | **纯扫描**答案页 |

切出的单页 PDF 与全部输出留在 `build/_scratch/shootout/`（gitignored）。

## 3. 资源矩阵（实跑，`nice 15`，OMP/MKL=1，单进程）

`seconds` / `maxrss_kb` 取自 `/usr/bin/time`。

| 工具 | s1 | s2 | s3 | s4(扫描) | s5(扫描) | 典型 RSS |
|---|---|---|---|---|---|---|
| `pdftotext -layout` | 0.03s | 0.03s | 0.03s | 0.02s | 0.01s | **~19 MB** |
| `markitdown 0.1.8` | 0.51s | 0.42s | 0.39s | 0.38s | 0.36s | ~108 MB |
| `pymupdf`（纯文本） | 0.14s | 0.15s | 0.15s | 0.15s | 0.14s | ~57 MB |
| `pymupdf4llm 0.3.4` | 0.24s | 0.17s | 0.18s | 0.16s | 0.19s | ~70–80 MB |
| `rapidocr-onnxruntime` | 7.88s | 3.42s | 3.93s | 4.57s | 2.07s | ~490 MB |

速度快 2 个数量级：文字层工具 ≈0.02–0.5 s，OCR ≈2–8 s。

## 4. 质量矩阵

`chars`=总字符；`CJK`=中文字数；`pipes`=疑似表格行（`|`≥2 的行数）；`ABCD`=选项标记数。

| 工具 | 样本 | chars | CJK | pipes | ABCD |
|---|---|---|---|---|---|
| pdftotext | s1 | 2,875 | 838 | 1 | **40** |
| markitdown | s1 | 6,565 | 838 | **43** | 40 |
| pymupdf | s1 | 2,089 | 838 | 4 | 40 |
| pymupdf4llm | s1 | 2,252 | 812 | 1 | 40 |
| rapidocr | s1 | 1,652 | 804 | 0 | **37** |
| pdftotext | s2 | 1,153 | 274 | 0 | – |
| markitdown | s2 | 3,461 | 274 | **23** | – |
| pymupdf4llm | s2 | 682 | 271 | **0** | – |
| rapidocr | s2 | 726 | 273 | 0 | – |
| pdftotext | s3 | 827 | 385 | 0 | – |
| markitdown | s3 | 2,109 | 385 | **17** | – |
| pymupdf4llm | s3 | 635 | 377 | 0 | – |
| pdftotext/markitdown/pymupdf | s4/s5 | **0–2** | 0 | 0 | – |
| pymupdf4llm | s4/s5 | 87* | 0 | 0 | – |
| rapidocr | s4 | **1,051** | 673 | 0 | 19 |
| rapidocr | s5 | **479** | 137 | 0 | 0 |

\* **陷阱**：pymupdf4llm 在扫描页输出的 87 字节**不是内容**，而是它打到 stdout 的一行警告
`Consider using the pymupdf_layout package for a greatly improved page layout analysis.`
**扫描页真实产出为 0。** 任何按字节数判"成功"的脚本都会在此误判。

## 5. 决定性差异（定点复核）

### 5.1 s2 第43题题干

| 工具 | 首行 |
|---|---|
| `pdftotext` | `43.（本题 10 分）某 16 位计算机 C 按字节编址，通用寄存器 R0～R15 的编…` ✅ |
| `markitdown` | `\| 43.（本题 \| 10 \| 分）某 \| 16 位计算机C \| \| 按字节编…` ❌ **被拆成表格** |
| `pymupdf4llm` | `43.（本题10 分）某16 位计算机 C 按字节编址…` ✅ |

`s2` 的 `pipes` 计数把这点量化：markitdown **23** vs pdftotext/pymupdf4llm **0**。
即 MarkItDown 的表格启发式会把**正常题干**误判为表格——这是它出局的直接原因。

### 5.2 s4 扫描页公式大小写

`rapidocr` 输出中 `O(1)` 出现 **0** 次，`0(1)` 出现 **1** 次 → **确证**把字母 O 认成数字 0。
扫描页公式**不可信**，必须人工校对。

### 5.3 s3 图片提取

`pymupdf4llm.to_markdown(..., write_images=True, image_path=...)` 在 s3 上：

- 提取出 **2 个 PNG**（`s3-2026-p11-figure.pdf-0-0.png` / `-0-1.png`）
- 生成 **2 条 Markdown 图片引用**

对比：`pdftotext` / `pymupdf`（纯文本）/`markitdown` / `rapidocr` 均**不产出任何图片**。
**图片/图表场景只有 pymupdf4llm 可用。**

## 6. 跑过 / 没跑

| 工具 | 状态 | 依据 |
|---|---|---|
| `pdftotext -layout` | ✅ 实跑 | 基线，全 5 样本 |
| `markitdown 0.1.8` | ✅ 实跑 | 全 5 样本（阶段1 已有全卷数据，本次复用） |
| `pymupdf 1.28.2`（纯文本） | ✅ 实跑 | 全 5 样本 |
| `pymupdf4llm 0.3.4` | ✅ 实跑 | 全 5 样本 + 图片提取 + API 核验 |
| `rapidocr-onnxruntime 1.2.3` | ✅ 实跑 | 全 5 样本 |
| `Docling` | ❌ **blocked_resources** | 干跑显示会装 **torch 2.14.1 + torchvision + triton + transformers 5.20 + 完整 CUDA 栈**（`nvidia-cublas/cudnn/nccl/cusparse/cusolver…`）。远超 ~1 GB 预算，且会引入 GPU 库（本机 GPU 被 Strata 占用，**禁止**）。未安装 |
| `MinerU 4.0` | ❌ **not tested – too heavy** | 同类重型依赖（torch + 大模型权重），本次预算内不可行 |
| `Marker` | ❌ **not tested – forbidden** | 依赖 PyTorch/Surya，**可能自行启动本地 LLM server**；本机明令禁止启动此类服务 |

## 7. 局限

- 仅 **5 个单页样本**，不可外推全库；其余 42 份 PDF 未抽样。
- **无人工真值**：上述 `pipes`/`CJK`/`ABCD`/`O(1)` 均为 **proxy 指标**，
  不能据此断言任何输出"准确"或"最佳"。
- 未评公式上下标、矩阵、电路图的内容保真。
- `pymupdf4llm` 会向 stdout 打警告行，**下游必须剥离**，否则污染 Markdown。
- 本次产出**全部是草稿**，未做人工校对，**不得**当作正式转录或计入 1034 题完成度。

## 8. 建议

1. **文字层页**：默认 `pdftotext -layout`（快、省、题干完整）；需要 Markdown 结构
   或要提图时改用 `pymupdf4llm 0.3.4`。
2. **扫描页**：`RapidOCR` 是唯一可选，但**必须**人工校对，公式一律 `unverified`。
3. **弃用 MarkItDown** 做题库转换（误判表格 + 丢图）。
4. **暂不引入 Docling/MinerU/Marker**：资源超预算且 Marker 有启动本地 LLM server 的风险。
5. 若要进一步提质量，优先考虑**同一页多工具交叉比对 + 差异页人工复核**，
   而不是继续堆重型模型。

## 9. 复现

```
tools/run_shootout_dell.sh          # 全矩阵实跑，输出 metrics.csv
tools/ocr_cpu_pilot.py              # 单页渲染+OCR（rapidocr 一列）
build/_scratch/shootout/            # 样本单页 PDF + 各工具输出 + metrics.csv（gitignored）
```
