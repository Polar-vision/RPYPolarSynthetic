from __future__ import annotations

import numpy as np


EPS = 1e-12


def wrap_angle(angle: np.ndarray | float) -> np.ndarray | float:
    """Wrap angles to [-pi, pi)."""
    return np.arctan2(np.sin(angle), np.cos(angle))


def rx(angle: float) -> np.ndarray:
    c, s = np.cos(angle), np.sin(angle)
    return np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, c, -s],
            [0.0, s, c],
        ]
    )


def ry(angle: float) -> np.ndarray:
    c, s = np.cos(angle), np.sin(angle)
    return np.array(
        [
            [c, 0.0, s],
            [0.0, 1.0, 0.0],
            [-s, 0.0, c],
        ]
    )


def rz(angle: float) -> np.ndarray:
    c, s = np.cos(angle), np.sin(angle)
    return np.array(
        [
            [c, -s, 0.0],
            [s, c, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )


def rpy_matrix(params: np.ndarray) -> np.ndarray:
    """Layered camera rotation R = Rz(yaw) Ry(pitch) Rx(roll).

    The yaw in this experiment is an in-plane rotation around the current optical
    axis. This is the axis convention needed for exact theta/yaw decoupling.
    """
    roll, pitch, yaw = params
    return rz(yaw) @ ry(pitch) @ rx(roll)


def rotation_angle_deg(r_est: np.ndarray, r_true: np.ndarray) -> float:
    delta = r_est @ r_true.T
    cos_angle = (np.trace(delta) - 1.0) * 0.5
    return float(np.rad2deg(np.arccos(np.clip(cos_angle, -1.0, 1.0))))


def bearing_to_polar(bearing: np.ndarray) -> np.ndarray:
    b = np.asarray(bearing)
    rho = np.linalg.norm(b[..., :2], axis=-1)
    theta = np.arctan2(rho, b[..., 2])
    phi = np.arctan2(b[..., 1], b[..., 0])
    return np.stack([theta, phi], axis=-1)


def polar_to_bearing(theta: np.ndarray, phi: np.ndarray) -> np.ndarray:
    sin_theta = np.sin(theta)
    return np.stack(
        [
            sin_theta * np.cos(phi),
            sin_theta * np.sin(phi),
            np.cos(theta),
        ],
        axis=-1,
    )


def camera_polar(points_world: np.ndarray, params: np.ndarray) -> np.ndarray:
    q = (rpy_matrix(params) @ points_world.T).T
    return bearing_to_polar(q)


def equidistant_project(points_camera: np.ndarray, f: float, cx: float, cy: float) -> np.ndarray:
    polar = bearing_to_polar(points_camera)
    theta, phi = polar[:, 0], polar[:, 1]
    radius = f * theta
    return np.column_stack([cx + radius * np.cos(phi), cy + radius * np.sin(phi)])


def equidistant_unproject(pixels: np.ndarray, f: float, cx: float, cy: float) -> np.ndarray:
    dx = pixels[:, 0] - cx
    dy = pixels[:, 1] - cy
    radius = np.hypot(dx, dy)
    theta = radius / f
    phi = np.arctan2(dy, dx)
    return polar_to_bearing(theta, phi)


def pixel_to_polar(pixels: np.ndarray, f: float, cx: float, cy: float) -> np.ndarray:
    return bearing_to_polar(equidistant_unproject(pixels, f, cx, cy))


def polar_covariance_from_pixel(
    pixel: np.ndarray,
    sigma_px: float,
    f: float,
    cx: float,
    cy: float,
    eps_px: float = 1e-3,
) -> np.ndarray:
    """Propagate isotropic pixel covariance through unprojection into [theta, phi].

    The finite-difference form keeps the function usable if the projection model
    is later replaced by a more complex distortion model.
    """
    pixel = np.asarray(pixel, dtype=float)

    def eval_polar(p: np.ndarray) -> np.ndarray:
        return pixel_to_polar(p.reshape(1, 2), f, cx, cy)[0]

    base = eval_polar(pixel)
    jac = np.zeros((2, 2))
    for axis in range(2):
        delta = np.zeros(2)
        delta[axis] = eps_px
        plus = eval_polar(pixel + delta)
        minus = eval_polar(pixel - delta)
        diff = plus - minus
        diff[1] = wrap_angle(diff[1])
        jac[:, axis] = diff / (2.0 * eps_px)

    cov_uv = (sigma_px**2) * np.eye(2)
    cov = jac @ cov_uv @ jac.T

    # Near the optical axis phi is physically ill-defined. The large variance
    # below makes that loss of information explicit instead of letting numerical
    # finite differences over-confidently weight phi.
    theta = base[0]
    if theta < np.deg2rad(0.05):
        cov[1, 1] = max(cov[1, 1], (np.pi / 2.0) ** 2)

    return cov + 1e-12 * np.eye(2)


def numerical_jacobian(fn, x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    y0 = np.asarray(fn(x), dtype=float)
    jac = np.zeros((y0.size, x.size))
    for i in range(x.size):
        step = np.zeros_like(x)
        step[i] = eps
        yp = np.asarray(fn(x + step), dtype=float)
        ym = np.asarray(fn(x - step), dtype=float)
        jac[:, i] = (yp - ym) / (2.0 * eps)
    return jac


def hessian_diagnostics(residual_fn, params: np.ndarray) -> dict[str, float]:
    jac = numerical_jacobian(residual_fn, params)
    hessian = jac.T @ jac
    singular_values = np.linalg.svd(hessian, compute_uv=False)
    floor = max(float(singular_values[-1]), 1e-12)
    condition = float(singular_values[0] / floor)

    tilt_block = hessian[:2, :2]
    yaw_info = max(float(abs(hessian[2, 2])), 1e-12)
    cross = hessian[:2, 2]
    coupling = float(np.linalg.norm(cross) / np.sqrt(max(np.linalg.norm(tilt_block), 1e-12) * yaw_info))
    return {"condition": condition, "tilt_yaw_coupling": coupling}
