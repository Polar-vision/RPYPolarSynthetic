"""Run the five scenario audits of section 9.10 and write their tables."""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from rpy_polar_synth import scenario_audit as sa  # noqa: E402

OUT = ROOT / "outputs_scenario_audit"


def write(name: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with (OUT / name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})
    print(f"  wrote {name} ({len(rows)} rows)")


def main() -> None:
    t_all = time.perf_counter()

    # ---- scenario 1 ----------------------------------------------------
    print("[1] laser interlock")
    a1 = sa.apt_interlock_audit()
    write("audit1_interlock.csv", a1.rows)
    write("audit1_summary.csv", [{
        "tol_deg": a1.tol_deg,
        "closed_form_us": a1.closed_form_us,
        "branch_us": a1.branch_us,
        "speedup": a1.branch_us / max(a1.closed_form_us, 1e-12),
        "union_only": a1.union_only,
        "union_trials": a1.union_trials,
    }])
    print(f"  closed form {a1.closed_form_us:.2f} us vs branch {a1.branch_us:.1f} us")
    print(f"  union-only exclusions: {a1.union_only}/{a1.union_trials}")

    # ---- scenario 2 ----------------------------------------------------
    print("[2] star field")
    write("audit2_stars.csv", sa.star_field_audit())
    write("audit2_roll.csv", sa.roll_crlb_table())
    err = sa.roll_fisher_check()
    print(f"  Fisher check rel err {err:.2e}")

    # ---- scenario 3 ----------------------------------------------------
    print("[3] mount limits")
    write("audit3_scale.csv", sa.mount_limit_scale_scan())
    write("audit3_random.csv", sa.mount_limit_random_rate(n=6000))
    write("audit3_window.csv", [sa.mount_gap_window(th) for th in (0.5, 1.0, 5.0, 30.0)])

    # ---- scenario 4 ----------------------------------------------------
    print("[4] baffle design")
    a4 = sa.baffle_audit()
    write("audit4_design.csv", a4["curve"])
    write("audit4_sampling.csv", a4["compare"])
    write("audit4_detect.csv", sa.baffle_detect_table())
    print("  beta_max curve:",
          ", ".join(f"k{r['k']} {r['gamma_deg']:.0f}:{r['beta_max_deg']:.1f}"
                    for r in a4["curve"]))

    reg = [sa.time_available_region(g, eps_deg=0.5) for g in (0.0, 30.0, 60.0, 90.0)]
    for r in reg:
        r["eps_deg"] = 0.5
    write("audit4_region.csv", reg)
    for r in reg:
        print(f"  gamma {r['gamma_deg']:.0f}: 3-D region {r['region_area_sr']:.3f} sr, "
              f"{r['region_nodes']} nodes, {r['region_seconds']:.2f} s vs "
              f"{r['exact_1d_seconds'] * 1e6:.0f} us 1-D")

    # ---- scenario 6 ----------------------------------------------------
    print("[6] thermal bands")
    write("audit5_thermal.csv", sa.thermal_parameter_map())
    a6 = sa.thermal_annulus_audit()
    write("audit5_geom.csv", a6)
    for r in a6:
        if r["components"] != 0 or r["area_sr"] > 0:
            print(f"  {r['face_set']:18s} [{r['a_min_deg']:.0f},{r['a_max_deg']:.0f}] "
                  f"-> {r['components']} components, area {r['area_sr']:.3f} sr")

    print(f"total {time.perf_counter() - t_all:.1f} s")


if __name__ == "__main__":
    main()
