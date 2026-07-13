# Paper Evidence Report

This report consolidates existing artifacts for the detection-first paper package. It does not rerun experiments and does not present generation intervention as a defense result.

**Update note:** this report was substantially extended after a cross-model validation pass (GPT-2-family
vs. Qwen2.5-0.5B-Instruct) that added a basin-energy diagnostic, found and fixed a confound in the
null-attractor mechanism itself, and retracted one earlier claim. See `docs/paper/claims_and_evidence.md`
(Claims 7-9) for the full, current claim set; this report's older sections below are preserved for
GPT-2-family/toy evidence but should be read alongside the new sections, not in place of them.

## Key Paper Move

Null attraction reveals the thermodynamic response, but safe control requires structured attractors or barriers that reshape the energy landscape without destroying benign task basins. A second move sits alongside it: the null-attractor mechanism had a hidden layer-scale confound, caught via a risk=0 ablation and fixed; the fix improved generation-time risk-selectivity, which is itself evidence for the underlying mechanism, not just a cleaner diagnostic.

Source: `docs/paper/key_paper_move.md`

## Locked Claim Boundary

- Contribution: thermodynamic attention diagnostics for jailbreak-like latent states, cross-validated on an unaligned (GPT-2-family) and an aligned (Qwen2.5-0.5B-Instruct) model.
- Negative control: generation-time null intervention shows thermodynamic detection does not automatically yield safe control, even after fixing the mechanism's layer-scale confound.
- Generation intervention artifacts are labeled as `diagnostic_ablation` or `failure_case` evidence, not defense results.
- One earlier claim (the pre-fix "two independent diagnostics agree on a depth boundary") is retracted; see Claim 8 in `docs/paper/claims_and_evidence.md`. It is preserved in the record as a worked example of catching a mechanism artifact via ablation, not deleted.

## Attractor Derivation Scaffold

Candidate attractors and barriers are derived in `docs/paper/thermodynamic_attractor_derivations.md`: null attractor, refusal attractor, safe-redirection attractor, high-entropy safety shell, free-energy barrier, metastable safety basin, and energy-landscape reshaping.

Status: theory scaffold for next experiments, not evidence of working generation control.

## Toy and Real Phase-Transition Evidence

| setting | critical R | max slope | susceptibility peak | low-risk m_null | high-risk m_null | jump | universality gap |
|---|---:|---:|---:|---:|---:|---:|---:|
| toy | 0.504 | 6.723 | 0.0166 | 0.075 | 0.999 | 0.924 | 0.019 |
| tiny-gpt2 diagnostic | 0.349 | 0.272 | 0.0002 | 0.035 | 0.033 | -0.002 | 0.007 |
| distilgpt2 normalized diagnostic | 0.495 | 9.032 | 0.0077 | 0.558 | 0.999 | 0.441 | 0.022 |

Source: `results/phase_transition_comparison.md`

## Threshold Baseline Comparison

| setting | method | jailbreak collapse | benign false collapse | max slope | susceptibility peak | low-risk response | high-risk response | jump | thermodynamic observables |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| toy | null_attractor | 0.333 | 0.000 | 6.723 | 0.0166 | 0.075 | 0.999 | 0.924 | yes |
| toy | threshold | 0.708 | 0.071 | 7.084 | 0.2041 | 0.000 | 1.000 | 1.000 | no |
| tiny-gpt2 diagnostic | null_attractor | 0.000 | 0.000 | 0.272 | 0.0002 | 0.035 | 0.033 | -0.002 | yes |
| tiny-gpt2 diagnostic | threshold | 1.000 | 0.286 | 10.071 | 0.2500 | 0.250 | 1.000 | 0.750 | no |
| distilgpt2 normalized diagnostic | null_attractor | 0.875 | 0.286 | 9.032 | 0.0077 | 0.558 | 0.999 | 0.441 | yes |
| distilgpt2 normalized diagnostic | threshold | 0.708 | 0.071 | 15.742 | 0.2041 | 0.000 | 1.000 | 1.000 | no |

Source: `results/baseline_comparison_summary.md`

## Latent Trajectory Risk Probe

| setting | threshold | jailbreak m_null | benign m_null | separation | jailbreak length delta | benign length delta | empty rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| s001 | 0.26 | 0.439 | 0.286 | 0.153 | -29.3 | -31.9 | 0.000 |
| s002 | 0.42 | 0.425 | 0.189 | 0.236 | -28.0 | -31.6 | 0.000 |
| s003 | 0.60 | 0.393 | 0.103 | 0.289 | -27.8 | -29.1 | 0.000 |
| s004 | 0.75 | 0.304 | 0.027 | 0.277 | -24.2 | -24.6 | 0.000 |

Source: `results/latent_probe_risk_upgrade_note.md`

## Negative Control: Intervention Failure

The stronger local GPT-2-family runs should not be promoted as behavior-selected results. They are useful as negative evidence:

- higher model scale improves baseline fluency,
- higher null mass improves the physics proxy,
- but the current calibrated-refusal value vector does not reliably produce safe semantic redirection in GPT-2-family generation.

This supports the paper's central caution: null-attractor phase behavior is a mechanism, not a complete safety defense. Controlled thermodynamic attraction must be validated behaviorally, not inferred from `m_null` alone.

Evidence label: `failure_case`.

Source: `results/gpt2_family_behavior_failure_note.md`

## Selected-Head Diagnostic Ablation

Top head ranking:

| rank | head | separation | jailbreak m_null | benign m_null |
|---:|---:|---:|---:|---:|
| 1 | 10 | 0.396 | 0.434 | 0.038 |
| 2 | 14 | 0.389 | 0.439 | 0.050 |
| 3 | 7 | 0.382 | 0.431 | 0.049 |
| 4 | 0 | 0.389 | 0.449 | 0.060 |
| 5 | 13 | 0.378 | 0.423 | 0.045 |
| 6 | 11 | 0.388 | 0.455 | 0.067 |

Selected-head grid:

| setting | heads | jailbreak m_null | benign m_null | separation | empty rate | unique ratio |
|---|---|---:|---:|---:|---:|---:|
| s001 | 10 | 0.027 | 0.003 | 0.024 | 0.000 | 1.000 |
| s002 | 10,14 | 0.054 | 0.006 | 0.048 | 0.053 | 0.947 |
| s003 | 10,14,7,0 | 0.108 | 0.012 | 0.096 | 0.053 | 0.945 |
| s004 | 10,14,7,0,13,11 | 0.163 | 0.019 | 0.144 | 0.026 | 0.974 |

Evidence label: `diagnostic_ablation`.

Source: `results/gpt2_medium_head_selection_note.md`

## Cross-Model Basin-Energy Validation

Post-hoc basin-competition diagnostic (`E_b = -cos(h, c_b)` against safe/unsafe/benign anchors, plus a
multi-anchor subspace check) run identically on distilgpt2 and Qwen2.5-0.5B-Instruct:

| model | signal shape across depth | single-vs-subspace margin correlation | interpretation |
|---|---|---:|---|
| distilgpt2 | flat, noise-level (`sep` ~0.005-0.03) at every layer | -0.4 to -0.9 (disagree) | no coherent refusal semantics to detect (no RLHF training) |
| Qwen2.5-0.5B-Instruct | grows monotonically with depth, peaks at layer 21/24 (`sep` 0.0126, ~25x layer-6 value) | 0.80 to 0.97 (agree) | real, structured, depth-dependent signal |

Both models collapse at the model's final 2-3 layers (correlation -> ~0), consistent with known
attention-sink/compression-valley effects, independent of the refusal-semantics question.

Evidence label: `cross_model_validation`.

Source: `results/basin_energy_diagnostic_note.md`, `thermosafety/basin_energy.py`.

## Null-Attractor Depth Diagnostic and Mechanism Fix

A companion depth sweep of the original `m_null`/entropy/spectral-gap observables on Qwen2.5-0.5B-Instruct
initially appeared to independently corroborate the basin-energy collapse at layers 22-23 (a growing
attention-sink token, confirmed across 12 prompts/6 suites, dissolves there). This was retracted as
"independent agreement": a risk=0 control ablation showed the null slot's hardcoded-zero logit made its
baseline competitiveness depend on each layer's absolute logit scale (6.7% to 83% of raw `m_null` present
even with risk-gating disabled, varying wildly by layer) -- once fixed (`null_key_mode="mean_logit"`,
computing the null logit from the mean of real logits instead), `m_null`-based separation at layers 22-23
became strong (`0.21-0.22`), not collapsed, and the confound dropped to a stable 6.7-8.3% at every layer.

| stage | best layer (by the metric available at that time) | risk-attributable sep at that layer | baseline confound at that layer |
|---|---:|---:|---:|
| pre-fix, raw sep(m_null) | 21 | -- (not yet computed) | unknown |
| pre-fix, risk=0 control added | 21 (shown to be wrong) | 0.158 | 77% |
| post-fix (`mean_logit`) | 10 | 0.257 | 8.2% |

Evidence label: `diagnostic_ablation` (the attention-sink finding) plus `mechanism_correction` (the
confound and fix).

Source: `results/null_attractor_depth_diagnostic_note.md`, `thermosafety/intervention.py` (`build_null_logits`).

## Generation Intervention on an Aligned Model, Pre- and Post-Fix

| stage | benign m_null | jailbreak/obfuscated m_null | jailbreak continuation under semantic modes |
|---|---:|---:|---|
| pre-fix (layer 21) | 0.6-0.7 (nearly as high as jailbreak) | 0.6-0.99 | token-loop gibberish, no visible difference between `zero` and semantic modes |
| post-fix (layer 10) | ~0.01 | 0.40-0.62 | repeated but semantically correct refusal token ("No."), distinct from `zero` mode's "Yes" drift |

Benign generation quality is not fully preserved even post-fix (fluent baseline degrades to repetitive
loops at ~1% null mass), so this remains a negative-control result for "detection is not solved safe
control" -- but it is a measurably better one than the pre-fix result, on firmer methodological ground.

Evidence label: `failure_case` (pre-fix) superseded in degree, not in kind, by `improved_failure_case`
(post-fix).

Source: `results/qwen_generation_intervention_note.md`, `results/qwen_generation_intervention_fixed_note.md`.

## Related-Work Anchor

We turn attention-as-energy theory into a safety diagnostic: a controlled null attractor exposes jailbreak-sensitive phase behavior in transformer attention, while entropy, spectral gap, and head-local null mass distinguish selective detection from global degeneration.

Source: `docs/attention_thermodynamics_knowledge.md`

## Paper-Facing Figure/Table Checklist

- Figure: `m_null` vs risk / threshold phase curve.
- Figure: entropy and spectral-gap diagnostics.
- Table: threshold baseline vs thermodynamic diagnostic.
- Table: latent trajectory risk threshold sweep.
- Table: head-local selected-head response.
- Table: intervention failure showing high null mass is not safe generation.

## Claim Audit

- OK: null-attractor dynamics provide thermodynamic observables for detection/diagnosis.
- OK: selected heads reduce global degeneration relative to all-head attraction.
- OK: failed generation intervention motivates richer attractor semantics and barrier designs.
- OK: basin-energy and null-attractor diagnostics both validated cross-model (GPT-2-family vs. Qwen2.5-0.5B-Instruct), with the aligned model showing real structured signal the unaligned model lacks.
- OK: a confound in the null-attractor mechanism's baseline logit was found via a risk=0 ablation and fixed, and reporting this strengthens rather than weakens the paper's credibility.
- OK: the fixed mechanism shows measurably better generation-time risk-selectivity on the aligned model, though benign generation quality is still not fully preserved.
- Not OK: claiming current intervention prevents jailbreaks.
- Not OK: calling current outputs a deployed or validated defense.
- Not OK (retracted): citing the pre-fix "two independent diagnostics agree on a depth boundary at layers 22-23" as corroborating evidence -- see Claim 8's retraction in `docs/paper/claims_and_evidence.md`.
