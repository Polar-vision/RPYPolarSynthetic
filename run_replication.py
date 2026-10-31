"""Run the replication study.

Four questions, one output directory:

    R1  does the 13.4% window survive when the channels are not identical?
    R2  how often is a pairwise tolerance table optimistic, and by how much?
    R3  does single-linkage setup grouping produce plans that cannot be run?
    R4  a worked three-sensor bracket, with the numbers a review would see.

Everything numerical is written to ``outputs_replication/``; the summary holds
the numbers quoted in ``analysis/v0.9.16-replication.md`` so the two cannot
drift apart.

Run with ``PYTHONPATH=src`` and the pinned interpreter.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import time

import numpy as np

from rpy_polar_synth.replication import (
    adas_case,
    audit_part,
    min_cap_bruteforce,
    optimism_factor,
    pairwise_radius,
    part_rate,
    pocket_part,
    random_suite,
    ring_unequal,
    unit,
    _ang,
)
from rpy_polar_synth.safety_scenarios import DEG

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs_replication"


def write_csv(name: str, rows: list[dict]) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(OUT / name, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def ring_closed_form() -> list[dict]:
    """Equal caps on an n-gon ring: ``rho = 1 / sin(k*pi/n)``, k = floor(n/2)."""
    base = np.array([0.0, 0.0, 1.0])
    e1 = np.array([1.0, 0.0, 0.0])
    e2 = np.array([0.0, 1.0, 0.0])
    rows = []
    for n in range(3, 10):
        k = n // 2
        rho = 1.0 / np.sin(k * np.pi / n)
        ring = np.asarray([
            unit(np.cos(4.0 * DEG) * base
                 + np.sin(4.0 * DEG) * (np.cos(2 * np.pi * i / n) * e1
                                        + np.sin(2 * np.pi * i / n) * e2))
            for i in range(n)])
        num = min_cap_bruteforce(ring)["radius_deg"] / pairwise_radius(ring)
        rows.append({"n": n, "rho_closed": float(rho), "rho_numeric": float(num),
                     "abs_err": float(abs(rho - num))})
    return rows


def r1() -> list[dict]:
    kappas = (0.05, 0.1, 0.2, 0.35, 0.5, 0.7, 0.85, 0.9, 1.0, 1.05, 1.1,
              1.2, 1.35, 1.5, 2.0, 3.0)
    return ring_unequal(kappas=kappas)


def r2(ns=(3, 4, 5, 6, 8, 10, 12, 16), per: int = 120,
       spread_deg: float = 2.0, seed: int = 20261031) -> tuple[list[dict], list[dict]]:
    rng = np.random.default_rng(seed)
    rows, agg = [], []
    for n in ns:
        ratios, flats = [], []
        for _ in range(per):
            C = random_suite(n, spread_deg, rng)
            if len(C) < n:
                continue
            o = optimism_factor(C)
            # flatness: second singular value of the tangent projection, so a
            # collinear cloud (which is where the table is exact) is ~0
            m = unit(C.mean(axis=0))
            tmp = np.array([1.0, 0.0, 0.0]) if abs(m[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
            e1 = unit(np.cross(tmp, m))
            e2 = np.cross(m, e1)
            P = np.stack([C @ e1, C @ e2], axis=1)
            P = P - P.mean(axis=0)
            sv = np.linalg.svd(P, compute_uv=False)
            flat = float(sv[1] / sv[0]) if sv[0] > 0 else 0.0
            ratios.append(o["rho"])
            flats.append(flat)
            rows.append({"n": n, "rho": o["rho"], "exact_deg": o["exact_deg"],
                         "pairwise_deg": o["pairwise_deg"],
                         "flatness": flat})
        a = np.asarray(ratios)
        agg.append({
            "n": n,
            "count": len(a),
            "rho_median": float(np.median(a)),
            "rho_p90": float(np.percentile(a, 90)),
            "rho_max": float(a.max()),
            "frac_over_1pct": float(np.mean(a >= 1.01)),
            "frac_over_5pct": float(np.mean(a >= 1.05)),
            "frac_over_10pct": float(np.mean(a >= 1.10)),
            "flatness_median": float(np.median(flats)),
        })
    return rows, agg


def r3(reach_deg: float = 25.0, seps=None, per_rate: int = 80) -> tuple[list[dict], list[dict]]:
    """Sweep the pocket radius, then measure the rate on scattered parts."""
    if seps is None:
        seps = [round(reach_deg * f, 2) for f in
                (0.60, 0.72, 0.84, 0.90, 0.96, 1.00, 1.04, 1.12, 1.20, 1.24,
                 1.28, 1.32, 1.40, 1.50)]
    rows, agg = [], []
    for a in seps:
        part = pocket_part(sep_deg=a, reach_deg=reach_deg,
                           rng=np.random.default_rng(4))
        rows.append({"sep_deg": a, "ratio": a / reach_deg, **audit_part(part)})
    agg.append({"kind": "scattered", **part_rate(n_parts=per_rate,
                                                reach_deg=reach_deg)})
    return rows, agg


def timing(rows_n=(3, 6, 12, 24)) -> list[dict]:
    """Cost of an exact verdict as the channel count grows.

    The enumeration is O(n^4) in the worst case, so the repeat count is scaled
    down with n rather than letting one data point dominate the run.
    """
    rng = np.random.default_rng(99)
    out = []
    for n in rows_n:
        C = random_suite(n, 3.0, rng)
        reps = max(3, 400 // n)
        t0 = time.perf_counter()
        for _ in range(reps):
            min_cap_bruteforce(C)
        dt = (time.perf_counter() - t0) / reps
        out.append({"n": n, "bruteforce_ms": dt * 1e3, "reps": reps})
    return out


def main() -> None:
    OUT.mkdir(exist_ok=True)
    summary: dict[str, object] = {}

    t0 = time.perf_counter()
    r0 = ring_closed_form()
    write_csv("r0_ring_closed_form.csv", r0)
    summary["R0"] = {"max_abs_err": max(r["abs_err"] for r in r0),
                     "rows": r0}

    r1_rows = r1()
    write_csv("r1_tolerance_imbalance.csv", r1_rows)
    peak = max(r1_rows, key=lambda r: r["window_frac"])
    summary["R1"] = {
        "peak_kappa": peak["kappa"],
        "peak_window_frac": peak["window_frac"],
        "window_at_kappa_1": [r for r in r1_rows if r["kappa"] == 1.0][0]["window_frac"],
        "window_at_kappa_0p5": [r for r in r1_rows if r["kappa"] == 0.5][0]["window_frac"],
        "window_at_kappa_2": [r for r in r1_rows if r["kappa"] == 2.0][0]["window_frac"],
        "rows": r1_rows,
    }

    r2_rows, r2_agg = r2()
    write_csv("r2_random_suites.csv", r2_rows)
    write_csv("r2_by_n.csv", r2_agg)
    summary["R2"] = {
        "instances": len(r2_rows),
        "by_n": r2_agg,
        "frac_over_5pct_all": float(np.mean([r["rho"] >= 1.05 for r in r2_rows])),
        "median_rho_all": float(np.median([r["rho"] for r in r2_rows])),
    }

    r3_rows, r3_agg = r3()
    write_csv("r3_setup_grouping.csv", r3_rows)
    write_csv("r3_summary.csv", r3_agg)
    bad = [r for r in r3_rows if r["phantom_cost"] > 0]
    summary["R3"] = {
        "sweep": r3_rows,
        "scattered": r3_agg[0],
        "phantom_window_ratio": [min(r["ratio"] for r in bad),
                                 max(r["ratio"] for r in bad)] if bad else [],
        "max_missing_setups": max(r["phantom_cost"] for r in r3_rows),
    }

    summary["R4"] = adas_case()

    tm = timing()
    write_csv("timing.csv", tm)
    summary["timing"] = tm

    summary["seconds"] = time.perf_counter() - t0
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False, default=str),
        encoding="utf-8")

    print(f"done in {summary['seconds']:.1f} s -> {OUT}")
    print("R1 peak window %.4f at kappa %.2f" %
          (summary["R1"]["peak_window_frac"], summary["R1"]["peak_kappa"]))
    print("R2 median rho %.4f, frac>=5%% %.3f" %
          (summary["R2"]["median_rho_all"], summary["R2"]["frac_over_5pct_all"]))
    print("R3 phantom window ratio %s, max missing setups %d"
          % (summary["R3"]["phantom_window_ratio"],
             summary["R3"]["max_missing_setups"]))
    print("R3 scattered: %.0f%% of parts, mean %.2f setups missing"
          % (100 * r3_agg[0]["rate"], r3_agg[0]["mean_missing_setups"]))
    print("R4 pairwise=%s exact=%s shortfall=%.3f deg"
          % (summary["R4"]["pairwise_verdict"], summary["R4"]["exact_verdict"],
             summary["R4"]["shortfall_deg"]))


if __name__ == "__main__":
    main()
