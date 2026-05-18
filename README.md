# RPYPolarSynthetic

Synthetic experiments for a **Roll-Pitch-Yaw stratified polar/bearing camera observation model**.

The project tests whether a camera observation can be decomposed into:

- a radial/bearing-angle part `theta`, mainly useful for tilt estimation;
- an angular part `phi`, useful for heading / in-plane optical-axis yaw;
- a covariance-aware residual that respects pixel-noise propagation and the optical-axis singularity.

The current repository contains two experiment layers:

1. `run_experiment.py`: a clean single-view sanity check.
2. `run_ba_experiment.py`: a harder two-view inverse-depth BA stress test.

## Model Convention

Yaw is defined as an in-plane rotation around the current camera optical axis. The rotation convention is:

```text
R = Rz(yaw) Ry(pitch) Rx(roll)
```

For a point direction `q = [x, y, z]^T` after roll-pitch rotation:

```text
theta = atan2(sqrt(x^2 + y^2), z)
phi   = atan2(y, x) + yaw
```

Thus `theta` is decoupled from optical-axis yaw, while `phi` shifts linearly with yaw. This is the geometric basis for the staged optimization.

## Project Layout

```text
RPYPolarSynthetic/
  run_experiment.py
  run_ba_experiment.py
  src/rpy_polar_synth/
    geometry.py
    experiment.py
    ba_experiment.py
    visualize.py
  outputs/
    monte_carlo_results.csv
    scene_3d.png
    image_measurements.png
    axis_singularity.png
    cost_landscape.png
    monte_carlo_summary.png
  outputs_ba/
    ba_monte_carlo_results.csv
    ba_monte_carlo_summary.png
```

## Environment

Tested locally with:

| Item | Value |
|---|---:|
| Python | 3.11.7 |
| numpy | 2.3.2 |
| scipy | 1.16.1 |
| matplotlib | 3.10.5 |

Install dependencies:

```powershell
cd E:\zuo\projects\RPYPolarSynthetic
pip install -r requirements.txt
```

## Experiment 1: Single-View Sanity Check

Run:

```powershell
python run_experiment.py
```

Configuration:

| Setting | Value |
|---|---:|
| Camera model | equidistant projection |
| Image size | 1600 x 1200 |
| Focal length | 620 px |
| Pixel noise sigma | 1.25 px |
| Points | 260 |
| Optical-axis-near points | 50 |
| True RPY | `(8, -13, 28)` deg |
| Yaw initialization errors | `0, 15, 30, 60, 90, 120` deg |
| Trials per level | 10 |
| Output directory | `outputs/` |

Methods:

| Method | Description |
|---|---|
| `uv_joint` | traditional UV reprojection residual |
| `polar_plain_joint` | raw `[theta, phi]` residual without covariance propagation |
| `polar_cov_joint` | covariance-aware polar residual with angle wrap and optical-axis gating |
| `polar_staged` | theta-first tilt estimation, phi-based yaw estimation, final joint polar optimization |

Results:

| Method | Convergence | Median rotation error | Median function evals |
|---|---:|---:|---:|
| `uv_joint` | 100.0% | 0.0175 deg | 14.0 |
| `polar_plain_joint` | 100.0% | 0.1667 deg | 17.5 |
| `polar_cov_joint` | 100.0% | 0.0125 deg | 15.0 |
| `polar_staged` | 100.0% | 0.0125 deg | 25.5 |

Interpretation:

This experiment verifies the geometry, covariance propagation, angle wrap, and optical-axis singularity handling. It does **not** by itself prove that staged optimization beats UV, because the problem is intentionally clean and low-dimensional.

Visualizations:

![3D synthetic scene](outputs/scene_3d.png)

![Noisy image measurements](outputs/image_measurements.png)

![Optical-axis singularity](outputs/axis_singularity.png)

![Cost landscape](outputs/cost_landscape.png)

![Single-view Monte-Carlo summary](outputs/monte_carlo_summary.png)

## Experiment 2: Two-View Inverse-Depth BA Stress Test

Run:

```powershell
python run_ba_experiment.py
```

Configuration:

| Setting | Value |
|---|---:|
| Camera model | equidistant projection |
| Image size | 1600 x 1200 |
| Focal length | 620 px |
| Pixel noise sigma | 1.25 px |
| Points | 72 |
| True RPY | `(9, -14, 31)` deg |
| Second camera center | `(0.85, -0.18, 0.16)` |
| Depth range | 4 m to 13 m |
| Outlier fraction | 6% shuffled matches |
| Yaw initialization errors | `0, 30, 60, 100, 140, 170` deg |
| Tilt initialization error | 24 deg |
| Log inverse-depth noise sigma | 0.65 |
| Trials per level | 6 |
| Output directory | `outputs_ba/` |

Optimized state:

```text
x = [roll, pitch, yaw, log_inv_depth_1, ..., log_inv_depth_N]
```

Methods:

| Method | Description |
|---|---|
| `ba_uv_joint` | joint inverse-depth BA using UV residual |
| `ba_polar_plain_joint` | joint inverse-depth BA using raw polar residual |
| `ba_polar_cov_joint` | joint inverse-depth BA using covariance-aware polar residual |
| `ba_polar_staged` | fixed-depth theta tilt initialization, phi yaw initialization, final joint inverse-depth BA |

Convergence criterion:

```text
rotation error < 3 deg
and inlier depth relative RMSE < 45%
```

Outliers participate in optimization. Depth RMSE is evaluated on inliers only, because shuffled matches have no recoverable depth correspondence.

Results:

| Method | Convergence | Median rotation error | Median inlier depth RMSE | Median function evals |
|---|---:|---:|---:|---:|
| `ba_uv_joint` | 0.0% | 53.5951 deg | 5.027 | 90.0 |
| `ba_polar_plain_joint` | 0.0% | 30.0168 deg | 3.299 | 90.0 |
| `ba_polar_cov_joint` | 0.0% | 31.1321 deg | 3.570 | 90.0 |
| `ba_polar_staged` | 100.0% | 0.6834 deg | 0.229 | 93.0 |

Per-yaw summary for `ba_polar_staged`:

| Initial yaw error | Convergence | Median rotation error | Median inlier depth RMSE |
|---:|---:|---:|---:|
| 0 deg | 100.0% | 0.433 deg | 0.204 |
| 30 deg | 100.0% | 0.710 deg | 0.310 |
| 60 deg | 100.0% | 0.969 deg | 0.287 |
| 100 deg | 100.0% | 0.576 deg | 0.182 |
| 140 deg | 100.0% | 0.489 deg | 0.166 |
| 170 deg | 100.0% | 0.879 deg | 0.260 |

Interpretation:

The stress test supports the larger story: the staged polar/bearing initialization substantially enlarges the convergence basin under depth-pose coupling, large yaw initialization error, and mild outlier contamination.

However, this is still synthetic evidence. A stronger paper-level claim should add more ablations, different camera motions, unknown translation, stronger outliers, and real datasets.

Visualization:

![BA Monte-Carlo summary](outputs_ba/ba_monte_carlo_summary.png)

## Current Claim

Supported:

- covariance-aware polar residual is better behaved than raw polar residual;
- `phi` must be wrapped and down-weighted near the optical axis;
- staged theta/phi initialization can dramatically improve difficult inverse-depth BA convergence in this synthetic setting.

Not yet fully proven:

- superiority on real VIO / SLAM datasets;
- robustness when translation, scale, bias, or extrinsics are also unknown;
- general advantage across camera models and motion patterns.

## Reproduce

```powershell
cd E:\zuo\projects\RPYPolarSynthetic
python run_experiment.py
python run_ba_experiment.py
python -m compileall src run_experiment.py run_ba_experiment.py
```

## Versioning

This project is intended to be versioned under:

```text
https://github.com/Polar-vision/RPYPolarSynthetic
```

Suggested version labels:

| Tag | Meaning |
|---|---|
| `v0.1.0-sanity` | single-view sanity-check implementation |
| `v0.2.0-ba-stress` | two-view inverse-depth BA stress-test implementation and analysis |
