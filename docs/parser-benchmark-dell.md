# Dell CPU 解析试点：MarkItDown vs pdftotext（2026-10-16）

> 阶段1 小样本试跑报告。仅覆盖 2 份样本，**不代表** 44 份全量结论。
> 所有产物在 `build/_scratch/`（gitignored），原始 PDF 未改动。

## 1. 执行环境

| 项 | 值 |
|---|---|
| 主机 | FJ-NJ-SER-1009（Dell Precision 5820 Tower X-Series） |
| OS / 内核 | Ubuntu 26.04 LTS / 7.0.0-38-generic |
| 用户 | `fjd`（组含 `llm-team`） |
| CPU | 20 逻辑核；开跑时 load 1.17 |
| 内存 | 30 GiB 总，MemAvailable 15 GiB |
| 磁盘 | `/` 可用 292 GiB |
| GPU | RTX A6000，**48277/49140 MiB 已被占用**（`/opt/strata` 42.1 GB + 一个 `.venv` python 6.2 GB）。本试点 **0 GPU 占用**，未触碰生产服务 |
| 仓库 | `ProfessorZhi/408-question-bank`（PRIVATE），shallow clone |
| HEAD | `ddcdc4813f7b16942814624bc3d3ae6994e68b51`（2026-10-16 15:14:04 +0800） |
| PDF 总数 | 44（`find` 实测，与预期一致） |

资源纪律：单进程、`nice -n 10`、`OMP_NUM_THREADS=1`。

## 2. 工具链（隔离 venv，未动全局）

系统 Python 3.14.4 **无 pip**（`ensurepip` 缺失）。已在
`/home/fjd/workspaces/408-question-bank-dell/venv` 建立隔离环境，
经官方 `bootstrap.pypa.io/get-pip.py` 引导 pip 26.2.1。**无 sudo / 无 apt / 未改全局。**

实测装的版本：

- `markitdown 0.1.8`
- 其 PDF 后端：`pdfminer.six 20260107`、`pdfplumber 0.11.10`、`pypdfium2 5.14.0`
- 传递依赖：`magika 0.6.3`、`onnxruntime 1.31.0`、`numpy 2.5.4`、`Pillow 12.3.0`

> **Python 3.14 兼容性风险已解除**：onnxruntime 1.31.0 提供 cp314 wheel，安装全程无编译。
>
> **注意**：`markitdown[pdf]` **不含 PyMuPDF**。若需要 PyMuPDF 需单独安装（本次未装，保持轻量）。

**OCR 引擎：本机一个都没有。** `tesseract` / `ocrmypdf` / `rapidocr_onnxruntime` /
`paddleocr` / `pytesseract` / `docling` / `mineru` 全部 absent。
（既有 `tools/extract_text.py` docstring 称"本机有 rapidocr-onnxruntime，离线可用"——
该描述在**本 Dell 主机上不成立**，疑为 Windows 侧环境。）

## 3. 样本与文本层普查

| 样本 | 页数 | 文本层（逐页非空白字符数） |
|---|---|---|
| `sources/exams/papers/2026.pdf` | 12 | p1–p12 **全部有**（518–3743/页，p5 最少，疑图表页） |
| `sources/mock-2027/pdf/mock2027-set2-paper.pdf` | 9 | **p1–p9 全部为 0 → 纯扫描件，无文本层** |
| （对照）`mock2027-set1-paper.pdf` | 13 | p1–p12 有（合计约 1 万字符），p13 为 0 |

即：卷1 是文字版，**卷2 是纯扫描版**，两者不能用同一路径处理。

## 4. 结果对比（2026.pdf，12 页文字层）

| 指标 | `pdftotext -layout` | `markitdown 0.1.8` |
|---|---|---|
| 字符数 | 14,954 | 44,148 |
| 行数 | 351 | 430 |
| 耗时 | **0.04 s** | 1.04 s |
| 峰值常驻内存 | **19.6 MB** | 122.4 MB |
| 选项 A/B/C/D 计数 | 40 / 40 / 40 / 40 | 40 / 40 / 40 / 40 |
| U+FFFD 乱码 | 0 | 0 |
| 第43题题干 | **单行完整** | **被切碎成 11 个单元格** ❌ |
| 表格 | 空格对齐，边框丢失 | 误建 294 行 `\|` 表格，大量误判 |
| 内嵌图片（`pdfimages` 实测 6 张） | 丢失 | **丢失（0 图片引用、0 base64）** ❌ |
| 扫描页（set2-p1） | 0 字符 | **0 字节（空输出）** ❌ |

### 4.1 决定性缺陷：MarkItDown 把正文误判为表格

第43题（16 位机指令位域表题）在 MarkItDown 输出中变成：

```
| 43.（本题 | 10 | 分）某 | 16 位计算机C | | 按字节编址，通用寄存器R0～R15的编号为 | ... |
```

题干被 `|` 切碎，后续 `R 型 / I 型 / M 型` 位域行也发生列错位。
**pdftotext 同一句是完整可读的一行。** 对"题号—题干—选项"结构而言这是不可接受的破坏，
且会把噪声直接带进后续校对流程。

### 4.2 MarkItDown 不是 OCR

set2 第1页（扫描件）MarkItDown 输出 **0 字节**，无任何报错。
**不得据此宣称转换成功**——它只是"没有文字层可抽"，并未识别图像中的文字。

### 4.3 图片一律丢失

2026.pdf 含 6 张内嵌 JPEG（p4×2、p9、p11 等）。两种工具都**不产出任何图片**，
MarkItDown 也未落 base64 或占位。**图形题必须另有渲染/切图链路。**

### 4.4 渲染能力已验证可用

用 venv 内 `pypdfium2` 把 set2 第1页渲染为 PNG：
1190×1682、167 KB、**0.11 s**。说明"自建 渲染→OCR"链路的渲染端在本机轻量可行，
缺的只是 OCR 引擎本身。

## 5. 结论

1. **文字层卷**（2026、卷1 等）：`pdftotext -layout` 是更优基线——快 26×、内存小 6×、
   且不破坏题干结构。MarkItDown 的 Markdown 包装在此场景是**负收益**。
2. **扫描卷**（卷2 等）：**两个工具都不可用**，必须引入 OCR。MarkItDown 不解决该问题。
3. **图形/表格**：两条路径都丢图；表格仅 pdftotext 的"空格对齐"尚可人工读。
4. 本机 CPU/RAM 余量充足（15 GiB 可用、load <2），单进程 CPU 跑 OCR 无资源障碍。

## 6. 未验证 / 待定

- **公式保真**：上下标、希腊字母、矩阵、位域下标 —— **未逐项核对，一律标记 `unverified`**。
- **图形内容**：仅统计到图片存在与否，未评内容。
- 其余 42 份 PDF **未抽样**，结论不可外推。
- 第43题等具体题目**未做人工校对**，本报告只描述抽取器行为，不构成题目正确性结论。
- 进度口径：本次**未产出任何可入库的正式转录**，不触及 47/47 之类的完成度计数。

## 7. 建议的下一步（待确认后再扩容）

1. **先补 OCR 引擎再谈扫描卷**：在隔离 venv 内试装 CPU 版 OCR（如 `rapidocr-onnxruntime`
   或 `tesseract` 的用户态替代），仅对 set2 的 **1 页**做渲染→识别小样，
   量 字符数 / 错字率 / 耗时 / 内存，再决定是否铺开。**不下载多 GB 模型。**
2. **文字层卷批量走 pdftotext**：2026、2025、卷1 可低风险批处理，
   但输出进 `build/_scratch/`，人工校对后再入库。
3. **图形题单列**：从 `pdfimages` 或渲染切图，产出独立图片资产清单，
   而非指望文本抽取器。
4. **文档纠偏**：修正 `tools/extract_text.py` 中关于本机已有 rapidocr 的描述。
