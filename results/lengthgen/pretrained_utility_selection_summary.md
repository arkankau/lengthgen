# Pretrained Utility-Selection Summary

Primary gate: **pass**.
Confirmatory lengths: `[5]`.

The competence gate is applied to pooled untouched exact-match accuracy. Cells below 0.50 are margin diagnostics, not confirmatory behavioral evidence.

| Length | Seeds | Baseline acc. | Competent | Utility max-control margin [95% CI] | Mass max-control margin [95% CI] | Utility-minus-mass [95% CI] | Utility max-control accuracy |
|---:|:---:|---:|:---:|---:|---:|---:|---:|
| 5 | 0,1,2 | 0.956 | yes | +0.702 [+0.529, +0.858] | -0.021 [-0.057, +0.014] | +0.723 [+0.544, +0.882] | +0.052 |
| 20 | 0,1,2 | 0.432 | no | +2.200 [+1.276, +2.935] | -0.035 [-0.080, +0.009] | +2.235 [+1.307, +2.963] | +0.167 |
| 80 | 0 | 0.023 | no | +0.163 [+0.059, +0.291] | -0.000 [-0.018, +0.019] | +0.163 [+0.057, +0.295] | +0.000 |

## Circuits

- Seed 0: source-mass layer 10 heads [19, 1, 3, 16]; utility-gain layer 8 heads [29, 22, 15, 3]; available lengths [5, 20, 80].
- Seed 1: source-mass layer 10 heads [1, 3, 19, 16]; utility-gain layer 15 heads [8, 7, 26, 9]; available lengths [5, 20].
- Seed 2: source-mass layer 10 heads [1, 19, 3, 16]; utility-gain layer 15 heads [8, 7, 26, 9]; available lengths [5, 20].

## Interpretation

Utility-gain selection rescues the fixed-spectrum source-max intervention at the competent five-pair condition and beats source-mass selection on paired examples. The positive margin direction also repeats at 20 pairs, but pooled baseline accuracy there is below the preregistered competence threshold. Seeds 1 and 2 omit the optional 80-pair diagnostic to prioritize confirmatory GPU cells; seed 0 supplies that tail.
