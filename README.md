# RPYPolarSynthetic

Synthetic experiments for a **Roll-Pitch-Yaw stratified polar/bearing camera observation model**.

The project tests whether a camera observation can be decomposed into:

- a radial/bearing-angle part `theta`, mainly useful for tilt estimation;
- an angular part `phi`, useful for heading / in-plane optical-axis yaw;
- a covariance-aware residual that respects pixel-noise propagation and the optical-axis singularity.

The current repository contains two experiment layers:

1. `run_experiment.py`: a clean single-view sanity check.
2. `run_ba_experiment.py`: a harder two-view inverse-depth BA stress test.

## Project-Specific RPY Convention

This project uses a deliberately non-navigation RPY convention. The word `yaw` here means **an in-plane rotation around the current camera optical axis**. It is not the usual vehicle / IMU heading angle around gravity.

The convention is:

| Variable | Meaning in this project |
|---|---|
| `roll` | first tilt rotation around the camera `x` axis |
| `pitch` | second tilt rotation around the camera `y` axis |
| `yaw` | final rotation around the camera optical axis `z` |

The rotation order is:

```text
R = Rz(yaw) Ry(pitch) Rx(roll)
```

For a point direction `q = [x, y, z]^T` after the roll-pitch tilt layer:

```text
theta = atan2(sqrt(x^2 + y^2), z)
phi   = atan2(y, x) + yaw
```

Thus `theta` is decoupled from optical-axis yaw, while `phi` shifts linearly with yaw. This is the geometric basis for the staged optimization.

This naming is intentional. If `yaw` is instead defined as a world-frame heading around gravity, the exact `theta`/`phi` decoupling used by this experiment generally does not hold.

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
    cost_landscape_pitch_yaw.png
    cost_landscape_roll_yaw.png
    cost_landscape_roll_pitch.png
    cost_landscape_all_slices.png
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

### Figure Interpretation

![3D synthetic scene](outputs/scene_3d.png)

`scene_3d.png` visualizes the generated world points and the true camera axes. The point color is the true bearing angle `theta`, namely the angle between the optical axis and the ray from the camera center to the point.

Key reading:

- The blue camera axis is the optical axis used by the polar/bearing model.
- Points cover both near-axis rays and large off-axis rays, so the experiment contains both well-conditioned and near-singular angular measurements.
- This figure checks that the synthetic scene is not a tiny narrow-FOV case; it contains enough angular diversity to test polar residuals.

What it supports:

- The experiment is evaluating a bearing-space observation model, not merely a small-angle pinhole approximation.
- The presence of near-axis points motivates explicit handling of the `phi` singularity.

What it does not prove:

- It does not prove convergence advantage by itself; it only documents the geometry being tested.

![Noisy image measurements](outputs/image_measurements.png)

`image_measurements.png` shows the noisy image-plane observations generated by the equidistant camera model. The black cross is the optical-axis projection. The color again encodes observed `theta`.

Key reading:

- In an equidistant camera, image radius is approximately `r = f * theta`, so points farther from the cross have larger `theta`.
- Pixel noise is injected in `u, v`, then transformed into polar/bearing observations.
- Near the optical axis, many pixels have very small radius. Their radial angle `theta` remains meaningful, but their azimuth `phi` is poorly defined.

What it supports:

- It connects the conventional UV observation space to the proposed polar observation space.
- It explains why covariance propagation is necessary: uniform pixel noise does not become uniform `[theta, phi]` noise.

![Optical-axis singularity](outputs/axis_singularity.png)

`axis_singularity.png` is the most important diagnostic figure for the covariance-aware residual. It plots the propagated angular uncertainty from isotropic pixel noise into `theta` and `phi`.

Key reading:

- `sigma_theta` stays relatively stable because the radial bearing angle is well-defined even near the center.
- `sigma_phi` grows rapidly as `theta -> 0`, because azimuth around the optical axis becomes physically ambiguous.
- The green dashed gate suppresses `phi` information near the optical axis instead of pretending that the angle is reliable.

What it supports:

- A raw polar residual is statistically wrong near the optical axis.
- The `phi` residual must be wrapped and down-weighted or removed when `theta` is too small.
- This is not only an implementation trick; it follows from the observation geometry.

Practical consequence:

```text
near optical axis: use theta strongly, use phi weakly or not at all
away from axis: use both theta and phi
```

![Cost landscape: pitch-yaw](outputs/cost_landscape.png)

`cost_landscape.png` is the original pitch-yaw slice, also saved as `cost_landscape_pitch_yaw.png`. It compares cost surfaces over pitch and optical-axis yaw offsets. The three panels show UV cost, theta-only polar cost, and covariance-aware polar cost.

Key reading:

- The theta-only panel should be read as a tilt diagnostic. Because this project's `yaw` is optical-axis rotation, changing yaw has little direct effect on `theta`.
- The full polar cost combines radial `theta` information with azimuthal `phi` information, so it localizes the true solution in both tilt and optical-axis yaw.
- The UV cost is a valid baseline, but it does not expose the radial/angular information structure as explicitly.

What it supports:

- The proposed staged story is geometrically plausible: estimate tilt using the radial/bearing angle first, then estimate optical-axis yaw using azimuth.
- The staged method is not claiming new visual information; it reorganizes existing information into better-conditioned subproblems.

Important caution:

- This plot depends on the project's optical-axis yaw convention. If yaw is a world-frame heading, the theta-only surface would not have the same interpretation.

The same three cost types are now also drawn for the other two tilt slices:

![Cost landscape: roll-yaw](outputs/cost_landscape_roll_yaw.png)

`cost_landscape_roll_yaw.png` holds pitch fixed and scans roll versus optical-axis yaw. This is the closest sibling of the original plot, but it shows that the same theta/phi logic is not tied to the pitch axis specifically.

![Cost landscape: roll-pitch](outputs/cost_landscape_roll_pitch.png)

`cost_landscape_roll_pitch.png` holds yaw fixed and scans the two tilt axes together. This is the most direct check that the roll-pitch subspace behaves like a tilt plane, while yaw remains the separate in-plane rotation.

![Cost landscape: all slices](outputs/cost_landscape_all_slices.png)

`cost_landscape_all_slices.png` arranges all nine panels together: three cost types times three coordinate slices. This is the most complete visualization for the observation model.

What the three slices together support:

- `pitch-yaw` and `roll-yaw` show that both tilt axes decouple differently from the optical-axis yaw, but neither breaks the basic staged story.
- `roll-pitch` shows the pure tilt plane, where the residual landscape should still be well-behaved near the truth.
- The three slices jointly support the claim that the decomposition is geometric, not an artifact of one special axis choice.

![Single-view Monte-Carlo summary](outputs/monte_carlo_summary.png)

`monte_carlo_summary.png` summarizes the clean single-view Monte-Carlo experiment.

Key reading:

- All methods converge in this clean 3-DOF pose-only setup.
- `polar_plain_joint` has a larger final error because raw `[theta, phi]` weighting ignores the actual covariance induced by pixel noise.
- `polar_cov_joint` slightly improves the final error compared with UV, while `polar_staged` reaches the same final accuracy but uses more function evaluations.

What it supports:

- Covariance-aware polar residuals are numerically meaningful.
- Raw polar residuals should not be used as the main scientific baseline.

What it does not support:

- It does not prove that staged optimization is superior. The single-view pose-only problem is too clean and too low-dimensional to expose the convergence-basin advantage.

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

### Figure Interpretation

`ba_monte_carlo_summary.png` is the central evidence figure for the larger claim. Unlike the single-view sanity check, this experiment optimizes pose and inverse depths together, so pose-depth coupling can trap direct joint optimization.

Key reading:

- The convergence-rate panel shows that direct joint BA with UV, raw polar, or covariance-aware polar residuals fails under the tested large-initial-error regime.
- The final-pose-error panel shows that `ba_polar_staged` stays below roughly one degree median error across yaw initialization errors up to 170 degrees.
- The inlier-depth-RMSE panel shows that staged initialization also allows the later joint BA to recover reasonable depths for true correspondences.
- The optimizer-effort panel shows that staged BA is not free, but the extra effort buys a much larger convergence basin.
- The staged-initialization panel separates the role of initialization from final BA: most of the pose rescue happens before the final joint refinement.
- The final-yaw-error panel should be read as final **optical-axis yaw** error, not world heading error.

What it supports:

- The larger story starts to hold in this synthetic stress test: theta/phi staged initialization can rescue a hard inverse-depth BA problem that direct joint optimization does not solve.
- The benefit is not merely from changing UV to polar residuals; `ba_polar_cov_joint` alone still fails in this setting. The staged structure is the important part.

Limitations:

- Translation is known.
- The scene and noise are synthetic.
- Outliers are mild and handled only by a robust loss, not by a full matching/outlier rejection pipeline.
- This is evidence for a research direction, not yet a complete VIO/SLAM claim.

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
| `v0.2.1-figure-report` | detailed figure interpretation and project-specific RPY documentation |
| `v0.2.2-landscape-slices` | complete roll-pitch-yaw cost landscape slices with six additional panels |
