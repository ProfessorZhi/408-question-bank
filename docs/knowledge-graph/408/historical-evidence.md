# 408 历年真题考查证据与主题趋势

**统计基线：** 2009—2025（17 卷 × 47 = 799 题），以仓库 `papers/exams/<year>/questions.md` 为当前研究样本。题面来源自身存在 OCR 与图表需复核状态。2026 为额外资料，2027 模拟卷不计入历史考频。

## 统计口径与可信度

- 全部 799 题均生成题号/题面行号链接。119 道综合题经阅读现存题干做主主题标注（`stem-reviewed`）；只核对题文主题，不承诺答案正确。
- 680 道选择题中有 505 道关键词**候选匹配**（`keyword-candidate`），175 道只有位置推定的学科（`subject-range-only`）。这些均**不应被当成经过人工核对的知识点频次**。
- 一个综合题常跨多个科目和知识点；下表只按**主知识点**每题计一次。分值、年份频率不可由此直接推导。
- 不能用“未被自动识别”的节点断言“历年从未考过”，不能把 17 年粗计数直接外推为下一年概率。

## 分章节证据表

| 学科 | 章节 | 综合题主主题（人工阅读题干） | 选择题关键词候选（未审） | 综合题示例 |
|---|---|---:|---:|---|
| 数据结构 | `DS01` 基础概念与算法 | 4 | 8 | [2013Q41](../../../papers/exams/2013/questions.md#L513)、[2018Q41](../../../papers/exams/2018/questions.md#L511)、[2020Q41](../../../papers/exams/2020/questions.md#L526) |
| 数据结构 | `DS02` 线性表 | 5 | 6 | [2009Q42](../../../papers/exams/2009/questions.md#L468)、[2010Q42](../../../papers/exams/2010/questions.md#L522)、[2012Q42](../../../papers/exams/2012/questions.md#L545) |
| 数据结构 | `DS03` 栈队列与数组 | 1 | 15 | [2019Q42](../../../papers/exams/2019/questions.md#L542) |
| 数据结构 | `DS04` 树与二叉树 | 6 | 39 | [2012Q41](../../../papers/exams/2012/questions.md#L535)、[2014Q41](../../../papers/exams/2014/questions.md#L476)、[2016Q42](../../../papers/exams/2016/questions.md#L579) |
| 数据结构 | `DS05` 图 | 9 | 29 | [2009Q41](../../../papers/exams/2009/questions.md#L461)、[2011Q41](../../../papers/exams/2011/questions.md#L500)、[2015Q42](../../../papers/exams/2015/questions.md#L512) |
| 数据结构 | `DS06` 查找 | 4 | 32 | [2010Q41](../../../papers/exams/2010/questions.md#L511)、[2011Q42](../../../papers/exams/2011/questions.md#L517)、[2013Q42](../../../papers/exams/2013/questions.md#L525) |
| 数据结构 | `DS07` 排序 | 4 | 21 | [2016Q43](../../../papers/exams/2016/questions.md#L589)、[2021Q42](../../../papers/exams/2021/questions.md#L520)、[2022Q42](../../../papers/exams/2022/questions.md#L550) |
| 计算机组成原理 | `CO01` 计算机系统与性能 | 1 | 5 | [2012Q43](../../../papers/exams/2012/questions.md#L562) |
| 计算机组成原理 | `CO02` 数据表示和运算 | 4 | 27 | [2011Q43](../../../papers/exams/2011/questions.md#L529)、[2017Q43](../../../papers/exams/2017/questions.md#L575)、[2020Q43](../../../papers/exams/2020/questions.md#L550) |
| 计算机组成原理 | `CO03` 存储系统 | 12 | 35 | [2010Q44](../../../papers/exams/2010/questions.md#L568)、[2011Q44](../../../papers/exams/2011/questions.md#L556)、[2013Q43](../../../papers/exams/2013/questions.md#L535) |
| 计算机组成原理 | `CO04` 指令系统与机器级程序 | 9 | 25 | [2010Q43](../../../papers/exams/2010/questions.md#L535)、[2013Q44](../../../papers/exams/2013/questions.md#L549)、[2014Q44](../../../papers/exams/2014/questions.md#L536) |
| 计算机组成原理 | `CO05` CPU与流水线 | 5 | 38 | [2009Q44](../../../papers/exams/2009/questions.md#L495)、[2012Q44](../../../papers/exams/2012/questions.md#L576)、[2015Q43](../../../papers/exams/2015/questions.md#L529) |
| 计算机组成原理 | `CO06` 总线与输入输出 | 3 | 17 | [2009Q43](../../../papers/exams/2009/questions.md#L484)、[2016Q44](../../../papers/exams/2016/questions.md#L601)、[2018Q43](../../../papers/exams/2018/questions.md#L540) |
| 操作系统 | `OS01` 系统基础与运行环境 | 3 | 14 | [2021Q46](../../../papers/exams/2021/questions.md#L618)、[2023Q46](../../../papers/exams/2023/questions.md#L637)、[2025Q46](../../../papers/exams/2025/questions.md#L593) |
| 操作系统 | `OS02` 进程线程和并发 | 14 | 37 | [2009Q45](../../../papers/exams/2009/questions.md#L510)、[2011Q45](../../../papers/exams/2011/questions.md#L592)、[2013Q45](../../../papers/exams/2013/questions.md#L578) |
| 操作系统 | `OS03` 内存与虚拟存储 | 9 | 25 | [2009Q46](../../../papers/exams/2009/questions.md#L517)、[2010Q46](../../../papers/exams/2010/questions.md#L627)、[2012Q45](../../../papers/exams/2012/questions.md#L620) |
| 操作系统 | `OS04` 文件系统 | 6 | 19 | [2011Q46](../../../papers/exams/2011/questions.md#L620)、[2012Q46](../../../papers/exams/2012/questions.md#L634)、[2014Q46](../../../papers/exams/2014/questions.md#L579) |
| 操作系统 | `OS05` 设备和外存IO | 2 | 9 | [2010Q45](../../../papers/exams/2010/questions.md#L611)、[2019Q44](../../../papers/exams/2019/questions.md#L562) |
| 计算机网络 | `CN01` 网络概述 | 0 | 12 | — |
| 计算机网络 | `CN02` 物理层 | 1 | 7 | [2025Q47](../../../papers/exams/2025/questions.md#L625) |
| 计算机网络 | `CN03` 数据链路层 | 3 | 25 | [2010Q47](../../../papers/exams/2010/questions.md#L652)、[2017Q47](../../../papers/exams/2017/questions.md#L674)、[2022Q47](../../../papers/exams/2022/questions.md#L619) |
| 计算机网络 | `CN04` 网络层 | 11 | 26 | [2009Q47](../../../papers/exams/2009/questions.md#L529)、[2011Q47](../../../papers/exams/2011/questions.md#L630)、[2013Q47](../../../papers/exams/2013/questions.md#L624) |
| 计算机网络 | `CN05` 传输层 | 3 | 25 | [2012Q47](../../../papers/exams/2012/questions.md#L644)、[2016Q41](../../../papers/exams/2016/questions.md#L565)、[2023Q47](../../../papers/exams/2023/questions.md#L651) |
| 计算机网络 | `CN06` 应用层 | 0 | 9 | — |

## 从历年实际题面观察到的命题机制

### 1. 数据结构重视“从约束到算法”的设计

可用例题：[2009 Q42 单链表倒数第 k 项](../../../papers/exams/2009/questions.md#L468)；[2018 Q41 数组最小未出现正数](../../../papers/exams/2018/questions.md#L511)；[2023 Q41 有向图入出度算法](../../../papers/exams/2023/questions.md#L512)；[2025 Q41 数组乘积极值算法](../../../papers/exams/2025/questions.md#L503)。题目将数据结构的实际表示、最坏/平均复杂度及空间限制放在同一要求中；原创题不应只替换数据规模。

### 2. 树、图、查找、排序在综合题中多路线轮换

可用例题：[2017 Q42 最小生成树唯一性](../../../papers/exams/2017/questions.md#L560)、[2020 Q42 前缀编码](../../../papers/exams/2020/questions.md#L538)、[2024 Q41 拓扑序列唯一性](../../../papers/exams/2024/questions.md#L483)、[2025 Q42 AOE 网](../../../papers/exams/2025/questions.md#L517)。同一章节也可考性质证明、构造反例、手工模拟与程序设计。

### 3. 组成原理突出软硬件联合解释

可用例题：[2017 Q43 C 整数/浮点](../../../papers/exams/2017/questions.md#L575) → [Q44 机器代码](../../../papers/exams/2017/questions.md#L604)；[2023 Q43 Cache 与数组](../../../papers/exams/2023/questions.md#L547) → [Q44 对应机器指令](../../../papers/exams/2023/questions.md#L574)；[2025 Q43 Cache/TLB](../../../papers/exams/2025/questions.md#L536) → [Q44 补码除法与机器码](../../../papers/exams/2025/questions.md#L560)。优秀原创题应保证 C 行为、二进制位段和访问时间相互自洽。

### 4. OS 的同步互斥与虚拟存储有持续综合命题价值

可用例题：[2009 Q45 生产消费同步](../../../papers/exams/2009/questions.md#L510)、[2015 Q45 信箱与信号量](../../../papers/exams/2015/questions.md#L583)、[2024 Q46 互斥与协作](../../../papers/exams/2024/questions.md#L588)、[2018 Q45 二级页表/进程切换](../../../papers/exams/2018/questions.md#L571)。不能仅根据“出现过 P/V”就声称重复命题；实际资源约束不同。

### 5. 网络综合题善于把多层协议放入一个完整场景

可用例题：[2017 Q47 GBN 传输过程](../../../papers/exams/2017/questions.md#L674)、[2021 Q47 ARP/交换表/DNS/Web](../../../papers/exams/2021/questions.md#L630)、[2023 Q47 FTP + TCP](../../../papers/exams/2023/questions.md#L651)、[2024 Q47 自治系统路由](../../../papers/exams/2024/questions.md#L600)。推荐新题同时提供必要的拓扑、时序与数据边界，避免要求学生自行补全协议状态。

## 暂不作出的结论

- 不排名“历年 408 真题全部知识点的精确考频”：题目可多标签，选择题分类还未审，且 OCR 存在污染。
- 不预测下一年必考点、不过度拟合 17 年数据；覆盖新考纲内容时，应优先以考纲范围为底线。
- 不复制现有王道题目或真题表述来凑创新题。知识图谱用于识别思维机制、原创题的条件约束和审题机制。

## 后续提高统计可信度的方式

1. 逐道审核 `exam-links.csv` 中 505 个候选标签与 175 个学科定位项，并允许多标签（主、次）；只修改人工实际确认的记录。
2. 对复合题增加 `prerequisite`、`application`、`trap` 三类边，再统计按题目和按知识点计数的不同口径。
3. 在校准后的数据上做“年 × 科目 × 章节 × 题型 × 认知层次”交叉统计，再讨论高频与低覆盖。
