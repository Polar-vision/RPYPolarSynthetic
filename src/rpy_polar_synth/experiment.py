from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from .geometry import (
    bearing_to_polar,
    camera_polar,
    equidistant_project,
    equidistant_unproject,
    hessian_diagnostics,
    pixel_to_polar,
    polar_covariance_from_pixel,
    polar_to_bearing,
    rotation_angle_deg,
    rpy_matrix,
    wrap_angle,
)


@dataclass(frozen=True)
class CameraConfig:
    width: int = 1600
    height: int = 1200
    f: float = 620.0
    sigma_px: float = 1.25

    @property
    def cx(self) -> float:
        return self.width * 0.5

    @property
    def cy(self) -> float:
        return self.height * 0.5


@dataclass(frozen=True)
class ScenarioConfig:
    n_points: int = 260
    optical_axis_points: int = 50
    theta_min_deg: float = 0.2
    theta_max_deg: float = 68.0
    central_theta_max_deg: float = 2.0
    true_rpy_deg: tuple[float, float, float] = (8.0, -13.0, 28.0)
    seed: int = 7


@dataclass
class SyntheticScene:
    points_world: np.ndarray
    points_camera_true: np.ndarray
    clean_pixels: np.ndarray
    observed_pixels: np.ndarray
    observed_polar: np.ndarray
    sqrt_info_polar: np.ndarray
    phi_gates: np.ndarray
    true_params: np.ndarray
    camera: CameraConfig


@dataclass
class OptimizationResult:
    method: str
    params: np.ndarray
    success: bool
    cost: float
    nfev: int
    rotation_error_deg: float
    roll_error_deg: float
    pitch_error_deg: float
    yaw_error_deg: float
    condition: float
    tilt_yaw_coupling: float
    message: str


def make_scene(
    scenario: ScenarioConfig = ScenarioConfig(),
    camera: CameraConfig = CameraConfig(),
) -> SyntheticScene:
    rng = np.random.default_rng(scenario.seed)
    true_params = np.deg2rad(np.array(scenario.true_rpy_deg, dtype=float))
    true_r = rpy_matrix(true_params)

    n_central = scenario.optical_axis_points
    n_wide = scenario.n_points - n_central

    theta_wide = np.deg2rad(
        rng.uniform(scenario.theta_min_deg, scenario.theta_max_deg, size=n_wide)
    )
    theta_central = np.deg2rad(
        rng.uniform(scenario.theta_min_deg, scenario.central_theta_max_deg, size=n_central)
    )
    theta = np.concatenate([theta_central, theta_wide])
    phi = rng.uniform(-np.pi, np.pi, size=scenario.n_points)
    depth = rng.uniform(4.0, 11.0, size=scenario.n_points)

    rays_camera = polar_to_bearing(theta, phi)
    points_camera_true = rays_camera * depth[:, None]
    points_world = (true_r.T @ points_camera_true.T).T
    clean_pixels = equidistant_project(points_camera_true, camera.f, camera.cx, camera.cy)
    observed_pixels = clean_pixels + rng.normal(0.0, camera.sigma_px, size=clean_pixels.shape)

    observed_polar = pixel_to_polar(observed_pixels, camera.f, camera.cx, camera.cy)
    covariances = np.array(
        [
            polar_covariance_from_pixel(pixel, camera.sigma_px, camera.f, camera.cx, camera.cy)
            for pixel in observed_pixels
        ]
    )
    sqrt_info = np.empty_like(covariances)
    for i, cov in enumerate(covariances):
        chol = np.linalg.cholesky(cov)
        sqrt_info[i] = np.linalg.inv(chol)

    theta_obs = observed_polar[:, 0]
    gate_start = np.sin(np.deg2rad(3.0))
    phi_gates = np.clip(np.sin(theta_obs) / gate_start, 0.0, 1.0)

    return SyntheticScene(
        points_world=points_world,
        points_camera_true=points_camera_true,
        clean_pixels=clean_pixels,
        observed_pixels=observed_pixels,
        observed_polar=observed_polar,
        sqrt_info_polar=sqrt_info,
        phi_gates=phi_gates,
        true_params=true_params,
        camera=camera,
    )


def uv_residual(params: np.ndarray, scene: SyntheticScene) -> np.ndarray:
    q = (rpy_matrix(params) @ scene.points_world.T).T
    predicted = equidistant_project(q, scene.camera.f, scene.camera.cx, scene.camera.cy)
    return ((predicted - scene.observed_pixels) / scene.camera.sigma_px).ravel()


def polar_residual(
    params: np.ndarray,
    scene: SyntheticScene,
    covariance_aware: bool = True,
    gate_axis: bool = True,
    theta_only: bool = False,
    phi_only: bool = False,
) -> np.ndarray:
    predicted = camera_polar(scene.points_world, params)
    dtheta = predicted[:, 0] - scene.observed_polar[:, 0]
    dphi = wrap_angle(predicted[:, 1] - scene.observed_polar[:, 1])

    if theta_only:
        if covariance_aware:
            sigma_theta = 1.0 / np.maximum(scene.sqrt_info_polar[:, 0, 0], 1e-12)
            return dtheta / np.maximum(sigma_theta, 1e-12)
        return dtheta / (scene.camera.sigma_px / scene.camera.f)

    if phi_only:
        if covariance_aware:
            raw = np.column_stack([np.zeros_like(dtheta), dphi])
            whitened = np.einsum("nij,nj->ni", scene.sqrt_info_polar, raw)
            if gate_axis:
                whitened[:, 1] *= scene.phi_gates
            return whitened.ravel()
        return dphi * scene.phi_gates / 0.03

    raw = np.column_stack([dtheta, dphi])
    if covariance_aware:
        whitened = np.einsum("nij,nj->ni", scene.sqrt_info_polar, raw)
        if gate_axis:
            whitened[:, 1] *= scene.phi_gates
        return whitened.ravel()

    nominal_theta_sigma = scene.camera.sigma_px / scene.camera.f
    return np.column_stack([dtheta / nominal_theta_sigma, dphi / 0.03]).ravel()


def optimize_joint(
    method: str,
    scene: SyntheticScene,
    initial_params: np.ndarray,
    max_nfev: int = 120,
) -> OptimizationResult:
    if method == "uv_joint":
        residual_fn = lambda p: uv_residual(p, scene)
    elif method == "polar_plain_joint":
        residual_fn = lambda p: polar_residual(p, scene, covariance_aware=False, gate_axis=False)
    elif method == "polar_cov_joint":
        residual_fn = lambda p: polar_residual(p, scene, covariance_aware=True, gate_axis=True)
    else:
        raise ValueError(f"Unknown joint method: {method}")

    result = least_squares(
        residual_fn,
        initial_params,
        method="trf",
        loss="huber",
        f_scale=2.5,
        max_nfev=max_nfev,
    )
    return summarize_result(method, result.x, scene, result.cost, result.success, result.nfev, result.message)


def optimize_staged(
    scene: SyntheticScene,
    initial_params: np.ndarray,
    max_nfev_per_stage: int = 90,
) -> OptimizationResult:
    tilt0 = initial_params[:2].copy()
    yaw0 = initial_params[2].copy()

    def theta_stage(tilt: np.ndarray) -> np.ndarray:
        params = np.array([tilt[0], tilt[1], yaw0])
        return polar_residual(params, scene, covariance_aware=True, gate_axis=True, theta_only=True)

    stage1 = least_squares(
        theta_stage,
        tilt0,
        method="trf",
        loss="huber",
        f_scale=2.5,
        max_nfev=max_nfev_per_stage,
    )

    def phi_stage(yaw: np.ndarray) -> np.ndarray:
        params = np.array([stage1.x[0], stage1.x[1], yaw[0]])
        return polar_residual(params, scene, covariance_aware=True, gate_axis=True, phi_only=True)

    stage2 = least_squares(
        phi_stage,
        np.array([yaw0]),
        method="trf",
        loss="huber",
        f_scale=2.5,
        max_nfev=max_nfev_per_stage,
    )

    staged_initial = np.array([stage1.x[0], stage1.x[1], stage2.x[0]])
    final = least_squares(
        lambda p: polar_residual(p, scene, covariance_aware=True, gate_axis=True),
        staged_initial,
        method="trf",
        loss="huber",
        f_scale=2.5,
        max_nfev=max_nfev_per_stage,
    )

    success = bool(stage1.success and stage2.success and final.success)
    message = f"stage1={stage1.message}; stage2={stage2.message}; final={final.message}"
    return summarize_result(
        "polar_staged",
        final.x,
        scene,
        final.cost,
        success,
        stage1.nfev + stage2.nfev + final.nfev,
        message,
    )


def summarize_result(
    method: str,
    params: np.ndarray,
    scene: SyntheticScene,
    cost: float,
    success: bool,
    nfev: int,
    message: str,
) -> OptimizationResult:
    delta = wrap_angle(params - scene.true_params)
    diagnostics = hessian_diagnostics(lambda p: polar_residual(p, scene), params)
    return OptimizationResult(
        method=method,
        params=params,
        success=bool(success),
        cost=float(cost),
        nfev=int(nfev),
        rotation_error_deg=rotation_angle_deg(rpy_matrix(params), rpy_matrix(scene.true_params)),
        roll_error_deg=float(np.rad2deg(delta[0])),
        pitch_error_deg=float(np.rad2deg(delta[1])),
        yaw_error_deg=float(np.rad2deg(delta[2])),
        condition=diagnostics["condition"],
        tilt_yaw_coupling=diagnostics["tilt_yaw_coupling"],
        message=str(message),
    )


def initial_guess(
    true_params: np.ndarray,
    yaw_error_deg: float,
    tilt_error_deg: float,
    rng: np.random.Generator,
) -> np.ndarray:
    tilt_direction = rng.normal(size=2)
    tilt_direction /= max(np.linalg.norm(tilt_direction), 1e-12)
    tilt_error = np.deg2rad(tilt_error_deg) * tilt_direction
    yaw_sign = rng.choice([-1.0, 1.0])
    perturbation = np.array([tilt_error[0], tilt_error[1], yaw_sign * np.deg2rad(yaw_error_deg)])
    return true_params + perturbation


def run_monte_carlo(
    scene: SyntheticScene,
    yaw_errors_deg: list[float] | None = None,
    trials_per_level: int = 10,
    tilt_error_deg: float = 14.0,
    seed: int = 31,
) -> list[dict[str, float | str | bool | int]]:
    if yaw_errors_deg is None:
        yaw_errors_deg = [0.0, 15.0, 30.0, 60.0, 90.0, 120.0]

    rng = np.random.default_rng(seed)
    methods = ["uv_joint", "polar_plain_joint", "polar_cov_joint", "polar_staged"]
    records: list[dict[str, float | str | bool | int]] = []

    for yaw_error in yaw_errors_deg:
        for trial in range(trials_per_level):
            init = initial_guess(scene.true_params, yaw_error, tilt_error_deg, rng)
            for method in methods:
                if method == "polar_staged":
                    result = optimize_staged(scene, init)
                else:
                    result = optimize_joint(method, scene, init)

                records.append(
                    {
                        "method": result.method,
                        "yaw_init_error_deg": yaw_error,
                        "trial": trial,
                        "success": result.success,
                        "converged_2deg": result.rotation_error_deg < 2.0,
                        "rotation_error_deg": result.rotation_error_deg,
                        "roll_error_deg": result.roll_error_deg,
                        "pitch_error_deg": result.pitch_error_deg,
                        "yaw_error_deg": result.yaw_error_deg,
                        "cost": result.cost,
                        "nfev": result.nfev,
                        "condition": result.condition,
                        "tilt_yaw_coupling": result.tilt_yaw_coupling,
                    }
                )

    return records


def write_csv(records: list[dict[str, float | str | bool | int]], path: Path) -> None:
    import csv

    if not records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)


def records_to_array(records: list[dict[str, float | str | bool | int]]) -> np.ndarray:
    dtype = [
        ("method", "U32"),
        ("yaw_init_error_deg", float),
        ("trial", int),
        ("success", bool),
        ("converged_2deg", bool),
        ("rotation_error_deg", float),
        ("roll_error_deg", float),
        ("pitch_error_deg", float),
        ("yaw_error_deg", float),
        ("cost", float),
        ("nfev", float),
        ("condition", float),
        ("tilt_yaw_coupling", float),
    ]
    rows = []
    for rec in records:
        rows.append(tuple(rec[name] for name, _ in dtype))
    return np.array(rows, dtype=dtype)


def build_landscape(
    scene: SyntheticScene,
    pitch_offsets_deg: np.ndarray,
    yaw_offsets_deg: np.ndarray,
) -> dict[str, np.ndarray]:
    return build_landscape_slice(
        scene,
        x_axis="yaw",
        y_axis="pitch",
        x_offsets_deg=yaw_offsets_deg,
        y_offsets_deg=pitch_offsets_deg,
    )


def build_landscape_slice(
    scene: SyntheticScene,
    x_axis: str,
    y_axis: str,
    x_offsets_deg: np.ndarray,
    y_offsets_deg: np.ndarray,
) -> dict[str, np.ndarray | str]:
    axis_to_index = {"roll": 0, "pitch": 1, "yaw": 2}
    if x_axis not in axis_to_index or y_axis not in axis_to_index:
        raise ValueError("Landscape axes must be selected from: roll, pitch, yaw.")
    if x_axis == y_axis:
        raise ValueError("Landscape x_axis and y_axis must be different.")

    uv = np.zeros((y_offsets_deg.size, x_offsets_deg.size))
    theta_only = np.zeros_like(uv)
    polar = np.zeros_like(uv)

    x_index = axis_to_index[x_axis]
    y_index = axis_to_index[y_axis]

    for i, y_offset in enumerate(np.deg2rad(y_offsets_deg)):
        for j, x_offset in enumerate(np.deg2rad(x_offsets_deg)):
            params = scene.true_params.copy()
            params[x_index] += x_offset
            params[y_index] += y_offset
            r_uv = uv_residual(params, scene)
            r_theta = polar_residual(params, scene, theta_only=True)
            r_polar = polar_residual(params, scene)
            uv[i, j] = 0.5 * float(r_uv @ r_uv)
            theta_only[i, j] = 0.5 * float(r_theta @ r_theta)
            polar[i, j] = 0.5 * float(r_polar @ r_polar)

    def normalize(cost: np.ndarray) -> np.ndarray:
        shifted = cost - np.nanmin(cost)
        return np.log10(shifted + 1.0)

    return {
        "x_axis": x_axis,
        "y_axis": y_axis,
        "x_offsets_deg": x_offsets_deg,
        "y_offsets_deg": y_offsets_deg,
        # Backward-compatible keys for the original pitch-yaw landscape.
        "pitch_offsets_deg": y_offsets_deg if y_axis == "pitch" else np.array([]),
        "yaw_offsets_deg": x_offsets_deg if x_axis == "yaw" else np.array([]),
        "uv": normalize(uv),
        "theta_only": normalize(theta_only),
        "polar": normalize(polar),
    }


def covariance_singularity_curve(
    camera: CameraConfig,
    theta_deg: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    if theta_deg is None:
        theta_deg = np.concatenate(
            [
                np.linspace(0.05, 3.0, 80),
                np.linspace(3.1, 70.0, 100),
            ]
        )

    sigma_theta = []
    sigma_phi = []
    gates = []
    for deg in theta_deg:
        theta = np.deg2rad(deg)
        pixel = np.array([camera.cx + camera.f * theta, camera.cy])
        cov = polar_covariance_from_pixel(pixel, camera.sigma_px, camera.f, camera.cx, camera.cy)
        sigma_theta.append(np.sqrt(cov[0, 0]))
        sigma_phi.append(np.sqrt(cov[1, 1]))
        gates.append(np.clip(np.sin(theta) / np.sin(np.deg2rad(3.0)), 0.0, 1.0))

    return {
        "theta_deg": theta_deg,
        "sigma_theta_deg": np.rad2deg(np.array(sigma_theta)),
        "sigma_phi_deg": np.rad2deg(np.array(sigma_phi)),
        "phi_gate": np.array(gates),
    }
