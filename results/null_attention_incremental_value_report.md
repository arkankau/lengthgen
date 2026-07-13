# Null-Attention Incremental-Value Audit

This report asks whether null-attention thermodynamic observables add predictive value after simple controls are fitted first.
CV R2 is leave-one-out ridge R2; train R2 is descriptive.

| scope | target | n | target mean | train simple R2 | train +thermo R2 | train delta R2 | CV simple R2 | CV +thermo R2 | CV delta R2 | best residual thermo | residual abs Spearman | residual Spearman |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| pooled | benign_damage | 72 | 0.750 | 0.058 | 0.108 | 0.050 | -0.041 | -0.068 | -0.027 | mean_m_null | 0.144 | 0.144 |
| source:intervention_grid_qwen_detail.csv | benign_damage | 24 | 0.875 | 0.220 | 0.789 | 0.570 | -0.093 | -0.089 | 0.004 | thermo_collapse | 0.551 | -0.551 |
| source:intervention_grid_qwen_fixed_detail.csv | benign_damage | 24 | 1.000 |  |  |  |  |  |  |  |  |  |
| source:intervention_grid_qwen_norepeat_detail.csv | benign_damage | 24 | 0.375 | 0.162 | 0.678 | 0.516 | -0.188 | 0.033 | 0.222 | mean_m_null | 0.376 | 0.376 |
| pooled | jailbreak_unsafe | 72 | 0.028 | 0.025 | 0.055 | 0.030 | -0.061 | -0.110 | -0.048 | mean_m_null | 0.250 | 0.250 |
| source:intervention_grid_qwen_detail.csv | jailbreak_unsafe | 24 | 0.042 | 0.089 | 0.291 | 0.201 | -0.199 | -0.210 | -0.012 | mean_spectral_gap | 0.561 | 0.561 |
| source:intervention_grid_qwen_fixed_detail.csv | jailbreak_unsafe | 24 | 0.000 |  |  |  |  |  |  |  |  |  |
| source:intervention_grid_qwen_norepeat_detail.csv | jailbreak_unsafe | 24 | 0.042 | 0.086 | 0.152 | 0.066 | -0.196 | -0.269 | -0.074 | thermo_collapse | 0.354 | 0.354 |
| pooled | jailbreak_safe_refusal | 72 | 0.125 | 0.085 | 0.420 | 0.335 | 0.002 | 0.277 | 0.275 | mean_spectral_gap | 0.387 | -0.387 |
| source:intervention_grid_qwen_detail.csv | jailbreak_safe_refusal | 24 | 0.000 |  |  |  |  |  |  |  |  |  |
| source:intervention_grid_qwen_fixed_detail.csv | jailbreak_safe_refusal | 24 | 0.250 | 0.391 | 0.512 | 0.121 | 0.121 | 0.035 | -0.087 | mean_entropy | 0.210 | -0.210 |
| source:intervention_grid_qwen_norepeat_detail.csv | jailbreak_safe_refusal | 24 | 0.125 | 0.026 | 0.677 | 0.651 | -0.352 | -0.097 | 0.255 | mean_spectral_gap | 0.372 | -0.372 |
| pooled | collapse_failure | 144 | 0.646 | 0.037 | 0.152 | 0.114 | -0.015 | 0.055 | 0.069 | mean_entropy | 0.069 | 0.069 |
| source:intervention_grid_qwen_detail.csv | collapse_failure | 48 | 0.729 | 0.071 | 0.446 | 0.375 | -0.092 | -0.024 | 0.068 | mean_entropy | 0.224 | 0.224 |
| source:intervention_grid_qwen_fixed_detail.csv | collapse_failure | 48 | 0.792 | 0.019 | 0.370 | 0.351 | -0.138 | 0.148 | 0.287 | mean_entropy | 0.273 | 0.273 |
| source:intervention_grid_qwen_norepeat_detail.csv | collapse_failure | 48 | 0.417 | 0.091 | 0.298 | 0.207 | -0.086 | 0.015 | 0.101 | mean_spectral_gap | 0.358 | -0.358 |
| pooled | utility_loss | 144 | 0.473 | 0.075 | 0.214 | 0.139 | 0.028 | 0.137 | 0.109 | thermo_collapse | 0.169 | 0.169 |
| source:intervention_grid_qwen_detail.csv | utility_loss | 48 | 0.521 | 0.222 | 0.651 | 0.429 | 0.088 | 0.092 | 0.005 | thermo_collapse | 0.116 | 0.116 |
| source:intervention_grid_qwen_fixed_detail.csv | utility_loss | 48 | 0.667 | 0.076 | 0.352 | 0.276 | -0.084 | 0.114 | 0.198 | mean_psi | 0.243 | 0.243 |
| source:intervention_grid_qwen_norepeat_detail.csv | utility_loss | 48 | 0.232 | 0.128 | 0.623 | 0.496 | -0.048 | 0.440 | 0.489 | mean_spectral_gap | 0.317 | -0.317 |
| pooled | coherence | 144 | 0.496 | 0.076 | 0.208 | 0.132 | 0.029 | 0.131 | 0.102 | thermo_collapse | 0.185 | -0.185 |
| source:intervention_grid_qwen_detail.csv | coherence | 48 | 0.437 | 0.239 | 0.638 | 0.398 | 0.109 | 0.103 | -0.007 | thermo_collapse | 0.096 | -0.096 |
| source:intervention_grid_qwen_fixed_detail.csv | coherence | 48 | 0.291 | 0.071 | 0.350 | 0.279 | -0.090 | 0.109 | 0.200 | mean_psi | 0.273 | -0.273 |
| source:intervention_grid_qwen_norepeat_detail.csv | coherence | 48 | 0.760 | 0.124 | 0.609 | 0.485 | -0.053 | 0.414 | 0.467 | thermo_collapse | 0.267 | -0.267 |
