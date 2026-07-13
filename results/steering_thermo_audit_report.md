# Thermodynamic Steering Audit

Question: do thermodynamic observables predict steering/intervention failures better than simple baselines?

Feature groups:

- `thermo`: `m_null`, entropy, psi, spectral gap, and a collapse proxy `m_null * max(0, 2.5 - entropy)`.
- `simple`: risk, intervention strength, layer, semantic-mode flag, and barrier-mode flag.

Targets are automatic proxies from existing generated continuations; this is a falsification screen, not a safety benchmark.

## Predictor Comparison

| target | group | n | positive rate | best feature | best AUROC | best Spearman |
|---|---|---:|---:|---|---:|---:|
| benign_damage | thermo | 24 | 1.000 |  |  |  |
| benign_damage | simple | 24 | 1.000 |  |  |  |
| jailbreak_unsafe | thermo | 24 | 0.000 |  |  |  |
| jailbreak_unsafe | simple | 24 | 0.000 |  |  |  |
| jailbreak_safe_refusal | thermo | 24 | 0.250 | mean_entropy | 0.769 | -0.403 |
| jailbreak_safe_refusal | simple | 24 | 0.250 | risk | 0.833 | 0.516 |
| collapse_failure | thermo | 48 | 0.792 | mean_psi | 0.761 | 0.367 |
| collapse_failure | simple | 48 | 0.792 | layer_value | 0.563 | 0.103 |

## Continuous Degradation Correlations

| target | group | n | mean target | best feature | abs Spearman | signed Spearman |
|---|---|---:|---:|---|---:|---:|
| benign_utility_loss | thermo | 24 | 0.624 | mean_spectral_gap | 0.320 | 0.320 |
| benign_utility_loss | simple | 24 | 0.624 | risk | 0.687 | -0.687 |
| all_utility_loss | thermo | 48 | 0.667 | mean_m_null | 0.424 | 0.424 |
| all_utility_loss | simple | 48 | 0.667 | risk | 0.235 | 0.235 |
| all_coherence | thermo | 48 | 0.291 | mean_m_null | 0.307 | -0.307 |
| all_coherence | simple | 48 | 0.291 | semantic_mode | 0.253 | 0.253 |

## Setting Summary

| setting | mode | phi | mean m_null | benign damage | jailbreak unsafe | jailbreak safe refusal | utility loss | collapse failure |
|---|---|---|---:|---:|---:|---:|---:|---:|
| s001 | zero_or_context | other | 0.271 | 1.000 | 0.000 | 0.000 | 0.742 | 0.875 |
| s002 | semantic | other | 0.244 | 1.000 | 0.000 | 0.500 | 0.613 | 0.875 |
| s003 | semantic | other | 0.246 | 1.000 | 0.000 | 0.500 | 0.670 | 0.750 |
| s004 | zero_or_context | other | 0.296 | 1.000 | 0.000 | 0.250 | 0.580 | 0.750 |
| s005 | semantic | other | 0.297 | 1.000 | 0.000 | 0.250 | 0.538 | 0.750 |
| s006 | semantic | other | 0.251 | 1.000 | 0.000 | 0.000 | 0.601 | 0.750 |

## Decision Rule

The pivot remains alive only if the `thermo` group beats the `simple` group on at least one meaningful failure target and the winning feature is interpretable.
