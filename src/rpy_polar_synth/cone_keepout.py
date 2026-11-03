"""Keep-out cones (sun avoidance) and why the candidate-set lemma stops applying.

The pointing decision of `pointing_prototype.cone_feasibility_exact` assumes every
constraint is a cap ``{u : angle(u, a_i) <= rho_i}`` with ``rho_i < 90 deg``, i.e.
a geodesically convex piece of the sphere.  A sun-avoidance constraint is the
opposite: the boresight must stay *outside* a cap of half-angle ``beta``,

    F = (C_1 & ... & C_n)  \  (D_1 | ... | D_m),
    D_j = {u : angle(u, s_j) <= beta_j}.

Three facts drive everything below.

(1)  Set-theoretically a keep-out is still a cap: ``D_j^c = cap(-s_j, pi - beta_j)``.
     So the *set* needs no new representation -- only the algorithm does.

(2)  That cap is convex iff ``pi - beta <= 90 deg``, i.e. iff ``beta >= 90 deg``.
     Hence the existing exact machinery covers sun exclusions of 90 deg and wider
     verbatim, and provably cannot cover anything narrower: for ``beta < 90`` the
     feasible set is a sphere with a bite taken out of it, which is not
     geodesically convex.

(3)  Convexity is exactly what makes the candidate set complete.  Its proof
     (see the lemma in pointing_prototype) uses that a feasible set with empty
     interior is an arc whose endpoints lie on two boundaries, and that Helly's
     theorem on S^2 caps has number 4.  Neither survives the complement.  The
     failure is not cosmetic: an infeasible instance can have an irreducible
     witness of arbitrary size, because "infeasible" now means "P is covered by
     a union of caps", and a minimal cover has no bounded size.

What replaces it.  The decision itself stays cheap if one branches on the
constraint that kills each region: split a box of the tangent chart, and either
certify the whole box feasible, or attribute the whole box to one violated
constraint, or split again.  That gives a constructive point in the feasible
case and a covering certificate (a partition, each cell tagged with the
constraint that excludes it) in the infeasible case.  The certificate is
numeric rather than combinatorial: it is resolution-limited, and there is no
minimal witness.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .pointing_prototype import (
    Decision,
    angle_between,
    cap_margin,
    cone_feasibility_exact,
    normalize,
)

__all__ = [
    "KeepoutScene",
    "keepout_as_cap",
    "is_convex_regime",
    "feasibility_capform",
    "feasibility_blind_candidates",
    "feasibility_keepout",
    "margin_keepout",
    "minimal_witness_size",
]


@dataclass
class KeepoutScene:
    """A pointing box plus a list of forbidden cones."""

    caps: np.ndarray          # (n, 3) cap centres
    tols: np.ndarray          # (n,)   cap half-angles, radians
    suns: np.ndarray          # (m, 3) forbidden-cone centres
    betas: np.ndarray         # (m,)   forbidden half-angles, radians

    @property
    def n_caps(self) -> int:
        return int(self.caps.shape[0])

    @property
    def n_keepouts(self) -> int:
        return int(self.suns.shape[0])


def keepout_as_cap(sun: np.ndarray, beta: float) -> tuple[np.ndarray, float]:
    """The complement of a keep-out cone, written as one cap."""
    return -normalize(np.asarray(sun, dtype=float)), np.pi - float(beta)


def is_convex_regime(betas: np.ndarray) -> bool:
    """True when every keep-out is wide enough to stay convex after complementation."""
    return bool(np.all(np.asarray(betas, dtype=float) >= np.pi / 2 - 1e-12))


def margin_keepout(u: np.ndarray, scene: KeepoutScene) -> float:
    """Max violation; <= 0 means feasible.  Caps: angle - rho.  Keep-outs: beta - angle."""
    capped = cap_margin(u, scene.caps, scene.tols)
    if scene.n_keepouts == 0:
        return capped
    ang = np.arccos(np.clip(scene.suns @ normalize(u), -1.0, 1.0))
    return float(max(capped, np.max(scene.betas - ang)))


def feasibility_capform(scene: KeepoutScene) -> Decision:
    """The framework as it stands, applied to the cap form of the keep-outs.

    Returns 'undetermined' whenever a keep-out is narrower than 90 deg, which is
    the implementation being honest about its own convexity assumption rather
    than a bug.
    """
    axes = [np.asarray(a, dtype=float) for a in scene.caps]
    tols = [float(t) for t in scene.tols]
    for s, b in zip(scene.suns, scene.betas):
        c, t = keepout_as_cap(s, b)
        axes.append(c)
        tols.append(t)
    dec = cone_feasibility_exact(np.asarray(axes), np.asarray(tols))
    dec.detail["convex_regime"] = is_convex_regime(scene.betas)
    dec.detail["keepout_as_cap_radii_deg"] = [180.0 - np.rad2deg(b) for b in scene.betas]
    return dec


def feasibility_blind_candidates(scene: KeepoutScene) -> Decision:
    """The candidate set applied with the convexity guard switched off.

    This is the natural way to "just add the sun cone" and it is what an
    implementation without the guard would do.  Included to show what breaks.
    """
    from .pointing_prototype import _best_candidate, _polish

    axes = [np.asarray(a, dtype=float) for a in scene.caps]
    tols = [float(t) for t in scene.tols]
    for s, b in zip(scene.suns, scene.betas):
        c, t = keepout_as_cap(s, b)
        axes.append(c)
        tols.append(t)
    axes = np.asarray(axes)
    tols = np.asarray(tols)
    if len(tols) == 1:
        return Decision("feasible", point=axes[0].copy(), margin=float(-tols[0]), n_caps=1)

    margin, point = _best_candidate(axes, tols)
    if point is not None and margin <= 1e-9:
        point, _ = _polish(axes, tols, point, margin)
        return Decision("feasible", point=point, margin=margin_keepout(point, scene),
                        n_caps=len(tols), detail={"method": "blind-candidate"})
    return Decision("infeasible", margin=margin, n_caps=len(tols),
                    detail={"method": "blind-candidate", "witness_size": len(tols)})


# ---------------------------------------------------------------------------
# Outer branching on the tangent chart
# ---------------------------------------------------------------------------

@dataclass
class BranchResult:
    decision: Decision
    nodes: int = 0
    leaves: int = 0
    depth: int = 0
    pruned_by: dict[str, int] = field(default_factory=dict)
    unresolved: int = 0


def _tangent_frame(base: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    base = normalize(np.asarray(base, dtype=float))
    tmp = np.array([0.0, 0.0, 1.0]) if abs(base[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = normalize(np.cross(tmp, base))
    e2 = np.cross(base, e1)
    return base, e1, e2


def _lift(base, e1, e2, x, y):
    v = base + x * e1 + y * e2
    return v / np.linalg.norm(v)


def _angle_bounds(base, e1, e2, target, box) -> tuple[float, float]:
    """Rigorous (min, max) of angle(u, target) over the chart box.

    ``f(x, y) = u(x, y) . target`` has |grad f| <= 1 / |v|, and |v| is bounded
    below by the distance from the origin to the rectangle, so a Lipschitz ball
    around the centre value is a valid enclosure.
    """
    x0, x1, y0, y1 = box
    cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    hx, hy = 0.5 * (x1 - x0), 0.5 * (y1 - y0)
    dx = max(0.0, abs(cx) - hx)
    dy = max(0.0, abs(cy) - hy)
    vmin = float(np.sqrt(1.0 + dx * dx + dy * dy))
    fc = float(_lift(base, e1, e2, cx, cy) @ target)
    delta = np.hypot(hx, hy) * np.sqrt(2.0) / vmin
    lo = max(-1.0, fc - delta)
    hi = min(1.0, fc + delta)
    return float(np.arccos(hi)), float(np.arccos(lo))


def feasibility_keepout(
    scene: KeepoutScene,
    eps_deg: float = 0.02,
    max_nodes: int = 300000,
    max_depth: int = 60,
) -> BranchResult:
    """Decide the non-convex feasibility question by branching on violated constraints.

    Each surviving box is either certified feasible (every constraint holds on
    the whole box) or attributed to one constraint that fails on the whole box.
    A box that is neither is split.  Hence the infeasible answer comes with a
    partition of the search domain, each cell tagged with its excluding
    constraint -- a numeric certificate, not an irreducible witness.
    """
    eps = np.deg2rad(eps_deg)
    base = normalize(np.average(scene.caps, axis=0))
    radius = float(np.max(np.arccos(np.clip(scene.caps @ base, -1.0, 1.0)) + scene.tols))
    radius = min(radius + 1e-9, np.deg2rad(70.0))
    t = float(np.tan(radius))
    b_, e1, e2 = _tangent_frame(base)

    caps_axes = np.asarray(scene.caps, dtype=float)
    caps_tols = np.asarray(scene.tols, dtype=float)
    sun_axes = np.asarray(scene.suns, dtype=float).reshape(-1, 3) if scene.n_keepouts else np.zeros((0, 3))
    betas = np.asarray(scene.betas, dtype=float).reshape(-1)

    stack = [(-t, t, -t, t, 0)]
    nodes = 0
    leaves = 0
    pruned: dict[str, int] = {}
    deepest = 0
    unresolved = 0

    while stack:
        box = stack.pop()
        x0, x1, y0, y1, depth = box
        nodes += 1
        deepest = max(deepest, depth)
        geom = (x0, x1, y0, y1)

        kill = None
        satisfied = 0
        for i in range(len(caps_tols)):
            a_lo, a_hi = _angle_bounds(b_, e1, e2, caps_axes[i], geom)
            if a_lo > caps_tols[i]:
                kill = ("cap", i)
                break
            if a_hi < caps_tols[i]:
                satisfied += 1
        if kill is None:
            for j in range(len(betas)):
                a_lo, a_hi = _angle_bounds(b_, e1, e2, sun_axes[j], geom)
                if a_hi < betas[j]:
                    kill = ("keepout", j)
                    break
                if a_lo > betas[j]:
                    satisfied += 1

        if kill is not None:
            leaves += 1
            key = f"{kill[0]}:{kill[1]}"
            pruned[key] = pruned.get(key, 0) + 1
            continue

        n_con = len(caps_tols) + len(betas)
        if satisfied == n_con:
            cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
            point = _lift(b_, e1, e2, cx, cy)
            m = margin_keepout(point, scene)
            if m <= 0.0:
                return BranchResult(
                    Decision("feasible", point=point, margin=m, n_caps=n_con,
                             detail={"method": "branch", "certified_box": True}),
                    nodes=nodes, leaves=leaves, depth=deepest, pruned_by=pruned,
                )
            continue

        cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if max(x1 - x0, y1 - y0) <= 2.0 * np.tan(eps):
            leaves += 1
            point = _lift(b_, e1, e2, cx, cy)
            if margin_keepout(point, scene) <= 0.0:
                return BranchResult(
                    Decision("feasible", point=point, margin=margin_keepout(point, scene),
                             n_caps=n_con, detail={"method": "branch", "certified_box": False}),
                    nodes=nodes, leaves=leaves, depth=deepest, pruned_by=pruned,
                )
            continue

        if depth >= max_depth or nodes >= max_nodes:
            unresolved += 1
            continue

        stack.append((x0, cx, y0, cy, depth + 1))
        stack.append((cx, x1, y0, cy, depth + 1))
        stack.append((x0, cx, cy, y1, depth + 1))
        stack.append((cx, x1, cy, y1, depth + 1))

    kind = "infeasible" if unresolved == 0 else "undetermined"
    return BranchResult(
        Decision(kind, margin=float("nan"),
                 n_caps=len(caps_tols) + len(betas),
                 detail={"method": "branch", "unresolved_boxes": unresolved,
                         "covering_cells": sum(pruned.values())}),
        nodes=nodes, leaves=leaves, depth=deepest, pruned_by=pruned, unresolved=unresolved,
    )


def minimal_witness_size(scene: KeepoutScene, max_size: int = 6, **kw) -> int:
    """Smallest subset of constraints that is already infeasible (-1 if none up to max_size)."""
    from itertools import combinations

    n = scene.n_caps + scene.n_keepouts
    for k in range(2, min(max_size, n) + 1):
        for idx in combinations(range(n), k):
            cap_idx = [i for i in idx if i < scene.n_caps]
            sun_idx = [i - scene.n_caps for i in idx if i >= scene.n_caps]
            sub = KeepoutScene(
                caps=scene.caps[cap_idx] if cap_idx else np.zeros((0, 3)),
                tols=scene.tols[cap_idx] if cap_idx else np.zeros(0),
                suns=scene.suns[sun_idx] if sun_idx else np.zeros((0, 3)),
                betas=scene.betas[sun_idx] if sun_idx else np.zeros(0),
            )
            if sub.n_caps == 0:
                continue
            res = feasibility_keepout(sub, **kw)
            if res.decision.kind == "infeasible":
                return k
    return -1
