# Threshold Baseline Comparison

This compares the null-attractor diagnostic against a plain `R(X) >= R_c` threshold rule. The threshold baseline can classify/block, but it does not modify an attention energy landscape and has no attention entropy, spectral gap, or null-basin dynamics.

- Diagnostics: `results/hf_diagnostics_expanded.csv`
- Threshold baseline R_c: 0.095

| method | jailbreak collapse | benign false collapse | max slope | susceptibility peak | low-risk response | high-risk response | jump | thermodynamic observables |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| null_attractor | 0.000 | 0.000 | 0.272 | 0.0002 | 0.035 | 0.033 | -0.002 | yes |
| threshold | 1.000 | 0.286 | 10.071 | 0.2500 | 0.250 | 1.000 | 0.750 | no |

## Reading

A threshold rule is an important control, but it is not the proposed mechanism. The relevant comparison is whether the null-attractor path provides order-parameter, entropy, and spectral-gap evidence of energy-landscape collapse rather than only a binary decision boundary.

## Artifacts

- `results\baseline_comparison_tinygpt2_expanded_summary.csv`
- `results\baseline_comparison_tinygpt2_expanded_curves.csv`
- `results\baseline_comparison_tinygpt2_expanded_curves.svg`
