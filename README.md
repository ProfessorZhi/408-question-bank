# 408 题库 · 408-question-bank

> **PUBLIC 仓库**（2026-10-18 起）。本仓库用于个人备考研究，**不做商业再发布**。
> 试卷原文著作权不属于本仓库，**公开可见不等于取得再分发许可**。
> 版权状况与使用边界见 [`RIGHTS.md`](RIGHTS.md) 与 [`docs/rights-and-licenses.md`](docs/rights-and-licenses.md)。

考研 408（计算机学科专业基础综合）题库。目标：把散落的 PDF / 图片试卷，整理成
**可长期维护、可自动质检、题析分离**的 Markdown 题库，并能一键生成
**学生卷（无答案）** 与 **教师解析卷**。

---

## 1. 覆盖范围（Scope）

| 集合 | 内容 | 题目构成 |
|---|---|---|
| `exams/2009` … `exams/2025` | 历年真题 | 40 选择 + 7 综合 = **47 题/卷** |
| `mock-2027/set-1` … `set-4` | 2027 模拟卷 1—4 | 40 选择 + 7 综合 = **47 题/卷** |

2026 真题资料已存在于参考源，但**不在本仓库承诺范围内**（未纳入验收口径）。

**验收硬指标**：每一卷必须 **47/47 完整**——题号连续、选项齐全、公式/代码/图表可用、
每道题在解析文件中都有对应条目。
**不允许**用少量示例题「充数」为一整卷。未完成的卷在 `index/coverage.md` 中如实标为
`incomplete`，不许含糊。

---

## 2. 目录结构

```
.
├── RIGHTS.md                  # 版权与使用边界（先读这个）
├── docs/
│   ├── provenance.md          # 来源登记表：上游 URL + commit SHA + 许可 + 使用范围
│   ├── rights-and-licenses.md # 逐来源权利分析与结论
│   ├── structure.md           # 数据组织规范（卷/题/元数据/图片）
│   ├── qa-policy.md           # 质检规则与状态机
│   ├── roadmap.md             # 阶段计划与当前状态
│   └── transfer-instructions.md # 素材如何传到本机（缺件时看这里）
├── schema/
│   └── question.schema.json   # 卷元数据 meta.yml 的 JSON Schema
├── sources/                   # ★ Source of truth（原样保存，只增不改）
│   ├── exams/papers/          # 真题试卷 PDF
│   ├── exams/answers/         # 真题答案 PDF
│   └── mock-2027/pdf/         # 2027 模拟卷 试题/解析 PDF
├── papers/                    # ★ Markdown 转录（题析分离）
│   ├── exams/<year>/
│   │   ├── meta.yml           # 卷元数据 + 每题状态
│   │   ├── questions.md       # 学生卷：题干 + 选项
│   │   ├── solutions.md       # 教师卷：答案 + 解析
│   │   └── assets/            # 该卷本地化图片
│   └── mock-2027/set-<n>/     # 同上结构
├── assets/                    # 跨卷共用图片（如有）
├── index/                     # 生成物：清单与覆盖统计
│   ├── sources-manifest.json  # 每个 PDF 的 sha256/页数/文本层/图片数
│   └── coverage.md            # 逐卷完成度
├── build/                     # 生成物：学生卷 / 教师卷（可发布）
├── tools/                     # 工具链
│   ├── inventory.py           # 扫描 sources/ 生成清单
│   ├── extract_text.py        # PDF 文本层提取（OCR 回退）
│   ├── qa_paper.py            # ★ 单卷质检：47/47、图片、答案题号对应
│   └── build_paper.py         # 生成学生卷 / 教师卷
└── .github/workflows/qa.yml   # CI：每次 push 跑全量质检
```

---

## 3. 数据模型

每卷三个文件，**题析物理分离**：

- `questions.md` —— 只含题干与选项。**禁止出现答案**（字段名、注释、折叠块都不行）。
- `solutions.md` —— 每题一条 `## 第 N 题`，含答案与解析。
- `meta.yml` —— 卷元数据；每题一条 `status`，取值见 `docs/qa-policy.md`。

题干与解析通过**题号 N** 关联，不通过标题文字匹配。质检脚本按题号集合做双向校验。

题目内的图片一律**本地化**到该卷 `assets/`，以相对路径引用：
`![图1](../assets/2009-q16-fig1.png)`。禁止外链。

---

## 4. 用法

```bash
# 1) 重建来源清单（新增 PDF 后跑）
python tools/inventory.py

# 2) 单卷质检 / 全量质检
python tools/qa_paper.py papers/exams/2009
python tools/qa_paper.py --all

# 3) 生成学生卷与教师卷
python tools/build_paper.py papers/mock-2027/set-1 --student -o build/
python tools/build_paper.py papers/mock-2027/set-1 --teacher -o build/
```

CI（`.github/workflows/qa.yml`）在每次 push 跑 `qa_paper.py --all`，
未达 47/47 的卷会被标红——这是**已知且被接受**的状态，直到该卷转录完成。

---

## 5. 状态与完成度

当前进度、每卷完成度、缺哪些材料，一律以
[`index/coverage.md`](index/coverage.md) 与 [`docs/roadmap.md`](docs/roadmap.md) 为准。
README 不手写进度数字，避免与生成物不一致。

---

## 6. 版权

本仓库**不主张**对试卷原文的著作权。试卷内容版权归其原始权利人
（教育部教育考试院等）。本仓库仅为个人研究目的做格式转换与整理，
来源逐条登记在 `docs/provenance.md`。

详见 [`RIGHTS.md`](RIGHTS.md)。
