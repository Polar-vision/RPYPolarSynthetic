"""Pointing prototype: 2-DOF axis estimation on S^2 with certificates.

This module is the engineering artefact behind section 11 of the technical
report. It contains three things that the report claims are useful, and nothing
else:

1. ``estimate_axis``  -- weighted axis estimation on S^2 from off-axis angles,
   carrying no roll parameter at all, so an unobservable gauge cannot be
   silently filled in.
2. ``crlb_axis``      -- the closed-form uncertainty of that estimate,
   sigma_theta = sigma_px / f per channel, combined over the observation set.
   For a uniform ring of N references it collapses to 2 sigma_theta / sqrt(N),
   independent of the off-axis angle.
3. ``cone_feasibility`` -- a three-valued decision for "is there a direction
   inside every tolerance cone". FEASIBLE and INFEASIBLE both come with a
   checkable certificate; when neither can be produced the answer is
   UNDETERMINED, which is the only sound answer for a safety interlock.

Nothing here is specific to a particular sensor: a star catalogue, a
retro-reflector constellation and a mount-limit model all reduce to the same
(cap axis, tolerance) pairs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations

import numpy as np
from scipy.optimize import least_squares, minimize

EPS = 1e-12


# ---------------------------------------------------------------------------
# small spherical helpers
# ---------------------------------------------------------------------------


def normalize(v: np.ndarray) -> np.ndarray:
    """Row-wise normalisation for both single vectors and stacks."""
    v = np.asarray(v, dtype=float)
    if v.ndim == 1:
        return v / max(np.linalg.norm(v), EPS)
    n = np.linalg.norm(v, axis=1, keepdims=True)
    return v / np.maximum(n, EPS)


def tangent_basis(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    a = normalize(a)
    tmp = np.array([1.0, 0.0, 0.0]) if abs(a[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = normalize(np.cross(a, tmp))
    e2 = np.cross(a, e1)
    return e1, e2


def axis_from_chart(alpha: float, beta: float) -> np.ndarray:
    return np.array(
        [np.cos(beta) * np.cos(alpha), np.cos(beta) * np.sin(alpha), np.sin(beta)]
    )


def angle_between(a: np.ndarray, b: np.ndarray) -> float:
    """Angle in radians between one direction and an array of directions."""
    return float(np.arccos(np.clip(normalize(a) @ normalize(b), -1.0, 1.0)))


def angles_between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = normalize(a)
    b = np.atleast_2d(b)
    return np.arccos(np.clip(b @ a, -1.0, 1.0))


# ---------------------------------------------------------------------------
# 2-DOF axis estimation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AxisEstimate:
    axis: np.ndarray
    sigma_t: np.ndarray        # (2,) 1-sigma along the two tangent directions, rad
    sigma_iso_rad: float       # sqrt(trace) summary, rad
    n_used: int
    cond: float
    cost: float
    sigma_px: float
    f: float

    @property
    def sigma_iso_deg(self) -> float:
        return float(np.rad2deg(self.sigma_iso_rad))


def _coarse_axis(u: np.ndarray, theta: np.ndarray, sigma_theta: float) -> np.ndarray:
    """Grid search over the sphere; cheap because n is small."""
    n_alpha, n_beta = 72, 37
    alphas = np.linspace(-np.pi, np.pi, n_alpha, endpoint=False)
    betas = np.linspace(-np.pi / 2, np.pi / 2, n_beta)
    best, best_cost = None, np.inf
    for beta in betas:
        for alpha in alphas:
            a = axis_from_chart(alpha, beta)
            r = (np.arccos(np.clip(u @ a, -1.0, 1.0)) - theta) / sigma_theta
            c = float(r @ r)
            if c < best_cost:
                best_cost, best = c, a
    return best


def estimate_axis(
    u: np.ndarray,
    theta: np.ndarray,
    sigma_theta: float,
    weights: np.ndarray | None = None,
) -> AxisEstimate:
    """Maximum-likelihood optical axis from off-axis angles.

    ``u`` are the known reference directions (unit vectors), ``theta`` the
    measured off-axis angles in radians, ``sigma_theta`` their common standard
    deviation. There is no roll parameter, hence no gauge and no prior.
    """
    u = np.atleast_2d(normalize(u))
    theta = np.asarray(theta, dtype=float)
    if weights is None:
        weights = np.ones(len(theta))
    weights = np.asarray(weights, dtype=float)

    a0 = _coarse_axis(u, theta, sigma_theta)
    alpha0 = np.arctan2(a0[1], a0[0])
    beta0 = np.arcsin(np.clip(a0[2], -1.0, 1.0))

    def residual(p: np.ndarray) -> np.ndarray:
        a = axis_from_chart(p[0], p[1])
        return weights * (np.arccos(np.clip(u @ a, -1.0, 1.0)) - theta) / sigma_theta

    res = least_squares(
        residual, np.array([alpha0, beta0]), method="trf", xtol=1e-14, ftol=1e-14
    )
    a_hat = axis_from_chart(res.x[0], res.x[1])
    jac = res.jac
    normal = jac.T @ jac
    cond = float(np.linalg.cond(normal))
    # Report the uncertainty in an orthonormal tangent frame, not in the chart,
    # so the two components are directly interpretable as angles.
    s1, s2 = crlb_axis(u, theta, sigma_theta, a_hat)
    sigma_t = np.array([s1, s2])
    return AxisEstimate(
        axis=a_hat,
        sigma_t=sigma_t,
        sigma_iso_rad=float(np.hypot(sigma_t[0], sigma_t[1])),
        n_used=int(np.count_nonzero(theta)),
        cond=cond,
        cost=float(res.cost),
        sigma_px=float(sigma_theta),
        f=float("nan"),
    )


def crlb_axis(
    u: np.ndarray,
    theta: np.ndarray,
    sigma_theta: float,
    axis: np.ndarray,
) -> tuple[float, float]:
    """Closed-form axis uncertainty at ``axis``.

    Each measurement contributes (e_j . u_i)^2 / (sin^2 theta_i sigma^2) to the
    information along tangent direction e_j, so

        sigma_j = sigma / sqrt( sum_i (e_j . u_i)^2 / sin^2 theta_i ).

    For a uniform ring of N references at angle theta this gives
    sigma_j = sigma sqrt(2/N), and the 2D summary is 2 sigma / sqrt(N), with no
    dependence on theta.
    """
    e1, e2 = tangent_basis(axis)
    a = normalize(axis)
    u = np.atleast_2d(normalize(u))
    sin_t = np.maximum(np.sin(theta), 1e-9)
    info = np.zeros(2)
    for j, e in enumerate((e1, e2)):
        info[j] = np.sum((u @ e) ** 2 / sin_t**2)
    sigma = sigma_theta / np.sqrt(np.maximum(info, EPS))
    return float(sigma[0]), float(sigma[1])


# ---------------------------------------------------------------------------
# Three-valued cone feasibility with certificates
# ---------------------------------------------------------------------------


@dataclass
class Decision:
    kind: str                                  # feasible | infeasible | undetermined
    point: np.ndarray | None = None            # witness of feasibility
    witness: tuple[int, ...] | None = None     # indices of an infeasible subset
    margin: float = float("nan")               # max_i (angle - tol); <=0 means feasible
    n_caps: int = 0
    detail: dict = field(default_factory=dict)


def cap_margin(b: np.ndarray, axes: np.ndarray, tols: np.ndarray) -> float:
    return float(np.max(angles_between(b, axes) - tols))


def _two_caps_feasible(u1, t1, u2, t2) -> bool:
    return angle_between(u1, u2) <= t1 + t2 + 1e-12


def _circle_circle_points(u1, t1, u2, t2) -> list[np.ndarray]:
    """Intersection points of two small circles on the sphere (0, 1 or 2).

    Computed in the orthonormal frame ``(u1, e, f)`` attached to the first
    circle, where the second circle's constraint is one cosine::

        cos t2 = cos t1 cos d + sin t1 cos(phi) sin d .

    Solving for ``cos(phi)`` is well conditioned at small radii.  The alternative
    expansion ``b = x u1 + y u2 +- z (u1 x u2)`` has coefficients that grow like
    ``1 / sin^2 d``, which loses about five digits at ``d = 1.5 deg`` and makes
    the feasibility test depend on a 1e-12 rad tolerance -- a decision that then
    flips on rounding for instances with a degree of real slack.  Measured in
    section 9.10.
    """
    d = angle_between(u1, u2)
    if d < 1e-12:
        return []
    e = normalize(u2 - float(u2 @ u1) * u1)
    f = np.cross(u1, e)
    denom = np.sin(t1) * np.sin(d)
    if abs(denom) < 1e-15:
        return []
    cosphi = (np.cos(t2) - np.cos(t1) * np.cos(d)) / denom
    if abs(cosphi) > 1.0 + 1e-12:
        return []
    cosphi = float(np.clip(cosphi, -1.0, 1.0))
    sinphi = math.sqrt(max(0.0, 1.0 - cosphi * cosphi))
    base = np.cos(t1) * u1 + np.sin(t1) * cosphi * e
    tang = np.sin(t1) * sinphi * f
    if sinphi <= 1e-15:
        return [normalize(base)]
    return [normalize(base + tang), normalize(base - tang)]


def _three_caps_feasible(axes: np.ndarray, tols: np.ndarray) -> bool:
    """Exact test for three caps.

    The intersection of three disks on the sphere is non-empty iff one of the
    arrangement vertices (a cap centre, or a pairwise circle-circle
    intersection) lies inside all three caps, or one cap contains another whose
    centre is therefore already a candidate. So testing the 3 centres and the 6
    circle-circle points is complete.
    """
    u1, u2, u3 = axes
    t1, t2, t3 = tols
    candidates = [u1, u2, u3]
    for i, j in ((0, 1), (0, 2), (1, 2)):
        candidates.extend(_circle_circle_points(axes[i], tols[i], axes[j], tols[j]))
    for b in candidates:
        if cap_margin(b, axes, tols) <= 1e-12:
            return True
    return False


def cone_feasibility(
    axes: np.ndarray,
    tols: np.ndarray,
    n_grid: int = 4000,
    refine: bool = True,
) -> Decision:
    """Decide whether a direction exists inside every tolerance cone.

    Returns FEASIBLE with a verified point, INFEASIBLE with a small infeasible
    subset (a Helly witness), or UNDETERMINED. All three answers are sound: a
    FEASIBLE answer is checked against every cap, an INFEASIBLE answer is a proof
    on a subset, and UNDETERMINED never claims either.
    """
    axes = np.atleast_2d(normalize(axes))
    tols = np.asarray(tols, dtype=float)
    n = len(tols)
    if n == 1:
        return Decision("feasible", point=axes[0].copy(), margin=-tols[0], n_caps=1)

    # 1) candidate search
    best_b, best_m = None, np.inf
    k = int(np.sqrt(n_grid))
    for beta in np.linspace(-np.pi / 2, np.pi / 2, k):
        for alpha in np.linspace(-np.pi, np.pi, k, endpoint=False):
            b = axis_from_chart(alpha, beta)
            m = cap_margin(b, axes, tols)
            if m < best_m:
                best_m, best_b = m, b
    if refine and best_b is not None:
        from scipy.optimize import minimize as _min

        def f(p):
            return cap_margin(axis_from_chart(p[0], p[1]), axes, tols)

        a0 = np.arctan2(best_b[1], best_b[0])
        b0 = np.arcsin(np.clip(best_b[2], -1.0, 1.0))
        opt = _min(f, np.array([a0, b0]), method="Nelder-Mead",
                   options={"xatol": 1e-10, "fatol": 1e-12, "maxiter": 4000})
        cand = axis_from_chart(opt.x[0], opt.x[1])
        if f(opt.x) < best_m:
            best_m, best_b = f(opt.x), cand
    if best_b is not None and best_m <= -1e-9:
        return Decision("feasible", point=best_b, margin=best_m, n_caps=n,
                        detail={"method": "search"})

    # 2) infeasibility witnesses, smallest first
    for i, j in combinations(range(n), 2):
        if not _two_caps_feasible(axes[i], tols[i], axes[j], tols[j]):
            return Decision("infeasible", witness=(i, j), margin=best_m, n_caps=n,
                            detail={"method": "pair"})
    if n <= 12:
        for idx in combinations(range(n), 3):
            sub = axes[list(idx)]
            sub_t = tols[list(idx)]
            if not _three_caps_feasible(sub, sub_t):
                return Decision("infeasible", witness=tuple(idx), margin=best_m, n_caps=n,
                                detail={"method": "triple"})

    return Decision("undetermined", point=best_b, margin=best_m, n_caps=n,
                    detail={"method": "search-failed"})


# ---------------------------------------------------------------------------
# Exact decision procedure for any number of caps
# ---------------------------------------------------------------------------
#
# Lemma (candidate set).  Let C_i = {b in S^2 : angle(b, u_i) <= Theta_i} with
# Theta_i < pi/2, so every cap is geodesically convex.  If K = C_1 & ... & C_n is
# non-empty, then K contains at least one point of the finite set
#
#     S = { u_i }  U  { boundary(C_i) & boundary(C_j) : i != j }.
#
# Proof sketch.  K is a closed geodesically convex subset of the sphere, hence a
# spherical polygon (possibly of dimension 0 or 1).  If K is a single point or an
# arc, its extreme points lie on at least two boundaries, otherwise K would
# contain a neighbourhood of that point; those points are in the pairwise
# intersections.  If K has interior, either its boundary has a vertex (again a
# pairwise intersection), or the boundary is a single circle, in which case
# K = C_j for some j and the centre u_j lies in K.  []
#
# Consequently K is empty iff no candidate passes every constraint, which makes
# the decision exact for every n, not only for n <= 3.  The cost is O(n^3):
# O(n^2) candidates, each checked against n caps.


def _candidates(axes: np.ndarray, tols: np.ndarray, dedup_tol: float = 1e-9) -> np.ndarray:
    """All points of the candidate set S, de-duplicated."""
    pts: list[np.ndarray] = [np.asarray(a, dtype=float) for a in axes]
    n = len(tols)
    for i, j in combinations(range(n), 2):
        pts.extend(_circle_circle_points(axes[i], tols[i], axes[j], tols[j]))
    out: list[np.ndarray] = []
    for p in pts:
        p = normalize(p)
        if not any(angle_between(p, q) <= dedup_tol for q in out):
            out.append(p)
    return np.asarray(out)


def _best_candidate(axes: np.ndarray, tols: np.ndarray) -> tuple[float, np.ndarray | None]:
    """Smallest constraint violation over the candidate set (<=0 means feasible)."""
    cands = _candidates(axes, tols)
    if len(cands) == 0:
        return float("inf"), None
    cosang = np.clip(np.einsum("mkj,nj->mn", cands[:, None, :], axes), -1.0, 1.0)
    margins = np.max(np.arccos(cosang) - tols[None, :], axis=1)
    k = int(np.argmin(margins))
    return float(margins[k]), cands[k]


def _polish(
    axes: np.ndarray, tols: np.ndarray, point: np.ndarray, margin: float
) -> tuple[np.ndarray, float]:
    """Locally maximise the worst-case slack; keep the best verified point."""
    from scipy.optimize import minimize as _min

    def f(p: np.ndarray) -> float:
        return cap_margin(axis_from_chart(p[0], p[1]), axes, tols)

    a0 = np.arctan2(point[1], point[0])
    b0 = np.arcsin(np.clip(point[2], -1.0, 1.0))
    best_pt, best_m = point, margin
    for start in ((a0, b0), (a0, b0 + 0.05), (a0 + 0.05, b0), (a0, b0 - 0.05)):
        opt = _min(f, np.array(start), method="Nelder-Mead",
                   options={"xatol": 1e-12, "fatol": 1e-14, "maxiter": 4000})
        cand = axis_from_chart(opt.x[0], opt.x[1])
        m = cap_margin(cand, axes, tols)
        if m < best_m:
            best_pt, best_m = cand, m
    return best_pt, best_m


def cone_feasibility_exact(axes: np.ndarray, tols: np.ndarray, tol: float = 1e-12) -> Decision:
    """Exact three-valued decision for any number of caps (all Theta < 90 deg).

    FEASIBLE     : a point of the candidate set satisfies every cap, returned
                   after being re-checked against all caps.
    INFEASIBLE   : the candidate set is exhausted, which by the lemma is a proof;
                   the returned subset is then shrunk greedily to an irreducible
                   infeasible subset (at most 4 caps by Helly's theorem on S^2).
    UNDETERMINED : only when a cap is not geodesically convex (Theta >= 90 deg).
    """
    axes = np.atleast_2d(normalize(axes))
    tols = np.asarray(tols, dtype=float)
    n = len(tols)
    if np.any(tols >= np.pi / 2):
        return Decision("undetermined", n_caps=n, detail={"reason": "non-convex cap"})
    if n == 1:
        return Decision("feasible", point=axes[0].copy(), margin=float(-tols[0]), n_caps=1,
                        detail={"method": "single"})

    margin, point = _best_candidate(axes, tols)
    if point is not None and margin <= tol:
        # A candidate on two boundaries has zero slack, which is a poor thing to
        # hand to an operator.  Maximise the worst-case slack locally; the result
        # is re-verified so this polishing step can never break soundness.
        point, margin = _polish(axes, tols, point, margin)
        verified = cap_margin(point, axes, tols)
        return Decision("feasible", point=point, margin=verified, n_caps=n,
                        detail={"method": "candidate+polish",
                                "n_candidates": len(_candidates(axes, tols))})

    # Infeasible: shrink to an irreducible subset so the witness is small.
    idx = list(range(n))
    changed = True
    while changed and len(idx) > 2:
        changed = False
        for i in list(idx):
            sub = [j for j in idx if j != i]
            m_sub, _ = _best_candidate(axes[sub], tols[sub])
            if m_sub > tol:
                idx = sub
                changed = True
                break
    return Decision(
        "infeasible",
        witness=tuple(idx),
        margin=margin,
        n_caps=n,
        detail={"method": "candidate-exhaustive", "witness_size": len(idx)},
    )
