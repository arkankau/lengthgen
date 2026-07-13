# Latent Probe Risk Upgrade

This note records the first generation-level run where the intervention uses a latent trajectory probe for `R(X)` instead of the original surface keyword heuristic.

## What changed

- Added `thermosafety.risk_provider.risk_scores_for_cases`.
- Added `--risk-source {surface,trajectory,mixed,probe_all,probe_latent}` to the intervention runner and grid evaluator.
- `probe_latent` extracts hidden-state trajectories from the loaded HF model and fits a small calibration probe using only latent features, excluding `surface_risk`.
- The existing leave-one-out probe scripts remain the validation path; the intervention runner uses batch-calibrated scores because it needs a stable control signal for the selected experiment batch.

## Full s007 latent-probe pass

Command output:

- Detail rows: `results/latent_probe_s007_grid.csv`
- Summary: `results/latent_probe_s007_grid_summary.csv`
- Report: `results/latent_probe_s007_grid_report.md`

Aggregate behavior at the old `s007` threshold `R_c=0.26`:

| group | mean risk | mean m_null | mean length delta | empty rate |
|---|---:|---:|---:|---:|
| jailbreak | 0.780 | 0.439 | -29.3 | 0.000 |
| benign | 0.377 | 0.286 | -31.9 | 0.000 |

The latent probe does drive stronger attraction on jailbreak prompts, but the old surface-risk threshold is too permissive for the new risk distribution.

## Focused threshold sweep

Command output:

- Detail rows: `results/latent_probe_threshold_grid.csv`
- Summary: `results/latent_probe_threshold_grid_summary.csv`
- Report: `results/latent_probe_threshold_grid_report.md`

All rows use the current behavior-selected attractor design: layer 5, all heads, calibrated-refusal value, `eta=4.0`, `beta=2.5`, `lambda=0.15`, `mix=0.55`, `phi=positive_logits`, suffix ` In brief,`.

| setting | threshold | jailbreak m_null | benign m_null | separation | jailbreak length delta | benign length delta | empty rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| s001 | 0.26 | 0.439 | 0.286 | 0.153 | -29.3 | -31.9 | 0.000 |
| s002 | 0.42 | 0.425 | 0.189 | 0.236 | -28.0 | -31.6 | 0.000 |
| s003 | 0.60 | 0.393 | 0.103 | 0.289 | -27.8 | -29.1 | 0.000 |
| s004 | 0.75 | 0.304 | 0.027 | 0.277 | -24.2 | -24.6 | 0.000 |

## Interpretation

The latent trajectory `R(X)` path is now wired into the actual intervention, not only the post-hoc diagnostic. The first calibration result favors `R_c=0.60`: it reduces benign attraction while preserving a meaningful jailbreak null-mass increase. This is weaker than the best surface-risk separation, so it should be presented as a mechanism upgrade and calibration target, not as a finished safety classifier.
