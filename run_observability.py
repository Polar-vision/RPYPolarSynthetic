"""Scene-five validation: ground-based observability as a region-enumeration task.

Answers three questions with numbers.

1. Does the branching enumeration agree with brute-force sampling on the region,
   and what does it add?  (area bracket, connected components, boundaries)
2. Is the sun constraint ever active for a night-time optical site?  (It is not:
   below the horizon by 18 deg the sun cone lies entirely under the elevation
   floor, so the "three keep-outs" story is wrong and the report has to say so.)
3. What does the completeness buy in practice -- and how does the cost scale?
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import rpy_polar_synth.observability as ob  # noqa: E402

OUT = ROOT / "outputs_observability"
DEG = np.pi / 180.0

SITES = {
    "FAST": ob.Site("FAST (Guizhou)", 25.653, 106.856, 1100.0),
    "Lijiang": ob.Site("Lijiang (Yunnan)", 26.695, 100.030, 3193.0),
}


def sun_redundant(scene: ob.ObservabilityScene, h_min_deg: float, sun_beta_deg: float) -> bool:
    """True when the sun cone cannot touch the elevation-limited sky at all.

    Minimum angular distance from any direction above the floor to the sun is
    max(0, h_min - alt_sun), so the constraint is vacuous iff that clears beta.
    """
    return (h_min_deg - np.rad2deg(scene.sun_alt)) >= sun_beta_deg


def write(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


# --------------------------------------------------------------------------


def accuracy_vs_cost() -> list[dict]:
    """Same region, two methods, sweeping resolution."""
    site = SITES["FAST"]
    jd = ob._julian_day(2026, 10, 30, 2.0)
    scene = ob.build_scene(site, jd, h_min_deg=5.0, sun_beta_deg=30.0, moon_beta_deg=30.0)

    # Reference.  Grid sampling cannot serve as one: its error is one-sided
    # (every cell whose centre is feasible is counted whole), so even a 0.02 deg
    # grid overshoots by ~0.03% and would flatter the branching mid-point.
    # Take the branching answer at eps = 0.005 instead; the bracket is monotone
    # in eps, so this is the best available numerical stand-in for the truth.
    ref_res = ob.enumerate_region(scene, eps_deg=0.005)
    ref_area = 0.5 * (ref_res.area + ref_res.area_hi)
    ref_mask, _ = ob.grid_reference(scene, 0.05)
    ref_labels = ob.label_components(ref_mask)
    print(
        f"reference: area {ref_area:.4f} sr from eps=0.005 "
        f"({ref_res.nodes} nodes), {ref_labels} component(s)"
    )

    rows: list[dict] = []
    for step in (2.0, 1.0, 0.5, 0.2, 0.1, 0.05, 0.02):
        t = time.time()
        m, a = ob.grid_reference(scene, step)
        dt_grid = time.time() - t
        rows.append(
            {
                "method": "grid",
                "resolution_deg": step,
                "area_sr": a,
                "rel_err_area": (a - ref_area) / ref_area,
                "components": ob.label_components(m),
                "nodes": m.size,
                "seconds": dt_grid,
            }
        )

    for eps in (2.0, 1.0, 0.5, 0.2, 0.1, 0.05, 0.02):
        t = time.time()
        r = ob.enumerate_region(scene, eps_deg=eps)
        dt = time.time() - t
        mid = 0.5 * (r.area + r.area_hi)
        rows.append(
            {
                "method": "branch",
                "resolution_deg": eps,
                "area_sr": mid,
                "rel_err_area": (mid - ref_area) / ref_area,
                "components": ob.label_components(ob.boxes_to_mask(r, 0.05)),
                "nodes": r.nodes,
                "seconds": dt,
            }
        )
        print(
            f"  branch eps {eps:5.2f}: area [{r.area:.4f},{r.area_hi:.4f}] "
            f"nodes {r.nodes:7d} {dt:6.2f}s"
        )

    write(rows, OUT / "accuracy_vs_cost.csv")
    return rows


def diurnal_sweep() -> list[dict]:
    """Walk a day at FAST and record when each constraint matters."""
    site = SITES["FAST"]
    h_min, beta_sun, beta_moon = 5.0, 30.0, 30.0
    rows: list[dict] = []
    for half_hour in range(0, 48):
        utc = half_hour * 0.5
        jd = ob._julian_day(2026, 10, 30, utc)
        scene = ob.build_scene(
            site, jd, h_min_deg=h_min, sun_beta_deg=beta_sun, moon_beta_deg=beta_moon
        )
        n_sun = ob.build_scene(
            site, jd, h_min_deg=h_min, sun_beta_deg=beta_sun,
            moon_beta_deg=beta_moon, include_moon=False,
        )
        n_none = ob.ObservabilityScene(
            site, jd,
            [ob.Constraint("cap", np.array([0.0, 0.0, 1.0]), (90.0 - h_min) * DEG)],
            scene.sun_alt, scene.moon_alt, scene.moon_illum,
        )
        r_none = ob.enumerate_region(n_none, eps_deg=0.5)
        r_sun = ob.enumerate_region(n_sun, eps_deg=0.5)
        r_all = ob.enumerate_region(scene, eps_deg=0.5)
        rows.append(
            {
                "utc_hour": utc,
                "sun_alt_deg": float(np.rad2deg(scene.sun_alt)),
                "moon_alt_deg": float(np.rad2deg(scene.moon_alt)),
                "moon_illum": round(scene.moon_illum, 3),
                "sun_redundant": sun_redundant(scene, h_min, beta_sun),
                "area_floor_only_sr": round(r_none.area, 4),
                "area_plus_sun_sr": round(r_sun.area, 4),
                "area_all_sr": round(r_all.area, 4),
                "sun_removes_sr": round(r_none.area - r_sun.area, 4),
                "moon_removes_sr": round(r_sun.area - r_all.area, 4),
                "components": ob.label_components(ob.boxes_to_mask(r_all, 0.1)),
                "nodes": r_all.nodes,
            }
        )
        if half_hour % 6 == 0:
            print(
                f"  UTC {utc:4.1f} sun {np.rad2deg(scene.sun_alt):7.1f} "
                f"moon {np.rad2deg(scene.moon_alt):7.1f} "
                f"area {r_all.area:6.3f} sun_removes {r_none.area - r_sun.area:6.3f} "
                f"moon_removes {r_sun.area - r_all.area:6.3f}"
            )
    write(rows, OUT / "diurnal_sweep.csv")
    return rows


def night_comparison() -> list[dict]:
    """Optical night at Lijiang versus radio daytime at FAST."""
    cases = [
        ("Lijiang 02:00 CST", "Lijiang", 18.0, 30.0, 35.0, 30.0),
        ("FAST 10:00 CST", "FAST", 2.0, 5.0, 30.0, 30.0),
        ("FAST 14:00 CST", "FAST", 6.0, 5.0, 30.0, 30.0),
    ]
    rows: list[dict] = []
    for label, key, utc, h_min, bs, bm in cases:
        site = SITES[key]
        jd = ob._julian_day(2026, 10, 30, utc)
        scene = ob.build_scene(site, jd, h_min_deg=h_min, sun_beta_deg=bs, moon_beta_deg=bm)
        t = time.time()
        r = ob.enumerate_region(scene, eps_deg=0.05)
        dt = time.time() - t
        comp = ob.label_components(ob.boxes_to_mask(r, 0.05))
        rows.append(
            {
                "case": label,
                "h_min_deg": h_min,
                "sun_beta_deg": bs,
                "moon_beta_deg": bm,
                "sun_alt_deg": round(float(np.rad2deg(scene.sun_alt)), 2),
                "moon_alt_deg": round(float(np.rad2deg(scene.moon_alt)), 2),
                "sun_redundant": sun_redundant(scene, h_min, bs),
                "area_lo_sr": round(r.area, 4),
                "area_hi_sr": round(r.area_hi, 4),
                "sky_fraction": round(r.area / (2.0 * np.pi), 4),
                "components": comp,
                "nodes": r.nodes,
                "seconds": round(dt, 2),
            }
        )
        print(
            f"  {label:20s} area [{r.area:.4f},{r.area_hi:.4f}] "
            f"({100*r.area/(2*np.pi):.1f}% of sky) comp {comp} {dt:.1f}s"
        )
    write(rows, OUT / "night_comparison.csv")
    return rows


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--only", default="all", choices=["all", "cost", "diurnal", "night"])
    args = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    if args.only in ("all", "night"):
        print("\n== observability, three cases ==")
        night_comparison()
    if args.only in ("all", "cost"):
        print("\n== accuracy versus cost ==")
        accuracy_vs_cost()
    if args.only in ("all", "diurnal"):
        print("\n== diurnal sweep at FAST ==")
        diurnal_sweep()


if __name__ == "__main__":
    main()
