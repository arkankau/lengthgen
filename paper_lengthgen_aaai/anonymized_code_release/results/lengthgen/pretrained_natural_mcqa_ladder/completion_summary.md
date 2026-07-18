# Natural-QA Length-Ladder Completion

The preregistered natural-QA mechanism test fails.

| Model | Full seeds | Margin, 32 minus 4 | Accuracy, 32 minus 4 | Source mass, 32 minus 4 | Rescue amplification |
|---|---:|---:|---:|---:|---:|
| Qwen2.5-1.5B-Instruct | 2 | -1.036 [-1.397, -0.698] | -0.047 [-0.074, -0.023] | +0.00095 [+0.00014, +0.00203] | -0.179 [-0.352, -0.005] |
| SmolLM2-1.7B-Instruct | 1 | -0.193 [-0.320, -0.066] | -0.102 [-0.156, -0.055] | -0.000074 [-0.000099, -0.000052] | +0.018 [-0.027, +0.066] |

Both models show worse answer margin and accuracy as unrelated natural passages are appended. The hypothesized mechanism does not replicate: Qwen source mass moves in the wrong direction and its rescue effect weakens, while SmolLM2 source mass declines without an increasing rescue effect. The matched-spectrum invariant holds below `5e-7` in both model analyses.

Qwen seed `1` is retained as a preregistered competence-gate failure (`187/192` eligible examples). It is not pooled with the full seeds. Model families are analyzed separately.
