# Submission checklist

状态：正文与图已定稿（12 页），以下为投稿前必须补齐或核实的项。
按“会直接被拒/会被审稿人抓”排序。

## A. 必须核实（我按记忆写的卷期页，未逐条查原文）

| # | 条目 | 需核实的内容 |
|---|---|---|
| 1 | Jung 1901, *J. reine angew. Math.* **123**, 241–257 | 卷号与起止页；标题拼写 "Ueber die kleinste Kugel…" 为当时正字法，勿改成 Über |
| 2 | Helly 1923, *Jber. DMV* **32**, 175–176 | 常被误记为 1913（那是讲座），核实 1923 与页码 |
| 3 | Welzl 1991, LNCS **555**, 359–370 | 页码与会议名 *New Results and New Trends in Computer Science* |
| 4 | Clarkson 1995, *JACM* **42**(2), 488–499 | 卷期页 |
| 10 | JCGM 106:2012 | 标题全称与发布年；确认引用的是判定规则/风险框架那一节 |
| 11 | Dodge & Romig 1929, *BSTJ* **8**(4), 613–631 | 卷期页；标题 "A method of sampling inspection" |
| 12 | Megiddo 1983, *SIAM J. Comput.* **12**(4), 759–776 | 卷期页 |

未列入的 [5]–[9] 是教材与标准，出版社/年份风险低，但仍应核对版次
（Rockafellar 1970、Nesterov–Nemirovski 1994、ASME Y14.5-2018、ISO 1101:2017、
LRO 431-SPEC-000113 Rev A 2007-04-06）。

## B. 期刊要求的附件（Elsevier / IEEE 各有硬性项）

- [ ] Highlights：3–5 条，每条 ≤85 字符（Measurement / Elsevier 强制）
- [ ] 作者姓名、单位、通讯作者、ORCID
- [ ] 利益冲突声明、资金声明、CRediT 贡献声明
- [ ] AI 使用声明（Elsevier 现行政策要求单独一节）
- [ ] 图件单独提交：`paper_fig1.png`、`p3_replay.png`、`paper_fig3.png`，400 dpi，宽 ≥1600 px
- [ ] 补充材料清单（代码与 outputs，按 §Data and code availability 的路径打包）
- [ ] 推荐审稿人 3–5 名（几何/公差分析、光机装调、计量判定规则三个方向各一）

## C. 投稿前应再确认的三个论断

1. **"文档中唯一的成对求和是 Table 9-3"**——只用了一份 45 页规范的文本检索，
   若审稿人熟悉该文档并能指出第二处，这条要改。措辞已留余地（"the replay found
   exactly one pairwise sum in the replayed document"），核实后仍建议保持这个限定。
2. **"§12.0 说激光测距望远镜装在 HGA 支架上"**——条款号需再对一次页码。
3. **"$3\sigma$ or worst case" 是文档自述的置信约定**——引文需逐字核对并给页码。

## D. 不做的事

- 不补"某型号因此出过事"的叙述：没有证据，写进去就是硬伤。
- 不把 13.4% / 15.5% / 3.3% 混用：三者的分母分别是判据允许跨度、分配值、设计盒。
  正文每处都带了分母，改稿时不要为了句子短而删。
