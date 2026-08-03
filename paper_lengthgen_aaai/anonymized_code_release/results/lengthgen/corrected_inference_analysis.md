# Corrected Inference and Robustness Analysis

## Primary inference family

| Claim | Clusters | Estimate | 95% interval | Exact p | Holm p |
|---|---:|---:|---:|---:|---:|
| source-max exceeds distractor control | 16 | +0.141846 | [+0.080444, +0.205507] | 3.05176e-05 | 9.15527e-05 |
| capacity increases the source-max minus source-min contrast | 16 | +0.150452 | [+0.093811, +0.209778] | 6.10352e-05 | 0.00012207 |
| utility-selected source-max exceeds matched control on natural QA | 6 | +0.378418 | [+0.253251, +0.520182] | 0.03125 | 0.03125 |

## Vacuity

All selected heads are vacuous in 8.4% of rows (86/1024).
Mean exact margin effect is +3.891 over all rows and +4.248 over active-circuit rows.

## Ceiling-robust association

Ceiling points: 151/384 (39.3%).
Attention pooled Spearman/Kendall: 0.854/0.713; non-ceiling: 0.912/0.751.
Variance pooled Spearman/Kendall: 0.445/0.338; non-ceiling: 0.544/0.402.
