# Measurement 投稿操作指南

投稿入口：<https://www.editorialmanager.com/meas/>

本目录下的文件已经按 Editorial Manager（EM）的「Item Type」命名，上传时对着下表选即可。

---

## 0. 文件对照表

| EM 里的 Item Type | 上传哪个文件 | 说明 |
|---|---|---|
| Manuscript | `Manuscript_anonymized.pdf` | 14 页，无作者信息，供双盲评审 |
| Title Page | `Title_page.pdf` | 1 页，含作者、单位、通讯方式、全部声明；如需可编辑版传 `Title_page.docx` |
| Cover Letter | `Cover_letter.pdf` | 1 页，已按 Measurement 口径重写 |
| Highlights | `Highlights.docx` | 5 条，每条 ≤85 字符（另附 `Highlights.txt` 备用） |
| Declaration of Interest Statement | `Declaration_of_Interest.docx` | 可编辑；无利益冲突声明 + 署名 + 日期 |
| Acknowledgments | `Acknowledgments.docx` | **必须是可编辑格式**，EM 该项明确要求；含基金号与致谢 |
| Figure | `figures/Figure_1.png`<br>`figures/Figure_2.png`<br>`figures/Figure_3.png` | 各 400 dpi，顺序 1/2/3 |
| Supplementary Material | `Supplementary_material.zip` | 代码 + 数据 + 派生结果，已验证可复现 |

正文里的三张图是内嵌的，单独图件是给生产环节用的，两套都要传。

`Abstract.txt` 和 `Highlights.txt` 是纯文本，用于粘贴到 EM 的文本框——EM 的摘要框不解析 LaTeX，直接把 Markdown 里的 `$\sqrt{3}A$` 粘进去会显示成乱码。

---

## 1. 已确认的两项（2026-11-03）

**① ORCID**：`0000-0003-1255-6332`，已写入 `submission_meta.json`，标题页与投稿信均已带上。

**② 生成式 AI 使用声明**（标题页最后一段），已按你的口径改为：

> During the preparation of this work the author used a large language model assistant to
> write code and to polish the language of the manuscript. The author reviewed and edited all
> content, verified every numerical result against the supplied code and data, and takes full
> responsibility for the content of the publication.

即：AI 只用于**编写代码**和**语言润色**，不涉及研究构思与论证。

---

## 2. EM 逐步操作

1. **登录** → 角色选 Author → 点 **Submit New Manuscript**。
2. **Choose Article Type** → 选 *Research paper*（若下拉里是 *Full Length Article*，选它）。
3. **Enter Title** → 粘贴完整标题（`Title_page.md` 第一段，冒号前后都要）：
   *A decision rule without an operating characteristic: the pairwise sum in conformance assessment of multi-channel boresight alignment*
4. **Add/Edit/Remove Authors** → 只加一个人：
   - Given name `Zhengkang`，Family name `Zuo`
   - E-mail `zuozhengkang@tyut.edu.cn`
   - ORCID `0000-0003-1255-6332`
   - Affiliation：`Polar-vision Laboratory, College of Geoscience and Surveying Engineering, Taiyuan University of Technology, Taiyuan 030024, Shanxi, China`
   - 勾选 **This is the corresponding author**
5. **Enter Keywords** → 逐个粘 8 个（EM 一般允许 6–10 个）：
   conformity assessment / decision rule / measurement uncertainty / boresight alignment /
   tolerance allocation / operating characteristic / minimal enclosing circle / guard band
6. **Classifications**（若出现该步）→ 勾选 **190 Measurement science**、**330 Mathematical tools for measurement**、**260 Measurement of geometrical quantities**。
7. **Enter Abstract** → 打开 `Abstract.txt` 整段粘贴。
8. **Upload Files** → 按第 0 节的对照表逐个上传，Item Type 别选错。图件三个要分别传、Order 填 1/2/3。
9. **Declarations**（各刊措辞不同，通常问三项）：
   - Competing interests → **No**
   - Funding → 有，粘贴 `Title_page.md` 里的 Funding 一段
   - Data availability → 选 *Available as supplementary material*，或直接粘贴同一段文字
10. **Suggested Reviewers**（可跳过）→ 若要填，见 `submission_meta.json` 里三个候选人；
    **邮箱必须先去其单位主页核实**，不要用猜的地址。
11. **Build PDF** → EM 会生成合并稿，务必打开检查：
    - 三张图是否都在、有没有被压成模糊
    - 参考文献是否到 [20]
    - 有没有把 Title Page 混进正文（混进去就破坏了匿名）
12. **Approve Submission** → 提交。

---

## 3. 几个容易踩的点

- **匿名**：正文 PDF 里没有姓名、单位、基金号、致谢，符合双盲要求。若 Measurement 走单盲，
  这样投也不违规——作者信息在 EM 里对编辑可见，只是审稿人看不到。
- **图不要只传 Word/PDF 里的内嵌版**：生产环节要单独的高分辨率图件，缺了会被退回补件。
- **Highlights 是硬性项**：EM 里既可能要文本，也可能要文件，两个都备好了。
- **不要提 TIM 拒稿**：那是 scope 不符的技术性退稿，与新投稿的学术判断无关，
  在 cover letter 里提只会引入无关信息。已在别处投过但未发表的稿件，不构成重复投稿。

---

## 4. 提交前 60 秒自检

- [ ] 标题与 `Title_page` 完全一致（含破折号后的副标题）
- [ ] 作者只有 Zhengkang Zuo，且已标为通讯作者
- [ ] 摘要栏里没有残留的 `$`、`\`、反引号
- [ ] 三张图都上传了，Order 是 1/2/3
- [ ] Supplementary 传了（审稿人复现时唯一能拿到的东西）
- [ ] 合并 PDF 里没有出现作者姓名
- [ ] Highlights 每条都没超过 85 字符（已自动校验：82/81/77/82/84）

---

## 5. 如果被退回补件，最可能是这三个

1. **要可编辑源文件**（.docx / .tex）。目前只有 Markdown 和 PDF。若被要求，我可以把
   Markdown 转成 Word 再交。
2. **图件格式**。Elsevier 偏好 EPS/PDF/TIFF，PNG 在 400 dpi 下通常可接受；若被要求换格式，
   用 `analysis/figures/` 里的脚本重出 TIFF 即可。
3. **摘要偏长**。现为 352 词。Measurement 对研究论文没有硬性上限，但若编辑要求压到 250 词，
   砍掉第二段的重复表述即可，不影响论证。
