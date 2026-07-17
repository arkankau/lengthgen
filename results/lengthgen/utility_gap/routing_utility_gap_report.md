# Routing Utility-Gap Audit

The first-order term is the gradient of the target-vs-baseline-competitor logit margin along the exact source-max permutation path at the natural attention row.

- Examples: 1024 across 32 model-length cells.
- Pooled Pearson / Spearman: 0.917 / 0.989.
- Within-cell Pearson: 0.843.
- Correlation of model-length mean predicted vs. actual changes: 0.978.
- Sign agreement: 0.995.
- Positive active source-minus-distractor utility gaps: 0.892.
- Mean predicted / actual margin change: +2.880 / +3.891.
- Mean absolute curvature residual: 1.193.
- Answer accuracy, natural / source-max: 0.239 / 0.533.

The audit tests a local sufficient-condition term, not a global linearity assumption; large residuals diagnose downstream curvature along the full swap.
