# EM 填表速查（复制粘贴用）

> 对应 `SUBMISSION_GUIDE.md` 的第 2 节。每个代码块直接整体复制。

## Title

```
A decision rule without an operating characteristic: the pairwise sum in conformance assessment of multi-channel boresight alignment
```

## Author

| 字段 | 内容 |
|---|---|
| Given name | `Zhengkang` |
| Family name | `Zuo` |
| E-mail | `zuozhengkang@tyut.edu.cn` |
| ORCID | `0000-0003-1255-6332` |
| Corresponding author | ✅ 勾选 |

Affiliation（若是一个大文本框）：

```
Polar-vision Laboratory, College of Geoscience and Surveying Engineering, Taiyuan University of Technology, Taiyuan 030024, Shanxi, China
```

## Keywords（逐个粘，一行一个）

```
conformity assessment
decision rule
measurement uncertainty
boresight alignment
tolerance allocation
operating characteristic
minimal enclosing circle
guard band
```

## Abstract

```
In conformity assessment a decision rule maps a measured quantity value to a verdict of conformance or non-conformance, and its adequacy is judged by its operating characteristic — the probability of rejection as a function of the true state of the item — together with the risks of incorrect decision that measurement uncertainty attaches to the verdict. This paper examines a decision rule that is ubiquitous in the alignment of multi-channel payloads yet has never been treated as one. Payloads are budgeted one channel at a time but often checked one pair at a time: every pair of channels must be alignable within the sum of its two allocations. The paper separates what that rule establishes in design from what it establishes in assembly. In design it is optimistic by a constant: with equal allocations A, a common orientation exists whenever the worst pairwise separation does not exceed √3·A, whereas the pairwise sum admits 2·A, so allocations derived from pairwise sums are 15.5% too small, the worst case being attained by three channels in an equilateral configuration. The constant is Jung's, and no new geometry is claimed. In assembly the rule has no operating characteristic at all: a pairwise violation implies that some channel already violates its own allocation, and whenever the per-channel check passes all three rules accept, with a witness at the origin. The rejection probability is therefore identically zero on conforming data, and no build record can discriminate the rules, because a build that would discriminate them has already been dispositioned as non-conforming. Sweeps over channel count, allocation-to-spread ratio and allocation heterogeneity bound the disagreement at a few percent of the design box, and at zero under a 3σ convention; across 32 sweep cells and 4729 conforming draws the rejection probability measured zero. A replay on a public ten-channel specification (NASA LRO 431-SPEC-000113 Rev A) reproduces its single pairwise addition to the arc-second, returns one clause undecided with a 1519-arc-second spread between two readings of the same sentence, recovers the document's mechanical partitioning from ten numbers alone, and locates the silent regime that three table-only questions predict in advance.
```

## Highlights（若要求粘贴文本）

```
- A pairwise boresight table cannot reject a build that passes the per-channel check
- On conforming data its rejection probability is identically zero for every n >= 3
- Used to set allocations it is optimistic by Jung's constant, 15.5 % too small
- A replay of NASA LRO 431-SPEC-000113 closes its one pairwise sum to the arc-second
- Three screening questions, answerable from the table alone, bound where this matters
```

## Declarations

**Competing interests** → `No`

**Funding**

```
This work was supported by the National Natural Science Foundation of China (grant no. T2600787) and the Natural Science Foundation of Shanxi Province (grant no. 202403021212106).
```

**Data availability**

```
The allocation table transcribed from the public specification, the solver, the sweep drivers, the derived CSV outputs and the figure scripts are provided as supplementary material with this submission. On acceptance the same package will be deposited in a public repository and the DOI added to the article. The specification itself is a public NASA document and is not redistributed.
```

**Generative AI**

```
During the preparation of this work the author used a large language model assistant to write code and to polish the language of the manuscript. The author reviewed and edited all content, verified every numerical result against the supplied code and data, and takes full responsibility for the content of the publication.
```
