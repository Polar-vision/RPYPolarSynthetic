# When is a pairwise boresight table sufficient? Closed-form bounds and a decisive test

> **DRAFT STATUS — READ BEFORE EDITING**
>
> This file is a **protocol draft**. Sections 1–4 and 6–8 are complete on theory and on  
> computed evidence. Section 5 is a **data slot**: it contains no measured claim, and it  
> must remain labelled as unexecuted until `measured_slot.json` has `status.state == FILLED`  
> and `_provenance` is complete.
>
> Two rules for anyone editing this file:
>
> 1. **Never invent a number for section 5.** A plausible-looking measurement is data  
>    fabrication. The correct state of that section is "not executed", not "about 0.05°".
> 2. **Never relabel section 4 as measurement.** Section 4 is a computed illustration. It  
>    is honest as an illustration and fraudulent as a result. The word *synthetic* must  
>    stay in its heading and in the sentence that introduces Table 2.
>
> What this draft buys you: every argument, every bound, every table of the final paper  
> except one column. When the record arrives, the work is to fill `measured_slot.json`, run  
> one script, and rewrite section 5 — not to write a paper.



---

## Abstract

A multi-channel payload is allocated tolerances one channel at a time and checked one pair  
at a time. This paper asks a narrower question than whether that check is correct: **what  
would it take to find out?** Three results are given. First, the ratio between the radius  
the pairwise sum permits and the radius that actually admits a common orientation has a  
closed form on ring families, $\rho=1/\sin(\pi/n)$, so the optimism of the table is  
$1-\sqrt3/2$ in capacity terms (13.40 % at $n=3$) or, read as an allocation, a shortfall of  
$2/\sqrt3-1$ (15.47 %). Second, the resulting blind band has a **fixed absolute width**  
that scales with the allocation and not with the channel count: at a 300 arc-second  
allocation it is 80.4 arc-seconds, so a table can pass a build that is short by a  
measurable, bounded amount. Third, and as the main contribution, the paper states what a  
record must contain to settle the matter — the measured per-channel deviations, the  
criterion actually in force at the review, and the assembly outcome — and shows that the  
middle column is the one that is never published, which is why the question has stayed  
open in an area where the geometry was settled in 1901. A screen identifies which systems  
can yield a decisive record at all; applied to a public ten-channel specification it  
returns zero disagreements in 1200 draws under the document's own three-sigma convention,  
which is reported here as a negative result about that specification rather than as  
evidence about practice. The decisive record itself is not yet in hand, and section 5 says  
so explicitly.

**Index Terms**—boresight alignment, conformance assessment, decision rule, minimal  
enclosing circle, tolerance allocation, measurement protocol, negative results.

---

## 1. Introduction

### 1.1 The question this paper answers

An alignment budget for a multi-channel payload is written twice: once as a requirement on  
a relative orientation, and once as an allocation to each channel. The two are connected in  
practice by a pairwise table — every pair of channels must lie within the sum of their two  
allocations. The table is attractive for organisational reasons that have nothing to do  
with geometry: a pairwise requirement has two owners, it fits in two interface control  
documents, and it can be verified by pointing one instrument at another.

The companion paper [1] establishes what that table can and cannot decide: on conforming  
data its rejection region is empty by construction, so no record of passing builds  
distinguishes it from an exact test; and the region it fails to see has bounded depth.

That result leaves an obvious question, and it is the subject here. **If the rule is  
unfalsifiable against passing records, what record would falsify it?** The question is not  
rhetorical. It determines whether the preceding result is a curiosity about a decision rule  
or a statement about engineering practice, and it determines what an organisation would have  
to write down in order to know which of the two it is holding.

### 1.2 Why the answer is not "measure more carefully"

The tempting answer is that better metrology settles it. It does not, and the reason is  
worth stating plainly because it shapes the entire protocol.

A pairwise table can only be shown insufficient by a build in which the table passes and the  
exact test fails. Both verdicts are functions of the *same* vector of measured deviations;  
improving the measurement of that vector moves both verdicts together. Precision buys  
resolution on where the build sits relative to the two boundaries. It does not buy a  
disagreement. A disagreement exists or not depending on where the build landed, and the  
only thing an experiment can do is find builds that landed in the band.

So the missing ingredient is not accuracy. It is **the joint record**: deviations,  
criterion, and outcome, on the same item, at the same time. Section 2 states what that  
record must contain and section 3 shows how narrow the window is in which it can exist at  
all.

### 1.3 Contributions

1. A closed form for the optimism ratio on ring families, with the absolute width of the  
   blind band as its consequence, and an explicit statement of which denominator each  
   percentage carries (section 3). The three percentages that circulate in this literature  
   — 13.40 %, 15.47 %, 3.3 % — have three different denominators, and mixing them is the  
   most common way this result is misreported.
2. A **screen** (section 2.2) that decides, from the design alone, whether a system can  
   yield a decisive record. This is what turns the open question into a finite task: most  
   systems cannot, and saying so is part of the result.
3. A **frozen predicate** for decisiveness (section 2.3), stated before any record is  
   examined, together with the interpretation of every possible outcome (section 6). The  
   paper is therefore a pre-registered test in structure even though its record is pending.
4. An explicit negative result on a public specification (section 5.3): the one public  
   ten-channel table available returns zero disagreements under its own confidence  
   convention, which is a statement about that specification and must not be generalised.

---

## 2. What a decisive measurement must contain

### 2.1 The three columns

A record settles the question if and only if it carries, for one physical item:

| Column | Content                                                                                | Typical location           | Published?           |
| ------ | -------------------------------------------------------------------------------------- | -------------------------- | -------------------- |
| **D**  | per-channel measured deviation $d_i$, with frame definition and instrument uncertainty | AIT metrology log          | never                |
| **C**  | the criterion actually in force at the review, quoted                                  | review record, check sheet | rarely               |
| **O**  | what happened: first assembly passed, or rework, or calibration absorbed it            | programme records          | never in this detail |

The literature contains D and C separately, in abundance — calibration papers report  
deviations [2], [3], standards fix the vocabulary of the criterion [4], [5] — and O  
separately, in the anecdotal form of lessons-learned documents. What is absent is the join.  
Every element of the join is individually unremarkable, which is exactly why its absence has  
gone unnoticed: no single field is hard to publish, and the triple is hard to publish  
because O belongs to whoever paid for the rework.

**This is the paper's central claim about the state of the art**, and it is a claim that can  
be checked rather than asserted: search for a document that reports all three for the same  
item. The companion paper's replay [1, §V] is the closest available case, and it is  
incomplete in precisely the O column.

### 2.2 The screen: can this system yield a decisive record at all

A record can only be decisive if the build could plausibly have landed in the band. Three  
conditions, all checkable from the design before any measurement:

| #  | Condition                                                                            | Why                                                                                                                                                                   |
| -- | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S1 | $A_{\min}/\sigma_{\text{meas}} \ge 2.5$                                              | if the allocation is loose relative to the build spread, the exact test passes too and there is nothing to disagree about                                             |
| S2 | $n \ge 3$                                                                            | at $n=2$ the pairwise rule **is** exact (section 3.2), so no disagreement is possible in principle                                                                    |
| S3 | the channels share one interface, **or** the system cannot be calibrated after build | a calibratable system absorbs the geometric shortfall, converting a feasibility question into a cost question; the cost form is weaker and needs O with a cost figure |

The screen is the practical yield of the theory, and its main use is negative: it tells an  
organisation which of its programmes are worth instrumenting for this purpose. On the  
public specification examined in section 5.3, S1 holds and S3 holds, but the confidence  
convention puts the build distribution far from the boundary, which is why that  
specification yields no disagreement — a correct application of the screen, not a  
contradiction of the theory.

### 2.3 The frozen predicate

> **Definition (decisive record).** A record is *decisive* iff the pairwise verdict on  
> column D is PASS and the exact verdict on the same D is FAIL.
>
> **Definition (confirmatory).** A decisive record is *confirmatory of the practical claim*  
> iff column O reports that first assembly did not pass, or that calibration was required to  
> absorb a residual.

These two definitions are fixed here, before any record exists, and section 6 pre-commits to  
the interpretation of each possible outcome. The reason is not procedural fastidiousness. The  
band is narrow enough that a record landing in it is a priori unlikely; if the predicate were  
chosen after seeing a record, any record could be read as support, and the test would  
reproduce at the level of the paper exactly the defect the paper is about.

### 2.4 The derived quantities, and one definition that has to be stated

Three quantities are computed from column D and the allocations, and the third is the one  
that is easy to get wrong.

*Enclosing radius.* $r^\star$ is the radius of the smallest disk containing all $d_i$,  
determined by two antipodal points or three boundary points and computed by enumerating both  
families. It is a property of the deviations alone.


*Verdicts.* The pairwise verdict is PASS iff every pair satisfies  
$\lVert d_i-d_j\rVert \le A_i+A_j$. **It is not conjoined with a per-channel test**, and this  
matters: adding "every channel inside its own allocation relative to a fixed datum" would  
make the pairwise verdict fail wherever the exact verdict fails, and the disagreement the  
paper is about would vanish by construction. The datum is precisely what the exact test is  
free to choose. The exact verdict is PASS iff some $x$ satisfies  
$\lVert x-d_i\rVert \le A_i$ for all $i$, decided by enumerating the candidate witnesses  
(each centre, and each crossing of two circle boundaries).

*The gap.* The engineering gap is the smallest uniform loosening $t\ge0$ such that the family  
becomes feasible with every allocation raised to $A_i+t$. It is **not** $r^\star-\min_i A_i$;  
the two agree only under equal allocations, and with unequal allocations the minimum of  
$\max_i(\lVert x-d_i\rVert-A_i)$ does not sit at a candidate point, so neither the slack of  
the exact test nor a difference of radii may be reported as the gap. The distinction is worth  
one paragraph because both shortcuts are natural and both overstate or understate the number  
an engineer would have to make up.

All three are computed by `run_paper4_record.py`, with $r^\star$ obtained from two  
independent solvers (support enumeration and bisection on the uniform-radius feasibility  
test) that must agree to $10^{-5}$ arc-seconds before any verdict is reported.

---

## 3. Closed-form bounds

### 3.1 The optimism ratio on ring families

For $n$ channels with equal allocation $A$ placed uniformly on a ring, the worst pairwise  
separation is $d=2R\sin(\pi/n)$ for a ring of radius $R$, so the radius the pairwise sum  
permits and the radius that admits a common orientation stand in the ratio

$\rho=\frac{1}{\sin(\pi/n)}.$

At $n=3$, $\rho=2/\sqrt3=1.1547$. The numerical check in `outputs_replication` reproduces  
this to $2.3\times10^{-4}$ over $n=3\ldots9$ (`R0.max_abs_err`), the residual being the  
finite step of the search rather than a discrepancy.

### 3.2 Two channels are exact, and this is not a detail

At $n=2$ the pairwise test and the exact test coincide: one pair, one constraint, no gap. The  
case is worth isolating because a large share of alignment practice is pairwise by  
construction, and in that share the table is right. The defect is introduced by the third  
channel, and only by the third channel.

### 3.3 The three denominators

This is the point at which the result is most often misreported, so each is given with its  
denominator.

| Quantity             | Value                           | Denominator                                | Meaning                                                                |
| -------------------- | ------------------------------- | ------------------------------------------ | ---------------------------------------------------------------------- |
| Capacity optimism    | $1-\sqrt3/2=13.40\%$            | the separation the pairwise sum permits    | the table permits 13.40 % more spread than a common orientation allows |
| Allocation shortfall | $2/\sqrt3-1=15.47\%$            | the allocation derived from a pairwise sum | an allocation built that way is 15.47 % too small                      |
| Blind band width     | $80.4$ arcsec at $A=300$ arcsec | absolute, scales with $A$                  | a passed build can be short by this much                               |

The first two are the same fact read in two directions and differ by which quantity is held  
fixed. They are not interchangeable in a sentence. The third is the one with engineering  
content: **it is absolute**, so a programme can compare it against its own metrology  
uncertainty and decide whether the band is inside or outside the noise.

### 3.4 The design-side statement, and the direction of the fix

Because $r^\star$ depends only on the geometry and $\min_i A_i$ only on the specification,  
tightening an allocation cannot make an infeasible design feasible — it shrinks the feasible  
set. The reflex "it does not fit, so tighten the tolerance" is directionally wrong for this  
class of problem. Only two moves exist: move a nominal to reduce $r^\star$, or relax the  
binding allocation to raise $\min_i A_i$. This is a statement about the model and it holds  
independently of any measurement, which is why it survives the pending status of section 5.

---

## 4. A synthetic illustration

> **The configuration in this section is computed, not measured.** It exists to show what a  
> disagreement looks like on paper. No physical system is described, and no claim is made  
> that any build has landed here. The numbers are reproducible from  
> `outputs_replication/summary.json` (entry `R4`) and `outputs_p3/summary.json` (entry  
> `C2_band`).

Three channels with unequal allocations in a configuration where the pairwise sum clears by  
a comfortable margin:

| Quantity                              | Value            |
| ------------------------------------- | ---------------- |
| pairwise radius permitted             | 0.4330°          |
| radius admitting a common orientation | 0.5000°          |
| $\rho$                                | 1.1547           |
| shortfall                             | 0.0500°          |
| pairwise verdict                      | PASS             |
| exact verdict                         | FAIL             |
| support set size                      | 3 (all channels) |

The table passes. No common orientation exists. The shortfall is $0.050°$, i.e. 180  
arc-seconds, and it is not a numerical artefact: the two solvers agree to $10^{-5}$ degrees  
by construction of the cross-check in [1, §IV].

**This is what the paper needs to find in the field, and it has not found it.** Everything  
down to this sentence is reproducible today; the next sentence is not, and the draft stops  
there rather than filling the gap with a configuration that looks like a build.

---

## 5. The measured test

> **STATUS: NOT EXECUTED.** This section is a container, not a result. Its subsections  
> describe what will be reported and in what form. No number in this section may be  
> populated from a model, a target, or an estimate. When a record is obtained, populate  
> `measured_slot.json`, run `run_paper4_record.py`, and rewrite this section from its  
> output.

### 5.1 The record

`[SLOT-5.1: system class, channel count, allocation range, whether one interface is shared,
whether the system is calibratable after build. Source: measured_slot.json:record.system]`

### 5.2 The measurement

`[SLOT-5.2: measured per-channel deviations, frame definition, instrument and its
uncertainty, epoch, repeatability. Source: measured_slot.json:record.measured_deviations]`

The repeatability figure is not decoration. The band at a 300 arc-second allocation is 80.4  
arc-seconds; a measurement whose repeatability approaches that figure cannot place a build  
inside or outside the band with confidence, and the record would be indecisive for  
metrological rather than geometric reasons. This is stated in advance so that the outcome  
cannot be reinterpreted afterwards.

### 5.3 The criterion in force, and the negative result already in hand

`[SLOT-5.3: the criterion quoted from the review record, with its wording. Source:
measured_slot.json:record.review_at_the_time]`

One thing is already known under this heading and should be reported as a negative result  
rather than buried. On the public ten-channel specification replayed in [1, §V], the  
pairwise rule and the exact rule return **zero disagreements in 1200 draws** under the  
document's own three-sigma convention; the worst-case reading puts the disagreement rate at  
**3.3 %** of the design box. So the one public table available is *not* an instance of the  
failure mode. That is a statement about that specification, obtained by applying the screen  
of section 2.2, and it must not be paraphrased as "the failure mode is rare in practice" —  
which is what a reader will try to do with it.

### 5.4 The outcome

`[SLOT-5.4: first assembly result, rework if any, whether calibration absorbed the residual
and at what residual, cost and schedule impact if recorded. Source:
measured_slot.json:record.outcome]`

### 5.5 The verdict on the predicate

`[SLOT-5.5: r*, gap, both verdicts, decisive yes/no, confirmatory yes/no, and the agreement
figure of the two solvers. Source: measured_slot.json:record.derived, written by
run_paper4_record.py — never typed by hand.]`

If the two solvers disagree by more than $10^{-5}$ arc-seconds, the section reports  
UNDECIDED and no verdict. The rule is inherited from the companion paper's dual-implementation  
constraint and is not negotiable: a tool used to release hardware must never return a wrong  
"no".

---

## 6. What each outcome would mean

Pre-committed, to be read as written whatever section 5 eventually reports.

| Section 5 finds                             | Reading                                                                          | Consequence for the practical claim                                                                                                                                |
| ------------------------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| decisive **and** confirmatory               | the table passed a build that then failed                                        | the claim holds in its strong form; the band is a field-observable failure mode, and the screen has a validated positive case                                      |
| decisive **but** not confirmatory           | the table passed a build that also passed, with calibration absorbing a residual | the claim holds in its cost form only: the shortfall is real but payable. This is the outcome most likely to be found, and it is the one that matters commercially |
| not decisive, screen predicted decisive     | the screen over-admits                                                           | the screen's S3 is too permissive; the result is a corrected screen, still publishable, and still useful                                                           |
| not decisive, screen predicted not decisive | consistent with the negative result of 5.3                                       | the paper's contribution reduces to the bounds plus the screen. This is a legitimate outcome and must be reported as such                                          |

The fourth row is the one to write down before starting, because it is the row a reader will  
suspect was added afterwards. It is not: it follows from the negative result already obtained  
on the public specification, and it is the most probable outcome of a single record.

---

## 7. Discussion

### 7.1 What the bounds do and do not settle

The bounds in section 3 are exact and require no measurement. They settle the design-side  
question completely: an allocation derived from a pairwise sum is 15.47 % too small, and  
this is a constant, not an estimate. What they do not settle is the frequency of the  
assembly-side failure, and no amount of theory can settle a frequency. That asymmetry —  
exact constants on one side, an open frequency on the other — is the structural reason this  
question has remained open, and stating it is more useful than another sweep over synthetic  
configurations.

### 7.2 Relation to the companion paper

[1] answers what the rule decides; this paper asks what could test it. The two are  
deliberately separated because they have different evidence requirements: [1] is complete  
with a public specification and reproducible code, while this paper cannot be completed  
without a record that no public specification contains. Presenting them as one paper would  
have forced the second half to be argued from the first half's evidence, which is the error  
the paper is about.

### 7.3 Limitations

The model is geometric. Thermal, fastener-torque, adhesive and stress-relief contributions  
are outside it, and a real shortfall may be smaller or larger than the geometric figure  
because of them [1, §IX]. The frame definition is assumed unambiguous, which in practice  
requires a written convention that many programmes leave implicit. And the cost form of the  
claim rests on a calibration time per unit that is programme-specific; the 33 万 per year  
figure quoted in the product analysis applies to a 10^5 units-per-year assumption and should  
not travel.

---

## 8. Conclusion

The pairwise sum is exact for two channels, optimistic by a fixed constant for three or more,  
and — the point of this paper — testable only by a record that joins measured deviations, the  
criterion in force, and the assembly outcome for one physical item. That join does not appear  
in the literature: each column does, the triple does not, and the missing column is the one  
owned by whoever paid for the rework. The paper gives the closed-form bounds, a screen that  
decides in advance whether a given system can produce a decisive record, and a frozen  
predicate for reading one. It does not yet have the record, and section 5 says so rather than  
supplying a plausible substitute.

---

## Data and code availability

Computed material: `outputs_replication/` (ring families, ratio sweeps, the R4  
configuration), `outputs_p3/` (public specification replay). Measured material: none yet;  
`analysis/paper/paper4/measured_slot.json` records the fields required and their current  
state.

## References

[1] Z. Zuo, "A decision rule without an operating characteristic: the pairwise sum in  
multi-channel boresight alignment," 2026, submitted.

[2] (calibration of multi-instrument payloads — to be completed from [1]'s reference list)

[3] (relative boresight estimation from image correspondences — idem)

[4] JCGM 106:2012, *Evaluation of measurement data — The role of uncertainty in conformity  
assessment*.

[5] ASME Y14.5-2018; ISO 1101:2017.
