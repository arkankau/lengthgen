# Thermodynamic Incremental-Value Audit

This report asks whether thermodynamic features explain residual degradation after simple controls are fitted first.
Train R2 is descriptive; CV R2 is the leave-one-out ridge estimate to reduce overfitting.

| scope | target | n | train simple R2 | train +thermo R2 | train delta R2 | CV simple R2 | CV +thermo R2 | CV delta R2 | best residual thermo | residual abs Spearman | residual Spearman |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| pooled | utility_loss | 240 | 0.761 | 0.781 | 0.020 | 0.748 | 0.758 | 0.010 | basin_margin | 0.142 | -0.142 |
| pooled | coherence | 240 | 0.745 | 0.761 | 0.017 | 0.730 | 0.737 | 0.007 | basin_margin | 0.158 | 0.158 |
| pooled | repetition_collapse | 240 | 0.686 | 0.705 | 0.019 | 0.668 | 0.675 | 0.007 | basin_margin | 0.144 | -0.144 |
| pooled | template_collapse | 240 | 0.155 | 0.163 | 0.008 | 0.089 | 0.066 | -0.023 | steering_alignment | 0.175 | -0.175 |
| pooled | semantic_drift | 240 | 0.727 | 0.745 | 0.019 | 0.715 | 0.721 | 0.006 | native_entropy | 0.104 | 0.104 |
| pooled | degradation_score | 240 | 0.713 | 0.720 | 0.007 | 0.697 | 0.693 | -0.003 | basin_margin | 0.083 | -0.083 |
| pooled | collapse_failure | 240 | 0.644 | 0.659 | 0.015 | 0.623 | 0.622 | -0.001 | steering_alignment | 0.184 | -0.184 |
| within_setting_mean | utility_loss | 240 | 0.646 | 0.930 | 0.284 | 0.282 | -0.073 | -0.355 | native_entropy | 0.411 | -0.023 |
| within_setting_mean | coherence | 240 | 0.613 | 0.928 | 0.315 | 0.210 | -0.096 | -0.307 | basin_entropy | 0.397 | 0.175 |
| within_setting_mean | repetition_collapse | 240 | 0.598 | 0.901 | 0.303 | 0.198 | -0.103 | -0.301 | basin_entropy | 0.408 | 0.008 |
| within_setting_mean | template_collapse | 240 | 0.554 | 0.928 | 0.374 | -0.057 | -0.347 | -0.289 | basin_entropy | 0.466 | -0.161 |
| within_setting_mean | semantic_drift | 240 | 0.786 | 0.954 | 0.168 | 0.638 | 0.530 | -0.108 | steering_alignment | 0.423 | -0.075 |
| within_setting_mean | degradation_score | 240 | 0.720 | 0.916 | 0.196 | 0.418 | 0.160 | -0.258 | basin_entropy | 0.410 | -0.146 |
| within_setting_mean | collapse_failure | 240 | 0.693 | 0.948 | 0.255 | 0.340 | 0.107 | -0.233 | basin_entropy | 0.393 | -0.172 |
