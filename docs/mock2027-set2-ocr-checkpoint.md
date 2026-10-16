# 2027 模拟卷 2 · OCR 重建检查点（draft-partial）

> 状态：**部分草稿，未达完整卷标准**。全部内容为机器 OCR，**0 题人工校对**（`proofread` 保持 0）。

## 1. 本卷为何是 draft-partial

`papers/mock-2027/set-2/` 只有 `draft-partial-questions.md` / `draft-partial-solutions.md`，
**没有** 正式的 `questions.md` / `solutions.md`。

| 项 | 结果 |
|---|---|
| 题号 | **47/47**（OCR 重建后无缺号） |
| 选择题答案 | 40/40 条 OCR 标记（来自解析 PDF 的 OCR，**未校对**） |
| 综合题解析段 | 7/7 段（OCR，未校对） |
| **选项齐备** | ❌ **5 题不全**：`3(AC)`、`5(ACD)`、`7(AC)`、`18(ACD)`、`19(ACD)` |
| QA | `qa_paper` choice=40/40 comp=7/7，**C4 警告 5 题**；0 阻断 |

按既定规则「不可把 0 内容补足以通过 QA」，**未**把选项补空壳凑齐，故降级为 draft-partial。

## 2. 本轮真正的技术进展（`tools/prepare_mock_ocr.py`）

纯扫描卷此前只能靠缓存 OCR，题号 40/47。本轮新增**页级重建**：

1. 每页做 **scale 2/3/4 多倍率**识别，检测框按 `(y, x)` 归并为行；
2. **题号分隔符归一化** —— 这是关键修复：
   OCR 常把题号后的分隔符识别错，例如
   - `06, 列关于有向图连通分量特性的欲述中…`（逗号）
   - `11。对元素个数相同的不同初始序列…`（句号）
   两者都逃过 `[.．、]` 的正则，导致漏题或**重复插入题号**（曾出现 `11. 11。…`）。
   现统一为 `NN. `；
3. 输出到 `build/_scratch/mockocr/<pdf-stem>/`（**不改** `408-raw-pages` 原缓存），
   由 `build_drafts.load_pages` 自动优先读取。

效果：set-2 题号 **40/47 → 47/47**。

配套：`index/image-verified-numbers.json` 记录**已由源页图确认、但 OCR 漏检**的题号
（卷 / 真实题号 / PDF 页码 / 题干 anchor / 证据）；`prepare_mock_ocr` 仅在 anchor
**唯一追溯**时才插入题号，否则记 `unresolved`，**绝不按序号推断**。

`tools/build_drafts.py` 同时增加**分级宽容选项识别**（strict → 冒号 → 允许字母后直接跟中文），
修复扫描件里 `A除单表…` / `B，在链表…` 这类丢失分隔符的选项。

## 3. 已按源页图补录的选项（`index/image-verified-content.json`）

| 题 | 源页 | 选项 | 证据 |
|---|---|---|---|
| set-2 Q8 | p3 | A=`II、III` B=`III` C=`III、IV` D=`II、IV` | GitHub Issue #3 目视 |
| set-2 Q33 | p6 | A=`I、II` B=`I、III` C=`II、III` D=`I、II、III` | GitHub Issue #3 目视 |

> **只录选项正文，不推断正确答案。** `override: true` 表示覆盖 OCR 的空值/错误值。

## 4. 仍需处理（下一阶段）

1. **补全 5 题残缺选项**：3、5、7、18、19。需按源页图（PDF 页见 Issue #3 与卷内页码）
   逐条读出后写入 `image-verified-content.json`，**不得推断**。
2. 全部 40 条选择题答案与 7 段解析仍是 OCR，**需逐题对照解析 PDF 校对**后才能谈 `proofread`。
3. 图形/代码/数学未校对：`assets/` 8 张图为内嵌位图提取，归属与内容未核。

## 5. 复现

```bash
tools/prepare_mock_ocr.py --paper mock-2027/set-2          # 页级重建（约 1–2 分钟）
tools/build_drafts.py --paper mock-2027/set-2              # 生成 draft-partial-*
tools/qa_paper.py papers/mock-2027/set-2
tools/audit_drafts.py --paper mock-2027/set-2
```

## 6. 失败/受限记录

- `scale 5/6` 对 RapidOCR 在本扫描件上**无新增检出**，已停止加码（不再做整卷高倍率重扫）。
- `prepare_mock_ocr` 对 Q6 的 anchor（`…特性的叙述中…`）报 `unresolved`：
  实际 OCR 把「叙述」认成「欲述」，anchor 未命中。**但该题号已由分隔符归一化正确检出**，
  故不影响结果；anchor 机制仅作兜底。
