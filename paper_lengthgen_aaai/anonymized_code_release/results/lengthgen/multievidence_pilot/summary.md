# Multi-Evidence Routing Summary

- Models: 1
- Minimum train-length exact match: 1.000
- Competence gate passed: True
- Maximum spectrum-invariant error: 4.77e-07

| length | baseline exact | source-max | source-min | control | max delta | min delta | control delta | max-minus-min |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 0.883 | 0.867 | 0.656 | 0.922 | -0.016 | -0.227 | +0.039 | +0.211 |
| 25 | 0.367 | 0.422 | 0.195 | 0.359 | +0.055 | -0.172 | -0.008 | +0.227 |

Interpretation is conditional on the competence gate. Source-max and source-min assign the same
complete attention spectrum to opposite ends of the two-token evidence-mass range. The distractor
control preserves both the spectrum and evidence mass.
