# Trajectory Probe Report

This is a tiny leave-one-out `latent` probe over 38 prompt-suite examples. It is a diagnostic scaffold, not a validated classifier.

- Leave-one-out accuracy: 0.76
- Jailbreak true-positive rate: 0.83
- Benign false-positive rate: 0.36
- Leave-one-suite-out accuracy: 0.71
- Leave-one-suite-out jailbreak true-positive rate: 0.83
- Leave-one-suite-out benign false-positive rate: 0.50

## Learned Weights

| feature | weight |
|---|---:|
| late_to_early_path_ratio | 0.632 |
| early_layer_path | -0.288 |
| layer_step_max | -0.277 |
| layer_step_std | -0.255 |
| last_first_cosine | 0.225 |
| layer_displacement | 0.186 |
| layer_step_mean | -0.169 |
| layer_path_length | -0.169 |
| hidden_norm | 0.159 |
| first_last_drift_delta | 0.146 |
| hidden_token_drift | 0.123 |
| token_dispersion_final | -0.122 |
| token_dispersion_delta | -0.068 |
| late_layer_path | -0.036 |
| native_attention_entropy | 0.000 |
| native_attention_peak | 0.000 |

## Note

The calibration sweep should use these scores as a candidate `probe` risk source, then compare against surface and mixed risk. Strong probe performance here would still need a larger held-out benchmark.
