# Axis B2: Disguised-Jailbreak / Cross-Template Detection -- Result (Hypothesis Falsified)

Source: `scripts/evaluate_detection_ood.py`, `results/detection_ood_metrics.csv`. Qwen2.5-0.5B-Instruct,
layer 16. AdvBench harmful + Alpaca benign, both wrapped in the SAME 6 jailbreak template families
(so only intent, not the wrapper, separates classes). n=40 base prompts/class/template.

## Results

| eval | detector | AUROC |
|---|---|---:|
| leave-one-template-out | logistic probe (trained on other 5 templates) | 1.000 |
| leave-one-template-out | basin_margin | 0.755 |
| leave-one-template-out | single_anchor_cos | 0.601 |
| raw -> disguised | logistic probe (trained on raw untemplated) | 0.999 |
| disguised pooled | surface_risk (keyword) | 0.659 |
| disguised pooled | basin_margin | 0.576 |
| disguised pooled | single_anchor_cos | 0.522 |

## Reading (hypothesis falsified)

The novel hypothesis was: a label-free refusal-geometry score should generalize to unseen jailbreak
templates better than a supervised probe that can overfit to template surface features. The data says
the opposite:

1. **The probe does not overfit -- it generalizes essentially perfectly.** Leave-one-template-out
   AUROC = 1.0; trained on raw untemplated prompts and tested on disguised = 0.999. The harmful-vs-benign
   distinction is robustly linearly separable in hidden states regardless of disguise, so there is no
   generalization gap for a label-free method to fill.
2. **The label-free geometric methods are near-chance on the disguised task** (basin 0.576, single-anchor
   0.522) and basin_margin even loses to the trivial surface keyword baseline (0.659). Basin competition
   is not a useful detector of disguised harmful intent.

## Conclusion for the project

This is the third rigorous negative empirical result, after Path C (defense degrades generation) and
Axis B (basin detection non-competitive on raw harmful vs benign). Together they establish, cleanly:

- Internal-state harmful/benign separation is real but **trivially captured by a supervised probe**,
  which generalizes across jailbreak templates -- a known property of hidden states, to which our
  thermodynamic basin-competition method adds nothing.
- Logit-space attraction/barrier control **degrades generation** rather than steering it (verifier-gated).

What survives as genuine, defensible contributions: (1) the verified two-level Boltzmann theory of the
null-attractor probe; (2) the confound-as-theorem + mandatory risk=0 baseline-control methodology, which
transfers to other internal-state safety-probe work; (3) this mapped boundary of what thermodynamic
attractor/barrier methods can and cannot do. This is a theory + methodology + negative-results paper,
not a positive-detector or positive-defense paper. Further empirical swings for a positive headline are
not warranted on this evidence.
