# Pretrained Causal Routing Summary

Each intervention acts in one calibration-selected layer and preserves the complete selected-head
attention spectrum. Deltas are paired against the natural model on identical examples.

| model | N | baseline acc | max dacc | min dacc | ctrl dacc | max dmargin | min dmargin | ctrl dmargin | invariant err |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| EleutherAI/pythia-70m | 3 | 0.500 | +0.250 | -0.500 | +0.000 | +0.106 | -1.785 | +0.021 | 1.19e-07 |
| EleutherAI/pythia-70m | 6 | 0.250 | +0.000 | -0.250 | +0.000 | +0.736 | -1.771 | -0.219 | 1.19e-07 |
