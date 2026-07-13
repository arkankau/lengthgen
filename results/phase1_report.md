# Phase 1 Null-Attractor Toy Report

This report summarizes a mechanism test, not a validated LLM defense. The toy risk functional changes the attention energy landscape, then `m_null` measures whether attention collapses into the appended null slot.

## Operating Region

At the default operating point, benign-complex collapse rate is 0.00, while direct-jailbreak collapse rate is 1.00.

| suite | n | mean risk | mean m_null | collapse rate | entropy | spectral gap |
|---|---:|---:|---:|---:|---:|---:|
| benign | 4 | 0.110 | 0.094 | 0.000 | 2.370 | 0.963 |
| benign_complex | 4 | 0.089 | 0.082 | 0.000 | 2.496 | 0.968 |
| direct_jailbreak | 4 | 0.666 | 0.917 | 1.000 | 0.353 | 0.926 |
| long_context_jailbreak | 4 | 0.555 | 0.553 | 0.500 | 1.522 | 0.948 |
| obfuscated_jailbreak | 4 | 0.459 | 0.498 | 0.500 | 1.625 | 0.951 |

## Figures

- `results/figures/m_null_vs_risk.svg`
- `results/figures/collapse_rate_by_suite.svg`
- `results/figures/entropy_by_suite.svg`
- `results/figures/spectral_gap_by_suite.svg`

## Artifacts

- Diagnostics: `results/toy_diagnostics.csv`
- Risk-threshold sweep: `results/threshold_sweep.csv`
- One-factor ablation sweep: `results/ablation_sweep.csv`

## Limitations

- The current `R(X)` is a transparent heuristic and should be replaced by a latent trajectory probe.
- Collapse here is diagnostic attention collapse, not an in-layer generation intervention.
- Prompt examples are intentionally non-operational and benchmark-safe.
