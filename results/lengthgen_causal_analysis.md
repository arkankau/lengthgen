# Direction A: attention-on-target vs variance as the driver of length-gen failure

## H-A1 / H-A2  (baselines; correlation of accuracy with each candidate across length)
- argmax/nope: corr(acc, attn_tgt)=+1.00  vs  corr(acc, var-ratio)=+0.76
- argmax/nope: corr(acc, attn_tgt)=+1.00  vs  corr(acc, var-ratio)=+0.86
- argmax/nope: corr(acc, attn_tgt)=+1.00  vs  corr(acc, var-ratio)=+0.77
- argmax/nope: corr(acc, attn_tgt)=+0.99  vs  corr(acc, var-ratio)=+0.79
- argmax/rope: corr(acc, attn_tgt)=+0.99  vs  corr(acc, var-ratio)=+0.85
- argmax/rope: corr(acc, attn_tgt)=+0.98  vs  corr(acc, var-ratio)=+0.79
- argmax/rope: corr(acc, attn_tgt)=+0.97  vs  corr(acc, var-ratio)=+0.84
- argmax/rope: corr(acc, attn_tgt)=+0.99  vs  corr(acc, var-ratio)=+0.89
- flagret/nope: corr(acc, attn_tgt)=+0.97  vs  corr(acc, var-ratio)=+0.34
- flagret/nope: corr(acc, attn_tgt)=+0.96  vs  corr(acc, var-ratio)=+0.28
- flagret/nope: corr(acc, attn_tgt)=+0.97  vs  corr(acc, var-ratio)=+0.27
- flagret/nope: corr(acc, attn_tgt)=+0.96  vs  corr(acc, var-ratio)=+0.41
- flagret/rope: corr(acc, attn_tgt)=+0.95  vs  corr(acc, var-ratio)=+0.43
- flagret/rope: corr(acc, attn_tgt)=+0.95  vs  corr(acc, var-ratio)=+0.38
- flagret/rope: corr(acc, attn_tgt)=+0.96  vs  corr(acc, var-ratio)=+0.37
- flagret/rope: corr(acc, attn_tgt)=+0.96  vs  corr(acc, var-ratio)=+0.42

- pooled mean corr(acc, **attn_tgt**) = +0.97
- pooled mean corr(acc, variance-ratio) = +0.59
- **attn_tgt is the better predictor** (H-A2 supported)

## H-A3  (does the fix restore attention on the correct source at long length?)
- argmax/nope: attn_tgt@longest  off=0.112  on=0.102  (fix does NOT restore attention)
- argmax/rope: attn_tgt@longest  off=0.246  on=0.071  (fix does NOT restore attention)
- flagret/nope: attn_tgt@longest  off=0.057  on=0.037  (fix does NOT restore attention)
- flagret/rope: attn_tgt@longest  off=0.016  on=0.010  (fix does NOT restore attention)
