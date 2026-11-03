"""Run the P3 replay on the LRO pointing and alignment specification.

Three questions, one output directory:

    C1  the two clauses in the document that can be checked against its own
        arithmetic (Table 9-3 pair margin, Table 8-3 containment convention)
    C2  one shared mounting interface instead of ten cubes: how much as-built
        spread a single shim can rescue, and where the pairwise table stops
        being a check at all
    C3  the production view -- 3 sigma as-built errors, the convention the
        document itself declares ("3 sigma or worst case allocations")

Run with ``PYTHONPATH=src`` and the pinned interpreter.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import time

import numpy as np

from rpy_polar_synth.p3_replay import (
    blind_band,
    disk_feasible,
    iis_disks,
    load_allocations,
    lola_nac,
    nac_pair,
    qualification,
    rescue_curve,
    simulate,
)
from rpy_polar_synth.replication import feasible as feasible_sphere
from rpy_polar_synth.replication import unit

# Kept local on purpose: importing it from safety_scenarios dragged in the whole
# pointing-prototype chain (branch_scale, cone_keepout) that this script does not
# use, and a trimmed checkout that ships only the replay solver failed on it.
DEG = np.pi / 180.0  # degrees to radians

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs_p3"


def write_csv(name: str, rows: list[dict]) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(OUT / name, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def to_sphere(delta_arcsec: np.ndarray) -> np.ndarray:
    """Tangent-plane offsets in arc-seconds -> unit vectors about +z."""
    d = np.atleast_2d(np.asarray(delta_arcsec, dtype=float))
    pole = np.array([0.0, 0.0, 1.0])
    out = [unit(pole + np.tan((p[0] / 3600.0) * DEG) * np.array([1.0, 0.0, 0.0])
                + np.tan((p[1] / 3600.0) * DEG) * np.array([0.0, 1.0, 0.0]))
           for p in d]
    return np.asarray(out)


def crosscheck(n_draw: int = 300, seed: int = 9) -> dict:
    """Planar exact test vs the spherical one from section 9.16.

    The replay works in the tangent plane because 300 arc-seconds is 0.08 deg;
    that approximation has to be checked, not assumed.  Two independent code
    paths, one question, any disagreement reported rather than hidden.
    """
    rng = np.random.default_rng(seed)
    A = np.array([300.0] * 4)
    disagree = 0
    for _ in range(n_draw):
        d = rng.normal(0.0, 160.0, size=(4, 2))
        if disk_feasible(d, A)["feasible"] != feasible_sphere(
                to_sphere(d), A / 3600.0)["feasible"]:
            disagree += 1
    return {"n_draw": n_draw, "disagreements": disagree,
            "note": "planar vs spherical common-point test"}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    t0 = time.perf_counter()
    table = load_allocations()
    names = table["names"]
    A = table["alloc_arcsec"]
    summary: dict = {"source": {
        "document": "LRO Pointing and Alignment Specification 431-SPEC-000113 rev A",
        "public": True,
        "units": "arc-seconds, per axis, half-cone",
    }}

    # ---- C1: the two clauses that can be checked against the document -------
    summary["C1_pair"] = nac_pair()
    summary["C1_containment"] = lola_nac()

    # ---- the table itself ---------------------------------------------------
    deck = [i for i, n in enumerate(names) if n != "LR-telescope"]
    write_csv("lro_channels.csv", [
        {"channel": n,
         "allocation_arcsec": float(A[i]),
         "section": table["sections"][i],
         "on_deck": "yes" if n != "LR-telescope" else "no",
         "note": table["notes"][i]}
        for i, n in enumerate(names)])

    # a deck that is fine on its own but breaks when the laser ranging telescope
    # -- which the document mounts on the HGA bracket, not on the instrument
    # deck -- is counted in the same group
    rng = np.random.default_rng(0)
    r = np.sqrt(rng.random((len(names), 1))) * 220.0
    th = rng.random((len(names), 1)) * 2.0 * np.pi
    demo = np.hstack([r * np.cos(th), r * np.sin(th)])
    iis = iis_disks(demo, A)
    summary["table"] = {
        "n_channels": len(names),
        "allocations_arcsec": A.tolist(),
        "min_arcsec": float(A.min()),
        "max_arcsec": float(A.max()),
        "iis_when_laser_ranging_displaced": iis,
        "iis_names": [names[k] for k in iis["subset"]],
        "deck_without_laser_feasible": disk_feasible(demo[deck], A[deck])["feasible"],
        "whole_group_feasible": disk_feasible(demo, A)["feasible"],
    }

    # ---- C2: worst case, one shim, spread as the only parameter -------------
    ratios = [0.6, 0.8, 1.0, 1.05, 1.10, 1.15, 1.25, 1.4, 1.6, 2.0, 2.5]
    curve = rescue_curve(A[deck], ratios, n_draw=2500)
    write_csv("rescue_curve.csv", curve)
    summary["C2_rescue"] = curve
    summary["C2_band"] = {"at_300": blind_band(300.0),
                          "at_500": blind_band(500.0),
                          "at_750": blind_band(750.0)}
    summary["C2_qualification"] = qualification(A[deck], 300.0)

    # ---- C3: production view -------------------------------------------------
    sig_rows = []
    for ratio in (1.2, 1.6, 2.0, 2.4, 3.0):
        r = simulate(A[deck] * (ratio / 3.0), sigma_arcsec=100.0,
                     n_draw=1200, seed=21)
        r["A_over_sigma"] = ratio
        sig_rows.append(r)
    write_csv("production_view.csv", sig_rows)
    summary["C3_production"] = sig_rows

    summary["crosscheck"] = crosscheck()
    summary["seconds"] = time.perf_counter() - t0
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False, default=str),
        encoding="utf-8")

    print(f"done in {summary['seconds']:.1f} s -> {OUT}")
    print("table: %d channels, %s..%s arcsec" % (len(names), A.min(), A.max()))
    print("C1 pair margin %.1f arcsec (rho %.3f)" %
          (summary["C1_pair"]["margin_arcsec"], summary["C1_pair"]["rho"]))
    print("C1 containment %s, overrun if built-limit %.0f arcsec" %
          (summary["C1_containment"]["verdict"],
           summary["C1_containment"]["overrun_if_built_arcsec"]))
    print("C1 IIS with laser ranging displaced: %s" %
          summary["table"]["iis_when_laser_ranging_displaced"])
    print("C2 rescue  T/A   pairwise  exact  missed")
    for r in curve:
        print("          %5.2f  %8.3f %6.3f %7.3f" %
              (r["T_over_Amin"], r["rate_pairwise"], r["rate_exact"],
               r["rate_missed_by_pairwise"]))
    print("C3 production  A/sigma  pairwise  exact   missed")
    for r in sig_rows:
        print("               %5.1f  %8.3f %6.3f %8.4f" %
              (r["A_over_sigma"], r["rate_pairwise"], r["rate_exact"],
               r["rate_missed_by_pairwise"]))
    print("crosscheck: %d/%d disagreements" %
          (summary["crosscheck"]["disagreements"], summary["crosscheck"]["n_draw"]))


if __name__ == "__main__":
    main()
