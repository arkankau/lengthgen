# Exact Qwen Replication

Available seeds: `[0, 1, 2, 3, 4, 5]`; missing: `[]`.
Original seed-0 margin: **+1.882**.
Five new-seed mean: **+0.042**; all positive: **yes**; new-seed-only exact p: **0.0625**.
With five prospective seeds, the smallest attainable two-sided exact sign-flip p-value is 0.0625.
Mean source-max minus control margin: **+0.349** (hierarchical 95% CI [+0.037, +0.982]).
Exact seed-level sign-flip p: **0.03125**.
Prospective success: **pass**.

| Seed | Layer | Heads | Mean margin | Mean accuracy |
|---:|---:|:---|---:|---:|
| 0 | 19 | [3, 1, 0, 2] | +1.882 | +0.113 |
| 1 | 14 | [3, 4, 0, 1] | +0.041 | +0.002 |
| 2 | 14 | [3, 4, 0, 1] | +0.036 | +0.012 |
| 3 | 14 | [3, 0, 4, 1] | +0.053 | +0.018 |
| 4 | 14 | [3, 0, 4, 1] | +0.039 | +0.002 |
| 5 | 14 | [3, 0, 4, 1] | +0.044 | +0.018 |
