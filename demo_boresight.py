"""Worked numbers for the product note (analysis/product-boresight.md).

The structure the product sells is one comparison:

    max over channels of angle(x*, c_i)  =  r*        (geometry, no tolerances)
    min over channels of theta_i                      (the specification)
    feasible  <=>  r* <= min theta_i

``r*`` does not depend on any tolerance, and the ``min`` does not depend on the
geometry, so the two sides of a design review separate cleanly.  Tightening a
tolerance can only shrink the feasible set -- a fact that surprises design
reviews, where "we are out of tolerance, tighten it" is the reflex.  The only
levers are to move the nominals (lowers ``r*``) or to relax the tightest
channel (raises the ``min``).

Two cases, computed with the same machinery as the study:

    1. an eight-channel payload: which three channels set ``r*``, and how far
       would they have to move to reach the tightest specification;
    2. the three-sensor bracket: the table passes, the truth does not, and the
       three repairs priced in degrees.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from rpy_polar_synth.replication import (
    adas_case,
    feasible,
    min_cap_bruteforce,
    pairwise_radius,
    unit,
)

ROOT = Path(__file__).resolve().parent
DEG = np.pi / 180.0


def payload_case() -> dict:
    """Eight channels on one bench: three tight, five loose."""
    specs = [
        ("star tracker A", 0.00, 0.00, 0.25),
        ("star tracker B", 0.30, 0.05, 0.25),
        ("laser terminal", 0.15, 0.29, 0.25),
        ("imager", -0.55, 0.62, 0.60),
        ("SWIR", 0.62, -0.58, 0.60),
        ("radiometer", -0.70, -0.66, 0.60),
        ("beacon", 0.10, -0.75, 0.60),
        ("coarse sun sensor", -0.20, 0.80, 0.60),
    ]
    names, C, th = [], [], []
    for nm, el, az, tol in specs:
        d = np.array([np.sin(az * DEG) * np.cos(el * DEG),
                      np.sin(el * DEG),
                      np.cos(az * DEG) * np.cos(el * DEG)])
        names.append(nm)
        C.append(unit(d))
        th.append(tol)
    return {"names": names, "C": np.asarray(C), "theta": np.asarray(th)}


def move_inward(C: np.ndarray, idx, delta_deg: float,
                target: np.ndarray | None = None) -> np.ndarray:
    """Move the listed channels ``delta`` degrees toward a common point.

    The target defaults to the centroid of the *whole* set: using the centroid
    of the moved channels themselves would be a no-op for a single channel,
    which silently turned a repair calculation into zero.
    """
    out = C.copy()
    cen = unit(C.mean(axis=0)) if target is None else unit(target)
    for i in idx:
        d = cen - C[i]
        d = d / np.linalg.norm(d)          # unit tangent direction, else the
        out[i] = unit(C[i] + np.tan(delta_deg * DEG) * d)   # step is scaled by
    return out                            # |cen - c_i| ~ 0.015 and vanishes


def main() -> None:
    payload = payload_case()
    C, th, names = payload["C"], payload["theta"], payload["names"]
    cap = min_cap_bruteforce(C)
    r_star, support = cap["radius_deg"], cap["support"]
    centre = cap["center"]
    feas = feasible(C, th)

    print("== eight-channel payload ==")
    print(f"r* (required by geometry) {r_star:.4f} deg, pinned by "
          f"{[names[i] for i in support]}")
    print(f"pairwise table would say  {pairwise_radius(C):.4f} deg "
          f"({pairwise_radius(C) / r_star - 1:+.1%})")
    print(f"tightest specification    {th.min():.4f} deg")
    print(f"verdict {feas['feasible']}, short by "
          f"{max(0.0, r_star - th.min()):.4f} deg")
    print()
    print("per channel: deficit against the uniform requirement r*")
    per = []
    for i, nm in enumerate(names):
        deficit = r_star - float(th[i])
        per.append({"channel": nm, "spec_deg": float(th[i]),
                    "deficit_deg": deficit, "in_support": i in support,
                    "angle_at_x_star_deg": float(np.degrees(
                        np.arccos(np.clip(C[i] @ centre, -1, 1))))})
        print(f"  {nm:20s} spec {th[i]:.2f}  deficit {deficit:+.3f}"
              f"{'   <- sets r*' if i in support else ''}")

    print()
    floor = pairwise_radius(C[[i for i in range(len(C)) if i not in support]])
    print(f"lever 1: move the three support channels inward; r* cannot go below")
    print(f"  {floor:.3f} deg, which is what the other five already demand")
    for d in (0.10, 0.20, 0.30, 0.50):
        r = min_cap_bruteforce(move_inward(C, support, d))["radius_deg"]
        print(f"  move {d:.2f} deg inward -> r* = {r:.3f} deg")
    print("lever 2: relax the three tight channels to r*")
    print(f"  star trackers and laser terminal -> {r_star:.3f} deg")

    adas = adas_case()
    print()
    print("== three-sensor bracket ==")
    print(f"  pairwise {adas['pairwise_radius_deg']:.3f} deg -> table says OK")
    print(f"  exact    {adas['exact_radius_deg']:.3f} deg -> needs "
          f"{adas['shortfall_deg']:.3f} deg more")
    Cb = np.asarray([unit(np.array([np.sin(az * DEG) * np.cos(el * DEG),
                                    np.sin(el * DEG),
                                    np.cos(az * DEG) * np.cos(el * DEG)]))
                     for el, az in ((0.50, 0.0), (-0.25, 0.433), (-0.25, -0.433))])
    tol = 0.45
    lo, hi = 0.0, 0.6
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if min_cap_bruteforce(move_inward(Cb, [0], mid))["radius_deg"] > tol:
            lo = mid
        else:
            hi = mid
    print(f"  repair A: tighten all three to {adas['exact_radius_deg']:.3f} deg")
    print(f"  repair B: re-aim the camera {hi:.3f} deg inward "
          f"(only if the boss has not been machined)")
    print(f"  repair C: accept {adas['shortfall_deg']:.3f} deg and calibrate "
          f"every unit")

    out = {"payload": {"r_star_deg": r_star,
                       "support": [names[i] for i in support],
                       "min_spec_deg": float(th.min()),
                       "per_channel": per,
                       "move_needed_deg": hi},
           "adas": adas}
    (ROOT / "outputs_replication" / "product_demo.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False, default=str),
        encoding="utf-8")


if __name__ == "__main__":
    main()
