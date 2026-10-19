# 408 知识图谱资料依据与版权边界

更新：2026-10-20。**本知识图谱不是官方考纲原文，也不是王道教材逐章全文搬运。** 本仓库只整理原创概念标签、知识关系以及本仓库已经持有的真题题号索引。

## 一、范围与分值依据

1. [2026 年 408 大纲公开整理（新东方）](https://kaoyan.xdf.cn/202511/15003718.html)：为本项目当前知识范围基线提供四科章节、考查方向和常见试卷结构参考。**性质：辅导机构转载整理，不是教育部考试院原件；最终以当年正式考纲为准。**
2. [2027 年 408 大纲第三方整理](https://zhenti.beokayy.club/outline)：用于关注下一版变动的线索。站点自述与 2026 相比没有变动，但**本项目没有独立核验官方 2027 原件**，因此当前 `concepts.json` 仍标记 `syllabus_reference_year=2026`。
3. [CC408 四科导学](https://cc408.cn/app/guide)：交叉核对四科分值、考试时间与题型的常规口径；不是统计分析原始数据。

## 二、王道及其他教辅目录的交叉参照

- [王道 2027 操作系统目录示例（第三方整理）](https://jlshdsdk.github.io/kaoyan-408-os/index.html)：参照“系统概述、进程与线程、内存、文件、I/O”组织层次，**未复制正文、配套原图或解析**。
- [第三方 2027 王道四科结构化项目](https://github.com/dengduanglang/408-knowledge)：证明“四科教材 + 考纲”可以形成结构化标签；其项目明确声明不应随公开仓库发布教材 PDF 或受保护的内容。只参考组织思路。
- [按 2026 考纲整理的开源 408 知识库](https://github.com/zhaoyang51/cs408-notes)：用于比较 24 章一级目录组织；该项目的题库数量/章节数**不作为本仓库真题统计**。
- [王道相关学习资源导航（非官方）](https://github.com/dreamer-wei/408)：只作延伸来源入口，未引用或复制其教材 PDF、题目及插图。

## 三、SciSpace 学术研究（方法参考，不当作考纲来源）

- Chen et al. (2018), **KnowEdu: A System to Construct Knowledge Graph for Education**, *IEEE Access*, DOI [10.1109/ACCESS.2018.2839607](https://doi.org/10.1109/ACCESS.2018.2839607)。启示：从教学概念和测评记录构造实体与教育关系，需验证实体识别和关系抽取。
- Manrique, Pereira & Marino (2019), **Exploring knowledge graphs for the identification of concept prerequisites**, *Smart Learning Environments*, DOI [10.1186/s40561-019-0104-3](https://doi.org/10.1186/s40561-019-0104-3)。启示：候选前置关系不能仅由相似词推出，应通过教学逻辑和人工黄金标准检查。
- 以上论文经 SciSpace 检索用于方法设计；我们没有使用这些论文生成“408 的考频”，也没有把其他领域论文中的预测精度当成本项目精度。

## 四、最重要的原始证据：本仓库既有真题

- [2009–2025 试题 Markdown](../../../papers/exams)：17 卷 799 题，是 `exam-links.csv` 的唯一题目级数据源。每条记录包含年份、题号、当前仓库内的起始行及标注方法。
- [源 PDF 目录](../../../sources/exams)：用于以后将候选标签与 PDF 页图对照。此轮**没有**重新逐页阅读全部 17 年 PDF。
- `needs-review` 的 OCR 错误和题图误挂可能影响关键词；本轮对题目的分类置信度按 `stem-reviewed`、`keyword-candidate`、`subject-range-only` 分层。

## 五、不得产生的推断

- 不能声称所有知识点均为 2027 官方考纲逐条认证。
- 不能声称 505 道自动匹配选择题已完成人工审核，亦不能据它们做精确考频或难度预测。
- 不能重制、拷贝王道原创插图、教学思维导图、答案解析或教材正文；原创 AI 命题插图必须有独立生成和审查记录。
- 本项目公开仓库涉及的历史试卷版权风险继续适用根目录 [`RIGHTS.md`](../../../RIGHTS.md)。
