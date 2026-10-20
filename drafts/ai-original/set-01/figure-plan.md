# Set 01 · 已完成题图清单

由原先8图规划扩展为**14张学生图+1张教师解析图**。所有文件均已创建，数据源为 `specs/exam.json`，渲染器为 `render_figures.py`；不是装饰性生图。英文短标签用于避免字体依赖，中文图意在题面的替代文本与条件中给出。

| 题号 | SVG | 关键数据 |
|---|---|---|
| Q05 | [BFS树](assets/q05-bfs.svg) | 树边/非树边、源点与连通性 |
| Q06 | [带权图](assets/q06-mst.svg) | 七条边、各边权值及桥DE |
| Q07 | [红黑树](assets/q07-rbtree.svg) | 已知B/R、未知颜色及黑色NIL约定 |
| Q08 | [B+树](assets/q08-bplus.svg) | 根分隔值、叶页内容及右向叶链 |
| Q19 | [流水线](assets/q19-pipeline.svg) | 五级与两条前递路径 |
| Q35 | [交换机](assets/q35-switches.svg) | S1/S2端口与四个主机 |
| Q36 | [SR时序](assets/q36-sr.svg) | 模8序号、原F6与重传ACK6丢失 |
| Q38 | [TCP时序](assets/q38-tcp.svg) | 乱序到达、段首字节和采样时刻T |
| Q41 | [两条链表](assets/q41-lists.svg) | 重复值、链指针、NULL |
| Q42 | [初始AVL](assets/q42-avl.svg) | 初始六个结点的左右孩子 |
| Q43 | [教学处理器M](assets/q43-machine.svg) | 阶段延迟、前递、分支EX判定 |
| Q45 | [同步缓冲](assets/q45-buffer.svg) | 单槽版本k须分别交付A/B；图不泄漏通知与确认方案 |
| Q46 | [COW共享页框](assets/q46-cow.svg) | 父子进程三对只读虚页到F2/F5/F8的共享关系及初始引用 |

| Q47 | [路由费用更新图](assets/q47-network.svg) | R1—R2—R3—R4及R1—R4额外链路；链路费用1→9但不断连，不直接泄漏安全更新顺序 |
| 仅教师Q42 | [两步AVL结果](assets/q42-answer.svg) | 插入15和删除50后的解答树 |

## 核验

```bash
python drafts/ai-original/set-01/render_figures.py --check
```

`--check`只读比较当前SVG与重生成结果，不写文件。无参数运行会重新生成该目录下15张SVG，应与spec一起审查再提交。SVG元数据含整个spec的SHA256，用以发现新旧题图混用。

源规格本身含答案键，不能把它嵌入学生作答网页。Q44共用M的模型，但仅需题定的指令编码表和字节表，无需重复插同一机器图。其他题只用文字、代码或表格，避免图片数量成为无意义指标。

作者已目视检查；独立审图与真实纸面试读仍待进行。图的可重现性不是学术正确性的充分条件。
