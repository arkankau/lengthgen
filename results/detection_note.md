# Axis B: Detection Metrics vs Baselines -- Result (Non-Competitive)

Task: binary detection, AdvBench harmful (n=200) vs Alpaca instruction-only benign (n=200), scoring
the prompt's mean-pooled hidden state on Qwen2.5-0.5B-Instruct. Source: `scripts/evaluate_detection.py`,
metrics in `results/detection_metrics.csv`. Harmful prompts cached under `.data_cache/` (gitignored,
never committed).

## Results (AUROC; best layer per detector)

| detector | best AUROC | layer | TPR@FPR=5% | notes |
|---|---:|---:|---:|---|
| logistic_probe (supervised, 5-fold CV) | ~1.00 | all | 1.00 | near-perfect but see caveat |
| single_anchor_cos (dist. from refusal) | 0.790 | 16 | 0.26 | simple 1-direction baseline |
| basin_margin (E_safe - E_unsafe) | 0.751 | 16 | 0.085 | our method |
| surface_risk (keyword heuristic) | 0.670 | -- | 0.13 | trivial baseline |

Full sweep (layers 14/16/18/20/21): basin_margin 0.70-0.75, single_anchor_cos 0.75-0.79,
probe ~1.0 throughout.

## Honest reading

1. **basin_margin is not a competitive detector.** It is beaten by the single-refusal-direction
   cosine baseline at *every* layer, and demolished by the supervised probe. The basin *competition*
   (safe vs. unsafe) buys nothing over simple distance-from-refusal -- the extra machinery is not
   justified for detection on this task.
2. **The supervised probe's ~1.0 is not a win to celebrate -- it signals a saturated task.** AdvBench
   (harmful) vs. Alpaca (benign) differ in topic and phrasing and are nearly linearly separable, so a
   896-dim probe trivially separates them. This measures harmful-*topic* detection, not jailbreak
   *evasion*, and does not discriminate methods meaningfully.
3. **Strict-FPR behavior is poor for every label-free detector** (TPR@5% of 0.04-0.26). None is
   deployment-grade; only the (saturated) probe clears it.

## What this means for the paper

The "positive competitive detector" framing (Axis B) is **not supported** by this evidence. Combined
with the clean failure of Axis C (defense), the empirical safety/detection contributions are negative
or non-competitive. What remains solidly true and defensible:

- the verified two-level Boltzmann theory and susceptibility prediction (`scripts/verify_theory.py`);
- the confound-as-theorem + mandatory risk=0 baseline control -- a transferable methodological warning
  that applies to other internal-state safety-probe work;
- the cross-model diagnostic finding that a basin signal exists on aligned models and not unaligned
  ones (existence, not competitiveness).

## The one caveat that could still yield a positive detection result

This task tests *direct harmful* prompts, where surface/topic cues already separate the classes (hence
the probe's ~1.0 and surface_risk's 0.67). It does NOT test the case internal-state detection is
actually motivated for: *disguised* jailbreaks that evade surface cues (obfuscated / templated /
many-shot), where a topic-probe trained on raw harmful text may fail but internal geometry might still
fire. That is the only remaining place an internal-state method could show unique value. It requires a
real jailbreak-templated evaluation set (not the 4-6 hand-built prompts per suite we currently have),
and after two negative empirical results it should be treated as uncertain, not assumed.
