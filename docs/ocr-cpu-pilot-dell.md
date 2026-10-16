# Dell CPU-only OCR 试点：RapidOCR 单页实测（2026-10-16）

> 阶段2 小样本试验。仅 3 页样本（1 页封面 + 2 页内容页），**不代表全量质量结论**。
> 输出均为**草稿**，需人工校对。产物在 `build/_scratch/ocr/`（gitignored），原 PDF 未改动。

## 1. 环境与门槛

主机 FJ-NJ-SER-1009（Dell Precision 5820），Ubuntu 26.04，用户 `fjd`。
本轮开跑时 load 0.26、MemAvailable 17 GiB → 满足 load<8 且 ≥4 GiB 门槛。

全程 **CPU-only，单进程**，`nice -n 15`、`OMP_NUM_THREADS=1`、`MKL_NUM_THREADS=1`；
**GPU 0 占用**，未触碰 `/opt/strata` 与任何既有 agent 会话。

隔离 venv `/home/fjd/workspaces/408-question-bank-dell/venv`（Python 3.14.4），本轮新增：

| 包 | 版本 | 形态 |
|---|---|---|
| `pymupdf` | 1.28.2 | `cp310-abi3` manylinux wheel（**未编译**） |
| `rapidocr-onnxruntime` | 1.2.3 | `py3-none-any`，**模型随包离线**（`ch_PP-OCRv3_det/rec` + `cls`），无多 GB 权重下载 |
| `opencv-python` | 5.0.0.93 | `cp37-abi3` wheel |

全部 `--only-binary=:all:`，**无源码编译、无 sudo、无 apt、未改全局 Python**。
venv 总占用 535 MB。

**阶段1 的 MarkItDown 已判定不适合作正式题库转换器**（切碎题干 + 丢图 + 无 OCR），
本阶段不再使用。

## 2. 实测结果（`sources/mock-2027/pdf/mock2027-set2-paper.pdf`，全 9 页纯扫描）

单页流程：`pypdfium2` 渲染一次 PNG → `RapidOCR` 识别一次。

| 页 | 渲染 | OCR | 行数 | 字符数 | 均值置信 | 最低分 | 低置信行 | 峰值 RSS |
|---|---|---|---|---|---|---|---|---|
| p1（封面） | 0.12 s | 0.84 s | 10 | 112 | 0.813 | 0.678 | 0 | 486 MB |
| p2（内容） | 0.18 s | 3.78 s | 44 | 1,007 | 0.829 | 0.521 | 2 | 495 MB |
| p3（内容） | 0.17 s | 3.51 s | 62 | 1,039 | 0.820 | 0.601 | 0 | 491 MB |
| p2 @scale3 | — | 4.87 s | 49 | 1,026 | 0.805 | 0.566 | 3 | 877 MB |

**内容页 ≈ 4.0 s/页、≈ 0.5 GB RSS**（单进程单核）。

### 2.1 渲染倍率对照：更高分辨率**没有**更好

scale 2 → 3：均值置信 0.829 → **0.805**（下降），OCR 耗时 +29%，峰值内存 +77%（495→877 MB），
且错误**照旧**（同一处 `择作`/`0(1)`/`人` 均未修正）。**结论：scale 2 是更优工作点，不必加码分辨率。**

### 2.2 真实错误样本（草稿，非校对结果）

同学术区域两档渲染下的原始输出对比：

| 应为 | scale 2 输出 | scale 3 输出 |
|---|---|---|
| `下列操作可以在O(1)的时间复杂度内完成的是（）` | `下列择作可以在0(1)的时间复杂度内完成的` | 同左 |
| `A.删除单链表的第i个元素` | `A剩除单表的第人个元素` | `A刻除单表的第人个元素` |

**典型错误模式**：`O`→`0`、`操作`→`择作`、`删除`→`剩除`/`刻除`、`i`→`人`。
即 **0.82 的均值置信并不可靠**——专业术语与字母数字混排是主要失分点，
且高置信行里也可能藏错。**OCR 初稿绝不可当人工校对完成。**

## 3. 全库页面普查与资源预测

对 44 份 PDF 逐页做文本层普查（`pdftotext` 非空白字符数）：

| 项 | 页数 |
|---|---|
| 全库总页数 | **483** |
| 已有文本层（可直接 `pdftotext`） | ≈ **388** |
| 纯扫描、**需 OCR** | ≈ **95** |

按内容页 ≈4.2 s/页、单核串行估算：

- **需 OCR 的 ~95 页 ≈ 0.1 核·小时**（约 7 分钟）
- 即便对全库 483 页无差别跑 OCR，也仅 ≈ **0.6 核·小时**

**CPU 时间不是瓶颈。** 真正的成本在**人工校对**：按 4 s/页算机器只花几分钟，
但每页 1,000+ 字符的术语/公式/图表仍需人逐题核对。

## 4. 既有管线 `tools/batch_extract.py` 验证

pymupdf 与 rapidocr 均装成后，按既定命令实跑：

```
tools/batch_extract.py --scope mock --ocr auto --limit-pages 3
```

验证通过项：

| 要求 | 实测 |
|---|---|
| 输出隔离 | 仅写 `build/_scratch/408-raw-pages/`；未改 `papers/`、未改任何源 PDF |
| 逐页缓存命中 | ✅ 重复执行报 `缓存命中 3` |
| 源哈希绑定 | ✅ 每页记录 `source_sha256`；与 `index/sources-manifest.json` 不符即 `[stop]` 拒绝处理 |
| 逐页 unverified | ✅ `"status": "unverified"`，另存 `method`(`text-layer`/`ocr-unverified`)、`dpi`、`min_chars`、`characters`、`confidence_mean`、`contains_images`、`processed_at` |
| 断点续跑 | ✅ `--limit-pages` 限额生效后即退出，报"剩余下次可断点续跑" |
| 限流 | ✅ 单进程；26 页产物耗时 1.63 s（其中仅 1 页走 OCR） |

累计产物 26 页：**25 页 `text-layer` + 1 页 `ocr-unverified`**。

### 4.1 一处需注意的行为

set1 p13 走 OCR 后得 `characters: 0`、`confidence_mean: null`。
渲染核查该页**墨水占比 0.0000%，确为空白页**，故返回空是正确的。
但工具**不区分"空白页"与"OCR 失败/识别为空"**——两者都表现为 `characters: 0`。
批处理时应把 `characters: 0` 的页单独拉出人工确认，避免静默漏页。

## 5. 结论

1. **离线 CPU OCR 链路在本机跑通且开销极低**（无 GPU、无网络依赖、无大模型权重）。
2. **质量不足以直接入库**：均值置信 0.82 下仍稳定出现 `O→0`、`删→剩` 类错误，
   必须保留 `unverified` 标记并走人工校对。
3. **scale 2 是推荐工作点**，提高渲染倍率无收益。
4. **文字层页不该走 OCR**：388/483 页已有文本层，用 `pdftotext` 更快更准（阶段1 结论）。
5. 原 PDF 只读未改；OCR 输出仅在 `build/_scratch/`。

## 6. 未验证 / 待定

- 仅测 3 页、1 份扫描卷；其余 4 份扫描 PDF **未抽样**，结论不可外推。
- **未做人工校对**，本报告只描述引擎行为，**不含任何题目正确性结论**。
- 公式（上下标、位域下标、矩阵）与图形的保真度**未评**，一律 `unverified`。
- **未产出任何可入库的正式转录**，不触及完成度计数（不声称 1034 题中的任何完成数）。
- 未测英文/公式专用识别模型，未测倾斜矫正、去噪等前处理的影响。

## 7. 建议的下一步（待确认后再扩容）

1. **分流处理**：388 页文本层走 `pdftotext`（或 `tools/extract_text.py`），
   仅 ~95 页扫描页进 OCR。
2. **小批量先跑 5–10 页**扫描页，人工抽校后评估真实可用率，再决定是否铺开全库。
3. **OCR 输出一律带 `unverified` + 页码 + 源 PDF SHA**，进 `build/_scratch/`，
   校对通过后才谈入库。
4. 如质量仍不达标，再评估换识别模型（仍限 CPU、限包体积），
   **不要**引入 GPU 或大模型服务。

## 8. 可复现信息

- 渲染+OCR 单页脚本：`tools/ocr_cpu_pilot.py`（草稿性质，输出到 `build/_scratch/`）
- 批处理管线：`tools/batch_extract.py`（既有，输出到 `build/_scratch/408-raw-pages/`）
- 源 PDF：`sources/mock-2027/pdf/mock2027-set2-paper.pdf`
  SHA256 前缀 `dd1e0bcbea35f4ae`
- 输出样例：`build/_scratch/ocr/mock2-p2.txt` SHA256 前缀 `79c79db7abb7cae8`
  （gitignored，未入库）

## 9. 全库批处理执行记录（2026-10-16）

受控启动器 `tools/run_batch_dell.sh`（flock 互斥 + PID 文件 + 日志），
低优先级后台单 worker 跑完全库：

```
tools/run_batch_dell.sh --scope all --limit-pages 0 --timeout 1800
```

- 资源纪律：`nice -n 15`、`ionice -c3`、`OMP/MKL/OPENBLAS_NUM_THREADS=1`、单进程
- worker PID 292197，起止 17:29:53 → 17:36:00，**耗时 6 分 07 秒**，`status=0`，0 报错
- 日志 `build/_scratch/logs/batch.log`（gitignored）；结束自动释放锁与 PID 文件

### 9.1 终态计数

| 项 | 数 |
|---|---|
| 源 PDF | **44 / 44 全覆盖** |
| 总页 | **483** |
| `text-layer`（有文字层，直接抽取） | **387**（80.1%） |
| `ocr-unverified`（扫描页，走 RapidOCR） | **96**（19.9%） |
| 未处理 / 异常页 | **0** |
| `characters == 0` 的页 | **1**（set1 p13，已核实为真空白页：墨水占比 0.0000%） |
| `status: unverified` | **483/483 全部** ✅ |
| 源 PDF sha256 复验 | 抽 5 份 **5/5 一致**（源未被改动） |
| 产物体积 | 4.1 MB（`build/_scratch/408-raw-pages/`，gitignored） |

本次 96 页需 OCR 与阶段2 基于 `pdftotext` 的独立普查（≈95 页）**交叉吻合**。

### 9.2 边界

- 产物**全部 `unverified`**，**不得**当作已校对转录，**不得**计入 47/47 之类完成度；
  未生成、也不会生成正式的 `questions.md` / `solutions.md`。
- OCR 页（96 页）质量未逐页人工校对；阶段2 已实测均值置信约 0.82 下仍存在
  `O→0`、`删除→剩除` 类错误。
- 空白页与"OCR 识别为空"在元数据中都表现为 `characters: 0`，本库仅 1 例且已确认为真空白。
