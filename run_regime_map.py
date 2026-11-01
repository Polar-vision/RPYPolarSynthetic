"""Regime map for the pairwise rule: where can it disagree with the geometry?

Two sweeps, both cheap enough to run in one go.

``grid``          equal allocations, ``n`` channels, allocation expressed in
                  standard deviations of the as-built spread.  Reports the share
                  of the design box on which the pairwise table accepts and no
                  common point exists, next to the same share for the per-channel
                  check (which the theory says is identically zero).

``heterogeneity`` nine channels, tightest allocation fixed at ``1.5 sigma``,
                  allocations spread geometrically up to ``ratio`` times the
                  tightest.  Isolates the third screening question.

``round_trip``    the design-side statement: fix the worst pairwise separation,
                  ask what allocation the pairwise rule implies (``d/2``) and
                  what the geometry requires (``d/sqrt(3)``), and confirm the
                  ratio 2/sqrt(3) on an equilateral triple.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np

from rpy_polar_synth.p3_replay import (
    disk_feasible,
    pairwise_ok,
    per_channel_ok,
    simulate,
)

OUT = Path("outputs_p3")
OUT.mkdir(exist_ok=True)


def grid(n_list=(3, 4, 5, 9), ratio_list=(0.8, 1.0, 1.2, 1.5, 1.8, 2.0, 2.4, 3.0),
         n_draw: int = 8000, seed: int = 31) -> list[dict]:
    rows = []
    for n in n_list:
        A = np.full(n, 100.0)
        for r in ratio_list:
            s = simulate(A, sigma_arcsec=100.0 / r, n_draw=n_draw, seed=seed + n)
            # per-axis sigma is set so that A_min / sigma == r
            rows.append({
                "n": n,
                "A_over_sigma": r,
                "rate_pairwise": s["rate_pairwise"],
                "rate_exact": s["rate_exact"],
                "missed_by_pairwise": s["rate_missed_by_pairwise"],
                "missed_by_per_channel": s["rate_missed_by_per_channel"],
                "rate_per_channel": s["rate_per_channel"],
            })
            print("n=%d  A/s=%.2f  pair=%.3f exact=%.3f missed=%.4f per_missed=%.4f"
                  % (n, r, rows[-1]["rate_pairwise"], rows[-1]["rate_exact"],
                     rows[-1]["missed_by_pairwise"], rows[-1]["missed_by_per_channel"]))
    return rows


def heterogeneity(n: int = 9, ratio_list=(1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0),
                  A_min: float = 150.0, sigma: float = 100.0,
                  n_draw: int = 8000, seed: int = 71) -> list[dict]:
    """Nine allocations, geometrically spaced, tightest one held fixed."""
    rows = []
    for ratio in ratio_list:
        A = A_min * np.geomspace(1.0, ratio, n)
        s = simulate(A, sigma_arcsec=sigma, n_draw=n_draw, seed=seed)
        rows.append({
            "n": n,
            "A_max_over_A_min": float(ratio),
            "A_min_over_sigma": A_min / sigma,
            "rate_pairwise": s["rate_pairwise"],
            "rate_exact": s["rate_exact"],
            "missed_by_pairwise": s["rate_missed_by_pairwise"],
        })
        print("ratio=%5.1f  pair=%.3f exact=%.3f missed=%.4f"
              % (ratio, rows[-1]["rate_pairwise"], rows[-1]["rate_exact"],
                 rows[-1]["missed_by_pairwise"]))
    return rows


def round_trip(d_list=(480.0, 519.62, 540.0, 570.0, 599.0), A: float = 300.0) -> list[dict]:
    """Design side: what allocation does each rule imply for a worst-case spread d?"""
    rows = []
    for d in d_list:
        pts = np.array([[0.0, 0.0], [d, 0.0], [d / 2, -d * math.sqrt(3) / 2]])
        f = disk_feasible(pts, np.full(3, A))
        rows.append({
            "d_arcsec": d,
            "A_arcsec": A,
            "pairwise_ok": pairwise_ok(pts, np.full(3, A)),
            "exact_ok": f["feasible"],
            "A_required_exact": d / math.sqrt(3),
            "A_implied_by_pairwise": d / 2,
            "ratio": (d / math.sqrt(3)) / (d / 2),
        })
        print("d=%.2f  pair=%s exact=%s  A_needed=%.1f vs %.1f"
              % (d, rows[-1]["pairwise_ok"], rows[-1]["exact_ok"],
                 d / math.sqrt(3), d / 2))
    return rows


def identity_check(n_list=(3, 5, 9), n_draw: int = 2000, seed: int = 5) -> dict:
    """Conforming data must be accepted by all three checks.  Count violations."""
    rng = np.random.default_rng(seed)
    bad = 0
    total = 0
    for n in n_list:
        A = np.full(n, 300.0)
        for k in range(n_draw):
            d = rng.normal(0.0, 120.0, size=(n, 2))
            if per_channel_ok(d, A):
                total += 1
                if not disk_feasible(d, A)["feasible"] or not pairwise_ok(d, A):
                    bad += 1
    return {"conforming_draws": total, "violations": bad}


def main() -> None:
    summary = {}
    g = grid()
    h = heterogeneity()
    r = round_trip()
    summary["grid"] = g
    summary["heterogeneity"] = h
    summary["round_trip"] = r
    summary["identity_check"] = identity_check()

    with open(OUT / "regime_grid.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(g[0]))
        w.writeheader()
        w.writerows(g)
    with open(OUT / "regime_heterogeneity.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(h[0]))
        w.writeheader()
        w.writerows(h)
    with open(OUT / "regime_round_trip.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(r[0]))
        w.writeheader()
        w.writerows(r)

    path = OUT / "regime_summary.json"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        old.update(summary)
        summary = old
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nidentity check:", summary["identity_check"])
    peak = max(g, key=lambda x: x["missed_by_pairwise"])
    print("peak missed: n=%d A/s=%.2f -> %.4f" % (peak["n"], peak["A_over_sigma"],
                                                  peak["missed_by_pairwise"]))
    print("2/sqrt3 - 1 = %.6f" % (2 / math.sqrt(3) - 1))


if __name__ == "__main__":
    main()
