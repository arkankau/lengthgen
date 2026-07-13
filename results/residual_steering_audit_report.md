# Residual Steering Thermodynamic Audit

This is a different intervention family from null-attention: residual-stream steering with a refusal-minus-unsafe direction.
The audit asks whether native thermodynamic/basin features predict steering-induced collapse or utility loss better than simple knobs.

## Binary Collapse Prediction

| target | group | n | positive rate | best feature | AUROC | Spearman |
|---|---|---:|---:|---|---:|---:|
| collapse_failure | thermo | 32 | 0.000 |  |  |  |
| collapse_failure | simple | 32 | 0.000 |  |  |  |

## Continuous Degradation Prediction

| target | group | n | mean target | best feature | abs Spearman | signed Spearman |
|---|---|---:|---:|---|---:|---:|
| utility_loss | thermo | 32 | 0.006 | native_entropy | 0.274 | 0.274 |
| utility_loss | simple | 32 | 0.006 | layer | 0.180 | -0.180 |
| coherence | thermo | 32 | 0.950 | basin_entropy | 0.228 | -0.228 |
| coherence | simple | 32 | 0.950 | risk | 0.235 | -0.235 |

## Setting Averages

| setting | layer | alpha | mean collapse | mean utility loss | mean coherence |
|---|---:|---:|---:|---:|---:|
| rs001 | 10 | -1.00 | 0.000 | 0.000 | 0.949 |
| rs002 | 10 | -0.50 | 0.000 | 0.000 | 0.949 |
| rs003 | 10 | 0.50 | 0.000 | 0.047 | 0.903 |
| rs004 | 10 | 1.00 | 0.000 | 0.000 | 1.000 |
| rs005 | 16 | -1.00 | 0.000 | 0.000 | 0.949 |
| rs006 | 16 | -0.50 | 0.000 | 0.000 | 0.949 |
| rs007 | 16 | 0.50 | 0.000 | 0.000 | 0.950 |
| rs008 | 16 | 1.00 | 0.000 | 0.000 | 0.950 |
