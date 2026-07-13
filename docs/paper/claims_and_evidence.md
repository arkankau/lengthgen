# Claims and Evidence

## Central Move

Null attraction reveals the thermodynamic response, but safe control requires structured attractors or barriers that reshape the energy landscape without destroying benign task basins.

Repo support:

- `docs/paper/key_paper_move.md`
- `docs/paper/thermodynamic_attractor_derivations.md`

Safe wording:

> The null attractor is a diagnostic probe of the attention energy landscape; its generation failure motivates semantically structured attractors and unsafe free-energy barriers.

Avoid:

> More null mass means better safety.

## Claim 1: Attention supports an energy / attractor interpretation

Evidence:

- Modern Hopfield work shows transformer attention can be interpreted as retrieval dynamics over energy minima.
- Energy Transformer and statistical-mechanics transformer work support energy-based and path-wise analyses of attention.

Repo support:

- `docs/attention_thermodynamics_knowledge.md`
- `results/related_work_literature_map.md`

Safe wording:

> We build on energy and Hopfield interpretations of attention to define a controlled diagnostic perturbation.

Avoid:

> Hopfield equivalence proves jailbreak detection.

## Claim 2: A controlled null attractor exposes phase-transition-like behavior

Evidence:

- Toy diagnostics show a sharp order-parameter jump.
- Phase-transition comparison reports toy jump `0.924`.
- DistilGPT2 normalized diagnostic shows a steep response but excessive low-risk null mass.

Repo support:

- `results/phase_transition_comparison.md`
- `results/phase_transition_toy_expanded_report.md`
- `results/phase_transition_distilgpt2_normalized_expanded_report.md`

Safe wording:

> The toy system demonstrates the intended order-parameter mechanism; real hidden-state diagnostics show partial but imperfect transfer.

Avoid:

> The real-model diagnostic is already a deployable operating point.

## Claim 3: Thermodynamic observables add information beyond thresholding

Evidence:

- Thresholding produces binary classification curves but no attention-level observables.
- Null-attractor diagnostics provide `m_null`, entropy, spectral-gap, and susceptibility-style measurements.

Repo support:

- `results/baseline_comparison_summary.md`
- `scripts/compare_threshold_baseline.py`

Safe wording:

> Plain thresholding is a useful baseline, but it does not test whether the attention energy landscape changes.

Avoid:

> Null attraction is better than thresholding on all classification metrics.

## Claim 4: Latent trajectory risk is the right direction for `R(X)`

Evidence:

- `probe_latent` excludes surface risk and uses hidden-state trajectory features.
- The focused latent threshold sweep favored `R_c=0.60`, reducing benign attraction while preserving jailbreak attraction.

Repo support:

- `thermosafety/risk_provider.py`
- `results/latent_probe_risk_upgrade_note.md`
- `results/trajectory_probe_latent_report_distilgpt2_expanded.md`

Safe wording:

> Latent risk improves the research direction by moving `R(X)` away from pure surface keywords, but the current probe is still a calibration scaffold.

Avoid:

> The latent probe is a validated jailbreak classifier.

## Negative Control: Generation intervention failure

Evidence:

- GPT2/GPT2-medium outputs were often worse than baseline.
- Stronger null attraction drove `m_null` near `0.990` while continuations stayed unsafe or poor.
- This separates physical null-basin activation from safe semantic redirection.
- Replicated on `Qwen/Qwen2.5-0.5B-Instruct`, an aligned model whose untouched baseline already refuses
  jailbreak prompts correctly and answers benign prompts coherently. At the original (pre-fix, confounded)
  layer 21, every tested null-value mode degraded generation into repetition or incoherence on jailbreak
  *and* benign *and* safety-research prompts alike, with no visible difference between `zero` and the
  semantic modes.
- **After fixing the layer-baseline confound (Claim 9)** and rerunning at the corrected layer 10:
  risk-selectivity improved substantially (benign/safety-research `m_null` ~1% vs. jailbreak/obfuscated
  40-62%, versus benign reaching 60-70% at the old layer 21), and `semantic_refusal`/`semantic_redirection`
  now produce a repeated but semantically correct refusal token ("No.") on jailbreak prompts, distinct
  from `zero` mode's affirmative-flavored drift ("Yes" "Yes" "Yes").
- **A repetition-controlled rerun (`--repetition-penalty`, `--no-repeat-ngram-size`) confirmed the refusal
  signal is real content, not a repeated-token-loop artifact** ("No." is followed by an unrelated but
  harmless tangent, not compliance). It also revealed the benign-preservation caveat is stronger than
  first characterized: without repetition masking it as neat loops, the same ~1% null mass on benign
  prompts produces run-together, malformed text with missing word boundaries -- a real coherence break,
  not just repetitive-but-fine output.
- **A verifier-gated bounded search (Path C) settles the question decisively.** We built a frozen,
  two-sided verifier (safety gain over baseline AND benign-utility preservation; ungameable -- "do
  nothing" fails the first, "refuse everything" fails the second) and searched the theory's best-motivated
  control levers, including the previously-unimplemented free-energy barrier
  `Phi=lambda*g_R*sigma(q.u_q)*sigma(k.u_k)` (Sec. 5 of the derivations). On Qwen2.5-0.5B-Instruct
  (baseline safety 0.75, utility 0.97) **every one of seven configurations reduced BOTH safety
  (-0.25 to -0.375) and utility (-0.29 to -0.35)**. Inspected continuations confirm the mechanism: the
  intervention collapses generation into token loops, destroying the aligned baseline's existing coherent
  refusals as well as benign text. The surgical-barrier hypothesis is falsified at this layer/scale/decoding.

Repo support:

- `results/gpt2_family_behavior_failure_note.md`
- `results/gpt2_medium_head_selection_note.md`
- `results/qwen_generation_intervention_note.md` (pre-fix, layer 21)
- `results/qwen_generation_intervention_fixed_note.md` (post-fix, layer 10)
- `results/qwen_generation_norepeat_note.md` (repetition-controlled confirmation)
- `results/defense_loop_note.md` + `results/defense_loop_state.csv` (verifier-gated Path C search)

Safe wording:

> Generation probes are negative-control ablations showing that null mass is not equivalent to safe control, on both an unaligned model (GPT-2-family, no trained refusal behavior) and an aligned model (Qwen2.5-0.5B-Instruct, working baseline refusal) alike. A verifier-gated search over the theory's best-motivated control levers -- including the free-energy barrier designed to be surgical -- reduced both safety and benign utility relative to an already-strong baseline, by collapsing generation into loops. This is the strongest form of the detection-vs-control boundary: not an untried gap, but a principled search for control that failed in a mechanistically interpretable way.

Avoid:

> The barrier or any structured attractor was not tried -- it was, under a frozen ungameable verifier, and it failed. Do not present generation-time control as merely future work that would obviously succeed.

Paper role:

> This result closes the diagnostic loop: it shows why the method should be presented as thermodynamic detection/diagnosis, while future control should use refusal/redirection attractors or `Phi(Q,K,X)` barriers.

Avoid:

> The intervention prevents jailbreaks.

## Claim 6: Head-local response is more controlled than all-head attraction

Evidence:

- GPT2-medium head selection found heads with high jailbreak-vs-benign null-mass separation.
- Top-6 selected heads reduced benign null mass to `0.019`, but did not solve unsafe continuations.

Repo support:

- `results/gpt2_medium_head_risk_separation.md`
- `results/gpt2_medium_head_selection_note.md`

Safe wording:

> Head selection supports the diagnostic distinction between local phase response and global degeneration.

Avoid:

> Selected heads are a complete intervention policy.

## Claim 7: GPT-2-family results are scoped by the absence of trained refusal behavior

Evidence:

- Post-hoc basin-energy diagnostics (`E_safe = -cos(h, a_safe)`, basin competition, subspace analysis) show
  flat, noise-level separation (`sep(margin)` ~0.005-0.03) at every hidden layer on distilgpt2, with
  single-anchor and multi-pair-subspace margins consistently *disagreeing* in sign (correlation -0.4 to
  -0.9).
- The identical, unmodified diagnostic run on `Qwen/Qwen2.5-0.5B-Instruct` (RLHF/safety-tuned, comparable
  parameter count) instead shows separation growing monotonically with depth (a ~25x increase from layer
  6 to layer 21 of 24) and strong agreement between the two independent margin constructions (correlation
  0.80 to 0.97).

Repo support:

- `results/basin_energy_diagnostic_note.md`
- `results/basin_energy_qwen_report.md`
- `thermosafety/basin_energy.py`, `scripts/evaluate_basin_energy.py`

Safe wording:

> The basin-energy method is validated by contrast: it produces a coherent, depth-growing signal on an
> aligned model and no signal on GPT-2-family models, consistent with GPT-2-family lacking trained refusal
> behavior to detect. Every GPT-2-family result in this paper (null-attractor diagnostics, generation-
> intervention failures, semantic-attractor smoke tests) should be read within that scope.

Avoid:

> The GPT-2-family results show the method does not work.

## Claim 8 (retracted as originally stated -- see Claim 9 for the corrected version): apparent cross-diagnostic depth-boundary agreement

Original evidence (now understood to be partly a mechanism artifact, not independent corroboration):

- On Qwen2.5-0.5B-Instruct, the basin-energy margin (cosine similarity to anchor centroids in hidden-state
  space) and the original null-attractor observables (`m_null`, entropy, spectral gap; risk-gated attention-
  logit competition) were computed independently, using unrelated mathematical constructions, at the same
  set of layers.
- Both diagnostics appeared to collapse at the same two final layers (22-23 of 24): the basin-energy
  correlation between its two margin constructions dropped from `0.97` to `~0.1-0.2`, and `m_null` crashed
  back to near zero regardless of prompt risk or label.
- Direct inspection of native attention weights confirmed a growing single-token attention sink builds
  steadily from layer 6 to layer 21 (mass `0.63` to `0.81`), then dissolves at layers 22-23 (dominant
  token switches, mass drops to `0.34-0.38`). Confirmed across 12 prompts spanning 6 suites.

**Why this is retracted as "independent agreement":** the `m_null` collapse at layers 22-23 was later
found (Claim 9) to be substantially caused by the null slot's hardcoded-zero logit failing to compete
against the strengthening sink there, not a property of risk-conditioned response. After fixing the null
slot's design (`null_key_mode="mean_logit"`), `m_null`-based separation at layers 22-23 is `0.21-0.22` --
strong, not collapsed. The attention-sink dissolution itself is real and confirmed (12 prompts, 6 suites),
but it does not imply the null-attractor mechanism's response should collapse there; that inference was an
artifact of the old design, not the sink dissolution itself. The basin-energy diagnostic's own collapse at
layers 22-23 (a hidden-state cosine-similarity measurement, unaffected by this fix) still stands, but
should now be treated as a single-diagnostic finding, not corroborated cross-diagnostic agreement, until
independently replicated by something not downstream of the fixed null-key mechanism.

Repo support:

- `results/null_attractor_depth_diagnostic_note.md` (sections "Verified mechanism" and the correction in
  "Root-cause fix")

Avoid:

> Two independent diagnostics agree on a structural boundary at layers 22-23. (Retracted -- one of the two
> was measuring an artifact of the mechanism being fixed in Claim 9.)

## Claim 9: fixing the null slot's hardcoded-zero logit removes the layer-baseline confound and corrects the depth curve

Evidence:

- The null slot's attention logit was hardcoded to `0` (`thermosafety/intervention.py`, not computed from
  an actual key vector), so its baseline competitiveness against real attention depended on each layer's
  natural logit scale, independent of risk. A risk=0 control sweep showed this confound was large and
  layer-dependent: 6.7% at layer 23 up to 83% at layer 6 of raw jailbreak `m_null` was present even with
  risk-gating fully disabled (see the retracted Claim 8 and the "Risk=0 control" section of
  `results/null_attractor_depth_diagnostic_note.md` for the pre-fix numbers).
- Fixed by computing the null logit as the mean of the real, causally-valid logits at that query position
  (`null_key_mode="mean_logit"`, now the default; `null_key_mode="zero"` preserves the old behavior for
  comparison). Verified with a deterministic unit test showing the null slot lands exactly at a uniform
  share regardless of the real logits' absolute scale, unlike the old hardcoded-zero design.
- Rerunning the full depth sweep with the fix: baseline fraction is now a stable, small 6.7-8.3% at
  *every* tested layer (2 through 23), and risk-attributable separation is substantial and roughly flat
  across nearly the whole depth range (`0.17-0.26`), rather than the narrow, artifact-inflated 6-21 band
  found before the fix. Layer 10 is the best-supported layer under the corrected metric
  (risk-attributable sep `0.257`), not layer 21 as originally selected.

Repo support:

- `thermosafety/intervention.py` (`build_null_logits`)
- `tests/test_intervention.py` (`test_build_null_logits_*`, `test_mean_logit_mode_flattens_layer_baseline_null_mass`)
- `results/null_attractor_depth_qwen_fixed_{summary,report}.{csv,md}`
- `results/null_attractor_depth_diagnostic_note.md` (section "Root-cause fix")

Safe wording:

> The null-attractor mechanism's layer-baseline confound has been fixed and verified, not merely
> characterized. Risk-attributable separation survives the fix and is now more robust (flat across nearly
> the whole depth range) than the pre-fix result suggested, but the specific "peak layer" and the
> layers-22-23-collapse narrative from the pre-fix analysis do not survive and should not be cited.

Avoid:

> The pre-fix depth curve and the fixed depth curve tell the same story with minor corrections; they
> disagree on which layers show the effect and on whether there is a final-layer collapse at all.

(The risk=0 control that originally diagnosed this confound, and its initial "layers 10/20 over 21"
correction, are superseded by Claim 9 above, which fixes the root cause rather than only working around
it. See `results/null_attractor_depth_diagnostic_note.md` for the full before/after history.)
