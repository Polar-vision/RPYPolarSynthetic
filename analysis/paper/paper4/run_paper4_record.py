"""Fill the derived block of measured_slot.json from a real record.

Refuses to run while the record is PENDING. That refusal is the point: the
script exists so that no one ever has to type a verdict by hand, and so that
the manuscript cannot acquire a measured claim it did not earn.

Pure standard library, no numpy: the geometry is small and exact, and a tool
that runs on any machine is one that will still run when the record arrives.

Usage:
    python analysis/paper/paper4/run_paper4_record.py [--slot PATH] [--write]
"""

from __future__ import annotations

import argparse
import json
import math
from itertools import combinations
from pathlib import Path

DEFAULT_SLOT = Path(__file__).resolve().parent / "measured_slot.json"

REQUIRED = [
    ("record.measured_deviations.d_i", "per-channel deviation vectors, arcsec"),
    ("record.measured_deviations.frame_definition", "which frame the vectors live in"),
    ("record.measured_deviations.instrument_uncertainty_arcsec", "instrument uncertainty"),
    ("record.allocations.A_i", "per-channel allocations, arcsec"),
    ("record.review_at_the_time.criterion_used", "criterion actually in force"),
    ("record.outcome.first_assembly_passed", "the dependent variable"),
    ("_provenance.release_permission", "documented permission to report"),
]


# ---------------------------------------------------------------------------
# small geometry kit
# ---------------------------------------------------------------------------

def _dist(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


def _sub(p, q):
    return (p[0] - q[0], p[1] - q[1])


def _add(p, q):
    return (p[0] + q[0], p[1] + q[1])


def _scale(p, s):
    return (p[0] * s, p[1] * s)


# ---------------------------------------------------------------------------
# the three tests, implemented twice each
# ---------------------------------------------------------------------------

def pairwise_ok(delta, A) -> bool:
    """Every pair reconcilable within the sum of the two allocations."""
    for i, j in combinations(range(len(delta)), 2):
        if _dist(delta[i], delta[j]) > A[i] + A[j] + 1e-12:
            return False
    return True


def per_channel_ok(delta, A) -> bool:
    """Every channel inside its own allocation."""
    return all(math.hypot(*delta[i]) <= A[i] + 1e-12 for i in range(len(delta)))


def _candidate_points(delta, A):
    """Points where a common intersection, if it exists, must have a witness.

    Either one disk contains the intersection (its centre is a witness) or the
    intersection's boundary has a vertex, which is a crossing of two circles.
    """
    pts = list(delta)
    for i, j in combinations(range(len(delta)), 2):
        dvec = _sub(delta[j], delta[i])
        r = math.hypot(*dvec)
        if r < 1e-12:
            continue
        ai, aj = A[i], A[j]
        if r > ai + aj:
            continue
        a = (ai * ai - aj * aj + r * r) / (2.0 * r)
        h2 = ai * ai - a * a
        if h2 < 0.0:
            continue
        h = math.sqrt(h2)
        u = (dvec[0] / r, dvec[1] / r)
        base = _add(delta[i], _scale(u, a))
        perp = (-u[1], u[0])
        pts.append(_add(base, _scale(perp, h)))
        if h > 1e-12:
            pts.append(_add(base, _scale(perp, -h)))
    return pts


def exact_feasible(delta, A, tol=1e-9):
    """Is there a point x with |x - d_i| <= A_i for every i? Exact, no solver."""
    best = None
    for c in _candidate_points(delta, A):
        slack = min(A[i] - _dist(c, delta[i]) for i in range(len(delta)))
        if best is None or slack > best[0]:
            best = (slack, c)
    slack, centre = best
    return {"feasible": slack >= -tol, "centre": centre, "slack": slack}


def mec_enumeration(delta):
    """Smallest enclosing circle by enumerating 2-point and 3-point supports."""
    n = len(delta)
    if n == 1:
        return 0.0, [0]

    best_r, best_support = math.inf, []
    for i, j in combinations(range(n), 2):
        centre = _scale(_add(delta[i], delta[j]), 0.5)
        r = max(_dist(delta[k], centre) for k in range(n))
        if r < best_r - 1e-12:
            best_r, best_support = r, [i, j]

    for i, j, k in combinations(range(n), 3):
        a, b, c = delta[i], delta[j], delta[k]
        d = 2.0 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
        if abs(d) < 1e-15:
            continue
        a2 = a[0] * a[0] + a[1] * a[1]
        b2 = b[0] * b[0] + b[1] * b[1]
        c2 = c[0] * c[0] + c[1] * c[1]
        ux = (a2 * (b[1] - c[1]) + b2 * (c[1] - a[1]) + c2 * (a[1] - b[1])) / d
        uy = (a2 * (c[0] - b[0]) + b2 * (a[0] - c[0]) + c2 * (b[0] - a[0])) / d
        centre = (ux, uy)
        r = max(_dist(delta[k2], centre) for k2 in range(n))
        if r < best_r - 1e-12:
            best_r, best_support = r, [i, j, k]

    return best_r, sorted(best_support)


def mec_bisection(delta):
    """Same quantity by bisecting the exact uniform-radius feasibility test."""
    n = len(delta)
    lo = 0.0
    hi = max(_dist(delta[i], delta[0]) for i in range(n)) + 1.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if exact_feasible(delta, [mid] * n)["feasible"]:
            hi = mid
        else:
            lo = mid
    return hi


def min_uniform_loosening(delta, A):
    """Smallest t >= 0 such that every allocation A_i can be raised by t.

    This is the engineering gap: how much each channel would have to be given
    to make one common orientation reachable. It is a convex problem in t, so
    bisection on the exact test is exact. Note it is NOT r* - min(A): with
    unequal allocations those differ, and the minimum over x of
    max_i(|x - d_i| - A_i) does not sit at a candidate point, so the slack of
    exact_feasible cannot be read as the gap either.
    """
    if exact_feasible(delta, A)["feasible"]:
        return 0.0
    lo = 0.0
    hi = max(_dist(delta[i], delta[j])
             for i, j in combinations(range(len(delta)), 2)) + max(A)
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if exact_feasible(delta, [a + mid for a in A])["feasible"]:
            hi = mid
        else:
            lo = mid
    return hi


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def get(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", type=Path, default=DEFAULT_SLOT)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    slot = json.loads(args.slot.read_text(encoding="utf-8"))
    state = slot.get("status", {}).get("state")

    missing = [(p, why) for p, why in REQUIRED if get(slot, p) in (None, [], "")]
    if state != "FILLED" or missing:
        print(f"slot state: {state}")
        if missing:
            print("missing required fields:")
            for p, why in missing:
                print(f"  - {p:52s} {why}")
        print()
        print("REFUSING to derive. A record is not in hand with these fields empty,")
        print("and a derived verdict computed from a guess would be indistinguishable")
        print("from a fabricated one. See README.md in this folder.")
        return 2

    rec = slot["record"]
    A = [float(x) for x in rec["allocations"]["A_i"]]
    delta = [(float(p[0]), float(p[1])) for p in rec["measured_deviations"]["d_i"]]
    if len(delta) != len(A):
        print(f"shape mismatch: {len(delta)} deviations vs {len(A)} allocations")
        return 3

    # The criterion of column C is the pairwise sum and nothing else: the table
    # asks that every pair lie within the sum of the two allocations. It does
    # not ask that each channel sit inside its own allocation relative to a fixed
    # datum, because the datum itself is what the exact test is free to choose.
    # Adding per-channel here would make every disagreement disappear.
    v_pair = pairwise_ok(delta, A)
    feas = exact_feasible(delta, A)
    v_exact = bool(feas["feasible"])

    r_enum, support = mec_enumeration(delta)
    r_bis = mec_bisection(delta)
    consistency = abs(r_enum - r_bis)

    a_min = min(A)
    # The gap is the uniform loosening that would make the family feasible.
    shortfall = min_uniform_loosening(delta, A)

    decisive = bool(v_pair and not v_exact)
    first_pass = rec["outcome"]["first_assembly_passed"]
    confirmatory = bool(decisive and first_pass is False)

    derived = {
        "r_star_arcsec": round(r_enum, 6),
        "support_set": [int(s) for s in support],
        "pairwise_verdict": "PASS" if v_pair else "FAIL",
        "exact_verdict": "PASS" if v_exact else "FAIL",
        "decisive": decisive,
        "confirmatory_of_claim": confirmatory,
        "shortfall_arcsec": round(shortfall, 6),
        "shortfall_over_Amin_frac": round(shortfall / a_min, 6),
        "r_star_minus_Amin_arcsec": round(r_enum - a_min, 6),
        # slack over the candidate set only; it is a lower bound on the true
        # optimum and is reported for cross-checking, never as the gap
        "slack_at_best_candidate_arcsec": round(feas["slack"], 6),
        "solver_agreement_arcsec": round(consistency, 9),
    }

    print(json.dumps(derived, indent=2))
    print()
    print(f"solver cross-check: enumeration {r_enum:.6f} vs bisection {r_bis:.6f} "
          f"-> {consistency:.2e} arcsec")
    if consistency > 1e-5:
        print("DISAGREEMENT above 1e-5 arcsec: emit UNDECIDED, do not report a verdict.")
        return 4

    unc = float(rec["measured_deviations"]["instrument_uncertainty_arcsec"])
    band = 80.3848 * a_min / 300.0
    print(f"instrument uncertainty {unc:.3f} arcsec vs scaled band {band:.1f} arcsec")
    if unc > 0.25 * band:
        print("WARNING: uncertainty exceeds a quarter of the band. The record may be")
        print("indecisive for metrological rather than geometric reasons; state this")
        print("in section 5.2 rather than reporting a verdict.")

    if not rec["review_at_the_time"]["criterion_used"] == "pairwise_sum":
        print()
        print("NOTE: the criterion in force was not reported as pairwise_sum. The")
        print("decisive predicate as frozen does not apply; report under section 6")
        print("row 4 or add a row, do not bend the definition.")

    if args.write:
        rec["derived"] = derived
        st = slot.setdefault("status", {})
        st["records_in_hand"] = max(int(st.get("records_in_hand") or 0), 1)
        args.slot.write_text(json.dumps(slot, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
        print(f"\nwrote derived block to {args.slot}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
