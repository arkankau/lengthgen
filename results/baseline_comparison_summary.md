# Baseline Comparison Summary

Plain thresholding is a classification control. It does not patch attention logits or produce attention entropy/spectral-gap evidence of null-basin dynamics.

| setting | method | jailbreak collapse | benign false collapse | max slope | susceptibility peak | low-risk response | high-risk response | jump | thermodynamic observables |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| toy | null_attractor | 0.333 | 0.000 | 6.723 | 0.0166 | 0.075 | 0.999 | 0.924 | yes |
| toy | threshold | 0.708 | 0.071 | 7.084 | 0.2041 | 0.000 | 1.000 | 1.000 | no |
| tiny-gpt2 diagnostic | null_attractor | 0.000 | 0.000 | 0.272 | 0.0002 | 0.035 | 0.033 | -0.002 | yes |
| tiny-gpt2 diagnostic | threshold | 1.000 | 0.286 | 10.071 | 0.2500 | 0.250 | 1.000 | 0.750 | no |
| distilgpt2 normalized diagnostic | null_attractor | 0.875 | 0.286 | 9.032 | 0.0077 | 0.558 | 0.999 | 0.441 | yes |
| distilgpt2 normalized diagnostic | threshold | 0.708 | 0.071 | 15.742 | 0.2041 | 0.000 | 1.000 | 1.000 | no |

## Takeaway

Thresholding can produce a sharper binary decision curve, but that is exactly why it is only a baseline. The null-attractor mechanism must be judged by whether it creates an attention-level order parameter with meaningful entropy and spectral-gap changes, not by whether it merely imitates `R(X) >= R_c`.
