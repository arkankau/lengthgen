# Reviewer-hardening statistics (layer-aggregation robustness, CIs, sign test)

## 4L/256
# results/lengthgen/gpu_resultsA.json

## (1) attention vs variance as predictor -- robustness to layer aggregation
| attn agg | var agg | corr(acc,attn) [95% CI] | corr(acc,var) [95% CI] | N |
|---|---|---|---|---|
| max | collapse | +0.94 [+0.92,+0.95] | +0.49 [+0.42,+0.55] | 384 |
| mean | mean | +0.90 [+0.89,+0.92] | +0.33 [+0.24,+0.43] | 384 |
| last | last | +0.91 [+0.89,+0.93] | +0.22 [+0.12,+0.31] | 384 |

## (2) variance-fix null: paired benefit across order-invariant (cell,seed) pairs
- pairs N=16, benefit<=0 in 15/16, mean=-0.047 [95% CI -0.062,-0.031]
- max benefit = +0.004; two-sided sign test p=0.0005

## 8L/512
# results/lengthgen/gpu_results_scale.json

## (1) attention vs variance as predictor -- robustness to layer aggregation
| attn agg | var agg | corr(acc,attn) [95% CI] | corr(acc,var) [95% CI] | N |
|---|---|---|---|---|
| max | collapse | +0.93 [+0.91,+0.94] | +0.57 [+0.53,+0.61] | 384 |
| mean | mean | +0.88 [+0.86,+0.90] | +0.22 [+0.10,+0.33] | 384 |
| last | last | +0.74 [+0.69,+0.79] | +0.04 [-0.07,+0.15] | 384 |

## (2) variance-fix null: paired benefit across order-invariant (cell,seed) pairs
- pairs N=16, benefit<=0 in 13/16, mean=-0.043 [95% CI -0.065,-0.022]
- max benefit = +0.012; two-sided sign test p=0.0213
