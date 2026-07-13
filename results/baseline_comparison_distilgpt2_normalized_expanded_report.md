# Threshold Baseline Comparison

This compares the null-attractor diagnostic against a plain `R(X) >= R_c` threshold rule. The threshold baseline can classify/block, but it does not modify an attention energy landscape and has no attention entropy, spectral gap, or null-basin dynamics.

- Diagnostics: `results/hf_diagnostics_distilgpt2_normalized_expanded.csv`
- Threshold baseline R_c: 0.556

| method | jailbreak collapse | benign false collapse | max slope | susceptibility peak | low-risk response | high-risk response | jump | thermodynamic observables |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| null_attractor | 0.875 | 0.286 | 9.032 | 0.0077 | 0.558 | 0.999 | 0.441 | yes |
| threshold | 0.708 | 0.071 | 15.742 | 0.2041 | 0.000 | 1.000 | 1.000 | no |

## Reading

A threshold rule is an important control, but it is not the proposed mechanism. The relevant comparison is whether the null-attractor path provides order-parameter, entropy, and spectral-gap evidence of energy-landscape collapse rather than only a binary decision boundary.

## Artifacts

- `results\baseline_comparison_distilgpt2_normalized_expanded_summary.csv`
- `results\baseline_comparison_distilgpt2_normalized_expanded_curves.csv`
- `results\baseline_comparison_distilgpt2_normalized_expanded_curves.svg`
