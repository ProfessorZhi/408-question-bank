# 阶段计划与当前状态

状态基准日期：**2026-10-16**。

---

## 阶段划分

| 阶段 | 目标 | 状态 |
|---|---|---|
| **P1 · 建仓与骨架** | 隔离目录、PRIVATE 仓库、目录规范、来源登记、权利分析、QA 机制、素材落盘 | ✅ 完成 |
| **P2 · 真题转录（2009—2024）** | 逐年转录 40+7 题，题析分离，图片本地化 | ⏳ 未开始 |
| **P3 · 2025 完整卷** | 47 题完整，答案三方交叉核对 | ⏳ 未开始 |
| **P4 · 2027 模拟卷 1—4** | 每卷 47 题；落实卷 1 解析首页勘误 | ⏳ 未开始 |
| **P5 · 生成与发布形态** | 学生卷 / 教师卷构建产物、索引视图 | ⏳ 未开始 |
| **P6 · 校对闭环** | 逐题 `needs-review → proofread`，C10 关键计算人工核 | ⏳ 未开始 |

---

## P1 已完成清单（可核验）

- [x] 独立工作目录：`C:\Users\vince.huang\Documents\408-question-bank`（新建，此前不存在）
- [x] PRIVATE 仓库：<https://github.com/ProfessorZhi/408-question-bank>
- [x] 目录规范与数据模型：`docs/structure.md`、`schema/question.schema.json`
- [x] 来源登记（4 条来源 + 1 条缺失件）：`docs/provenance.md`
- [x] 权利分析（含上游 LICENSE 存档与「无 LICENSE」结论）：`docs/rights-and-licenses.md`、`sources/_upstream-licenses/`
- [x] QA 规则与状态机：`docs/qa-policy.md`
- [x] 工具链：`tools/inventory.py`、`tools/qa_paper.py`、`tools/build_paper.py`、`tools/extract_text.py`
- [x] CI：`.github/workflows/qa.yml`
- [x] 真题 PDF 入库：2009—2025 试卷 17 份 + 答案 17 份（`sources/exams/`）
- [x] 2027 模拟卷 PDF 入库：试题/解析各 4 份（`sources/mock-2027/pdf/`）
- [x] 素材缺件结论：`408-question-bank-import-staging.zip`（44MB）**未到设备**

## P1 未完成 / 已知缺口

- [ ] **44MB 页面图像包未到设备** —— 影响图表像素级对照（见 `docs/transfer-instructions.md`）
- [ ] `papers/` 下**尚无任何转录正文** —— 每卷 md 都还没写
- [ ] `papers/exams/<year>/meta.yml` 未逐题枚举
- [ ] CI 尚未在 GitHub 上跑过一次（本地跑得到结果，但远端首跑待首次 push 后确认）

---

## P2—P6 的执行顺序（建议）

1. **先做 2025（P3）**：只有一卷，且已有三方材料（PDF 试卷 + PDF 答案 + Tommy 的 Markdown
   线索），最适合把「转录 → 交叉核对 → 校对」整条流水线跑通一遍。
2. **再做 2027 模拟卷 4 卷（P4）**：**用户自有材料**，权利最干净，且是本次主材料；
   卷 1 的勘误清单能顺带验证「勘误落实」流程。
3. **最后做 2009—2024 真题（P2）**：量大（16 卷 × 47 题 = 752 题），
   底本又是重排版（有已知错字率），需要最成熟的流水线。
4. P5 生成形态可**穿插进行**：只要有一卷完成就能验证 `build_paper.py`。

---

## 风险登记

| 风险 | 影响 | 缓解 |
|---|---|---|
| 真题底本是「基于图片重生成」的，非官方扫描，含约 1 错/100KB | 转录出的文字可能带错 | 逐题标 `confidence`；存疑处保留页图对照；C10 人工核关键计算 |
| 缺 44MB 页面图像包 | 图表无法像素级核对 | P1 用 PDF 内嵌图替代；到货后补对照 |
| 第三方 Markdown（DongDong/Tommy）质量不可靠 | 若误采信会污染答案 | 已明确规则：答案**只**来自 source PDF（`docs/qa-policy.md` §3） |
| 752 + 188 题的转录量巨大 | 长期未完成 | 状态机允许「部分完成且可见」；CI 只阻断真假错误，不阻断进度 |
| 试卷内容权利人不明 | 无法公开 | 仓库保持 PRIVATE；`RIGHTS.md` 写死禁止转 public |
