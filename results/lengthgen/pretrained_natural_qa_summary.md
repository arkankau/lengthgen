# Pretrained Natural-QA Summary

Preregistered success rule: **fail**.
Multi-evidence trigger: **no**.
Seeds passing the untouched competence gate: `[0]`.

| Seed | Main acc. | Gold-only acc. | No-context acc. | Context gain | Gate |
|---:|---:|---:|---:|---:|:---:|
| 0 | 0.500 | 0.562 | 0.109 | +0.391 | pass |
| 1 | 0.453 | 0.469 | 0.094 | +0.359 | fail |
| 2 | 0.422 | 0.500 | 0.031 | +0.391 | fail |

| Selector | Source max minus matched control | Resampled 95% CI |
|---|---:|---:|
| source_mass | +0.556 | [+0.332, +0.811] |
| utility_gain | +2.213 | [+1.795, +2.631] |
| utility minus source-mass | +1.657 | [+1.255, +2.057] |

Selector effects are diagnostic over gate-passing seeds only. When one seed passes, the intervals resample paired examples within that seed and do not establish cross-seed generality.

The competence gate is evaluated before calibration or intervention. Multi-evidence QA is attempted only if at least two untouched single-evidence runs pass and the held-out causal result satisfies the full preregistered rule.
