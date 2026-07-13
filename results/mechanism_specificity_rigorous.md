# Mechanism-Specificity: Rigorous Re-Test

Common target = repetition_collapse (1 - unique_token_ratio), identical in both families.
Control baseline is FLEXIBLE (squares + interactions); CV is leave-one-SETTING-out; partial R^2
= share of control-unexplained variance that thermo explains; CIs bootstrap over settings.

## null-attention
- rows=144, settings=18
- flexible-control CV R^2 = -0.058; +thermo CV R^2 = 0.169; raw delta = 0.226
- **partial R^2 = 0.226**  (bootstrap mean 0.253, 95% CI [0.004, 0.460])
- permutation test: observed delta 0.226, p = 0.003

## residual-steering
- rows=240, settings=24
- flexible-control CV R^2 = 0.250; +thermo CV R^2 = 0.047; raw delta = -0.203
- **partial R^2 = -0.271**  (bootstrap mean -0.022, 95% CI [-0.341, 0.290])
- permutation test: observed delta -0.203, p = 0.993

## Pre-registered verdict
- null partial-R^2 CI = [0.004, 0.460]
- steering partial-R^2 CI = [-0.341, 0.290]
- non-overlapping (null CI above steering CI): **False**

MECHANISM-SPECIFICITY NOT SUPPORTED by non-overlapping CIs on the common target (report honestly).
