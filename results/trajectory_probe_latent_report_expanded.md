# Trajectory Probe Report

This is a tiny leave-one-out `latent` probe over 38 prompt-suite examples. It is a diagnostic scaffold, not a validated classifier.

- Leave-one-out accuracy: 0.66
- Jailbreak true-positive rate: 0.75
- Benign false-positive rate: 0.50
- Leave-one-suite-out accuracy: 0.66
- Leave-one-suite-out jailbreak true-positive rate: 0.75
- Leave-one-suite-out benign false-positive rate: 0.50

## Learned Weights

| feature | weight |
|---|---:|
| last_first_cosine | -0.491 |
| hidden_norm | 0.482 |
| hidden_token_drift | 0.333 |
| first_last_drift_delta | 0.314 |
| early_layer_path | 0.145 |
| layer_step_std | -0.079 |
| layer_step_max | -0.079 |
| late_layer_path | -0.079 |
| layer_displacement | -0.079 |
| layer_path_length | -0.079 |
| layer_step_mean | -0.079 |
| token_dispersion_final | 0.070 |
| token_dispersion_delta | 0.015 |
| late_to_early_path_ratio | 0.001 |
| native_attention_entropy | 0.000 |
| native_attention_peak | 0.000 |

## Note

The calibration sweep should use these scores as a candidate `probe` risk source, then compare against surface and mixed risk. Strong probe performance here would still need a larger held-out benchmark.
