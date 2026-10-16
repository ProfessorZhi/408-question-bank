# 模拟卷4：源页定点核验 · 第二批（2026-10-17，Dell 隔离分支）

> **本卷依然不是完成品。** 本轮只把 **5 道选择题**的题干与选项按源 PDF 渲染图逐字重录，
> 并核验了 **40 条选择题答案**的来源原表。全卷 **0 题 `proofread`**，
> `questions.md` / `solutions.md` **仍未建立**（理由见 §6）。

## 0. 本轮工作位置

| 项 | 值 |
|---|---|
| 主机 | Dell-LLM-Lab |
| 目标仓库 | `/home/fjd/workspaces/408-question-bank-dell/repo`（私有 `ProfessorZhi/408-question-bank`） |
| 隔离工作树 | `/home/fjd/workspaces/408-question-bank-dell/worktrees/mock4-source-review-20261017` |
| 本分支 | `work/408-mock4-dell-source-review-20261017` |
| 基（源）分支 | `origin/work/408-mock4-ocr-working-draft-20261017` @ `f75d71b` |
| 未改动 | `main`、`work/dell-408-transcription-20261016`、其它工作树；未 force push；未用 Actions |

工作树由 `git worktree add -b` 从远端源分支创建，目标目录与分支名事先确认均不存在，无覆盖。

## 1. 本轮修复：第 3、10、11、12、13 题

这 5 题属于既有审计列出的 **17 道未通过 A–D 严格选项检查**的题。原稿的病根是同一类：
**四个选项被 OCR 挤在同一行**，且正文含大量误字，因此 `qa_paper.py` 的 C4 判为「选项不齐」。

修复方式：把试题 PDF 对应页渲染为图像（400 dpi，只读），**逐字读取**后重录题干与 A–D 选项，
每个选项独占一行。**只重录题干与选项，不据此判定标准答案。**

| 题 | 源页 | 原稿典型误字 → 源图实际 |
|---|---|---|
| 3 | 试题 PDF 第 2 页 | 二又树→二叉树；正殉→正确；逼历→遍历；时结点→叶结点；`A.IIT、IV B.工、了、IV…`→`Ⅲ、Ⅳ / Ⅱ、Ⅲ、Ⅳ / Ⅱ、Ⅲ / Ⅳ` |
| 10 | 试题 PDF 第 3 页 | MINTMAX→MINIMAX；`-创建…最小站`→Ⅰ.；`IIL`→Ⅲ.；`A. I，亚 B. Q，开…`→`Ⅰ、Ⅲ / Ⅱ、Ⅲ / Ⅰ、Ⅱ、Ⅲ / Ⅰ、Ⅱ` |
| 11 | 试题 PDF 第 3 页 | 块速→快速；基致→基数；竟定→稳定；推排序→堆排序；铺助→辅助 |
| 12 | 试题 PDF 第 3 页 | 机嚣语言→机器语言；一名→一句；这笠→这样；`D. 甫天和旭售`→**D. 解释程序** |
| 13 | 试题 PDF 第 3 页 | 阶公之差→阶码之差 |

每题正文内已加 `<!-- source: 试题PDF第N页; verification: image-reviewed question/options -->`
与一条核对说明，注明「仅核对题干与选项，未判定标准答案，整题仍未 proofread」。

## 2. 机器闸门前后对比（可复现）

`questions.md` 尚未建立，故把两份 draft 临时装配成一份「partial 卷」再跑闸门（见 §7）。

```
修复前（HEAD = f75d71b）
  choice=40/40 comp=7/7 total=47/47
  C4 选项不齐共 17 题：3(A), 10(A), 11(AC), 12(A), 13(A), 14(BCD), 16(A), 17(A), 18(AC), …

修复后（本分支）
  choice=40/40 comp=7/7 total=47/47
  C4 选项不齐共 12 题：14(BCD), 16(A), 17(A), 18(AC), 20(AC), 21(AC), 22(ACD), 24(A), 29(AC), 36(A), 37(CD), 39(A)
```

**清掉的正是 3、10、11、12、13 这 5 题**，与预期完全一致；两轮均 **0 阻断**（C7 图片缺失、C8 答案泄漏皆无）。

其余闸门本轮结果：

| 闸门 | 结果 |
|---|---|
| C1 / C2 / C3 | ✅ 40/40、7/7、47/47 |
| C4 | ⚠️ 12 题仍不齐（即上表，全是尚未源页核对的题） |
| C5 题号双向一致 | ✅ 无告警 |
| C6 答案字母可解析 | ✅ 40/40 |
| C7 图片存在 | ✅ 无阻断（本卷正文未引用 `assets/`，故无坏链） |
| C8 答案泄漏 | ✅ 无阻断 |
| C9 `proofread` | **0/47** |
| `validate_meta.py` | ✅ 22 份 meta.yml，不合规 0 份 |

`audit_drafts.py`（针对 partial 装配）：

```
[audit] 题 47  解 47  图 0  公式(行内/块) 19/0  代码块 0
[audit] 风险: high=28 medium=0
    empty-option: 28
```

28 条 `empty-option` 全部落在上述 12 道未核对题上；**没有** `no-answer`、`no-solution`、
`qset`、`missing-image`、`answer-leak` 类告警 —— 即「题号齐、答案可解析、无坏链」，
差的只是这 12 题的选项正文与其余内容的逐字校对。

## 3. 40 条选择题答案：已核对来源原表

按 `mock2027-set4-solution.pdf` **第 1 页「一、单项选择题」答案表**逐字核对，
40 条字母与原表**完全一致**（01.B 02.A 03.A 04.D 05.C 06.C 07.A 08.C 09.B 10.A /
11.B 12.D 13.B 14.A 15.A 16.A 17.B 18.C 19.D 20.A / 21.B 22.C 23.B 24.C 25.C 26.D 27.B 28.D 29.D 30.A /
31.B 32.D 33.B 34.C 35.D 36.C 37.A 38.C 39.A 40.D）。

另有 **3 条独立旁证**：解析 PDF 第 5 页 Q38/Q39/Q40 的解析正文分别得出 C / A / D，
与答案表一致。**这仍不等于「答案正确」**——它只证明「我们抄录的字母与源 PDF 答案表一致」，
不等于命题方答案本身无误，也不等于选题目干已校对。

## 4. 41—47 综合题解析：**确认未逐字一致**（本轮只核查，未修复）

抽查解析 PDF 第 5 页（Q41 起、Q42 开头）与草稿逐句对比，**发现真实缺陷**，因此 41—47 一律保持 `ocr-uncertain`：

1. **整段丢字**：源「因为存在这样的根结点，**根结点关键字 <** 左孩子结点的关键字 < 右孩子结点的关键字」，
   草稿丢掉了「根结点关键字 <」。
2. **丢字**：源「在题目举例介绍的基数树中，**结点 10** 的左孩子是 100」，草稿作「…基数树中，的左孩子是 100」。
3. **代码块被 OCR 打坏**：源
   `bool isEnd; // 标记当前结点是否为深色结点` / `string result; // isEnd == True时…` / `TreeNode *lChild, *rChild;` / `}`
   在草稿里成了 `bool isEna; // 标` / `string result; // isEna` / `TreeNode *1Child，*rChildy` / `】`。
4. **时间复杂度符号错**：源为 `O(n)`（两处），草稿作 `O(m)` 与 `O(D`。
5. **确认存在跨题串段（1 行）**：Q41 代码注释里的「isEnd == True时，result存储相应的位串的结果」
   被 OCR 甩进了 Q42 第 (1) 问的段落中。这与既有审计「Q41–47 解析可能跨题串段」的判断一致。
6. **页码归属反而是对的**：草稿标 Q41=解析 p5、Q42=解析 pp5–6，与源 PDF 实际一致（Q41 始于 p5 下半页）。

结论：41—47 需要一次**逐页整段重录**，不是打补丁能解决的。本轮**未**改动这 7 题任何文字。

## 5. 当前剩余阻断（诚实清单）

| # | 剩余项 | 数量 |
|---|---|---|
| 1 | 选择题选项仍未通过 A–D 源页核对 | **12** 题：14、16、17、18、20、21、22、24、29、36、37、39 |
| 2 | 选择题未做任何源页核对（选项结构侥幸没被 C4 抓到） | 3 题：6、8、25 |
| 3 | 综合题 41—47 题干与分析未逐字校对 | 7 题 |
| 4 | 题目图仍未裁入 `assets/`（本卷引用 0 张，故无坏链，但也无图） | 0 张已入库 |
| 5 | `proofread` | **0 / 47** |

## 6. 为什么本轮**没有**建立正式 `questions.md` / `solutions.md`

`draft-ocr-all-questions-source-reviewed20.md` 自己的抬头写明：升级为正式 `questions.md`
的条件是「逐题选项、图表、代码和公式**全部**与源 PDF 核验」。本轮只把核对题数从 20 提到 **25**，
条件未满足，因此**不升级**，只改 draft 本体。这样：
- 不会让一份 22 题仍 `ocr-uncertain` 的稿件冒充整卷；
- `qa_paper.py --all` 对 `mock-2027/set-4` 仍会如实报「questions.md 不存在（本卷尚未开始转录）」。

## 7. 复现

```bash
WT=/home/fjd/workspaces/408-question-bank-dell/worktrees/mock4-source-review-20261017
PY=/home/fjd/workspaces/408-question-bank-dell/venv/bin/python          # pyyaml + pymupdf
PYV=/home/fjd/workspaces/408-question-bank-dell/venv-compare/bin/python # 另含 jsonschema

# 1) 元数据 schema
$PYV tools/validate_meta.py

# 2) 结构闸门：把两份 draft 临时装配成 partial 卷再跑（build/_scratch 已在 .gitignore）
mkdir -p build/_scratch/mock4-partial
cp papers/mock-2027/set-4/draft-ocr-all-questions-source-reviewed20.md build/_scratch/mock4-partial/questions.md
cp papers/mock-2027/set-4/draft-ocr-all-solutions.md                 build/_scratch/mock4-partial/solutions.md
cp papers/mock-2027/set-4/meta.yml                                   build/_scratch/mock4-partial/meta.yml
$PY tools/qa_paper.py build/_scratch/mock4-partial

# 3) 内容审计：audit_drafts.py 只认 papers/<id>/questions.md，故需临时落一份再删
mkdir -p papers/_staged-mock4-partial
cp build/_scratch/mock4-partial/{questions.md,solutions.md,meta.yml} papers/_staged-mock4-partial/
$PY tools/audit_drafts.py --paper _staged-mock4-partial
rm -rf papers/_staged-mock4-partial
```

源页图渲染（PDF 只读）：

```bash
# 裁剪辅助脚本：参数 = <pdf> <页码> <x0> <y0> <x1> <y1> <dpi> <输出>
python scripts/crop.py sources/mock-2027/pdf/mock2027-set4-paper.pdf 3 0.08 0.465 1.00 0.585 400 q10.png
```

## 8. 工具链观察（非本卷内容，建议后续处理）

`tools/audit_drafts.py` 在目标卷缺 `questions.md` 时**未捕获异常**，直接抛 `FileNotFoundError`
栈回溯退出（`main()` 第 145 行直接读文件）。`qa_paper.py` 对同样情况是**优雅降级**并给出
「尚未开始转录」的可读提示。建议让 `audit_drafts.py` 对齐 `qa_paper.py` 的行为。

## 9. 下一步（按性价比排序）

1. 继续攻剩下 **12 题**（14、16、17、18、20、21、22、24、29、36、37、39）的选项 —— 同本轮方法，
   按试题 PDF 第 4—7 页渲染图定点核读，尤其注意 **36/37 跨页**与 **37 与 36、38 同页**的图码归属。
2. 41—47 综合题**整段重录**（解析 PDF 第 5—8 页），替换 §4 列出的 6 类缺陷。
3. 逐题补 `assets/` 图并按相对链接引用（39、37、41、47 等含图题），每张图确认归属后再入库。
4. 以上齐备后才考虑把 draft 升级为正式 `questions.md` / `solutions.md`，再谈 `proofread`。
