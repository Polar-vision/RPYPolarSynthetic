# A Decision Rule Without an Operating Characteristic

Reproducible code and data for the manuscript

> **"A Decision Rule Without an Operating Characteristic: The Pairwise Sum
> in Multi-Channel Boresight Alignment"**
> Zhengkang Zuo — Polar-vision Laboratory, College of Geoscience and
> Surveying Engineering, Taiyuan University of Technology.

This repository contains every script, table and figure behind the paper's
numerical claims, in a self-contained form. The manuscript source
(`analysis/paper/tim_manuscript.md` and `tim_supplement.md`), the five
figures, and the compiled PDFs (`analysis/paper/tim_manuscript.pdf` and
`tim_supplement.pdf`) are all included.

## What is in here

```
analysis/
  data/lro_alignment_allocations.csv   # ten-channel LRO allocation table,
                                       # clause numbers + verbatim quotes
  figures/                             # paper_fig1, p3_replay, paper_fig3,
                                       # ress_fig1, ress_fig2 (all @400 dpi)
  paper/tim_manuscript.md              # manuscript (IEEE TIM skeleton)
  paper/tim_manuscript.pdf             # compiled manuscript (16 pp)
  paper/tim_supplement.md              # one-page supplement (Fig. S-1)
  paper/tim_supplement.pdf             # compiled supplement (1 p)
outputs_p3/                            # P3 replay + regime map (10 tables)
outputs_ress/                          # error profiles, coverage, record
                                       # reachability, learning rate (11 tables)
src/rpy_polar_synth/
  p3_replay.py                         # planar disk-intersection solver,
                                       # certificates (support set / IIS)
  ress.py                              # reliability-facing measurement kit
  replication.py                       # independent spherical-cap solver,
                                       # used only for the 0/300 cross-check
run_p3_replay.py                       # Section V: the ten-channel replay
run_regime_map.py                      # Section VI-C/D: the regime map
run_ress.py                            # Sections VI-A/B, VII: the RESS kit
plot_p3_replay.py  plot_paper_fig1.py  # figures
plot_regime.py     plot_ress.py
```

## Reproducing

Dependencies: Python 3.10+ with `numpy` and `matplotlib`.

```bash
export PYTHONPATH=src        # Windows: set PYTHONPATH=src

python run_p3_replay.py      # ~70 s  -> outputs_p3/
python run_regime_map.py     #         -> outputs_p3/ (8000 draws/cell)
python run_ress.py           # ~95 s  -> outputs_ress/

python plot_p3_replay.py     # -> analysis/figures/p3_replay.png
python plot_paper_fig1.py    # -> analysis/figures/paper_fig1.png
python plot_regime.py        # -> analysis/figures/paper_fig3.png
python plot_ress.py          # -> analysis/figures/ress_fig1.png, ress_fig2.png
```

The runs are deterministic under fixed seeds (see each script). The
`outputs_*` directories already hold the committed results; re-running the
scripts reproduces them bit-for-bit.

## Key numbers, and where they come from

| Claim | Script | Evidence |
|---|---|---|
| LRO Table 9-3 `1''` margin reproduced exactly (n=2) | `run_p3_replay.py` | `outputs_p3/lro_channels.csv` |
| LOLA-into-NAC returned undecided, `1519''` between readings | `run_p3_replay.py` | `outputs_p3/production_view.csv` |
| IIS = {LAMP, laser-ranging telescope} | `run_p3_replay.py` | replay summary |
| 0/1200 misses at the 3-sigma convention | `run_p3_replay.py` | `outputs_p3/summary.json` |
| Worst disagreement 3.3 % at T/A = 1.25 | `run_p3_replay.py` | replay summary |
| Regime peak 2.61 % (n=9, A/σ=1.8); per-channel miss ≡ 0 | `run_regime_map.py` | `outputs_p3/regime_grid.csv` |
| Detection coverage 0.92–0.997 vs 1.000; false-alarm 0 vs 0.22–0.87 | `run_ress.py` | `outputs_ress/coverage.csv` |
| Record reachability 2.7e-5; tangent at r*=A | `run_ress.py` | `outputs_ress/record.csv`, `box_shares.csv` |
| p = 3.3 % needs 48 units to observe once | `run_ress.py` | `outputs_ress/economics.csv` |
| 2/√3 − 1 = 15.47 % guaranteed threshold (Proposition 3) | closed form | — |

## Notes

- `replication.py` implements the independent spherical-cap solver used only
  to cross-check the planar solver; the paper reports "no disagreement on 300
  random instances". The degree-to-radian constant is defined locally so the
  three modules have no dependency outside this package.
- The public specification replayed is NASA GSFC *LRO Pointing and Alignment
  Specification*, 431-SPEC-000113 Rev. A (6 Apr 2007). The allocation table
  with clause numbers and verbatim quotes is in
  `analysis/data/lro_alignment_allocations.csv`.
