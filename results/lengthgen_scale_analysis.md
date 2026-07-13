# Scale confirmation (8 layers / width 512, ~8x params of 4L/256), complete 32 configs

Data: results/lengthgen/gpu_results_scale.json

# Length-Gen GPU Analysis

Per-token accuracy (mean over seeds). var-collapse = min-layer ratio var@longest/var@train:
`pre` = before the fix (raw collapse); `post` = after the fix (want ~1.0 => fix stabilizes it).
Benefit = PAIRED per-seed tok(fix)-tok(no-fix) at the length where the no-fix baseline breaks.

## argmax (invariant-order)
| PE | fix | 1x | 2x | 3x | 10x | 20x | 50x | em@1x | var-collapse(pre/post) |
|---|---|---|---|---|---|---|---|---|---|
| nope | off | 1.00 | 1.00 | 1.00 | 0.92 | 0.83 | 0.66 | 1.00 | 0.25 / 0.25 |
| nope | on | 1.00 | 1.00 | 0.99 | 0.88 | 0.75 | 0.62 | 1.00 | 0.38 / 0.96 |
- nope: post-LN benefit at 50x = **-0.039** [-0.078, +0.012], 3/4 seeds negative
| rope | off | 1.00 | 0.99 | 0.96 | 0.69 | 0.60 | 0.56 | 1.00 | 0.14 / 0.14 |
| rope | on | 1.00 | 0.99 | 0.97 | 0.72 | 0.60 | 0.53 | 1.00 | 0.57 / 0.99 |
- rope: post-LN benefit at 50x = **-0.034** [-0.141, +0.012], 2/4 seeds negative

## flagret (invariant-order)
| PE | fix | 1x | 2x | 3x | 10x | 20x | 50x | em@1x | var-collapse(pre/post) |
|---|---|---|---|---|---|---|---|---|---|
| nope | off | 1.00 | 1.00 | 0.97 | 0.68 | 0.62 | 0.58 | 1.00 | 0.47 / 0.47 |
| nope | on | 1.00 | 0.96 | 0.89 | 0.68 | 0.65 | 0.56 | 1.00 | 0.54 / 1.00 |
- nope: post-LN benefit at 50x = **-0.021** [-0.043, +0.012], 3/4 seeds negative
| rope | off | 1.00 | 1.00 | 1.00 | 0.66 | 0.61 | 0.58 | 1.00 | 0.41 / 0.41 |
| rope | on | 1.00 | 1.00 | 0.98 | 0.56 | 0.53 | 0.50 | 1.00 | 0.44 / 1.00 |
- rope: post-LN benefit at 50x = **-0.079** [-0.102, -0.051], 4/4 seeds negative

## Verdict
- argmax (invariant): best post-LN benefit where baseline breaks = -0.034
- flagret (invariant): best post-LN benefit where baseline breaks = -0.021

**GENUINE NULL: across order-invariant tasks the fix stabilizes downstream variance (post-collapse ~1.0) yet yields no length-gen benefit (best -0.021); harmful under RoPE. Variance stabilization is decoupled from length generalization -> scopes/contests 2504.02827.**

## Attention vs variance predictor
# Direction A: attention-on-target vs variance as the driver of length-gen failure

## H-A1 / H-A2  (baselines; correlation of accuracy with each candidate across length)
- argmax/nope: corr(acc, attn_tgt)=+0.98  vs  corr(acc, var-ratio)=+0.71
- argmax/nope: corr(acc, attn_tgt)=+0.97  vs  corr(acc, var-ratio)=+0.68
- argmax/nope: corr(acc, attn_tgt)=+0.98  vs  corr(acc, var-ratio)=+0.67
- argmax/nope: corr(acc, attn_tgt)=+0.97  vs  corr(acc, var-ratio)=+0.75
- argmax/rope: corr(acc, attn_tgt)=+0.98  vs  corr(acc, var-ratio)=+0.83
- argmax/rope: corr(acc, attn_tgt)=+0.96  vs  corr(acc, var-ratio)=+0.85
- argmax/rope: corr(acc, attn_tgt)=+0.97  vs  corr(acc, var-ratio)=+0.62
- argmax/rope: corr(acc, attn_tgt)=+0.95  vs  corr(acc, var-ratio)=+0.90
- flagret/nope: corr(acc, attn_tgt)=+0.97  vs  corr(acc, var-ratio)=+0.30
- flagret/nope: corr(acc, attn_tgt)=+0.98  vs  corr(acc, var-ratio)=+0.44
- flagret/nope: corr(acc, attn_tgt)=+0.98  vs  corr(acc, var-ratio)=+0.44
- flagret/nope: corr(acc, attn_tgt)=+0.97  vs  corr(acc, var-ratio)=+0.43
- flagret/rope: corr(acc, attn_tgt)=+0.97  vs  corr(acc, var-ratio)=+0.43
- flagret/rope: corr(acc, attn_tgt)=+0.97  vs  corr(acc, var-ratio)=+0.52
- flagret/rope: corr(acc, attn_tgt)=+0.98  vs  corr(acc, var-ratio)=+0.51
- flagret/rope: corr(acc, attn_tgt)=+0.96  vs  corr(acc, var-ratio)=+0.50

- pooled mean corr(acc, **attn_tgt**) = +0.97
- pooled mean corr(acc, variance-ratio) = +0.60
- **attn_tgt is the better predictor** (H-A2 supported)

## H-A3  (does the fix restore attention on the correct source at long length?)
- argmax/nope: attn_tgt@longest  off=0.506  on=0.268  (fix does NOT restore attention)
- argmax/rope: attn_tgt@longest  off=0.099  on=0.178  (fix restores attention)
- flagret/nope: attn_tgt@longest  off=0.071  on=0.094  (fix does NOT restore attention)
- flagret/rope: attn_tgt@longest  off=0.022  on=0.014  (fix does NOT restore attention)
