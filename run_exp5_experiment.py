from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rpy_polar_synth.airborne_strip_experiment import (  # noqa: E402
    default_airborne_strip_scenario,
    make_airborne_strip_scene,
)
from rpy_polar_synth.experiment import CameraConfig  # noqa: E402
from rpy_polar_synth.free_xyz_ba_experiment import (  # noqa: E402
    free_xyz_records_to_array,
    run_free_xyz_monte_carlo,
    write_free_xyz_csv,
)
from rpy_polar_synth.visualize import (  # noqa: E402
    save_airborne_strip_plan_plot,
    save_airborne_strip_scene_plot,
    save_free_xyz_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Experiment 5: UAV-style oblique multi-strip free-XYZ BA stress test."
    )
    parser.add_argument("--output", type=Path, default=ROOT / "outputs_exp5", help="Output directory.")
    parser.add_argument("--trials", type=int, default=3, help="Monte-Carlo trials per yaw level.")
    parser.add_argument("--mc-seed", type=int, default=541, help="Monte-Carlo perturbation seed.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    camera = CameraConfig()
    scenario = default_airborne_strip_scenario()
    args.output.mkdir(parents=True, exist_ok=True)

    print("Running Experiment 5 UAV oblique multi-strip BA stress test...")
    scene = make_airborne_strip_scene(scenario, camera)
    records = run_free_xyz_monte_carlo(
        scene,
        trials_per_level=args.trials,
        tilt_error_deg=22.0,
        translation_error_m=0.70,
        seed=args.mc_seed,
        staged_cycles=1,
        staged_final_use_sparsity=False,
    )
    records_array = free_xyz_records_to_array(records)

    csv_path = args.output / "exp5_uav_oblique_results.csv"
    scene_path = args.output / "exp5_uav_oblique_scene_3d.png"
    plan_path = args.output / "exp5_uav_oblique_plan_view.png"
    summary_path = args.output / "exp5_uav_oblique_summary.png"

    write_free_xyz_csv(records, csv_path)
    save_airborne_strip_scene_plot(
        scene,
        scenario.strip_ids,
        scene_path,
        title="Experiment 5 UAV oblique multi-strip BA scene",
    )
    save_airborne_strip_plan_plot(
        scene,
        scenario.strip_ids,
        plan_path,
        title="Experiment 5 UAV oblique strip layout",
    )
    save_free_xyz_summary(
        records_array,
        summary_path,
        title="Experiment 5 UAV oblique multi-strip BA summary",
    )

    print(f"  - {csv_path}")
    print(f"  - {scene_path}")
    print(f"  - {plan_path}")
    print(f"  - {summary_path}")
    print(f"Done. Experiment 5 outputs saved to: {args.output}")


if __name__ == "__main__":
    main()
