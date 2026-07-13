# Thermodynamic Steering Audit

Question: do thermodynamic observables predict steering/intervention failures better than simple baselines?

Feature groups:

- `thermo`: `m_null`, entropy, psi, spectral gap, and a collapse proxy `m_null * max(0, 2.5 - entropy)`.
- `simple`: risk, intervention strength, layer, semantic-mode flag, and barrier-mode flag.

Targets are automatic proxies from existing generated continuations; this is a falsification screen, not a safety benchmark.

## Predictor Comparison

| target | group | n | positive rate | best feature | best AUROC | best Spearman |
|---|---|---:|---:|---|---:|---:|
| benign_damage | thermo | 72 | 0.750 | thermo_collapse | 0.684 | 0.276 |
| benign_damage | simple | 72 | 0.750 | semantic_mode | 0.574 | -0.136 |
| jailbreak_unsafe | thermo | 72 | 0.028 | mean_m_null | 0.679 | -0.102 |
| jailbreak_unsafe | simple | 72 | 0.028 | semantic_mode | 0.671 | 0.120 |
| jailbreak_safe_refusal | thermo | 72 | 0.125 | mean_psi | 0.725 | -0.258 |
| jailbreak_safe_refusal | simple | 72 | 0.125 | risk | 0.706 | 0.244 |
| collapse_failure | thermo | 144 | 0.646 | mean_psi | 0.672 | 0.285 |
| collapse_failure | simple | 144 | 0.646 | semantic_mode | 0.576 | -0.154 |

## Continuous Degradation Correlations

| target | group | n | mean target | best feature | abs Spearman | signed Spearman |
|---|---|---:|---:|---|---:|---:|
| benign_utility_loss | thermo | 72 | 0.452 | mean_spectral_gap | 0.289 | 0.289 |
| benign_utility_loss | simple | 72 | 0.452 | risk | 0.292 | -0.292 |
| all_utility_loss | thermo | 144 | 0.473 | thermo_collapse | 0.279 | 0.279 |
| all_utility_loss | simple | 144 | 0.473 | semantic_mode | 0.202 | -0.202 |
| all_coherence | thermo | 144 | 0.496 | mean_m_null | 0.242 | -0.242 |
| all_coherence | simple | 144 | 0.496 | semantic_mode | 0.210 | 0.210 |

## Source-Stratified Binary Checks

| source | target | group | n | positive rate | best feature | best AUROC | best Spearman |
|---|---|---|---:|---:|---|---:|---:|
| intervention_grid_qwen_detail.csv | benign_damage | thermo | 24 | 0.875 | mean_spectral_gap | 0.730 | 0.264 |
| intervention_grid_qwen_detail.csv | benign_damage | simple | 24 | 0.875 | layer_value | 0.786 | 0.378 |
| intervention_grid_qwen_detail.csv | collapse_failure | thermo | 48 | 0.729 | thermo_collapse | 0.626 | 0.195 |
| intervention_grid_qwen_detail.csv | collapse_failure | simple | 48 | 0.729 | semantic_mode | 0.623 | -0.232 |
| intervention_grid_qwen_fixed_detail.csv | benign_damage | thermo | 24 | 1.000 |  |  |  |
| intervention_grid_qwen_fixed_detail.csv | benign_damage | simple | 24 | 1.000 |  |  |  |
| intervention_grid_qwen_fixed_detail.csv | collapse_failure | thermo | 48 | 0.792 | mean_psi | 0.761 | 0.367 |
| intervention_grid_qwen_fixed_detail.csv | collapse_failure | simple | 48 | 0.792 | layer_value | 0.563 | 0.103 |
| intervention_grid_qwen_norepeat_detail.csv | benign_damage | thermo | 24 | 0.375 | mean_m_null | 0.811 | 0.523 |
| intervention_grid_qwen_norepeat_detail.csv | benign_damage | simple | 24 | 0.375 | layer_value | 0.633 | -0.258 |
| intervention_grid_qwen_norepeat_detail.csv | collapse_failure | thermo | 48 | 0.417 | mean_m_null | 0.720 | 0.375 |
| intervention_grid_qwen_norepeat_detail.csv | collapse_failure | simple | 48 | 0.417 | semantic_mode | 0.600 | -0.209 |

## Setting Summary

| source | setting | mode | phi | mean m_null | benign damage | jailbreak unsafe | jailbreak safe refusal | utility loss | collapse failure |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| intervention_grid_qwen_detail.csv | s001 | zero_or_context | other | 0.847 | 1.000 | 0.000 | 0.000 | 0.762 | 1.000 |
| intervention_grid_qwen_detail.csv | s002 | semantic | other | 0.826 | 1.000 | 0.000 | 0.000 | 0.647 | 0.625 |
| intervention_grid_qwen_detail.csv | s003 | semantic | other | 0.827 | 1.000 | 0.000 | 0.000 | 0.621 | 0.625 |
| intervention_grid_qwen_detail.csv | s004 | zero_or_context | other | 0.405 | 1.000 | 0.000 | 0.000 | 0.445 | 0.750 |
| intervention_grid_qwen_detail.csv | s005 | semantic | other | 0.427 | 1.000 | 0.000 | 0.000 | 0.667 | 1.000 |
| intervention_grid_qwen_detail.csv | s006 | semantic | other | 0.439 | 0.250 | 0.250 | 0.000 | 0.120 | 0.375 |
| intervention_grid_qwen_fixed_detail.csv | s001 | zero_or_context | other | 0.271 | 1.000 | 0.000 | 0.000 | 0.742 | 0.875 |
| intervention_grid_qwen_fixed_detail.csv | s002 | semantic | other | 0.244 | 1.000 | 0.000 | 0.500 | 0.613 | 0.875 |
| intervention_grid_qwen_fixed_detail.csv | s003 | semantic | other | 0.246 | 1.000 | 0.000 | 0.500 | 0.670 | 0.750 |
| intervention_grid_qwen_fixed_detail.csv | s004 | zero_or_context | other | 0.296 | 1.000 | 0.000 | 0.250 | 0.580 | 0.750 |
| intervention_grid_qwen_fixed_detail.csv | s005 | semantic | other | 0.297 | 1.000 | 0.000 | 0.250 | 0.538 | 0.750 |
| intervention_grid_qwen_fixed_detail.csv | s006 | semantic | other | 0.251 | 1.000 | 0.000 | 0.000 | 0.601 | 0.750 |
| intervention_grid_qwen_norepeat_detail.csv | s001 | zero_or_context | other | 0.293 | 0.500 | 0.000 | 0.000 | 0.378 | 0.625 |
| intervention_grid_qwen_norepeat_detail.csv | s002 | semantic | other | 0.248 | 0.250 | 0.000 | 0.250 | 0.096 | 0.250 |
| intervention_grid_qwen_norepeat_detail.csv | s003 | semantic | other | 0.233 | 0.000 | 0.250 | 0.250 | 0.048 | 0.125 |
| intervention_grid_qwen_norepeat_detail.csv | s004 | zero_or_context | other | 0.290 | 0.500 | 0.000 | 0.250 | 0.193 | 0.500 |
| intervention_grid_qwen_norepeat_detail.csv | s005 | semantic | other | 0.286 | 0.250 | 0.000 | 0.000 | 0.213 | 0.375 |
| intervention_grid_qwen_norepeat_detail.csv | s006 | semantic | other | 0.279 | 0.750 | 0.000 | 0.000 | 0.208 | 0.625 |

## Decision Rule

The pivot remains alive only if the `thermo` group beats the `simple` group on at least one meaningful failure target and the winning feature is interpretable.
