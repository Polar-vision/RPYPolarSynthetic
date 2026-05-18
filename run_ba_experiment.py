from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rpy_polar_synth.ba_experiment import (  # noqa: E402
    BAScenarioConfig,
    ba_records_to_array,
    make_ba_scene,
    run_ba_monte_carlo,
    write_ba_csv,
)
from rpy_polar_synth.experiment import CameraConfig  # noqa: E402
from rpy_polar_synth.visualize import save_ba_summary  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run two-view inverse-depth BA stress tests for the RPY polar story."
    )
    parser.add_argument("--output", type=Path, default=ROOT / "outputs_ba", help="Output directory.")
    parser.add_argument("--trials", type=int, default=6, help="Monte-Carlo trials per yaw level.")
    parser.add_argument("--seed", type=int, default=41, help="Synthetic BA scene seed.")
    parser.add_argument("--mc-seed", type=int, default=73, help="Monte-Carlo perturbation seed.")
    parser.add_argument("--outliers", type=float, default=0.06, help="Fraction of shuffled matches.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    camera = CameraConfig()
    scenario = BAScenarioConfig(seed=args.seed, outlier_fraction=args.outliers)
    scene = make_ba_scene(scenario, camera)

    print("Running two-view inverse-depth BA stress test...")
    records = run_ba_monte_carlo(scene, trials_per_level=args.trials, seed=args.mc_seed)
    records_array = ba_records_to_array(records)

    args.output.mkdir(parents=True, exist_ok=True)
    write_ba_csv(records, args.output / "ba_monte_carlo_results.csv")
    save_ba_summary(records_array, args.output / "ba_monte_carlo_summary.png")

    print(f"Done. BA results saved to: {args.output}")
    print("Key files:")
    for name in ["ba_monte_carlo_results.csv", "ba_monte_carlo_summary.png"]:
        print(f"  - {args.output / name}")


if __name__ == "__main__":
    main()
