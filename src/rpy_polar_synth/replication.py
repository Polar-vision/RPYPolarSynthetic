"""Is the S3 defect a one-off, or a reusable pattern?

Section 9.15 left exactly one scenario with an irreplaceable claim: the
alignment-tolerance problem, because it is the only one where an *existing*
criterion is provably wrong on a set of positive measure.  That raises the only
question worth asking next:

    is "an existing pairwise criterion is optimistic" a property of that one
    geometry, or does it recur whenever a group must share one setting?

This module answers it with the smallest possible machinery.  The object is a
family of caps on the sphere; the question is whether they share a point.

Two exact solvers are implemented independently, because a study about a wrong
criterion must not get its truth from the method under test:

    * ``min_cap_bruteforce`` -- the fact that a minimal enclosing cap is pinned
      by two antipodal points or by three points on its boundary.  Enumerate
      pairs and triples, keep the feasible candidates, take the smallest.  Exact,
      O(n^4), independent of any solver.
    * ``min_cap_socp`` -- ``max s  s.t.  c_i . x >= s,  |x| <= 1``, a conic
      program.  Different code path, different failure modes.

They agree to 1e-9, and that agreement is the licence to use either one as truth.

The pairwise criterion is modelled as the tolerance table a design review
actually walks through: every pair of channels must be reconcilable within the
sum of their tolerances.  That is ``d_ij <= theta_i + theta_j`` for all pairs,
which is necessary and insufficient.  Its optimism factor is

    rho = r*(C) / (max_ij d_ij / 2),

where ``r*`` is the exact minimal uniform half-angle admitting a common point.
``rho >= 1`` always, ``rho = 1`` iff the minimal cap is pinned by a diameter.
``rho - 1`` is the fraction by which the table under-sizes every tolerance when
the allocation is uniform -- a scale-free number, which is why it can be quoted
to a customer without knowing their units.

Scenarios:

    R1  tolerance imbalance    three caps on a 120 deg ring, one tolerance
                               scaled by kappa.  Does the 13.4% window survive
                               when the channels are not identical?
    R2  random suites          n nominal directions in a cone, uniform
                               tolerance.  How often, and by how much, is the
                               pairwise table optimistic?
    R3  setup grouping         single-linkage clustering of machinable features
                               into shared setups.  The clustering is the
                               criterion; a cluster that no orientation serves
                               is a phantom setup, i.e. a plan that promises
                               one fixture and needs two.
    R4  automotive suite       one bracket, three sensors, real tolerance
                               numbers, as a worked customer case.
"""

from __future__ import annotations

from itertools import combinations
import time

import numpy as np

DEG = np.pi / 180.0  # degrees to radians (was imported from safety_scenarios)

__all__ = [
    "unit",
    "min_cap_bruteforce",
    "min_cap_socp",
    "pairwise_radius",
    "optimism_factor",
    "feasible",
    "iis",
    "random_suite",
    "ring_unequal",
    "setup_grouping",
    "adas_case",
]


# ---------------------------------------------------------------------------
# exact solvers
# ---------------------------------------------------------------------------

def unit(v) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def _ang(u, v) -> float:
    """Angle in **degrees**.  Every radius in this module is in degrees."""
    return float(np.degrees(np.arccos(np.clip(float(u @ v), -1.0, 1.0))))


def min_cap_bruteforce(C: np.ndarray) -> dict:
    """Smallest cap containing every direction in ``C`` (rows are unit vectors).

    A minimal enclosing cap on the sphere is pinned either by two points that
    are endpoints of a diameter, or by three points on its boundary.  Enumerate
    both families, discard candidates that fail to cover the set, keep the
    smallest.  Exact up to floating point; no solver involved.
    """
    C = np.atleast_2d(np.asarray(C, dtype=float))
    n = len(C)
    if n == 1:
        return {"radius_deg": 0.0, "center": C[0].copy(), "support": [0],
                "pinned_by": 1}

    best = None
    for i, j in combinations(range(n), 2):
        d = _ang(C[i], C[j])
        centre = unit(C[i] + C[j])
        r = 0.5 * d
        if r <= 1e-12:
            continue
        if max(_ang(centre, C[k]) for k in range(n)) <= r + 1e-7:
            if best is None or r < best["radius_deg"]:
                best = {"radius_deg": r, "center": centre,
                        "support": [i, j], "pinned_by": 2}
    if best is not None:
        return best

    for i, j, k in combinations(range(n), 3):
        a, b, c = C[i], C[j], C[k]
        # the spherical circumcentre is equidistant from all three, i.e. its
        # direction is orthogonal to both difference vectors
        axis = np.cross(a - b, a - c)
        if np.linalg.norm(axis) < 1e-12:
            continue
        for sign in (1.0, -1.0):
            x = unit(sign * axis)
            r = _ang(x, a)
            if r > 90.0:
                continue
            if max(_ang(x, C[m]) for m in range(n)) <= r + 1e-7:
                if best is None or r < best["radius_deg"]:
                    best = {"radius_deg": r, "center": x,
                            "support": [i, j, k], "pinned_by": 3}
    if best is None:                     # whole sphere: >=4 points, no cap < 90
        return {"radius_deg": 180.0, "center": np.array([0.0, 0.0, 1.0]),
                "support": list(range(n)), "pinned_by": -1}
    return best


def min_cap_socp(C: np.ndarray) -> dict:
    """Same problem through a conic program: maximise the worst-case dot product.

    Independent of the enumeration above, so agreement between the two is
    evidence about the answer rather than about one implementation.
    """
    import cvxpy as cp

    C = np.atleast_2d(np.asarray(C, dtype=float))
    x = cp.Variable(C.shape[1])
    s = cp.Variable()
    cons = [C @ x >= s, cp.norm(x, 2) <= 1]
    prob = cp.Problem(cp.Maximize(s), cons)
    prob.solve(solver=cp.CLARABEL)
    if prob.status not in ("optimal", "optimal_inaccurate"):
        raise RuntimeError(f"status {prob.status}")
    xv = unit(x.value)
    r = max(_ang(xv, c) for c in C)
    return {"radius_deg": r, "center": xv, "s": float(s.value)}


# ---------------------------------------------------------------------------
# the two criteria
# ---------------------------------------------------------------------------

def pairwise_radius(C: np.ndarray) -> float:
    """Half the largest pairwise separation: what a pairwise table asks for."""
    C = np.atleast_2d(np.asarray(C, dtype=float))
    n = len(C)
    if n < 2:
        return 0.0
    return 0.5 * max(_ang(C[i], C[j]) for i, j in combinations(range(n), 2))


def optimism_factor(C: np.ndarray) -> dict:
    """``rho = exact / pairwise``; the factor by which the table is optimistic."""
    exact = min_cap_bruteforce(C)["radius_deg"]
    pair = pairwise_radius(C)
    rho = np.inf if pair <= 0 else exact / pair
    return {"exact_deg": exact, "pairwise_deg": pair, "rho": float(rho),
            "gap_deg": exact - pair}


def _frame(c):
    """Orthonormal (e1, e2, c) with c as the pole."""
    c = unit(c)
    tmp = np.array([1.0, 0.0, 0.0]) if abs(c[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = unit(np.cross(tmp, c))
    e2 = np.cross(c, e1)
    return e1, e2, c


def feasible(C: np.ndarray, thetas_deg) -> dict:
    """Exact feasibility of a cap family with possibly unequal radii.

    The margin function ``f(x) = max_i (angle(x, c_i) - theta_i)`` is
    geodesically convex on any hemisphere containing the caps (the angle to a
    fixed direction is geodesically convex, and a max of convex functions is
    convex), so a local descent reaches the global optimum.  The convex case
    therefore needs no branch and bound and no conic solver at all.

    A conic formulation was tried first and rejected: with tolerances of a few
    degrees ``cos(theta)`` sits within 1e-3 of 1, so the solver's absolute
    tolerance swamps the signal and it reported infeasible where a 0.01 deg
    grid found a point 0.7 deg inside every cap.  A wrong "no" is the one error
    this project cannot afford, hence the geometric form.
    """
    from scipy.optimize import minimize

    C = np.atleast_2d(np.asarray(C, dtype=float))
    th = np.asarray(thetas_deg, dtype=float)
    e1, e2, pole = _frame(C.mean(axis=0))

    def point(p):
        d = pole + np.tan(np.radians(p[0])) * e1 + np.tan(np.radians(p[1])) * e2
        return unit(d)

    def f(p):
        x = point(p)
        return float(np.max(np.degrees(np.arccos(np.clip(C @ x, -1.0, 1.0))) - th))

    best = None
    starts = [np.zeros(2)]
    rad = max(float(np.max(np.abs(th))), 1.0)
    for k in range(8):
        starts.append(rad * np.array([np.cos(k * np.pi / 4), np.sin(k * np.pi / 4)]))
    for s in starts:
        r = minimize(f, s, method="Nelder-Mead",
                     options={"xatol": 1e-10, "fatol": 1e-12,
                              "maxiter": 4000, "maxfev": 8000})
        r = minimize(f, r.x, method="BFGS", options={"gtol": 1e-12})
        if best is None or r.fun < best.fun:
            best = r
    x = point(best.x)
    return {"feasible": bool(best.fun <= 1e-7), "center": x,
            "margin_deg": float(best.fun)}


def iis(C: np.ndarray, thetas_deg) -> dict:
    """Smallest infeasible subset, by greedy deletion.

    This is the output a design engineer can act on: not "infeasible" but
    "these three channels cannot be reconciled, drop one or loosen it by X".
    """
    C = np.atleast_2d(np.asarray(C, dtype=float))
    th = np.asarray(thetas_deg, dtype=float)
    keep = list(range(len(C)))
    if feasible(C, th)["feasible"]:
        return {"infeasible": False, "subset": [], "size": 0,
                "loosen_deg": 0.0}
    for drop in range(len(C)):
        trial = [k for k in keep if k != drop]
        if not feasible(C[trial], th[trial])["feasible"]:
            keep = trial
    sub = min_cap_bruteforce(C[keep])["radius_deg"]
    return {"infeasible": True, "subset": keep, "size": len(keep),
            "loosen_deg": float(sub - np.max(th[keep]))}


# ---------------------------------------------------------------------------
# R1 -- does the window survive unbalanced tolerances?
# ---------------------------------------------------------------------------

def ring_unequal(kappas=(0.05, 0.1, 0.2, 0.35, 0.5, 0.7, 0.85, 1.0, 1.2)):
    """Three caps on a ring of radius r; the third tolerance is ``kappa`` times.

    Pairwise passes from ``tau >= sqrt(3)/(1+kappa)`` on the binding pair.  The
    exact threshold is found by bisection on a conic feasibility test.  The
    returned window is the width of the band where the table says yes and no
    orientation exists.
    """
    r_deg = 3.0
    base = np.array([0.0, 0.0, 1.0])
    e1 = np.array([1.0, 0.0, 0.0])
    e2 = np.array([0.0, 1.0, 0.0])
    ring = [np.cos(r_deg * DEG) * base
            + np.sin(r_deg * DEG) * (np.cos(120.0 * k * DEG) * e1
                                     + np.sin(120.0 * k * DEG) * e2)
            for k in range(3)]
    ring = np.asarray([unit(v) for v in ring])

    rows = []
    for kappa in kappas:
        # exact threshold, by bisection on tau
        lo, hi = 0.5, 2.5
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            th = np.array([mid, mid, kappa * mid]) * r_deg
            if feasible(ring, th)["feasible"]:
                hi = mid
            else:
                lo = mid
        tau_exact = hi
        # the table passes when *every* pair reconciles: the binding pair is the
        # tight one (1,2) for kappa > 1 and a pair with the loose cap for
        # kappa < 1.  Using only sqrt(3)/(1+kappa) would credit the loose cap
        # with absorbing the tight pair, which is not what a table does.
        d = np.asarray([[_ang(ring[i], ring[j]) for j in range(3)]
                        for i in range(3)]) / r_deg
        tau_pair = 0.0
        for i, j in combinations(range(3), 2):
            w = (1.0 if i != 2 else kappa) + (1.0 if j != 2 else kappa)
            tau_pair = max(tau_pair, d[i, j] / w)
        rows.append({
            "kappa": kappa,
            "tau_pairwise": float(tau_pair),
            "tau_exact": float(tau_exact),
            "window": float(tau_exact - tau_pair),
            "window_frac": float(1.0 - tau_pair / tau_exact),
            "table_false_feasible": int(tau_pair < tau_exact),
        })
    return rows


# ---------------------------------------------------------------------------
# R2 -- how often is the table optimistic, and by how much?
# ---------------------------------------------------------------------------

def random_suite(n: int, spread_deg: float, rng, min_sep_deg: float = 0.6) -> np.ndarray:
    """``n`` nominal directions inside a cap of ``spread_deg`` around +z."""
    out = []
    tries = 0
    while len(out) < n and tries < 4000:
        tries += 1
        # uniform in the cap
        cz = 1.0 - rng.random() * (1.0 - np.cos(spread_deg * DEG))
        sz = np.sqrt(max(0.0, 1.0 - cz * cz))
        phi = 2.0 * np.pi * rng.random()
        v = np.array([sz * np.cos(phi), sz * np.sin(phi), cz])
        if all(_ang(v, w) >= min_sep_deg for w in out):
            out.append(v)
    return np.asarray(out)


# ---------------------------------------------------------------------------
# R3 -- single-linkage setup grouping
# ---------------------------------------------------------------------------

def pocket_part(n_pockets: int = 3, per_pocket: int = 6, spread_deg: float = 3.0,
                sep_deg: float = 18.0, reach_deg: float = 25.0,
                rng=None, ring: bool = True) -> dict:
    """A machined part as pockets of features, each pocket one machinable face.

    ``ring`` places the pocket normals at ``0, sep, 2*sep, ...`` along a great
    circle, which is the worst arrangement and the easiest to reason about;
    otherwise they are scattered in a 55 deg cap.

    ``spread_deg`` is the wobble of features inside a pocket (a face is not a
    mathematical plane).  Two features can share a setup when their normals are
    within ``2 * reach``, which is exactly the edge rule single linkage uses.
    """
    rng = np.random.default_rng(0) if rng is None else rng
    base = np.array([0.0, 0.0, 1.0])
    e1 = np.array([1.0, 0.0, 0.0])
    e2 = np.array([0.0, 1.0, 0.0])
    if ring:
        # pocket normals on a circle of angular radius sep, equally spaced: the
        # mutual separation is then sep*sqrt(3) for n = 3, and the smallest cap
        # containing all of them has radius exactly sep, which is what makes the
        # construction readable.  A great-circle arrangement would put them on
        # one line, where the table happens to be exact, so nothing is tested.
        centres = []
        for k in range(n_pockets):
            ang = 2.0 * np.pi * k / n_pockets
            centres.append(unit(np.cos(sep_deg * DEG) * base
                                + np.sin(sep_deg * DEG)
                                * (np.cos(ang) * e1 + np.sin(ang) * e2)))
    else:
        centres = list(random_suite(n_pockets, 40.0, rng, min_sep_deg=6.0))

    feats, labels = [], []
    for idx, c in enumerate(centres):
        u1, u2, _ = _frame(c)
        for _ in range(per_pocket):
            a = spread_deg * np.sqrt(rng.random())
            phi = 2.0 * np.pi * rng.random()
            v = unit(c + np.tan(a * DEG) * (np.cos(phi) * u1
                                            + np.sin(phi) * u2))
            feats.append(v)
            labels.append(idx)
    return {"features": np.asarray(feats), "labels": np.asarray(labels),
            "centres": np.asarray(centres), "reach_deg": reach_deg,
            "sep_deg": sep_deg}


def _single_linkage(F: np.ndarray, thresh_deg: float) -> list[list[int]]:
    n = len(F)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i, j in combinations(range(n), 2):
        if _ang(F[i], F[j]) <= thresh_deg:
            ra, rb = find(i), find(j)
            if ra != rb:
                parent[ra] = rb
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def _min_setups(F: np.ndarray, labels: np.ndarray, reach_deg: float) -> int:
    """Fewest orientations covering every feature (exact at pocket level).

    A set of pockets shares one setup exactly when the minimal cap of *all*
    their features fits in ``reach``.  Pairwise distance is the wrong test --
    that is the whole point of this scenario, so it must not sneak back in
    here.  Splitting a pocket never helps when its own spread is far below
    ``reach``, so the cover is computed over pockets.
    """
    ids = sorted(set(labels.tolist()))
    n = len(ids)
    if n == 0:
        return 0
    N = 1 << n
    ok = [False] * N
    for m in range(1, N):
        sel = np.isin(labels, [ids[i] for i in range(n) if m >> i & 1])
        ok[m] = min_cap_bruteforce(F[sel])["radius_deg"] <= reach_deg + 1e-9
    INF = 99
    dp = [INF] * N
    dp[0] = 0
    for m in range(N):
        if dp[m] == INF:
            continue
        for sub in range(1, N):
            if ok[sub] and dp[m | sub] > dp[m] + 1:
                dp[m | sub] = dp[m] + 1
    return dp[N - 1]


def audit_part(part: dict) -> dict:
    """What the plan promises (single linkage) vs what the machine needs."""
    F = part["features"]
    reach = part["reach_deg"]
    groups = _single_linkage(F, 2.0 * reach)
    phantom, worst = 0, 0.0
    for g in groups:
        if len(g) < 2:
            continue
        r = min_cap_bruteforce(F[g])["radius_deg"]
        if r > reach + 1e-9:
            phantom += 1
            worst = max(worst, r - reach)
    return {
        "n_features": int(len(F)),
        "reach_deg": float(reach),
        "sep_deg": float(part["sep_deg"]),
        "plan_setups": len(groups),
        "true_setups": int(_min_setups(F, part["labels"], reach)),
        "phantom": phantom,
        "worst_excess_deg": float(worst),
        "phantom_cost": int(_min_setups(F, part["labels"], reach) - len(groups)),
    }


def part_sweep(reach_deg: float = 25.0, seps=None, **kw) -> list[dict]:
    """Vary the pocket separation: where does the promise stop being true?"""
    if seps is None:
        seps = [k * 2.5 for k in range(1, 15)]
    rows = []
    for sep in seps:
        part = pocket_part(sep_deg=sep, reach_deg=reach_deg, rng=np.random.default_rng(4), **kw)
        rows.append(audit_part(part))
    return rows


def part_rate(n_parts: int = 200, reach_deg: float = 25.0, n_pockets: int = 4,
              per_pocket: int = 5, seed: int = 5150) -> dict:
    """Scattered pockets: how often does a part carry at least one phantom?"""
    hits = 0
    costs = []
    for k in range(n_parts):
        part = pocket_part(n_pockets=n_pockets, per_pocket=per_pocket,
                           reach_deg=reach_deg, ring=False,
                           rng=np.random.default_rng(seed + k))
        a = audit_part(part)
        hits += int(a["phantom"] > 0)
        costs.append(a["phantom_cost"])
    return {"n_parts": n_parts, "reach_deg": reach_deg,
            "n_pockets": n_pockets, "parts_with_phantom": hits,
            "rate": hits / n_parts,
            "mean_missing_setups": float(np.mean(costs)),
            "max_missing_setups": int(max(costs))}


# ---------------------------------------------------------------------------
# R4 -- one bracket, three sensors, numbers from a real-class suite
# ---------------------------------------------------------------------------

def adas_case(sensors=None) -> dict:
    """Does a bracket orientation exist that puts every sensor in tolerance?

    Each channel has a nominal direction on the vehicle frame -- fixed by the
    mechanical layout, not adjustable without a shim -- and an angular tolerance
    to the vehicle axis.  The bracket supplies one common orientation.  A design
    review walks the pairwise table; this asks the triple question.

    Default numbers are a three-sensor forward suite whose nominals sit on a
    small equilateral ring: 0.866 deg apart, so every pair reconciles inside
    +/-0.45 deg, while the three together need 0.50 deg.
    """
    if sensors is None:
        sensors = [
            # name, elevation_deg, azimuth_deg, tolerance_deg
            ("camera", 0.50, 0.0, 0.45),
            ("lidar", -0.25, 0.433, 0.45),
            ("radar", -0.25, -0.433, 0.45),
        ]
    axes, th = [], []
    for _, el, az, tol in sensors:
        d = np.array([np.sin(az * DEG) * np.cos(el * DEG),
                      np.sin(el * DEG),
                      np.cos(az * DEG) * np.cos(el * DEG)])
        axes.append(unit(d))
        th.append(tol)
    C = np.asarray(axes)
    th = np.asarray(th)
    exact = min_cap_bruteforce(C)
    pair = pairwise_radius(C)
    return {
        "sensors": [s[0] for s in sensors],
        "tolerances_deg": th.tolist(),
        "pairwise_gaps_deg": [round(float(_ang(C[0], C[1])), 4),
                              round(float(_ang(C[0], C[2])), 4),
                              round(float(_ang(C[1], C[2])), 4)],
        "exact_radius_deg": float(exact["radius_deg"]),
        "pairwise_radius_deg": float(pair),
        "rho": float(exact["radius_deg"] / pair),
        "pairwise_verdict": bool(pair <= th.min()),
        "exact_verdict": bool(exact["radius_deg"] <= th.min()),
        "shortfall_deg": float(exact["radius_deg"] - th.min()),
        "pinned_by": exact["pinned_by"],
        "support": exact["support"],
        "iis": iis(C, th),
    }
