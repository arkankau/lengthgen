# Natural Multiple-Choice QA Summary

Stage-1 replicated success: **pass**.
Full-size preregistered result: **pass**.
Full-size seeds: `[0, 1, 2]`.
Competent seeds: `[0, 1, 2]`.
Utility-margin exact seed-level sign-flip p: **0.25**.
Six-seed confirmatory result: **pending/fail**.

| Seed | Full context on no-context failures | Gold only | No context (pool) | Rescue rate | Gate |
|---:|---:|---:|---:|---:|:---:|
| 0 | 0.981 | 0.994 | 0.896 | +0.981 | pass |
| 1 | 0.966 | 0.977 | 0.903 | +0.966 | pass |
| 2 | 0.951 | 0.979 | 0.907 | +0.951 | pass |

| Selector | Margin max-control | 95% CI | Free-choice accuracy delta | 95% CI |
|---|---:|---:|---:|---:|
| source_mass | -0.112 | [-0.188, -0.043] | +0.000 | [+0.000, +0.000] |
| utility_gain | +0.336 | [+0.176, +0.512] | +0.008 | [+0.000, +0.021] |

| Greedy-generation contrast | Mean | 95% CI |
|---|---:|---:|
| First-token accuracy | +0.000 | [+0.000, +0.000] |
| Repetition fraction | +0.000 | [+0.000, +0.000] |

The answer decision is the model's unconstrained top-1 next token; no gold answer token is fed to the model.
A separate greedy-decoding audit keeps the intervention active across multiple generated tokens and reports repetition collapse.
Hierarchical intervals resample competent seeds and paired evaluation examples.
