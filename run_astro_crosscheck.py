"""Section 9.12: cross-check the observability verdict against astroplan.

Four stages, each answering a different question:

1. ``ephemeris`` -- how far is the shipped Meeus path from astropy, in arcmin?
2. ``area``      -- does the area bracket contain an independently computed
                    area, and how big is the ephemeris gap next to it?
3. ``verdicts``  -- do the two boolean verdicts disagree, and where?
4. ``timing``    -- what does each implementation cost per verdict?

Usage:  python run_astro_crosscheck.py     (needs astropy + astroplan)
"""

from __future__ import annotations

import csv
import time
from pathlib import Path

import numpy as np

from rpy_polar_synth import astro_crosscheck as ac

OUT = Path("outputs_astro_crosscheck")

#: candidate nights across 2025; the actual instant is chosen per site by
#: ``night_epochs`` so that the site is dark and the Moon is up
DAYS = tuple(2460676.5 + 30.0 * k for k in range(12))


def write(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def pct(v: np.ndarray, q: float) -> float:
    return float(np.percentile(v, q))


def stage_ephemeris() -> None:
    t0 = time.time()
    rows = ac.scan_ephemeris(days=365, per_day=6)
    write(rows, OUT / "ac_ephemeris.csv")

    print(f"\n[1] ephemeris, {len(rows)} samples, {time.time() - t0:.1f}s")
    print("    quantity                median      p95       max   (arcmin)")
    for key, label in (
        ("err_sun_arcmin", "sun direction"),
        ("err_moon_arcmin", "moon direction"),
        ("err_alt_arcmin", "target altitude"),
    ):
        v = np.array([r[key] for r in rows])
        print(f"    {label:20s} {np.median(v):8.2f} {pct(v, 95):8.2f} {v.max():8.2f}")


def stage_area() -> list[dict]:
    rows: list[dict] = []
    t0 = time.time()
    for site in ac.SITES:
        for jd in ac.night_epochs(site, DAYS, n=2):
            # eps 0.1 deg so the bracket is ~4x the grid's own boundary band at
            # a 0.02 deg cell: the containment test must not be decided by the
            # test value's resolution
            out = ac.scan_area(site, jd, eps_deg=0.1, cell_deg=0.02)
            for tag in ("meeus", "astro"):
                r = out[tag]
                rows.append(
                    {
                        "site": site.name,
                        "jd": round(jd, 5),
                        "ephemeris": tag,
                        "area_lo_sr": round(r["lo"], 6),
                        "area_hi_sr": round(r["hi"], 6),
                        "width_sr": round(r["hi"] - r["lo"], 6),
                        "grid_area_sr": round(r["grid"], 6),
                        "grid_band_sr": round(r["grid_band"], 6),
                        "grid_cells": r["grid_cells"],
                        "nodes": r["nodes"],
                        "contains_grid": int(r["lo"] <= r["grid"] <= r["hi"]),
                    }
                )
    write(rows, OUT / "ac_area.csv")

    print(f"\n[2] area, {len(rows)} scenes, eps=0.1 deg, grid 0.02 deg, {time.time() - t0:.1f}s")
    print("    site      ephemeris  bracket lo..hi          width     grid     inside")
    for r in rows:
        print(
            f"    {r['site']:9s} {r['ephemeris']:6s} "
            f"[{r['area_lo_sr']:.4f},{r['area_hi_sr']:.4f}] "
            f"{r['width_sr']:.4f} {r['grid_area_sr']:.4f}   {bool(r['contains_grid'])}"
        )

    gaps, widths = [], []
    for i in range(0, len(rows), 2):
        m, a = rows[i], rows[i + 1]
        mid_m = 0.5 * (m["area_lo_sr"] + m["area_hi_sr"])
        mid_a = 0.5 * (a["area_lo_sr"] + a["area_hi_sr"])
        gaps.append(abs(mid_m - mid_a) / mid_m * 100.0)
        widths.append(0.5 * (m["width_sr"] + a["width_sr"]) / mid_m * 100.0)
    print(
        f"    ephemeris gap {np.median(gaps):.3f}% (median, max {max(gaps):.3f}%) "
        f"vs bracket width {np.median(widths):.3f}%"
    )
    return rows


def stage_verdicts() -> None:
    rows: list[dict] = []
    t0 = time.time()
    band = 1.1  # median Moon-ephemeris error, degrees (stage 1)
    for site in ac.SITES:
        for jd in ac.night_epochs(site, DAYS, n=2):
            res = ac.scan_verdicts(site, jd, hours=8.0, step_min=2.0)
            ap, ours, mg = res["astroplan"], res["ours"], res["margin_deg"]
            dis = ap != ours
            near = np.abs(mg) <= band
            rows.append(
                {
                    "site": site.name,
                    "jd": round(jd, 5),
                    "step_min": 2.0,
                    "n_eval": int(ap.size),
                    "disagree": int(dis.sum()),
                    "disagree_pct": round(100.0 * dis.mean(), 4),
                    "max_abs_margin_disagree_deg": round(
                        float(np.abs(mg[dis]).max()), 4
                    )
                    if dis.any()
                    else 0.0,
                    "min_abs_margin_agree_deg": round(
                        float(np.abs(mg[~dis]).min()), 4
                    )
                    if (~dis).any()
                    else float("nan"),
                    "n_within_moon_err": int(near.sum()),
                    "disagree_within_moon_err": int((dis & near).sum()),
                    "disagree_beyond_moon_err": int((dis & ~near).sum()),
                    "obs_frac_astroplan": round(float(ap.mean()), 4),
                    "obs_frac_ours": round(float(ours.mean()), 4),
                }
            )
            # one night per site is dumped per-sample for the figure
            if jd == ac.night_epochs(site, DAYS, n=2)[-1]:
                per = [
                    {
                        "site": site.name,
                        "jd": round(jd, 5),
                        "target": i,
                        "step": k,
                        "margin_deg": round(float(mg[i, k]), 4),
                        "verdict_ours": int(bool(ours[i, k])),
                        "verdict_astroplan": int(bool(ap[i, k])),
                        "disagree": int(bool(dis[i, k])),
                    }
                    for i in range(mg.shape[0])
                    for k in range(mg.shape[1])
                ]
                write(per, OUT / f"ac_margins_{site.name.lower()}.csv")
    write(rows, OUT / "ac_verdicts.csv")

    print(f"\n[3] verdicts, {time.time() - t0:.1f}s")
    for r in rows:
        print(
            f"    {r['site']:9s} n={r['n_eval']:5d} disagree {r['disagree']:4d} "
            f"({r['disagree_pct']:.2f}%) worst |margin| {r['max_abs_margin_disagree_deg']:.3f} deg "
            f"| within {band:.1f} deg: {r['disagree_within_moon_err']}/{r['n_within_moon_err']} "
            f"beyond: {r['disagree_beyond_moon_err']}"
        )


def stage_timing() -> None:
    rows = []
    for site in ac.SITES:
        tm = ac.timing(site, ac.night_epochs(site, DAYS, n=1)[0])
        rows.append({"site": site.name, **{k: round(v, 4) for k, v in tm.items()}})
    write(rows, OUT / "ac_timing.csv")
    print("\n[4] cost per verdict")
    for r in rows:
        print(
            f"    {r['site']:9s} astroplan {r['astroplan_us_per_eval']:6.2f} us   "
            f"ours {r['ours_us_per_eval']:5.2f} us   ratio {r['ratio']:.1f}x"
        )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    stage_ephemeris()
    stage_area()
    stage_verdicts()
    stage_timing()
    print(f"\ntotal {time.time() - t0:.1f}s -> {OUT}/")


if __name__ == "__main__":
    main()
