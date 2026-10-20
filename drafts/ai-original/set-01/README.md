# 408 AI Original · Set 01（完整初稿 v3.2 · 原创机制和卷面可读性优化）

**已成稿：47/47题；40道单选、160个选项；7道综合题；150分、180分钟目标；15张SVG。** 当前状态是 `complete-draft-author-checked`，不是独立专家终审或考生试做校准后的正式命题。

## 直接使用

- **[学生卷：questions.md](questions.md)**：完整47题，只包含题干、选项、题图与一般约定。
- **[教师解答：solutions.md](solutions.md)**：40题答案表、逐项错因、7道综合题推导及分步评分细则。
- [逐题状态：review.md](review.md)、[实际验算范围：verification.md](verification.md)、[题图清单：figure-plan.md](figure-plan.md)。
- **[对标2024–2025阅读负担与卷内重复](readability-audit.md)**：26道小题压缩记录、可重复的长度指标、答案位置分布；[校验脚本](audit_readability.py)。
- **[综合题阅读负担与卷内重复审计](reading-load-audit.md)**：2024/2025和Set01现存Markdown题面长度对照、Q19与Q43同机制重叠的修正。
- [Q46/Q47独立算法模型复核脚本](audit_v3.py)：作者二套算法与反事实测试，不等于外部专家签核。
- **[2009–2025 历年119道综合题原创性纵向审查](originality-evolution-2009-2025.md)**：逐年机制演化、网络大题追踪、对Set 01七题的重新审稿。现有Q41–Q47已成稿，但原创性**未通过终审**，不得据程序验算绿色推定命题满分。
- [OS/CN改题记录：revision-20261020-focus.md](revision-20261020-focus.md)；[七大题原创性与常规考法分配](originality-balance-v3.md)。
- [机器可读清单：item-plan.json](item-plan.json)、[题目数据真值：specs/exam.json](specs/exam.json)。后者**含答案**，不得作为学生公开作答页面的一部分。

## 构成

| 科目 | 单选 | 综合 | 分值 |
|---|---:|---:|---:|
| 数据结构 | Q1–11 | Q41=13、Q42=10 | 45 |
| 组成原理 | Q12–22 | Q43=12、Q44=11 | 45 |
| 操作系统 | Q23–32 | Q45=7、Q46=8 | 35 |
| 计算机网络 | Q33–40 | Q47=9 | 25 |
| **合计** | **40题 / 80分** | **7题 / 70分** | **150** |

Q41是带重复版本号的有序链表公共连续段算法；Q42为AVL插入、前驱删除与查找；Q43–44共享一套明确的教学ISA和流水线规则；Q45为双订阅者逐版本交付的同步设计与反例诊断；Q46在明确定义的写时复制规则下考查页框引用计数、异常与复制；Q47由链路代价变化推出稳定最短路径、混合路由暂态环路及唯一的逐台安全更新顺序。

Q19已从与Q43前三条指令重合的流水线题更换成微程序字段编码，不再提前提示Q43的load-use停顿。相较方向稿，题图从预计8张增加到**14张学生图+1张教师专用AVL答案图**。图由结构化数据和确定性SVG代码制作，并非让生成模型猜边、猜位宽。表格、代码和纯文字能表达清楚时不强行加图。

## 已做与未做

**已做**：完整题面与解答；出题者逐项逻辑检查；41题计算/枚举/模拟交叉检验；6题概念性作者解释；Q46包含COW逐步页框模拟，Q47独立枚举全部6种转发表更新顺序；15张SVG可逐字节重现；原版图做过作者目视检查，v3新增或重绘题图仍需独立视觉审稿与纸面试读。

**未做**：第二位命题专家独立盲审、真实考生180分钟试做、项目反应理论/区分度统计、全网原创性唯一性检索。**2024–2025同档难度与10/10质量是目标，不是已验证结论。** 条件完整和程序测试通过不自动等于每个自然语言干扰项都已由机器证明。

## 可复现检查

```bash
python drafts/ai-original/set-01/check_plan.py
python drafts/ai-original/set-01/render_figures.py --check
python drafts/ai-original/set-01/verify_paper.py --json /tmp/ai408-validation.json
python drafts/ai-original/set-01/audit_readability.py --json /tmp/ai408-readability.json
python drafts/ai-original/set-01/audit_v3.py
```

前两项使用Python标准库；第三项还需要C11编译器gcc或cc。编译产物只在临时目录中生成并自动回收，不访问用户设备、不联网取题、不读取凭据。GitHub的独立 `AI Original Draft QA` 工作流会上传实际验证报告；原有历史题库QA工作流保持原样。

## 历史草案与版本边界

[命题蓝图](blueprint.md)记录当前定稿前的覆盖方向与变动。原始方向稿可在提交 `259ebef1078e2022bf0dc11353553ba23a9524c1` 的Git历史中查看；不把旧的0/47、8图或11/23/6难度预算当成当前实际质量数据。

知识点ID参照[PR #26](https://github.com/ProfessorZhi/408-question-bank/pull/26)；未经官方全文逐条核准的考纲转录不作为“官方认可原创题”的证据。本次仅更新PR #27草稿区和独立验证工作流，不合并main，不更改历史真题、源PDF、备份或旧受阻PR。未使用Dell、Fleet、RDC或其他个人设备。
