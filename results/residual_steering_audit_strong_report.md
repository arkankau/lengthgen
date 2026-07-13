# Residual Steering Thermodynamic Audit

This is a different intervention family from null-attention: residual-stream steering with a refusal-minus-unsafe direction.
The audit asks whether native thermodynamic/basin features predict steering-induced collapse or utility loss better than simple knobs.

## Binary Collapse Prediction

| target | group | n | positive rate | best feature | AUROC | Spearman |
|---|---|---:|---:|---|---:|---:|
| collapse_failure | thermo | 48 | 0.000 |  |  |  |
| collapse_failure | simple | 48 | 0.000 |  |  |  |

## Continuous Degradation Prediction

| target | group | n | mean target | best feature | abs Spearman | signed Spearman |
|---|---|---:|---:|---|---:|---:|
| utility_loss | thermo | 48 | 0.013 | native_specific_heat | 0.358 | 0.358 |
| utility_loss | simple | 48 | 0.013 | alpha | 0.175 | 0.175 |
| coherence | thermo | 48 | 0.952 | basin_margin | 0.330 | -0.330 |
| coherence | simple | 48 | 0.952 | risk | 0.110 | -0.110 |

## Setting Averages

| setting | layer | alpha | mean collapse | mean utility loss | mean coherence |
|---|---:|---:|---:|---:|---:|
| rs001 | 10 | -8.00 | 0.000 | 0.000 | 0.949 |
| rs002 | 10 | -4.00 | 0.000 | 0.000 | 0.982 |
| rs003 | 10 | -2.00 | 0.000 | 0.000 | 0.949 |
| rs004 | 10 | 2.00 | 0.000 | 0.067 | 0.900 |
| rs005 | 10 | 4.00 | 0.000 | 0.067 | 0.933 |
| rs006 | 10 | 8.00 | 0.000 | 0.000 | 1.000 |
| rs007 | 16 | -8.00 | 0.000 | 0.000 | 0.967 |
| rs008 | 16 | -4.00 | 0.000 | 0.000 | 0.949 |
| rs009 | 16 | -2.00 | 0.000 | 0.000 | 0.950 |
| rs010 | 16 | 2.00 | 0.000 | 0.000 | 0.950 |
| rs011 | 16 | 4.00 | 0.000 | 0.019 | 0.931 |
| rs012 | 16 | 8.00 | 0.000 | 0.000 | 0.967 |
