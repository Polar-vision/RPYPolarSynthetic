from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .experiment import CameraConfig
from .free_xyz_ba_experiment import (
    FreeXYZBAScene,
    FreeXYZBAScenarioConfig,
    _apply_track_dropout_and_occlusion,
    _visibility_and_pixel,
)
from .geometry import bearing_to_polar, equidistant_unproject, polar_covariance_from_pixel


@dataclass(frozen=True)
class AirborneStripScenario:
    name: str
    free_xyz_config: FreeXYZBAScenarioConfig
    strip_ids: tuple[int, ...]
    strip_names: tuple[str, ...]
    point_boxes_world: tuple[tuple[float, float, float, float, float, float], ...]


def _rpy_from_optical_axis_and_yaw(axis_world: np.ndarray, yaw_deg: float) -> np.ndarray:
    axis_world = np.asarray(axis_world, dtype=float)
    axis_world /= max(np.linalg.norm(axis_world), 1e-12)
    pitch = -np.arcsin(np.clip(axis_world[0], -1.0, 1.0))
    roll = np.arctan2(axis_world[1], axis_world[2])
    yaw = np.deg2rad(yaw_deg)
    return np.array([roll, pitch, yaw], dtype=float)


def default_airborne_strip_scenario() -> AirborneStripScenario:
    # Internally, this project assumes points in front of the camera have
    # positive camera z. For an oblique airborne block, we therefore model the
    # world with "down" as positive z so the cameras can still look toward
    # positive z while remaining above the scene in the visualization.
    y_positions = (-27.0, -9.0, 9.0, 27.0)
    strip_names = ("west strip", "center strip", "east strip")

    strip_ids: list[int] = []
    centers_world: list[np.ndarray] = []
    params_rpy: list[np.ndarray] = []

    # Two central-strip anchors first so every landmark can be triangulated from
    # a realistic high-overlap reference pair before the rest of the block is optimized.
    for y, yaw_deg in ((-9.0, 4.0), (9.0, 8.0)):
        center = np.array([0.0, y, 0.35], dtype=float)
        target = np.array([4.5, 0.20 * y, 24.5], dtype=float)
        strip_ids.append(1)
        centers_world.append(center)
        params_rpy.append(_rpy_from_optical_axis_and_yaw(target - center, yaw_deg))

    strip_specs = (
        (0, -18.0, -12.0, -10.5),
        (1, 0.0, 4.5, 2.0),
        (2, 18.0, 12.0, 11.5),
    )
    for strip_id, x_world, target_x_world, yaw_base_deg in strip_specs:
        for view_idx, y_world in enumerate(y_positions):
            if strip_id == 1 and y_world in (-9.0, 9.0):
                continue
            center = np.array(
                [
                    x_world,
                    y_world,
                    0.35 + 0.25 * np.sin(0.16 * y_world + 0.45 * strip_id),
                ],
                dtype=float,
            )
            target = np.array(
                [
                    target_x_world,
                    0.26 * y_world,
                    24.5 + 1.2 * np.cos(0.11 * y_world - 0.25 * strip_id),
                ],
                dtype=float,
            )
            yaw_deg = yaw_base_deg + 2.4 * view_idx
            strip_ids.append(strip_id)
            centers_world.append(center)
            params_rpy.append(_rpy_from_optical_axis_and_yaw(target - center, yaw_deg))

    free_xyz_config = FreeXYZBAScenarioConfig(
        name="uav_oblique",
        true_rpy_deg=tuple(tuple(np.rad2deg(params)) for params in params_rpy),
        centers_world=tuple(tuple(center) for center in centers_world),
        occluder_boxes_world=(
            (-5.5, -1.5, -6.0, 1.5, 7.0, 22.0),
            (4.0, 8.5, 5.5, 11.5, 8.5, 25.0),
            (-8.5, -3.5, -17.5, -11.0, 10.0, 23.0),
        ),
        n_points=180,
        fixed_view_count=2,
        min_track_length=4,
        min_track_span=4,
        depth_min=16.0,
        depth_max=34.0,
        theta_target_max_deg=80.0,
        seed=501,
    )

    return AirborneStripScenario(
        name="uav_oblique",
        free_xyz_config=free_xyz_config,
        strip_ids=tuple(strip_ids),
        strip_names=strip_names,
        point_boxes_world=(
            (-13.5, -5.5, -15.0, -6.5, 14.0, 26.0),
            (4.5, 12.5, -13.5, -5.0, 13.5, 25.5),
            (-9.0, 1.5, -1.0, 8.0, 15.5, 31.0),
            (-11.5, -3.0, 8.0, 17.5, 13.0, 24.5),
            (3.5, 12.5, 9.5, 18.5, 14.5, 28.0),
        ),
    )


def _sample_point_from_boxes(
    rng: np.random.Generator,
    point_boxes_world: np.ndarray,
) -> np.ndarray:
    box = point_boxes_world[rng.integers(point_boxes_world.shape[0])]
    return np.array(
        [
            rng.uniform(box[0], box[1]),
            rng.uniform(box[2], box[3]),
            rng.uniform(box[4], box[5]),
        ],
        dtype=float,
    )


def make_airborne_strip_scene(
    scenario: AirborneStripScenario,
    camera: CameraConfig = CameraConfig(),
) -> FreeXYZBAScene:
    config = scenario.free_xyz_config
    rng = np.random.default_rng(config.seed)
    true_params = np.deg2rad(np.array(config.true_rpy_deg, dtype=float))
    true_centers_world = np.array(config.centers_world, dtype=float)
    theta_target_max_rad = np.deg2rad(config.theta_target_max_deg)
    n_views = true_params.shape[0]
    point_boxes_world = np.array(scenario.point_boxes_world, dtype=float).reshape(-1, 6)
    occluder_boxes_world = np.array(config.occluder_boxes_world, dtype=float).reshape(-1, 6)

    points_world: list[np.ndarray] = []
    visibility_masks: list[np.ndarray] = []
    clean_pixels_by_view: list[list[np.ndarray]] = [[] for _ in range(n_views)]
    visible_points_by_view: list[list[int]] = [[] for _ in range(n_views)]

    attempts = 0
    max_attempts = config.n_points * 3000
    while len(points_world) < config.n_points and attempts < max_attempts:
        attempts += 1
        candidate = _sample_point_from_boxes(rng, point_boxes_world)

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

        if not np.all(visible[: config.fixed_view_count]):
            continue
        visible = _apply_track_dropout_and_occlusion(
            candidate,
            visible,
            config,
            true_params,
            true_centers_world,
            rng,
        )
        visible_views = np.flatnonzero(visible)
        if visible_views.size < config.min_track_length:
            continue
        if int(visible_views[-1] - visible_views[0]) < config.min_track_span:
            continue

        point_index = len(points_world)
        points_world.append(candidate)
        visibility_masks.append(visible)
        for view in visible_views:
            visible_points_by_view[view].append(point_index)
            clean_pixels_by_view[view].append(pixels[view])

    if len(points_world) < config.n_points:
        raise RuntimeError(f"Could not sample enough airborne tracks for scenario '{scenario.name}'.")

    points_world_array = np.array(points_world, dtype=float)
    visibility_mask = np.array(visibility_masks, dtype=bool)
    track_lengths = visibility_mask.sum(axis=1)
    gap_counts = np.zeros(points_world_array.shape[0], dtype=int)
    for point_idx, mask in enumerate(visibility_mask):
        visible_views = np.flatnonzero(mask)
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
    scene_scale_m = float(np.median(np.linalg.norm(points_world_array - true_centers_world[0], axis=1)))

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
        fixed_view_count=config.fixed_view_count,
        camera=camera,
    )
