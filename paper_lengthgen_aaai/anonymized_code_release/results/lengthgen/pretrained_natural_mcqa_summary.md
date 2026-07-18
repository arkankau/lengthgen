# Natural Multiple-Choice QA Summary

Stage-1 replicated success: **pass**.
Full-size preregistered result: **pass**.
Full-size seeds: `[0, 1, 2, 3, 4, 5]`.
Competent seeds: `[0, 1, 2, 3, 4, 5]`.
Utility-margin exact seed-level sign-flip p: **0.03125**.
Six-seed confirmatory result: **pass**.

| Seed | Full context on no-context failures | Gold only | No context (pool) | Rescue rate | Gate |
|---:|---:|---:|---:|---:|:---:|
| 0 | 0.981 | 0.994 | 0.896 | +0.981 | pass |
| 1 | 0.966 | 0.977 | 0.903 | +0.966 | pass |
| 2 | 0.951 | 0.979 | 0.907 | +0.951 | pass |
| 3 | 0.966 | 0.990 | 0.904 | +0.966 | pass |
| 4 | 0.954 | 0.988 | 0.893 | +0.954 | pass |
| 5 | 0.953 | 0.991 | 0.896 | +0.953 | pass |

| Selector | Margin max-control | 95% CI | Free-choice accuracy delta | 95% CI |
|---|---:|---:|---:|---:|
| source_mass | -0.090 | [-0.141, -0.049] | +0.000 | [+0.000, +0.000] |
| utility_gain | +0.378 | [+0.253, +0.520] | +0.005 | [+0.000, +0.013] |

| Greedy-generation contrast | Mean | 95% CI |
|---|---:|---:|
| First-token accuracy | +0.000 | [+0.000, +0.000] |
| Repetition fraction | +0.000 | [+0.000, +0.000] |

The answer decision is the model's unconstrained top-1 next token; no gold answer token is fed to the model.
A separate greedy-decoding audit keeps the intervention active across multiple generated tokens and reports repetition collapse.
Hierarchical intervals resample competent seeds and paired evaluation examples.
