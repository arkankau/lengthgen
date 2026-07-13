# Residual Steering Thermodynamic Audit

This is a different intervention family from null-attention: residual-stream steering with a refusal-minus-unsafe direction.
The audit asks whether native thermodynamic/basin features predict steering-induced collapse or utility loss better than simple knobs.

## Binary Collapse Prediction

| scope | target | group | n | positive rate | best feature | AUROC | Spearman |
|---|---|---|---:|---:|---|---:|---:|
| pooled | collapse_failure | thermo | 240 | 0.263 | basin_margin | 0.693 | 0.294 |
| within_setting_mean | collapse_failure | thermo | 240 | 0.263 | native_entropy | 0.887 | 0.464 |
| pooled | collapse_failure | simple | 240 | 0.263 | steering_strength | 0.956 | 0.696 |
| within_setting_mean | collapse_failure | simple | 240 | 0.263 | risk | 0.937 | 0.676 |

## Continuous Degradation Prediction

| scope | target | group | n | mean target | best feature | abs Spearman | signed Spearman |
|---|---|---|---:|---:|---|---:|---:|
| pooled | utility_loss | thermo | 240 | 0.198 | basin_margin | 0.408 | 0.408 |
| within_setting_mean | utility_loss | thermo | 240 | 0.198 | native_entropy | 0.582 | 0.556 |
| pooled | utility_loss | simple | 240 | 0.198 | steering_strength | 0.807 | 0.807 |
| within_setting_mean | utility_loss | simple | 240 | 0.198 | risk | 0.777 | 0.777 |
| pooled | coherence | thermo | 240 | 0.737 | basin_margin | 0.390 | -0.390 |
| within_setting_mean | coherence | thermo | 240 | 0.737 | native_entropy | 0.617 | -0.540 |
| pooled | coherence | simple | 240 | 0.737 | steering_strength | 0.650 | -0.650 |
| within_setting_mean | coherence | simple | 240 | 0.737 | risk | 0.552 | -0.516 |
| pooled | repetition_collapse | thermo | 240 | 0.311 | basin_margin | 0.397 | 0.397 |
| within_setting_mean | repetition_collapse | thermo | 240 | 0.311 | native_entropy | 0.608 | 0.608 |
| pooled | repetition_collapse | simple | 240 | 0.311 | steering_strength | 0.663 | 0.663 |
| within_setting_mean | repetition_collapse | simple | 240 | 0.311 | risk | 0.539 | 0.534 |
| pooled | template_collapse | thermo | 240 | 0.053 | steering_alignment | 0.206 | 0.206 |
| within_setting_mean | template_collapse | thermo | 240 | 0.053 | native_entropy | 0.427 | 0.092 |
| pooled | template_collapse | simple | 240 | 0.053 | risk | 0.291 | 0.291 |
| within_setting_mean | template_collapse | simple | 240 | 0.053 | risk | 0.504 | 0.429 |
| pooled | semantic_drift | thermo | 240 | 0.557 | basin_margin | 0.478 | 0.478 |
| within_setting_mean | semantic_drift | thermo | 240 | 0.557 | native_entropy | 0.665 | 0.665 |
| pooled | semantic_drift | simple | 240 | 0.557 | steering_strength | 0.897 | 0.897 |
| within_setting_mean | semantic_drift | simple | 240 | 0.557 | risk | 0.879 | 0.879 |
| pooled | degradation_score | thermo | 240 | 0.353 | basin_margin | 0.352 | 0.352 |
| within_setting_mean | degradation_score | thermo | 240 | 0.353 | native_entropy | 0.618 | 0.618 |
| pooled | degradation_score | simple | 240 | 0.353 | steering_strength | 0.730 | 0.730 |
| within_setting_mean | degradation_score | simple | 240 | 0.353 | risk | 0.677 | 0.677 |

## Setting Averages

| setting | layer | alpha | mean collapse | mean utility loss | mean coherence |
|---|---:|---:|---:|---:|---:|
| rs001 | 6 | -64.00 | 0.500 | 0.457 | 0.481 |
| rs002 | 6 | -32.00 | 0.500 | 0.359 | 0.565 |
| rs003 | 6 | -16.00 | 0.000 | 0.063 | 0.879 |
| rs004 | 6 | -8.00 | 0.000 | 0.031 | 0.930 |
| rs005 | 6 | 8.00 | 0.100 | 0.069 | 0.854 |
| rs006 | 6 | 16.00 | 0.000 | 0.110 | 0.819 |
| rs007 | 6 | 32.00 | 0.100 | 0.167 | 0.756 |
| rs008 | 6 | 64.00 | 0.400 | 0.362 | 0.567 |
| rs009 | 10 | -64.00 | 0.500 | 0.340 | 0.595 |
| rs010 | 10 | -32.00 | 0.400 | 0.360 | 0.564 |
| rs011 | 10 | -16.00 | 0.300 | 0.211 | 0.718 |
| rs012 | 10 | -8.00 | 0.100 | 0.065 | 0.871 |
| rs013 | 10 | 8.00 | 0.200 | 0.077 | 0.870 |
| rs014 | 10 | 16.00 | 0.000 | 0.104 | 0.838 |
| rs015 | 10 | 32.00 | 0.400 | 0.265 | 0.658 |
| rs016 | 10 | 64.00 | 0.500 | 0.432 | 0.497 |
| rs017 | 16 | -64.00 | 0.500 | 0.409 | 0.516 |
| rs018 | 16 | -32.00 | 0.400 | 0.112 | 0.825 |
| rs019 | 16 | -16.00 | 0.100 | 0.038 | 0.894 |
| rs020 | 16 | -8.00 | 0.100 | 0.056 | 0.886 |
| rs021 | 16 | 8.00 | 0.200 | 0.048 | 0.887 |
| rs022 | 16 | 16.00 | 0.100 | 0.045 | 0.892 |
| rs023 | 16 | 32.00 | 0.400 | 0.164 | 0.784 |
| rs024 | 16 | 64.00 | 0.500 | 0.409 | 0.529 |

## Failure-Mode Averages

| setting | layer | alpha | repetition | template | semantic drift | degradation |
|---|---:|---:|---:|---:|---:|---:|
| rs001 | 6 | -64.00 | 0.578 | 0.200 | 0.799 | 0.578 |
| rs002 | 6 | -32.00 | 0.553 | 0.000 | 0.573 | 0.553 |
| rs003 | 6 | -16.00 | 0.169 | 0.033 | 0.523 | 0.182 |
| rs004 | 6 | -8.00 | 0.111 | 0.033 | 0.502 | 0.139 |
| rs005 | 6 | 8.00 | 0.185 | 0.100 | 0.448 | 0.280 |
| rs006 | 6 | 16.00 | 0.210 | 0.000 | 0.472 | 0.210 |
| rs007 | 6 | 32.00 | 0.274 | 0.000 | 0.588 | 0.274 |
| rs008 | 6 | 64.00 | 0.512 | 0.000 | 0.693 | 0.512 |
| rs009 | 10 | -64.00 | 0.487 | 0.033 | 0.813 | 0.527 |
| rs010 | 10 | -32.00 | 0.463 | 0.000 | 0.654 | 0.463 |
| rs011 | 10 | -16.00 | 0.374 | 0.000 | 0.596 | 0.374 |
| rs012 | 10 | -8.00 | 0.173 | 0.000 | 0.501 | 0.173 |
| rs013 | 10 | 8.00 | 0.162 | 0.100 | 0.504 | 0.257 |
| rs014 | 10 | 16.00 | 0.201 | 0.000 | 0.534 | 0.201 |
| rs015 | 10 | 32.00 | 0.414 | 0.000 | 0.542 | 0.414 |
| rs016 | 10 | 64.00 | 0.419 | 0.000 | 0.604 | 0.538 |
| rs017 | 16 | -64.00 | 0.536 | 0.000 | 0.653 | 0.547 |
| rs018 | 16 | -32.00 | 0.241 | 0.243 | 0.479 | 0.327 |
| rs019 | 16 | -16.00 | 0.142 | 0.203 | 0.421 | 0.262 |
| rs020 | 16 | -8.00 | 0.147 | 0.133 | 0.237 | 0.266 |
| rs021 | 16 | 8.00 | 0.146 | 0.170 | 0.430 | 0.298 |
| rs022 | 16 | 16.00 | 0.146 | 0.033 | 0.472 | 0.173 |
| rs023 | 16 | 32.00 | 0.385 | 0.000 | 0.659 | 0.385 |
| rs024 | 16 | 64.00 | 0.445 | 0.000 | 0.659 | 0.543 |
