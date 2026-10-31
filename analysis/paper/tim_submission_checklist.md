# 投 IEEE TIM：稿件状态与投稿前清单

> 稿件：`analysis/paper/tim_manuscript.md` → `tim_manuscript.pdf`
> 16 个 A4 单栏页 / 8,220 词 / 4 图 + Fig. S-1 / 8 表 / 22 条文献 / 摘要 246 词
> 补充材料：`analysis/paper/tim_supplement.md` → `tim_supplement.pdf`
> 重建：`bash analysis/_build/make_paper.sh tim_manuscript && bash analysis/_build/make_paper.sh tim_supplement`

## 0. 一句话

**骨架换完了，§5 五步压缩已执行，文献也从 12 条补到 22 条并全部核过 DOI/卷期页。**
剩下的主要是投稿事务：作者信息、ORCID、超页费决策。唯一仍建议在投稿前重算的是
Table IV / Fig. 4(a)：目前 regime map 是 3000 抽样，最好按 8000 抽样重跑并同步正文。

## 1. TIM 硬性项

| 项 | TIM 要求 | 本稿 | 状态 |
|---|---|---|---|
| 摘要 | 单段、≤250 词、无公式、无引用、无缩写 | 246 词、单段、无 `$...$`、无 `[n]` | ✅ |
| Index Terms | 必填，字母序 | 6 条，字母序 | ✅ |
| Nomenclature | 建议（符号多时） | 12 符号双列 | ✅ |
| 正文页数 | 双栏 8 页内免费，超出 $265/页（非 IMS 会员）/ $220（会员） | 单栏 16 页 ≈ 双栏 10–11 页 → 超 2–3 页，约 $530–795 | ⚠️ 待决策 |
| 文献编号 | 按**首次引用**顺序 | 已校验：[1]→[22] 严格按首次出现 | ✅ |
| 文献数量 | 常规 20–30 条 | 22 条，含 LROC 标定、bundle adjustment、alignment Kalman filter、tolerance review、conformity assessment | ✅ |
| 图件 | 单独文件，≥300 dpi | 已按 400 dpi 重导出（`plot_*.py` 已改） | ✅ |
| 作者 ORCID | **每位作者都必须有**，投稿时填 | 占位 | ❌ |
| 首页脚注 | 收稿日期、基金、利益冲突、单位与邮箱 | 已有占位段 | ⚠️ 待填 |
| 文件大小 | ≤20 MB | 正文 2.6 MB + 补充材料 0.3 MB | ✅ |
| 作者简介 | TIM 不刊 | 未写 | ✅ |
| 大修机会 | 只有一次大修，3 周；二次大修自动拒 | — | 提醒 |

## 2. 章节骨架（TIM 惯例 ↔ 本稿）

| TIM 惯例 | 本稿 | 素材来源 |
|---|---|---|
| I. Introduction（A 动机 / B 前人 / C 贡献） | 同；B 现为 4 条：偏差估计 / 可行域几何 / 公差分配 / 判定规则 | 旧 §1 + §2.1–2.3 + 新增标定文献段 |
| II. 模型（含测量不确定度） | II. Measurement Model and Decision Rules，含 **D. Guard Bands** | 旧 §2.4 扩写 |
| III. 理论（命题 + 证明） | III. A–G，四个命题 + 三个推论 | 旧 §4 |
| IV. 实现（复杂度 + 证书） | IV. Making the Decision Exactly | 旧 §4.6 扩写 |
| V. 案例/回放 | V. Replay on a Public Ten-Channel Specification | 旧 §5 |
| VI. 工作特性（定量） | VI. A–E，**A/B 为新增**（单边误差剖面、DC/SP） | 新实验 `outputs_ress/` |
| VII. 为什么记录测不出来 | VII. A–C，**A/B 为新增**（可及域 + 学习速率） | 新实验 |
| VIII. 讨论与局限 | VIII. A 筛查 / B 局限 / C 什么能推翻 | 旧 §8–9 合并 |
| IX. Conclusion | 同 | 旧 §10 |
| Appendix | A 枚举完备性 | 环族闭式已并入 §III-G |
| Acknowledgment | 一句，回应"界 vs 率"的审稿意见 | 新增 |
| Supplementary Material | `tim_supplement.md` / `tim_supplement.pdf` | Fig. S-1（原 Fig. 5） |

**新增的科学内容（相对 Measurement 版）**：
- **§III-F 推论 3**：漏检必然意味着短缺 ≤ 15.47%，且等边族取到——把 13.4% 从"设计侧乐观系数"翻译成"装配侧的保证检测阈值"。这是全文最值钱的一条。
- **§VI-A/B**：两个 0 是定理不是观测（逐台恒不漏、两两恒不叫），配 DC/SP 八格表。这张表同时说明"现场换判据是理性的"——审稿人会认。
- **§VII-A/B**：记录支撑集与错误域在 r\*=A 处相切（Table VI），以及 p=3.3% 需 48 台才能看见一次（Table VIII）。把"没有数据"从修辞变成算术。
- **§II-D**：保护带替换 A→A−w 后所有命题逐字成立——提前挡掉"你没考虑测量不确定度"。

## 3. 还缺什么（按被拒风险排序）

1. **Table IV / Fig. 4(a) 仍是 3000 抽样。** 不是逻辑问题，但投稿前最好用 8000 抽样重跑
   `run_regime_map.py` 并同步表 IV、图 4(a) 与 §VIII-A 的峰值口径。
2. **ORCID 与作者信息。**
3. **超页费**：$530–795 量级；§5 的五步已经执行，若仍要免超页费，只能继续删正文，
   不建议再动 §III-F、§VI-B、§VII-A。
4. **是否披露"源自内部技术报告"**：不是一稿多投（未发表、未投稿），但 cover letter
   里一句话说明来源，比被审稿人问出来好。
5. **文献条目已实检。** 10 条新增文献 + 7 条旧经典文献的卷期页/DOI 已核对；Chase–Parkinson
   页码已修正为 23–37。

## 4. 三个必须再核的论断（沿用旧清单，未变）

1. "文档中唯一的成对求和是 Table 9-3"——只检索了一份 45 页规范。
2. Clause 12.0 说激光测距望远镜装在 HGA 支架上——条款号需对页码。
3. "$3\sigma$ or worst case" 是文档自述的置信约定——需逐字引文。

## 5. 压页措施：已执行

按原"删了不心疼"排序，五步已经完成：Fig. 5 移到 `tim_supplement.md`；Appendix B 并入 §III-G；
§VI-A 的 21 格网格压成两句；§VIII-B 并为三条；Nomenclature 删到 12 个符号。结果是
**正文数字一个没改**，但文献补齐后单栏仍为 16 页，估双栏 10–11 页。

**不要再删的**：§III-F（15.47%）、§VI-B（DC/SP 表）、§VII-A（相切表 Table VI）。
这三处是审稿人唯一无法说"这是老几何"的地方。若坚持免超页费，下一步只能删 Fig. 2/4 或
进一步压缩 §V–§VIII，而不是再动这三处。

## 6. 复现

```
bash analysis/_build/make_paper.sh tim_manuscript     # 本稿
bash analysis/_build/make_paper.sh tim_supplement     # 补充材料（Fig. S-1）
bash analysis/_build/make_paper.sh                    # Measurement 版（旧稿）
PYTHONPATH=src python run_ress.py && python plot_ress.py   # 图 3 与 Fig. S-1 的数据
PYTHONPATH=src python run_regime_map.py && python plot_regime.py  # 图 4 的数据；投稿前建议改 8000 抽样
```

图号表号已按出现顺序固定（正文 Fig. 1–4、TABLE I–VIII；补充材料 Fig. S-1）。
**改稿时插新表要整体重排**，或在正文用 "Table IX" 之后另起，不要插在中间。
