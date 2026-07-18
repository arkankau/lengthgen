# Pretrained Dose-Response Summary

Preregistered success rule: **pass**.
Endpoint positive: `True`; mean path nondecreasing: `True`; alpha zero: `True`.
Seeds: `[0, 1, 2, 3, 4]`; missing: `[]`.

| Alpha | Source minus matched control | Hierarchical 95% CI | Source/control L1 | Seed means |
|---:|---:|---:|---:|:---|
| 0.00 | +0.000 | [+0.000, +0.000] | 0.000/0.000 | +0.000, +0.000, +0.000, +0.000, +0.000 |
| 0.25 | +0.446 | [+0.415, +0.475] | 0.384/0.387 | +0.436, +0.478, +0.414, +0.443, +0.458 |
| 0.50 | +0.817 | [+0.767, +0.867] | 0.768/0.775 | +0.780, +0.856, +0.789, +0.801, +0.858 |
| 0.75 | +1.128 | [+1.059, +1.199] | 1.152/1.162 | +1.080, +1.216, +1.075, +1.117, +1.149 |
| 1.00 | +1.417 | [+1.332, +1.514] | 1.536/1.549 | +1.348, +1.547, +1.369, +1.396, +1.426 |

The endpoint tests the established fixed-spectrum intervention. The interior alphas test whether the effect is a smooth routing response rather than an artifact that appears only after a maximal attention rewrite.
