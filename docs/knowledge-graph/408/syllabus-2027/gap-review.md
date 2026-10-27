# 2027 范围对照：现有 217 节点的细化缺口与王道延伸边界

这个清单只是**建议新标签和拆分方向**，没有改动已被799道题、115条关系引用的 `concepts.json` 稳定 ID。`outline-explicit-finer-granularity` 表示公开大纲转录有此条目但217节点尚未单列；不是官方文献本身已经逐字校对。

| 目标章节 | 候选细分/扩展点 | 证据等级 | 原因 |
|---|---|---|---|
| DS02 | 静态链表的结构与操作 | book-extension | 官方要求链式存储；静态链表作为一种实现不单独列在公开转录栏目。 |
| DS07 | 计数排序的完整算法 | book-extension | 官方排序项目列举不单列计数排序；可用于理解但不应强制覆盖。 |
| DS05 | 有向无环图表达式表示 | book-extension | 教材列出，但官方图基本应用只单列最小生成树/最短路径/拓扑/关键路径。 |
| CO03 | 段式和段页式虚拟存储转换机制 | outline-explicit-finer-granularity | 已有CO03.10偏重页表，应拆分段地址与段页式关系，范围为考纲栏目所列。 |
| CO05 | SMP共享内存多处理器与向量处理器 | outline-explicit-finer-granularity | 已有CO05.10将SISD、SIMD、多核、多线程折在一起，宜独立细分。 |
| OS01 | 宏内核、微内核与外核 | outline-explicit-finer-granularity | 外核是列出的结构名称，现有OS01.06标签不显式；宜单设一个可查询概念。 |
| OS02 | 条件变量及其与互斥锁协作 | outline-explicit-finer-granularity | 现有OS02.07的标题只写PV，需补独立的条件变量节点，不能漏学。 |
| OS02 | 消息传递、共享内存、管道与信号 | outline-explicit-finer-granularity | 已有OS02.11合并IPC和管道，不足以区分消息传递与信号。 |
| OS03 | 请求分页性能改进、写时复制 | mixed-editorial-detail | 请求分页性能是范围，写时复制只是辅助解释，不应作为独立官方必考。 |
| OS05 | 阻塞与非阻塞I/O及设备接口分类 | outline-explicit-finer-granularity | 现有OS05.01只有IO管理软件层次，需把接口行为细分。 |
| OS05 | 磁盘逻辑格式化、分区、引导管理 | outline-explicit-finer-granularity | 现有OS05.04较偏物理寻址，磁盘管理应单列训练目标。 |
| CN01 | 数据报与虚电路的服务模型 | outline-explicit-finer-granularity | 现有CN01.05只写电路/分组交换，尚无数据报/虚电路标签。 |
| CN02 | 物理层接口机械、电气和功能特性 | outline-explicit-finer-granularity | 现有CN02.05宽泛描述传输介质特性，应独立标注接口特性。 |
| CN03 | 频分、时分、波分及码分多路复用 | outline-explicit-finer-granularity | 现有CN03.07将多路访问概括成ALOHA/CSMA，缺正交复用。 |
| CN03 | 令牌传递与轮询访问协议 | outline-explicit-finer-granularity | 现有CN03.07尚未表示令牌传递；与随机接入应分开。 |
| CN06 | 邮件格式及MIME基本功能 | outline-explicit-finer-granularity | 已有CN06.04/05只强调SMTP/POP3，须补电子邮件格式及MIME。 |
| CN04 | IGMP细节和多播路由协议 | book-extension | 公开考纲细目写IP组播概念和地址，IGMP详细协议属于王道扩展，不应作为必考独立条目。 |
| CN04 | IPv4到IPv6的过渡机制 | book-extension | 公开考纲只列IPv6主要特点和地址，教材过渡机制可作为补充但不直接加权。 |

下一次修订知识图谱应先审查这些建议，再决定是否增补叶节点或仅加细分说明；不能把 `book-extension` 自动标为官方强制考试范围。

