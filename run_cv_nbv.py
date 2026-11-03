"""Compare exact branching and grid search on real LLFF next-best-view tasks."""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from rpy_polar_synth.cv_nbv import (  # noqa: E402
    branch_query,
    build_grid,
    greedy_sequences,
    grid_query,
    load_llff_scene,
)

OUT = ROOT / "outputs_cv_nbv"


def write_csv(rows, path):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", default="fern,flower,fortress,horns,leaves,orchids,room,trex")
    ap.add_argument("--beta-fractions", default="0.15,0.25,0.40,0.55")
    ap.add_argument("--eps", default="0.5,0.2,0.05")
    ap.add_argument("--seeds-per-scene", type=int, default=3)
    args = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    fractions = [float(x) for x in args.beta_fractions.split(",")]
    eps_values = [float(x) for x in args.eps.split(",")]
    rows = []
    scene_rows = []
    t_start = time.time()

    for scene_name in args.scenes.split(","):
        scene = load_llff_scene(ROOT / "analysis" / "data" / f"llff_{scene_name}" / "poses_bounds.npy")
        extent = float(np.degrees(scene.cap_radius))
        scene_rows.append({
            "scene": scene.name,
            "n_views": scene.n_views,
            "cap_radius_deg": round(extent, 6),
            "ray_rms_dataset_units": round(scene.ray_rms, 6),
        })
        seed_ids = np.linspace(0, scene.n_views - 1, args.seeds_per_scene).round().astype(int)
        instances = []
        for fraction in fractions:
            beta = extent * fraction
            for seed, step, selected, eligible in (
                (seed, step, selected, eligible)
                for seed in seed_ids
                for step, (selected, eligible) in enumerate(greedy_sequences(scene, beta, [seed]))
            ):
                instances.append((fraction, beta, int(seed), step, selected, eligible))
        print(f"{scene.name}: {len(instances)} instances, extent {extent:.2f} deg", flush=True)

        for eps in eps_values:
            grid = build_grid(scene, eps)
            for fraction, beta, seed, step, selected, eligible in instances:
                gh, gi, gs = grid_query(grid, scene.cap_radius, selected, beta)
                bh, br, margin = branch_query(scene, selected, beta, eps)
                miss = (not gh) and bh
                rows.append({
                    "scene": scene.name,
                    "n_views": scene.n_views,
                    "cap_radius_deg": round(extent, 6),
                    "beta_fraction": fraction,
                    "beta_deg": round(beta, 6),
                    "seed": seed,
                    "step": step,
                    "n_selected": len(selected),
                    "real_eligible": int(len(eligible)),
                    "eps_deg": eps,
                    "grid_points": grid.n_points,
                    "grid_setup_s": round(grid.setup_seconds, 6),
                    "grid_hit": int(gh),
                    "grid_first_index": gi,
                    "grid_s": round(gs, 6),
                    "branch_hit": int(bh),
                    "branch_nodes": br.nodes,
                    "branch_s": round(br.seconds, 6),
                    "branch_truncated": int(br.truncated),
                    "branch_point_clearance_deg": round(-margin / np.pi * 180.0, 8) if bh else "",
                    "grid_miss_branch_hit": int(miss),
                    "real_witnessed_miss": int(miss and len(eligible) > 0),
                    "hard_le5_real": int(len(eligible) <= 5),
                })
            done = [r for r in rows if r["scene"] == scene.name and r["eps_deg"] == eps]
            misses = sum(r["grid_miss_branch_hit"] for r in done)
            witnessed = sum(r["real_witnessed_miss"] for r in done)
            print(f"  eps={eps}: n={len(done)}, grid-miss/branch-hit={misses}, real-witnessed={witnessed}", flush=True)
            write_csv(rows, OUT / "cv_nbv_results.csv")

    write_csv(scene_rows, OUT / "cv_nbv_scenes.csv")
    write_csv(rows, OUT / "cv_nbv_results.csv")
    print(f"\nTOTAL {len(rows)} queries in {time.time() - t_start:.1f}s")
    for eps in eps_values:
        part = [r for r in rows if r["eps_deg"] == eps]
        print(
            f"eps={eps}: grid misses with exact hit={sum(r['grid_miss_branch_hit'] for r in part)}, "
            f"real-witnessed={sum(r['real_witnessed_miss'] for r in part)}, "
            f"branch failures={sum(not r['branch_hit'] for r in part)}"
        )


if __name__ == "__main__":
    main()
