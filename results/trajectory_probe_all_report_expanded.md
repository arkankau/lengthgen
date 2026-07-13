# Trajectory Probe Report

This is a tiny leave-one-out `all` probe over 38 prompt-suite examples. It is a diagnostic scaffold, not a validated classifier.

- Leave-one-out accuracy: 0.76
- Jailbreak true-positive rate: 0.83
- Benign false-positive rate: 0.36
- Leave-one-suite-out accuracy: 0.66
- Leave-one-suite-out jailbreak true-positive rate: 0.71
- Leave-one-suite-out benign false-positive rate: 0.43

## Learned Weights

| feature | weight |
|---|---:|
| surface_risk | 1.235 |
| last_first_cosine | -0.538 |
| hidden_norm | 0.415 |
| hidden_token_drift | 0.254 |
| first_last_drift_delta | 0.241 |
| token_dispersion_final | 0.173 |
| token_dispersion_delta | 0.131 |
| late_to_early_path_ratio | -0.046 |
| early_layer_path | 0.045 |
| layer_step_std | -0.042 |
| layer_step_max | -0.042 |
| late_layer_path | -0.042 |
| layer_displacement | -0.042 |
| layer_path_length | -0.042 |
| layer_step_mean | -0.042 |
| native_attention_entropy | 0.000 |
| native_attention_peak | 0.000 |

## Note

The calibration sweep should use these scores as a candidate `probe` risk source, then compare against surface and mixed risk. Strong probe performance here would still need a larger held-out benchmark.
