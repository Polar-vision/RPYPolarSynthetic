"""Real-scale branch experiment of section 9.11: does the box count hold up?

Runs the level-wise vectorised branch over flight-software-sized keep-out
suites, three enclosures, and writes the tables the report quotes.
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from rpy_polar_synth import branch_scale as bs  # noqa: E402

OUT = ROOT / "outputs_branch_scale"


def write(name: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with (OUT / name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})
    print(f"  wrote {name} ({len(rows)} rows)")


def domain_area(extent_deg: float) -> float:
    return 2.0 * np.pi * (1.0 - np.cos(np.deg2rad(extent_deg)))


def mc_area(scene, extent_deg: float, n: int = 400_000, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    z = rng.uniform(np.cos(np.deg2rad(extent_deg)), 1.0, n)
    phi = rng.uniform(0.0, 2.0 * np.pi, n)
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    u = np.column_stack([r * np.cos(phi), r * np.sin(phi), z])
    ang = np.arccos(np.clip(u @ scene.suns.T, -1.0, 1.0))
    ok = (ang > scene.betas[None, :]).all(axis=1)
    return float(domain_area(extent_deg) * ok.mean())


def main() -> None:
    t_all = time.perf_counter()

    # ---- 0. enclosures: still conservative? still the same answer? --------
    print("[0] enclosure checks")
    checks = [{
        "check": "max_violation_rad",
        "lip": bs.check_bound("lip", n=400, samples=50),
        "ia": bs.check_bound("ia", n=400, samples=50),
        "tri": bs.check_bound("tri", n=400, samples=50),
        "note": "sampled points must never fall outside the enclosure",
    }]
    sc = bs.flight_suite(n_stars=200, pointing_tol_deg=60)
    ref = mc_area(sc, 60.0)
    checks[0]["mc_area_sr"] = ref
    for bd in ("lip", "ia", "tri"):
        r = bs.vectorised_branch(sc, eps_deg=0.1, extent_deg=60, bound=bd)
        checks[0][f"{bd}_area_sr"] = r.feasible_area_sr
    write("bs_checks.csv", checks)
    print(f"  MC feasible area {ref:.4f} sr; violation "
          f"{checks[0]['lip']:.1e}/{checks[0]['ia']:.1e}/{checks[0]['tri']:.1e}")

    # ---- 1. the three enclosures at the same instance --------------------
    print("[1] enclosure comparison (m=208, eps=0.1 deg)")
    rows = []
    total = domain_area(60.0)
    for bd in ("lip", "ia", "tri"):
        r = bs.vectorised_branch(sc, eps_deg=0.1, extent_deg=60, bound=bd)
        rows.append({
            "bound": bd, "nodes": r.nodes, "leaves_killed": r.leaves_killed,
            "m_eff": r.m_eff, "seconds": r.seconds, "depth": r.depth,
            "feasible_area_sr": r.feasible_area_sr,
            "certified_frac": r.killed_area_sr / total,
            "resolution_frac": r.resolution_area_sr / total,
            "feasible_frac": r.feasible_area_sr / total,
            "nodes_per_m_eff": r.nodes / max(r.m_eff, 1),
        })
        print(f"  {bd}: nodes {r.nodes}, m_eff {r.m_eff}, {r.seconds:.2f}s, "
              f"certified {100 * r.killed_area_sr / total:.1f}% of area")
    write("bs_bounds.csv", rows)

    # ---- 2. resolution --------------------------------------------------
    print("[2] resolution scan")
    for n_star in (0, 200):
        rr = bs.scan_resolution((1.0, 0.5, 0.25, 0.12, 0.06, 0.03, 0.02),
                                extent_deg=60.0, n_stars=n_star)
        write(f"bs_resolution_{n_star}stars.csv", rr)
        for r in rr:
            print(f"  eps {r['eps_deg']:>5}: nodes {r['nodes']:>8} depth {r['depth']:>2} "
                  f"{r['seconds']:.2f}s nodes*eps {r['nodes_times_eps']:.0f}")

    # ---- 3. extent ------------------------------------------------------
    print("[3] extent scan")
    re_ = bs.scan_extent((2.0, 5.0, 10.0, 20.0, 40.0, 60.0), eps_deg=0.05, n_stars=200)
    write("bs_extent.csv", re_)
    for r in re_:
        print(f"  extent {r['extent_deg']:>4}: nodes {r['nodes']:>7} m_eff {r['m_eff']:>3} "
              f"{r['seconds']:.2f}s")

    # ---- 4. suite size --------------------------------------------------
    print("[4] constraint-count scan")
    rc = bs.scan_constraint_count((0, 10, 25, 50, 100, 200, 400), eps_deg=0.05, extent_deg=60.0)
    write("bs_constraints.csv", rc)
    for r in rc:
        print(f"  m {r['m_total']:>4}: nodes {r['nodes']:>7} m_eff {r['m_eff']:>3} "
              f"{r['seconds']:.2f}s  {r['us_per_box_per_constraint']:.3f} us/box/con")

    # ---- 5. adversarial: interface length, not constraint count ----------
    print("[5] interface-length scans (separated vs merged)")
    ra = bs.scan_adversarial((2, 4, 8, 16, 32, 64), beta_deg=0.5, eps_deg=0.02,
                             extent_deg=30.0, merged=False)
    write("bs_separated.csv", ra)
    for r in ra:
        print(f"  separated k {r['k']:>3}: nodes {r['nodes']:>7} m_eff {r['m_eff']:>3} "
              f"{r['seconds']:.2f}s per-boundary {r['nodes_per_boundary']:.0f}")
    rm = bs.scan_adversarial((2, 4, 8, 16, 32, 64), beta_deg=0.5, eps_deg=0.02,
                             extent_deg=30.0, merged=True)
    write("bs_merged.csv", rm)
    for r in rm:
        print(f"  merged    k {r['k']:>3}: nodes {r['nodes']:>7} m_eff {r['m_eff']:>3} "
              f"{r['seconds']:.2f}s per-boundary {r['nodes_per_boundary']:.0f}")

    print(f"total {time.perf_counter() - t_all:.1f} s")


if __name__ == "__main__":
    main()
