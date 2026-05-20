from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rpy_polar_synth.experiment import CameraConfig  # noqa: E402
from rpy_polar_synth.free_xyz_ba_experiment import (  # noqa: E402
    default_free_xyz_scenarios,
    free_xyz_records_to_array,
    make_free_xyz_scene,
    run_free_xyz_monte_carlo,
    write_free_xyz_csv,
)
from rpy_polar_synth.visualize import save_free_xyz_scene_plot, save_free_xyz_summary  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Experiment 4: free-XYZ multi-track BA in local and global regimes."
    )
    parser.add_argument("--output", type=Path, default=ROOT / "outputs_exp4", help="Output directory.")
    parser.add_argument("--trials", type=int, default=4, help="Monte-Carlo trials per yaw level.")
    parser.add_argument("--mc-seed", type=int, default=181, help="Monte-Carlo perturbation seed.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    camera = CameraConfig()
    args.output.mkdir(parents=True, exist_ok=True)

    print("Running Experiment 4 free-XYZ BA stress tests...")
    for scenario in default_free_xyz_scenarios():
        scene = make_free_xyz_scene(scenario, camera)
        records = run_free_xyz_monte_carlo(scene, trials_per_level=args.trials, seed=args.mc_seed)
        records_array = free_xyz_records_to_array(records)

        csv_path = args.output / f"exp4_{scene.name}_results.csv"
        scene_path = args.output / f"exp4_{scene.name}_scene_3d.png"
        summary_path = args.output / f"exp4_{scene.name}_summary.png"

        write_free_xyz_csv(records, csv_path)
        save_free_xyz_scene_plot(
            scene,
            scene_path,
            title=f"Experiment 4 {scene.name.capitalize()} free-XYZ BA scene",
        )
        save_free_xyz_summary(
            records_array,
            summary_path,
            title=f"Experiment 4 {scene.name.capitalize()} free-XYZ BA summary",
        )

        print(f"  {scene.name}:")
        print(f"    - {csv_path}")
        print(f"    - {scene_path}")
        print(f"    - {summary_path}")

    print(f"Done. Experiment 4 outputs saved to: {args.output}")


if __name__ == "__main__":
    main()
