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
    polar_covariance_from_pixel,
    polar_to_bearing,
    rotation_angle_deg,
    rpy_matrix,
    wrap_angle,
)


@dataclass(frozen=True)
class FreeXYZBAScenarioConfig:
    name: str
    true_rpy_deg: tuple[tuple[float, float, float], ...]
    centers_world: tuple[tuple[float, float, float], ...]
    occluder_boxes_world: tuple[tuple[float, float, float, float, float, float], ...]
    n_points: int
    fixed_view_count: int
    min_track_length: int
    min_track_span: int
    depth_min: float
    depth_max: float
    theta_target_max_deg: float
    seed: int


@dataclass
class FreeXYZBAScene:
    name: str
    points_world: np.ndarray
    visibility_mask: np.ndarray
    track_lengths: np.ndarray
    gap_counts: np.ndarray
    scene_scale_m: float
    obs_view_indices: np.ndarray
    obs_point_indices: np.ndarray
    point_obs_indices: tuple[np.ndarray, ...]
    view_obs_offsets: np.ndarray
    observed_pixels: np.ndarray
    observed_polar: np.ndarray
    sqrt_info_polar: np.ndarray
    phi_gates: np.ndarray
    true_params: np.ndarray
    true_centers_world: np.ndarray
    occluder_boxes_world: np.ndarray
    fixed_view_count: int
    camera: CameraConfig


@dataclass
class FreeXYZBAResult:
    method: str
    params_all: np.ndarray
    centers_all: np.ndarray
    points_world: np.ndarray
    success: bool
    cost: float
    nfev: int
    rotation_error_deg: float
    translation_error_m: float
    structure_rmse_m: float
    structure_rel_rmse: float
    stage_rotation_error_deg: float
    stage_structure_rel_rmse: float
    message: str


def default_local_free_xyz_scenario() -> FreeXYZBAScenarioConfig:
    return FreeXYZBAScenarioConfig(
        name="local",
        true_rpy_deg=(
            (0.0, 0.0, 0.0),
            (0.8, -0.7, 1.2),
            (1.6, -1.0, 2.2),
            (2.4, -1.2, 3.2),
            (3.0, -1.0, 4.0),
        ),
        centers_world=(
            (0.0, 0.0, 0.0),
            (0.85, -0.10, 0.04),
            (1.80, -0.06, 0.10),
            (2.80, 0.02, 0.18),
            (3.85, 0.12, 0.24),
        ),
        occluder_boxes_world=(
            (1.4, 2.8, -2.8, 0.8, 8.0, 15.0),
            (-4.8, -2.2, 1.4, 4.8, 11.0, 18.0),
        ),
        n_points=120,
        fixed_view_count=2,
        min_track_length=3,
        min_track_span=2,
        depth_min=12.0,
        depth_max=42.0,
        theta_target_max_deg=70.0,
        seed=101,
    )


def default_global_free_xyz_scenario() -> FreeXYZBAScenarioConfig:
    return FreeXYZBAScenarioConfig(
        name="global",
        true_rpy_deg=(
            (0.0, 0.0, 0.0),
            (0.8, -0.6, 0.8),
            (1.4, -1.0, 1.6),
            (2.1, -1.4, 2.5),
            (2.8, -1.0, 3.5),
            (2.5, -0.2, 4.2),
            (1.8, 0.5, 4.8),
            (1.0, 0.9, 5.2),
        ),
        centers_world=(
            (0.0, 0.0, 0.0),
            (1.20, -0.12, 0.05),
            (2.60, -0.24, 0.12),
            (4.10, -0.20, 0.20),
            (5.80, -0.02, 0.32),
            (7.40, 0.28, 0.48),
            (8.70, 0.66, 0.62),
            (9.70, 1.10, 0.76),
        ),
        occluder_boxes_world=(
            (2.0, 4.2, -3.6, 1.0, 10.0, 18.0),
            (5.7, 7.9, 1.6, 5.8, 15.0, 24.0),
            (-8.5, -4.2, -6.5, -1.5, 13.5, 24.0),
        ),
        n_points=160,
        fixed_view_count=2,
        min_track_length=5,
        min_track_span=4,
        depth_min=18.0,
        depth_max=58.0,
        theta_target_max_deg=72.0,
        seed=131,
    )


def default_free_xyz_scenarios() -> tuple[FreeXYZBAScenarioConfig, FreeXYZBAScenarioConfig]:
    return default_local_free_xyz_scenario(), default_global_free_xyz_scenario()


def _visibility_and_pixel(
    point_world: np.ndarray,
    params: np.ndarray,
    center_world: np.ndarray,
    camera: CameraConfig,
    theta_target_max_rad: float,
) -> tuple[bool, np.ndarray]:
    q = rpy_matrix(params) @ (point_world - center_world)
    if q[2] <= 0.2:
        return False, np.zeros(2)
    theta = np.arctan2(np.linalg.norm(q[:2]), q[2])
    if theta > theta_target_max_rad:
        return False, np.zeros(2)
    pixel = equidistant_project(q.reshape(1, 3), camera.f, camera.cx, camera.cy)[0]
    if not (8.0 < pixel[0] < camera.width - 8.0 and 8.0 < pixel[1] < camera.height - 8.0):
        return False, np.zeros(2)
    return True, pixel


def _sample_candidate_point(
    rng: np.random.Generator,
    depth_min: float,
    depth_max: float,
    central: bool,
) -> np.ndarray:
    if central:
        theta = np.deg2rad(rng.uniform(0.3, 5.0))
    else:
        theta = np.deg2rad(rng.uniform(2.0, 62.0))
    phi = rng.uniform(-np.pi, np.pi)
    depth = rng.uniform(depth_min, depth_max)
    return polar_to_bearing(np.array(theta), np.array(phi)) * depth


def _segment_intersects_aabb(
    origin: np.ndarray,
    target: np.ndarray,
    box: np.ndarray,
) -> bool:
    direction = target - origin
    t_min = 0.0
    t_max = 1.0
    for axis in range(3):
        lower = float(box[2 * axis])
        upper = float(box[2 * axis + 1])
        delta = float(direction[axis])
        if abs(delta) < 1e-12:
            coord = float(origin[axis])
            if coord < lower or coord > upper:
                return False
            continue
        inv_delta = 1.0 / delta
        t1 = (lower - float(origin[axis])) * inv_delta
        t2 = (upper - float(origin[axis])) * inv_delta
        lo = min(t1, t2)
        hi = max(t1, t2)
        t_min = max(t_min, lo)
        t_max = min(t_max, hi)
        if t_min > t_max:
            return False
    return t_max > max(t_min, 1e-6) and t_min < 1.0 - 1e-6


def _apply_track_dropout_and_occlusion(
    point_world: np.ndarray,
    geometric_visible: np.ndarray,
    scenario: FreeXYZBAScenarioConfig,
    true_params: np.ndarray,
    true_centers_world: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    visible = geometric_visible.copy()
    n_views = visible.size
    max_end_view = int(np.flatnonzero(visible)[-1])
    min_end_view = max(scenario.min_track_span, scenario.fixed_view_count)

    q0 = rpy_matrix(true_params[0]) @ (point_world - true_centers_world[0])
    theta0 = np.arctan2(np.linalg.norm(q0[:2]), q0[2])
    theta_norm = np.clip(theta0 / np.deg2rad(scenario.theta_target_max_deg), 0.0, 1.0)
    depth_norm = np.clip(
        (q0[2] - scenario.depth_min) / max(scenario.depth_max - scenario.depth_min, 1e-12),
        0.0,
        1.0,
    )

    retention = np.clip(
        0.20 + 0.55 * depth_norm + 0.25 * (1.0 - theta_norm) + 0.10 * rng.normal(),
        0.0,
        1.0,
    )
    alpha = 1.0 + 3.0 * retention
    beta = 1.2 + 3.5 * (1.0 - retention)
    end_fraction = rng.beta(alpha, beta)
    end_view = min_end_view + int(
        np.floor(end_fraction * (max_end_view - min_end_view + 1 - 1e-9))
    )
    visible[end_view + 1 :] = False

    occluder_boxes = np.array(scenario.occluder_boxes_world, dtype=float).reshape(-1, 6)
    for view in range(scenario.fixed_view_count, end_view + 1):
        if not visible[view]:
            continue
        for box in occluder_boxes:
            if _segment_intersects_aabb(true_centers_world[view], point_world, box):
                visible[view] = False
                break
    return visible


def make_free_xyz_scene(
    scenario: FreeXYZBAScenarioConfig,
    camera: CameraConfig = CameraConfig(),
) -> FreeXYZBAScene:
    rng = np.random.default_rng(scenario.seed)
    true_params = np.deg2rad(np.array(scenario.true_rpy_deg, dtype=float))
    true_centers_world = np.array(scenario.centers_world, dtype=float)
    n_views = true_params.shape[0]
    theta_target_max_rad = np.deg2rad(scenario.theta_target_max_deg)

    points_world: list[np.ndarray] = []
    visibility_masks: list[np.ndarray] = []
    clean_pixels_by_view: list[list[np.ndarray]] = [[] for _ in range(n_views)]
    visible_points_by_view: list[list[int]] = [[] for _ in range(n_views)]
    occluder_boxes_world = np.array(scenario.occluder_boxes_world, dtype=float).reshape(-1, 6)

    attempts = 0
    max_attempts = scenario.n_points * 2200
    while len(points_world) < scenario.n_points and attempts < max_attempts:
        attempts += 1
        central = len(points_world) < max(12, scenario.n_points // 5)
        candidate = _sample_candidate_point(rng, scenario.depth_min, scenario.depth_max, central)

        visible = np.zeros(n_views, dtype=bool)
        pixels: list[np.ndarray] = []
        for view in range(n_views):
            is_visible, pixel = _visibility_and_pixel(
                candidate,
                true_params[view],
                true_centers_world[view],
                camera,
                theta_target_max_rad,
            )
            visible[view] = is_visible
            pixels.append(pixel)

        visible_views = np.flatnonzero(visible)
        if not np.all(visible[: scenario.fixed_view_count]):
            continue
        visible = _apply_track_dropout_and_occlusion(
            candidate,
            visible,
            scenario,
            true_params,
            true_centers_world,
            rng,
        )
        visible_views = np.flatnonzero(visible)
        if visible_views.size < scenario.min_track_length:
            continue
        if int(visible_views[-1] - visible_views[0]) < scenario.min_track_span:
            continue

        point_index = len(points_world)
        points_world.append(candidate)
        visibility_masks.append(visible)
        for view in visible_views:
            visible_points_by_view[view].append(point_index)
            clean_pixels_by_view[view].append(pixels[view])

    if len(points_world) < scenario.n_points:
        raise RuntimeError(f"Could not sample enough visible tracks for scenario '{scenario.name}'.")

    points_world_array = np.array(points_world)
    visibility_mask = np.array(visibility_masks)
    track_lengths = visibility_mask.sum(axis=1)
    gap_counts = np.zeros(points_world_array.shape[0], dtype=int)
    for point_idx, mask in enumerate(visibility_mask):
        visible_views = np.flatnonzero(mask)
        if visible_views.size == 0:
            continue
        span = mask[visible_views[0] : visible_views[-1] + 1]
        gap_counts[point_idx] = int(np.count_nonzero(~span))

    obs_view_indices: list[int] = []
    obs_point_indices: list[int] = []
    observed_pixels: list[np.ndarray] = []
    view_obs_offsets = [0]
    for view in range(n_views):
        clean_pixels = np.array(clean_pixels_by_view[view], dtype=float).reshape(-1, 2)
        point_indices = np.array(visible_points_by_view[view], dtype=int)
        noisy_pixels = clean_pixels + rng.normal(0.0, camera.sigma_px, size=clean_pixels.shape)
        obs_view_indices.extend([view] * point_indices.size)
        obs_point_indices.extend(point_indices.tolist())
        observed_pixels.extend(noisy_pixels)
        view_obs_offsets.append(len(obs_point_indices))

    obs_view_indices_array = np.array(obs_view_indices, dtype=int)
    obs_point_indices_array = np.array(obs_point_indices, dtype=int)
    observed_pixels_array = np.array(observed_pixels, dtype=float)
    observed_polar = bearing_to_polar(
        equidistant_unproject(observed_pixels_array, camera.f, camera.cx, camera.cy)
    )

    covariances = np.array(
        [
            polar_covariance_from_pixel(pixel, camera.sigma_px, camera.f, camera.cx, camera.cy)
            for pixel in observed_pixels_array
        ]
    )
    sqrt_info = np.empty_like(covariances)
    for i, cov in enumerate(covariances):
        sqrt_info[i] = np.linalg.inv(np.linalg.cholesky(cov))

    gate_start = np.sin(np.deg2rad(3.0))
    phi_gates = np.clip(np.sin(observed_polar[:, 0]) / gate_start, 0.0, 1.0)
    point_obs_indices = tuple(
        np.flatnonzero(obs_point_indices_array == point_idx) for point_idx in range(points_world_array.shape[0])
    )
    scene_scale_m = float(
        np.median(np.linalg.norm(points_world_array - true_centers_world[0], axis=1))
    )

    return FreeXYZBAScene(
        name=scenario.name,
        points_world=points_world_array,
        visibility_mask=visibility_mask,
        track_lengths=track_lengths,
        gap_counts=gap_counts,
        scene_scale_m=scene_scale_m,
        obs_view_indices=obs_view_indices_array,
        obs_point_indices=obs_point_indices_array,
        point_obs_indices=point_obs_indices,
        view_obs_offsets=np.array(view_obs_offsets, dtype=int),
        observed_pixels=observed_pixels_array,
        observed_polar=observed_polar,
        sqrt_info_polar=sqrt_info,
        phi_gates=phi_gates,
        true_params=true_params,
        true_centers_world=true_centers_world,
        occluder_boxes_world=occluder_boxes_world,
        fixed_view_count=scenario.fixed_view_count,
        camera=camera,
    )


def _n_views(scene: FreeXYZBAScene) -> int:
    return int(scene.true_params.shape[0])


def _n_opt_views(scene: FreeXYZBAScene) -> int:
    return _n_views(scene) - scene.fixed_view_count


def _pack_state(params_opt: np.ndarray, centers_opt: np.ndarray, points_world: np.ndarray) -> np.ndarray:
    return np.concatenate([params_opt.ravel(), centers_opt.ravel(), points_world.ravel()])


def _unpack_state(x: np.ndarray, scene: FreeXYZBAScene) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n_opt = _n_opt_views(scene)
    n_points = scene.points_world.shape[0]
    params_opt = x[: 3 * n_opt].reshape(n_opt, 3)
    centers_opt = x[3 * n_opt : 6 * n_opt].reshape(n_opt, 3)
    points_world = x[6 * n_opt :].reshape(n_points, 3)
    return params_opt, centers_opt, points_world


def _assemble_full_state(
    params_opt: np.ndarray,
    centers_opt: np.ndarray,
    points_world: np.ndarray,
    scene: FreeXYZBAScene,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    params_all = scene.true_params.copy()
    centers_all = scene.true_centers_world.copy()
    params_all[scene.fixed_view_count :] = params_opt
    centers_all[scene.fixed_view_count :] = centers_opt
    return params_all, centers_all, points_world


def _full_state_from_x(x: np.ndarray, scene: FreeXYZBAScene) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    params_opt, centers_opt, points_world = _unpack_state(x, scene)
    return _assemble_full_state(params_opt, centers_opt, points_world, scene)


def _triangulate_point_from_observations(
    scene: FreeXYZBAScene,
    point_obs_indices: np.ndarray,
    params_all: np.ndarray,
    centers_all: np.ndarray,
    allowed_views: np.ndarray | None = None,
) -> np.ndarray:
    a = np.zeros((3, 3))
    b = np.zeros(3)
    for obs_idx in point_obs_indices:
        view = scene.obs_view_indices[obs_idx]
        if allowed_views is not None and not bool(allowed_views[view]):
            continue
        pixel = scene.observed_pixels[obs_idx : obs_idx + 1]
        bearing_cam = equidistant_unproject(pixel, scene.camera.f, scene.camera.cx, scene.camera.cy)[0]
        direction_world = rpy_matrix(params_all[view]).T @ bearing_cam
        direction_world /= max(np.linalg.norm(direction_world), 1e-12)
        projector = np.eye(3) - np.outer(direction_world, direction_world)
        a += projector
        b += projector @ centers_all[view]
    if np.linalg.norm(a) < 1e-10:
        raise RuntimeError("Triangulation received no valid observations.")
    return np.linalg.solve(a + 1e-6 * np.eye(3), b)


def triangulate_points_from_observations(
    scene: FreeXYZBAScene,
    params_all: np.ndarray,
    centers_all: np.ndarray,
    allowed_views: np.ndarray | None = None,
) -> np.ndarray:
    points = np.zeros_like(scene.points_world)
    for point_idx, obs_indices in enumerate(scene.point_obs_indices):
        points[point_idx] = _triangulate_point_from_observations(
            scene,
            obs_indices,
            params_all,
            centers_all,
            allowed_views=allowed_views,
        )
    return points


def _predict_camera_points_for_view(
    points_world: np.ndarray,
    params: np.ndarray,
    center_world: np.ndarray,
) -> np.ndarray:
    return (rpy_matrix(params) @ (points_world - center_world).T).T


def free_xyz_uv_residual(x: np.ndarray, scene: FreeXYZBAScene) -> np.ndarray:
    params_all, centers_all, points_world = _full_state_from_x(x, scene)
    residuals: list[np.ndarray] = []
    for view in range(_n_views(scene)):
        start, end = scene.view_obs_offsets[view], scene.view_obs_offsets[view + 1]
        if start == end:
            continue
        point_indices = scene.obs_point_indices[start:end]
        q = _predict_camera_points_for_view(points_world[point_indices], params_all[view], centers_all[view])
        predicted = equidistant_project(q, scene.camera.f, scene.camera.cx, scene.camera.cy)
        residuals.append(((predicted - scene.observed_pixels[start:end]) / scene.camera.sigma_px).ravel())
    return np.concatenate(residuals)


def free_xyz_polar_residual(
    x: np.ndarray,
    scene: FreeXYZBAScene,
    covariance_aware: bool = True,
    gate_axis: bool = True,
    theta_only: bool = False,
    phi_only: bool = False,
) -> np.ndarray:
    params_all, centers_all, points_world = _full_state_from_x(x, scene)
    residuals: list[np.ndarray] = []
    nominal_theta_sigma = scene.camera.sigma_px / scene.camera.f

    for view in range(_n_views(scene)):
        start, end = scene.view_obs_offsets[view], scene.view_obs_offsets[view + 1]
        if start == end:
            continue
        point_indices = scene.obs_point_indices[start:end]
        q = _predict_camera_points_for_view(points_world[point_indices], params_all[view], centers_all[view])
        predicted = bearing_to_polar(q)
        dtheta = predicted[:, 0] - scene.observed_polar[start:end, 0]
        dphi = wrap_angle(predicted[:, 1] - scene.observed_polar[start:end, 1])

        if theta_only:
            if covariance_aware:
                sigma_theta = 1.0 / np.maximum(scene.sqrt_info_polar[start:end, 0, 0], 1e-12)
                residuals.append(dtheta / np.maximum(sigma_theta, 1e-12))
            else:
                residuals.append(dtheta / nominal_theta_sigma)
            continue

        if phi_only:
            if covariance_aware:
                raw = np.column_stack([np.zeros_like(dtheta), dphi])
                whitened = np.einsum("nij,nj->ni", scene.sqrt_info_polar[start:end], raw)
                if gate_axis:
                    whitened[:, 1] *= scene.phi_gates[start:end]
                residuals.append(whitened[:, 1])
            else:
                residuals.append(dphi * scene.phi_gates[start:end] / 0.03)
            continue

        raw = np.column_stack([dtheta, dphi])
        if covariance_aware:
            whitened = np.einsum("nij,nj->ni", scene.sqrt_info_polar[start:end], raw)
            if gate_axis:
                whitened[:, 1] *= scene.phi_gates[start:end]
            residuals.append(whitened.ravel())
        else:
            residuals.append(np.column_stack([dtheta / nominal_theta_sigma, dphi / 0.03]).ravel())

    return np.concatenate(residuals)


def free_xyz_ba_sparsity(scene: FreeXYZBAScene, residual_dim_per_obs: int = 2) -> lil_matrix:
    n_obs = scene.observed_pixels.shape[0]
    n_opt = _n_opt_views(scene)
    n_points = scene.points_world.shape[0]
    pattern = lil_matrix((residual_dim_per_obs * n_obs, 6 * n_opt + 3 * n_points), dtype=int)

    for obs_idx in range(n_obs):
        view = scene.obs_view_indices[obs_idx]
        point = scene.obs_point_indices[obs_idx]
        rows = range(residual_dim_per_obs * obs_idx, residual_dim_per_obs * (obs_idx + 1))
        if view >= scene.fixed_view_count:
            opt_view = view - scene.fixed_view_count
            pose_offset = 3 * opt_view
            center_offset = 3 * n_opt + 3 * opt_view
            for row in rows:
                pattern[row, pose_offset : pose_offset + 3] = 1
                pattern[row, center_offset : center_offset + 3] = 1
                point_offset = 6 * n_opt + 3 * point
                pattern[row, point_offset : point_offset + 3] = 1
        else:
            point_offset = 6 * n_opt + 3 * point
            for row in rows:
                pattern[row, point_offset : point_offset + 3] = 1
    return pattern


def _max_rotation_error_deg(params_all: np.ndarray, scene: FreeXYZBAScene) -> float:
    errors = [
        rotation_angle_deg(rpy_matrix(params_all[view]), rpy_matrix(scene.true_params[view]))
        for view in range(scene.fixed_view_count, _n_views(scene))
    ]
    return float(max(errors) if errors else 0.0)


def _max_translation_error_m(centers_all: np.ndarray, scene: FreeXYZBAScene) -> float:
    errors = np.linalg.norm(
        centers_all[scene.fixed_view_count :] - scene.true_centers_world[scene.fixed_view_count :],
        axis=1,
    )
    return float(max(errors) if errors.size else 0.0)


def _structure_rmse_m(points_world: np.ndarray, scene: FreeXYZBAScene) -> float:
    return float(np.sqrt(np.mean(np.sum((points_world - scene.points_world) ** 2, axis=1))))


def _structure_rel_rmse(points_world: np.ndarray, scene: FreeXYZBAScene) -> float:
    return _structure_rmse_m(points_world, scene) / max(scene.scene_scale_m, 1e-12)


def summarize_free_xyz_result(
    method: str,
    x: np.ndarray,
    scene: FreeXYZBAScene,
    cost: float,
    success: bool,
    nfev: int,
    message: str,
    stage_rotation_error_deg: float = np.nan,
    stage_structure_rel_rmse: float = np.nan,
) -> FreeXYZBAResult:
    params_all, centers_all, points_world = _full_state_from_x(x, scene)
    return FreeXYZBAResult(
        method=method,
        params_all=params_all,
        centers_all=centers_all,
        points_world=points_world,
        success=bool(success),
        cost=float(cost),
        nfev=int(nfev),
        rotation_error_deg=_max_rotation_error_deg(params_all, scene),
        translation_error_m=_max_translation_error_m(centers_all, scene),
        structure_rmse_m=_structure_rmse_m(points_world, scene),
        structure_rel_rmse=_structure_rel_rmse(points_world, scene),
        stage_rotation_error_deg=float(stage_rotation_error_deg),
        stage_structure_rel_rmse=float(stage_structure_rel_rmse),
        message=str(message),
    )


def optimize_free_xyz_joint(
    method: str,
    scene: FreeXYZBAScene,
    initial_x: np.ndarray,
    max_nfev: int = 150,
) -> FreeXYZBAResult:
    if method == "xyz_uv_joint":
        residual_fn = lambda x: free_xyz_uv_residual(x, scene)
    elif method == "xyz_polar_cov_joint":
        residual_fn = lambda x: free_xyz_polar_residual(x, scene, covariance_aware=True, gate_axis=True)
    else:
        raise ValueError(f"Unknown free-XYZ BA method: {method}")

    result = least_squares(
        residual_fn,
        initial_x,
        jac_sparsity=free_xyz_ba_sparsity(scene),
        method="trf",
        loss="huber",
        f_scale=2.5,
        x_scale="jac",
        max_nfev=max_nfev,
    )
    return summarize_free_xyz_result(
        method,
        result.x,
        scene,
        result.cost,
        result.success,
        result.nfev,
        result.message,
    )


def optimize_free_xyz_staged(
    scene: FreeXYZBAScene,
    initial_x: np.ndarray,
    max_nfev_per_stage: int = 110,
    staged_cycles: int = 1,
    final_use_sparsity: bool = True,
) -> FreeXYZBAResult:
    params_opt0, centers_opt0, points0 = _unpack_state(initial_x, scene)
    n_opt = _n_opt_views(scene)
    roll_pitch = params_opt0[:, :2].copy()
    yaw = params_opt0[:, 2].copy()
    stage_success = True
    stage_nfev = 0
    stage_messages: list[str] = []

    for cycle_idx in range(staged_cycles):
        def theta_stage(roll_pitch_flat: np.ndarray) -> np.ndarray:
            params_opt = np.column_stack([roll_pitch_flat.reshape(n_opt, 2), yaw])
            x = _pack_state(params_opt, centers_opt0, points0)
            return free_xyz_polar_residual(
                x,
                scene,
                covariance_aware=True,
                gate_axis=True,
                theta_only=True,
            )

        stage1 = least_squares(
            theta_stage,
            roll_pitch.ravel(),
            method="trf",
            loss="huber",
            f_scale=2.5,
            max_nfev=max_nfev_per_stage,
        )
        roll_pitch = stage1.x.reshape(n_opt, 2)

        def phi_stage(yaw_vec: np.ndarray) -> np.ndarray:
            params_opt = np.column_stack([roll_pitch, yaw_vec])
            x = _pack_state(params_opt, centers_opt0, points0)
            return free_xyz_polar_residual(
                x,
                scene,
                covariance_aware=True,
                gate_axis=True,
                phi_only=True,
            )

        stage2 = least_squares(
            phi_stage,
            yaw,
            method="trf",
            loss="huber",
            f_scale=2.5,
            max_nfev=max_nfev_per_stage,
        )
        yaw = stage2.x
        stage_success = bool(stage_success and stage1.success and stage2.success)
        stage_nfev += int(stage1.nfev + stage2.nfev)
        stage_messages.append(
            f"cycle{cycle_idx + 1}.theta={stage1.message}; cycle{cycle_idx + 1}.phi={stage2.message}"
        )

    staged_params_opt = np.column_stack([roll_pitch, yaw])
    staged_params_all, _, _ = _assemble_full_state(staged_params_opt, centers_opt0, points0, scene)
    staged_x = _pack_state(staged_params_opt, centers_opt0, points0)
    staged_pose_error = _max_rotation_error_deg(staged_params_all, scene)
    staged_structure_rel_rmse = _structure_rel_rmse(points0, scene)

    final_kwargs = {}
    if final_use_sparsity:
        final_kwargs["jac_sparsity"] = free_xyz_ba_sparsity(scene)
    final = least_squares(
        lambda x: free_xyz_polar_residual(x, scene, covariance_aware=True, gate_axis=True),
        staged_x,
        method="trf",
        loss="huber",
        f_scale=2.5,
        x_scale="jac",
        max_nfev=max_nfev_per_stage,
        **final_kwargs,
    )

    success = bool(stage_success and final.success)
    message = "; ".join(stage_messages + [f"final={final.message}"])
    return summarize_free_xyz_result(
        "xyz_polar_staged",
        final.x,
        scene,
        final.cost,
        success,
        stage_nfev + final.nfev,
        message,
        stage_rotation_error_deg=staged_pose_error,
        stage_structure_rel_rmse=staged_structure_rel_rmse,
    )


def initial_free_xyz_guess(
    scene: FreeXYZBAScene,
    yaw_error_deg: float,
    tilt_error_deg: float,
    translation_error_m: float,
    rng: np.random.Generator,
) -> np.ndarray:
    params_all = scene.true_params.copy()
    centers_all = scene.true_centers_world.copy()
    yaw_sign = rng.choice([-1.0, 1.0])

    for view in range(scene.fixed_view_count, _n_views(scene)):
        tilt_direction = rng.normal(size=2)
        tilt_direction /= max(np.linalg.norm(tilt_direction), 1e-12)
        tilt_error = np.deg2rad(tilt_error_deg) * tilt_direction
        params_all[view, :2] += tilt_error
        params_all[view, 2] += yaw_sign * np.deg2rad(yaw_error_deg)

        center_dir = rng.normal(size=3)
        center_dir /= max(np.linalg.norm(center_dir), 1e-12)
        centers_all[view] += translation_error_m * center_dir

    fixed_views = np.zeros(_n_views(scene), dtype=bool)
    fixed_views[: scene.fixed_view_count] = True
    points_init = triangulate_points_from_observations(
        scene,
        scene.true_params,
        scene.true_centers_world,
        allowed_views=fixed_views,
    )
    params_opt = params_all[scene.fixed_view_count :]
    centers_opt = centers_all[scene.fixed_view_count :]
    return _pack_state(params_opt, centers_opt, points_init)


def run_free_xyz_monte_carlo(
    scene: FreeXYZBAScene,
    yaw_errors_deg: list[float] | None = None,
    trials_per_level: int = 4,
    tilt_error_deg: float = 18.0,
    translation_error_m: float = 0.24,
    seed: int = 181,
    staged_cycles: int = 1,
    staged_final_use_sparsity: bool = True,
) -> list[dict[str, float | str | bool | int]]:
    if yaw_errors_deg is None:
        yaw_errors_deg = [0.0, 30.0, 60.0, 100.0, 140.0]

    rng = np.random.default_rng(seed)
    methods = ["xyz_uv_joint", "xyz_polar_cov_joint", "xyz_polar_staged"]
    records: list[dict[str, float | str | bool | int]] = []
    structure_success_threshold = 0.30

    for yaw_error in yaw_errors_deg:
        for trial in range(trials_per_level):
            initial_x = initial_free_xyz_guess(
                scene,
                yaw_error_deg=yaw_error,
                tilt_error_deg=tilt_error_deg,
                translation_error_m=translation_error_m,
                rng=rng,
            )
            init_params_all, init_centers_all, init_points_world = _full_state_from_x(initial_x, scene)
            initial_rotation_error = _max_rotation_error_deg(init_params_all, scene)
            initial_translation_error = _max_translation_error_m(init_centers_all, scene)
            initial_structure_rel_rmse = _structure_rel_rmse(init_points_world, scene)

            for method in methods:
                if method == "xyz_polar_staged":
                    result = optimize_free_xyz_staged(
                        scene,
                        initial_x,
                        staged_cycles=staged_cycles,
                        final_use_sparsity=staged_final_use_sparsity,
                    )
                else:
                    result = optimize_free_xyz_joint(method, scene, initial_x)

                converged = result.rotation_error_deg < 3.0 and result.structure_rel_rmse < structure_success_threshold
                records.append(
                    {
                        "regime": scene.name,
                        "method": result.method,
                        "yaw_init_error_deg": yaw_error,
                        "trial": trial,
                        "success": result.success,
                        "converged": converged,
                        "initial_rotation_error_deg": initial_rotation_error,
                        "initial_translation_error_m": initial_translation_error,
                        "initial_structure_rel_rmse": initial_structure_rel_rmse,
                        "stage_rotation_error_deg": result.stage_rotation_error_deg,
                        "stage_structure_rel_rmse": result.stage_structure_rel_rmse,
                        "rotation_error_deg": result.rotation_error_deg,
                        "translation_error_m": result.translation_error_m,
                        "structure_rmse_m": result.structure_rmse_m,
                        "structure_rel_rmse": result.structure_rel_rmse,
                        "cost": result.cost,
                        "nfev": result.nfev,
                    }
                )

    return records


def free_xyz_records_to_array(records: list[dict[str, float | str | bool | int]]) -> np.ndarray:
    dtype = [
        ("regime", "U16"),
        ("method", "U32"),
        ("yaw_init_error_deg", float),
        ("trial", int),
        ("success", bool),
        ("converged", bool),
        ("initial_rotation_error_deg", float),
        ("initial_translation_error_m", float),
        ("initial_structure_rel_rmse", float),
        ("stage_rotation_error_deg", float),
        ("stage_structure_rel_rmse", float),
        ("rotation_error_deg", float),
        ("translation_error_m", float),
        ("structure_rmse_m", float),
        ("structure_rel_rmse", float),
        ("cost", float),
        ("nfev", float),
    ]
    return np.array([tuple(rec[name] for name, _ in dtype) for rec in records], dtype=dtype)


def write_free_xyz_csv(records: list[dict[str, float | str | bool | int]], path: Path) -> None:
    write_csv(records, path)
