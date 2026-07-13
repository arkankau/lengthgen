# Trajectory Probe Report

This is a tiny leave-one-out `latent` probe over 20 prompt-suite examples. It is a diagnostic scaffold, not a validated classifier.

- Leave-one-out accuracy: 0.70
- Jailbreak true-positive rate: 0.83
- Benign false-positive rate: 0.50

## Learned Weights

| feature | weight |
|---|---:|
| hidden_token_drift | 0.485 |
| last_first_cosine | -0.432 |
| hidden_norm | 0.046 |
| layer_path_length | 0.035 |
| layer_displacement | 0.034 |
| native_attention_entropy | 0.000 |
| native_attention_peak | 0.000 |

## Note

The calibration sweep should use these scores as a candidate `probe` risk source, then compare against surface and mixed risk. Strong probe performance here would still need a larger held-out benchmark.
