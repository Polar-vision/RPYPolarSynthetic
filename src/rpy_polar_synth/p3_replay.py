"""P3 replay: a real multi-channel payload specification, run through the tool.

The two earlier studies used numbers we chose.  This one does not.  The input is
the pointing and alignment specification of a flown NASA payload -- LRO,
document ``431-SPEC-000113`` revision A -- which allocates, per instrument, the
angle within which its boresight must be brought to the spacecraft reference:

    LROC-NAC-L/R, LROC-WAC, LOLA, LAMP   300 arc-sec per axis
    Diviner, CRaTER, LEND                500
    Mini-RF                              750
    Laser ranging telescope               36

Ten channels, one common reference, real numbers on every row.  The document is
public, so nothing needed redacting; what a partner table would add is the one
column that is *not* public -- the as-built deviation of each instrument -- and
that gap is the subject of the replay rather than a nuisance to be papered over.

**The question.**  The specification is written per instrument, and every clause
is satisfied by aligning each instrument on its own cube.  A cheaper mechanical
architecture is one common mounting interface: shim the deck once, and every
instrument moves together.  Does a single deck orientation exist that brings all
ten boresights inside their own allocations?

A shim supplies one vector ``x``; the residual of channel ``i`` is ``d_i - x``,
where ``d_i`` is the as-built deviation.  So the question is whether the disks
``|x - d_i| <= A_i`` share a point -- the planar form of the cap problem, exact
for allocations of a few arc-minutes.

**Three verdicts, and the reason they differ.**  Each page of the specification
checks one channel against its own allocation (``|d_i| <= A_i``).  The pairwise
form sums two allocations (``|d_i - d_j| <= A_i + A_j``), which is what the
per-instrument clauses imply and what a review walks through.  The exact form
asks for a common point.  Necessary, necessary, sufficient -- and the gap
between the second and the third is the 13.41% of section 9.16, now denominated
in arc-seconds of a real budget.

Functions:

    ``load_allocations``   read the CSV with provenance columns
    ``disk_feasible``      exact common-point test, candidate enumeration
    ``min_common_radius``  smallest uniform radius admitting a common point
    ``simulate``           the three verdicts over as-built draws
    ``blind_band``         the analytic window for n channels at one allocation
    ``price_of_one_shim``  how much every allocation must grow for one shim
    ``nac_pair``           the one clause in the document that sums, reproduced
    ``lola_nac``           a containment clause whose convention is unstated
"""

from __future__ import annotations

import csv
from itertools import combinations
from pathlib import Path

import numpy as np

__all__ = [
    "ARCSEC",
    "load_allocations",
    "disk_feasible",
    "min_common_radius",
    "per_channel_ok",
    "pairwise_ok",
    "simulate",
    "blind_band",
    "price_of_one_shim",
    "rescue_curve",
    "qualification",
    "nac_pair",
    "lola_nac",
    "iis_disks",
]

ARCSEC = 1.0  # every length in this module is arc-seconds unless stated


# ---------------------------------------------------------------------------
# input
# ---------------------------------------------------------------------------

def load_allocations(path: str | Path | None = None) -> dict:
    """The spec's per-instrument allocations, with the clause each came from."""
    if path is None:
        path = (Path(__file__).resolve().parents[2]
                / "analysis" / "data" / "lro_alignment_allocations.csv")
    names, alloc, sections, notes = [], [], [], []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            names.append(row["channel"])
            alloc.append(float(row["allocation_arcsec"]))
            sections.append(row["section"])
            notes.append(row["note"])
    return {"names": names, "alloc_arcsec": np.asarray(alloc),
            "sections": sections, "notes": notes}


# ---------------------------------------------------------------------------
# exact common-point test in the tangent plane
# ---------------------------------------------------------------------------

def _candidates(delta: np.ndarray, A: np.ndarray) -> np.ndarray:
    """Points where a common intersection, if it exists, must have a witness.

    Either one disk is contained in all the others (its centre is a witness) or
    the intersection's boundary has a vertex, which is a crossing of two circle
    boundaries.  Enumerating both families is exact.
    """
    pts = [np.asarray(p, dtype=float).copy() for p in delta]
    n = len(delta)
    for i, j in combinations(range(n), 2):
        d = delta[j] - delta[i]
        r = float(np.linalg.norm(d))
        if r < 1e-12:
            continue
        ai, aj = A[i], A[j]
        if r > ai + aj:
            continue
        a = (ai * ai - aj * aj + r * r) / (2.0 * r)
        h2 = ai * ai - a * a
        if h2 < 0.0:
            continue
        h = np.sqrt(max(h2, 0.0))
        u = d / r
        p = delta[i] + a * u
        perp = np.array([-u[1], u[0]])
        pts.append(p + h * perp)
        if h > 1e-12:
            pts.append(p - h * perp)
    return np.asarray(pts)


def disk_feasible(delta, A, tol: float = 1e-9) -> dict:
    """Is there a point ``x`` with ``|x - d_i| <= A_i`` for every ``i``?

    Returns the witness and the worst signed slack (positive = feasible), in
    arc-seconds.  Exact up to floating point, no solver.
    """
    delta = np.atleast_2d(np.asarray(delta, dtype=float))
    A = np.asarray(A, dtype=float)
    C = _candidates(delta, A)
    # slack at every candidate: min_i (A_i - |c - d_i|)
    dist = np.linalg.norm(C[:, None, :] - delta[None, :, :], axis=2)
    slack = (A[None, :] - dist).min(axis=1)
    k = int(np.argmax(slack))
    return {"feasible": bool(slack[k] >= -tol), "center": C[k],
            "slack_arcsec": float(slack[k])}


def min_common_radius(delta, A, hi: float = 20000.0) -> float:
    """Smallest ``t`` such that a common point exists with every radius ``A_i + t``.

    Convex in ``t``, so bisection on the exact test is exact.
    """
    delta = np.atleast_2d(np.asarray(delta, dtype=float))
    A = np.asarray(A, dtype=float)
    if disk_feasible(delta, A)["feasible"]:
        return 0.0
    lo, up = 0.0, hi
    for _ in range(60):
        mid = 0.5 * (lo + up)
        if disk_feasible(delta, A + mid)["feasible"]:
            up = mid
        else:
            lo = mid
    return up


def per_channel_ok(delta, A) -> bool:
    """Every instrument inside its own allocation -- what each clause states."""
    delta = np.atleast_2d(np.asarray(delta, dtype=float))
    return bool(np.all(np.linalg.norm(delta, axis=1) <= np.asarray(A) + 1e-12))


def pairwise_ok(delta, A) -> bool:
    """Every pair reconcilable within the sum of two allocations."""
    delta = np.atleast_2d(np.asarray(delta, dtype=float))
    A = np.asarray(A, dtype=float)
    n = len(delta)
    for i, j in combinations(range(n), 2):
        if np.linalg.norm(delta[i] - delta[j]) > A[i] + A[j] + 1e-12:
            return False
    return True


def iis_disks(delta, A) -> dict:
    """Smallest subset that has no common point -- what to act on."""
    delta = np.atleast_2d(np.asarray(delta, dtype=float))
    A = np.asarray(A, dtype=float)
    keep = list(range(len(delta)))
    if disk_feasible(delta, A)["feasible"]:
        return {"infeasible": False, "subset": [], "loosen_arcsec": 0.0}
    for drop in range(len(delta)):
        trial = [k for k in keep if k != drop]
        if not disk_feasible(delta[trial], A[trial])["feasible"]:
            keep = trial
    r = min_common_radius(delta[keep], A[keep])
    return {"infeasible": True, "subset": keep, "loosen_arcsec": r}


# ---------------------------------------------------------------------------
# the three verdicts, over as-built draws
# ---------------------------------------------------------------------------

def simulate(alloc_arcsec, sigma_arcsec: float = 100.0, n_draw: int = 4000,
             seed: int = 2009) -> dict:
    """Draw as-built deviations, score the three checks, count the disagreements.

    ``sigma`` is per axis.  The specification says its budgets are "3 sigma or
    worst case", so the 300 arc-second alignment allocation corresponds to
    ``sigma = 100``; the sweep covers the rest.
    """
    A = np.asarray(alloc_arcsec, dtype=float)
    n = len(A)
    rng = np.random.default_rng(seed)
    d = rng.normal(0.0, sigma_arcsec, size=(n_draw, n, 2))

    per, pair, exact = [], [], []
    slack = np.empty(n_draw)
    for k in range(n_draw):
        per.append(per_channel_ok(d[k], A))
        pair.append(pairwise_ok(d[k], A))
        f = disk_feasible(d[k], A)
        exact.append(f["feasible"])
        slack[k] = f["slack_arcsec"]
    per = np.asarray(per)
    pair = np.asarray(pair)
    exact = np.asarray(exact)

    miss_pair = pair & ~exact          # table says yes, no common point
    miss_per = per & ~exact
    return {
        "n_channels": n,
        "sigma_arcsec": sigma_arcsec,
        "n_draw": n_draw,
        "rate_per_channel": float(per.mean()),
        "rate_pairwise": float(pair.mean()),
        "rate_exact": float(exact.mean()),
        "rate_missed_by_pairwise": float(miss_pair.mean()),
        "rate_missed_by_per_channel": float(miss_per.mean()),
        "share_of_failures_missed_by_pairwise":
            float(miss_pair.sum() / max((~exact).sum(), 1)),
        "share_of_failures_missed_by_per_channel":
            float(miss_per.sum() / max((~exact).sum(), 1)),
        "slack_p01_arcsec": float(np.percentile(slack, 1)),
        "slack_median_arcsec": float(np.median(slack)),
        "min_alloc_arcsec": float(A.min()),
        "max_alloc_arcsec": float(A.max()),
    }


# ---------------------------------------------------------------------------
# analytic window, in arc-seconds of a real budget
# ---------------------------------------------------------------------------

def blind_band(theta_arcsec: float, n: int = 3) -> dict:
    """Equal allocations ``theta``: where the pairwise sum outruns the geometry.

    For ``n`` channels on a ring of radius ``a`` the largest pair separation is
    ``2 a sin(pi/n)`` and the exact requirement is ``a``.  Pairwise arithmetic
    demands ``a sin(pi/n) <= theta``; geometry demands ``a <= theta``.  The band
    between them has width ``theta (1/sin(pi/n) - 1)`` on ``a``, i.e. a relative
    width of ``1 - sin(pi/n)`` -- ``13.41%`` at ``n = 3``, and it shrinks to
    nothing as ``n`` grows and an opposite pair appears.
    """
    if n < 3:
        return {"n": n, "pairwise_capacity_arcsec": 2.0 * theta_arcsec,
                "exact_capacity_arcsec": theta_arcsec,
                "band_arcsec": 0.0, "band_frac": 0.0, "rho": 1.0}
    s = np.sin(np.pi / n)
    pair_cap = 2.0 * theta_arcsec          # max separation the table accepts
    exact_cap = 2.0 * theta_arcsec * s     # same separation, geometric limit
    return {
        "n": n,
        "pairwise_capacity_arcsec": float(pair_cap),
        "exact_capacity_arcsec": float(exact_cap),
        "band_arcsec": float(pair_cap - exact_cap),
        "band_frac": float(1.0 - s),
        "rho": float(1.0 / s),
    }


def price_of_one_shim(alloc_arcsec, sigma_arcsec: float = 100.0,
                      target: float = 0.997, n_draw: int = 1500,
                      seed: int = 77) -> dict:
    """How much every allocation must grow for one shim to work ``target`` of the time.

    Gaussian as-built errors, so this is the *production* view: a 3 sigma
    allocation already sits far outside the spread, which is why real
    specifications rarely meet the defect.  The worst-case view is
    ``rescue_curve``.
    """
    A = np.asarray(alloc_arcsec, dtype=float)
    lo, hi = 1.0, 12.0

    def rate(scale):
        rng = np.random.default_rng(seed)
        d = rng.normal(0.0, sigma_arcsec, size=(n_draw, len(A), 2))
        ok = sum(disk_feasible(d[k], A * scale)["feasible"] for k in range(n_draw))
        return ok / n_draw

    if rate(1.0) >= target:
        return {"scale": 1.0, "rate_at_1": rate(1.0), "target": target}
    for _ in range(18):
        mid = 0.5 * (lo + hi)
        if rate(mid) >= target:
            hi = mid
        else:
            lo = mid
    return {"scale": float(hi), "rate_at_scale": float(rate(hi)),
            "rate_at_1": float(rate(1.0)), "target": target}


def rescue_curve(alloc_arcsec, ratios, n_draw: int = 3000,
                 seed: int = 412) -> list[dict]:
    """Worst case, no distribution: as-built spread in a disk of radius ``T``.

    ``T / A`` is the only design parameter that matters.  Below 1 a shim is not
    needed -- the identity orientation already satisfies every allocation.
    Above about 1.15 no shim exists for three channels, and the pairwise check
    stops certifying too a little later.  Between the two lies the whole
    commercial question: how likely is a mechanical tolerance to land there?

    Both verdicts are evaluated at the *same* draws, so the gap column is a
    paired count rather than a difference of two independent rates.
    """
    A = np.asarray(alloc_arcsec, dtype=float)
    n = len(A)
    ref = float(A.min())
    rng = np.random.default_rng(seed)
    rows = []
    for ratio in ratios:
        T = ratio * ref
        pair_ok = 0
        exact_ok = 0
        missed = 0
        for _ in range(n_draw):
            r = np.sqrt(rng.random((n, 1))) * T
            th = rng.random((n, 1)) * 2.0 * np.pi
            d = np.hstack([r * np.cos(th), r * np.sin(th)])
            p = pairwise_ok(d, A)
            e = disk_feasible(d, A)["feasible"]
            pair_ok += p
            exact_ok += e
            missed += int(p and not e)
        rows.append({
            "n_channels": n,
            "T_over_Amin": float(ratio),
            "rate_pairwise": pair_ok / n_draw,
            "rate_exact": exact_ok / n_draw,
            "rate_missed_by_pairwise": missed / n_draw,
        })
    return rows


def qualification(alloc_arcsec, spread_arcsec: float) -> dict:
    """The five-minute screen for a candidate table.

    Given the tightest allocation and the mechanical spread the shop actually
    holds, say whether a shared-orientation architecture is worth costing, and
    whether the pairwise arithmetic would mislead.
    """
    A = float(np.min(alloc_arcsec))
    rho = 2.0 / np.sqrt(3.0)
    return {
        "min_alloc_arcsec": A,
        "spread_arcsec": float(spread_arcsec),
        "T_over_A": float(spread_arcsec / A),
        "shim_needed": bool(spread_arcsec > A),
        "shim_possible": bool(spread_arcsec <= A),
        "pairwise_would_claim_arcsec": float(rho * A),
        "over_promise_arcsec": float(rho * A - A),
        "band": [float(A), float(rho * A)],
    }


# ---------------------------------------------------------------------------
# two clauses that can be checked against the document's own arithmetic
# ---------------------------------------------------------------------------

def nac_pair() -> dict:
    """Table 9-3: two NACs, 102 arc-seconds of allocation, 103 of requirement.

    For two channels the pairwise sum *is* the exact criterion -- the minimal
    enclosing disk of two points is the one on their diameter -- so the table's
    own arithmetic is exact here, and the tool must reproduce its 1 arc-second
    margin rather than improve on it.  This is the control: a place where the
    method that is wrong for three channels is exactly right for two.
    """
    alloc_each = 51.0                     # 102 total, split evenly
    requirement = 103.0                   # 500 microradians, Table 9-3
    A = np.array([alloc_each, alloc_each])
    worst = alloc_each * 2.0              # a pair separates along its own line
    return {
        "channels": 2,
        "allocation_total_arcsec": float(worst),
        "requirement_arcsec": requirement,
        "margin_arcsec": float(requirement - worst),
        "rho": 1.0,
        "verdict_pairwise": bool(worst <= requirement),
        "verdict_exact": bool(worst <= requirement),
        "note": ("two channels: exact = pairwise, so the summing convention in "
                 "Table 9-3 is not optimistic here"),
    }


def lola_nac() -> dict:
    """Table 8-3: LOLA must sit inside a NAC field of view.

    The requirement is 1.4 deg; a NAC half-field is 0.05 rad / 2 = 1.4324 deg,
    so the geometric slack is 116 arc-seconds while the co-alignment allocation
    is 1636 arc-seconds.  Two readings of the clause are possible and they
    differ by 1520 arc-seconds, so the correct output is UNDECIDED, not a
    verdict -- which is exactly the case the three-valued rule exists for.
    """
    req = 5040.0                          # 1.4 deg
    alloc = 1636.0                        # Table 8-3 total
    half_fov = np.degrees(0.05 / 2.0) * 3600.0     # 0.05 rad per NAC
    return {
        "requirement_arcsec": req,
        "allocation_arcsec": alloc,
        "half_fov_arcsec": float(half_fov),
        "geometric_slack_arcsec": float(half_fov - req),
        "reading_nominal_limit": "allocation is spent inside the 1.4 deg",
        "reading_built_limit": "1.4 deg bounds the as-built offset",
        "overrun_if_built_arcsec": float(alloc - (half_fov - req)),
        "verdict": "UNDECIDED",
    }
