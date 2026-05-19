from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rpy_polar_synth.experiment import CameraConfig  # noqa: E402
from rpy_polar_synth.realistic_ba_experiment import (  # noqa: E402
    RealisticBAScenarioConfig,
    make_realistic_ba_scene,
    realistic_ba_records_to_array,
    run_realistic_ba_monte_carlo,
    write_realistic_ba_csv,
)
from rpy_polar_synth.visualize import save_realistic_ba_summary  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Experiment 3: a more realistic synthetic BA stress test with unknown translation."
    )
    parser.add_argument("--output", type=Path, default=ROOT / "outputs_exp3", help="Output directory.")
    parser.add_argument("--trials", type=int, default=6, help="Monte-Carlo trials per yaw level.")
    parser.add_argument("--seed", type=int, default=53, help="Synthetic BA scene seed.")
    parser.add_argument("--mc-seed", type=int, default=79, help="Monte-Carlo perturbation seed.")
    parser.add_argument("--outliers", type=float, default=0.06, help="Fraction of shuffled matches.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    camera = CameraConfig()
    scenario = RealisticBAScenarioConfig(seed=args.seed, outlier_fraction=args.outliers)
    scene = make_realistic_ba_scene(scenario, camera)

    print("Running Experiment 3 realistic BA stress test...")
    records = run_realistic_ba_monte_carlo(scene, trials_per_level=args.trials, seed=args.mc_seed)
    records_array = realistic_ba_records_to_array(records)

    args.output.mkdir(parents=True, exist_ok=True)
    write_realistic_ba_csv(records, args.output / "exp3_monte_carlo_results.csv")
    save_realistic_ba_summary(records_array, args.output / "exp3_monte_carlo_summary.png")

    print(f"Done. Experiment 3 results saved to: {args.output}")
    print("Key files:")
    for name in ["exp3_monte_carlo_results.csv", "exp3_monte_carlo_summary.png"]:
        print(f"  - {args.output / name}")


if __name__ == "__main__":
    main()
