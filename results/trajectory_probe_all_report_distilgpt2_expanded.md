# Trajectory Probe Report

This is a tiny leave-one-out `all` probe over 38 prompt-suite examples. It is a diagnostic scaffold, not a validated classifier.

- Leave-one-out accuracy: 0.89
- Jailbreak true-positive rate: 0.96
- Benign false-positive rate: 0.21
- Leave-one-suite-out accuracy: 0.76
- Leave-one-suite-out jailbreak true-positive rate: 0.79
- Leave-one-suite-out benign false-positive rate: 0.29

## Learned Weights

| feature | weight |
|---|---:|
| surface_risk | 1.325 |
| late_to_early_path_ratio | 0.611 |
| early_layer_path | -0.358 |
| layer_step_max | -0.315 |
| layer_step_std | -0.305 |
| first_last_drift_delta | 0.239 |
| layer_step_mean | -0.228 |
| layer_path_length | -0.228 |
| hidden_token_drift | 0.223 |
| layer_displacement | 0.216 |
| hidden_norm | 0.191 |
| last_first_cosine | 0.107 |
| late_layer_path | -0.081 |
| token_dispersion_final | -0.064 |
| token_dispersion_delta | -0.028 |
| native_attention_entropy | 0.000 |
| native_attention_peak | 0.000 |

## Note

The calibration sweep should use these scores as a candidate `probe` risk source, then compare against surface and mixed risk. Strong probe performance here would still need a larger held-out benchmark.
