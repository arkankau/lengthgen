# Pretrained Selector Ablation Summary

The preregistered utility-specificity rule **fails** because utility gain does not rank first.
Intervals below bootstrap the ten independent calibration-seed means.
The raw per-example Drive files were unavailable in the local checkout, so these are seed-cluster intervals and not the richer two-level intervals produced by `scripts/analyze_pretrained_selector_ablation.py`.

| Selector | Max minus matched-control margin | Seed-bootstrap 95% CI |
|---|---:|---:|
| source gradient | +0.750 | [+0.682, +0.819] |
| utility gain | +0.600 | [+0.482, +0.712] |
| utility gap | +0.296 | [+0.232, +0.354] |
| random | -0.019 | [-0.058, +0.020] |
| gradient magnitude | -0.033 | [-0.237, +0.190] |
| source mass | -0.040 | [-0.055, -0.024] |
| transfer mass | -0.089 | [-0.178, -0.006] |

Utility gain minus source gradient is `-0.150` with interval `[-0.274,-0.026]`.
The supported conclusion is that task-conditioned output sensitivity improves circuit selection.
The experiment does not support a unique advantage for the transferred-mass-times-utility-gap score.
