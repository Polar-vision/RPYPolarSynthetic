# Paper 4: how to go from protocol draft to measured paper

This folder holds everything that separates the draft from a submittable measured paper.
There is exactly one thing in it: **the record**. Everything else is already done.

## The line this folder is built around

Paper 4's selling point is one sentence: *a table passed and the assembly did not*. That
sentence is either an observation or a fabrication, with nothing in between. A
plausible-looking synthetic value in section 5 is not a placeholder — it is the paper's
result, invented. So:

- `measured_slot.json` uses `null` for every unobtained value, and a validator refuses to
  let the manuscript proceed while `status.state == "PENDING"`.
- Section 4 of the draft is a **computed** illustration and says so three times. It is
  legitimate as an illustration. It may never be described as a build.
- The frozen predicates in `measured_slot.json` were written before any record exists. Do
  not edit them after seeing a record; that is the one action that would make the test
  circular.

## What the record has to contain

| Field | Why the paper dies without it |
|---|---|
| `measured_deviations.d_i` | the independent variable |
| `measured_deviations.frame_definition` | without a stated frame the vector is uninterpretable |
| `measured_deviations.instrument_uncertainty_arcsec` | the band is 80.4 arcsec at a 300 arcsec allocation; uncertainty must be well under it or the record is indecisive for metrological reasons |
| `review_at_the_time.criterion_used` | if this is `unknown`, the record cannot show the pairwise rule was in force, and the decisive claim collapses |
| `outcome.first_assembly_passed` | the dependent variable |
| `_provenance.*` | without a release, the record cannot be reported at all |

The field most often missing in practice is `review_at_the_time`. Programmes keep the
metrology log and keep the rework order; they rarely keep the wording of the check that was
applied. Ask for it at the same time as the deviations — once the review is over, the
wording is gone.

## The five-step replacement

1. **Obtain the record** under a written release (see `_provenance`).
2. **Fill `measured_slot.json`**: `record.*` fields, then `_provenance`, then set
   `status.state = "FILLED"` and `records_in_hand`.
3. **Run `run_paper4_record.py`** — computes `derived` (r*, support set, both verdicts,
   `decisive`, shortfall) and refuses to write if either verdict is inconsistent with an
   independent solver, in the same spirit as the dual-implementation rule of the companion
   project.
4. **Rewrite section 5** from the script's output. Delete the `STATUS: NOT EXECUTED` banner
   only at this point. Keep section 4 as it is and keep the word *synthetic* in its heading.
5. **Check section 6 against what was found.** Section 6 is already written for all four
   outcomes. If the record lands in a row that section 6 does not have, that is a finding
   about the framing and needs a paragraph of its own — not a quiet edit to the table.

## Where the record can come from

The realistic route is the same one as the product's P3 gate: enter a real alignment review
in a service capacity, and contract for the anonymised triple as part of the deliverable.
Public specifications cannot supply it — the public ten-channel table has been replayed and
lacks both the measured deviations and the outcome. This is recorded as a negative result in
section 5.3 of the draft rather than glossed over.

Target: **one** record makes the paper publishable as a measured test. **Twenty** make the
frequency claim available, which is a different and much better paper.

## What is already finished and does not depend on the record

- Section 3: $\rho=1/\sin(\pi/n)$, the 13.40 % / 15.47 % distinction, the 80.4 arcsec band,
  the direction-of-fix statement.
- Section 2.2: the screen (S1–S3).
- Section 2.3, 2.4 and section 6: the frozen predicates, the derivation of the three
  quantities, and the four-row interpretation table.
- Section 7.1: why the constants are exact and the frequency is not.

These are the parts a reviewer will test. They can be reviewed today.

## Validation of the script (done on 2026-11-01)

`run_paper4_record.py` was exercised on four analytic cases with known answers:

| Case | Known answer | Script | Pass |
|---|---|---|---|
| equilateral, side 0.866°, $A=0.45°$ (= `R4`) | $r^\star=1800$″, gap $=180$″, PASS/FAIL | $r^\star=1799.947$″, gap $=179.947$″, PASS/FAIL | ✅ |
| two channels, gap-free | pairwise **is** exact, gap $=0$ | PASS/PASS, gap $=0.000$ | ✅ |
| three channels, wide allocation | both PASS, gap $=0$ | PASS/PASS, gap $=0.000$ | ✅ |
| three channels, table already fails | FAIL/FAIL, not decisive | FAIL/FAIL, `decisive=false` | ✅ |

Two solvers (support enumeration vs bisection) agree to $3\times10^{-10}$ arcsec on the `R4`
case. The `R4` residual ($1799.947$ vs $1800$) is the rounding of $0.866°$ into arc-seconds,
not a solver error.

Two definitions were corrected during this validation and are now stated in section 2.4 of
the draft, because both are easy to get wrong in a way that silently destroys the paper:

1. The pairwise verdict must **not** include a per-channel test. Conjoining it with one makes
   the pairwise verdict fail wherever the exact verdict fails, and no decisive record can ever
   exist. The datum is what the exact test chooses.
2. The gap is the uniform loosening $t$, not $r^\star-\min_i A_i$. The two coincide only under
   equal allocations.
