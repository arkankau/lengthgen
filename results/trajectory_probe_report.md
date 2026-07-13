# Trajectory Probe Report

This is a tiny leave-one-out probe over 20 prompt-suite examples. It is a diagnostic scaffold, not a validated classifier.

- Leave-one-out accuracy: 0.75
- Jailbreak true-positive rate: 0.83
- Benign false-positive rate: 0.38

## Learned Weights

| feature | weight |
|---|---:|
| surface_risk | 1.837 |
| last_first_cosine | -0.347 |
| hidden_token_drift | 0.265 |
| layer_path_length | 0.120 |
| layer_displacement | 0.120 |
| hidden_norm | -0.093 |
| native_attention_entropy | 0.000 |
| native_attention_peak | 0.000 |

## Note

The calibration sweep should use these scores as a candidate `probe` risk source, then compare against surface and mixed risk. Strong probe performance here would still need a larger held-out benchmark.
