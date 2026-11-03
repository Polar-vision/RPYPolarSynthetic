"""Real-scale test of the load-bearing assumption behind sections 9.6 and 9.10.

Sections 9.6 and 9.10 both lean on one sentence that was never checked at real
size: *at engineering tolerances the outer branch stays in the ten-thousand box
range, and the cost law is O(1/eps)*.  Every number quoted there came from
instances with a handful of constraints, a pointing box of a few degrees, and a
scalar loop over the constraint list.

This module rebuilds the same branch as a level-by-level vectorised sweep, so a
real flight-software keep-out suite (sun, moon, Earth, plumes, radiators, plus a
bright-star catalogue) can actually be run, and then measures how the box count
responds to the three things that vary in practice:

    m_eff   how many constraint boundaries actually cross the pointing box
    L       how wide the pointing box is
    eps     the resolution at which a box is declared a leaf

The bound used is the same one as ``cone_keepout._angle_bounds`` (a Lipschitz
ball on ``u . target`` with ``|grad f| <= 1/|v|``), so the completeness argument
carries over verbatim; ``check_bounds_against_scalar`` verifies the vectorised
version reproduces the scalar one to machine precision.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .cone_keepout import KeepoutScene, _tangent_frame, margin_keepout
from .pointing_prototype import normalize

__all__ = [
    "ScaleScene",
    "flight_suite",
    "star_keepouts",
    "adversarial_cluster",
    "vectorised_branch",
    "check_bounds_against_scalar",
    "scan_resolution",
    "scan_extent",
    "scan_constraint_count",
]


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------

@dataclass
class ScaleScene(KeepoutScene):
    """A keep-out suite plus the pointing cap the branch is run over."""

    label: str = ""
    pointing_tol: float = 0.0


def star_keepouts(n: int, beta_deg: float, seed: int = 0) -> np.ndarray:
    """``n`` roughly-uniform sky directions, as a stand-in for a bright-star list.

    A Fibonacci lattice plus jitter, not a real catalogue.  The bright-star sky
    is close enough to isotropic at this density that the lattice is a fair
    proxy for *how many* stars fall inside a pointing box; it is not a fair
    proxy for any individual star's position, and nothing below depends on one.
    """
    i = np.arange(n, dtype=float) + 0.5
    z = 1.0 - 2.0 * i / n
    phi = np.pi * (1.0 + 5.0 ** 0.5) * i
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    dirs = np.column_stack([r * np.cos(phi), r * np.sin(phi), z])
    rng = np.random.default_rng(seed)
    dirs = dirs + rng.normal(scale=np.deg2rad(0.5), size=dirs.shape)
    return dirs / np.linalg.norm(dirs, axis=1, keepdims=True)


def flight_suite(n_stars: int = 0, star_beta_deg: float = 2.0,
                 pointing_tol_deg: float = 1.0, seed: int = 7) -> ScaleScene:
    """A plausible flight-software suite: the named keep-outs plus a star list.

    Half-angles are the usual order of magnitude (sun 30 deg, moon 20 deg,
    Earth limb 20 deg, plume 15 deg, radiator 25 deg), not any one vehicle's
    ICD.  Directions are chosen so that some cones cut the pointing cap and
    others miss it entirely -- that mix is what decides ``m_eff``.
    """
    base = normalize(np.array([0.0, 0.0, 1.0]))
    e1, e2 = np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])

    def dir_at(az_deg: float, el_deg: float) -> np.ndarray:
        az, el = np.deg2rad(az_deg), np.deg2rad(el_deg)
        return normalize(np.cos(el) * (np.cos(az) * e1 + np.sin(az) * e2) + np.sin(el) * base)

    named = [
        ("sun", dir_at(0.0, 14.0), 30.0),
        ("moon", dir_at(140.0, 9.0), 20.0),
        ("earth", dir_at(250.0, 26.0), 20.0),
        ("plume_a", dir_at(75.0, 21.0), 15.0),
        ("plume_b", dir_at(190.0, 17.0), 15.0),
        ("plume_c", dir_at(310.0, 23.0), 15.0),
        ("radiator", dir_at(45.0, 31.0), 25.0),
    ]
    suns = [d for _, d, _ in named]
    betas = [np.deg2rad(b) for _, _, b in named]
    if n_stars:
        st = star_keepouts(n_stars, star_beta_deg, seed=seed)
        suns.extend(list(st))
        betas.extend([np.deg2rad(star_beta_deg)] * len(st))

    return ScaleScene(
        caps=base.reshape(1, 3),
        tols=np.array([np.deg2rad(pointing_tol_deg)]),
        suns=np.asarray(suns, dtype=float),
        betas=np.asarray(betas, dtype=float),
        label=f"flight+{n_stars}stars",
        pointing_tol=np.deg2rad(pointing_tol_deg),
    )


def adversarial_cluster(k: int, beta_deg: float = 1.0, ring_deg: float = 3.0,
                        pointing_tol_deg: float = 5.0, merged: bool = True) -> ScaleScene:
    """``k`` cones arranged so that every one of their boundaries crosses the cap.

    ``merged=True`` packs them on a small ring: the cones overlap, so the union
    is one blob and only its *outer* boundary survives as an interface.  ``k``
    grows, the interface length does not, and the box count should stay flat.

    ``merged=False`` spaces them ``3*beta`` apart on a large ring: now every
    cone contributes its own closed boundary, the interface length grows like
    ``k``, and the box count should grow with it.  The pair of runs separates
    "many constraints" from "long interface", which is the distinction that
    actually predicts the cost.
    """
    base = normalize(np.array([0.0, 0.0, 1.0]))
    e1, e2 = np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])
    if not merged:
        need = k * 3.0 * beta_deg / (2.0 * np.pi)
        ring_deg = max(ring_deg, need)
    ang = np.linspace(0.0, 2.0 * np.pi, k, endpoint=False)
    rho = np.deg2rad(ring_deg)
    suns = [normalize(np.cos(rho) * base + np.sin(rho) * (np.cos(a) * e1 + np.sin(a) * e2))
            for a in ang]
    return ScaleScene(
        caps=base.reshape(1, 3),
        tols=np.array([np.deg2rad(pointing_tol_deg)]),
        suns=np.asarray(suns, dtype=float),
        betas=np.full(k, np.deg2rad(beta_deg)),
        label=("cluster" if merged else "separated") + str(k),
        pointing_tol=np.deg2rad(pointing_tol_deg),
    )


# ---------------------------------------------------------------------------
# Vectorised branch
# ---------------------------------------------------------------------------

def _bounds_batch(base, e1, e2, target, x0, x1, y0, y1):
    """Vectorised twin of ``cone_keepout._angle_bounds`` (the Lipschitz ball).

    Returns (angle_lo, angle_hi) for every box at once.  Identical algebra:
    a Lipschitz ball around the centre value, with the gradient bound
    ``|grad (u.target)| <= 1/|v|`` and ``|v|`` bounded below by the distance
    from the chart origin to the box.

    Kept for the comparison in section 9.11; the width of this enclosure is
    ``O(box / sin(theta))`` after the arccos, so it degenerates near a cone's
    axis and near small half-angles.
    """
    cx = 0.5 * (x0 + x1)
    cy = 0.5 * (y0 + y1)
    hx = 0.5 * (x1 - x0)
    hy = 0.5 * (y1 - y0)
    v = base[None, :] + cx[:, None] * e1[None, :] + cy[:, None] * e2[None, :]
    nv = np.linalg.norm(v, axis=1)
    u = v / nv[:, None]
    fc = u @ target
    dx = np.maximum(0.0, np.abs(cx) - hx)
    dy = np.maximum(0.0, np.abs(cy) - hy)
    vmin = np.sqrt(1.0 + dx * dx + dy * dy)
    delta = np.hypot(hx, hy) * np.sqrt(2.0) / vmin
    lo = np.clip(fc - delta, -1.0, 1.0)
    hi = np.clip(fc + delta, -1.0, 1.0)
    return np.arccos(hi), np.arccos(lo)


def _box_geometry(base, e1, e2, x0, x1, y0, y1):
    """Per-box centre direction and angular radius -- independent of any target.

    ``rho`` bounds ``angle(u, u_c)`` over the whole box.  The four corners are
    the extreme points of the gnomonic rectangle, and the distance to a point is
    convex on the hemisphere around it, so the max over the box is at a corner.
    Both quantities are reused for every constraint at this level.
    """
    cx = 0.5 * (x0 + x1)
    cy = 0.5 * (y0 + y1)
    vc = base[None, :] + cx[:, None] * e1[None, :] + cy[:, None] * e2[None, :]
    uc = vc / np.linalg.norm(vc, axis=1, keepdims=True)

    X = np.stack([x0, x1, x0, x1], axis=1)
    Y = np.stack([y0, y0, y1, y1], axis=1)
    V = base[None, None, :] + X[..., None] * e1[None, None, :] + Y[..., None] * e2[None, None, :]
    U = V / np.linalg.norm(V, axis=2, keepdims=True)
    dot = np.einsum("bkc,bc->bk", U, uc, optimize=False)
    rho = np.max(np.arccos(np.clip(dot, -1.0, 1.0)), axis=1)
    return uc, rho


def _bounds_tri(target, uc, rho):
    """Angle enclosure by the spherical triangle inequality.

    ``|angle(u, t) - angle(u_c, t)| <= angle(u, u_c) <= rho``, so the range of
    the angle over the box is inside ``[theta_c - rho, theta_c + rho]``.

    The width is ``2 rho`` -- the box's own angular size -- whatever the target
    and wherever the box sits.  ``_bounds_batch`` instead has width
    ``O(box / sin theta)`` and ``_bounds_ia`` loses a first-order term from
    splitting ``N`` and ``D`` at different corners; both are rigorous but both
    need a finer grid than this one to resolve the same cone.
    """
    thc = np.arccos(np.clip(uc @ target, -1.0, 1.0))
    lo = np.clip(thc - rho, 0.0, np.pi)
    hi = np.clip(thc + rho, 0.0, np.pi)
    return lo, hi


def _bounds_ia(base, e1, e2, target, x0, x1, y0, y1):
    """Rigorous enclosure by interval arithmetic on the gnomonic chart.

    On the chart, ``u . target = N / D`` with ``N = a + b x + c y`` (affine,
    so its extremes are at corners) and ``D = sqrt(1 + x^2 + y^2)`` (extremes
    from the box's distance range).  Hence

        N_min / D_max  <=  u . target  <=  N_max / D_min ,

    which is exact on the numerator and only slightly loose on the
    denominator.  Compared with ``_bounds_batch`` the enclosure width stays
    ``O(box)`` in the angle instead of ``O(box / sin theta)``.

    The division has to be split by sign: when ``N < 0`` (angle past 90 deg)
    dividing by the *smaller* denominator makes the ratio more negative, so the
    two quotients swap roles.  Getting that wrong yields a bound that is too
    tight on one side, i.e. boxes certified as infeasible when they are not.
    """
    a = float(base @ target)
    b = float(e1 @ target)
    c = float(e2 @ target)
    n1 = a + b * x0 + c * y0
    n2 = a + b * x1 + c * y0
    n3 = a + b * x0 + c * y1
    n4 = a + b * x1 + c * y1
    n_min = np.minimum(np.minimum(n1, n2), np.minimum(n3, n4))
    n_max = np.maximum(np.maximum(n1, n2), np.maximum(n3, n4))

    cx = 0.5 * (x0 + x1)
    cy = 0.5 * (y0 + y1)
    hx = 0.5 * (x1 - x0)
    hy = 0.5 * (y1 - y0)
    dx = np.maximum(0.0, np.abs(cx) - hx)
    dy = np.maximum(0.0, np.abs(cy) - hy)
    d_min = np.sqrt(1.0 + dx * dx + dy * dy)
    mx = np.maximum(np.abs(x0), np.abs(x1))
    my = np.maximum(np.abs(y0), np.abs(y1))
    d_max = np.sqrt(1.0 + mx * mx + my * my)

    f_hi = np.where(n_max >= 0.0, n_max / d_min, n_max / d_max)
    f_lo = np.where(n_min >= 0.0, n_min / d_max, n_min / d_min)
    return np.arccos(np.clip(f_hi, -1.0, 1.0)), np.arccos(np.clip(f_lo, -1.0, 1.0))


@dataclass
class SweepResult:
    nodes: int = 0
    leaves_feasible: int = 0
    leaves_killed: int = 0
    leaves_at_resolution: int = 0
    depth: int = 0
    seconds: float = 0.0
    nodes_to_first_feasible: int = -1
    per_level: list[int] = field(default_factory=list)
    kill_by: dict[str, int] = field(default_factory=dict)
    truncated: bool = False
    m_eff: int = 0
    eps_deg: float = 0.0
    extent_deg: float = 0.0
    m_total: int = 0
    feasible_area_sr: float = 0.0
    killed_area_sr: float = 0.0
    resolution_area_sr: float = 0.0
    first_point: np.ndarray | None = None
    first_margin: float | None = None


def _box_area(x0, x1, y0, y1) -> np.ndarray:
    """Solid angle of the gnomonic image, to leading order (centre rule)."""
    cx = 0.5 * (x0 + x1)
    cy = 0.5 * (y0 + y1)
    return (x1 - x0) * (y1 - y0) / (1.0 + cx * cx + cy * cy) ** 1.5


def _batch_margin(scene: ScaleScene, base, e1, e2, cx, cy) -> np.ndarray:
    """``margin_keepout`` for a batch of chart points (>0 means violation)."""
    v = base[None, :] + cx[:, None] * e1[None, :] + cy[:, None] * e2[None, :]
    u = v / np.linalg.norm(v, axis=1, keepdims=True)
    caps = np.asarray(scene.caps, dtype=float)
    tols = np.asarray(scene.tols, dtype=float)
    ang = np.arccos(np.clip(u @ caps.T, -1.0, 1.0))
    m = np.max(ang - tols[None, :], axis=1)
    suns = np.asarray(scene.suns, dtype=float).reshape(-1, 3)
    if len(suns):
        betas = np.asarray(scene.betas, dtype=float).reshape(-1)
        ang = np.arccos(np.clip(u @ suns.T, -1.0, 1.0))
        m = np.maximum(m, np.max(betas[None, :] - ang, axis=1))
    return m


def vectorised_branch(
    scene: ScaleScene,
    eps_deg: float = 0.02,
    extent_deg: float = 60.0,
    max_nodes: int = 4_000_000,
    max_depth: int = 40,
    early_exit: bool = False,
    bound: str = "tri",
) -> SweepResult:
    """Breadth-first sweep of the whole pointing cap, counting every box.

    Two counts matter and they are different questions, so both are returned:

    * ``nodes`` -- boxes until the partition is complete.  This is the cost of
      the *existence* answer ("is there any feasible attitude in this cap"),
      because an infeasible verdict has to cover the domain.  The sweep keeps
      going even after a feasible cell is found, so this number is comparable
      across feasible and infeasible scenes.
    * ``nodes_to_first_feasible`` -- boxes until the first cell certified (or
      found at resolution) feasible.  This is the cost of the *point* answer
      ("give me a feasible attitude"), and it is the mode an interlock would
      use; pass ``early_exit=True`` to stop there.

    The bound is rigorous, so a killed box is genuinely infeasible and the
    partition is a certificate; ``truncated`` says the run hit ``max_nodes``
    before finishing, in which case ``nodes`` is a lower bound only.

    ``m_eff`` counts the constraints that actually killed at least one box --
    a lower bound on how many boundaries cross the cap, which is the quantity
    the box count should scale with.
    """
    import time

    t0 = time.perf_counter()
    eps = np.deg2rad(eps_deg)
    base, e1, e2 = _tangent_frame(normalize(np.array([0.0, 0.0, 1.0])))
    t = float(np.tan(np.deg2rad(extent_deg)))

    caps = np.asarray(scene.caps, dtype=float)
    cap_tols = np.asarray(scene.tols, dtype=float)
    suns = np.asarray(scene.suns, dtype=float).reshape(-1, 3)
    betas = np.asarray(scene.betas, dtype=float).reshape(-1)
    n_con = len(cap_tols) + len(betas)

    targets = np.vstack([caps, suns]) if len(suns) else caps
    tols = np.concatenate([cap_tols, betas]) if len(betas) else cap_tols
    is_keepout = np.array([False] * len(cap_tols) + [True] * len(betas))

    res = SweepResult(eps_deg=eps_deg, extent_deg=extent_deg, m_total=n_con)
    x0 = np.array([-t]); x1 = np.array([t]); y0 = np.array([-t]); y1 = np.array([t])
    depth = 0
    tol_leaf = 2.0 * np.tan(eps)
    m_eff = 0

    while x0.size and depth < max_depth:
        B = x0.size
        if res.nodes + B > max_nodes:
            res.truncated = True
            break
        res.per_level.append(int(B))

        killed = np.zeros(B, dtype=bool)
        kill_id = np.full(B, -1, dtype=int)
        satisfied = np.zeros(B, dtype=int)

        uc, rho = _box_geometry(base, e1, e2, x0, x1, y0, y1)

        for j in range(n_con):
            if bound == "tri":
                a_lo, a_hi = _bounds_tri(targets[j], uc, rho)
            elif bound == "ia":
                a_lo, a_hi = _bounds_ia(base, e1, e2, targets[j], x0, x1, y0, y1)
            else:
                a_lo, a_hi = _bounds_batch(base, e1, e2, targets[j], x0, x1, y0, y1)
            if is_keepout[j]:
                viol = a_hi < tols[j]
                ok = a_lo > tols[j]
            else:
                viol = a_lo > tols[j]
                ok = a_hi < tols[j]
            newly = viol & ~killed
            kill_id[newly] = j
            killed |= viol
            satisfied += ok

        res.nodes += B
        res.depth = depth

        nk = int(killed.sum())
        res.leaves_killed += nk
        if nk:
            res.killed_area_sr += float(_box_area(x0[killed], x1[killed], y0[killed], y1[killed]).sum())
            ids, cnt = np.unique(kill_id[killed], return_counts=True)
            for j, c in zip(ids.tolist(), cnt.tolist()):
                key = ("keepout" if is_keepout[j] else "cap") + f":{j}"
                res.kill_by[key] = res.kill_by.get(key, 0) + c
            m_eff = max(m_eff, len(ids))

        alive = ~killed
        if not alive.any():
            break

        # ---- certified feasible: every constraint holds on the whole box ---
        cert = alive & (satisfied == n_con)
        if cert.any():
            idx = np.flatnonzero(cert)
            cxv = 0.5 * (x0[idx] + x1[idx])
            cyv = 0.5 * (y0[idx] + y1[idx])
            mg = _batch_margin(scene, base, e1, e2, cxv, cyv)
            good = mg <= 0.0
            if good.any():
                res.leaves_feasible += int(good.sum())
                res.feasible_area_sr += float(
                    _box_area(x0[idx[good]], x1[idx[good]], y0[idx[good]], y1[idx[good]]).sum())
                if res.nodes_to_first_feasible < 0:
                    res.nodes_to_first_feasible = res.nodes
                    first = int(np.flatnonzero(good)[0])
                    res.first_point = _lift_one(base, e1, e2, cxv[first], cyv[first])
                    res.first_margin = float(mg[first])
                if early_exit:
                    res.seconds = time.perf_counter() - t0
                    res.m_eff = m_eff
                    return res
            alive = alive.copy()
            alive[idx[good]] = False
            if not alive.any():
                break

        # ---- boxes at target resolution ------------------------------------
        side = np.maximum(x1 - x0, y1 - y0)
        small = alive & (side <= tol_leaf)
        if small.any():
            cxv = 0.5 * (x0[small] + x1[small])
            cyv = 0.5 * (y0[small] + y1[small])
            mg = _batch_margin(scene, base, e1, e2, cxv, cyv)
            good = mg <= 0.0
            res.leaves_at_resolution += int(small.sum())
            res.resolution_area_sr += float(
                _box_area(x0[small][~good], x1[small][~good],
                          y0[small][~good], y1[small][~good]).sum())
            if good.any():
                res.leaves_feasible += int(good.sum())
                res.feasible_area_sr += float(
                    _box_area(x0[small][good], x1[small][good], y0[small][good], y1[small][good]).sum())
                if res.nodes_to_first_feasible < 0:
                    res.nodes_to_first_feasible = res.nodes
                    first = int(np.flatnonzero(good)[0])
                    res.first_point = _lift_one(base, e1, e2, cxv[first], cyv[first])
                    res.first_margin = float(mg[first])
                if early_exit:
                    res.seconds = time.perf_counter() - t0
                    res.m_eff = m_eff
                    return res
            alive = alive.copy()
            alive[np.flatnonzero(small)] = False
            if not alive.any():
                break

        sx0, sx1 = x0[alive], x1[alive]
        sy0, sy1 = y0[alive], y1[alive]
        mx = 0.5 * (sx0 + sx1)
        my = 0.5 * (sy0 + sy1)
        x0 = np.concatenate([sx0, mx, sx0, mx])
        x1 = np.concatenate([mx, sx1, mx, sx1])
        y0 = np.concatenate([sy0, sy0, my, my])
        y1 = np.concatenate([my, my, sy1, sy1])
        depth += 1

    res.seconds = time.perf_counter() - t0
    res.m_eff = m_eff
    return res


def _lift_one(base, e1, e2, x, y):
    v = base + x * e1 + y * e2
    return v / np.linalg.norm(v)


def _lift_center(base, e1, e2, x0, x1, y0, y1):
    return _lift_one(base, e1, e2, 0.5 * (x0 + x1), 0.5 * (y0 + y1))


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_bounds_ia(n: int = 300, samples: int = 40, seed: int = 11) -> float:
    """Worst violation of a bound over random boxes, by dense sampling inside.

    Returns the largest amount by which a sampled point fell outside
    ``[angle_lo, angle_hi]`` (should be 0 up to rounding).
    """
    return check_bound("ia", n=n, samples=samples, seed=seed)


def check_bound(kind: str = "tri", n: int = 300, samples: int = 40, seed: int = 11) -> float:
    """Worst conservativeness violation of one enclosure, by sampling."""
    rng = np.random.default_rng(seed)
    base, e1, e2 = _tangent_frame(normalize(np.array([0.0, 0.0, 1.0])))
    target = normalize(rng.normal(size=3))
    worst = 0.0
    for _ in range(n):
        a, b = np.sort(rng.uniform(-2.0, 2.0, 2))
        c, d = np.sort(rng.uniform(-2.0, 2.0, 2))
        x0, x1 = np.array([a]), np.array([b])
        y0, y1 = np.array([c]), np.array([d])
        if kind == "tri":
            uc, rho = _box_geometry(base, e1, e2, x0, x1, y0, y1)
            lo, hi = _bounds_tri(target, uc, rho)
        elif kind == "ia":
            lo, hi = _bounds_ia(base, e1, e2, target, x0, x1, y0, y1)
        elif kind == "lip":
            lo, hi = _bounds_batch(base, e1, e2, target, x0, x1, y0, y1)
        else:
            raise ValueError(kind)
        xs = rng.uniform(a, b, samples)
        ys = rng.uniform(c, d, samples)
        v = base[None, :] + xs[:, None] * e1[None, :] + ys[:, None] * e2[None, :]
        u = v / np.linalg.norm(v, axis=1, keepdims=True)
        ang = np.arccos(np.clip(u @ target, -1.0, 1.0))
        worst = max(worst, float(np.max(ang - hi[0])), float(np.max(lo[0] - ang)))
    return max(worst, 0.0)


def check_bounds_against_scalar(n: int = 400, seed: int = 3) -> float:
    """Max abs difference between the vectorised and scalar angle bounds."""
    from .cone_keepout import _angle_bounds

    rng = np.random.default_rng(seed)
    base, e1, e2 = _tangent_frame(normalize(np.array([0.0, 0.0, 1.0])))
    target = normalize(rng.normal(size=3))
    worst = 0.0
    for _ in range(n):
        a, b = np.sort(rng.uniform(-1.0, 1.0, 2))
        c, d = np.sort(rng.uniform(-1.0, 1.0, 2))
        lo_s, hi_s = _angle_bounds(base, e1, e2, target, (a, b, c, d))
        lo_v, hi_v = _bounds_batch(base, e1, e2, target,
                                   np.array([a]), np.array([b]),
                                   np.array([c]), np.array([d]))
        worst = max(worst, abs(lo_s - float(lo_v[0])), abs(hi_s - float(hi_v[0])))
    return worst


# ---------------------------------------------------------------------------
# Scans
# ---------------------------------------------------------------------------

def scan_resolution(eps_deg_list, extent_deg: float = 60.0, n_stars: int = 0,
                    **kw) -> list[dict]:
    """Box count against resolution -- should be O(1/eps), not O(1/eps^2)."""
    rows = []
    for eps in eps_deg_list:
        sc = flight_suite(n_stars=n_stars, pointing_tol_deg=extent_deg, **kw)
        r = vectorised_branch(sc, eps_deg=eps, extent_deg=extent_deg)
        rows.append({
            "extent_deg": extent_deg, "eps_deg": eps, "n_stars": n_stars,
            "m_total": r.m_total, "m_eff": r.m_eff,
            "nodes": r.nodes, "leaves_killed": r.leaves_killed,
            "depth": r.depth, "seconds": r.seconds,
            "nodes_to_first_feasible": r.nodes_to_first_feasible,
            "truncated": int(r.truncated),
            "nodes_times_eps": r.nodes * eps,
        })
    return rows


def scan_extent(extent_deg_list, eps_deg: float = 0.05, n_stars: int = 0, **kw) -> list[dict]:
    """Box count against pointing-cap width -- should be linear in extent."""
    rows = []
    for ext in extent_deg_list:
        sc = flight_suite(n_stars=n_stars, pointing_tol_deg=ext, **kw)
        r = vectorised_branch(sc, eps_deg=eps_deg, extent_deg=ext)
        rows.append({
            "extent_deg": ext, "eps_deg": eps_deg, "n_stars": n_stars,
            "m_total": r.m_total, "m_eff": r.m_eff,
            "nodes": r.nodes, "depth": r.depth, "seconds": r.seconds,
            "nodes_to_first_feasible": r.nodes_to_first_feasible,
            "truncated": int(r.truncated),
        })
    return rows


def scan_constraint_count(star_counts, eps_deg: float = 0.05, extent_deg: float = 60.0) -> list[dict]:
    """Box count and wall time against suite size -- count flat, time linear."""
    rows = []
    for n_star in star_counts:
        sc = flight_suite(n_stars=n_star, pointing_tol_deg=extent_deg)
        r = vectorised_branch(sc, eps_deg=eps_deg, extent_deg=extent_deg)
        rows.append({
            "n_stars": n_star, "m_total": r.m_total, "m_eff": r.m_eff,
            "nodes": r.nodes, "depth": r.depth, "seconds": r.seconds,
            "us_per_box_per_constraint": 1e6 * r.seconds / max(r.nodes * r.m_total, 1),
            "nodes_to_first_feasible": r.nodes_to_first_feasible,
            "truncated": int(r.truncated),
        })
    return rows


def scan_adversarial(ks, beta_deg: float = 0.5, eps_deg: float = 0.02,
                     extent_deg: float = 30.0, merged: bool = False) -> list[dict]:
    """Box count against the number of closed boundaries in the cap."""
    rows = []
    for k in ks:
        sc = adversarial_cluster(k, beta_deg=beta_deg, pointing_tol_deg=extent_deg,
                                 merged=merged)
        r = vectorised_branch(sc, eps_deg=eps_deg, extent_deg=extent_deg)
        rows.append({
            "k": k, "beta_deg": beta_deg, "eps_deg": eps_deg,
            "extent_deg": extent_deg, "merged": int(merged), "m_eff": r.m_eff,
            "nodes": r.nodes, "depth": r.depth, "seconds": r.seconds,
            "nodes_per_boundary": r.nodes / max(k, 1),
            "truncated": int(r.truncated),
        })
    return rows
