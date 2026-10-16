# 质检规则与状态机

原则：**宁可标记「未完成」，不要假装完成。**
凡是没把握的内容，状态写成 `needs-review` 并在 `notes` 里写清**为什么**。
绝不猜测、绝不「补全得像真的」。

---

## 1. 逐题状态机

```
                 ┌──────────────────────────────────────────┐
                 │                                          │
  (无) ──▶ pending ──转录──▶ needs-review ──校对──▶ proofread
                 ▲             │    ▲                   │
                 │             │    │                   │
                 └── 材料缺失 ──┘    └── 复核发现疑点 ────┘
                       blocked              │
                                           ▼
                                     needs-review
```

| 状态 | 含义 | 允许的下一步 |
|---|---|---|
| `pending` | 还没转录 | → needs-review |
| `blocked` | 缺材料（如缺页图），无法继续 | 等材料到 → needs-review |
| `needs-review` | 已转录，但**未**逐题对照原文 | → proofread |
| `proofread` | 已逐题对照 source PDF（必要时含页图），题号/选项/公式/图表均核过 | 终态；若发现疑点回退 |
| `ocr-uncertain` | 有内容但 OCR/文本层不可信，**保留原文并标注** | 人工确认 → needs-review |

**关键约束**
- 从 `needs-review` → `proofread` 必须**有对照动作的证据**（在 `notes` 里写清对照了什么、
  哪一页、发现什么问题）。
- **批量把状态改成 `proofread` 而不实际对照 = 造假。** CI 会在 `coverage.md` 里标出
  「`proofread` 但无对照记录」的题，作为审计线索。

## 2. 卷级验收（硬指标）

一卷**只有**同时满足下面全部，才能标 `complete`：

| # | 检查 | 判定 |
|---|---|---|
| C1 | 选择题题号集合 `== {1..40}` | `qa_paper.py` 自动 |
| C2 | 综合题题号集合 `== {41..47}` | `qa_paper.py` 自动 |
| C3 | 合计 `== 47` | `qa_paper.py` 自动 |
| C4 | 每道选择题恰有 A/B/C/D 四个选项 | `qa_paper.py` 自动 |
| C5 | `questions.md` 题号集合 `== solutions.md` 题号集合 | `qa_paper.py` 自动 |
| C6 | 每道选择题在 solutions 里有可解析的答案字母 | `qa_paper.py` 自动 |
| C7 | `questions.md` 中引用的每个图片文件**存在** | `qa_paper.py` 自动 |
| C8 | `questions.md` 中**不含**答案泄漏关键词 | `qa_paper.py` 自动 |
| C9 | 逐题 `status ∈ {proofread}` 或已登记豁免 | `qa_paper.py` 自动（报告，不阻断） |
| C10 | 关键计算（数值题）与 source PDF 核对一致 | **人工**，结果记入 notes |

C1—C8 是**机器闸门**，CI 必须绿。C9—C10 是**人工闸门**，进 `coverage.md` 供追踪。

## 3. 答案相关规则（最易出错处）

1. **答案只能来自 source PDF 的答案/解析文件**，不能来自第三方 Markdown。
   （本次已实测 DongDong 上游答案含大量 `?` 占位——见 `docs/provenance.md` S2。）
2. 上游若自述有勘误（如 2027 模拟卷 1 解析首页的「勘误」清单），
   **必须逐条落实**，并在该题 `notes` 里写明「已按勘误第 X 条修正」。
3. 选择题答案出现 `?` / 空 / 与解析文不一致 ⇒ **一律 `needs-review`**，不许二选一猜测。
4. 综合题答案若 source 里是图片（手写/扫描），允许转写，但必须在 `notes` 标
   `confidence: low` 并保留对应页图路径。

## 4. 图片规则

- **本地化**：所有图必须下载/截取到 `assets/`，禁止外链、禁止 base64 内联。
- 检查 C7 只验「文件存在」。**像素级正确性**靠人工（或与 44MB 页面图像包对照）。
- 页面整页截图（`papers/**/_pages/`）算 **interim 产物**，**不算**完整 Markdown 的一部分，
  且被 `.gitignore` 排除。

> ⚠️ **只用页面图片索引 ≠ 完成转录。** 这是本次任务明确要点：
> 页面图只是过渡形态，最终交付必须是逐题可编辑的 Markdown。

## 5. 公式与代码

- 公式：LaTeX。行内 `$...$`，块 `$$...$$`。
- 代码：带语言标注的围栏块（```c / ```python / ```asm）。
- **不允许**用图片代替本可打字的公式与代码——那是把问题藏起来。

## 6. 不可信内容怎么处理

发现以下任一情况，**保留原文、加标记、不改写**：

| 情况 | 标记 |
|---|---|
| OCR 出怪异字符/断字 | `ocr-uncertain` + notes 写原文片段 |
| PDF 文本层缺字（重排版底本的已知问题） | `needs-review` + notes 标「文本层缺失，待页图确认」 |
| 答案与解析文矛盾 | `needs-review` + notes 列出两处原文 |
| 题号在 source 里就跳号/重复 | `needs-review` + notes 说明，**不自行重编号** |

## 7. CI 行为

`.github/workflows/qa.yml` 在每次 push / PR 跑：

```bash
python tools/qa_paper.py --all --json index/qa-report.json
```

- **阻断**：C7（图片缺失）、C8（答案泄漏）——这两类是「已经错了」，必须修。
- **报告不阻断**：C1—C6、C9——转录尚未完成是**已知且被接受**的状态，
  在 `coverage.md` 与 job summary 里展示完成度。
- 已完成的卷若 C1—C6 掉红，那是**回归**，必须修。

> 判断依据：C1—C6 在转录中途必然红。把一个「尚在建设中」的仓库 CI 全绿是自欺；
> 真正的护栏是让**完成度可见**、让**已完成的部分不许回退**。
