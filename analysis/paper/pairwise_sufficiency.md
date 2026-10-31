# A decision rule without an operating characteristic

**The pairwise sum in multi-channel boresight alignment: a sharp bound, an empty rejection region, and a replay on a public ten-channel specification**

*Manuscript draft · 31 October 2026*

---

## Abstract

Multi-channel payloads are budgeted one channel at a time but often checked one *pair* at a time: every pair of channels must be alignable within the sum of its two allocations. This paper separates what that rule establishes in design from what it establishes in assembly. In design it is optimistic by a constant: with equal allocations $A$, a common orientation exists whenever the worst pairwise separation does not exceed $\sqrt{3}A$, whereas the pairwise sum admits $2A$, so allocations derived from pairwise sums are $15.5\%$ too small, the worst case being attained by three channels in an equilateral configuration. The constant is Jung's, and no new geometry is claimed. In assembly the rule has no operating characteristic at all: a pairwise violation implies that some channel already violates its own allocation, and whenever the per-channel check passes all three rules accept, with a witness at the origin. The rejection probability is therefore identically zero on conforming data, and no build record can discriminate the rules, because a build that would discriminate them has already been dispositioned as non-conforming. Sweeps over channel count, allocation-to-spread ratio and allocation heterogeneity bound the disagreement at a few percent of the design box, and at zero under a $3\sigma$ convention; across 32 sweep cells and 4729 conforming draws the rejection probability measured zero. A replay on a public ten-channel specification (NASA LRO `431-SPEC-000113` Rev A) reproduces its single pairwise addition to the arc-second, returns one clause undecided with a $1519''$ spread between two readings of the same sentence, recovers the document's mechanical partitioning from ten numbers alone, and locates the silent regime that three table-only questions predict in advance.

**Keywords**: boresight alignment; tolerance allocation; decision rule; operating characteristic; spherical caps; minimal enclosing circle; multi-instrument payload

---

## 1. Introduction

A camera, a laser rangefinder, a radar and a star tracker on one spacecraft share a mechanical reference. Each carries an angular allocation — “aligned to the spacecraft reference to within $300$ arc-seconds per axis”, say — set during design and verified during assembly. Both activities are usually organised **pairwise**. In design, the sum of two allocations is required to cover the worst relative misalignment the two channels can accumulate. In assembly, every pair of as-built deviations is required to lie within the sum of the two allocations. The two statements look like the same statement seen from opposite ends, and they are not.

The geometry underneath is elementary and old. Each channel's allocation is a disk on the tangent plane, or a cap on the sphere, and a single common orientation exists exactly when the disks intersect. That pairwise intersection of convex sets does not imply intersection of the family is Helly's theorem, in the plane since 1923 [2]; that a planar set of diameter $d$ fits in a circle of radius $d/\sqrt{3}$ is Jung's theorem, from 1901 [1]. Neither is in question here and this paper claims neither. The contribution is a statement about a *decision rule* built on that geometry, and about what kind of evidence could ever test such a rule.

The distinction that motivates the paper is one that conformance-assessment practice makes explicitly and tolerance analysis usually does not. A decision rule used to declare conformity is characterised by its operating characteristic: the probability of rejection as a function of the true state of the item [10]. Acceptance sampling has been built on that curve since Dodge and Romig [11]. A rule whose operating characteristic is flat — which rejects nothing, or rejects everything, regardless of the state — is not a weak rule but a non-rule, and no amount of field data can validate it. Section 4.1 shows that the pairwise sum, used as a conformity check, is exactly of this kind: its rejection region is contained in the region already rejected by the per-channel check, so on conforming data it is silent by construction rather than by luck.

Three consequences are worked out and measured.

*First*, the two uses of the rule come apart. Used to **set** allocations, the pairwise sum is optimistic by a sharp constant: $2/\sqrt{3}$, Jung's constant, or $15.5\%$ of the allocation in the worst case, attained by three channels in an equilateral configuration (Section 4.3–4.4). Used to **disposition** a build, it is not optimistic and not pessimistic; it is inert, and it becomes informative only after the per-channel check has already failed, at which point the question is rework capacity rather than conformity (Section 4.1).

*Second*, the regime where the rule's optimism is measurable is narrow and can be located from the table alone. Sweeping channel count, allocation-to-spread ratio and allocation heterogeneity, the disagreement peaks at a few percent of the design box, and it collapses when any one of three conditions fails (Section 6). The screening questions of Section 8 follow from those three conditions and require no measurement.

*Third*, a replay on a public document shows what the rule's silence looks like in practice, and what a certificate adds when the document is ambiguous. The specification replayed in Section 5 is careful and internally consistent; it is also, in the one place where it adds two allocations, adding them for exactly two channels, where the addition is exact. That is not luck — Section 4.2 shows it cannot be otherwise, because a sum written in a specification is almost always written for a pair — and it is the mechanism by which the rule's defect stays invisible.

The paper is organised as follows. Section 2 positions the work against alignment budgeting practice, geometric feasibility and conformance-decision theory. Section 3 fixes the model and the three tests. Section 4 states and proves the four propositions. Section 5 replays a public ten-channel specification. Section 6 maps the regime in which the rules disagree and measures how large the disagreement is. Section 7 explains why the field record cannot contain the disagreement, Section 8 turns that explanation into a screen, and Section 9 states what the paper does not show, including the single piece of evidence that would most change its conclusion.

## 2. Background

### 2.1 Alignment budgeting as practised

An angular alignment budget is written twice: once as a requirement on a relative orientation, once as an allocation to each contributor. The contributors are the instrument's own alignment cube, the bracket, the interface, and the reference transfer; the allocation is usually stated as a half-cone per axis at a declared confidence, and the conventions for combining allocations are the classical ones of tolerance analysis — arithmetic (worst case) or statistical root-sum-square. Dimensional and geometrical tolerancing standards [8, 9] fix the language for the mechanical contributors but deliberately do not prescribe how a multi-instrument budget should be combined; that is left to the programme.

In practice the combination is done pairwise, for a reason that is organisational as much as technical: a pairwise requirement is a requirement between two responsible parties, it can be written into two interface control documents, and it can be verified by pointing one instrument at another. A three-way requirement has no natural owner. The result is a table whose rows are pairs, and a review whose question is “is every row inside its sum?”.

That question has a precise answer, and the answer is the subject of this paper.

### 2.2 Feasibility of a family of angular constraints

The mathematical object is the intersection of a family of disks (or spherical caps) in two dimensions, and it is well understood. The smallest enclosing circle is determined by two or three of the points; linear-time algorithms exist [12], as does the randomised incremental construction that most implementations use [3], and the LP-type framework that explains why both work [4]. The intersection of disks is a convex set, so feasibility is a convex feasibility problem and can be written as a second-order cone program [5, 6] — a representation worth having for extensions, but not needed for the pure allocation problem, where enumeration is exact and cheap.

What is not in that literature is the question this paper asks. The literature decides feasibility; it does not ask what a *scalar summary* of a tolerance table can decide, nor when the answer a summary gives can be tested against a build. Those are questions about a decision rule, and they belong to the neighbouring tradition.

### 2.3 Decision rules and their operating characteristics

Conformance assessment formalises the distinction that this paper turns on. A decision rule maps a measured value to accept/reject; its performance is characterised by the probability of acceptance as a function of the true value, and the uncertainty of the measurement is handled by a guard band or by an explicitly stated risk [10]. The framework presupposes that the rule *has* such a curve and that the curve is not degenerate. Acceptance sampling made the same presupposition explicit a century earlier, in the form of the operating-characteristic curve that a sampling plan is chosen to deliver [11].

A rule that is evaluated only on items that have already passed another rule has no operating characteristic of its own: its curve is identically zero on the population it is applied to. This is the situation of the pairwise sum in conformity assessment, and it is not a criticism of the engineers who use it — it is a statement about which question the rule can answer. The remainder of the paper makes the statement precise and then measures the other question, the one the rule can answer but is not usually asked.

## 3. Model

### 3.1 Idealisation

Let $n$ channels share one mounting interface. Channel $i$ has an as-built angular deviation $d_i\in\mathbb{R}^2$ from its nominal direction, expressed in the tangent plane at the common boresight, and an allocation $A_i$ (half-cone, per axis). A single shim of the interface displaces every channel by the same vector $x$, so the residual of channel $i$ is $d_i-x$. The interface is adequate if

$$
\exists\,x\in\mathbb{R}^2:\quad \lVert d_i-x\rVert\le A_i\quad\text{for all } i=1,\dots,n,
\tag{1}
$$

that is, if the disks $D_i=D(d_i,A_i)$ have a common point.

Four idealisations bound what follows, and each is stated where it bites. The tangent-plane replacement of the sphere is accurate to $O(\theta^2)$; the largest allocation in the document replayed in Section 5 is $750''=0.208^\circ$, a relative distortion below $1.4\times10^{-5}$, and a planar solver was cross-checked against an independent spherical-cap solver on 300 random four-channel instances with no disagreement on any. The interface is rigid, isothermal and order-free: thermal gradients, fastener preload and tightening sequence, adhesive cure shrinkage and structural flexibility all move channels relative to one another and none of them appear in (1). The deviations are taken as given, so the question of how they were measured — and with what uncertainty — is outside the model, which is why the paper speaks of feasibility and not of conformity in the metrological sense. And one interface is a counterfactual for the document replayed in Section 5, which aligns each instrument on its own cube; the replay is a validation of the method against the document's arithmetic, not a claim about the flight article.

### 3.2 Three tests

Three tests appear in practice, and their logical relations are not symmetric.

| Test | Condition | Status |
|---|---|---|
| Per-channel | $\lVert d_i\rVert\le A_i$ for all $i$ | sufficient ($x=0$) |
| Pairwise | $\lVert d_i-d_j\rVert\le A_i+A_j$ for all $i\neq j$ | necessary |
| Exact | (1) | necessary and sufficient |

The per-channel test is the assembly gate: it is what an alignment measurement is compared against, channel by channel, and it is the only one of the three that is normally written into an acceptance procedure. The pairwise test is the design rule, and occasionally the rework rule. The exact test is the one nobody runs, because it needs all channels at once and returns a verdict rather than a per-channel number.

## 4. Theory

### 4.1 The pairwise test cannot fire on conforming data

**Proposition 1.** Let $\lVert d_i\rVert\le A_i$ for every $i$. Then $x=0$ satisfies (1), and $\lVert d_i-d_j\rVert\le A_i+A_j$ for every pair. Conversely, if $\lVert d_i-d_j\rVert>A_i+A_j$ for some pair, then at least one of $i,j$ violates its own allocation.

*Proof.* The first part is the triangle inequality, $\lVert d_i-d_j\rVert\le\lVert d_i\rVert+\lVert d_j\rVert\le A_i+A_j$, and $x=0$ gives residual $d_i$. For the converse, if both channels were within allocation the first part would apply. $\square$

Two corollaries carry the weight.

**Corollary 1 (the rejection region is inside the failed region).** Write $C=\{d:\lVert d_i\rVert\le A_i\ \forall i\}$ for the conforming set. Proposition 1 gives $\{d:\exists i,j,\ \lVert d_i-d_j\rVert>A_i+A_j\}\subset\mathbb{R}^{2n}\setminus C$. The exact test's rejection region is inside the same complement, since $d\in C$ implies $x=0$ is feasible. Hence **all three tests accept every conforming configuration**, and the pairwise and exact tests can differ only on data that the per-channel check has already rejected.

**Corollary 2 (no operating characteristic).** If a population of builds is supported on $C$ — which is what “the assembly passed its alignment check” means — then the pairwise test's rejection probability is zero, identically in $A$, $n$ and the distribution of $d$. The rule has no operating characteristic on the population to which it is applied, and no record of passing builds can distinguish it from the exact test.

This is trivial, and triviality is the content: it says that the question “how often does the pairwise rule get it wrong?” has the answer zero for structural reasons, and that the answer is not evidence of correctness. It also relocates the rule's real function. After the per-channel gate fails on some channel, the question changes from *is this build conforming* to *can one shim still save it*, and there the rule does have power — it is a rework-capacity criterion, evaluated on a population that has already failed. Section 5.5 measures exactly that population.

Numerically: across the 32 cells of the sweep in Section 6, the share of draws that the per-channel test accepts and the exact test rejects was zero in every cell; across 4729 draws conditioned on per-channel acceptance, the count of draws rejected by either the exact or the pairwise test was zero.

### 4.2 For two channels the rule is exact

**Proposition 2.** For $n=2$ the pairwise condition is necessary and sufficient for (1): two disks intersect if and only if the distance between their centres does not exceed the sum of their radii.

This is the two-circle condition, and it holds for unequal radii without modification. Its practical consequence is diagnostic. Wherever a specification writes a *sum* of two allocations, it is writing it for a pair — two cameras that must be co-aligned, one instrument that must fall inside another's field of view. In exactly those places the shortcut is not a shortcut; it is the answer. The defect cannot appear where the rule is written, which is Section 7's point stated algebraically.

### 4.3 The band, and its constant

**Proposition 3.** Let $A_i=A$ for all $i$, let $d=\max_{i,j}\lVert d_i-d_j\rVert$, let $r^{\star}$ be the radius of the smallest disk containing all $d_i$, and set $\rho=r^{\star}/(d/2)$. Then

1. (1) holds if and only if $r^{\star}\le A$;
2. $\rho=1$ if the minimal disk is pinned by a diameter pair, and $\rho>1$ otherwise;
3. $\rho\le2/\sqrt{3}$ for every planar configuration, with equality for three points in an equilateral triangle.

*Proof.* (1) is the definition of $r^{\star}$. (2): $r^{\star}\ge d/2$ always, with equality exactly when the two farthest points are antipodal on the minimal circle. (3) is Jung's theorem in the plane, $r^{\star}\le d/\sqrt{3}$. $\square$

The pairwise rule accepts $d\le2A$; the geometry accepts $d\le\sqrt{3}A$. The disagreement is therefore the band

$$
\sqrt{3}\,A<d\le2A,
\qquad (2-\sqrt{3})A=0.268\,A,
\qquad \frac{2-\sqrt{3}}{2}=1-\frac{\sqrt{3}}{2}=13.4\%,
\tag{2}
$$

where $13.4\%$ is the band measured against the span the table permits and $26.8\%$ is the same band measured against the allocation. Both describe the same strip, and quoting one without its denominator is how the figure gets misread; for $A=300''$ the strip is $519.6''$–$600''$, i.e. $80.4''$ wide. The band is non-empty in the strong sense: for every $d$ inside it there are configurations that are feasible (three nearly collinear channels, whose minimal circle is the diameter circle, $r^{\star}=d/2\le A$ throughout) and configurations that are not (the equilateral triple). Feasibility is not a function of $d$ alone, which is why no scalar summary of a table — not the largest pair, not the mean — can decide (1).

![Figure 1](../figures/paper_fig1.png)

*Figure 1. (a) Three channels with equal allocation $A$ whose deviations form an equilateral triangle of side $1.95A$: every pair is inside its sum ($1.95A<2A$) and no common orientation exists ($r^{\star}=1.13A>A$). (b) The three tests on one axis; the shaded strip is where the pairwise rule admits configurations that the geometry rejects.*

### 4.4 The design-side statement

Proposition 3 is a statement about a given set of deviations. The designer's question is the inverse, and its answer is a multiplier.

**Proposition 4.** Suppose every admissible build satisfies $d\le d_{\max}$ for the worst pairwise separation, and let $A_i=A$. Then $A\ge d_{\max}/\sqrt{3}$ is necessary and sufficient for (1) to hold on every such build; the pairwise sum requires only $A\ge d_{\max}/2$. The ratio is $2/\sqrt{3}=1.1547$.

*Proof.* Necessity and sufficiency follow from Proposition 3 with $d=d_{\max}$ attained by an equilateral triple, which is admissible for any $d_{\max}$. The pairwise requirement is $2A\ge d_{\max}$. $\square$

So an allocation set derived from pairwise sums under-provisions by up to $15.5\%$, and the worst case is three channels. More channels do not make it worse — by Jung's theorem the extremal configuration is always a triangle — which is counter-intuitive enough to be worth stating twice: the failure is not a many-channel effect, it is a three-channel effect that any group of three within a larger payload can realise.

The right-hand panel of Figure 3 draws this as a nomogram: for a given worst pairwise separation $d$, the table implies an allocation $d/2$ and the geometry requires $d/\sqrt{3}$, and the strip between the two lines is the shortfall, always $15.5\%$ of whichever allocation is chosen.

### 4.5 Ring families and scale invariance

For $n$ equally spaced channels on a circle, $\rho_n=1/\sin(\lfloor n/2\rfloor\pi/n)$: exactly $1$ for even $n$, where an antipodal pair pins the disk, and $1/\cos(\pi/2n)$ for odd $n$, peaking at $n=3$ and decaying as $1+\pi^2/(8n^2)$. The values for $n=3,5,7,9$ are $1.1547$, $1.0515$, $1.0257$, $1.0154$.

That last sequence states something precise and easy to over-read, so: for a *given* worst separation $d$, no configuration of any number of channels is more pessimistic than an equilateral triple of the same diameter, and adding channels to an evenly spread ring brings $\rho$ toward $1$. This is a statement about the extremal configuration at fixed spread, not about exposure as $n$ grows. Section 6.1 measures the other direction — for a fixed allocation, more channels mean a larger spread, so a random draw migrates further into the band and the exposure rises with $n$ before saturating. Both are true and they answer different questions: Proposition 3 bounds how wrong a single verdict can be, and the sweep of Section 6 bounds how often it is wrong. Both thresholds in (2) are proportional to $A$, so the *fraction* is independent of the tolerance magnitude: a payload with $0.5^\circ$ allocations and one with $30^\circ$ allocations have identical disagreement geometry, and only the absolute width changes. Whatever this failure is, it is not a small-angle artefact and not a numerical one.

### 4.6 Deciding (1) exactly, and what a certificate adds

The minimal enclosing disk is determined by two or three of the points, so (1) can be decided by enumerating candidates — the $d_i$ themselves and the pairwise circle intersections — and testing each against all constraints: $O(n^3)$ arithmetic, no solver, no tolerance parameter, no initial guess. For the pure allocation problem this enumeration is complete and a binary verdict plus a witness suffices.

Two by-products are more useful than the verdict. The **support set** — the two or three channels that pin the answer — answers “which channels would have to move”. The **minimal infeasible subset** (IIS), obtained by deletion, answers “which channels cannot share an interface”, and by Helly's theorem in the plane it has at most three members [2]. A third verdict — undecided — becomes necessary only when non-convex constraints such as keep-out cones are added, and then the undecided branch must carry the unsearched area rather than a shrug. Section 5.3 is a case where the third verdict is the honest answer for a different reason: the document admits two readings, and the two readings differ by a number.

## 5. A public specification and its replay

### 5.1 The table

`431-SPEC-000113` Rev A (NASA/GSFC, 2007) states, per instrument, an alignment allocation relative to the spacecraft reference, as a half-cone in arc-seconds per axis, at a declared confidence (“$3\sigma$ or worst case”) [7]. Ten channels are specified: five at $300''$ (the two LROC narrow-angle cameras, the wide-angle camera, LOLA and LAMP), three at $500''$ (Diviner, CRaTER, LEND), Mini-RF at $750''$, and the laser-ranging telescope at $36''$.

Three of the four columns a full replay needs are public: the nominal geometry, the allocation, and the reference frame. The fourth — the as-built deviation of each channel — is not, and will not be. The as-built spread $T$ is therefore carried as a free parameter and swept, with the criteria compared inside the sweep rather than against an asserted value. That is the only honest use of a public document here: it constrains the allocations, not the build.

### 5.2 The one place the document does arithmetic

Table 9-3 allocates $102''$ to the relative alignment of the two narrow-angle cameras against a requirement of $103''$ ($500\,\mu$rad) — a margin of $1''$. Two channels, so by Proposition 2 the pairwise rule is exact, and the solver reproduces the $102''$ capacity and the $1''$ margin with $\rho=1.000$.

The document's only pairwise addition is in the one case where pairwise addition is exact. The same arithmetic applied to three channels would over-state the capacity by $13.4\%$, and the document contains no three-channel sum. This is Proposition 1's mechanism seen from the design side, and it is why Section 7 can be stated as a general claim rather than a suspicion about this document.

### 5.3 A clause with two readings

Section 8.4.2 requires LOLA's field of view to fall within $1.4^\circ=5040''$ of a narrow-angle camera's boresight; Table 8-3 allocates $1636''$ of co-alignment. The half field of view of a narrow-angle camera is $0.05\,\mathrm{rad}/2=1.4324^\circ=5157''$.

Two readings are grammatically available. Under the first, $1.4^\circ$ bounds the *nominal* placement and the allocation is spent inside it, leaving $117''$ of geometric slack. Under the second, $1.4^\circ$ bounds the *as-built* placement, in which case the requirement plus the allocation exceeds the geometric room by $5040+1636-5157=1519''$ and the clause cannot be met as written. The document does not say which reading applies.

The output is *undecided*, with the gap between the readings quantified. This is not fault-finding: a clause that will be signed off should not depend on which reading its reviewer adopts, and the value of a third verdict is that it makes the ambiguity a number rather than a footnote. In a decision procedure that returns only yes or no, this clause would have been returned as one or the other, silently.

### 5.4 A partition recovered from the numbers

Take an as-built spread $T=220''$ (uniform in a disk, the worst-case convention) for the ten channels. The nine instruments on the deck, treated as one interface, are feasible with at least $140.3''$ to spare. Add the laser-ranging telescope — allocated $36''$, six times tighter than anything else, and mounted six hundred millimetres away on a different bracket — and the family becomes infeasible: every allocation would have to grow by $15.4''$ before a common point exists; the minimal infeasible subset is $\{$LAMP, laser-ranging telescope$\}$, and loosening a single allocation by $0.96''$ restores feasibility.

Section 12.0 of the specification states that the laser-ranging optic is mounted on the high-gain-antenna bracket, not on the instrument deck. The tool recovered the document's mechanical partitioning from ten numbers, without being told the partitioning. That is the practical content of the IIS: not a diagnostic about arithmetic, but a statement about structure, obtained from the same table a reviewer already has.

### 5.5 The rescue regime

The regime in which the pairwise rule has power is the one Proposition 1 excludes from conformity: builds in which at least one channel is outside its allocation and the question is whether one shim still saves the build. Sweeping the as-built spread $T$ over the design box for the nine deck instruments, with their real unequal allocations:

| $T/A_{\min}$ | 1.00 | 1.05 | 1.10 | 1.15 | 1.25 | 1.40 | 1.60 | 2.00 |
|---|---|---|---|---|---|---|---|---|
| pairwise says a shim exists | 1.000 | 0.982 | 0.926 | 0.837 | **0.602** | 0.370 | 0.144 | 0.014 |
| one actually exists | 1.000 | 0.976 | 0.915 | 0.815 | **0.569** | 0.338 | 0.126 | 0.011 |
| builds the table misses | 0.000 | 0.006 | 0.011 | 0.022 | **0.033** | 0.032 | 0.018 | 0.002 |

The two rules agree at $T/A_{\min}\le1$, where every channel is inside its allocation and no shim is needed — that is Proposition 1, visible as a table — and they agree again above $1.6$, where neither promises much. Between them the rule over-states the chance that one shim saves the build, peaking at $3.3$ percentage points of the design box at $T/A_{\min}=1.25$, where the rule promises a rescue in $60.2\%$ of builds and geometry allows $56.9\%$: a $5.8\%$ relative over-statement.

![Figure 2](../figures/p3_replay.png)

*Figure 2. Replay on the ten-channel specification. (a) The ten allocations, with the band of (2) marked at $300''$; the $36''$ laser-ranging telescope is mounted on the antenna bracket, not the instrument deck. (b) Share of the design box for which one shim exists: pairwise estimate against exact, nine deck instruments, worst-case convention. (c) The knife edge at $T=1.05A$: three boundary arcs of radius $A$ whose centres sit outside the frame. (d) The field-of-view clause of Section 5.3: requirement plus allocation exceeds the half field of view by $1519''$.*


## 6. Where the disagreement can be measured

Section 5.5 is one slice through a three-dimensional regime. This section maps it, by channel count and by allocation heterogeneity, using equal allocations so that $\rho$ of Proposition 3 applies without confounding.

### 6.1 Channel count and allocation-to-spread ratio

Share of the design box on which the pairwise rule accepts and no common point exists, in percent, three thousand draws per cell, Gaussian as-built deviations with per-axis $\sigma$ and equal allocations $A$:

| $n$ \ $A/\sigma$ | 1.0 | 1.2 | 1.5 | 1.8 | 2.0 | 2.4 | 3.0 |
|---|---|---|---|---|---|---|---|
| 3 | 0.50 | 0.60 | 0.53 | 0.30 | 0.07 | 0.00 | 0.00 |
| 4 | 1.10 | 1.43 | 1.33 | 0.83 | 0.57 | 0.07 | 0.00 |
| 5 | 0.60 | 1.63 | 2.07 | 0.70 | 0.73 | 0.17 | 0.00 |
| 9 | 0.00 | 0.43 | 1.60 | 2.87 | 2.37 | 0.57 | 0.03 |

Monte Carlo standard error is about $0.15$ percentage points at these rates, so the table resolves the order of magnitude of each cell and not the differences within a row: the peak position is meaningful to about one grid step, and the non-monotonicity at $n=5$ between $1.8$ and $2.0$ is not. Three features are robust. The peak sits at $A/\sigma\approx1.2$–$1.8$, that is, at allocations of one to two standard deviations — designs that have been squeezed, not designs that are comfortable. It grows with channel count but saturates: the peak rises by a factor $1.4$ from $n=5$ to $n=9$, not by the factor $1.8$ that a “more channels, more failure” intuition would suggest. The band of (2) has a fixed width in $d$, namely $0.268A$, so extra channels move the population through the band rather than widening it, and the extremal configuration is a triangle at every $n$ (Proposition 3). And it is gone by $A/\sigma=3$: at the convention the replayed specification itself declares, the residual is $0.03\%$ at nine channels and zero below five.

The zero in the $n=9$, $A/\sigma=1$ cell is not a discrepancy but a ceiling effect: at one standard deviation the pairwise rule itself accepts only $0.7\%$ of builds, so there is almost no acceptance region in which to disagree.

### 6.2 Allocation heterogeneity

Nine channels at $A_{\min}=1.5\sigma$, allocations spaced geometrically up to $A_{\max}$, again in percent:

| $A_{\max}/A_{\min}$ | 1.0 | 1.5 | 2.0 | 3.0 | 5.0 | 10 | 20 |
|---|---|---|---|---|---|---|---|
| missed by the table | 1.80 | 2.73 | 1.90 | 0.80 | 0.33 | 0.10 | 0.00 |

Heterogeneity is not neutral, and it is not monotone either, which is worth stating because the intuitive account is only half right. A channel with a slack allocation absorbs the common component of the spread for others — the shim can be pushed toward it — so $\rho$ of Proposition 3 collapses toward $1$ as allocations become unequal. But spreading the allocations at a *fixed* tightest value also enlarges the acceptance region: the pairwise rate rises from $17\%$ to $48\%$ between ratios $1$ and $1.5$ in the same sweep, and the disagreement can only live inside an acceptance region. The two effects compete, and the measured result is a hump: $1.8\%$ at equal allocations, $2.7\%$ at ratio $1.5$, then $1.9\%$, $0.8\%$, $0.33\%$, $0.10\%$ and $0.00\%$ at ratios $2$, $3$, $5$, $10$ and $20$. Dilution wins decisively only beyond a factor of five, and the replayed deck's own ratio of $2.5$ ($300''$ to $750''$) sits near the top of the hump rather than past it.

![Figure 3](../figures/paper_fig3.png)

*Figure 3. (a) Share of the design box on which the table accepts and geometry does not, against the allocation measured in standard deviations, for four channel counts; hollow markers are the peaks. (b) The same against allocation heterogeneity at fixed channel count: a slack channel absorbs the spread. (c) The design-side statement of Proposition 4.*

### 6.3 Reading the two sweeps together

The two sweeps place the number measured in Section 5.5 without claiming to predict it. The nine deck instruments have unequal allocations spanning a ratio of $2.5$ and, at $T/A_{\min}=1.25$, a missed share of $3.3\%$; the heterogeneous cells of Section 6.2 sit in the range $0.8$–$2.7\%$, so the deck case is of the right order, but the two sweeps use different parametrisations — spread relative to the tightest allocation under a worst-case draw, against allocation relative to $\sigma$ under a Gaussian one — and no point prediction should be read across them. What transfers is the shape: the effect needs few channels, allocations of comparable size sitting at one to two standard deviations, and it is bounded above by a few percent of the design box in every configuration tested. That bound, not any single cell, is the paper's quantitative claim.

## 7. Why the record is silent

Proposition 1 explains the silence; three features of this class of document explain why the silent regime is the one that gets visited. Each is a fact about practice, and each has a number attached in Section 6.

**The clauses are pairwise.** Where a specification writes a sum it writes it for two instruments — two cameras, one instrument inside another's field of view — and Proposition 2 makes the addition exact there. The configuration that would expose the defect, three channels sharing one orientation, is the one the document does not contain. The replay found exactly one pairwise sum in the replayed document, and it is correct to the arc-second.

**The confidence convention is generous.** Allocations at $3\sigma$ against an as-built spread of order $1\sigma$ leave a factor of three between the two sides of the inequality. The disagreement needs the allocation to be comparable to the spread, and the convention forbids that by construction: at $A/\sigma=3$ it is $0.03\%$ at nine channels and zero below five.

**The allocations are heterogeneous, though this one is not decisive.** A slack channel absorbs the common component for the others, and at large ratios the disagreement disappears: $0.8\%$ at ratio $3$, $0.10\%$ at ratio $10$, zero at ratio $20$. But the replayed deck's own ratio is $2.5$, which sits on the hump of Section 6.2 rather than past it, and the document's ratio of $20.8$ counts the laser-ranging telescope, which is not on the deck. This feature therefore does not by itself account for the null in this document: the $3\sigma$ convention does.

Of the three features, the first is structural and the second is decisive for this document; the third is a contributory dilution that would matter more in a payload with one very loose channel. The conclusion is uncomfortable but clean: a measured $0$ is **not evidence that the rule is correct**. It is evidence about the regime, and here it is evidence about a regime that the conventions exclude in advance. The methodological statement is worth isolating because it transfers to any decision rule evaluated only on data that has already passed a stronger rule:

> The frequency with which a rule is contradicted is not a measure of its validity when the rule is only tested where it is trivially true.

Two readings of that statement are available and the difference matters. The weak reading is that more data would help. The strong reading, which Proposition 1 supports, is that no data of the kind collected can help: a build that would distinguish the two rules has already failed its per-channel check and is documented as a non-conformance — an alignment problem, an assembly problem, a supplier problem — and never as a tolerance-analysis error. The defect is not rare in the record. It is unrepresentable in the record.

## 8. A screen

The three features of Section 7 are properties of the table, not of the build, so they can be checked before any measurement is made. They are not equally important, and the sweeps of Section 6 rank them:

1. **Is the tightest allocation at least $2.5\sigma$?** This is the dominant knob, and it is decisive on its own. At $A_{\min}/\sigma=3$ the missed share is $0.03\%$ at nine channels and zero below five, whatever the allocation pattern; at $1.5\sigma$ it is $1$–$3\%$. A *yes* here bounds the answer to a fraction of a percent before any geometry is computed.
2. **How many channels share the interface?** The exposure rises with channel count — a peak of $0.6\%$ at three, $1.4\%$ at four, $2.1\%$ at five, $2.9\%$ at nine — so a large family is the unfavourable direction, contrary to what the extremal-configuration argument of Section 4.5 might suggest. The factor available is about five across the whole range, and it saturates.
3. **How heterogeneous are the allocations?** Dilution is real but arrives late and is not monotone: it protects beyond a ratio of about five, and between one and two it can make things slightly worse (Section 6.2). A *no* here is a weak all-clear.

Applied to the replayed specification: $3\sigma$ on the tightest channel (question 1 passed, and passed decisively), ten channels (question 2 at its worst), a deck ratio of $2.5$ (question 3 not protective). The screen's verdict is therefore *expect a fraction of a percent* — the dominant axis is safe by a factor of three, and the two modifiers can buy back only a factor of a few. That is what the $1200$-draw measurement then found.

A screen that predicts its own null result is a weak test of the screen, and this one should be read that way. What it does claim is the right shape: it tells a reviewer in five minutes whether the geometry is worth computing at all, it ranks the axes instead of listing them, and it tells an analyst when a reported $0$ is informative — here, informative precisely because the dominant axis can be named — and when it is empty.

The screen's thresholds are calibrated to the sweeps of Section 6, not derived, and they are a triage heuristic rather than a specification. The constant of Proposition 3, by contrast, is exact and needs no calibration: $2/\sqrt{3}$ holds for every $n$, every scale and every configuration, and it is attained.

## 9. Threats to validity

**No as-built column.** Every number in Sections 5.5 and 6 is a function of a swept parameter, not of a measurement. The sweep design — uniform in a disk for the worst-case convention, Gaussian at the declared confidence otherwise — is a convention, and the percentages are shares of a design box, not frequencies in a population of builds. The distinction between “$13.4\%$ of the tolerance span” and “$13.4\%$ of designs” is the one this paper exists to keep straight, and it applies to its own measurements too.

**One interface is counterfactual for this document.** The specification replayed in Section 5 aligns each instrument separately. Section 5.2 checks the method against the document's arithmetic, which is a real check, but it is not evidence that the flight article used a shared interface. The partition recovered in Section 5.4 is a consistency check with the document's mechanical description, not a discovery about the spacecraft.

**The model is geometric and static.** Thermal gradients, preload, cure shrinkage and flexibility are outside it, and several of them produce relative motions of the same order as the allocations. A tool of this kind belongs upstream of those effects, in the allocation and rework decisions, not downstream in the verification of a finished assembly.

**The screen's thresholds are calibrated.** $2.5\sigma$, the channel-count slope and the factor of five come from Section 6, where the third is the weakest: the hump in Section 6.2 means heterogeneity protects only beyond a clear margin. They are defensible and they are not laws, and the ranking of the three axes is more robust than any of the numbers attached to them.

**No failure is claimed.** The paper does not assert that any programme has suffered a misalignment attributable to this rule. The claim is narrower and, we think, harder to dismiss: the rule's guarantee in design is weaker than its use by a constant that is known, attained and scale-free; and in conformity assessment its guarantee is empty, so that the empirical record cannot adjudicate it.

**What would change the conclusion.** One column of as-built deviations from a build in which the per-channel check passed and the assembly nevertheless required rework, together with the criterion the review actually applied, would convert the bound of Proposition 3 from a possibility into a rate, and would test Proposition 1 against practice rather than against its own definition. Nothing else in this paper is as decisive, and no public document contains it. Failing that, the reverse case is equally informative: a documented rework in which the pairwise table promised a rescue that one shim did not deliver would establish that the rework population is non-empty and that the $5.8\%$ relative over-statement of Section 5.5 has been paid for.

## 10. Conclusion

The pairwise sum rule is the two-channel feasibility condition applied to $n$ channels. It is exact at $n=2$; it is inert at $n\ge3$ for conformity, because its rejection region lies inside the region the per-channel check has already rejected, so on conforming data it cannot fire and no build record can test it; and when it is used to set allocations it is optimistic by at most Jung's constant — allocations must be $2/\sqrt{3}=15.5\%$ larger than pairwise sums imply, with the worst case attained by three channels in an equilateral configuration and independent of the tolerance magnitude.

On a public ten-channel specification the accounting closes. The rule reproduces the document's one pairwise addition to the arc-second, in the one place where that addition is exact. One clause is returned undecided with a $1519''$ spread between its two readings. The minimal infeasible subset recovers the document's mechanical partitioning from ten numbers. And the disagreement, measured across channel counts, allocation-to-spread ratios and allocation heterogeneity, peaks at $2.9\%$ of the design box, falls to $3.3$ percentage points on the document's own unequal allocations, and vanishes at the $3\sigma$ convention the document declares — a null result that three questions answerable from the table alone predict in advance.

The rule is not wrong. In design it is optimistic by a constant that can be carried in a nomogram; in assembly it is silent, and it is silent for a reason that no further measurement will remove.

---

## Data and code availability

- Allocations, with clause numbers and verbatim quotes: `analysis/data/lro_alignment_allocations.csv`.
- Solver (planar enumeration, cross-checked against an independent spherical-cap solver, no disagreement on 300 random instances): `src/rpy_polar_synth/p3_replay.py`.
- Replay sweeps: `run_p3_replay.py`. Regime map: `run_regime_map.py`. Figures: `plot_p3_replay.py`, `plot_paper_fig1.py`, `plot_regime.py`.
- Outputs: `outputs_p3/lro_channels.csv`, `rescue_curve.csv`, `production_view.csv`, `regime_grid.csv`, `regime_heterogeneity.csv`, `regime_round_trip.csv`, `summary.json`, `regime_summary.json`.

## References

[1] H. Jung, “Ueber die kleinste Kugel, die eine räumliche Figur einschliesst”, *Journal für die reine und angewandte Mathematik* **123** (1901) 241–257.

[2] E. Helly, “Über Mengen konvexer Körper mit gemeinschaftlichen Punkten”, *Jahresbericht der Deutschen Mathematiker-Vereinigung* **32** (1923) 175–176.

[3] E. Welzl, “Smallest enclosing disks (balls and ellipsoids)”, in *New Results and New Trends in Computer Science*, Lecture Notes in Computer Science **555**, Springer (1991) 359–370.

[4] K. L. Clarkson, “Las Vegas algorithms for linear and integer programming when the dimension is small”, *Journal of the ACM* **42**(2) (1995) 488–499.

[5] R. T. Rockafellar, *Convex Analysis*, Princeton University Press (1970).

[6] Yu. Nesterov, A. Nemirovski, *Interior-Point Polynomial Algorithms in Convex Programming*, SIAM (1994).

[7] NASA Goddard Space Flight Center, *LRO Pointing and Alignment Specification*, 431-SPEC-000113 Rev A, 6 April 2007.

[8] ASME Y14.5-2018, *Dimensioning and Tolerancing*, American Society of Mechanical Engineers (2018).

[9] ISO 1101:2017, *Geometrical product specifications (GPS) — Geometrical tolerancing — Tolerances of form, orientation, location and run-out*, International Organization for Standardization (2017).

[10] JCGM 106:2012, *Evaluation of measurement data — The role of measurement uncertainty in conformity assessment*, Joint Committee for Guides in Metrology (2012).

[11] H. F. Dodge, H. G. Romig, “A method of sampling inspection”, *Bell System Technical Journal* **8**(4) (1929) 613–631.

[12] N. Megiddo, “Linear-time algorithms for linear programming in $R^3$ and related problems”, *SIAM Journal on Computing* **12**(4) (1983) 759–776.
