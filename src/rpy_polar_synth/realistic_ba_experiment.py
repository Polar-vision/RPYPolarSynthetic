from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix

from .experiment import CameraConfig, write_csv
from .geometry import (
    bearing_to_polar,
    equidistant_project,
    equidistant_unproject,
    pixel_to_polar,
    polar_covariance_from_pixel,
    polar_to_bearing,
    rotation_angle_deg,
    rpy_matrix,
    wrap_angle,
)


@dataclass(frozen=True)
class RealisticBAScenarioConfig:
    n_points: int = 90
    theta1_min_deg: float = 0.5
    theta1_max_deg: float = 64.0
    theta_target_max_deg: float = 72.0
    depth_min: float = 3.5
    depth_max: float = 16.0
    true_rpy_deg: tuple[tuple[float, float, float], tuple[float, float, float]] = (
        (8.0, -13.0, 22.0),
        (12.0, -9.0, 36.0),
    )
    centers_world: tuple[tuple[float, float, float], tuple[float, float, float]] = (
        (0.78, -0.18, 0.15),
        (1.52, -0.34, 0.27),
    )
    outlier_fraction: float = 0.06
    first_view_sigma_px: float = 1.25
    target_view_sigma_px: float = 1.25
    motion_prior_sigma_m: float = 0.10
    seed: int = 53


@dataclass
class RealisticBAScene:
    points_world: np.ndarray
    anchor_bearings: np.ndarray
    true_depths: np.ndarray
    observed_pixels1: np.ndarray
    observed_pixels: np.ndarray
    observed_polar: np.ndarray
    sqrt_info_polar: np.ndarray
    phi_gates: np.ndarray
    inlier_mask: np.ndarray
    true_params: np.ndarray
    true_centers_world: np.ndarray
    motion_prior_norms: np.ndarray
    camera: CameraConfig
    first_view_sigma_px: float
    target_view_sigma_px: float
    motion_prior_sigma_m: float


@dataclass
class RealisticBAResult:
    method: str
    params: np.ndarray
    centers_world: np.ndarray
    log_inv_depths: np.ndarray
    success: bool
    cost: float
    nfev: int
    rotation_error_deg: float
    translation_error_m: float
    tilt_error_deg: float
    yaw_error_deg: float
    depth_rel_rmse: float
    depth_rel_median: float
    inlier_depth_rel_rmse: float
    inlier_depth_rel_median: float
    stage_rotation_error_deg: float
    message: str


def _n_target_views(scene: RealisticBAScene) -> int:
    return int(scene.true_params.shape[0])


def _depths_from_log_inv(log_inv_depths: np.ndarray) -> np.ndarray:
    return np.exp(-log_inv_depths)


def _point_worlds(anchor_bearings: np.ndarray, depths: np.ndarray) -> np.ndarray:
    return anchor_bearings * depths[:, None]


def _pack_ba(params: np.ndarray, centers_world: np.ndarray, log_inv_depths: np.ndarray) -> np.ndarray:
    return np.concatenate([params.ravel(), centers_world.ravel(), log_inv_depths])


def _unpack_ba(x: np.ndarray, n_views: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    params = x[: 3 * n_views].reshape(n_views, 3)
    centers_world = x[3 * n_views : 6 * n_views].reshape(n_views, 3)
    log_inv_depths = x[6 * n_views :]
    return params, centers_world, log_inv_depths


def _max_pose_error(params: np.ndarray, true_params: np.ndarray) -> float:
    errors = [rotation_angle_deg(rpy_matrix(p), rpy_matrix(t)) for p, t in zip(params, true_params)]
    return float(np.max(errors))


def _max_translation_error(centers_world: np.ndarray, true_centers_world: np.ndarray) -> float:
    errors = np.linalg.norm(centers_world - true_centers_world, axis=1)
    return float(np.max(errors))


def make_realistic_ba_scene(
    scenario: RealisticBAScenarioConfig = RealisticBAScenarioConfig(),
    camera: CameraConfig = CameraConfig(),
) -> RealisticBAScene:
    rng = np.random.default_rng(scenario.seed)
    true_params = np.deg2rad(np.array(scenario.true_rpy_deg, dtype=float))
    true_centers_world = np.array(scenario.centers_world, dtype=float)
    n_views = true_params.shape[0]
    true_rotations = np.array([rpy_matrix(params) for params in true_params])

    points_world: list[np.ndarray] = []
    depths: list[float] = []
    pixels1: list[np.ndarray] = []
    pixels_target: list[list[np.ndarray]] = [[] for _ in range(n_views)]

    attempts = 0
    while len(points_world) < scenario.n_points and attempts < scenario.n_points * 400:
        attempts += 1
        if len(points_world) < max(10, scenario.n_points // 5):
            theta = np.deg2rad(rng.uniform(scenario.theta1_min_deg, 3.0))
        else:
            theta = np.deg2rad(rng.uniform(scenario.theta1_min_deg, scenario.theta1_max_deg))
        phi = rng.uniform(-np.pi, np.pi)
        depth = rng.uniform(scenario.depth_min, scenario.depth_max)
        ray1 = polar_to_bearing(np.array(theta), np.array(phi))
        point_world = depth * ray1

        pixel1 = equidistant_project(point_world.reshape(1, 3), camera.f, camera.cx, camera.cy)[0]
        if not (8.0 < pixel1[0] < camera.width - 8.0 and 8.0 < pixel1[1] < camera.height - 8.0):
            continue

        target_pixels: list[np.ndarray] = []
        valid = True
        for view in range(n_views):
            q = true_rotations[view] @ (point_world - true_centers_world[view])
            if q[2] <= 0.15:
                valid = False
                break
            theta_target = np.arctan2(np.linalg.norm(q[:2]), q[2])
            if theta_target > np.deg2rad(scenario.theta_target_max_deg):
                valid = False
                break
            pixel = equidistant_project(q.reshape(1, 3), camera.f, camera.cx, camera.cy)[0]
            if not (8.0 < pixel[0] < camera.width - 8.0 and 8.0 < pixel[1] < camera.height - 8.0):
                valid = False
                break
            target_pixels.append(pixel)

        if not valid:
            continue

        points_world.append(point_world)
        depths.append(float(depth))
        pixels1.append(pixel1)
        for view, pixel in enumerate(target_pixels):
            pixels_target[view].append(pixel)

    if len(points_world) < scenario.n_points:
        raise RuntimeError("Could not sample enough points visible in all target views for Experiment 3.")

    clean_pixels1 = np.array(pixels1)
    clean_target_pixels = np.array([np.array(view_pixels) for view_pixels in pixels_target])
    true_depths = np.array(depths)

    observed_pixels1 = clean_pixels1 + rng.normal(0.0, scenario.first_view_sigma_px, size=clean_pixels1.shape)
    anchor_bearings = equidistant_unproject(observed_pixels1, camera.f, camera.cx, camera.cy)

    observed_pixels = clean_target_pixels + rng.normal(
        0.0,
        scenario.target_view_sigma_px,
        size=clean_target_pixels.shape,
    )

    inlier_mask = np.ones(scenario.n_points, dtype=bool)
    n_outliers = int(round(scenario.outlier_fraction * scenario.n_points))
    if n_outliers > 0:
        outlier_indices = rng.choice(scenario.n_points, size=n_outliers, replace=False)
        for view in range(n_views):
            replacement = observed_pixels[view].copy()
            rng.shuffle(replacement, axis=0)
            observed_pixels[view, outlier_indices] = replacement[outlier_indices]
        inlier_mask[outlier_indices] = False

    observed_polar = np.array(
        [pixel_to_polar(observed_pixels[view], camera.f, camera.cx, camera.cy) for view in range(n_views)]
    )

    covariances = np.array(
        [
            [
                polar_covariance_from_pixel(
                    pixel,
                    scenario.target_view_sigma_px,
                    camera.f,
                    camera.cx,
                    camera.cy,
                )
                for pixel in observed_pixels[view]
            ]
            for view in range(n_views)
        ]
    )
    sqrt_info = np.empty_like(covariances)
    for view in range(n_views):
        for i, cov in enumerate(covariances[view]):
            sqrt_info[view, i] = np.linalg.inv(np.linalg.cholesky(cov))

    gate_start = np.sin(np.deg2rad(3.0))
    phi_gates = np.clip(np.sin(observed_polar[:, :, 0]) / gate_start, 0.0, 1.0)
    motion_prior_norms = np.array(
        [
            np.linalg.norm(true_centers_world[0]),
            *[
                np.linalg.norm(true_centers_world[view] - true_centers_world[view - 1])
                for view in range(1, n_views)
            ],
        ]
    )

    return RealisticBAScene(
        points_world=np.array(points_world),
        anchor_bearings=anchor_bearings,
        true_depths=true_depths,
        observed_pixels1=observed_pixels1,
        observed_pixels=observed_pixels,
        observed_polar=observed_polar,
        sqrt_info_polar=sqrt_info,
        phi_gates=phi_gates,
        inlier_mask=inlier_mask,
        true_params=true_params,
        true_centers_world=true_centers_world,
        motion_prior_norms=motion_prior_norms,
        camera=camera,
        first_view_sigma_px=scenario.first_view_sigma_px,
        target_view_sigma_px=scenario.target_view_sigma_px,
        motion_prior_sigma_m=scenario.motion_prior_sigma_m,
    )


def _predict_target_points(
    params: np.ndarray,
    centers_world: np.ndarray,
    log_inv_depths: np.ndarray,
    scene: RealisticBAScene,
) -> np.ndarray:
    depths = _depths_from_log_inv(log_inv_depths)
    points_world = _point_worlds(scene.anchor_bearings, depths)
    predictions = []
    for view in range(_n_target_views(scene)):
        vectors = points_world - centers_world[view]
        predictions.append((rpy_matrix(params[view]) @ vectors.T).T)
    return np.array(predictions)


def _translation_prior_residual(centers_world: np.ndarray, scene: RealisticBAScene) -> np.ndarray:
    residuals = []
    sigma = max(scene.motion_prior_sigma_m, 1e-12)
    residuals.append((np.linalg.norm(centers_world[0]) - scene.motion_prior_norms[0]) / sigma)
    for view in range(1, _n_target_views(scene)):
        baseline = centers_world[view] - centers_world[view - 1]
        residuals.append((np.linalg.norm(baseline) - scene.motion_prior_norms[view]) / sigma)
    return np.array(residuals)


def ba_uv_residual(x: np.ndarray, scene: RealisticBAScene) -> np.ndarray:
    params, centers_world, log_inv_depths = _unpack_ba(x, _n_target_views(scene))
    q = _predict_target_points(params, centers_world, log_inv_depths, scene)
    residuals = []
    for view in range(_n_target_views(scene)):
        predicted = equidistant_project(q[view], scene.camera.f, scene.camera.cx, scene.camera.cy)
        residuals.append(((predicted - scene.observed_pixels[view]) / scene.target_view_sigma_px).ravel())
    residuals.append(_translation_prior_residual(centers_world, scene))
    return np.concatenate(residuals)


def ba_polar_residual(
    x: np.ndarray,
    scene: RealisticBAScene,
    covariance_aware: bool = True,
    gate_axis: bool = True,
    theta_only: bool = False,
    phi_only: bool = False,
) -> np.ndarray:
    params, centers_world, log_inv_depths = _unpack_ba(x, _n_target_views(scene))
    q = _predict_target_points(params, centers_world, log_inv_depths, scene)
    predicted = np.array([bearing_to_polar(q_view) for q_view in q])
    residuals: list[np.ndarray] = []

    for view in range(_n_target_views(scene)):
        dtheta = predicted[view, :, 0] - scene.observed_polar[view, :, 0]
        dphi = wrap_angle(predicted[view, :, 1] - scene.observed_polar[view, :, 1])

        if theta_only:
            if covariance_aware:
                sigma_theta = 1.0 / np.maximum(scene.sqrt_info_polar[view, :, 0, 0], 1e-12)
                residuals.append(dtheta / np.maximum(sigma_theta, 1e-12))
            else:
                residuals.append(dtheta / (scene.target_view_sigma_px / scene.camera.f))
            continue

        if phi_only:
            if covariance_aware:
                raw = np.column_stack([np.zeros_like(dtheta), dphi])
                whitened = np.einsum("nij,nj->ni", scene.sqrt_info_polar[view], raw)
                if gate_axis:
                    whitened[:, 1] *= scene.phi_gates[view]
                residuals.append(whitened[:, 1])
            else:
                residuals.append(dphi * scene.phi_gates[view] / 0.03)
            continue

        raw = np.column_stack([dtheta, dphi])
        if covariance_aware:
            whitened = np.einsum("nij,nj->ni", scene.sqrt_info_polar[view], raw)
            if gate_axis:
                whitened[:, 1] *= scene.phi_gates[view]
            residuals.append(whitened.ravel())
        else:
            nominal_theta_sigma = scene.target_view_sigma_px / scene.camera.f
            residuals.append(np.column_stack([dtheta / nominal_theta_sigma, dphi / 0.03]).ravel())

    if not theta_only and not phi_only:
        residuals.append(_translation_prior_residual(centers_world, scene))
    return np.concatenate(residuals)


def _full_ba_sparsity(n_views: int, n_points: int, residual_dim_per_obs: int = 2) -> lil_matrix:
    rows_per_view = residual_dim_per_obs * n_points
    pattern = lil_matrix((rows_per_view * n_views + n_views, 6 * n_views + n_points), dtype=int)
    for view in range(n_views):
        param_offset = 3 * view
        center_offset = 3 * n_views + 3 * view
        row_offset = rows_per_view * view
        for i in range(n_points):
            rows = range(row_offset + residual_dim_per_obs * i, row_offset + residual_dim_per_obs * (i + 1))
            for row in rows:
                pattern[row, param_offset : param_offset + 3] = 1
                pattern[row, center_offset : center_offset + 3] = 1
                pattern[row, 6 * n_views + i] = 1
    prior_row_offset = rows_per_view * n_views
    pattern[prior_row_offset, 3 * n_views : 3 * n_views + 3] = 1
    for view in range(1, n_views):
        row = prior_row_offset + view
        center_prev_offset = 3 * n_views + 3 * (view - 1)
        center_curr_offset = 3 * n_views + 3 * view
        pattern[row, center_prev_offset : center_prev_offset + 3] = 1
        pattern[row, center_curr_offset : center_curr_offset + 3] = 1
    return pattern


def _ba_bounds(scene: RealisticBAScene) -> tuple[np.ndarray, np.ndarray]:
    n_views = _n_target_views(scene)
    n_points = scene.true_depths.size
    lower = np.concatenate(
        [
            np.tile(np.deg2rad([-180.0, -89.0, -360.0]), n_views),
            np.tile(np.array([-3.0, -3.0, -3.0]), n_views),
            np.full(n_points, np.log(1.0 / 60.0)),
        ]
    )
    upper = np.concatenate(
        [
            np.tile(np.deg2rad([180.0, 89.0, 360.0]), n_views),
            np.tile(np.array([3.0, 3.0, 3.0]), n_views),
            np.full(n_points, np.log(1.0 / 1.0)),
        ]
    )
    return lower, upper


def _summarize_result(
    method: str,
    x: np.ndarray,
    scene: RealisticBAScene,
    cost: float,
    success: bool,
    nfev: int,
    message: str,
    stage_rotation_error_deg: float = np.nan,
) -> RealisticBAResult:
    params, centers_world, log_inv_depths = _unpack_ba(x, _n_target_views(scene))
    depth_est = _depths_from_log_inv(log_inv_depths)
    rel_depth = (depth_est - scene.true_depths) / scene.true_depths
    inlier_rel_depth = rel_depth[scene.inlier_mask]

    delta = wrap_angle(params - scene.true_params)
    tilt_errors = np.rad2deg(np.linalg.norm(delta[:, :2], axis=1))
    yaw_errors = np.abs(np.rad2deg(delta[:, 2]))

    return RealisticBAResult(
        method=method,
        params=params,
        centers_world=centers_world,
        log_inv_depths=log_inv_depths,
        success=bool(success),
        cost=float(cost),
        nfev=int(nfev),
        rotation_error_deg=_max_pose_error(params, scene.true_params),
        translation_error_m=_max_translation_error(centers_world, scene.true_centers_world),
        tilt_error_deg=float(np.max(tilt_errors)),
        yaw_error_deg=float(np.max(yaw_errors)),
        depth_rel_rmse=float(np.sqrt(np.mean(rel_depth**2))),
        depth_rel_median=float(np.median(np.abs(rel_depth))),
        inlier_depth_rel_rmse=float(np.sqrt(np.mean(inlier_rel_depth**2))),
        inlier_depth_rel_median=float(np.median(np.abs(inlier_rel_depth))),
        stage_rotation_error_deg=float(stage_rotation_error_deg),
        message=str(message),
    )


def optimize_realistic_ba_joint(
    method: str,
    scene: RealisticBAScene,
    initial_x: np.ndarray,
    max_nfev: int = 120,
) -> RealisticBAResult:
    n_views = _n_target_views(scene)
    if method == "ba_uv_joint":
        residual_fn = lambda x: ba_uv_residual(x, scene)
    elif method == "ba_polar_plain_joint":
        residual_fn = lambda x: ba_polar_residual(x, scene, covariance_aware=False, gate_axis=False)
    elif method == "ba_polar_cov_joint":
        residual_fn = lambda x: ba_polar_residual(x, scene, covariance_aware=True, gate_axis=True)
    else:
        raise ValueError(f"Unknown BA method: {method}")

    result = least_squares(
        residual_fn,
        initial_x,
        bounds=_ba_bounds(scene),
        jac_sparsity=_full_ba_sparsity(n_views, scene.true_depths.size),
        method="trf",
        loss="huber",
        f_scale=2.5,
        x_scale="jac",
        max_nfev=max_nfev,
    )
    return _summarize_result(method, result.x, scene, result.cost, result.success, result.nfev, result.message)


def optimize_realistic_ba_staged(
    scene: RealisticBAScene,
    initial_x: np.ndarray,
    max_nfev_per_stage: int = 90,
) -> RealisticBAResult:
    n_views = _n_target_views(scene)
    params0, centers0, log_inv0 = _unpack_ba(initial_x, n_views)

    # Keep translations and inverse depths fixed during staged rotation
    # initialization so the optimizer cannot hide orientation errors inside the
    # hardest translation-depth coupling.
    def theta_stage(roll_pitch: np.ndarray) -> np.ndarray:
        roll_pitch = roll_pitch.reshape(n_views, 2)
        params = np.column_stack([roll_pitch, params0[:, 2]])
        x = _pack_ba(params, centers0, log_inv0)
        return ba_polar_residual(x, scene, covariance_aware=True, gate_axis=True, theta_only=True)

    stage1 = least_squares(
        theta_stage,
        params0[:, :2].ravel(),
        bounds=(
            np.tile(np.deg2rad([-180.0, -89.0]), n_views),
            np.tile(np.deg2rad([180.0, 89.0]), n_views),
        ),
        method="trf",
        loss="huber",
        f_scale=2.5,
        max_nfev=max_nfev_per_stage,
    )

    roll_pitch1 = stage1.x.reshape(n_views, 2)

    def phi_stage(yaw: np.ndarray) -> np.ndarray:
        params = np.column_stack([roll_pitch1, yaw])
        x = _pack_ba(params, centers0, log_inv0)
        return ba_polar_residual(x, scene, covariance_aware=True, gate_axis=True, phi_only=True)

    stage2 = least_squares(
        phi_stage,
        params0[:, 2].copy(),
        bounds=(
            np.full(n_views, np.deg2rad(-360.0)),
            np.full(n_views, np.deg2rad(360.0)),
        ),
        method="trf",
        loss="huber",
        f_scale=2.5,
        max_nfev=max_nfev_per_stage,
    )

    staged_params = np.column_stack([roll_pitch1, stage2.x])
    staged_x = _pack_ba(staged_params, centers0, log_inv0)
    staged_pose_error = _max_pose_error(staged_params, scene.true_params)

    final = least_squares(
        lambda x: ba_polar_residual(x, scene, covariance_aware=True, gate_axis=True),
        staged_x,
        bounds=_ba_bounds(scene),
        jac_sparsity=_full_ba_sparsity(n_views, scene.true_depths.size),
        method="trf",
        loss="huber",
        f_scale=2.5,
        x_scale="jac",
        max_nfev=max_nfev_per_stage,
    )

    success = bool(stage1.success and stage2.success and final.success)
    message = f"stage1={stage1.message}; stage2={stage2.message}; final={final.message}"
    return _summarize_result(
        "ba_polar_staged",
        final.x,
        scene,
        final.cost,
        success,
        stage1.nfev + stage2.nfev + final.nfev,
        message,
        stage_rotation_error_deg=staged_pose_error,
    )


def _initial_guess(
    scene: RealisticBAScene,
    yaw_error_deg: float,
    tilt_error_deg: float,
    translation_error_m: float,
    depth_log_sigma: float,
    rng: np.random.Generator,
) -> np.ndarray:
    n_views = _n_target_views(scene)
    params = scene.true_params.copy()
    centers = scene.true_centers_world.copy()

    for view in range(n_views):
        tilt_direction = rng.normal(size=2)
        tilt_direction /= max(np.linalg.norm(tilt_direction), 1e-12)
        tilt_error = np.deg2rad(tilt_error_deg) * tilt_direction
        yaw_sign = rng.choice([-1.0, 1.0])
        params[view] += np.array([tilt_error[0], tilt_error[1], yaw_sign * np.deg2rad(yaw_error_deg)])

        center_dir = rng.normal(size=3)
        center_dir /= max(np.linalg.norm(center_dir), 1e-12)
        centers[view] += translation_error_m * center_dir

    log_inv_true = np.log(1.0 / scene.true_depths)
    log_inv_guess = log_inv_true + rng.normal(0.0, depth_log_sigma, size=scene.true_depths.size)
    lower, upper = _ba_bounds(scene)
    log_inv_guess = np.clip(log_inv_guess, lower[6 * n_views :] + 1e-6, upper[6 * n_views :] - 1e-6)
    return _pack_ba(params, centers, log_inv_guess)


def run_realistic_ba_monte_carlo(
    scene: RealisticBAScene,
    yaw_errors_deg: list[float] | None = None,
    trials_per_level: int = 6,
    tilt_error_deg: float = 24.0,
    translation_error_m: float = 0.28,
    depth_log_sigma: float = 0.55,
    seed: int = 79,
) -> list[dict[str, float | str | bool | int]]:
    if yaw_errors_deg is None:
        yaw_errors_deg = [0.0, 30.0, 60.0, 100.0, 140.0, 170.0]

    rng = np.random.default_rng(seed)
    methods = ["ba_uv_joint", "ba_polar_plain_joint", "ba_polar_cov_joint", "ba_polar_staged"]
    records: list[dict[str, float | str | bool | int]] = []

    for yaw_error in yaw_errors_deg:
        for trial in range(trials_per_level):
            initial_x = _initial_guess(
                scene,
                yaw_error,
                tilt_error_deg,
                translation_error_m,
                depth_log_sigma,
                rng,
            )
            initial_params, initial_centers, initial_log_inv = _unpack_ba(initial_x, _n_target_views(scene))
            initial_pose_error = _max_pose_error(initial_params, scene.true_params)
            initial_translation_error = _max_translation_error(initial_centers, scene.true_centers_world)
            initial_depths = _depths_from_log_inv(initial_log_inv)
            initial_depth_rmse = float(
                np.sqrt(np.mean(((initial_depths - scene.true_depths) / scene.true_depths) ** 2))
            )

            for method in methods:
                if method == "ba_polar_staged":
                    result = optimize_realistic_ba_staged(scene, initial_x)
                else:
                    result = optimize_realistic_ba_joint(method, scene, initial_x)

                converged = result.rotation_error_deg < 3.0 and result.inlier_depth_rel_rmse < 0.45
                records.append(
                    {
                        "method": result.method,
                        "yaw_init_error_deg": yaw_error,
                        "trial": trial,
                        "success": result.success,
                        "converged": converged,
                        "initial_rotation_error_deg": initial_pose_error,
                        "initial_translation_error_m": initial_translation_error,
                        "initial_depth_rel_rmse": initial_depth_rmse,
                        "stage_rotation_error_deg": result.stage_rotation_error_deg,
                        "rotation_error_deg": result.rotation_error_deg,
                        "translation_error_m": result.translation_error_m,
                        "tilt_error_deg": result.tilt_error_deg,
                        "yaw_error_deg": result.yaw_error_deg,
                        "depth_rel_rmse": result.depth_rel_rmse,
                        "depth_rel_median": result.depth_rel_median,
                        "inlier_depth_rel_rmse": result.inlier_depth_rel_rmse,
                        "inlier_depth_rel_median": result.inlier_depth_rel_median,
                        "cost": result.cost,
                        "nfev": result.nfev,
                    }
                )

    return records


def realistic_ba_records_to_array(records: list[dict[str, float | str | bool | int]]) -> np.ndarray:
    dtype = [
        ("method", "U32"),
        ("yaw_init_error_deg", float),
        ("trial", int),
        ("success", bool),
        ("converged", bool),
        ("initial_rotation_error_deg", float),
        ("initial_translation_error_m", float),
        ("initial_depth_rel_rmse", float),
        ("stage_rotation_error_deg", float),
        ("rotation_error_deg", float),
        ("translation_error_m", float),
        ("tilt_error_deg", float),
        ("yaw_error_deg", float),
        ("depth_rel_rmse", float),
        ("depth_rel_median", float),
        ("inlier_depth_rel_rmse", float),
        ("inlier_depth_rel_median", float),
        ("cost", float),
        ("nfev", float),
    ]
    return np.array([tuple(rec[name] for name, _ in dtype) for rec in records], dtype=dtype)


def write_realistic_ba_csv(records: list[dict[str, float | str | bool | int]], path: Path) -> None:
    write_csv(records, path)
