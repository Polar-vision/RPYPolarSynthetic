"""Reliability-facing measurements for a one-sided alignment criterion.

The geometry says the pairwise sum accepts configurations that have no common
point.  A reliability reviewer asks different questions about the same fact,
and this module answers them with counts and with bounds:

* how often does each criterion err, and in which direction
* what does each detect, what does it cry wolf about, and how deep is the
  blind spot (a number, not a rate)
* which part of the design box can a build record occupy, and is that part
  disjoint from the region where the criterion is wrong
* how many units would a programme have to fly before it could expect to learn
  that the criterion was wrong

Three criteria are in use: ``P`` (every channel inside its own allocation),
``W`` (every pair inside the sum of two allocations), and ``E`` (a common point
exists).  Two facts are theorems, not measurements, and both are checked here
as identities rather than estimated as rates:

    P accepts  =>  E accepts        (x = 0 is a witness)
    W rejects  =>  E rejects        (triangle inequality)

so P is sound and incomplete, W is necessary and not sufficient, and the two
err in opposite directions: P cries wolf, W stays silent.
"""

from __future__ import annotations

import math
import time

import numpy as np

from rpy_polar_synth.p3_replay import (
    disk_feasible,
    pairwise_ok,
    per_channel_ok,
)

__all__ = [
    "wilson",
    "draw_errors",
    "verdicts",
    "gate_profile",
    "coverage_profile",
    "shortfall_profile",
    "record_bands",
    "conforming_share",
    "common_mode_check",
    "distribution_check",
    "learning_units",
    "required_consequence_ratio",
    "evaluation_cost",
    "JUNG",
]

JUNG = 2.0 / math.sqrt(3.0)          # 1.154700..., the depth of the blind spot
SHORTFALL_DEPTH = JUNG - 1.0         # 0.154701..., as a fraction of the allocation


# ---------------------------------------------------------------------------
# counts and intervals
# ---------------------------------------------------------------------------

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval.  Used wherever a rate is reported, because most
    of these rates are small and the normal approximation is not usable."""
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / den
    half = z * math.sqrt(max(p * (1.0 - p) / n + z * z / (4.0 * n * n), 0.0)) / den
    return (max(centre - half, 0.0), min(centre + half, 1.0))


def draw_errors(n: int, sigma: float, n_draw: int, dist: str = "normal",
                seed: int = 0) -> np.ndarray:
    """As-built deviations, shape ``(n_draw, n, 2)``, per-axis sd = ``sigma``.

    ``normal``  the usual assumption
    ``disk``    uniform over a disk with the same per-axis sd, so the design box
                is bounded rather than Gaussian
    ``t3``      Student-t on three degrees of freedom, same per-axis sd; checks
                that nothing depends on light tails
    """
    rng = np.random.default_rng(seed)
    if dist == "normal":
        return rng.normal(0.0, sigma, size=(n_draw, n, 2))
    if dist == "disk":
        R = 2.0 * sigma
        r = R * np.sqrt(rng.random((n_draw, n, 1)))
        th = rng.random((n_draw, n, 1)) * 2.0 * np.pi
        return np.concatenate([r * np.cos(th), r * np.sin(th)], axis=2)
    if dist == "t3":
        base = rng.standard_t(3, size=(n_draw, n, 2))
        return base * (sigma / math.sqrt(3.0))
    raise ValueError(f"unknown distribution {dist!r}")


def verdicts(d: np.ndarray, A: np.ndarray) -> dict:
    """The three verdicts on every draw.  ``True`` means *accept*."""
    n_draw = len(d)
    infeasible = np.empty(n_draw, dtype=bool)
    for k in range(n_draw):
        infeasible[k] = not disk_feasible(d[k], A)["feasible"]
    return {
        "infeasible": infeasible,
        "P": np.array([per_channel_ok(d[k], A) for k in range(n_draw)]),
        "W": np.array([pairwise_ok(d[k], A) for k in range(n_draw)]),
    }


def shortfall(d: np.ndarray, A: np.ndarray, hi: float = 4000.0,
              iters: int = 26) -> float:
    """How much every allocation would have to grow for a common point to appear.

    Equal allocations only, since the Jung bound that this feeds is stated for a
    single radius.  Bisection on the exact test, so the answer is the true
    infimum up to ``2**-26`` of the bracket.
    """
    lo, up = 0.0, hi
    for _ in range(iters):
        mid = 0.5 * (lo + up)
        if disk_feasible(d, A + mid)["feasible"]:
            up = mid
        else:
            lo = mid
    return up


# ---------------------------------------------------------------------------
# error profile and detection quality
# ---------------------------------------------------------------------------

def gate_profile(A, sigma: float, n_draw: int = 4000, dist: str = "normal",
                 seed: int = 0, audit: int = 200) -> dict:
    """Confusion counts for the three gates, plus the waiver audit.

    ``fa`` false accept: the gate accepts and no common point exists.
    ``fr`` false reject: the gate rejects and a common point does exist.

    The two identities of the module are checked here as identities: a nonzero
    ``fr_W`` or ``fa_P`` would mean an implementation bug, not a theory failure.
    """
    A = np.asarray(A, dtype=float)
    d = draw_errors(len(A), sigma, n_draw, dist, seed)
    v = verdicts(d, A)
    inf, P, W = v["infeasible"], v["P"], v["W"]

    out = {
        "n": int(len(A)),
        "A_over_sigma": float(A.min() / sigma),
        "dist": dist,
        "n_draw": n_draw,
        "infeasible_rate": float(inf.mean()),
        "reject_P": float((~P).mean()),
        "reject_W": float((~W).mean()),
        "accept_exact": float((~inf).mean()),
    }
    for name, g in (("P", P), ("W", W)):
        fa, fr = int(np.sum(g & inf)), int(np.sum(~g & ~inf))
        out[f"fa_{name}"], out[f"fa_{name}_lo"], out[f"fa_{name}_hi"] = (
            fa / n_draw, *wilson(fa, n_draw))
        out[f"fr_{name}"], out[f"fr_{name}_lo"], out[f"fr_{name}_hi"] = (
            fr / n_draw, *wilson(fr, n_draw))

    # the population a build record actually contains
    sel = P
    out["conforming_draws"] = int(sel.sum())
    out["cond_accept_W"] = float(W[sel].mean()) if sel.any() else float("nan")
    out["cond_accept_exact"] = float((~inf[sel]).mean()) if sel.any() else float("nan")

    # waiver audit: hardware that fails a clause but clears the table
    waivable = (~P) & W
    out["waiver_rate"] = float(waivable.mean())
    idx = np.flatnonzero(waivable)[:audit] if audit else np.array([], dtype=int)
    if len(idx):
        unalign = inf[idx]
        out["waiver_audited"] = int(len(idx))
        out["waiver_unalignable"] = float(unalign.mean()) if len(idx) else float("nan")
        if unalign.any():
            ex = [shortfall(d[k], A) for k in idx[unalign]]
            out["excess_p50_over_A"] = float(np.median(ex) / A.min())
            out["excess_p90_over_A"] = float(np.percentile(ex, 90) / A.min())
        else:
            out["excess_p50_over_A"] = out["excess_p90_over_A"] = 0.0
    else:
        out["waiver_audited"] = 0
        out["waiver_unalignable"] = float("nan")
        out["excess_p50_over_A"] = out["excess_p90_over_A"] = 0.0
    return out


def coverage_profile(A, sigma: float, n_draw: int = 4000,
                     seed: int = 0) -> dict:
    """Diagnostic coverage and spurious-trip rate, per gate.

    Coverage is conditional on the failure mode of interest, ``no common point
    exists``; the spurious rate is conditional on the item being good.
    """
    A = np.asarray(A, dtype=float)
    d = draw_errors(len(A), sigma, n_draw, "normal", seed)
    v = verdicts(d, A)
    inf, P, W = v["infeasible"], v["P"], v["W"]
    n_bad, n_good = int(inf.sum()), int((~inf).sum())
    out = {"n": int(len(A)), "A_over_sigma": float(A.min() / sigma),
           "n_bad": n_bad, "n_good": n_good}
    for name, g in (("P", P), ("W", W)):
        caught = int(np.sum(~g & inf))
        out[f"dc_{name}"] = caught / n_bad if n_bad else float("nan")
        out[f"dc_{name}_lo"], out[f"dc_{name}_hi"] = wilson(caught, n_bad)
        spur = int(np.sum(~g & ~inf))
        out[f"sp_{name}"] = spur / n_good if n_good else float("nan")
        out[f"sp_{name}_lo"], out[f"sp_{name}_hi"] = wilson(spur, n_good)
    return out


def shortfall_profile(A, sigma: float, n_draw: int = 3000, n_audit: int = 600,
                      edges=(0.0, 0.02, 0.05, 0.08, SHORTFALL_DEPTH, 0.25, 0.5, 10.0),
                      seed: int = 0) -> list[dict]:
    """Coverage of the pairwise test against the depth of the shortfall.

    Jung's theorem bounds the blind spot: a configuration that needs a radius
    ``r`` has a largest pair separation of at least ``sqrt(3) r``, so once the
    shortfall passes ``2/sqrt(3) - 1 = 15.47%`` of the allocation some pair has
    already exceeded its sum and the table rejects.  Every miss therefore lies
    left of that line.  Inside the band coverage is partial and configuration
    dependent, which is what the bins measure.
    """
    A = np.asarray(A, dtype=float)
    if A.min() != A.max():
        raise ValueError("shortfall profile needs equal allocations")
    d = draw_errors(len(A), sigma, n_draw, "normal", seed)
    inf = np.array([not disk_feasible(d[k], A)["feasible"] for k in range(len(d))])
    W = np.array([pairwise_ok(d[k], A) for k in range(len(d))])
    idx = np.flatnonzero(inf)[:n_audit]
    r = np.array([shortfall(d[k], A) for k in idx]) / A.min()
    caught = ~W[idx]

    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (r >= lo) & (r < hi)
        n = int(m.sum())
        rows.append({
            "n": int(len(A)),
            "A_over_sigma": float(A.min() / sigma),
            "shortfall_lo": float(lo), "shortfall_hi": float(hi),
            "n_bad": n,
            "coverage": float(caught[m].mean()) if n else float("nan"),
            "coverage_lo": wilson(int(caught[m].sum()), n)[0] if n else float("nan"),
            "coverage_hi": wilson(int(caught[m].sum()), n)[1] if n else float("nan"),
        })
    rows.append({
        "n": int(len(A)), "A_over_sigma": float(A.min() / sigma),
        "shortfall_lo": float("nan"), "shortfall_hi": float("nan"),
        "n_bad": int(len(idx)),
        "coverage": float(caught.mean()) if len(idx) else float("nan"),
        "coverage_lo": float("nan"), "coverage_hi": float("nan"),
        "max_shortfall_among_misses": float(r[~caught].max()) if (~caught).any() else 0.0,
    })
    return rows


def record_bands(A: float = 300.0, ratios=(0.85, 0.92, 1.00, 1.02, 1.06,
                                          1.15, 1.16, 1.25, 1.40)) -> list[dict]:
    """The three verdicts on a family swept through the boundary.

    An equilateral triple centred on the nominal axis, with circumradius ``r``.
    At ``r = A`` every channel sits exactly at its allocation: the last point a
    build record can contain, and the first point at which the geometry fails.
    The record's support and the criterion's error region are adjacent there
    and nowhere else.
    """
    rows = []
    for t in ratios:
        R = t * A
        pts = np.array([[R * math.cos(th), R * math.sin(th)]
                        for th in (0.0, 2.0 * math.pi / 3.0, 4.0 * math.pi / 3.0)])
        f = disk_feasible(pts, np.full(3, A))
        d_max = max(np.linalg.norm(pts[i] - pts[j])
                    for i in range(3) for j in range(i))
        rows.append({
            "r_over_A": float(t),
            "d_max_over_A": float(d_max / A),
            "per_channel_ok": bool(per_channel_ok(pts, np.full(3, A))),
            "pairwise_ok": bool(pairwise_ok(pts, np.full(3, A))),
            "exact_ok": bool(f["feasible"]),
        })
    return rows


# ---------------------------------------------------------------------------
# what a record can see
# ---------------------------------------------------------------------------

def conforming_share(A, sigma: float, box_k: float = 3.0,
                     n_draw: int = 200000, seed: int = 0) -> dict:
    """Share of a bounded design box on which the per-channel gate passes.

    The box is ``|d_ij| <= box_k * sigma`` per axis -- the support a ``3 sigma``
    convention implicitly assumes.  The conforming region is a product of disks
    inside squares, so the share is closed form while the disks stay inside
    their squares, and it collapses with channel count: ten channels at
    ``A = 2 sigma`` occupy three parts in a hundred thousand of the box.
    """
    A = np.asarray(A, dtype=float)
    half = box_k * sigma
    per = []
    for a in A:
        if a >= half * math.sqrt(2.0):
            per.append(1.0)
        elif a <= half:
            per.append(math.pi * a * a / (4.0 * half * half))
        else:
            per.append(_disk_square_overlap(a, half))
    analytic = float(np.prod(per))

    rng = np.random.default_rng(seed)
    d = rng.uniform(-half, half, size=(n_draw, len(A), 2))
    ok = np.all(np.linalg.norm(d, axis=2) <= A, axis=1)
    hits = int(ok.sum())
    return {"n": int(len(A)), "A_over_sigma": float(A.min() / sigma),
            "box_k": box_k, "analytic_share": analytic,
            "mc_share": hits / n_draw, "mc_hits": hits, "n_draw": n_draw,
            "mc_lo": wilson(hits, n_draw)[0], "mc_hi": wilson(hits, n_draw)[1]}


def _disk_square_overlap(a: float, half: float) -> float:
    """Area of a disk of radius ``a`` inside a square of half-width ``half``."""
    rng = np.random.default_rng(12345)
    N = 400000
    pts = rng.uniform(-half, half, size=(N, 2))
    return float(np.mean(np.einsum("ij,ij->i", pts, pts) <= a * a))


def box_shares(A, sigma: float, box_k: float = 3.0, n_draw: int = 6000,
               seed: int = 0) -> dict:
    """Two shares of the same box: alignable, and visible to a build record.

    A design that is alignable with one shim is not the same object as one whose
    channels each sit inside their own allocation, and the gap between the two
    shares is the rework a per-channel gate would order for no reason.
    """
    A = np.asarray(A, dtype=float)
    half = box_k * sigma
    rng = np.random.default_rng(seed)
    d = rng.uniform(-half, half, size=(n_draw, len(A), 2))
    feasible = np.array([disk_feasible(d[k], A)["feasible"] for k in range(n_draw)])
    conforming = np.all(np.linalg.norm(d, axis=2) <= A, axis=1)
    n_ok, n_cf = int(feasible.sum()), int(conforming.sum())
    return {"n": int(len(A)), "A_over_sigma": float(A.min() / sigma),
            "box_k": box_k, "n_draw": n_draw,
            "feasible_share": n_ok / n_draw,
            "feasible_lo": wilson(n_ok, n_draw)[0],
            "feasible_hi": wilson(n_ok, n_draw)[1],
            "conforming_share": n_cf / n_draw,
            "conforming_lo": wilson(n_cf, n_draw)[0],
            "conforming_hi": wilson(n_cf, n_draw)[1],
            "ratio": (n_cf / n_ok) if n_ok else float("nan")}


# ---------------------------------------------------------------------------
# robustness
# ---------------------------------------------------------------------------

def common_mode_check(A, sigma: float, bias, n_draw: int = 800,
                      seed: int = 0) -> dict:
    """A common offset moves every channel together: which verdicts survive?

    Feasibility and the pairwise test depend on differences only, so both are
    invariant; the per-channel test is not.  Worth stating because it removes a
    whole error source from the analysis (bench, fixture, reference cube) and
    because it is the one place the per-channel gate is the odd one out.
    """
    A = np.asarray(A, dtype=float)
    bias = np.asarray(bias, dtype=float)
    d = draw_errors(len(A), sigma, n_draw, "normal", seed)
    v0, v1 = verdicts(d, A), verdicts(d + bias, A)
    return {
        "n": int(len(A)),
        "bias_over_A": float(np.linalg.norm(bias) / A.min()),
        "n_draw": n_draw,
        "infeasible_changed": int(np.sum(v0["infeasible"] != v1["infeasible"])),
        "pairwise_changed": int(np.sum(v0["W"] != v1["W"])),
        "per_channel_changed": int(np.sum(v0["P"] != v1["P"])),
    }


def distribution_check(A, sigma: float, dists=("normal", "disk", "t3"),
                       n_draw: int = 4000, seed: int = 0) -> list[dict]:
    """Same geometry, three as-built distributions, all at the same per-axis sd."""
    rows = []
    for i, dist in enumerate(dists):
        p = gate_profile(A, sigma, n_draw=n_draw, dist=dist, seed=seed + i, audit=0)
        rows.append({k: p[k] for k in ("n", "A_over_sigma", "dist",
                                       "infeasible_rate", "reject_W", "fa_W",
                                       "fa_P", "cond_accept_W")})
    return rows


# ---------------------------------------------------------------------------
# learning and economics
# ---------------------------------------------------------------------------

def learning_units(miss_rates, conf: float = 0.8) -> list[dict]:
    """Units a programme must fly before it can expect to see one miss.

    ``N = ln(1 - conf) / ln(1 - p)``.  If a design is built once or twice, the
    criterion's error is not merely rare, it is unobservable within the life of
    the programme, which is why the alternative route is to compute the rate
    instead of waiting for it.
    """
    rows = []
    for p in miss_rates:
        rows.append({"miss_rate": float(p), "confidence": conf,
                     "units": float("inf") if p <= 0 else
                     math.log(1.0 - conf) / math.log(1.0 - p)})
    return rows


def required_consequence_ratio(miss_rates) -> list[dict]:
    """How expensive must one late discovery be, per unit of analysis cost?

    Per payload: deciding exactly costs ``c_a``; the table costs ``p * dC``
    where ``p`` is the miss rate and ``dC`` the extra cost of finding the defect
    at integration rather than at analysis.  Exact pays iff
    ``dC / c_a > 1/p``.
    """
    return [{"miss_rate": float(p),
             "required_ratio": float("inf") if p <= 0 else 1.0 / p}
            for p in miss_rates]


def evaluation_cost(A, n_rep: int = 400, seed: int = 0) -> dict:
    """Wall-clock cost of deciding one configuration exactly."""
    rng = np.random.default_rng(seed)
    A = np.asarray(A, dtype=float)
    d = rng.normal(0.0, A.min() / 1.5, size=(n_rep, len(A), 2))
    t0 = time.perf_counter()
    for k in range(n_rep):
        disk_feasible(d[k], A)
    exact = (time.perf_counter() - t0) / n_rep
    t1 = time.perf_counter()
    for k in range(n_rep):
        pairwise_ok(d[k], A)
    pair = (time.perf_counter() - t1) / n_rep
    return {"n": int(len(A)), "exact_seconds": exact, "pairwise_seconds": pair,
            "ratio": exact / pair if pair > 0 else float("inf"), "n_rep": n_rep}
