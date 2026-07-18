# Multi-Evidence Routing Summary

- Models: 8
- Minimum train-length exact match: 1.000
- Competence gate passed: True
- Maximum spectrum-invariant error: 4.77e-07

| length | baseline exact | source-max | source-min | control | max delta | min delta | control delta | max-minus-min | max-minus-control |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 0.952 | 0.971 | 0.393 | 0.964 | +0.019 | -0.559 | +0.012 | +0.578 | +0.007 |
| 25 | 0.484 | 0.550 | 0.194 | 0.507 | +0.066 | -0.291 | +0.023 | +0.356 | +0.043 |

Interpretation is conditional on the competence gate. Source-max and source-min assign the same
complete attention spectrum to opposite ends of the two-token evidence-mass range. The distractor
control preserves both the spectrum and evidence mass.
