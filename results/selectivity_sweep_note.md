# Selectivity Sweep Note

This note records the first gentler Phase 4 tuning pass. The goal is not to maximize collapse. The goal is to preserve a risk-conditioned attention order parameter while reducing benign generation damage.

## Why the Selectivity Objective Exists

Raw `m_null` is not enough. A setting can produce very high null mass simply by making the intervention blunt across many prompts. That would look strong mechanistically but fail the central criterion: the null basin should preferentially attract high-risk trajectories while leaving benign trajectories comparatively intact.

The selectivity ranking therefore uses four signals together:

- Reward: jailbreak-suite `m_null` minus benign-suite `m_null`
- Penalize: benign empty-continuation rate
- Penalize: benign length shrinkage versus baseline
- Inspect separately: jailbreak empty-continuation rate, because some high-risk collapse is expected but broad blanking is not yet a defense result

This turns the tuning question into: which setting best separates high-risk and benign trajectories without merely suppressing everything?

## Broad Sweep

Broad sampled sweep:

- Prompt sample: 2 cases per suite
- Layers: `5`, `4,5`
- Thresholds: `0.26`, `0.34`, `0.42`, `0.50`
- `eta_null`: `2.5`, `3.0`, `3.5`, `4.0`
- `beta_collapse`: `1.5`, `2.5`
- `kappa`: `18.0`

Top sampled settings favored single layer `5`, high `eta_null=4.0`, and `beta_collapse=2.5`. This improved selectivity relative to the previous `4,5` candidate by lowering benign `m_null` and reducing benign length impact.

| setting | layers | threshold | eta | beta | score | separation | jailbreak m_null | benign m_null | jailbreak empty | benign empty | jailbreak len delta | benign len delta |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| s028 | 5 | 0.34 | 4.0 | 2.5 | 0.387 | 0.477 | 0.508 | 0.031 | 0.200 | 0.000 | -13.1 | -9.0 |
| s030 | 5 | 0.42 | 4.0 | 2.5 | 0.379 | 0.469 | 0.495 | 0.026 | 0.200 | 0.000 | -13.6 | -9.0 |
| s026 | 5 | 0.26 | 4.0 | 2.5 | 0.378 | 0.474 | 0.544 | 0.070 | 0.200 | 0.000 | -10.7 | -9.7 |

## Full Local Validation

The best single-layer family was then validated on all 38 local prompt cases.

| threshold | layers | eta | beta | score | separation | jailbreak m_null | benign m_null | jailbreak empty | benign empty | jailbreak len delta | benign len delta |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.26 | 5 | 4.0 | 2.5 | 0.359 | 0.456 | 0.507 | 0.051 | 0.150 | 0.000 | -8.4 | -9.7 |
| 0.34 | 5 | 4.0 | 2.5 | 0.289 | 0.383 | 0.413 | 0.030 | 0.183 | 0.000 | -10.9 | -9.4 |
| 0.42 | 5 | 4.0 | 2.5 | 0.232 | 0.326 | 0.353 | 0.027 | 0.183 | 0.000 | -10.8 | -9.4 |

## Current Operating Point

Current candidate:

- Layer: `5`
- `risk_threshold`: `0.26`
- `eta_null`: `4.0`
- `beta_collapse`: `2.5`
- `kappa`: `18.0`

Compared with the earlier `4,5` candidate, this is more selective: it keeps benign empty-continuation rate at zero, lowers benign null mass, and reduces benign length damage while retaining strong high-risk null mass.

## Caveat

This is still a mechanism and selectivity result, not a defense result. The next milestone is manual generation review plus ASR/FRR-style evaluation. The operating point is worth carrying forward because it shows a cleaner attention-level separation, not because it proves robust jailbreak prevention.
