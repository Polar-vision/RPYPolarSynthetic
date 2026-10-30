"""Empirical test of the three scenarios claimed for the geometric layer.

Section 9.13 closed the door on ordinary next-best-view and pose-estimation
value.  Three scenarios remained where a complete, certifying existence query
might still be worth something:

    A  multi-camera / multi-sensor placement: does an installation direction
       exist that simultaneously covers every assigned target and avoids every
       obstacle and forbidden-view cone?
    B  inspection-plan pruning: a plan is a sequence of waypoints, each with a
       reachable cone (joint limits), occluder keep-outs and a lighting cap;
       a planner wants infeasible plans removed *soundly*;
    C  a safety shell around a learned proposer: the network proposes a
       direction, the geometric layer verifies it exactly, and when it rejects,
       answers whether a repair exists inside a bounded deviation cap.

The comparison is always the same pair.  Grid sampling (standard practice)
evaluates the constraints exactly at cell centres: its YES is exact but its NO
is forever inconclusive, and a feasible set narrower than one cell vanishes.
The branch of section 9 carries a rigorous two-sided bound, so its YES is
exact, its NO is a proof whenever the undecided residue reaches zero, and the
residue itself quantifies the remaining doubt when it is not.

Truth convention.  A YES is only ever recorded from a certified point, so it
is exact for both methods.  A NO truth is taken from the branch only when the
undecided residue is exactly zero -- a mathematical proof, stronger than any
grid.  Scenes where the fine branch leaves a non-zero residue are reported as
UNKNOWN and excluded from accuracy counts (there are essentially none for the
margin-ful random scenes used here).
"""

from __future__ import annotations

from dataclasses import dataclass
import time

import numpy as np

from .branch_scale import ScaleScene, vectorised_branch
from .cone_keepout import _tangent_frame
from .pointing_prototype import normalize

DEG = np.pi / 180.0
Z = np.array([0.0, 0.0, 1.0])

__all__ = [
    "dir_at",
    "rot_to_z",
    "chart_points",
    "scene_margins",
    "grid_verdict",
    "branch_verdict",
    "random_placement_scene",
    "lens_scene",
    "run_placement_random",
    "run_lens_sweep",
    "random_waypoint_scene",
    "run_plan_pruning",
    "run_safety_shell",
]


# ---------------------------------------------------------------------------
# shared geometry helpers
# ---------------------------------------------------------------------------

def dir_at(base: np.ndarray, e1: np.ndarray, e2: np.ndarray,
           rho_deg: float, az_deg: float) -> np.ndarray:
    """Unit vector at angular distance ``rho_deg`` and azimuth ``az_deg``."""
    rho, az = rho_deg * DEG, az_deg * DEG
    return normalize(
        np.cos(rho) * base + np.sin(rho) * (np.cos(az) * e1 + np.sin(az) * e2)
    )


def rot_to_z(axis: np.ndarray) -> np.ndarray:
    """Rotation matrix taking ``axis`` to the z axis (Rodrigues)."""
    a = normalize(np.asarray(axis, dtype=float))
    v = np.cross(a, Z)
    c = float(a @ Z)
    s = np.linalg.norm(v)
    if s < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    kx = np.array([[0.0, -v[2], v[1]], [v[2], 0.0, -v[0]], [-v[1], v[0], 0.0]])
    return np.eye(3) + kx + kx @ kx * (1.0 - c) / (s * s)


def rotate_scene(scene: ScaleScene, r: np.ndarray) -> ScaleScene:
    caps = np.asarray(scene.caps, dtype=float) @ r.T
    suns = np.asarray(scene.suns, dtype=float).reshape(-1, 3) @ r.T
    return ScaleScene(caps=caps, tols=np.asarray(scene.tols, dtype=float),
                      suns=suns, betas=np.asarray(scene.betas, dtype=float),
                      label=scene.label, pointing_tol=scene.pointing_tol)


def chart_points(axis: np.ndarray, extent_deg: float, step_deg: float):
    """Cell-centre gnomonic grid over ``cap(axis, extent_deg)``."""
    base, e1, e2 = _tangent_frame(normalize(np.asarray(axis, dtype=float)))
    t = float(np.tan(extent_deg * DEG))
    n = max(1, int(np.ceil(2.0 * t / np.tan(step_deg * DEG))))
    coords = -t + (np.arange(n) + 0.5) * (2.0 * t / n)
    xx, yy = np.meshgrid(coords, coords, indexing="xy")
    v = (base[None, None, :] + xx[..., None] * e1[None, None, :]
         + yy[..., None] * e2[None, None, :])
    u = v / np.linalg.norm(v, axis=2, keepdims=True)
    return u.reshape(-1, 3)


def scene_margins(scene: ScaleScene, u: np.ndarray) -> np.ndarray:
    """Signed margin at each direction; positive means violation."""
    caps = np.asarray(scene.caps, dtype=float)
    tols = np.asarray(scene.tols, dtype=float)
    m = np.max(np.arccos(np.clip(u @ caps.T, -1.0, 1.0)) - tols[None, :], axis=1)
    suns = np.asarray(scene.suns, dtype=float).reshape(-1, 3)
    if len(suns):
        betas = np.asarray(scene.betas, dtype=float).reshape(-1)
        mk = np.max(betas[None, :] - np.arccos(np.clip(u @ suns.T, -1.0, 1.0)),
                    axis=1)
        m = np.maximum(m, mk)
    return m


# ---------------------------------------------------------------------------
# the two competitors
# ---------------------------------------------------------------------------

def grid_verdict(scene: ScaleScene, axis: np.ndarray, extent_deg: float,
                 step_deg: float) -> dict:
    """Standard practice: sample, evaluate exactly, report what was found."""
    t0 = time.perf_counter()
    u = chart_points(axis, extent_deg, step_deg)
    m = scene_margins(scene, u)
    i = int(np.argmin(m))
    return {
        "feasible": bool(m[i] <= 0.0),       # YES is exact; NO is inconclusive
        "n_points": len(u),
        "best_margin_deg": float(m[i] / DEG),
        "seconds": time.perf_counter() - t0,
    }


def branch_verdict(scene: ScaleScene, extent_deg: float, eps_deg: float,
                   axis: np.ndarray | None = None,
                   max_nodes: int = 4_000_000) -> dict:
    """Certifying existence query.

    ``verdict`` is YES (certified point found), NO_PROVEN (the partition
    killed every box: a proof) or NO_RESIDUE (nothing found, but an undecided
    frontier of ``residue_sr`` steradians remains -- the method *says so*,
    which is itself the difference from a grid).
    """
    if axis is not None:
        scene = rotate_scene(scene, rot_to_z(axis))
    r = vectorised_branch(scene, eps_deg=eps_deg, extent_deg=extent_deg,
                          max_nodes=max_nodes, early_exit=False, bound="tri")
    if r.leaves_feasible > 0:
        verdict = "YES"
    elif r.leaves_at_resolution == 0 and not r.truncated:
        verdict = "NO_PROVEN"
    else:
        verdict = "NO_RESIDUE"
    return {
        "verdict": verdict,
        "nodes": r.nodes,
        "residue_sr": float(r.resolution_area_sr),
        "seconds": r.seconds,
        "truncated": bool(r.truncated),
        "first_point": r.first_point,
        "first_margin_deg": (None if r.first_margin is None
                             else float(r.first_margin / DEG)),
    }


# ---------------------------------------------------------------------------
# A -- multi-camera / multi-sensor placement
# ---------------------------------------------------------------------------

def random_placement_scene(rng: np.random.Generator, extent_deg: float = 20.0,
                           tightness: float = 1.0) -> ScaleScene:
    """One sensor's installation-direction problem.

    Coverage: the direction must fall inside every assigned target cap.
    Avoidance: obstacle and forbidden-view keep-outs.  ``tightness`` scales
    the keep-out radii to move the feasible/infeasible mix.
    """
    base, e1, e2 = _tangent_frame(Z)
    caps = [Z.copy()]
    tols = [extent_deg * DEG]
    for _ in range(int(rng.integers(2, 4))):
        a = dir_at(base, e1, e2, rng.uniform(0.0, 12.0),
                   rng.uniform(0.0, 360.0))
        caps.append(a)
        tols.append(rng.uniform(8.0, 18.0) * DEG)
    n_ko = int(rng.integers(2, 5))
    suns = [dir_at(base, e1, e2, rng.uniform(0.0, 18.0),
                   rng.uniform(0.0, 360.0)) for _ in range(n_ko)]
    betas = rng.uniform(3.0, 10.0, n_ko) * DEG * tightness
    return ScaleScene(caps=np.asarray(caps), tols=np.asarray(tols),
                      suns=np.asarray(suns), betas=np.asarray(betas),
                      label="placement", pointing_tol=extent_deg * DEG)


def lens_scene(width_deg: float, r_deg: float = 5.0, extent_deg: float = 10.0
               ) -> ScaleScene:
    """Feasible set is a lens of two caps with controlled width ``width_deg``.

    The two cap axes sit at +/-(r - w/2) around the origin; for w > 0 the
    intersection is a lens of radial width ``w`` and length about
    ``2*sqrt(2*R*w)``; for w < 0 the caps are disjoint and the scene is
    infeasible with margin |w|.  An off-axis keep-out is added so the scene
    is not a pure two-cap toy.
    """
    base, e1, e2 = _tangent_frame(Z)
    half = r_deg - 0.5 * width_deg
    caps = [Z.copy(),
            dir_at(base, e1, e2, half, 0.0),
            dir_at(base, e1, e2, half, 180.0)]
    tols = [extent_deg * DEG, r_deg * DEG, r_deg * DEG]
    suns = [dir_at(base, e1, e2, 6.0, 90.0)]
    betas = [2.0 * DEG]
    return ScaleScene(caps=np.asarray(caps), tols=np.asarray(tols),
                      suns=np.asarray(suns), betas=np.asarray(betas),
                      label=f"lens{ width_deg:+.3f}",
                      pointing_tol=extent_deg * DEG)


def run_placement_random(seed: int = 5, per_tightness: int = 30,
                         extent_deg: float = 20.0,
                         grid_steps=(1.0, 0.5, 0.25),
                         branch_eps: float = 0.1,
                         truth_eps: float = 0.03) -> list[dict]:
    """Random placement scenes: verdict accuracy of grids vs the branch."""
    rng = np.random.default_rng(seed)
    rows = []
    sid = 0
    for tightness in (0.7, 1.0, 1.3):
        for _ in range(per_tightness):
            scene = random_placement_scene(rng, extent_deg, tightness)
            truth = branch_verdict(scene, extent_deg, truth_eps)
            row = {
                "scene": sid, "tightness": tightness,
                "truth": truth["verdict"],
                "truth_nodes": truth["nodes"],
                "truth_seconds": truth["seconds"],
            }
            for step in grid_steps:
                g = grid_verdict(scene, Z, extent_deg, step)
                row[f"grid{step}_yes"] = int(g["feasible"])
                row[f"grid{step}_s"] = g["seconds"]
            b = branch_verdict(scene, extent_deg, branch_eps)
            row["branch_verdict"] = b["verdict"]
            row["branch_nodes"] = b["nodes"]
            row["branch_s"] = b["seconds"]
            rows.append(row)
            sid += 1
    return rows


def blob_scene(width_deg: float, rng: np.random.Generator, r_deg: float = 5.0,
               extent_deg: float = 10.0) -> ScaleScene:
    """Feasible set is a small *blob*, not a thin lens: three caps whose axes
    sit on a 120 deg ring leave a rounded-triangle intersection of diameter
    about ``width_deg`` (positive) or nothing (negative).

    The lens scene taught the wrong lesson if left alone: a grid misses a
    feasible set by *area*, not by width, and a 0.02 deg wide but 0.9 deg
    long lens has plenty of area.  The blob is the honest adversary.  Its
    centre is placed at a random offset inside the search cap, so a grid
    augmented with the cap centre gains nothing.
    """
    base, e1, e2 = _tangent_frame(Z)
    centre = dir_at(base, e1, e2, rng.uniform(1.0, 6.0), rng.uniform(0.0, 360.0))
    cb, c1, c2 = _tangent_frame(centre)
    az0 = rng.uniform(0.0, 360.0)
    half = r_deg - 0.5 * width_deg
    caps = [Z.copy()] + [dir_at(cb, c1, c2, half, az0 + 120.0 * k) for k in range(3)]
    tols = [extent_deg * DEG] + [r_deg * DEG] * 3
    suns = [dir_at(base, e1, e2, 8.5, 45.0)]  # stays >= 1 deg clear of the blob
    betas = [1.5 * DEG]
    return ScaleScene(caps=np.asarray(caps), tols=np.asarray(tols),
                      suns=np.asarray(suns), betas=np.asarray(betas),
                      label=f"blob{width_deg:+.3f}", pointing_tol=extent_deg * DEG)


def run_lens_sweep(widths_deg=(0.5, 0.2, 0.1, 0.05, 0.02,
                               -0.02, -0.05, -0.1, -0.2),
                   blob_widths_deg=(0.5, 0.2, 0.1, 0.05, 0.02,
                                    -0.02, -0.05, -0.1),
                   blob_seeds: int = 8,
                   extent_deg: float = 10.0,
                   grid_steps=(0.5, 0.25, 0.1),
                   branch_eps: float = 0.01) -> list[dict]:
    """Narrow-feature scenes: where the grid's NO is wrong, and what a proof costs.

    Two shapes.  ``lens`` rows (thin but long) show grids do *not* miss
    narrow features per se; ``blob`` rows (small in both dimensions, random
    location, several seeds per width) show the failure mode that survives:
    feasible pockets smaller than one cell.  Positive widths are feasible by
    construction, negative widths infeasible with margin |w|.  The branch
    runs at an eps below the narrowest positive width.
    """
    rows = []

    def fill(scene, w, shape, tag):
        row = {"shape": shape, "width_deg": w, "instance": tag,
               "truth": "YES" if w > 0 else "NO"}
        for step in grid_steps:
            g = grid_verdict(scene, Z, extent_deg, step)
            row[f"grid{step}_yes"] = int(g["feasible"])
            row[f"grid{step}_s"] = g["seconds"]
        b = branch_verdict(scene, extent_deg, branch_eps)
        row["branch_verdict"] = b["verdict"]
        row["branch_nodes"] = b["nodes"]
        row["branch_s"] = b["seconds"]
        row["branch_residue_sr"] = b["residue_sr"]
        rows.append(row)

    for w in widths_deg:
        fill(lens_scene(w, extent_deg=extent_deg), w, "lens", 0)
    for w in blob_widths_deg:
        for s in range(blob_seeds):
            rng = np.random.default_rng(1000 + 97 * s + int(abs(w) * 1000))
            fill(blob_scene(w, rng, extent_deg=extent_deg), w, "blob", s)
    return rows


# ---------------------------------------------------------------------------
# B -- inspection-plan pruning
# ---------------------------------------------------------------------------

def random_waypoint_scene(rng: np.random.Generator, light: np.ndarray,
                          kind: str = "normal") -> tuple[ScaleScene, np.ndarray, float, str]:
    """One waypoint's viewing-direction problem.

    Returns (scene, reachable-cone axis, cone radius, truth label).  ``kind``
    is "normal" (truth from a dense grid), "barely" (a 0.3 deg lens,
    feasible by construction) or "infeasible" (a -0.25 deg lens, infeasible
    by construction).
    """
    base, e1, e2 = _tangent_frame(Z)
    b = dir_at(base, e1, e2, rng.uniform(0.0, 30.0), rng.uniform(0.0, 360.0))
    rho = rng.uniform(15.0, 28.0)
    fb, f1, f2 = _tangent_frame(b)
    if kind in ("barely", "infeasible"):
        w = 0.3 if kind == "barely" else -0.25
        r = 3.0
        az = rng.uniform(0.0, 360.0)
        half = r - 0.5 * w
        caps = [b, dir_at(fb, f1, f2, half, az), dir_at(fb, f1, f2, half, az + 180.0)]
        tols = [rho * DEG, r * DEG, r * DEG]
        suns = [dir_at(fb, f1, f2, rng.uniform(6.0, 10.0), az + 90.0)]
        betas = [2.0 * DEG]
        truth = "YES" if w > 0 else "NO"
    else:
        caps = [b, light]
        tols = [rho * DEG, 75.0 * DEG]
        n_occ = int(rng.integers(1, 4))
        suns = [dir_at(fb, f1, f2, rng.uniform(0.0, rho), rng.uniform(0.0, 360.0))
                for _ in range(n_occ)]
        betas = (rng.uniform(2.0, 8.0, n_occ) * DEG).tolist()
        truth = "?"
    scene = ScaleScene(caps=np.asarray(caps), tols=np.asarray(tols),
                       suns=np.asarray(suns), betas=np.asarray(betas),
                       label=f"wp_{kind}", pointing_tol=rho * DEG)
    return scene, b, float(rho), truth


def run_plan_pruning(seed: int = 9, n_plans: int = 36, waypoints: int = 6,
                     grid_step: float = 0.5, branch_eps: float = 0.05,
                     truth_step: float = 0.04) -> tuple[list[dict], list[dict]]:
    """Prune multi-waypoint inspection plans; count valid plans each method loses.

    Plan mix: normal plans, plans with one barely-feasible waypoint, plans
    with one constructed-infeasible waypoint.  A plan is feasible iff every
    waypoint is feasible.
    """
    rng = np.random.default_rng(seed)
    _, e1, e2 = _tangent_frame(Z)
    light = dir_at(Z, e1, e2, 50.0, 30.0)

    wp_rows, plan_rows = [], []
    for p in range(n_plans):
        kind = "normal" if p % 3 else ("barely" if (p // 3) % 2 else "infeasible")
        special = int(rng.integers(0, waypoints)) if kind != "normal" else -1
        plan_truth, plan_grid, plan_branch = True, True, True
        t_grid = t_branch = 0.0
        for w_i in range(waypoints):
            k = kind if w_i == special else "normal"
            scene, b, rho, truth = random_waypoint_scene(rng, light, k)
            if truth == "?":
                u = chart_points(b, rho, truth_step)
                truth = "YES" if (scene_margins(scene, u) <= 0.0).any() else "NO"
            g = grid_verdict(scene, b, rho, grid_step)
            br = branch_verdict(scene, rho, branch_eps, axis=b)
            t_grid += g["seconds"]
            t_branch += br["seconds"]
            g_yes = g["feasible"]
            b_yes = br["verdict"] == "YES"
            wp_rows.append({
                "plan": p, "waypoint": w_i, "kind": k, "truth": truth,
                "grid_yes": int(g_yes), "branch_verdict": br["verdict"],
                "branch_nodes": br["nodes"],
                "grid_wrong": int(g_yes != (truth == "YES")),
                "branch_wrong": int(b_yes != (truth == "YES")),
            })
            plan_truth &= truth == "YES"
            plan_grid &= g_yes
            plan_branch &= b_yes
        plan_rows.append({
            "plan": p, "kind": kind, "truth_feasible": int(plan_truth),
            "grid_feasible": int(plan_grid), "branch_feasible": int(plan_branch),
            "grid_seconds": t_grid, "branch_seconds": t_branch,
        })
    return plan_rows, wp_rows


# ---------------------------------------------------------------------------
# C -- safety shell around a learned proposer
# ---------------------------------------------------------------------------

def _shell_scene() -> ScaleScene:
    """Fixed installation scene: two coverage caps plus four keep-outs."""
    base, e1, e2 = _tangent_frame(Z)
    caps = [Z.copy(),
            dir_at(base, e1, e2, 8.0, 40.0),
            dir_at(base, e1, e2, 10.0, 200.0)]
    tols = [30.0 * DEG, 16.0 * DEG, 14.0 * DEG]
    suns = [dir_at(base, e1, e2, 12.0, 100.0),
            dir_at(base, e1, e2, 15.0, 250.0),
            dir_at(base, e1, e2, 6.0, 320.0),
            dir_at(base, e1, e2, 18.0, 10.0)]
    betas = [5.0 * DEG, 7.0 * DEG, 4.0 * DEG, 8.0 * DEG]
    return ScaleScene(caps=np.asarray(caps), tols=np.asarray(tols),
                      suns=np.asarray(suns), betas=np.asarray(betas),
                      label="shell", pointing_tol=30.0 * DEG)


def run_safety_shell(seed: int = 17, n_proposals: int = 300,
                     repair_delta_deg: float = 5.0,
                     grid_steps=(0.5, 0.3),
                     branch_eps: float = 0.05,
                     truth_step: float = 0.02) -> tuple[list[dict], dict]:
    """NN proposes, the geometric layer verifies, then answers repairability.

    Stage 1 (point check) is exact and trivially cheap for *every* method --
    it is kept in the protocol to say so honestly, not as a comparison.
    Stage 2 (does a repair exist within ``repair_delta_deg`` of the rejected
    proposal?) is an existence query and is where the methods differ.
    """
    rng = np.random.default_rng(seed)
    scene = _shell_scene()

    # Feasible pool from a dense reference grid (stage-1 acceptance baseline).
    u_dense = chart_points(Z, 30.0, 0.1)
    m_dense = scene_margins(scene, u_dense)
    feas_pool = u_dense[m_dense <= -0.2 * DEG]
    if not len(feas_pool):
        raise RuntimeError("shell scene has no comfortably feasible points")

    rows = []
    n_type = {"noisy": 0, "uniform": 0, "boundary": 0}
    for i in range(n_proposals):
        kind = ["noisy", "uniform", "boundary"][i % 3]
        n_type[kind] += 1
        if kind == "uniform":
            u = normalize(rng.normal(size=3) + 3.0 * Z)
            if u[2] < np.cos(30.0 * DEG):
                u = chart_points(Z, 30.0, 5.0)[rng.integers(0, 100)]
        else:
            p = feas_pool[rng.integers(0, len(feas_pool))]
            if kind == "noisy":
                sigma = rng.choice([1.0, 3.0]) * DEG
            else:
                sigma = rng.uniform(0.1, 0.6) * DEG  # boundary-straddler
            base, e1, e2 = _tangent_frame(p)
            v = p + sigma * (rng.normal() * e1 + rng.normal() * e2)
            u = normalize(v)

        # stage 1: exact point check (identical for every method)
        t0 = time.perf_counter()
        margin = float(scene_margins(scene, u[None, :])[0])
        t_point = time.perf_counter() - t0
        accepted = margin <= 0.0
        row = {"proposal": i, "kind": kind, "accepted": int(accepted),
               "margin_deg": margin / DEG, "point_check_us": 1e6 * t_point}
        if not accepted:
            # stage 2: repair existence within a bounded deviation cap
            repair_cap = ScaleScene(
                caps=np.vstack([scene.caps, u[None, :]]),
                tols=np.concatenate([scene.tols, [repair_delta_deg * DEG]]),
                suns=scene.suns, betas=scene.betas,
                label="repair", pointing_tol=repair_delta_deg * DEG)
            u_t = chart_points(u, repair_delta_deg, truth_step)
            truth = "YES" if (scene_margins(repair_cap, u_t) <= 0.0).any() else "NO"
            row["repair_truth"] = truth
            for step in grid_steps:
                g = grid_verdict(repair_cap, u, repair_delta_deg, step)
                row[f"repair_grid{step}_yes"] = int(g["feasible"])
                row[f"repair_grid{step}_us"] = 1e6 * g["seconds"]
            br = branch_verdict(repair_cap, repair_delta_deg, branch_eps, axis=u)
            row["repair_branch"] = br["verdict"]
            row["repair_branch_us"] = 1e6 * br["seconds"]
            row["repair_branch_nodes"] = br["nodes"]
        rows.append(row)

    summary = {
        "n_proposals": n_proposals, **n_type,
        "accepted": sum(r["accepted"] for r in rows),
        "feasible_fraction_cap": float((m_dense <= 0.0).mean()),
    }
    return rows, summary
