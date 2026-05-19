from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rpy_polar_synth.experiment import (  # noqa: E402
    CameraConfig,
    ScenarioConfig,
    build_landscape,
    build_landscape_slice,
    covariance_singularity_curve,
    make_scene,
    records_to_array,
    run_monte_carlo,
    write_csv,
)
from rpy_polar_synth.visualize import save_all_figures  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run synthetic experiments for RPY-stratified polar/bearing residuals."
    )
    parser.add_argument("--output", type=Path, default=ROOT / "outputs", help="Output directory.")
    parser.add_argument("--trials", type=int, default=10, help="Monte-Carlo trials per yaw level.")
    parser.add_argument("--seed", type=int, default=7, help="Synthetic scene seed.")
    parser.add_argument("--mc-seed", type=int, default=31, help="Monte-Carlo perturbation seed.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    camera = CameraConfig()
    scenario = ScenarioConfig(seed=args.seed)
    scene = make_scene(scenario, camera)

    print("Running Monte-Carlo optimization experiments...")
    records = run_monte_carlo(scene, trials_per_level=args.trials, seed=args.mc_seed)
    records_array = records_to_array(records)

    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(records, args.output / "monte_carlo_results.csv")

    print("Building diagnostic visualizations...")
    tilt_offsets = np.linspace(-30.0, 30.0, 121)
    yaw_offsets = np.linspace(-150.0, 150.0, 151)
    landscapes = {
        "pitch-yaw": build_landscape(
            scene,
            pitch_offsets_deg=tilt_offsets,
            yaw_offsets_deg=yaw_offsets,
        ),
        "roll-yaw": build_landscape_slice(
            scene,
            x_axis="yaw",
            y_axis="roll",
            x_offsets_deg=yaw_offsets,
            y_offsets_deg=tilt_offsets,
        ),
        "roll-pitch": build_landscape_slice(
            scene,
            x_axis="pitch",
            y_axis="roll",
            x_offsets_deg=tilt_offsets,
            y_offsets_deg=tilt_offsets,
        ),
    }
    curve = covariance_singularity_curve(camera)
    save_all_figures(scene, records_array, curve, landscapes, args.output)

    print(f"Done. Results saved to: {args.output}")
    print("Key files:")
    for name in [
        "monte_carlo_results.csv",
        "scene_3d.png",
        "image_measurements.png",
        "axis_singularity.png",
        "cost_landscape.png",
        "cost_landscape_pitch_yaw.png",
        "cost_landscape_roll_yaw.png",
        "cost_landscape_roll_pitch.png",
        "cost_landscape_all_slices.png",
        "monte_carlo_summary.png",
    ]:
        print(f"  - {args.output / name}")


if __name__ == "__main__":
    main()
