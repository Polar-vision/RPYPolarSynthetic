from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .experiment import SyntheticScene
from .geometry import rpy_matrix


COLORS = {
    "uv_joint": "#4C78A8",
    "polar_plain_joint": "#F58518",
    "polar_cov_joint": "#54A24B",
    "polar_staged": "#B279A2",
    "ba_uv_joint": "#4C78A8",
    "ba_polar_plain_joint": "#F58518",
    "ba_polar_cov_joint": "#54A24B",
    "ba_polar_staged": "#B279A2",
}

LABELS = {
    "uv_joint": "UV joint",
    "polar_plain_joint": "plain polar",
    "polar_cov_joint": "cov-aware polar",
    "polar_staged": "staged polar",
    "ba_uv_joint": "BA UV joint",
    "ba_polar_plain_joint": "BA plain polar",
    "ba_polar_cov_joint": "BA cov-aware polar",
    "ba_polar_staged": "BA staged polar",
}


def save_scene_plot(scene: SyntheticScene, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    theta = np.rad2deg(np.arctan2(
        np.linalg.norm(scene.points_camera_true[:, :2], axis=1),
        scene.points_camera_true[:, 2],
    ))
    scatter = ax.scatter(
        scene.points_world[:, 0],
        scene.points_world[:, 1],
        scene.points_world[:, 2],
        c=theta,
        s=12,
        cmap="viridis",
        alpha=0.85,
    )

    r_wc = rpy_matrix(scene.true_params).T
    origin = np.zeros(3)
    axes = r_wc @ np.eye(3)
    axis_colors = ["#D62728", "#2CA02C", "#1F77B4"]
    axis_names = ["camera x", "camera y", "optical axis"]
    for idx in range(3):
        ax.quiver(
            origin[0],
            origin[1],
            origin[2],
            axes[0, idx],
            axes[1, idx],
            axes[2, idx],
            length=2.0,
            color=axis_colors[idx],
            linewidth=2,
            label=axis_names[idx],
        )

    ax.set_title("Synthetic 3D scene and true camera axes")
    ax.set_xlabel("world x")
    ax.set_ylabel("world y")
    ax.set_zlabel("world z")
    ax.legend(loc="upper left")
    colorbar = fig.colorbar(scatter, ax=ax, shrink=0.72, pad=0.08)
    colorbar.set_label("true bearing theta (deg)")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_image_observation_plot(scene: SyntheticScene, path: Path) -> None:
    theta = scene.observed_polar[:, 0]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(
        scene.observed_pixels[:, 0],
        scene.observed_pixels[:, 1],
        c=np.rad2deg(theta),
        s=16,
        cmap="plasma",
        alpha=0.9,
        label="noisy observations",
    )
    ax.scatter([scene.camera.cx], [scene.camera.cy], marker="+", s=120, c="black", label="optical axis")
    ax.set_aspect("equal", adjustable="box")
    ax.invert_yaxis()
    ax.set_xlim(0, scene.camera.width)
    ax.set_ylim(scene.camera.height, 0)
    ax.set_title("Synthetic image measurements")
    ax.set_xlabel("u (px)")
    ax.set_ylabel("v (px)")
    ax.legend(loc="upper right")
    colorbar = fig.colorbar(ax.collections[0], ax=ax)
    colorbar.set_label("observed theta (deg)")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_singularity_plot(curve: dict[str, np.ndarray], path: Path) -> None:
    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.plot(curve["theta_deg"], curve["sigma_theta_deg"], label="sigma theta", color="#4C78A8")
    ax1.plot(curve["theta_deg"], curve["sigma_phi_deg"], label="sigma phi", color="#F58518")
    ax1.set_yscale("log")
    ax1.set_xlabel("bearing theta (deg)")
    ax1.set_ylabel("propagated angular sigma (deg, log scale)")
    ax1.grid(True, which="both", alpha=0.25)
    ax1.legend(loc="upper right")

    ax2 = ax1.twinx()
    ax2.plot(curve["theta_deg"], curve["phi_gate"], color="#54A24B", linestyle="--", label="phi gate")
    ax2.set_ylabel("axis gate")
    ax2.set_ylim(-0.05, 1.05)
    ax2.legend(loc="center right")

    ax1.set_title("Optical-axis singularity: phi uncertainty grows near theta = 0")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_landscape_plot(landscape: dict[str, np.ndarray], path: Path) -> None:
    pitch = landscape["pitch_offsets_deg"]
    yaw = landscape["yaw_offsets_deg"]
    extent = [yaw.min(), yaw.max(), pitch.min(), pitch.max()]
    items = [
        ("uv", "UV cost"),
        ("theta_only", "theta-only polar cost"),
        ("polar", "cov-aware polar cost"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(13, 4), constrained_layout=True)
    for ax, (key, title) in zip(axes, items):
        image = ax.imshow(
            landscape[key],
            origin="lower",
            extent=extent,
            aspect="auto",
            cmap="magma",
        )
        ax.axvline(0.0, color="white", linewidth=0.8, alpha=0.7)
        ax.axhline(0.0, color="white", linewidth=0.8, alpha=0.7)
        ax.set_title(title)
        ax.set_xlabel("yaw offset (deg)")
        ax.set_ylabel("pitch offset (deg)")
        fig.colorbar(image, ax=ax, label="log10(cost - min + 1)")

    fig.savefig(path, dpi=180)
    plt.close(fig)


def _aggregate(records: np.ndarray, metric: str) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    methods = list(LABELS)
    yaw_levels = np.unique(records["yaw_init_error_deg"])
    values = np.full((len(methods), len(yaw_levels)), np.nan)
    p25 = np.full_like(values, np.nan)
    p75 = np.full_like(values, np.nan)

    for i, method in enumerate(methods):
        for j, yaw in enumerate(yaw_levels):
            mask = (records["method"] == method) & (records["yaw_init_error_deg"] == yaw)
            data = records[metric][mask]
            if data.size:
                values[i, j] = np.median(data)
                p25[i, j] = np.percentile(data, 25)
                p75[i, j] = np.percentile(data, 75)
    return methods, yaw_levels, values, np.stack([p25, p75], axis=0)


def save_monte_carlo_summary(records: np.ndarray, path: Path) -> None:
    methods = list(LABELS)
    yaw_levels = np.unique(records["yaw_init_error_deg"])

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)

    ax = axes[0, 0]
    for method in methods:
        rates = []
        for yaw in yaw_levels:
            mask = (records["method"] == method) & (records["yaw_init_error_deg"] == yaw)
            rates.append(100.0 * np.mean(records["converged_2deg"][mask]))
        ax.plot(yaw_levels, rates, marker="o", color=COLORS[method], label=LABELS[method])
    ax.set_title("Convergence rate")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("runs below 2 deg rotation error (%)")
    ax.set_ylim(-3, 103)
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[0, 1]
    methods, yaw_levels, med, spread = _aggregate(records, "rotation_error_deg")
    for i, method in enumerate(methods):
        yerr = np.vstack([med[i] - spread[0, i], spread[1, i] - med[i]])
        ax.errorbar(
            yaw_levels,
            med[i],
            yerr=yerr,
            marker="o",
            capsize=3,
            color=COLORS[method],
            label=LABELS[method],
        )
    ax.set_yscale("log")
    ax.set_title("Final rotation error")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("median error (deg, log scale)")
    ax.grid(True, which="both", alpha=0.25)

    ax = axes[1, 0]
    methods, yaw_levels, med, _ = _aggregate(records, "nfev")
    for i, method in enumerate(methods):
        ax.plot(yaw_levels, med[i], marker="o", color=COLORS[method], label=LABELS[method])
    ax.set_title("Optimizer effort")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("median function evaluations")
    ax.grid(True, alpha=0.25)

    ax = axes[1, 1]
    methods, yaw_levels, med, _ = _aggregate(records, "tilt_yaw_coupling")
    for i, method in enumerate(methods):
        ax.plot(yaw_levels, med[i], marker="o", color=COLORS[method], label=LABELS[method])
    ax.set_title("Tilt-yaw coupling at solution")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("normalized Hessian cross block")
    ax.grid(True, alpha=0.25)

    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_all_figures(
    scene: SyntheticScene,
    records: np.ndarray,
    curve: dict[str, np.ndarray],
    landscape: dict[str, np.ndarray],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    save_scene_plot(scene, output_dir / "scene_3d.png")
    save_image_observation_plot(scene, output_dir / "image_measurements.png")
    save_singularity_plot(curve, output_dir / "axis_singularity.png")
    save_landscape_plot(landscape, output_dir / "cost_landscape.png")
    save_monte_carlo_summary(records, output_dir / "monte_carlo_summary.png")


def _aggregate_methods(
    records: np.ndarray,
    methods: list[str],
    metric: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    yaw_levels = np.unique(records["yaw_init_error_deg"])
    values = np.full((len(methods), len(yaw_levels)), np.nan)
    p25 = np.full_like(values, np.nan)
    p75 = np.full_like(values, np.nan)

    for i, method in enumerate(methods):
        for j, yaw in enumerate(yaw_levels):
            mask = (records["method"] == method) & (records["yaw_init_error_deg"] == yaw)
            data = records[metric][mask]
            data = data[np.isfinite(data)]
            if data.size:
                values[i, j] = np.median(data)
                p25[i, j] = np.percentile(data, 25)
                p75[i, j] = np.percentile(data, 75)
    return yaw_levels, values, np.stack([p25, p75], axis=0)


def save_ba_summary(records: np.ndarray, path: Path) -> None:
    methods = ["ba_uv_joint", "ba_polar_plain_joint", "ba_polar_cov_joint", "ba_polar_staged"]
    yaw_levels = np.unique(records["yaw_init_error_deg"])

    fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)

    ax = axes[0, 0]
    for method in methods:
        rates = []
        for yaw in yaw_levels:
            mask = (records["method"] == method) & (records["yaw_init_error_deg"] == yaw)
            rates.append(100.0 * np.mean(records["converged"][mask]))
        ax.plot(yaw_levels, rates, marker="o", color=COLORS[method], label=LABELS[method])
    ax.set_title("BA convergence rate")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("pose < 3 deg and inlier depth RMSE < 45% (%)")
    ax.set_ylim(-3, 103)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[0, 1]
    yaw_levels, med, spread = _aggregate_methods(records, methods, "rotation_error_deg")
    for i, method in enumerate(methods):
        yerr = np.vstack([med[i] - spread[0, i], spread[1, i] - med[i]])
        ax.errorbar(
            yaw_levels,
            med[i],
            yerr=yerr,
            marker="o",
            capsize=3,
            color=COLORS[method],
            label=LABELS[method],
        )
    ax.set_yscale("log")
    ax.set_title("Final pose error")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("median rotation error (deg)")
    ax.grid(True, which="both", alpha=0.25)

    ax = axes[0, 2]
    yaw_levels, med, spread = _aggregate_methods(records, methods, "inlier_depth_rel_rmse")
    for i, method in enumerate(methods):
        yerr = np.vstack([med[i] - spread[0, i], spread[1, i] - med[i]])
        ax.errorbar(
            yaw_levels,
            med[i],
            yerr=yerr,
            marker="o",
            capsize=3,
            color=COLORS[method],
            label=LABELS[method],
        )
    ax.set_yscale("log")
    ax.set_title("Final inverse-depth BA quality")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("inlier relative depth RMSE")
    ax.grid(True, which="both", alpha=0.25)

    ax = axes[1, 0]
    yaw_levels, med, _ = _aggregate_methods(records, methods, "nfev")
    for i, method in enumerate(methods):
        ax.plot(yaw_levels, med[i], marker="o", color=COLORS[method], label=LABELS[method])
    ax.set_title("Optimizer effort")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("median function evaluations")
    ax.grid(True, alpha=0.25)

    ax = axes[1, 1]
    staged_mask = records["method"] == "ba_polar_staged"
    staged = records[staged_mask]
    yaws = np.unique(staged["yaw_init_error_deg"])
    initial = []
    after_stage = []
    final = []
    for yaw in yaws:
        mask = staged["yaw_init_error_deg"] == yaw
        initial.append(np.median(staged["initial_rotation_error_deg"][mask]))
        after_stage.append(np.median(staged["stage_rotation_error_deg"][mask]))
        final.append(np.median(staged["rotation_error_deg"][mask]))
    ax.plot(yaws, initial, marker="o", label="initial", color="#777777")
    ax.plot(yaws, after_stage, marker="o", label="after staged init", color=COLORS["ba_polar_staged"])
    ax.plot(yaws, final, marker="o", label="after joint BA", color="#222222")
    ax.set_yscale("log")
    ax.set_title("What staged initialization changes")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("median pose error (deg)")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[1, 2]
    yaw_levels, med, _ = _aggregate_methods(records, methods, "yaw_error_deg")
    for i, method in enumerate(methods):
        ax.plot(yaw_levels, med[i], marker="o", color=COLORS[method], label=LABELS[method])
    ax.set_yscale("log")
    ax.set_title("Final yaw error")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("median yaw error (deg)")
    ax.grid(True, which="both", alpha=0.25)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)
