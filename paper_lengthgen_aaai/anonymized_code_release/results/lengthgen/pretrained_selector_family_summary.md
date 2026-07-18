# Pretrained Selector Family Summary

Cross-family selector result: **heterogeneous_or_incomplete**.

| Model | Seeds | Top selector | Top effect | Utility rank |
|---|:---|---|---:|---:|
| EleutherAI/pythia-1.4b | [0, 1, 2] | utility_gain | +0.519 | 1 |
| HuggingFaceTB/SmolLM2-1.7B | [0, 1, 2] | utility_gain | +1.253 | 1 |
| Qwen/Qwen2.5-1.5B | [0, 1, 2] | utility_gap | +1.493 | 2 |

Each model uses the same calibration budget, held-out evaluation size, and selector set.
A universal selector is claimed only when at least three complete families agree.
