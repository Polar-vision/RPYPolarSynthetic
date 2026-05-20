# 2026-05-20 Experiment 2 and 3 Scene Figure Update

## Request

Add synthetic scene visualization and explanation for Experiment 2 and Experiment 3, regenerate outputs, and sync the result to git.

## Changes

- Added `save_ba_scene_plot` and `save_realistic_ba_scene_plot` in `src/rpy_polar_synth/visualize.py`.
- Added `points_world` to `BAScene` and `RealisticBAScene` so scene plotting uses the true sampled geometry directly.
- Updated `run_ba_experiment.py` to export `outputs_ba/ba_scene_3d.png`.
- Updated `run_exp3_experiment.py` to export `outputs_exp3/exp3_scene_3d.png`.
- Expanded `README.md` with scene-figure interpretation for both experiments.
- Added version note `v0.3.1-ba-scene-figures` to the README version table.

## Verification

- `python -m compileall src run_experiment.py run_ba_experiment.py run_exp3_experiment.py`
- `python run_ba_experiment.py`
- `python run_exp3_experiment.py`

## Generated Outputs

- `outputs_ba/ba_scene_3d.png`
- `outputs_exp3/exp3_scene_3d.png`

## Notes

- This update does not change the staged BA story or the README conclusions.
- The new figures are meant to document scene geometry and make the later Monte-Carlo interpretation easier to read.
