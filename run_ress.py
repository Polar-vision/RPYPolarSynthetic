"""The measurements a reliability journal asks for, on the alignment table.

Four questions, four outputs:

``gate_profile.csv``   false accept and false reject for both criteria in use,
                       with Wilson intervals, over channel count and margin
``shortfall.csv``      coverage of the pairwise test against the depth of the
                       shortfall, next to Jung's 15.47% bound on that depth
``record.csv``         what share of the design box a build record can occupy,
                       and the equilateral family that straddles the boundary
``economics.csv``      how many units must fly before a miss could be seen, and
                       how expensive a late discovery must be to justify analysis
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import numpy as np

from rpy_polar_synth.p3_replay import load_allocations
from rpy_polar_synth.ress import (
    JUNG,
    box_shares,
    SHORTFALL_DEPTH,
    common_mode_check,
    conforming_share,
    coverage_profile,
    distribution_check,
    evaluation_cost,
    gate_profile,
    learning_units,
    record_bands,
    required_consequence_ratio,
    shortfall_profile,
)

OUT = Path("outputs_ress")
OUT.mkdir(exist_ok=True)

N_LIST = (3, 5, 9)
RATIO_LIST = (1.0, 1.2, 1.5, 1.8, 2.0, 2.4, 3.0)
A_UNIT = 100.0


def write_csv(name: str, rows: list[dict]) -> None:
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(OUT / name, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    t0 = time.perf_counter()
    summary: dict = {"JUNG": JUNG, "shortfall_depth": SHORTFALL_DEPTH,
                     "A_unit_arcsec": A_UNIT}

    # --- 1. error profile ---------------------------------------------------
    prof = []
    print("gate profile")
    for n in N_LIST:
        A = np.full(n, A_UNIT)
        for ratio in RATIO_LIST:
            p = gate_profile(A, A_UNIT / ratio, n_draw=8000, seed=101 + n,
                             audit=150)
            prof.append(p)
            print("  n=%d A/s=%.1f  faP=%.3f frP=%.3f | faW=%.4f frW=%.4f | "
                  "condW=%.3f waiv_unalign=%.3f"
                  % (n, ratio, p["fa_P"], p["fr_P"], p["fa_W"], p["fr_W"],
                     p["cond_accept_W"], p["waiver_unalignable"]))
    write_csv("gate_profile.csv", prof)
    summary["gate_profile"] = prof

    # --- 2. coverage, and the depth of the blind spot -----------------------
    cov = []
    print("coverage")
    for n in (5, 9):
        A = np.full(n, A_UNIT)
        for ratio in (1.2, 1.5, 2.0, 2.4):
            c = coverage_profile(A, A_UNIT / ratio, n_draw=2500, seed=203 + n)
            cov.append(c)
            print("  n=%d A/s=%.1f  DC_P=%.3f SP_P=%.3f | DC_W=%.3f SP_W=%.4f"
                  % (n, ratio, c["dc_P"], c["sp_P"], c["dc_W"], c["sp_W"]))
    write_csv("coverage.csv", cov)
    summary["coverage"] = cov

    short = []
    print("shortfall")
    for n, ratio in ((3, 1.5), (5, 1.5), (9, 1.5), (9, 2.0)):
        rows = shortfall_profile(np.full(n, A_UNIT), A_UNIT / ratio,
                                 n_draw=2500, n_audit=500, seed=307)
        short.extend(rows)
        tail = rows[-1]
        print("  n=%d A/s=%.1f  worst miss at %.4f of the allocation (bound %.4f)"
              % (n, ratio, tail["max_shortfall_among_misses"], SHORTFALL_DEPTH))
    write_csv("shortfall.csv", short)
    summary["shortfall"] = short

    # --- 3. what a record can occupy ---------------------------------------
    share = []
    print("conforming share of the box")
    for n in (3, 5, 10):
        for ratio in (1.2, 1.5, 2.0, 2.4, 3.0):
            s = conforming_share(np.full(n, ratio * A_UNIT), A_UNIT, 3.0)
            share.append(s)
            print("  n=%2d A/s=%.1f  analytic=%.3e  mc=%.3e"
                  % (n, ratio, s["analytic_share"], s["mc_share"]))
    write_csv("conforming.csv", share)
    summary["conforming"] = share

    box = []
    print("alignable vs visible, same box")
    for n, ratio in ((5, 1.5), (10, 2.0), (10, 2.4)):
        b = box_shares(np.full(n, ratio * A_UNIT), A_UNIT, 3.0, 6000, 505)
        box.append(b)
        print("  n=%2d A/s=%.1f  alignable=%.4f  record sees=%.2e  ratio=%.2e"
              % (n, ratio, b["feasible_share"], b["conforming_share"], b["ratio"]))
    write_csv("box_shares.csv", box)
    summary["box_shares"] = box

    bands = record_bands(A_UNIT)
    write_csv("record.csv", bands)
    summary["record_bands"] = bands
    print("record boundary:")
    for b in bands:
        print("  r/A=%.2f  P=%s W=%s E=%s" % (b["r_over_A"], b["per_channel_ok"],
                                              b["pairwise_ok"], b["exact_ok"]))

    # --- 4. robustness ------------------------------------------------------
    dist = distribution_check(np.full(9, A_UNIT), A_UNIT / 1.5, n_draw=3000,
                              seed=401)
    write_csv("distribution.csv", dist)
    summary["distribution"] = dist
    print("distribution (n=9, A/sigma=1.5)")
    for d in dist:
        print("  %-7s miss=%.4f  cond_accept=%.3f" % (d["dist"], d["fa_W"],
                                                      d["cond_accept_W"]))

    cm = common_mode_check(np.full(5, A_UNIT), A_UNIT / 1.5,
                           [0.36 * A_UNIT, -0.24 * A_UNIT],
                           n_draw=600, seed=409)
    summary["common_mode"] = cm
    print("common mode: %s" % cm)

    # --- the replayed specification's own deck ------------------------------
    tbl = load_allocations()
    names, A_all = tbl["names"], tbl["alloc_arcsec"]
    deck = [i for i, nm in enumerate(names) if nm != "LR-telescope"]
    A_deck = A_all[deck]
    lro = []
    for sigma in (100.0, 150.0):
        p = gate_profile(A_deck, sigma, n_draw=12000, seed=601, audit=120)
        p["case"] = "LRO deck, 9 channels"
        lro.append(p)
        print("LRO deck sigma=%.0f  faW=%d/12000  frW=%.4f  faP=%.4f  "
              "waiv=%.3f unalign=%.3f"
              % (sigma, round(p["fa_W"] * 12000), p["fr_W"], p["fa_P"],
                 p["waiver_rate"], p["waiver_unalignable"]))
    write_csv("lro_deck.csv", lro)
    summary["lro_deck"] = lro

    # --- 5. learning and economics -----------------------------------------
    miss_grid = [0.001, 0.003, 0.01, 0.02, 0.033]
    econ = learning_units(miss_grid, 0.8)
    econ2 = required_consequence_ratio(miss_grid)
    for e, r in zip(econ, econ2):
        e.update({k: v for k, v in r.items() if k != "miss_rate"})
    write_csv("economics.csv", econ)
    summary["economics"] = econ
    print("learning units (80%):")
    for e in econ:
        print("  p=%.3f -> N=%.1f units, required dC/c_a=%.1f"
              % (e["miss_rate"], e["units"], e["required_ratio"]))

    cost = evaluation_cost(np.full(9, 300.0), n_rep=400)
    summary["evaluation_cost"] = cost
    print("cost per decision: exact %.3f ms, pairwise %.3f ms (ratio %.1f)"
          % (cost["exact_seconds"] * 1e3, cost["pairwise_seconds"] * 1e3,
             cost["ratio"]))

    summary["wall_seconds"] = time.perf_counter() - t0
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("done in %.1f s" % summary["wall_seconds"])


if __name__ == "__main__":
    main()
