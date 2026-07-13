# GPT-2 Local Model Upgrade

This note records the first stronger-local-model pass after moving beyond `distilgpt2`.

## Model

- Model: `gpt2`
- Source: Hugging Face public model cache
- Runtime: local CPU
- Hook compatibility: GPT-2 attention path, same intervention implementation
- Layer tested: 8
- Risk source: `probe_latent`

`gpt2` is now cached locally under the Hugging Face cache, so future runs can use `--local-files-only`.

## Smoke Test

Output files:

- `results/gpt2_smoke_probe_latent_grid.csv`
- `results/gpt2_smoke_probe_latent_grid_summary.csv`
- `results/gpt2_smoke_probe_latent_grid_report.md`

The smoke test used one benign and one direct jailbreak prompt. At `R_c=0.60`, benign `m_null` was `0.102` and jailbreak `m_null` was `0.547`, confirming the stronger model path works with the latent probe and null-attractor hook.

## Full R_c=0.60 Run

Output files:

- `results/gpt2_latent_probe_r060_grid.csv`
- `results/gpt2_latent_probe_r060_grid_summary.csv`
- `results/gpt2_latent_probe_r060_grid_report.md`

Aggregate behavior:

| group | mean risk | mean m_null | mean length delta | empty rate |
|---|---:|---:|---:|---:|
| jailbreak | 0.805 | 0.440 | -6.9 | 0.000 |
| benign | 0.335 | 0.175 | -8.0 | 0.000 |

Compared with the `distilgpt2` latent-probe run, `gpt2` preserves generation length much better while retaining a clear jailbreak-vs-benign null-mass separation.

## Threshold Sweep

Output files:

- `results/gpt2_latent_probe_threshold_grid.csv`
- `results/gpt2_latent_probe_threshold_grid_summary.csv`
- `results/gpt2_latent_probe_threshold_grid_report.md`

All rows use layer 8, all heads, calibrated-refusal value, `eta=4.0`, `beta=2.5`, `lambda=0.15`, `mix=0.55`, `phi=positive_logits`, suffix ` In brief,`.

| setting | threshold | jailbreak m_null | benign m_null | separation | jailbreak length delta | benign length delta | empty rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| s001 | 0.42 | 0.492 | 0.241 | 0.251 | -6.7 | -6.6 | 0.000 |
| s002 | 0.50 | 0.468 | 0.211 | 0.257 | -6.7 | -6.6 | 0.000 |
| s003 | 0.60 | 0.440 | 0.175 | 0.265 | -6.9 | -8.0 | 0.000 |
| s004 | 0.70 | 0.409 | 0.125 | 0.284 | -6.4 | -8.5 | 0.000 |

## Current Reading

The best tested `gpt2` operating point is `R_c=0.70`. It gives the strongest null-mass separation in this sweep while keeping empty continuations at zero. This should become the stronger-local-model comparison point against the earlier `distilgpt2` results.
