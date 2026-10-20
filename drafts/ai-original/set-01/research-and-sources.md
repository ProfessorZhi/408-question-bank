# 研究参考与规则来源

## SciSpace检索的命题质量研究

本轮通过SciSpace检索“计算机教育中的生成式选择题、干扰项和难度标定”，随后核对原始论文页面。研究只用于制定检查方法，**不为本试卷背书，也没有参与签核本卷答案**。

1. Zengaffinen et al., *Can LLMs Model Incorrect Student Reasoning? A Case Study on Distractor Generation* (2026), [arXiv:2603.15547](https://arxiv.org/abs/2603.15547)。作者分析先恢复正确解、模拟学生误解、再选择干扰项的过程及其失效点。本卷对应做法是逐题解释三个错误选项的具体错因，先核对正确结果再设计干扰值。这是方法上的采用，不保证干扰项实测有效。
2. Brant, Kühn & Pang, *Estimating Exam Item Difficulty with LLMs: A Benchmark on Brazil's ENEM Corpus* (2026), [arXiv:2602.06631](https://arxiv.org/abs/2602.06631)。以官方测量参数比较模型难度估计，并报告校准和多模态评估限制。本卷因此保留“未经过考生试做、未获IRT或区分度数据”的状态，不把模型预估当作考试难度实测。两条均按预印本来源引用，不一概称为已同行评议定论。

## 协议和操作系统语义

- [RFC 9293：TCP](https://www.rfc-editor.org/rfc/rfc9293.html)，序号、连接与累计确认语义用于Q38。Q47 v3已改为网络层路由更新题，不再是TCP题。Q39明确使用题定的教学分轮模型，而非宣称真实TCP总按逐RTT批量发送。
- [RFC 5681：TCP拥塞控制](https://www.rfc-editor.org/rfc/rfc5681.html)，仅作慢启动/拥塞避免术语参照；不从旧教材默认值推断当前所有实现的初始窗口。
- [The Open Group：open](https://pubs.opengroup.org/onlinepubs/9799919799/functions/open.html) 和 [lseek](https://pubs.opengroup.org/onlinepubs/9799919799/functions/lseek.html)，用于区分文件描述符、打开文件对象和文件偏移。Q24明确给定POSIX式模型，不要求适用于所有操作系统。
- [RFC 791：Internet Protocol](https://www.rfc-editor.org/rfc/rfc791.html)：Q47涉及IPv4 TTL逐路由器递减的语义；题干将减1后为0即丢弃作为明确约定。
- [IETF RFC 5715 §6.7](https://datatracker.ietf.org/doc/html/rfc5715#section-6.7)与[RFC 6976 §2.1.1](https://datatracker.ietf.org/doc/html/rfc6976#section-2.1.1)：**已在公开标准中提出费用增大后的有序FIB更新及微环路避免**，属于Q47的既有原理，不是本卷首创；考生无需预先知道这些术语。
- [MIT xv6 教材 §5（Page faults）](https://mit-pdos.github.io/xv6-riscv-book/pgfault.html)：明确记载COW写异常、页表引用计数和单引用页不必复制的优化，为Q46机制的教科书先例。

## 考试资料边界

2024与2025的既有题面只用于结构、能力和知识范围比较；[知识图谱PR #26](https://github.com/ProfessorZhi/408-question-bank/pull/26)中的稳定ID用于标签。没有复制王道教材正文、原题配图、商业题库答案或未授权的考纲PDF。通用算法/定义与现有训练题可能相似；**未做全网逐题原创唯一性审查**，不能声称这47题的所有机制都前所未有。

本卷的教学ISA、流水线和Q46写时复制、Q47转发表更新约定以题干为准；这些是特意声明的模型，不冒充某现实CPU或操作系统的完整规范。
