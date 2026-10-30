"""Five further candidate scenarios, tested one by one.

Section 9.14 closed the CV/AI door and left a narrow one open: value survives
only where the answer is an *existence* question whose "no" must be proved, and
the feasible set can be squeezed below one sampling cell.  This module takes the
five scenarios that looked structurally isomorphic to that opening and puts each
through the same protocol, rather than assuming the analogy holds.

    S1  spacecraft attitude keep-out suite   sun/moon/limb/plume/radiator plus a
        bright-star catalogue; does an attitude exist inside a small pointing
        box?  Also separates the *point* query (stop at the first feasible box)
        from the *existence* query (must cover the whole box).
    S2  radiotherapy beam direction          target coverage cap, gantry/couch
        band, organ-at-risk keep-outs.  A closed-form family: the free region is
        a crescent whose area vanishes as ``gap -> 0``, and the true verdict
        flips at ``gap = 2 * tol`` exactly.
    S3  optical alignment tolerance          three equal caps on a 120 deg ring.
        Closed form: feasible iff ``theta >= r``, while the industry's pairwise
        check passes for ``theta >= r*sqrt(3)/2``.  The window between them is
        ``1 - sqrt(3)/2`` wide and independent of tolerance size.
    S4  conjunction / formation view window  the sun sweeps a great circle; the
        question "is the whole pass clean" is one-dimensional and its boundary
        is a tangency (zero measure).  Sampling in time is the industry method.
    S5  redundant-arm approach directions    reach cap minus joint-limit holes
        and an obstacle; the safety question is whether an approach exists at
        all, and whether a patch can be proved empty.

Protocol, identical to section 9.14:

    * grid      -- cell-centre evaluation.  YES exact, NO forever inconclusive.
    * branch    -- rigorous two-sided bound.  YES exact, NO is a proof only when
                   the undecided residue reaches zero; otherwise the residue is
                   reported as the remaining doubt.
    * truth     -- constructed closed form wherever the family admits one (S2,
                   S3, S4), otherwise the branch at a fine eps as in 9.14.

A scenario only earns a "unique advantage" if the branch beats the grid on a
question the customer actually asks; a scenario where the grid is right and
merely unable to prove it is reported as exactly that.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time

import numpy as np

from .branch_scale import ScaleScene, flight_suite, vectorised_branch
from .cone_keepout import _tangent_frame
from .pointing_prototype import normalize
from .safety_scenarios import (
    DEG,
    Z,
    branch_verdict,
    dir_at,
    grid_verdict,
    rotate_scene,
    rot_to_z,
    scene_margins,
)

__all__ = [
    "Case",
    "resolve_truth",
    "run_case",
    "point_query",
    "spacecraft_cases",
    "spacecraft_infeasible_cases",
    "spacecraft_grazing_cases",
    "rt_case",
    "rt_gap_sweep",
    "tol_case",
    "tol_sweep",
    "window_case",
    "window_sweep",
    "interval_branch_1d",
    "arm_cases",
]

# numerical slack for "this endpoint is already violating"; at exact tangency
# the margin is zero, and a strict `> 0` test would report a violation that
# only exists in floating point
TOL = 1e-12


# ---------------------------------------------------------------------------
# protocol
# ---------------------------------------------------------------------------

@dataclass
class Case:
    """One instance of one scenario."""

    scenario: str
    sid: int
    scene: ScaleScene
    extent_deg: float
    axis: np.ndarray = field(default_factory=lambda: Z.copy())
    truth: str | None = None          # "YES" / "NO" when known by construction
    meta: dict = field(default_factory=dict)


def resolve_truth(case: Case, eps_deg: float = 0.01) -> tuple[str, str]:
    """Truth from the closed form when available, else from a fine branch.

    A fine branch that stops on a non-zero residue returns UNKNOWN: those
    instances are excluded from accuracy counts, never counted as either way.
    """
    if case.truth is not None:
        return case.truth, "closed-form"
    b = branch_verdict(case.scene, case.extent_deg, eps_deg, axis=case.axis)
    if b["verdict"] == "YES":
        return "YES", "branch"
    if b["verdict"] == "NO_PROVEN":
        return "NO", "branch"
    return "UNKNOWN", "residue"


def point_query(case: Case, eps_deg: float = 0.05) -> dict:
    """Cost of the *point* answer: stop at the first certified feasible box."""
    scene = case.scene
    if not np.allclose(case.axis, Z):
        scene = rotate_scene(scene, rot_to_z(case.axis))
    t0 = time.perf_counter()
    r = vectorised_branch(scene, eps_deg=eps_deg, extent_deg=case.extent_deg,
                          max_nodes=4_000_000, early_exit=True, bound="tri")
    dt = time.perf_counter() - t0
    return {
        "point_feasible": bool(r.leaves_feasible > 0),
        "point_boxes": int(r.nodes_to_first_feasible),
        "point_seconds": dt,
    }


def run_case(case: Case, grid_steps=(0.5, 0.25, 0.1), branch_eps: float = 0.05,
             truth_eps: float = 0.01, with_point: bool = False) -> dict:
    """Grid at several resolutions vs one branch run, both against truth."""
    truth, truth_src = resolve_truth(case, truth_eps)
    row = {
        "scenario": case.scenario,
        "scene": case.sid,
        "truth": truth,
        "truth_source": truth_src,
        "extent_deg": case.extent_deg,
        **case.meta,
    }
    for step in grid_steps:
        g = grid_verdict(case.scene, case.axis, case.extent_deg, step)
        row[f"grid{step}_yes"] = int(g["feasible"])
        row[f"grid{step}_s"] = g["seconds"]
        row[f"grid{step}_n"] = g["n_points"]
        if truth != "UNKNOWN":
            row[f"grid{step}_fn"] = int(truth == "YES" and not g["feasible"])
            row[f"grid{step}_fp"] = int(truth == "NO" and g["feasible"])
    b = branch_verdict(case.scene, case.extent_deg, branch_eps, axis=case.axis)
    row["branch"] = b["verdict"]
    row["branch_nodes"] = b["nodes"]
    row["branch_s"] = b["seconds"]
    row["branch_residue_sr"] = b["residue_sr"]
    # Three-way, not two.  NO_RESIDUE is *not* a claim: the branch says "I could
    # not decide, and here is the area I failed to exclude".  Scoring it as a NO
    # would credit the method with a flaw it does not have, and (worse) would
    # make refraining from a guess look like an error.  Only YES and NO_PROVEN
    # are claims, and only a claim can be wrong.
    claim = {"YES": "YES", "NO_PROVEN": "NO",
             "NO_RESIDUE": "UNDECIDED"}[b["verdict"]]
    row["branch_claim"] = claim
    if truth != "UNKNOWN":
        row["branch_wrong"] = int((claim == "YES" and truth == "NO")
                                  or (claim == "NO" and truth == "YES"))
        row["branch_fn"] = int(truth == "YES" and claim == "NO")
        row["branch_fp"] = int(truth == "NO" and claim == "YES")
        row["branch_undecided"] = int(claim == "UNDECIDED")
        row["branch_proved_no"] = int(claim == "NO")
    if with_point:
        row.update(point_query(case, branch_eps))
    return row


# ---------------------------------------------------------------------------
# S1 -- spacecraft attitude keep-out suite
# ---------------------------------------------------------------------------

def spacecraft_cases(pointing_tols=(1.0, 0.4, 0.15, 0.06),
                     star_counts=(0, 20, 60, 120, 200),
                     star_beta_deg: float = 2.0,
                     seed: int = 7) -> list[Case]:
    """One attitude-existence query per (pointing box size, star count).

    ``flight_suite`` already builds the named cones; adding stars raises the
    constraint count without changing the geometry, which is exactly the axis
    section 9.11 varied for box counts.  Here the question is different: does
    the *verdict* survive at real constraint counts, and what does a proof cost.
    """
    cases = []
    sid = 0
    for tol in pointing_tols:
        for n in star_counts:
            scene = flight_suite(n_stars=n, star_beta_deg=star_beta_deg,
                                 pointing_tol_deg=tol, seed=seed + n)
            cases.append(Case(
                scenario="S1_spacecraft", sid=sid, scene=scene,
                extent_deg=tol, axis=Z.copy(), truth=None,
                meta={"pointing_tol_deg": tol, "stars": n,
                      "m_constraints": int(len(scene.tols) + len(scene.betas))},
            ))
            sid += 1
    return cases


def spacecraft_infeasible_cases(pointing_tols=(1.0, 0.4, 0.15, 0.06),
                               star_counts=(0, 60, 200),
                               sun_beta_deg: float = 30.0,
                               seed: int = 7) -> list[Case]:
    """The other half of the flight question: the target is inside a keep-out.

    This is the ordinary reason a slew is refused -- the commanded direction is
    within the sun exclusion cone, so no attitude in the box is legal.  The
    suite is the same named cone set, with the sun moved onto the box centre.
    Since every ``u`` in the box is within ``tol <= 1 deg`` of the centre and the
    cone is ``30 deg`` wide, the violation margin at the box centre is at least
    ``30 - tol`` degrees: infeasibility here is a construction with a margin of
    tens of degrees, not a numerical accident.  What the family measures is
    therefore not accuracy but the *cost of a proof*: a grid can only ever say
    "nothing found", this branch must kill the whole box.
    """
    cases = []
    sid = 1000
    for tol in pointing_tols:
        for n in star_counts:
            scene = flight_suite(n_stars=n, star_beta_deg=2.0,
                                 pointing_tol_deg=tol, seed=seed + n)
            suns = np.asarray(scene.suns, dtype=float).copy()
            suns[0] = Z.copy()                       # the sun sits on the target
            sc = ScaleScene(caps=scene.caps, tols=scene.tols, suns=suns,
                            betas=np.asarray(scene.betas, dtype=float),
                            label=f"target_in_sun+{n}stars",
                            pointing_tol=scene.pointing_tol)
            cases.append(Case(
                scenario="S1c_spacecraft_infeasible", sid=sid, scene=sc,
                extent_deg=tol, axis=Z.copy(), truth="NO",
                meta={"pointing_tol_deg": tol, "stars": n,
                      "m_constraints": int(len(sc.tols) + len(sc.betas)),
                      "family": "target_in_keepout"},
            ))
            sid += 1
    return cases


# ---------------------------------------------------------------------------
# S1b -- the one geometry in the flight suite that is ever critical
# ---------------------------------------------------------------------------
def spacecraft_grazing_case(w_deg: float, tol_deg: float = 1.0,
                            n_stars: int = 200, sun_beta_deg: float = 30.0,
                            sid: int = 0, seed: int = 11) -> Case:
    """A sun cone cutting the pointing box, leaving a crescent of width ``w``.

    The full suite is kept (named cones plus the star catalogue), but every
    constraint that would fall inside the box is removed, so the free region is
    exactly the crescent between the box rim and the cone boundary: width
    ``w > 0``, and the box is swallowed whole at ``w >= 2*tol``.  That makes the
    truth a construction while the constraint count stays real.
    """
    base, e1, e2 = _tangent_frame(Z)
    scene = flight_suite(n_stars=n_stars, star_beta_deg=2.0,
                         pointing_tol_deg=tol_deg, seed=seed)
    suns = np.asarray(scene.suns, dtype=float)
    betas = np.asarray(scene.betas, dtype=float)
    keep = np.arccos(np.clip(suns @ Z, -1.0, 1.0)) > 5.0 * tol_deg * DEG
    suns, betas = suns[keep], betas[keep]
    d = sun_beta_deg + tol_deg - w_deg
    grazing = dir_at(base, e1, e2, d, 0.0)
    suns = np.vstack([suns, grazing.reshape(1, 3)])
    betas = np.concatenate([betas, [sun_beta_deg * DEG]])
    truth = "YES" if w_deg < 2.0 * tol_deg else "NO"
    sc = ScaleScene(caps=Z.reshape(1, 3), tols=np.array([tol_deg * DEG]),
                    suns=suns, betas=betas, label=f"graze{w_deg:.2f}",
                    pointing_tol=tol_deg * DEG)
    return Case(scenario="S1b_spacecraft_grazing", sid=sid, scene=sc,
                extent_deg=tol_deg, axis=Z.copy(), truth=truth,
                meta={"w_deg": w_deg, "pointing_tol_deg": tol_deg,
                      "stars": int(n_stars),
                      "m_constraints": int(1 + len(betas))})


def spacecraft_grazing_cases(ws_deg=None, **kw) -> list[Case]:
    if ws_deg is None:
        ws_deg = (0.05, 0.1, 0.2, 0.4, 0.7, 1.0, 1.4, 1.8, 1.95,
                  1.99, 2.0, 2.02)
    return [spacecraft_grazing_case(w, sid=i, **kw) for i, w in enumerate(ws_deg)]


# ---------------------------------------------------------------------------
# S2 -- radiotherapy beam direction
# ---------------------------------------------------------------------------
def rt_case(gap_deg: float, tol_deg: float = 8.0, beta_deg: float = 20.0,
            el_min: float = 12.0, el_max: float = 85.0, az_deg: float = 0.0,
            sid: int = 0) -> Case:
    """A beam-direction feasibility problem with a closed-form answer.

    The target cap has radius ``tol``; one organ-at-risk keep-out cone has
    half-angle ``beta`` and sits at angular distance ``d = tol + beta - gap``
    from the target axis.  Overlap therefore grows with ``gap``:

        gap <= 0        cone and cap separated          -> whole cap free
        0 < gap < 2tol  cone clips the cap              -> crescent, area -> 0
        gap = 2tol      cone exactly swallows the cap   -> one tangent point
        gap > 2tol      cone contains the cap           -> infeasible

    So the true verdict flips at ``gap = 2 * tol`` exactly, and the free region
    thins to nothing as ``gap -> 0``.  Both ends of that sweep are adversarial
    to a grid for opposite reasons, and neither needs a branch to get truth.

    The gantry/couch band is kept in the scene because it is what an engineer
    would model, not because it bites here: with ``el_min = 12`` and
    ``el_max = 85`` it is redundant, the same redundancies section 9.9 found
    for optical night-time sun constraints.
    """
    base, e1, e2 = _tangent_frame(Z)
    oar = dir_at(base, e1, e2, tol_deg + beta_deg - gap_deg, az_deg)
    caps = np.asarray([Z.copy(), Z.copy()], dtype=float)          # target, band
    tols = np.asarray([tol_deg * DEG, (90.0 - el_min) * DEG])
    suns = np.asarray([oar, -Z], dtype=float)                     # OAR, floor
    betas = np.asarray([beta_deg * DEG, (90.0 - el_max) * DEG])
    truth = "YES" if gap_deg <= 2.0 * tol_deg else "NO"
    scene = ScaleScene(caps=caps, tols=tols, suns=suns, betas=betas,
                       label=f"rt{gap_deg:+.2f}", pointing_tol=tol_deg * DEG)
    return Case(scenario="S2_radiotherapy", sid=sid, scene=scene,
                extent_deg=tol_deg * 1.2 + 1.0, axis=Z.copy(), truth=truth,
                meta={"gap_deg": gap_deg, "tol_deg": tol_deg,
                      "beta_deg": beta_deg,
                      "gap_over_tol": gap_deg / tol_deg})


def rt_gap_sweep(gaps_deg=None, **kw) -> list[Case]:
    if gaps_deg is None:
        # dense near the tangency at gap = 2*tol = 16 deg: that is the only
        # place the two methods can disagree
        gaps_deg = (-2.0, 0.0, 2.0, 4.0, 8.0, 12.0, 14.0, 15.0, 15.5,
                    15.8, 15.9, 15.95, 16.0, 16.05, 16.2, 17.0, 20.0)
    return [rt_case(g, sid=i, **kw) for i, g in enumerate(gaps_deg)]


# ---------------------------------------------------------------------------
# S3 -- optical alignment tolerance
# ---------------------------------------------------------------------------

def tol_case(tau: float, r_deg: float = 3.0, sid: int = 0) -> Case:
    """Three equal caps of radius ``tau*r`` on a ring of radius ``r``, 120 apart.

    Closed form: the point minimising the worst-case distance to the three axes
    is the ring centre, at distance ``r``, so the intersection is non-empty iff
    ``tau >= 1``.  The pairwise test used in practice passes as soon as two caps
    of radius ``tau*r`` intersect, i.e. ``tau >= sqrt(3)/2 = 0.866``.  The gap
    between the two, ``1 - sqrt(3)/2``, is the Helly window of section 9.10.3.

    Read as a tolerance-design problem: ''pick the loosest tolerance that still
    admits an alignment''.  The pairwise rule over-loosens by 13.4%; a grid
    under-loosens, because just above ``tau = 1`` the feasible set is a tiny
    triangle of linear size ``r*(tau-1)``.
    """
    base, e1, e2 = _tangent_frame(Z)
    axes = [dir_at(base, e1, e2, r_deg, 120.0 * k) for k in range(3)]
    theta = tau * r_deg
    caps = np.asarray([Z.copy()] + axes, dtype=float)
    tols = np.asarray([90.0 * DEG] + [theta * DEG] * 3)
    scene = ScaleScene(caps=caps, tols=tols,
                       suns=np.zeros((0, 3)), betas=np.zeros(0),
                       label=f"tol{tau:.3f}", pointing_tol=r_deg * DEG)
    return Case(scenario="S3_tolerance", sid=sid, scene=scene,
                extent_deg=2.2 * r_deg, axis=Z.copy(),
                truth="YES" if tau >= 1.0 else "NO",
                meta={"tau": tau, "r_deg": r_deg, "theta_deg": theta,
                      "pairwise_ok": int(tau >= np.sqrt(3.0) / 2.0)})


def tol_sweep(taus=None, **kw) -> list[Case]:
    if taus is None:
        taus = (0.80, 0.85, 0.866, 0.88, 0.90, 0.92, 0.95, 0.97, 0.99,
                1.00, 1.005, 1.01, 1.02, 1.05, 1.10)
    return [tol_case(t, sid=i, **kw) for i, t in enumerate(taus)]


# ---------------------------------------------------------------------------
# S4 -- conjunction / formation view window (one-dimensional)
# ---------------------------------------------------------------------------

def window_case(over_deg: float, beta_deg: float = 12.0, arc_deg: float = 40.0,
                n_steps: int = 401, sid: int = 0) -> dict:
    """Sun sweeps a great circle that passes ``beta - over`` from a keep-out.

    ``over`` is how far the closest approach dips *inside* the cone: positive
    means a real violation, negative means a clean pass, zero is the tangency.
    The violation window half-width along the arc shrinks like
    ``sqrt(over)``, which is why a coarse time step reports a near-tangent pass
    as clean.  Everything here is analytic, so the sampling error is measured
    against an exact truth rather than against a finer sample.
    """
    axis = Z.copy()                      # keep-out axis
    keepout = ScaleScene(caps=Z.reshape(1, 3), tols=np.array([90.0 * DEG]),
                         suns=axis.reshape(1, 3), betas=np.array([beta_deg * DEG]),
                         label="window", pointing_tol=90.0 * DEG)
    # Sun path: a great circle whose minimum angular distance to `axis` is
    # beta - over.  Build it in the tangent frame of `axis`.
    base, e1, e2 = _tangent_frame(axis)
    d = (beta_deg - over_deg) * DEG
    # path parameter t in [-arc/2, arc/2]; sun(t) = rotate the tangent point.
    ts = np.linspace(-0.5 * arc_deg, 0.5 * arc_deg, n_steps) * DEG

    def sun_at(t):
        # tangent point at distance d from axis, then rotate around axis by t
        p = np.cos(d) * base + np.sin(d) * e1
        return (np.cos(t) * p + np.sin(t) * e2)

    suns = np.array([sun_at(t) for t in ts])
    margins = beta_deg * DEG - np.arccos(np.clip(suns @ axis, -1.0, 1.0))
    return {
        "scenario": "S4_window", "scene": sid,
        "over_deg": over_deg, "beta_deg": beta_deg, "arc_deg": arc_deg,
        "truth": ("BOUNDARY" if abs(over_deg) <= 1e-9
                  else ("NO" if over_deg > 0.0 else "YES")),
        "min_margin_deg": float(margins.min() / DEG),
        "max_margin_deg": float(margins.max() / DEG),
        "violation_halfwidth_deg": float(
            (np.abs(ts[margins > 0]).max() / DEG) if (margins > 0).any() else 0.0),
        "_scene": keepout, "_ts": ts, "_sun": sun_at, "_axis": axis,
    }


def _sample_window(case: dict, step_deg: float, phase: float = 0.35) -> dict:
    """Industry practice: uniform time samples, report clean if none violates.

    ``phase`` offsets the lattice away from the arc midpoint on purpose.  A
    sampler that happens to place a sample at the closest approach will find
    every violation ever built, which flatters it; a real scheduler has no such
    alignment.  The offset is fixed (not random) so the table is reproducible.
    """
    t0, t1 = float(case["_ts"][0]), float(case["_ts"][-1])
    step = step_deg * DEG
    n = max(2, int(np.ceil((t1 - t0) / step)) + 1)
    ts = np.linspace(t0 + phase * step, t1 - (1.0 - phase) * step, n)
    beta = case["beta_deg"] * DEG
    viol = False
    worst = -np.inf
    for t in ts:
        ang = np.arccos(np.clip(case["_sun"](t) @ case["_axis"], -1.0, 1.0))
        m = beta - ang                      # positive = inside the cone
        worst = max(worst, m)
        viol |= m > 0.0
    return {"step_deg": step_deg, "n_samples": int(n),
            "clean": int(not viol), "worst_violation_deg": float(worst / DEG)}


def interval_branch_1d(f, a: float, b: float, lip: float, eps: float,
                       max_boxes: int = 200_000) -> dict:
    """The same certificate idea in one dimension.

    ``f`` is a violation margin (positive = violation) with ``|f'| <= lip``.
    A box is killed when its upper bound is below zero, violated when an
    endpoint is already positive, and split otherwise.  Returns
    CLEAN_PROVEN (whole arc safe), VIOLATION (a point proved violating) or
    CLEAN_RESIDUE (undecided arc length remains -- the part a sampler cannot
    report).
    """
    stack = [(a, b)]
    boxes = 0
    residue = 0.0
    while stack:
        lo, hi = stack.pop()
        boxes += 1
        if boxes > max_boxes:
            residue += hi - lo
            continue
        flo, fhi = f(lo), f(hi)
        if flo > TOL or fhi > TOL:
            return {"verdict": "VIOLATION", "boxes": boxes,
                    "residue_deg": 0.0}
        if max(flo, fhi) + lip * 0.5 * (hi - lo) <= 0.0:
            continue
        if hi - lo <= eps:
            residue += hi - lo
            continue
        mid = 0.5 * (lo + hi)
        stack.extend([(lo, mid), (mid, hi)])
    if residue == 0.0:
        return {"verdict": "CLEAN_PROVEN", "boxes": boxes, "residue_deg": 0.0}
    return {"verdict": "CLEAN_RESIDUE", "boxes": boxes,
            "residue_deg": float(residue / DEG)}


def window_sweep(overs_deg=(-0.2, -0.1, -0.05, -0.02, 0.0, 0.005, 0.01, 0.02,
                            0.05, 0.1, 0.2),
                 steps_deg=(5.0, 2.0, 1.0, 0.5),
                 branch_eps_deg: float = 0.01) -> tuple[list[dict], list[dict]]:
    """Sampling vs a 1-D interval branch on a 1-D boundary problem."""
    rows, branch_rows = [], []
    for sid, over in enumerate(overs_deg):
        case = window_case(over, sid=sid)
        for step in steps_deg:
            r = _sample_window(case, step)
            r.update({"over_deg": over, "truth": case["truth"],
                      "wrong": (0 if case["truth"] == "BOUNDARY" else
                                int((r["clean"] == 1) != (case["truth"] == "YES"))),
                      "violation_halfwidth_deg": case["violation_halfwidth_deg"]})
            rows.append(r)
        beta = case["beta_deg"] * DEG
        lo, hi = float(case["_ts"][0]), float(case["_ts"][-1])

        def f(t, _sun=case["_sun"], _axis=case["_axis"], _b=beta):
            # violation margin: positive means the sun is inside the cone
            return float(_b - np.arccos(np.clip(_sun(t) @ _axis, -1.0, 1.0)))

        br = interval_branch_1d(f, lo, hi, lip=1.0, eps=branch_eps_deg * DEG)
        br.update({"over_deg": over, "truth": case["truth"],
                   "fn": (0 if case["truth"] != "YES" else
                          int(br["verdict"] == "VIOLATION")),
                   "fp": (0 if case["truth"] != "NO" else
                          int(br["verdict"] == "CLEAN_PROVEN")),
                   "undecided": int(br["verdict"] == "CLEAN_RESIDUE")})
        branch_rows.append(br)
    return rows, branch_rows


# ---------------------------------------------------------------------------
# S5 -- redundant-arm approach directions
# ---------------------------------------------------------------------------

def arm_case(kind: str, sid: int, rng: np.random.Generator | None = None,
             reach_deg: float = 6.0, width_deg: float = 0.05) -> Case:
    """Reachable approach directions = reach cap minus holes, obstacle.

    ``normal``    random joint-limit holes; truth from a fine branch.
    ``slit``      two holes leave a corridor ``width_deg`` wide; feasible by
                  construction, and narrower than any sensible cell.
    ``blocked``   the holes are placed so their union covers the reach cap:
                  infeasible by construction, the case a safety layer must be
                  able to *prove* rather than merely fail to sample.
    """
    rng = np.random.default_rng(sid) if rng is None else rng
    base, e1, e2 = _tangent_frame(Z)
    caps = Z.reshape(1, 3).copy()
    tols = np.array([reach_deg * DEG])
    if kind == "slit":
        # Two holes leave a corridor of width ``w``.  The corridor is placed at
        # a random offset inside the reach cap on purpose: a pocket centred on
        # the chart's origin is found by any lattice, which would flatter the
        # grid (the same lesson as section 9.14's blob scenes).
        w = width_deg
        h = 1.2
        centre = dir_at(base, e1, e2, rng.uniform(1.0, reach_deg * 0.6),
                        rng.uniform(0.0, 360.0))
        cb, c1, c2 = _tangent_frame(centre)
        suns = np.asarray([dir_at(cb, c1, c2, h, 0.0),
                           dir_at(cb, c1, c2, h, 180.0)], dtype=float)
        betas = np.asarray([(h - 0.5 * w) * DEG, (h - 0.5 * w) * DEG])
        truth = "YES"
        meta = {"kind": kind, "width_deg": w}
    elif kind == "blocked":
        # A ring of keep-outs that jointly covers the reach cap: infeasibility
        # is a construction, not a sampling result.  The ring radius, the count
        # and the phase move with the seed so the six instances are six
        # geometries; a fixed construction would have produced one scene printed
        # six times, which is not a sample of anything.
        n_ring = int(rng.integers(5, 8))
        a_ring = float(rng.uniform(2.0, 3.2))
        phase = float(rng.uniform(0.0, 360.0))
        # worst-case uncovered point of the ring's angular coverage sits at the
        # mid-gap radius; padding it by 0.3 deg makes the cover strict
        beta = float(np.sqrt(reach_deg ** 2 + a_ring ** 2
                             - 2.0 * reach_deg * a_ring
                             * np.cos(np.pi / n_ring))) + 0.3
        suns = np.asarray(
            [dir_at(base, e1, e2, a_ring, phase + 360.0 * k / n_ring)
             for k in range(n_ring)]
            + [Z.copy()]
        )
        betas = np.asarray([beta * DEG] * n_ring + [2.0 * DEG])
        truth = "NO"
        meta = {"kind": kind, "width_deg": np.nan, "ring_deg": a_ring,
                "n_ring": n_ring}
    else:
        n = int(rng.integers(2, 5))
        suns = np.asarray([dir_at(base, e1, e2, rng.uniform(1.0, reach_deg * 0.8),
                                  rng.uniform(0.0, 360.0)) for _ in range(n)])
        betas = rng.uniform(2.0, 6.0, n) * DEG
        truth = None
        meta = {"kind": kind, "width_deg": np.nan}
    scene = ScaleScene(caps=caps, tols=tols, suns=suns, betas=betas,
                       label=f"arm_{kind}", pointing_tol=_rad(reach_deg))
    return Case(scenario="S5_arm", sid=sid, scene=scene, extent_deg=reach_deg,
                axis=Z.copy(), truth=truth, meta=meta)


def _rad(deg: float) -> float:
    return deg * DEG


def arm_cases(n_normal: int = 24, n_blocked: int = 6, **kw) -> list[Case]:
    """Two families only, on purpose.

    A "thin corridor" family was built first and thrown away: with the reach cap
    far larger than the holes, the complement of two holes is *most of the cap*,
    so the grid finds a feasible point every time and the instance says nothing
    about corridors.  The small-pocket regime for approach patches is the same
    cap-minus-cap geometry already measured in S2 and S3, and is not re-measured
    here under a different name.
    """
    cases = []
    sid = 0
    for _ in range(n_normal):
        cases.append(arm_case("normal", sid, **kw))
        sid += 1
    for _ in range(n_blocked):
        cases.append(arm_case("blocked", sid, **kw))
        sid += 1
    return cases
