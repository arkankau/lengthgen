# Data Dictionary

## Scope

The package contains generated controlled-task data, saved model outputs and attention measurements, summary
statistics, preregistrations, and selected controlled-model checkpoints. It does not introduce a static novel
dataset. Pretrained checkpoints are not redistributed.

Natural multiple-choice QA examples are derived from the public SQuAD training split. Saved artifacts identify
the source dataset, split, seed, eligibility rule, and selected example IDs. Reproduction from scratch downloads
SQuAD through the Hugging Face `datasets` library.

## Common units

| Field | Meaning |
|---|---|
| `accuracy`, `token_accuracy`, `exact_match` | Fraction of examples answered correctly, in `[0,1]` |
| `margin` | Correct-answer logit minus the strongest competing-answer logit |
| `source_mass` | Sum of attention weights assigned to labeled evidence positions |
| `transfer_mass`, `delta` | Attention mass moved from donor positions to evidence positions |
| `invariant_error` | Maximum absolute difference between sorted attention weights before and after a swap |
| `utility_gain` | First-order predicted margin change from moved mass and source-donor value utility |
| `ci95` | Two-sided 95% interval produced by the analysis named in the relevant report |
| `n_examples` | Number of paired evaluation examples contributing to a cell |
| `n_seeds` | Number of independent experiment or calibration seeds in an aggregate |

Margin and accuracy are different units and should not be compared numerically across rows. A reported
intervention contrast is paired unless its report explicitly says otherwise.

## Condition names

| Name | Definition |
|---|---|
| `baseline` or `untouched` | Original model forward pass |
| `source_max` | Swap the largest selected-head attention weight onto the labeled source position |
| `source_min` | Swap the smallest selected-head attention weight onto the labeled source position |
| `distractor_control` or `control` | Permute non-source weights while preserving source mass, using the control rule recorded by the runner |
| `evidence_max` | Multi-evidence analogue that assigns the largest available weights to labeled evidence positions |
| `matched_control` | Control chosen to minimize attainable displacement mismatch under the stated invariants |

All fixed-spectrum conditions preserve the complete multiset of attention weights within each intervened row.
Floating-point implementations report the residual invariant error.

## Record levels

- Per-example records store paired outcomes for each condition and are the source for intervals and sign tests.
- Per-seed summaries aggregate evaluation examples within one frozen calibration seed.
- Hierarchical summaries resample seed clusters first and paired examples second when multiple seeds are available.
- Preregistration files contain planned models, selectors, competence gates, contrasts, and stopping rules.
- `.npz` files contain dense attention-spectrum arrays for the endogenous-assignment audit.
- `.pt` files are controlled-model checkpoints only; pretrained model weights are downloaded from their public IDs.

## Matched main-figure subsets

Main Figure 5 uses experiment seed 0, 128 paired examples in every cell, and the shared 5/20/80 key-value-pair
ladder for all four models. Main Figure 6 uses seed 0, 128 paired examples in every cell, and the shared
4/8/16/32-passage ladder for Qwen and SmolLM2. Broader seed aggregates are reported separately in the
supplement and are not substituted into these matched visual comparisons.
