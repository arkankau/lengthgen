# Phase-Transition Analysis

This report analyzes null-attractor behavior as a mechanism test. It does not claim a working LLM defense or an in-layer intervention.

- Diagnostics: `results/hf_diagnostics_distilgpt2_normalized_expanded.csv`
- Estimated critical risk: 0.495
- Max finite slope d(m_null)/dR: 9.032
- Susceptibility peak risk: 0.518
- Susceptibility proxy peak var(m_null): 0.0077
- Low-risk mean m_null: 0.558
- High-risk mean m_null: 0.999
- Order-parameter jump: 0.441
- Suite universality gap: 0.022

## Artifacts

- `results\phase_transition_distilgpt2_normalized_expanded_bins.csv`
- `results\phase_transition_distilgpt2_normalized_expanded_suite_curves.csv`
- `results\phase_transition_distilgpt2_normalized_expanded_m_null_vs_risk.svg`
- `results\phase_transition_distilgpt2_normalized_expanded_susceptibility.svg`
- `results\phase_transition_distilgpt2_normalized_expanded_entropy_vs_risk.svg`
- `results\phase_transition_distilgpt2_normalized_expanded_spectral_gap_vs_risk.svg`

## Interpretation Guardrail

The key claim to test is not threshold classification. The relevant evidence is whether `m_null` behaves like an order parameter as `R(X)` crosses a critical region, and whether entropy/spectral-gap changes are consistent with collapse into an absorbing null basin.
