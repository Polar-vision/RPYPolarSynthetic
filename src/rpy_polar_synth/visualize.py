from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .ba_experiment import BAScene
from .experiment import SyntheticScene
from .free_xyz_ba_experiment import FreeXYZBAScene
from .geometry import rpy_matrix
from .realistic_ba_experiment import RealisticBAScene


COLORS = {
    "uv_joint": "#4C78A8",
    "polar_plain_joint": "#F58518",
    "polar_cov_joint": "#54A24B",
    "polar_staged": "#B279A2",
    "ba_uv_joint": "#4C78A8",
    "ba_polar_plain_joint": "#F58518",
    "ba_polar_cov_joint": "#54A24B",
    "ba_polar_staged": "#B279A2",
    "xyz_uv_joint": "#4C78A8",
    "xyz_polar_cov_joint": "#54A24B",
    "xyz_polar_staged": "#B279A2",
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
    "xyz_uv_joint": "free-XYZ UV joint",
    "xyz_polar_cov_joint": "free-XYZ cov-aware polar",
    "xyz_polar_staged": "free-XYZ staged polar",
}


MARKERS = {
    "uv_joint": "o",
    "polar_plain_joint": "s",
    "polar_cov_joint": "^",
    "polar_staged": "D",
    "ba_uv_joint": "o",
    "ba_polar_plain_joint": "s",
    "ba_polar_cov_joint": "^",
    "ba_polar_staged": "D",
    "xyz_uv_joint": "o",
    "xyz_polar_cov_joint": "^",
    "xyz_polar_staged": "D",
}


LINESTYLES = {
    "uv_joint": "-",
    "polar_plain_joint": "--",
    "polar_cov_joint": "-.",
    "polar_staged": ":",
    "ba_uv_joint": "-",
    "ba_polar_plain_joint": "--",
    "ba_polar_cov_joint": "-.",
    "ba_polar_staged": ":",
    "xyz_uv_joint": "-",
    "xyz_polar_cov_joint": "-.",
    "xyz_polar_staged": ":",
}


def _x_offsets(yaw_levels: np.ndarray, methods: list[str]) -> dict[str, np.ndarray]:
    if yaw_levels.size <= 1 or not methods:
        return {method: yaw_levels.copy() for method in methods}

    sorted_levels = np.sort(yaw_levels.astype(float))
    deltas = np.diff(sorted_levels)
    base_step = float(np.min(deltas)) if deltas.size else 1.0
    jitter = min(base_step * 0.18, 1.5)
    center = (len(methods) - 1) / 2.0
    offsets = {}
    for i, method in enumerate(methods):
        offsets[method] = yaw_levels + (i - center) * jitter
    return offsets


def _plot_series(ax, x, y, method: str, label: str, yerr=None, zorder: int = 2) -> None:
    common = {
        "color": COLORS[method],
        "marker": MARKERS.get(method, "o"),
        "linestyle": LINESTYLES.get(method, "-"),
        "linewidth": 1.8,
        "markersize": 5.5,
        "label": label,
        "zorder": zorder,
    }
    if yerr is None:
        ax.plot(x, y, **common)
    else:
        ax.errorbar(
            x,
            y,
            yerr=yerr,
            capsize=3,
            **common,
        )


def _monte_carlo_metadata(records: np.ndarray) -> tuple[int, int, int]:
    yaw_levels = np.unique(records["yaw_init_error_deg"])
    trial_counts = []
    for yaw in yaw_levels:
        mask = records["yaw_init_error_deg"] == yaw
        trial_counts.append(len(np.unique(records["trial"][mask])))
    n_trials = int(min(trial_counts)) if trial_counts else 0
    n_methods = int(len(np.unique(records["method"])))
    return n_trials, int(len(yaw_levels)), n_methods


def _camera_axes_world(params: np.ndarray) -> np.ndarray:
    return rpy_matrix(params).T @ np.eye(3)


def _set_equal_3d(ax, points: np.ndarray, padding: float = 0.12) -> None:
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    center = 0.5 * (mins + maxs)
    half_span = 0.5 * np.max(maxs - mins)
    half_span = max(half_span * (1.0 + padding), 1.0)
    ax.set_xlim(center[0] - half_span, center[0] + half_span)
    ax.set_ylim(center[1] - half_span, center[1] + half_span)
    ax.set_zlim(center[2] - half_span, center[2] + half_span)
    ax.set_box_aspect((1.0, 1.0, 1.0))


def _plot_camera_frame(
    ax,
    center: np.ndarray,
    params: np.ndarray,
    axis_length: float,
    label: str,
    marker_color: str,
) -> None:
    ax.scatter(
        [center[0]],
        [center[1]],
        [center[2]],
        s=34,
        c=marker_color,
        edgecolors="black",
        linewidths=0.5,
    )
    axes = _camera_axes_world(params)
    for idx, color in enumerate(["#D62728", "#2CA02C", "#1F77B4"]):
        direction = axes[:, idx] * axis_length
        ax.quiver(
            center[0],
            center[1],
            center[2],
            direction[0],
            direction[1],
            direction[2],
            color=color,
            linewidth=2.2 if idx == 2 else 1.5,
            arrow_length_ratio=0.12,
        )
    text_offset = np.array([0.06, 0.06, 0.06]) * axis_length
    ax.text(*(center + text_offset), label, fontsize=8, color=marker_color)


def _plot_anchor_rays(ax, points_world: np.ndarray, max_rays: int = 18) -> None:
    if points_world.size == 0:
        return
    indices = np.linspace(0, points_world.shape[0] - 1, min(points_world.shape[0], max_rays), dtype=int)
    for idx, point in enumerate(points_world[indices]):
        ax.plot(
            [0.0, point[0]],
            [0.0, point[1]],
            [0.0, point[2]],
            color="#B8B8B8",
            linewidth=0.9,
            alpha=0.35,
            label="anchor rays" if idx == 0 else None,
        )


def save_ba_scene_plot(scene: BAScene, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    points_world = scene.points_world

    fig = plt.figure(figsize=(8.4, 6.4))
    ax = fig.add_subplot(111, projection="3d")

    scatter = ax.scatter(
        points_world[:, 0],
        points_world[:, 1],
        points_world[:, 2],
        c=scene.true_depths,
        s=16,
        cmap="viridis",
        alpha=0.88,
        label="scene points",
    )
    outlier_points = points_world[~scene.inlier_mask]
    if outlier_points.size:
        ax.scatter(
            outlier_points[:, 0],
            outlier_points[:, 1],
            outlier_points[:, 2],
            c="black",
            marker="x",
            s=36,
            linewidths=1.0,
            label="shuffled-track outliers",
        )

    _plot_anchor_rays(ax, points_world)
    _plot_camera_frame(ax, np.zeros(3), np.zeros(3), axis_length=0.45, label="anchor view", marker_color="#333333")
    _plot_camera_frame(
        ax,
        scene.center2_world,
        scene.true_params,
        axis_length=0.45,
        label="target view",
        marker_color="#9467BD",
    )

    baseline = np.vstack([np.zeros(3), scene.center2_world])
    ax.plot(
        baseline[:, 0],
        baseline[:, 1],
        baseline[:, 2],
        color="#666666",
        linestyle="--",
        linewidth=1.5,
        label="camera baseline",
    )

    all_points = np.vstack([points_world, np.zeros(3), scene.center2_world])
    _set_equal_3d(ax, all_points)
    ax.set_title("Experiment 2 synthetic scene")
    ax.set_xlabel("world x")
    ax.set_ylabel("world y")
    ax.set_zlabel("world z")
    ax.legend(loc="upper left", fontsize=8)
    colorbar = fig.colorbar(scatter, ax=ax, shrink=0.76, pad=0.08)
    colorbar.set_label("true depth (m)")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_realistic_ba_scene_plot(scene: RealisticBAScene, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    points_world = scene.points_world

    fig = plt.figure(figsize=(8.8, 6.4))
    ax = fig.add_subplot(111, projection="3d")

    scatter = ax.scatter(
        points_world[:, 0],
        points_world[:, 1],
        points_world[:, 2],
        c=scene.true_depths,
        s=16,
        cmap="plasma",
        alpha=0.88,
        label="scene points",
    )
    outlier_points = points_world[~scene.inlier_mask]
    if outlier_points.size:
        ax.scatter(
            outlier_points[:, 0],
            outlier_points[:, 1],
            outlier_points[:, 2],
            c="black",
            marker="x",
            s=36,
            linewidths=1.0,
            label="shuffled-track outliers",
        )

    _plot_anchor_rays(ax, points_world, max_rays=22)
    _plot_camera_frame(ax, np.zeros(3), np.zeros(3), axis_length=0.42, label="anchor view", marker_color="#333333")

    camera_colors = ["#9467BD", "#8C564B"]
    for view, (center, params) in enumerate(zip(scene.true_centers_world, scene.true_params), start=2):
        _plot_camera_frame(
            ax,
            center,
            params,
            axis_length=0.42,
            label=f"view {view}",
            marker_color=camera_colors[(view - 2) % len(camera_colors)],
        )

    camera_path = np.vstack([np.zeros(3), scene.true_centers_world])
    ax.plot(
        camera_path[:, 0],
        camera_path[:, 1],
        camera_path[:, 2],
        color="#666666",
        linestyle="--",
        linewidth=1.5,
        label="camera baseline path",
    )

    all_points = np.vstack([points_world, np.zeros(3), scene.true_centers_world])
    _set_equal_3d(ax, all_points)
    ax.set_title("Experiment 3 synthetic local BA window")
    ax.set_xlabel("world x")
    ax.set_ylabel("world y")
    ax.set_zlabel("world z")
    ax.legend(loc="upper left", fontsize=8)
    colorbar = fig.colorbar(scatter, ax=ax, shrink=0.76, pad=0.08)
    colorbar.set_label("true depth (m)")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


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
    x_offsets = landscape.get("x_offsets_deg")
    y_offsets = landscape.get("y_offsets_deg")
    x_axis = str(landscape.get("x_axis", "yaw"))
    y_axis = str(landscape.get("y_axis", "pitch"))
    if x_offsets is None or y_offsets is None:
        x_offsets = landscape["yaw_offsets_deg"]
        y_offsets = landscape["pitch_offsets_deg"]
    extent = [x_offsets.min(), x_offsets.max(), y_offsets.min(), y_offsets.max()]
    items = [
        ("uv", "UV cost"),
        ("theta_only", "theta-only polar cost"),
        ("polar", "cov-aware polar cost"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(13, 4), constrained_layout=True)
    fig.suptitle(f"{y_axis} offset vs {x_axis} offset")
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
        ax.set_xlabel(f"{x_axis} offset (deg)")
        ax.set_ylabel(f"{y_axis} offset (deg)")
        fig.colorbar(image, ax=ax, label="log10(cost - min + 1)")

    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_landscape_overview(landscapes: dict[str, dict[str, np.ndarray]], path: Path) -> None:
    items = [
        ("uv", "UV cost"),
        ("theta_only", "theta-only polar cost"),
        ("polar", "cov-aware polar cost"),
    ]

    fig, axes = plt.subplots(
        len(landscapes),
        len(items),
        figsize=(13, 11),
        constrained_layout=True,
    )
    for row, (slice_name, landscape) in enumerate(landscapes.items()):
        x_offsets = landscape["x_offsets_deg"]
        y_offsets = landscape["y_offsets_deg"]
        x_axis = str(landscape["x_axis"])
        y_axis = str(landscape["y_axis"])
        extent = [x_offsets.min(), x_offsets.max(), y_offsets.min(), y_offsets.max()]
        for col, (key, title) in enumerate(items):
            ax = axes[row, col]
            image = ax.imshow(
                landscape[key],
                origin="lower",
                extent=extent,
                aspect="auto",
                cmap="magma",
            )
            ax.axvline(0.0, color="white", linewidth=0.8, alpha=0.7)
            ax.axhline(0.0, color="white", linewidth=0.8, alpha=0.7)
            if row == 0:
                ax.set_title(title)
            ax.set_xlabel(f"{x_axis} offset (deg)")
            ax.set_ylabel(f"{y_axis} offset (deg)")
            ax.text(
                0.02,
                0.95,
                slice_name,
                transform=ax.transAxes,
                va="top",
                ha="left",
                color="white",
                fontsize=9,
                bbox={"facecolor": "black", "alpha": 0.35, "edgecolor": "none", "pad": 3},
            )
            fig.colorbar(image, ax=ax, label="log10(cost - min + 1)")

    fig.savefig(path, dpi=180)
    plt.close(fig)


def _aggregate(records: np.ndarray, metric: str) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    methods = [method for method in LABELS if method in set(records["method"])]
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
    methods = [method for method in LABELS if method in set(records["method"])]
    yaw_levels = np.unique(records["yaw_init_error_deg"])
    plot_x = _x_offsets(yaw_levels, methods)
    n_trials, n_yaws, _ = _monte_carlo_metadata(records)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    fig.suptitle(
        f"Single-view Monte Carlo summary: {n_trials} trials/level, "
        f"{n_trials * n_yaws} runs/method\n"
        "Markers/curves show medians; bars show 25th-75th percentiles; x jitter is display-only.",
        fontsize=12,
    )

    ax = axes[0, 0]
    for i, method in enumerate(methods):
        rates = []
        for yaw in yaw_levels:
            mask = (records["method"] == method) & (records["yaw_init_error_deg"] == yaw)
            rates.append(100.0 * np.mean(records["converged_2deg"][mask]))
        _plot_series(ax, plot_x[method], rates, method, LABELS[method], zorder=2 + i)
    ax.set_title("Convergence rate")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("runs below 2 deg rotation error (%)")
    ax.set_ylim(-3, 103)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8, ncols=2)

    ax = axes[0, 1]
    methods, yaw_levels, med, spread = _aggregate(records, "rotation_error_deg")
    plot_x = _x_offsets(yaw_levels, methods)
    for i, method in enumerate(methods):
        yerr = np.vstack([med[i] - spread[0, i], spread[1, i] - med[i]])
        _plot_series(ax, plot_x[method], med[i], method, LABELS[method], yerr=yerr, zorder=2 + i)
    ax.set_yscale("log")
    ax.set_title("Final rotation error")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("median error (deg, log scale)")
    ax.grid(True, which="both", alpha=0.25)

    ax = axes[1, 0]
    methods, yaw_levels, med, _ = _aggregate(records, "nfev")
    plot_x = _x_offsets(yaw_levels, methods)
    for i, method in enumerate(methods):
        _plot_series(ax, plot_x[method], med[i], method, LABELS[method], zorder=2 + i)
    ax.set_title("Optimizer effort")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("median function evaluations")
    ax.grid(True, alpha=0.25)

    ax = axes[1, 1]
    methods, yaw_levels, med, _ = _aggregate(records, "tilt_yaw_coupling")
    plot_x = _x_offsets(yaw_levels, methods)
    for i, method in enumerate(methods):
        _plot_series(ax, plot_x[method], med[i], method, LABELS[method], zorder=2 + i)
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
    landscapes: dict[str, dict[str, np.ndarray]],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    save_scene_plot(scene, output_dir / "scene_3d.png")
    save_image_observation_plot(scene, output_dir / "image_measurements.png")
    save_singularity_plot(curve, output_dir / "axis_singularity.png")
    save_landscape_plot(landscapes["pitch-yaw"], output_dir / "cost_landscape.png")
    save_landscape_plot(landscapes["pitch-yaw"], output_dir / "cost_landscape_pitch_yaw.png")
    save_landscape_plot(landscapes["roll-yaw"], output_dir / "cost_landscape_roll_yaw.png")
    save_landscape_plot(landscapes["roll-pitch"], output_dir / "cost_landscape_roll_pitch.png")
    save_landscape_overview(landscapes, output_dir / "cost_landscape_all_slices.png")
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
    plot_x = _x_offsets(yaw_levels, methods)
    n_trials, n_yaws, _ = _monte_carlo_metadata(records)

    fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
    fig.suptitle(
        f"Two-view BA Monte Carlo summary: {n_trials} trials/level, "
        f"{n_trials * n_yaws} runs/method\n"
        "Markers/curves show medians; bars show 25th-75th percentiles; x jitter is display-only.",
        fontsize=12,
    )

    ax = axes[0, 0]
    for i, method in enumerate(methods):
        rates = []
        for yaw in yaw_levels:
            mask = (records["method"] == method) & (records["yaw_init_error_deg"] == yaw)
            rates.append(100.0 * np.mean(records["converged"][mask]))
        _plot_series(ax, plot_x[method], rates, method, LABELS[method], zorder=2 + i)
    ax.set_title("BA convergence rate")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("pose < 3 deg and inlier depth RMSE < 45% (%)")
    ax.set_ylim(-3, 103)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[0, 1]
    yaw_levels, med, spread = _aggregate_methods(records, methods, "rotation_error_deg")
    plot_x = _x_offsets(yaw_levels, methods)
    for i, method in enumerate(methods):
        yerr = np.vstack([med[i] - spread[0, i], spread[1, i] - med[i]])
        _plot_series(ax, plot_x[method], med[i], method, LABELS[method], yerr=yerr, zorder=2 + i)
    ax.set_yscale("log")
    ax.set_title("Final pose error")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("median rotation error (deg)")
    ax.grid(True, which="both", alpha=0.25)

    ax = axes[0, 2]
    yaw_levels, med, spread = _aggregate_methods(records, methods, "inlier_depth_rel_rmse")
    plot_x = _x_offsets(yaw_levels, methods)
    for i, method in enumerate(methods):
        yerr = np.vstack([med[i] - spread[0, i], spread[1, i] - med[i]])
        _plot_series(ax, plot_x[method], med[i], method, LABELS[method], yerr=yerr, zorder=2 + i)
    ax.set_yscale("log")
    ax.set_title("Final inverse-depth BA quality")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("inlier relative depth RMSE")
    ax.grid(True, which="both", alpha=0.25)

    ax = axes[1, 0]
    yaw_levels, med, _ = _aggregate_methods(records, methods, "nfev")
    plot_x = _x_offsets(yaw_levels, methods)
    for i, method in enumerate(methods):
        _plot_series(ax, plot_x[method], med[i], method, LABELS[method], zorder=2 + i)
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
    plot_x = _x_offsets(yaw_levels, methods)
    for i, method in enumerate(methods):
        _plot_series(ax, plot_x[method], med[i], method, LABELS[method], zorder=2 + i)
    ax.set_yscale("log")
    ax.set_title("Final yaw error")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("median yaw error (deg)")
    ax.grid(True, which="both", alpha=0.25)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_realistic_ba_summary(records: np.ndarray, path: Path) -> None:
    methods = ["ba_uv_joint", "ba_polar_plain_joint", "ba_polar_cov_joint", "ba_polar_staged"]
    yaw_levels = np.unique(records["yaw_init_error_deg"])
    plot_x = _x_offsets(yaw_levels, methods)
    n_trials, n_yaws, _ = _monte_carlo_metadata(records)

    fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
    fig.suptitle(
        f"Realistic BA Monte Carlo summary: {n_trials} trials/level, "
        f"{n_trials * n_yaws} runs/method\n"
        "Markers/curves show medians; bars show 25th-75th percentiles; x jitter is display-only.",
        fontsize=12,
    )

    ax = axes[0, 0]
    for i, method in enumerate(methods):
        rates = []
        for yaw in yaw_levels:
            mask = (records["method"] == method) & (records["yaw_init_error_deg"] == yaw)
            rates.append(100.0 * np.mean(records["converged"][mask]))
        _plot_series(ax, plot_x[method], rates, method, LABELS[method], zorder=2 + i)
    ax.set_title("BA convergence rate")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("rotation < 3 deg and inlier depth RMSE < 45% (%)")
    ax.set_ylim(-3, 103)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[0, 1]
    yaw_levels, med, spread = _aggregate_methods(records, methods, "rotation_error_deg")
    plot_x = _x_offsets(yaw_levels, methods)
    for i, method in enumerate(methods):
        yerr = np.vstack([med[i] - spread[0, i], spread[1, i] - med[i]])
        _plot_series(ax, plot_x[method], med[i], method, LABELS[method], yerr=yerr, zorder=2 + i)
    ax.set_yscale("log")
    ax.set_title("Final pose error")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("median rotation error (deg)")
    ax.grid(True, which="both", alpha=0.25)

    ax = axes[0, 2]
    yaw_levels, med, spread = _aggregate_methods(records, methods, "translation_error_m")
    plot_x = _x_offsets(yaw_levels, methods)
    for i, method in enumerate(methods):
        yerr = np.vstack([med[i] - spread[0, i], spread[1, i] - med[i]])
        _plot_series(ax, plot_x[method], med[i], method, LABELS[method], yerr=yerr, zorder=2 + i)
    ax.set_yscale("log")
    ax.set_title("Final translation error")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("median translation error (m)")
    ax.grid(True, which="both", alpha=0.25)

    ax = axes[1, 0]
    yaw_levels, med, spread = _aggregate_methods(records, methods, "inlier_depth_rel_rmse")
    plot_x = _x_offsets(yaw_levels, methods)
    for i, method in enumerate(methods):
        yerr = np.vstack([med[i] - spread[0, i], spread[1, i] - med[i]])
        _plot_series(ax, plot_x[method], med[i], method, LABELS[method], yerr=yerr, zorder=2 + i)
    ax.set_yscale("log")
    ax.set_title("Final inverse-depth BA quality")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("inlier relative depth RMSE")
    ax.grid(True, which="both", alpha=0.25)

    ax = axes[1, 1]
    yaw_levels, med, _ = _aggregate_methods(records, methods, "nfev")
    plot_x = _x_offsets(yaw_levels, methods)
    for i, method in enumerate(methods):
        _plot_series(ax, plot_x[method], med[i], method, LABELS[method], zorder=2 + i)
    ax.set_title("Optimizer effort")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("median function evaluations")
    ax.grid(True, alpha=0.25)

    ax = axes[1, 2]
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

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_free_xyz_scene_plot(scene: FreeXYZBAScene, path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(8.8, 6.5))
    ax = fig.add_subplot(111, projection="3d")

    scatter = ax.scatter(
        scene.points_world[:, 0],
        scene.points_world[:, 1],
        scene.points_world[:, 2],
        c=scene.track_lengths,
        s=16,
        cmap="viridis",
        alpha=0.88,
        label="landmarks",
    )

    path_points = scene.true_centers_world
    ax.plot(
        path_points[:, 0],
        path_points[:, 1],
        path_points[:, 2],
        color="#666666",
        linestyle="--",
        linewidth=1.5,
        label="camera path",
    )

    for view, (center, params) in enumerate(zip(scene.true_centers_world, scene.true_params)):
        marker_color = "#333333" if view < scene.fixed_view_count else "#9467BD"
        label = f"view {view + 1}"
        if view < scene.fixed_view_count:
            label += " (fixed)"
        else:
            label += " (optimized)"
        _plot_camera_frame(ax, center, params, axis_length=0.36, label=label, marker_color=marker_color)

    all_points = np.vstack([scene.points_world, scene.true_centers_world])
    _set_equal_3d(ax, all_points)
    ax.set_title(title)
    ax.set_xlabel("world x")
    ax.set_ylabel("world y")
    ax.set_zlabel("world z")
    ax.legend(loc="upper left", fontsize=8)
    colorbar = fig.colorbar(scatter, ax=ax, shrink=0.76, pad=0.08)
    colorbar.set_label("track length (views)")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_free_xyz_summary(records: np.ndarray, path: Path, title: str) -> None:
    methods = ["xyz_uv_joint", "xyz_polar_cov_joint", "xyz_polar_staged"]
    yaw_levels = np.unique(records["yaw_init_error_deg"])
    plot_x = _x_offsets(yaw_levels, methods)
    n_trials, n_yaws, _ = _monte_carlo_metadata(records)

    fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
    fig.suptitle(
        f"{title}: {n_trials} trials/level, {n_trials * n_yaws} runs/method\n"
        "Markers/curves show medians; bars show 25th-75th percentiles; x jitter is display-only.",
        fontsize=12,
    )

    ax = axes[0, 0]
    for i, method in enumerate(methods):
        rates = []
        for yaw in yaw_levels:
            mask = (records["method"] == method) & (records["yaw_init_error_deg"] == yaw)
            rates.append(100.0 * np.mean(records["converged"][mask]))
        _plot_series(ax, plot_x[method], rates, method, LABELS[method], zorder=2 + i)
    ax.set_title("BA convergence rate")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("pose < 3 deg and structure rel. RMSE < 30% (%)")
    ax.set_ylim(-3, 103)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[0, 1]
    yaw_levels, med, spread = _aggregate_methods(records, methods, "rotation_error_deg")
    plot_x = _x_offsets(yaw_levels, methods)
    for i, method in enumerate(methods):
        yerr = np.vstack([med[i] - spread[0, i], spread[1, i] - med[i]])
        _plot_series(ax, plot_x[method], med[i], method, LABELS[method], yerr=yerr, zorder=2 + i)
    ax.set_yscale("log")
    ax.set_title("Final pose error")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("max rotation error across optimized poses (deg)")
    ax.grid(True, which="both", alpha=0.25)

    ax = axes[0, 2]
    yaw_levels, med, spread = _aggregate_methods(records, methods, "structure_rel_rmse")
    plot_x = _x_offsets(yaw_levels, methods)
    for i, method in enumerate(methods):
        yerr = np.vstack([med[i] - spread[0, i], spread[1, i] - med[i]])
        _plot_series(ax, plot_x[method], med[i], method, LABELS[method], yerr=yerr, zorder=2 + i)
    ax.set_yscale("log")
    ax.set_title("Final structure quality")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("relative XYZ RMSE")
    ax.grid(True, which="both", alpha=0.25)

    ax = axes[1, 0]
    yaw_levels, med, spread = _aggregate_methods(records, methods, "translation_error_m")
    plot_x = _x_offsets(yaw_levels, methods)
    for i, method in enumerate(methods):
        yerr = np.vstack([med[i] - spread[0, i], spread[1, i] - med[i]])
        _plot_series(ax, plot_x[method], med[i], method, LABELS[method], yerr=yerr, zorder=2 + i)
    ax.set_yscale("log")
    ax.set_title("Final translation error")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("max center error across optimized poses (m)")
    ax.grid(True, which="both", alpha=0.25)

    ax = axes[1, 1]
    yaw_levels, med, _ = _aggregate_methods(records, methods, "nfev")
    plot_x = _x_offsets(yaw_levels, methods)
    for i, method in enumerate(methods):
        _plot_series(ax, plot_x[method], med[i], method, LABELS[method], zorder=2 + i)
    ax.set_title("Optimizer effort")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("median function evaluations")
    ax.grid(True, alpha=0.25)

    ax = axes[1, 2]
    staged_mask = records["method"] == "xyz_polar_staged"
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
    ax.plot(yaws, after_stage, marker="o", label="after staged init", color=COLORS["xyz_polar_staged"])
    ax.plot(yaws, final, marker="o", label="after joint BA", color="#222222")
    ax.set_yscale("log")
    ax.set_title("What staged initialization changes")
    ax.set_xlabel("initial yaw error (deg)")
    ax.set_ylabel("median pose error (deg)")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180)
    plt.close(fig)
