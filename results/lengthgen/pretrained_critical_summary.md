# Pretrained Critical Experiment Summary

The gates below were fixed in `pretrained_critical_preregistration.json` before these GPU runs.

## Format Replication

Gate: **fail**; model=Qwen/Qwen2.5-1.5B; format=equals_newline; invariant error=4.77e-07.

| N | baseline acc | max-control dacc | max-control dmargin | source-min dmargin |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 0.164 | +0.086 | +1.349 | -0.794 |
| 20 | 0.203 | +0.047 | +1.536 | -0.265 |
| 80 | 0.023 | +0.008 | +0.353 | -0.073 |

## Held-out Format Replication

Gate: **fail**; pilot selected=arrow_newline from ['colon_semicolon', 'arrow_newline', 'is_newline']; full-run competence=fail; positive max-control cells=3/3; negative source-min cells=3/3.

- N=5: baseline=0.156, max-control dmargin=+4.633, source-min dmargin=-1.086.
- N=20: baseline=0.117, max-control dmargin=+3.558, source-min dmargin=-0.893.
- N=80: baseline=0.008, max-control dmargin=+0.674, source-min dmargin=-0.240.

## Llama-family Replication

Gate: **fail**; model=HuggingFaceTB/SmolLM2-1.7B; N=5 pilot accuracy=0.594; positive max-control cells=0/3; negative source-min competent cells=2/2.

- N=5: baseline=0.945, max-control dmargin=-0.018, source-min dmargin=-0.133.
- N=20: baseline=0.516, max-control dmargin=-0.199, source-min dmargin=-0.190.
- N=80: baseline=0.023, max-control dmargin=-0.056, source-min dmargin=-0.012.

## Pretrained Utility Gap

- **Qwen/Qwen2.5-1.5B**: mean source-max Spearman=+0.832; directional gate=pass.
  - N=5 source_max: exact=+0.357, first-order=+0.346, Spearman=+0.798, sign=0.750, MAE residual=0.232.
  - N=5 source_min: exact=-0.574, first-order=-0.403, Spearman=+0.710, sign=0.734, MAE residual=0.448.
  - N=20 source_max: exact=+0.844, first-order=+0.628, Spearman=+0.866, sign=0.781, MAE residual=0.427.
  - N=20 source_min: exact=-0.655, first-order=-0.318, Spearman=+0.817, sign=0.797, MAE residual=0.567.
- **Qwen/Qwen2.5-1.5B**: mean source-max Spearman=+0.898; directional gate=pass.
  - N=5 source_max: exact=+0.648, first-order=+0.996, Spearman=+0.881, sign=0.797, MAE residual=0.505.
  - N=5 source_min: exact=-0.604, first-order=-0.550, Spearman=+0.840, sign=0.812, MAE residual=0.301.
  - N=20 source_max: exact=+0.832, first-order=+0.698, Spearman=+0.916, sign=0.844, MAE residual=0.333.
  - N=20 source_min: exact=-0.569, first-order=-0.292, Spearman=+0.789, sign=0.766, MAE residual=0.352.
- **Qwen/Qwen2.5-1.5B**: mean source-max Spearman=+0.866; directional gate=pass.
  - N=5 source_max: exact=+0.630, first-order=+0.602, Spearman=+0.916, sign=0.844, MAE residual=0.252.
  - N=5 source_min: exact=-0.285, first-order=-0.206, Spearman=+0.612, sign=0.609, MAE residual=0.375.
  - N=20 source_max: exact=+0.814, first-order=+0.565, Spearman=+0.817, sign=0.812, MAE residual=0.520.
  - N=20 source_min: exact=-0.522, first-order=-0.244, Spearman=+0.805, sign=0.672, MAE residual=0.481.
- **EleutherAI/pythia-1.4b**: mean source-max Spearman=+0.547; directional gate=pass.
  - N=5 source_max: exact=+0.912, first-order=+0.956, Spearman=+0.647, sign=0.812, MAE residual=0.642.
  - N=5 source_min: exact=-2.310, first-order=-1.640, Spearman=+0.582, sign=0.906, MAE residual=1.207.
  - N=20 source_max: exact=+1.193, first-order=+1.019, Spearman=+0.448, sign=0.812, MAE residual=0.806.
  - N=20 source_min: exact=-0.489, first-order=-0.503, Spearman=+0.408, sign=0.594, MAE residual=0.775.
- **EleutherAI/pythia-1.4b**: mean source-max Spearman=+0.586; directional gate=pass.
  - N=5 source_max: exact=+0.744, first-order=+0.770, Spearman=+0.560, sign=0.766, MAE residual=0.724.
  - N=5 source_min: exact=-2.371, first-order=-1.507, Spearman=+0.320, sign=0.875, MAE residual=1.385.
  - N=20 source_max: exact=+1.246, first-order=+1.043, Spearman=+0.611, sign=0.922, MAE residual=0.747.
  - N=20 source_min: exact=-0.503, first-order=-0.555, Spearman=+0.257, sign=0.641, MAE residual=0.794.
- **EleutherAI/pythia-1.4b**: mean source-max Spearman=+0.500; directional gate=pass.
  - N=5 source_max: exact=+0.753, first-order=+0.778, Spearman=+0.469, sign=0.688, MAE residual=0.768.
  - N=5 source_min: exact=-2.272, first-order=-1.785, Spearman=+0.528, sign=0.953, MAE residual=1.177.
  - N=20 source_max: exact=+1.033, first-order=+0.834, Spearman=+0.530, sign=0.844, MAE residual=0.659.
  - N=20 source_min: exact=-0.511, first-order=-0.661, Spearman=+0.643, sign=0.641, MAE residual=0.819.
- **google/gemma-2-2b**: mean source-max Spearman=+0.534; directional gate=pass.
  - N=5 source_max: exact=+0.038, first-order=+0.045, Spearman=+0.496, sign=0.734, MAE residual=0.079.
  - N=5 source_min: exact=-1.312, first-order=-0.836, Spearman=+0.735, sign=0.844, MAE residual=1.313.
  - N=20 source_max: exact=+0.086, first-order=+0.076, Spearman=+0.572, sign=0.703, MAE residual=0.151.
  - N=20 source_min: exact=-0.870, first-order=-0.592, Spearman=+0.687, sign=0.828, MAE residual=0.864.
- **google/gemma-2-2b**: mean source-max Spearman=+0.582; directional gate=pass.
  - N=5 source_max: exact=+0.053, first-order=+0.058, Spearman=+0.550, sign=0.766, MAE residual=0.102.
  - N=5 source_min: exact=-1.517, first-order=-0.904, Spearman=+0.683, sign=0.812, MAE residual=1.090.
  - N=20 source_max: exact=+0.038, first-order=+0.033, Spearman=+0.613, sign=0.656, MAE residual=0.141.
  - N=20 source_min: exact=-1.242, first-order=-0.707, Spearman=+0.672, sign=0.797, MAE residual=1.039.
- **google/gemma-2-2b**: mean source-max Spearman=+0.548; directional gate=pass.
  - N=5 source_max: exact=+0.058, first-order=+0.065, Spearman=+0.488, sign=0.750, MAE residual=0.100.
  - N=5 source_min: exact=-1.410, first-order=-0.767, Spearman=+0.806, sign=0.859, MAE residual=0.988.
  - N=20 source_max: exact=+0.025, first-order=+0.033, Spearman=+0.607, sign=0.672, MAE residual=0.100.
  - N=20 source_min: exact=-0.726, first-order=-0.724, Spearman=+0.700, sign=0.797, MAE residual=0.818.

## Utility Seed Replication

- **EleutherAI/pythia-1.4b**, seeds=[0, 1, 2]: gate=pass; positive source-max cells=6/6; mean seed Spearman=+0.544 [+0.500,+0.586]; missing seeds=[]; sign agreement=0.807.
- **Qwen/Qwen2.5-1.5B**, seeds=[0, 1, 2]: gate=pass; positive source-max cells=6/6; mean seed Spearman=+0.866 [+0.832,+0.898]; missing seeds=[]; sign agreement=0.805.
- **google/gemma-2-2b**, seeds=[0, 1, 2]: gate=pass; positive source-max cells=6/6; mean seed Spearman=+0.554 [+0.534,+0.582]; missing seeds=[]; sign agreement=0.714.

## Selection Robustness

Gate: **pass**; positive selected cells=9/9; paired intervals exclude zero in 9/9; selected/random mean dmargin=+0.874/-0.059.

| seed | configuration | layer | K | max-control dmargin [95% CI] |
| ---: | --- | ---: | ---: | ---: |
| 0 | selected_k2 | 14 | 2 | +0.641 [+0.311,+1.018] |
| 0 | selected_k4 | 14 | 4 | +1.430 [+0.919,+2.003] |
| 0 | selected_k8 | 14 | 8 | +1.418 [+0.885,+2.013] |
| 0 | adjacent_minus | 13 | 4 | +0.067 [-0.091,+0.231] |
| 0 | adjacent_plus | 15 | 4 | -0.355 [-0.568,-0.181] |
| 0 | random_layer | 11 | 4 | -0.093 [-0.227,+0.029] |
| 1 | selected_k2 | 14 | 2 | +0.459 [+0.167,+0.801] |
| 1 | selected_k4 | 14 | 4 | +0.981 [+0.507,+1.539] |
| 1 | selected_k8 | 14 | 8 | +1.069 [+0.584,+1.598] |
| 1 | adjacent_minus | 13 | 4 | +0.049 [-0.085,+0.189] |
| 1 | adjacent_plus | 15 | 4 | -0.277 [-0.395,-0.168] |
| 1 | random_layer | 21 | 4 | -0.190 [-0.326,-0.059] |
| 2 | selected_k2 | 14 | 2 | +0.281 [+0.025,+0.550] |
| 2 | selected_k4 | 14 | 4 | +0.749 [+0.356,+1.190] |
| 2 | selected_k8 | 14 | 8 | +0.835 [+0.427,+1.288] |
| 2 | adjacent_minus | 13 | 4 | +0.326 [+0.146,+0.548] |
| 2 | adjacent_plus | 15 | 4 | +0.239 [+0.065,+0.457] |
| 2 | random_layer | 7 | 4 | +0.106 [-0.007,+0.223] |
