"""Run the five candidate scenarios of ``next_scenarios`` and dump the tables.

    PYTHONPATH=src python run_next_scenarios.py

Writes ``outputs_next/*.csv`` plus ``outputs_next/summary.json``.  Every table
carries the truth source, so a reader can tell a closed-form family (S2/S3/S4)
from a branch-derived truth (S1/S5) without trusting the prose.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from rpy_polar_synth.next_scenarios import (
    arm_case,
    arm_cases,
    rt_gap_sweep,
    run_case,
    spacecraft_cases,
    spacecraft_infeasible_cases,
    tol_sweep,
    window_sweep,
)
from rpy_polar_synth.safety_scenarios import chart_points, scene_margins, Z

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs_next"
OUT.mkdir(exist_ok=True)


def write_csv(rows: list[dict], path: Path) -> None:
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"  -> {path.name} ({len(rows)} rows)")


def main() -> None:
    summary: dict = {}

    # ---------------- S1: spacecraft keep-out suite ----------------
    print("S1 spacecraft keep-out suite")
    cases = spacecraft_cases()
    rows = [run_case(c, grid_steps=(0.5, 0.1, 0.05), branch_eps=0.05,
                     truth_eps=0.01, with_point=True) for c in cases]
    write_csv(rows, OUT / "next_s1_spacecraft.csv")

    def agg(rows, key):
        vals = [r[key] for r in rows if key in r]
        return float(np.mean(vals)) if vals else None

    summary["S1"] = {
        "n": len(rows),
        "truth_yes": sum(r["truth"] == "YES" for r in rows),
        "truth_no": sum(r["truth"] == "NO" for r in rows),
        "truth_unknown": sum(r["truth"] == "UNKNOWN" for r in rows),
        "grid0.5_fn": sum(r.get("grid0.5_fn", 0) for r in rows),
        "grid0.1_fn": sum(r.get("grid0.1_fn", 0) for r in rows),
        "grid0.05_fn": sum(r.get("grid0.05_fn", 0) for r in rows),
        "grid0.5_fp": sum(r.get("grid0.5_fp", 0) for r in rows),
        "branch_wrong": sum(r.get("branch_wrong", 0) for r in rows),
        "branch_undecided": sum(r.get("branch_undecided", 0) for r in rows),
        "branch_proved_no": sum(r.get("branch_proved_no", 0) for r in rows),
        "median_branch_s": float(np.median([r["branch_s"] for r in rows])),
        "median_grid0.1_s": float(np.median([r["grid0.1_s"] for r in rows])),
        "median_point_boxes": float(np.median([r["point_boxes"] for r in rows])),
        "median_exist_boxes": float(np.median([r["branch_nodes"] for r in rows])),
        "cost": [
            {
                "tol_deg": r["pointing_tol_deg"],
                "stars": r["stars"],
                "m": r["m_constraints"],
                "branch_ms": round(float(r["branch_s"]) * 1e3, 2),
                "nodes": r["branch_nodes"],
                "point_ms": round(float(r["point_seconds"]) * 1e3, 2),
                "point_boxes": r["point_boxes"],
                "grid0.05_n": r["grid0.05_n"],
            }
            for r in rows
        ],
    }

    # ---------------- S1c: infeasible by construction ----------------
    print("S1c spacecraft target inside a keep-out")
    casesc = spacecraft_infeasible_cases()
    rowsc = [run_case(c, grid_steps=(0.5, 0.1, 0.05), branch_eps=0.05,
                      truth_eps=0.01) for c in casesc]
    write_csv(rowsc, OUT / "next_s1c_spacecraft_infeasible.csv")
    summary["S1c"] = {
        "n": len(rowsc),
        "truth_no": sum(r["truth"] == "NO" for r in rowsc),
        "grid0.5_yes": sum(int(r["grid0.5_yes"]) for r in rowsc),
        "grid0.1_yes": sum(int(r["grid0.1_yes"]) for r in rowsc),
        "branch_proved_no": sum(r.get("branch_proved_no", 0) for r in rowsc),
        "branch_undecided": sum(r.get("branch_undecided", 0) for r in rowsc),
        "branch_wrong": sum(r.get("branch_wrong", 0) for r in rowsc),
        "median_branch_ms": round(float(np.median([r["branch_s"] for r in rowsc])) * 1e3, 2),
        "median_nodes": float(np.median([r["branch_nodes"] for r in rowsc])),
        "median_grid0.05_ms": round(float(np.median([r["grid0.05_s"] for r in rowsc])) * 1e3, 2),
        "min_margin_deg": float(np.min([r["branch_residue_sr"] for r in rowsc])),
        "rows": [
            {"tol_deg": r["pointing_tol_deg"], "stars": r["stars"],
             "m": r["m_constraints"], "branch": r["branch"],
             "nodes": r["branch_nodes"], "grid0.05_yes": r["grid0.05_yes"]}
            for r in rowsc
        ],
    }

    # ---------------- S1b: the critical geometry in the suite ----------------
    print("S1b spacecraft grazing sun")
    from rpy_polar_synth.next_scenarios import spacecraft_grazing_cases
    casesb = spacecraft_grazing_cases()
    rowsb = [run_case(c, grid_steps=(0.5, 0.25, 0.1), branch_eps=0.02,
                      truth_eps=0.01) for c in casesb]
    write_csv(rowsb, OUT / "next_s1b_spacecraft_grazing.csv")
    summary["S1b"] = {
        "n": len(rowsb),
        "w_deg": [r["w_deg"] for r in rowsb],
        "truth": [r["truth"] for r in rowsb],
        "grid0.5": [r["grid0.5_yes"] for r in rowsb],
        "grid0.25": [r["grid0.25_yes"] for r in rowsb],
        "grid0.1": [r["grid0.1_yes"] for r in rowsb],
        "branch": [r["branch"] for r in rowsb],
        "grid0.5_fn": sum(r.get("grid0.5_fn", 0) for r in rowsb),
        "grid0.25_fn": sum(r.get("grid0.25_fn", 0) for r in rowsb),
        "grid0.1_fn": sum(r.get("grid0.1_fn", 0) for r in rowsb),
        "branch_wrong": sum(r.get("branch_wrong", 0) for r in rowsb),
        "branch_undecided": sum(r.get("branch_undecided", 0) for r in rowsb),
        "branch_proved_no": sum(r.get("branch_proved_no", 0) for r in rowsb),
        "residue_at_199_sr": [r["branch_residue_sr"] for r in rowsb
                              if r["w_deg"] == 1.99],
    }

    # ---------------- S2: radiotherapy beam directions ----------------
    print("S2 radiotherapy beam directions")
    rows2 = [run_case(c, grid_steps=(1.0, 0.5, 0.2), branch_eps=0.02,
                      truth_eps=0.01) for c in rt_gap_sweep()]
    write_csv(rows2, OUT / "next_s2_radiotherapy.csv")
    summary["S2"] = {
        "n": len(rows2),
        "grid0.5_fn_scenes": [r["scene"] for r in rows2 if r.get("grid0.5_fn")],
        "grid0.5_fp": sum(r.get("grid0.5_fp", 0) for r in rows2),
        "branch_undecided": sum(r.get("branch_undecided", 0) for r in rows2),
        "branch_wrong": sum(r.get("branch_wrong", 0) for r in rows2),
        "branch_proved_no": sum(r.get("branch_proved_no", 0) for r in rows2),
        "gaps": [r["gap_deg"] for r in rows2],
        "truth": [r["truth"] for r in rows2],
        "branch": [r["branch"] for r in rows2],
        "grid0.5": [r["grid0.5_yes"] for r in rows2],
        "grid0.2": [r["grid0.2_yes"] for r in rows2],
        "branch_nodes": [r["branch_nodes"] for r in rows2],
    }

    # ---------------- S3: alignment tolerance ----------------
    print("S3 optical alignment tolerance")
    rows3 = [run_case(c, grid_steps=(1.0, 0.5, 0.25), branch_eps=0.02,
                      truth_eps=0.01) for c in tol_sweep()]
    write_csv(rows3, OUT / "next_s3_tolerance.csv")
    summary["S3"] = {
        "n": len(rows3),
        "tau": [r["tau"] for r in rows3],
        "truth": [r["truth"] for r in rows3],
        "pairwise": [r["pairwise_ok"] for r in rows3],
        "grid1.0": [r["grid1.0_yes"] for r in rows3],
        "grid0.5": [r["grid0.5_yes"] for r in rows3],
        "grid0.25": [r["grid0.25_yes"] for r in rows3],
        "grid0.5_fn": sum(r.get("grid0.5_fn", 0) for r in rows3),
        "grid0.5_fp": sum(r.get("grid0.5_fp", 0) for r in rows3),
        "grid0.25_fn": sum(r.get("grid0.25_fn", 0) for r in rows3),
        "branch": [r["branch"] for r in rows3],
        "branch_undecided": sum(r.get("branch_undecided", 0) for r in rows3),
        "branch_wrong": sum(r.get("branch_wrong", 0) for r in rows3),
        "branch_proved_no": sum(r.get("branch_proved_no", 0) for r in rows3),
        "pairwise_fp": sum(int(r["pairwise_ok"] == 1 and r["truth"] == "NO")
                           for r in rows3),
        "pairwise_fn": sum(int(r["pairwise_ok"] == 0 and r["truth"] == "YES")
                           for r in rows3),
        "median_nodes": float(np.median([r["branch_nodes"] for r in rows3])),
        "window_lo": float(np.sqrt(3.0) / 2.0),
        "window_width": float(1.0 - np.sqrt(3.0) / 2.0),
    }

    # ---------------- S4: pass window (1-D) ----------------
    print("S4 conjunction / formation pass window")
    rows4, rows4b = window_sweep()
    write_csv(rows4, OUT / "next_s4_window_sample.csv")
    write_csv(rows4b, OUT / "next_s4_window_branch.csv")
    summary["S4"] = {
        "n": len(rows4),
        "by_step": {
            str(step): {
                "missed": sum(r["wrong"] for r in rows4 if r["step_deg"] == step),
                "n": sum(1 for r in rows4 if r["step_deg"] == step),
            }
            for step in (5.0, 2.0, 1.0, 0.5)
        },
        "branch_verdicts": [r["verdict"] for r in rows4b],
        "branch_fn": sum(r["fn"] for r in rows4b),
        "branch_undecided": sum(r["undecided"] for r in rows4b),
        "overs": [r["over_deg"] for r in rows4b],
    }

    # ---------------- S5: redundant arm ----------------
    print("S5 redundant-arm approach directions")
    rows5 = []
    for c in arm_cases():
        # verify the constructed "blocked" scenes really are covered
        if c.meta.get("kind") == "blocked":
            u = chart_points(Z, c.extent_deg, 0.05)
            if float(scene_margins(c.scene, u).min()) <= 0.0:
                c.truth = None
                c.meta["cover_check"] = "failed"
        r = run_case(c, grid_steps=(0.5, 0.2, 0.05), branch_eps=0.01,
                     truth_eps=0.01)
        rows5.append(r)
    write_csv(rows5, OUT / "next_s5_arm.csv")
    by_kind = {}
    for r in rows5:
        k = r["kind"]
        by_kind.setdefault(k, {"n": 0, "grid0.5_fn": 0, "grid0.2_fn": 0,
                               "grid0.05_fn": 0, "grid0.5_fp": 0,
                               "branch_wrong": 0, "branch_undecided": 0,
                               "proved_no": 0, "residue": 0, "truth": {},
                               "nodes": [], "branch_ms": []})
        d = by_kind[k]
        d["n"] += 1
        d["grid0.5_fn"] += r.get("grid0.5_fn", 0)
        d["grid0.2_fn"] += r.get("grid0.2_fn", 0)
        d["grid0.05_fn"] += r.get("grid0.05_fn", 0)
        d["grid0.5_fp"] += r.get("grid0.5_fp", 0)
        d["branch_wrong"] += r.get("branch_wrong", 0)
        d["branch_undecided"] += r.get("branch_undecided", 0)
        d["proved_no"] += r.get("branch_proved_no", 0)
        d["residue"] += int(r["branch"] == "NO_RESIDUE")
        d["truth"][r["truth"]] = d["truth"].get(r["truth"], 0) + 1
        d["nodes"].append(r["branch_nodes"])
        d["branch_ms"].append(round(float(r["branch_s"]) * 1e3, 2))
    for d in by_kind.values():
        d["nodes"] = sorted(d["nodes"])
    summary["S5"] = by_kind

    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nsummary written ->", OUT / "summary.json")
    print(json.dumps(summary, indent=2, ensure_ascii=False)[:4000])


if __name__ == "__main__":
    main()
