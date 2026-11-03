"""Keep-out cones (sun avoidance): what the exact framework covers, and what it cannot."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from rpy_polar_synth.cone_keepout import (  # noqa: E402
    KeepoutScene,
    feasibility_blind_candidates,
    feasibility_capform,
    feasibility_keepout,
    is_convex_regime,
    margin_keepout,
)
from rpy_polar_synth.pointing_prototype import axis_from_chart  # noqa: E402

OUT = ROOT / "outputs_keepout"
DEG = np.deg2rad


def pointing_box(radius_deg: float = 2.0, offset_deg: float = 1.5) -> tuple[np.ndarray, np.ndarray]:
    """Three caps 120 deg apart: the intersection is a small curved triangle."""
    caps = np.array([
        axis_from_chart(DEG(offset_deg * np.cos(t)), DEG(offset_deg * np.sin(t)))
        for t in DEG([0.0, 120.0, 240.0])
    ])
    return caps, np.full(3, DEG(radius_deg))


def grid_reference(scene: KeepoutScene, n: int = 320) -> tuple[float, float]:
    """Dense-grid truth: (best margin, fraction of the domain that is forbidden).

    Sampled in the same tangent chart the branching uses, over the ball that
    contains the pointing box, so the two cover the same domain.
    """
    from rpy_polar_synth.cone_keepout import _lift, _tangent_frame

    base = np.average(scene.caps, axis=0)
    base = base / np.linalg.norm(base)
    b_, e1, e2 = _tangent_frame(base)
    radius = float(np.max(np.arccos(np.clip(scene.caps @ b_, -1.0, 1.0)) + scene.tols))
    t = np.tan(min(radius + 1e-9, DEG(70.0)))
    xs = np.linspace(-t, t, n)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    V = base[None, None, :] + X[..., None] * e1 + Y[..., None] * e2
    V = V / np.linalg.norm(V, axis=2, keepdims=True)
    U = V.reshape(-1, 3)

    viol = np.arccos(np.clip(U @ scene.caps.T, -1.0, 1.0)) - scene.tols[None, :]
    worst = viol.max(axis=1)
    if scene.n_keepouts:
        ang = np.arccos(np.clip(U @ scene.suns.T, -1.0, 1.0))
        worst = np.maximum(worst, (scene.betas[None, :] - ang).max(axis=1))
    inside = worst <= 0.0
    return float(worst.min()), float(1.0 - inside.mean())


def sweep() -> list[dict]:
    caps, tols = pointing_box()
    rows: list[dict] = []
    betas = [3.0, 5.0, 8.0, 15.0, 30.0, 45.0, 60.0, 75.0, 85.0, 90.0, 95.0, 105.0]
    for beta in betas:
        # Position the sun relative to the exclusion cone so the interesting band
        # (box straddles the exclusion boundary) is sampled at the same resolution
        # for every beta.
        for ratio in (0.4, 0.85, 0.95, 0.99, 1.01, 1.06, 1.2, 1.6):
            delta = beta * ratio
            if delta > 170.0:
                continue
            scene = KeepoutScene(
                caps=caps, tols=tols,
                suns=np.array([axis_from_chart(0.0, DEG(delta))]),
                betas=np.array([DEG(beta)]),
            )
            capform = feasibility_capform(scene)
            blind = feasibility_blind_candidates(scene)
            branch = feasibility_keepout(scene, eps_deg=0.02)
            g_margin, g_frac = grid_reference(scene)
            rows.append({
                "beta_deg": beta,
                "delta_deg": round(delta, 4),
                "delta_over_beta": ratio,
                "convex_regime": is_convex_regime(scene.betas),
                "capform": capform.kind,
                "blind": blind.kind,
                "branch": branch.decision.kind,
                "grid_margin_deg": np.rad2deg(g_margin),
                "grid_forbidden_frac": g_frac,
                "branch_nodes": branch.nodes,
                "branch_depth": branch.depth,
                "blind_point_margin_deg": (
                    np.rad2deg(blind.margin) if blind.kind == "feasible" else np.nan
                ),
                "branch_point_margin_deg": (
                    np.rad2deg(margin_keepout(branch.decision.point, scene))
                    if branch.decision.kind == "feasible" else np.nan
                ),
            })
            print(f"beta={beta:6.1f} delta={delta:7.3f} capform={capform.kind:12s} "
                  f"blind={blind.kind:10s} branch={branch.decision.kind:10s} "
                  f"grid={np.rad2deg(g_margin):+7.3f} nodes={branch.nodes}")
    return rows


def witness_demo() -> list[dict]:
    """A 1 deg pointing box bracketed by a ring of exclusion cones.

    The ring is sized so that the union covers the box while no single cone does
    -- each cone owns an arc of the boundary.  Then the instance is infeasible
    and *every* cone is needed, so the irreducible certificate has size k + 1.
    Nothing of size <= 4 can be infeasible once k >= 4, which is the precise
    sense in which Helly's bound of 4 stops applying.
    """
    rows: list[dict] = []
    R = 1.0
    rho = 0.5
    centre = axis_from_chart(0.0, 0.0)
    for k in (2, 3, 4, 5, 6, 8):
        # Covering radius: the box boundary is worst halfway between two centres.
        # A 3% pad is needed because landing exactly on the covering radius leaves
        # the boundary circle itself allowed, which would make the instance
        # feasible by a measure-zero margin.
        beta = 1.03 * float(np.sqrt(R**2 + rho**2 - 2.0 * R * rho * np.cos(np.pi / k)))
        ang = np.linspace(0.0, 2.0 * np.pi, k, endpoint=False)
        ax_x = np.array([1.0, 0.0, 0.0])
        e1 = np.array([0.0, 1.0, 0.0])
        e2 = np.array([0.0, 0.0, 1.0])
        r = DEG(rho)
        suns = np.array([
            np.cos(r) * ax_x + np.sin(r) * (np.cos(a) * e1 + np.sin(a) * e2) for a in ang
        ])
        scene = KeepoutScene(caps=centre[None, :], tols=np.array([DEG(R)]),
                             suns=suns, betas=np.full(k, DEG(beta)))
        res = feasibility_keepout(scene, eps_deg=0.02)
        drops = []
        for j in range(k):
            keep = [i for i in range(k) if i != j]
            sub = KeepoutScene(caps=centre[None, :], tols=np.array([DEG(R)]),
                               suns=suns[keep], betas=scene.betas[keep])
            drops.append(feasibility_keepout(sub, eps_deg=0.02).decision.kind)
        irredundant = all(d == "feasible" for d in drops)
        rows.append({
            "n_keepouts": k,
            "keepout_beta_deg": beta,
            "branch": res.decision.kind,
            "drops_feasible": sum(d == "feasible" for d in drops),
            "irredundant": irredundant,
            "witness_size": k + 1,
            "nodes": res.nodes,
        })
        print(f"k={k:2d} beta={beta:5.3f} branch={res.decision.kind:12s} "
              f"irredundant={irredundant} drops={drops} nodes={res.nodes}")
    return rows


def interior_sweep() -> list[dict]:
    """The discriminating geometry: the exclusion cone sits inside the pointing box.

    The feasible set is then an annulus.  No candidate point of the lemma lies in
    it -- the cap centre is inside the hole and the boundaries never cross -- so
    the candidate set is empty of feasible points while the answer is feasible.
    """
    rows: list[dict] = []
    a = axis_from_chart(0.0, 0.0)
    for R in (1.2, 1.5, 2.0, 3.0):
        for ratio in (0.2, 0.35, 0.5, 0.66, 0.8, 0.95):
            beta = R * ratio
            scene = KeepoutScene(caps=a[None, :], tols=np.array([DEG(R)]),
                                 suns=a[None, :], betas=np.array([DEG(beta)]))
            g, frac = grid_reference(scene, 400)
            blind = feasibility_blind_candidates(scene)
            branch = feasibility_keepout(scene, eps_deg=0.02)
            truth = "feasible" if g <= 0 else "infeasible"
            rows.append({
                "box_radius_deg": R,
                "beta_deg": beta,
                "beta_over_R": ratio,
                "grid_margin_deg": np.rad2deg(g),
                "grid_forbidden_frac": frac,
                "truth": truth,
                "blind": blind.kind,
                "branch": branch.decision.kind,
                "branch_nodes": branch.nodes,
            })
            print(f"R={R:4.1f} beta={beta:5.2f} truth={truth:10s} blind={blind.kind:12s} "
                  f"branch={branch.decision.kind:10s} nodes={branch.nodes}")
    return rows


def write(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    rows = sweep()
    write(rows, OUT / "keepout_sweep.csv")
    wrows = witness_demo()
    write(wrows, OUT / "keepout_witness.csv")
    irows = interior_sweep()
    write(irows, OUT / "keepout_interior.csv")

    nonconvex = [r for r in rows if not r["convex_regime"]]
    convex = [r for r in rows if r["convex_regime"]]
    print(f"\nsweep {len(rows)} instances: convex {len(convex)}, non-convex {len(nonconvex)}")
    print("capform undetermined in non-convex regime:",
          sum(r["capform"] == "undetermined" for r in nonconvex), "/", len(nonconvex))
    print("capform agreed with branch in convex regime:",
          sum(r["capform"] == r["branch"] for r in convex), "/", len(convex))

    # Instances that are not at the resolution limit: the grid margin is a
    # reliable truth whenever it is away from zero.
    hard = [r for r in nonconvex if abs(r["grid_margin_deg"]) > 0.05]
    truth = ["feasible" if r["grid_margin_deg"] <= 0 else "infeasible" for r in hard]
    blind_ok = [r["blind"] == t for r, t in zip(hard, truth)]
    branch_ok = [r["branch"] == t for r, t in zip(hard, truth)]
    print(f"\nnon-convex, |grid margin| > 0.05 deg: {len(hard)} instances")
    print("  blind candidate set correct:", sum(blind_ok), "-> errors:", len(hard) - sum(blind_ok))
    print("  branch correct:", sum(branch_ok), "-> errors:", len(hard) - sum(branch_ok))
    bad = [r for r, ok in zip(hard, blind_ok) if not ok]
    if bad:
        print("  blind failure direction:",
              {d: sum(r["blind"] == d for r in bad) for d in ("feasible", "infeasible")})
        print("  blind false-feasible returned a violating point:",
              sum(r["blind"] == "feasible" and r["blind_point_margin_deg"] > 1e-6 for r in bad))
    print("  branch node count: median",
          float(np.median([r["branch_nodes"] for r in rows])),
          "max", max(r["branch_nodes"] for r in rows))

    inner = [r for r in irows if abs(r["grid_margin_deg"]) > 0.05]
    print(f"\ninterior geometry (annulus), |grid margin| > 0.05 deg: {len(inner)}")
    print("  blind correct:", sum(r["blind"] == r["truth"] for r in inner), "/", len(inner))
    print("  branch correct:", sum(r["branch"] == r["truth"] for r in inner), "/", len(inner))
    wrong = [r for r in inner if r["blind"] != r["truth"]]
    if wrong:
        print("  blind error directions:",
              {d: sum(r["blind"] == d for r in wrong) for d in ("feasible", "infeasible")})


if __name__ == "__main__":
    main()
