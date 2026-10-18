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
- [ ] **CI 已配置但从未真正执行过** —— 见下节「CI 实测结果」。**不要**把它当作验证过的护栏。

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

## CI 实测结果（2026-10-16）

首次 push 后 GitHub Actions 起了 1 次 run（run id `38857392737`），**失败**，特征是：

- 耗时 **2 秒**（`startedAt 05:45:00Z` → `completedAt 05:45:02Z`）
- job 的 `steps` 为**空数组** —— **没有任何一个 step 被执行**
- 取失败日志时报 `results-receiver.actions.githubusercontent.com ... EOF`

**判断**：这是 **runner/基础设施层面**的问题，**不是**质检脚本失败
（脚本一步都没跑）。此前在本机其它仓库上见过完全相同的签名。

因此：

- ❌ **不能说 CI 已经验证通过**。它现在只是一个「提交的配置」，不是有效的护栏。
- ✅ 同等的检查在本机**逐条实跑通过**（证据见下）。
- 待办：查该账号的 Actions 是否被禁用 / 配额耗尽；确认后再声称 CI 生效。
  诊断曾被本机到 `api.github.com` 的 TLS 阵发失败打断（见
  `docs/provenance.md` 同类网络记录），未得结论。

### 本机实跑证据（可复现）

| 命令 | 结果 |
|---|---|
| `python tools/selftest_qa.py` | ✅ 5/5 对照样本判定与期望一致（**能翻红也能翻绿**） |
| `python tools/validate_meta.py` | ✅ 21 份 meta.yml，不合规 0 份 |
| `python tools/inventory.py` | ✅ 48 个文件（PDF 42 个），登记 sha256/页数/文本层 |
| `python tools/qa_paper.py --all --write-coverage` | ✅ 21 卷，阻断 0 卷（均为「尚未转录」） |

> 校验过程中 schema 实际抓到两个**真缺陷**（不是误报）：
> ① `extraction.method: pending` 不在枚举内；
> ② 生成 YAML 时键名 `no` 未加引号，被 YAML 1.1 解析成布尔 `False`，**题号静默丢失**。
> 两者都已修。这说明校验链路是有效的，不是摆设。

---

## 风险登记

| 风险 | 影响 | 缓解 |
|---|---|---|
| 真题底本是「基于图片重生成」的，非官方扫描，含约 1 错/100KB | 转录出的文字可能带错 | 逐题标 `confidence`；存疑处保留页图对照；C10 人工核关键计算 |
| 缺 44MB 页面图像包 | 图表无法像素级核对 | P1 用 PDF 内嵌图替代；到货后补对照 |
| 第三方 Markdown（DongDong/Tommy）质量不可靠 | 若误采信会污染答案 | 已明确规则：答案**只**来自 source PDF（`docs/qa-policy.md` §3） |
| 752 + 188 题的转录量巨大 | 长期未完成 | 状态机允许「部分完成且可见」；CI 只阻断真假错误，不阻断进度 |
| 试卷内容权利人不明 | 无法公开 | **2026-10-18 所有者决定转为 PUBLIC**；许可问题本身未解决，见 `RIGHTS.md` 变更记录 |
