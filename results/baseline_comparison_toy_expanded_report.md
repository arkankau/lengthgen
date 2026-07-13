# Threshold Baseline Comparison

This compares the null-attractor diagnostic against a plain `R(X) >= R_c` threshold rule. The threshold baseline can classify/block, but it does not modify an attention energy landscape and has no attention entropy, spectral gap, or null-basin dynamics.

- Diagnostics: `results/toy_diagnostics_expanded.csv`
- Threshold baseline R_c: 0.237

| method | jailbreak collapse | benign false collapse | max slope | susceptibility peak | low-risk response | high-risk response | jump | thermodynamic observables |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| null_attractor | 0.333 | 0.000 | 6.723 | 0.0166 | 0.075 | 0.999 | 0.924 | yes |
| threshold | 0.708 | 0.071 | 7.084 | 0.2041 | 0.000 | 1.000 | 1.000 | no |

## Reading

A threshold rule is an important control, but it is not the proposed mechanism. The relevant comparison is whether the null-attractor path provides order-parameter, entropy, and spectral-gap evidence of energy-landscape collapse rather than only a binary decision boundary.

## Artifacts

- `results\baseline_comparison_toy_expanded_summary.csv`
- `results\baseline_comparison_toy_expanded_curves.csv`
- `results\baseline_comparison_toy_expanded_curves.svg`
