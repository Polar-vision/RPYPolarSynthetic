"""Run the three scenario validations of section 9.14 and write CSVs."""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path

from rpy_polar_synth.safety_scenarios import (
    run_lens_sweep,
    run_placement_random,
    run_plan_pruning,
    run_safety_shell,
)

OUT = Path("outputs_safety")
OUT.mkdir(exist_ok=True)


def write_csv(name: str, rows: list[dict]) -> None:
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})
    print(f"wrote {OUT / name} ({len(rows)} rows)")


def main() -> None:
    t0 = time.perf_counter()

    print("A1: random multi-camera placement scenes ...")
    a_random = run_placement_random()
    write_csv("safety_a_random.csv", a_random)

    print("A2: narrow-lens sweep ...")
    a_lens = run_lens_sweep()
    write_csv("safety_a_lens.csv", a_lens)

    print("B: inspection-plan pruning ...")
    plans, waypoints = run_plan_pruning()
    write_csv("safety_b_plans.csv", plans)
    write_csv("safety_b_waypoints.csv", waypoints)

    print("C: safety shell ...")
    shell_rows, shell_summary = run_safety_shell()
    write_csv("safety_c_shell.csv", shell_rows)
    with open(OUT / "safety_c_summary.json", "w") as f:
        json.dump(shell_summary, f, indent=2)

    print(f"done in {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
