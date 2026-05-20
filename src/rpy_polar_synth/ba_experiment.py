from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix

from .experiment import CameraConfig, write_csv
from .geometry import (
    camera_polar,
    equidistant_project,
    pixel_to_polar,
    polar_covariance_from_pixel,
    polar_to_bearing,
    rotation_angle_deg,
    rpy_matrix,
    wrap_angle,
)


@dataclass(frozen=True)
class BAScenarioConfig:
    n_points: int = 72
    theta1_min_deg: float = 0.4
    theta1_max_deg: float = 58.0
    theta2_max_deg: float = 62.0
    depth_min: float = 4.0
    depth_max: float = 13.0
    true_rpy_deg: tuple[float, float, float] = (9.0, -14.0, 31.0)
    center2_world: tuple[float, float, float] = (0.85, -0.18, 0.16)
    outlier_fraction: float = 0.06
    seed: int = 41


@dataclass
class BAScene:
    points_world: np.ndarray
    anchor_bearings: np.ndarray
    true_depths: np.ndarray
    center2_world: np.ndarray
    observed_pixels2: np.ndarray
    observed_polar2: np.ndarray
    sqrt_info_polar2: np.ndarray
    phi_gates2: np.ndarray
    inlier_mask: np.ndarray
    true_params: np.ndarray
    camera: CameraConfig


@dataclass
class BAResult:
    method: str
    params: np.ndarray
    log_inv_depths: np.ndarray
    success: bool
    cost: float
    nfev: int
    rotation_error_deg: float
    tilt_error_deg: float
    yaw_error_deg: float
    depth_rel_rmse: float
    depth_rel_median: float
    inlier_depth_rel_rmse: float
    inlier_depth_rel_median: float
    stage_rotation_error_deg: float
    message: str


def make_ba_scene(
    scenario: BAScenarioConfig = BAScenarioConfig(),
    camera: CameraConfig = CameraConfig(),
) -> BAScene:
    rng = np.random.default_rng(scenario.seed)
    true_params = np.deg2rad(np.array(scenario.true_rpy_deg, dtype=float))
    true_r = rpy_matrix(true_params)
    center2 = np.array(scenario.center2_world, dtype=float)

    bearings: list[np.ndarray] = []
    depths: list[float] = []
    pixels2: list[np.ndarray] = []
    attempts = 0
    while len(bearings) < scenario.n_points and attempts < scenario.n_points * 200:
        attempts += 1
        if len(bearings) < max(6, scenario.n_points // 5):
            theta = np.deg2rad(rng.uniform(scenario.theta1_min_deg, 3.0))
        else:
            theta = np.deg2rad(rng.uniform(scenario.theta1_min_deg, scenario.theta1_max_deg))
        phi = rng.uniform(-np.pi, np.pi)
        depth = rng.uniform(scenario.depth_min, scenario.depth_max)
        bearing = polar_to_bearing(np.array(theta), np.array(phi))
        point_world = depth * bearing
        q2 = true_r @ (point_world - center2)
        if q2[2] <= 0.15:
            continue
        theta2 = np.arctan2(np.linalg.norm(q2[:2]), q2[2])
        if theta2 > np.deg2rad(scenario.theta2_max_deg):
            continue
        pixel = equidistant_project(q2.reshape(1, 3), camera.f, camera.cx, camera.cy)[0]
        if not (8.0 < pixel[0] < camera.width - 8.0 and 8.0 < pixel[1] < camera.height - 8.0):
            continue
        bearings.append(bearing)
        depths.append(float(depth))
        pixels2.append(pixel)

    if len(bearings) < scenario.n_points:
        raise RuntimeError("Could not sample enough points visible in both views.")

    anchor_bearings = np.array(bearings)
    true_depths = np.array(depths)
    clean_pixels2 = np.array(pixels2)
    observed_pixels2 = clean_pixels2 + rng.normal(0.0, camera.sigma_px, size=clean_pixels2.shape)

    inlier_mask = np.ones(scenario.n_points, dtype=bool)
    n_outliers = int(round(scenario.outlier_fraction * scenario.n_points))
    if n_outliers > 0:
        outlier_indices = rng.choice(scenario.n_points, size=n_outliers, replace=False)
        replacement = observed_pixels2.copy()
        rng.shuffle(replacement, axis=0)
        observed_pixels2[outlier_indices] = replacement[outlier_indices]
        inlier_mask[outlier_indices] = False

    observed_polar2 = pixel_to_polar(observed_pixels2, camera.f, camera.cx, camera.cy)
    covariances = np.array(
        [
            polar_covariance_from_pixel(pixel, camera.sigma_px, camera.f, camera.cx, camera.cy)
            for pixel in observed_pixels2
        ]
    )
    sqrt_info = np.empty_like(covariances)
    for i, cov in enumerate(covariances):
        sqrt_info[i] = np.linalg.inv(np.linalg.cholesky(cov))

    gate_start = np.sin(np.deg2rad(3.0))
    phi_gates = np.clip(np.sin(observed_polar2[:, 0]) / gate_start, 0.0, 1.0)

    return BAScene(
        points_world=anchor_bearings * true_depths[:, None],
        anchor_bearings=anchor_bearings,
        true_depths=true_depths,
        center2_world=center2,
        observed_pixels2=observed_pixels2,
        observed_polar2=observed_polar2,
        sqrt_info_polar2=sqrt_info,
        phi_gates2=phi_gates,
        inlier_mask=inlier_mask,
        true_params=true_params,
        camera=camera,
    )


def pack_ba(params: np.ndarray, log_inv_depths: np.ndarray) -> np.ndarray:
    return np.concatenate([params, log_inv_depths])


def unpack_ba(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return x[:3], x[3:]


def depths_from_log_inv(log_inv_depths: np.ndarray) -> np.ndarray:
    return np.exp(-log_inv_depths)


def points_from_depths(scene: BAScene, log_inv_depths: np.ndarray) -> np.ndarray:
    depths = depths_from_log_inv(log_inv_depths)
    return scene.anchor_bearings * depths[:, None]


def predict_camera2_points(params: np.ndarray, log_inv_depths: np.ndarray, scene: BAScene) -> np.ndarray:
    points_world = points_from_depths(scene, log_inv_depths)
    vectors = points_world - scene.center2_world
    return (rpy_matrix(params) @ vectors.T).T


def ba_uv_residual(x: np.ndarray, scene: BAScene) -> np.ndarray:
    params, log_inv_depths = unpack_ba(x)
    q2 = predict_camera2_points(params, log_inv_depths, scene)
    predicted = equidistant_project(q2, scene.camera.f, scene.camera.cx, scene.camera.cy)
    return ((predicted - scene.observed_pixels2) / scene.camera.sigma_px).ravel()


def ba_polar_residual(
    x: np.ndarray,
    scene: BAScene,
    covariance_aware: bool = True,
    gate_axis: bool = True,
    theta_only: bool = False,
    phi_only: bool = False,
) -> np.ndarray:
    params, log_inv_depths = unpack_ba(x)
    q2 = predict_camera2_points(params, log_inv_depths, scene)
    predicted = camera_polar(q2, np.zeros(3))
    dtheta = predicted[:, 0] - scene.observed_polar2[:, 0]
    dphi = wrap_angle(predicted[:, 1] - scene.observed_polar2[:, 1])

    if theta_only:
        if covariance_aware:
            sigma_theta = 1.0 / np.maximum(scene.sqrt_info_polar2[:, 0, 0], 1e-12)
            return dtheta / np.maximum(sigma_theta, 1e-12)
        return dtheta / (scene.camera.sigma_px / scene.camera.f)

    if phi_only:
        if covariance_aware:
            raw = np.column_stack([np.zeros_like(dtheta), dphi])
            whitened = np.einsum("nij,nj->ni", scene.sqrt_info_polar2, raw)
            if gate_axis:
                whitened[:, 1] *= scene.phi_gates2
            return whitened[:, 1]
        return dphi * scene.phi_gates2 / 0.03

    raw = np.column_stack([dtheta, dphi])
    if covariance_aware:
        whitened = np.einsum("nij,nj->ni", scene.sqrt_info_polar2, raw)
        if gate_axis:
            whitened[:, 1] *= scene.phi_gates2
        return whitened.ravel()

    nominal_theta_sigma = scene.camera.sigma_px / scene.camera.f
    return np.column_stack([dtheta / nominal_theta_sigma, dphi / 0.03]).ravel()


def full_ba_sparsity(n_points: int, residual_dim_per_point: int = 2) -> lil_matrix:
    pattern = lil_matrix((residual_dim_per_point * n_points, 3 + n_points), dtype=int)
    for i in range(n_points):
        rows = range(residual_dim_per_point * i, residual_dim_per_point * (i + 1))
        for row in rows:
            pattern[row, 0:3] = 1
            pattern[row, 3 + i] = 1
    return pattern


def theta_stage_sparsity(n_points: int) -> lil_matrix:
    pattern = lil_matrix((n_points, 2 + n_points), dtype=int)
    for i in range(n_points):
        pattern[i, 0:2] = 1
        pattern[i, 2 + i] = 1
    return pattern


def ba_bounds(scene: BAScene) -> tuple[np.ndarray, np.ndarray]:
    n = scene.true_depths.size
    lower = np.concatenate([np.deg2rad([-180.0, -89.0, -360.0]), np.full(n, np.log(1.0 / 60.0))])
    upper = np.concatenate([np.deg2rad([180.0, 89.0, 360.0]), np.full(n, np.log(1.0 / 1.0))])
    return lower, upper


def stage1_bounds(scene: BAScene) -> tuple[np.ndarray, np.ndarray]:
    n = scene.true_depths.size
    lower = np.concatenate([np.deg2rad([-180.0, -89.0]), np.full(n, np.log(1.0 / 60.0))])
    upper = np.concatenate([np.deg2rad([180.0, 89.0]), np.full(n, np.log(1.0 / 1.0))])
    return lower, upper


def summarize_ba_result(
    method: str,
    x: np.ndarray,
    scene: BAScene,
    cost: float,
    success: bool,
    nfev: int,
    message: str,
    stage_rotation_error_deg: float = np.nan,
) -> BAResult:
    params, log_inv_depths = unpack_ba(x)
    delta = wrap_angle(params - scene.true_params)
    depth_est = depths_from_log_inv(log_inv_depths)
    rel_depth = (depth_est - scene.true_depths) / scene.true_depths
    inlier_rel_depth = rel_depth[scene.inlier_mask]
    return BAResult(
        method=method,
        params=params,
        log_inv_depths=log_inv_depths,
        success=bool(success),
        cost=float(cost),
        nfev=int(nfev),
        rotation_error_deg=rotation_angle_deg(rpy_matrix(params), rpy_matrix(scene.true_params)),
        tilt_error_deg=float(np.rad2deg(np.linalg.norm(delta[:2]))),
        yaw_error_deg=float(abs(np.rad2deg(delta[2]))),
        depth_rel_rmse=float(np.sqrt(np.mean(rel_depth**2))),
        depth_rel_median=float(np.median(np.abs(rel_depth))),
        inlier_depth_rel_rmse=float(np.sqrt(np.mean(inlier_rel_depth**2))),
        inlier_depth_rel_median=float(np.median(np.abs(inlier_rel_depth))),
        stage_rotation_error_deg=float(stage_rotation_error_deg),
        message=str(message),
    )


def optimize_ba_joint(
    method: str,
    scene: BAScene,
    initial_x: np.ndarray,
    max_nfev: int = 90,
) -> BAResult:
    if method == "ba_uv_joint":
        residual_fn = lambda x: ba_uv_residual(x, scene)
        sparsity = full_ba_sparsity(scene.true_depths.size)
    elif method == "ba_polar_plain_joint":
        residual_fn = lambda x: ba_polar_residual(x, scene, covariance_aware=False, gate_axis=False)
        sparsity = full_ba_sparsity(scene.true_depths.size)
    elif method == "ba_polar_cov_joint":
        residual_fn = lambda x: ba_polar_residual(x, scene, covariance_aware=True, gate_axis=True)
        sparsity = full_ba_sparsity(scene.true_depths.size)
    else:
        raise ValueError(f"Unknown BA method: {method}")

    result = least_squares(
        residual_fn,
        initial_x,
        bounds=ba_bounds(scene),
        jac_sparsity=sparsity,
        method="trf",
        loss="huber",
        f_scale=2.5,
        x_scale="jac",
        max_nfev=max_nfev,
    )
    return summarize_ba_result(method, result.x, scene, result.cost, result.success, result.nfev, result.message)


def optimize_ba_staged(
    scene: BAScene,
    initial_x: np.ndarray,
    max_nfev_per_stage: int = 70,
) -> BAResult:
    params0, log_inv0 = unpack_ba(initial_x)

    # For initialization we intentionally keep depths fixed. If depths are free
    # in the theta-only stage, they can absorb tilt errors and destroy the
    # geometric decoupling this experiment is meant to test.
    def theta_stage(roll_pitch: np.ndarray) -> np.ndarray:
        params = np.array([roll_pitch[0], roll_pitch[1], params0[2]])
        x = pack_ba(params, log_inv0)
        return ba_polar_residual(x, scene, covariance_aware=True, gate_axis=True, theta_only=True)

    stage1 = least_squares(
        theta_stage,
        params0[:2],
        bounds=(np.deg2rad([-180.0, -89.0]), np.deg2rad([180.0, 89.0])),
        method="trf",
        loss="huber",
        f_scale=2.5,
        max_nfev=max_nfev_per_stage,
    )

    roll_pitch1 = stage1.x[:2]

    def phi_stage(yaw: np.ndarray) -> np.ndarray:
        params = np.array([roll_pitch1[0], roll_pitch1[1], yaw[0]])
        return ba_polar_residual(
            pack_ba(params, log_inv0),
            scene,
            covariance_aware=True,
            gate_axis=True,
            phi_only=True,
        )

    stage2 = least_squares(
        phi_stage,
        np.array([params0[2]]),
        bounds=(np.array([np.deg2rad(-360.0)]), np.array([np.deg2rad(360.0)])),
        method="trf",
        loss="huber",
        f_scale=2.5,
        max_nfev=max_nfev_per_stage,
    )

    staged_params = np.array([roll_pitch1[0], roll_pitch1[1], stage2.x[0]])
    staged_x = pack_ba(staged_params, log_inv0)
    staged_pose_error = rotation_angle_deg(rpy_matrix(staged_params), rpy_matrix(scene.true_params))

    final = least_squares(
        lambda x: ba_polar_residual(x, scene, covariance_aware=True, gate_axis=True),
        staged_x,
        bounds=ba_bounds(scene),
        jac_sparsity=full_ba_sparsity(scene.true_depths.size),
        method="trf",
        loss="huber",
        f_scale=2.5,
        x_scale="jac",
        max_nfev=max_nfev_per_stage,
    )

    success = bool(stage1.success and stage2.success and final.success)
    message = f"stage1={stage1.message}; stage2={stage2.message}; final={final.message}"
    return summarize_ba_result(
        "ba_polar_staged",
        final.x,
        scene,
        final.cost,
        success,
        stage1.nfev + stage2.nfev + final.nfev,
        message,
        stage_rotation_error_deg=staged_pose_error,
    )


def initial_ba_guess(
    scene: BAScene,
    yaw_error_deg: float,
    tilt_error_deg: float,
    depth_log_sigma: float,
    rng: np.random.Generator,
) -> np.ndarray:
    tilt_direction = rng.normal(size=2)
    tilt_direction /= max(np.linalg.norm(tilt_direction), 1e-12)
    tilt_error = np.deg2rad(tilt_error_deg) * tilt_direction
    yaw_sign = rng.choice([-1.0, 1.0])
    params = scene.true_params + np.array(
        [tilt_error[0], tilt_error[1], yaw_sign * np.deg2rad(yaw_error_deg)]
    )

    log_inv_true = np.log(1.0 / scene.true_depths)
    log_inv_guess = log_inv_true + rng.normal(0.0, depth_log_sigma, size=scene.true_depths.size)
    lower, upper = ba_bounds(scene)
    log_inv_guess = np.clip(log_inv_guess, lower[3:] + 1e-6, upper[3:] - 1e-6)
    return pack_ba(params, log_inv_guess)


def run_ba_monte_carlo(
    scene: BAScene,
    yaw_errors_deg: list[float] | None = None,
    trials_per_level: int = 6,
    tilt_error_deg: float = 24.0,
    depth_log_sigma: float = 0.65,
    seed: int = 73,
) -> list[dict[str, float | str | bool | int]]:
    if yaw_errors_deg is None:
        yaw_errors_deg = [0.0, 30.0, 60.0, 100.0, 140.0, 170.0]

    rng = np.random.default_rng(seed)
    methods = ["ba_uv_joint", "ba_polar_plain_joint", "ba_polar_cov_joint", "ba_polar_staged"]
    records: list[dict[str, float | str | bool | int]] = []

    for yaw_error in yaw_errors_deg:
        for trial in range(trials_per_level):
            initial_x = initial_ba_guess(scene, yaw_error, tilt_error_deg, depth_log_sigma, rng)
            initial_params, initial_log_inv = unpack_ba(initial_x)
            initial_pose_error = rotation_angle_deg(rpy_matrix(initial_params), rpy_matrix(scene.true_params))
            initial_depths = depths_from_log_inv(initial_log_inv)
            initial_depth_rmse = float(
                np.sqrt(np.mean(((initial_depths - scene.true_depths) / scene.true_depths) ** 2))
            )

            for method in methods:
                if method == "ba_polar_staged":
                    result = optimize_ba_staged(scene, initial_x)
                else:
                    result = optimize_ba_joint(method, scene, initial_x)

                converged = result.rotation_error_deg < 3.0 and result.inlier_depth_rel_rmse < 0.45
                records.append(
                    {
                        "method": result.method,
                        "yaw_init_error_deg": yaw_error,
                        "trial": trial,
                        "success": result.success,
                        "converged": converged,
                        "initial_rotation_error_deg": initial_pose_error,
                        "initial_depth_rel_rmse": initial_depth_rmse,
                        "stage_rotation_error_deg": result.stage_rotation_error_deg,
                        "rotation_error_deg": result.rotation_error_deg,
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


def ba_records_to_array(records: list[dict[str, float | str | bool | int]]) -> np.ndarray:
    dtype = [
        ("method", "U32"),
        ("yaw_init_error_deg", float),
        ("trial", int),
        ("success", bool),
        ("converged", bool),
        ("initial_rotation_error_deg", float),
        ("initial_depth_rel_rmse", float),
        ("stage_rotation_error_deg", float),
        ("rotation_error_deg", float),
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


def write_ba_csv(records: list[dict[str, float | str | bool | int]], path: Path) -> None:
    write_csv(records, path)
