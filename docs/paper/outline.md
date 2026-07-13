# Null-Attractor Attention: Thermodynamic Diagnostics for Jailbreak Detection

## Working Thesis

Transformer attention can be treated as an energy-style retrieval process. By adding a controlled null attractor and measuring null mass, entropy, spectral gap, and head-local response, we can diagnose jailbreak-like latent states and distinguish selective phase behavior from global degeneration. This has now been validated across two model families with different training: GPT-2-family (no RLHF/safety training) and Qwen2.5-0.5B-Instruct (RLHF/safety-tuned), which behave qualitatively differently in a way that itself supports the thesis (see Claim 7 in `docs/paper/claims_and_evidence.md`).

## Key Paper Move

Null attraction reveals the thermodynamic response, but safe control requires structured attractors or barriers that reshape the energy landscape without destroying benign task basins. A second, methodological move sits alongside it: the null-attractor mechanism itself had a hidden confound (the null slot's logit was hardcoded to `0` rather than computed, making its baseline competitiveness depend on each layer's absolute logit scale, independent of risk). Diagnosing and fixing this confound (Claim 9) is itself part of the paper's contribution -- it demonstrates why baseline-controlled diagnostics (a risk=0 ablation) are necessary before trusting a raw thermodynamic observable, and fixing it measurably improved generation-time risk-selectivity, not just the diagnostic's internal consistency.

## Claim Discipline

This paper is a diagnostic paper. It does not claim that the current generation-time intervention is a working jailbreak defense.

Locked claims:

1. Attention can be interpreted as Hopfield/energy-style retrieval dynamics.
2. A controlled null attractor exposes risk-conditioned phase behavior.
3. Entropy, spectral gap, and head-local null mass distinguish selective detection from global degeneration.
4. GPT-2-family results are scoped by the absence of trained refusal behavior; basin-energy and null-attractor diagnostics both show flat/noisy signal on GPT-2-family and a real, structured signal on an aligned model (Qwen2.5-0.5B-Instruct), which is itself evidence the methods are measuring something real rather than an artifact of the math (Claim 7, `claims_and_evidence.md`).
5. A confound in the null-attractor mechanism's baseline competitiveness was found and fixed; the corrected mechanism produces flat baseline fraction across depth and measurably better generation-time risk-selectivity (Claim 9).

Negative-control boundary:

- Generation-time null intervention remains a failed-or-limited control experiment even after the mechanism fix: benign generation quality is not fully preserved, and jailbreak "redirection" produces a repeated but semantically correct refusal token rather than a fluent safe explanation. This is evidence that null mass (even risk-selective null mass) is not yet sufficient for safe semantic control, not a main contribution.
- A prior, retracted claim (originally "Claim 8": two independent diagnostics agree on a depth-wise structural boundary at layers 22-23 of Qwen's 24) turned out to be partly caused by the pre-fix mechanism confound, not independent corroboration. See Claim 8's retraction in `claims_and_evidence.md`. This should be reported in the paper as a worked example of catching an artifact via ablation, not omitted.

## Proposed Structure

1. **Introduction**
   - Jailbreaks can be viewed as adversarial attempts to steer latent model dynamics.
   - Existing surface filters miss internal trajectory behavior.
   - We propose a thermodynamic diagnostic based on controlled null-attractor response.

2. **Background**
   - Transformer attention as energy / Hopfield retrieval.
   - Attention sinks and softmax collapse.
   - Internal-state jailbreak detection and refusal geometry.

3. **Method**
   - Append a null key/value pair; define risk-conditioned null bias and inverse-temperature schedule.
   - Measure `m_null`, entropy, spectral gap, and selected-head response.
   - Basin-energy diagnostic: score hidden states against safe/unsafe/benign anchor centroids (`E_b = -cos(h, c_b)`), Boltzmann basin occupancy, free energy, and a multi-anchor subspace analysis testing whether one direction captures the refusal/unsafe axis (`thermosafety/basin_energy.py`).
   - Semantic attractors (`semantic_refusal`, `semantic_redirection`): calibrate the null slot's value from refusal/unsafe/redirect anchor texts instead of a blank sink (`thermosafety/intervention.py`).
   - Root-cause fix (`null_key_mode="mean_logit"`): compute the null slot's logit from the mean of real, causally-valid logits instead of hardcoding it to `0`, removing a layer-scale-dependent baseline confound (Claim 9).
   - Derive richer candidate attractors and barriers for future control tests (`docs/paper/thermodynamic_attractor_derivations.md`).
   - Treat generation intervention as a diagnostic ablation. Frame null attraction as a diagnostic probe, not a safety policy.

4. **Experiments**
   - Toy phase-transition mechanism.
   - Real hidden-state post-hoc diagnostics (GPT-2-family).
   - Latent trajectory risk probe.
   - Threshold baseline comparison.
   - GPT-family intervention failure case.
   - Head-local selected-head diagnostic.
   - Basin-energy diagnostic, cross-model: flat/noisy signal on distilgpt2 vs. depth-growing, internally-consistent signal on Qwen2.5-0.5B-Instruct (`results/basin_energy_diagnostic_note.md`).
   - Null-attractor depth diagnostic with an automatic risk=0 baseline control (`results/null_attractor_depth_diagnostic_note.md`); includes the retracted "cross-diagnostic depth-boundary" finding as a worked example of catching a mechanism artifact.
   - Generation intervention on Qwen2.5-0.5B-Instruct, pre- and post-fix (`results/qwen_generation_intervention_note.md`, `results/qwen_generation_intervention_fixed_note.md`): the fixed mechanism shows measurably better risk-selectivity and produces a semantically correct (if repetitive) refusal token on jailbreak prompts, without fully preserving benign generation quality.

5. **Limitations**
   - Detection is not safe generation control, even after fixing the mechanism confound.
   - High null mass can worsen continuations; benign generation quality is not fully preserved even at ~1% null mass on the corrected layer.
   - Current refusal-vector attractor is semantically crude; refusal is known to be multi-dimensional (refusal cones, Wollschlager et al. ICML 2025), not fully captured by a single mean-difference anchor.
   - GPT-2-family results are scoped by the absence of trained refusal behavior; conclusions there should not be generalized to aligned models without separate validation (which this paper now provides for one aligned model).
   - Stronger benchmarks, richer attractor semantics, and validation on additional aligned models remain future work.

6. **Conclusion**
   - Thermodynamic attention diagnostics are a promising internal detection lens, now validated across an unaligned and an aligned model.
   - Safe redirection requires more than inducing an absorbing null basin; fixing a mechanism confound measurably improved but did not solve generation-time control.
   - The next control hypothesis is semantic attractor/barrier design, not stronger null collapse -- and any such design should be validated with the same baseline-controlled diagnostic discipline (a risk=0 ablation) used to catch the confound in this paper.
