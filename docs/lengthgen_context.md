# Length Generalization Project Context

This is the current handoff context for the length-generalization work in this repo.

Repo: https://github.com/arkankau/lengthgen

Local root: `thermo-safety/`.

The length-generalization work is the active focus.

Do not invent results or citations.

Everything below is verified.

## Paper

Title: "Selection over Scale in Transformer Length Generalization".

Location: `paper_lengthgen_aaai/main.tex`.

The paper uses AAAI 2027 style files: `aaai2027.sty`, `aaai2027.bst`, and natbib `\citep`.

Bibliography entries are verified against primary paper pages (arXiv, ACL Anthology, OpenReview, or the
publisher).

All bibliography entries are cited.

The thesis is positive and non-adversarial.

The internal property that supports length generalization on retrieval is attention staying concentrated on the token holding the answer.

This is "attention on the correct source".

Attention-output variance is a co-varying symptom.

Attention-output variance is not the controlling variable.

The paper never argues that another paper is wrong.

The variance account from Li et al., arXiv:2504.02827, is cited neutrally as one candidate account that we measured.

## Evidence

The primary controlled grid uses 4-layer decoder transformers with `d_model=256` and is replicated at
8 layers with `d_model=512`.

Training length is 1 to 5.

Evaluation goes to 50x length, equal to length 250.

Correlational evidence:

Attention-on-correct-source predicts per-token accuracy with within-cell `r=0.97`.

Attention-on-correct-source predicts per-token accuracy with pooled `r=0.94`.

Attention-output variance predicts per-token accuracy worse, with within-cell `r=0.59`.

Attention-output variance predicts per-token accuracy worse, with pooled `r=0.45`.

Variance intervention evidence:

The variance intervention is post-attention LayerNorm.

It provably holds downstream variance constant.

It does not improve length generalization.

The paired benefit is `<=0` in all cells.

It lowers accuracy under RoPE.

Interventional causal-control evidence:

Length-scaled logit sharpening is SSMax-style.

The setting is `loglen` with `ref=6`.

It raises attention-on-source and accuracy in proportion.

Across the 4 task-by-positional-encoding cells, the accuracy gain tracks the attention gain at `r=+1.0`.

The variance fix raises neither attention-on-source nor accuracy.

The verdict is partial.

Only `argmax/NoPE` clears the pre-registered `+0.05` bar.

`argmax/NoPE` gives `+0.083` across `4/4` seeds.

`argmax/RoPE` is the one cell where attention did not rise and accuracy did not improve.

This is consistent with the account.

Math evidence:

The paper cites, rather than claims, the standard weighted-sum variance identity, Gibbs/free-energy form of
softmax, rearrangement inequality, and smoothness remainder.

The group free-energy identity is exact:
`m_S = sigmoid((F_D-F_S)/T)`.
It is used to describe evidence-versus-distractor competition without claiming that raw distractor count
alone determines failure.

The new capacity--assignment theorem fixes a complete sorted attention spectrum and decomposes evidence
mass as `m_S = C_r^- + rho_S K_r`.
It proves that permutation-invariant concentration statistics cannot identify task-correct routing and gives
the exact affine output-margin range over all assignments.

The new nonlinear routing-margin theorem identifies the first-order effect of a spectrum-preserving source
swap as transferred mass times the local source-versus-distractor value-utility gap, with a quadratic
smoothness remainder.

The theorem does not say attention alone guarantees correctness.
It requires positive downstream utility and controlled curvature, and explicitly permits source-max to fail
when those conditions do not hold.

Fixed-spectrum evidence:

- Source-max raises per-token accuracy by `+0.153`.
- Source-min lowers it by `-0.043`.
- A distractor-only permutation changes it by `+0.011`.
- Every sorted-spectrum invariant is preserved to below `1e-6` numerical error.

Capacity-by-assignment factorial:

- Sharpening raises mean maximum attention weight from `0.362` to `0.655`.
- The source-max minus source-min contrast grows from `0.196` to `0.346`.
- The interaction is `+0.151`, bootstrap 95% interval `[0.094, 0.210]`, positive in `15/16` models.
- Sharpening without reassignment changes accuracy by at most `+0.009`.

Value-utility audit:

- `1,024` examples across the 16 controlled models.
- First-order versus exact finite margin change: Pearson `0.917`, Spearman `0.989`.
- Sign agreement: `99.5%`.
- Positive active utility gaps: `89.2%`.
- Mean absolute nonlinear residual: `1.19`; this is a local theorem test, not a global linearity claim.

Multi-evidence causal evidence:

- The `pairadd` task requires routing two independently marked digits and computing their sum modulo ten.
- Eight models across NoPE/RoPE and four seeds all reach `1.0` train-length exact match.
- At `5x` length, natural exact match is `0.484`, evidence-max is `0.550`, evidence-min is `0.194`, and the evidence-mass-preserving control is `0.507`.
- Evidence-max minus control is `+0.043`, bootstrap 95% interval `[0.017, 0.072]`.
- Evidence-max minus evidence-min is `+0.356`, interval `[0.257, 0.450]`.
- The complete selected-head spectrum is preserved exactly; maximum derived-invariant error is `4.77e-7`.
- This extends the routing law to one learned `r=2` computation. It does not establish sufficiency for unrestricted reasoning.

Pretrained-family evidence:

- Pythia-1.4B and Qwen2.5-1.5B show joint accuracy and selected-head source-attention decline.
- Gemma-2-2B retains approximately flat accuracy while mean source attention declines.
- Source attention is the strongest within-length candidate in four of five head-set probes.
- Gemma rules out a universal mean-attention failure law and supports a model- and task-dependent threshold.
- These probes are observational; controlled scratch-model interventions carry the causal claim.

Pretrained causal implementation:

- `colab/pretrained_causal_routing.py` applies source-max, source-min, and distractor-control permutations inside a selected pretrained attention layer.
- `colab/pretrained_utility_selection.py` compares natural-source-mass selection with independently calibrated first-order utility-gain selection on matched evaluation examples.
- It supports GPT-NeoX, Qwen2, Gemma2, and Llama-style grouped-query or multi-head attention through a Transformers attention backend.
- It records paired accuracy and output-margin changes plus exact spectrum-invariant diagnostics.
- Pythia-70M has a 128-example validation run, but its baseline task competence is too weak for a paper claim.
- Qwen2.5-1.5B has a full 128-example-per-length run at 5, 20, 80, and 160 pairs. Source-max improves accuracy by `+0.102`, `+0.188`, `+0.109`, and `+0.062`; all paired 95% intervals exclude zero.
- Source-max improves the correct-answer margin by `+1.177` to `+2.527` logits, source-min lowers it at every length, and the maximum spectrum-invariant error is `4.77e-7`.
- Qwen2.5-7B is complete in NF4 with bfloat16 computation and 96 paired examples at 5, 20, and 80 pairs. Source-max minus control raises the output margin by `+0.185`, `+0.747`, and `+0.773`; every paired 95% interval excludes zero.
- At 20 pairs, source-max beats control by `+0.125` accuracy with interval `[+0.062,+0.198]`. The 80-pair baseline accuracy is `0.010`, so that cell is informative in margin space but floor-limited in accuracy.
- The initial FP16 NF4 attempt produced NaN margins and is retained as a failed numerical configuration. BF16 corrected it.
- Pythia-1.4B is complete with 128 paired examples at 5, 20, and 80 pairs. Source-max minus control margin intervals exclude zero at every length.
- At five pairs, source-max beats control by `+0.070` accuracy (`[+0.016,+0.133]`) and `+0.639` margin (`[+0.400,+0.887]`), while source-min lowers baseline accuracy by `-0.250` and margin by `-2.480`.
- At 80 pairs Pythia baseline accuracy is exactly zero, so the tail supports the margin prediction but cannot test accuracy rescue; source-min also loses its negative margin sign there.
- Gemma-2-2B is complete with 128 paired examples at 5, 20, and 80 pairs and retains `0.711`--`0.758` baseline accuracy.
- Gemma source-max versus control is statistically neutral at all lengths. Source-min lowers accuracy by `-0.094`, `-0.133`, and `-0.117` and margin by `-1.680`, `-1.341`, and `-1.096`; every paired interval excludes zero.
- Natural Gemma source mass remains high (`0.670 -> 0.440`), and source-max adds `0.059`--`0.129` without improving behavior. This is the high-competence saturation boundary allowed by the theorem's utility condition.
- The causal package now spans Qwen2, GPT-NeoX, Gemma2, and Llama architectures.
- The pretrained utility-gap audit is complete on Qwen2.5-1.5B, Pythia-1.4B, and Gemma-2-2B at 5 and 20 pairs with 64 examples per cell and independent calibration/evaluation RNG streams.
- Source-max first-order versus exact Spearman correlations are `0.798/0.866` for Qwen, `0.647/0.448` for Pythia, and `0.496/0.572` for Gemma. Every cell has positive association, and source-min has the predicted negative mean effect throughout.
- The Qwen causal selection audit is complete for seeds `0,1,2`, head counts `2,4,8`, adjacent layers, and deterministic random layers. All `9/9` selected seed-by-K margin intervals exclude zero; selected cells average `+0.874` versus `-0.059` for random-layer controls.
- Utility-gap seeds `1` and `2` are complete for Qwen, Pythia, and Gemma. Across seeds `0,1,2`, all `6/6` source-max cells have positive association in every model; mean seed-level Spearman is `0.866` for Qwen, `0.544` for Pythia, and `0.554` for Gemma. Gemma's mean exact source-max effect is only `+0.050`, preserving the high-competence saturation boundary.
- The preregistered `equals_newline` format preserves the source-max and source-min directions at 5, 20, and 80 pairs but fails competence with baseline accuracy `0.164`, `0.203`, and `0.023`.
- A blinded baseline-only pilot selected `arrow_newline` from three held-out candidates. Its full seed-zero run failed competence (`0.156`, `0.117`, `0.008` accuracy), although source-max minus control margin stayed positive (`+4.633`, `+3.558`, `+0.674`) and source-min stayed negative. The locked second-format gate therefore fails.
- SmolLM2-1.7B passed the Llama competence pilot (`0.594` at five pairs) and backend smoke test. In the full run, baseline accuracy was `0.945`, `0.516`, and `0.023`, but source-max minus control margin was `-0.018`, `-0.199`, and `-0.056`; source-min remained negative in the two competent cells. The Llama source-max gate fails, showing that source-mass-only head selection is not architecture-universal.
- A separately locked SmolLM2 utility-selection follow-up uses 64 disjoint calibration examples per seed and ranks heads by mean predicted source-max gain: transferred mass times the local source-versus-donor utility gap.
- At five pairs, all three independent calibrations pass. Pooled baseline accuracy is `0.956`; utility-selected source-max minus control margin is `+0.702` with a two-level seed-and-example interval `[+0.529,+0.858]`, versus `-0.021` (`[-0.057,+0.014]`) for source-mass selection. The paired utility-minus-mass effect is `+0.723` (`[+0.544,+0.882]`) and the accuracy effect is `+0.052`.
- At 20 pairs the utility margin effect is positive in all three seeds and pools to `+2.200`, but pooled untouched accuracy is `0.432`, below the locked competence gate. Seed zero supplies the 80-pair diagnostic (`+0.163` margin, baseline accuracy `0.023`); seeds one and two omit that optional tail to prioritize confirmatory cells.
- The equal-budget selector ablation is complete over ten calibration seeds. Source-gradient selection ranks first at `+0.750` max-minus-control margin, utility gain ranks second at `+0.600`, and utility gap ranks third at `+0.296`; source mass is `-0.040` and random selection is `-0.019`. Utility gain minus source gradient is `-0.150` with a calibration-seed bootstrap interval `[-0.274,-0.026]`. The utility-specificity rule therefore fails, while the broader output-conditioned selection claim survives.
- The raw interpolation audit is restored over five calibration seeds. Mean source-max-minus-matched-control margin is `0.000`, `0.446`, `0.817`, `1.128`, and `1.417` at alphas `0`, `0.25`, `0.5`, `0.75`, and `1`; every seed is nondecreasing and the hierarchical endpoint interval is `[+1.332,+1.514]`.
- The amended context-dependent SQuAD multiple-choice test passes the locked 64-calibration/128-evaluation design over seeds `0,1,2`. Full-context rescue on no-context failures is `0.981`, `0.966`, and `0.951`. Utility-selected source-max-minus-control margin pools to `+0.336` with hierarchical interval `[+0.176,+0.512]`; source-mass selection is `-0.112` (`[-0.188,-0.043]`). Unconstrained next-token accuracy changes by `+0.008` (`[0.000,+0.021]`), and eight-token greedy decoding adds no first-answer or repetition cost.
- The registered variable-evidence stage is complete for pair, triple, and quadruple modular sum under NoPE/RoPE and seeds `0,1`. Pair and triple models reach perfect train exact match, but the triple max-minus-control effect is `-0.001` (`[-0.009,+0.008]`). Quadruple evidence fails the competence gate with minimum train exact match `0.090`. The positive set-routing result therefore remains supported through two sources, not arbitrary arity.
- The equal-budget selector-family comparison is complete on Qwen2.5-1.5B, Pythia-1.4B, and SmolLM2-1.7B over three seeds each. Utility gain ranks first on Pythia (`+0.519`) and SmolLM (`+1.253`) but second on Qwen, where utility gap, utility gain, and source gradient tie near `+1.49`. The strict universal-selector claim fails; the broader output-conditioned-selection result replicates.

## Positioning

The paper is positioned as a theory-backed mechanistic study with controlled causal evidence and
observational pretrained-family validation.

The novelty is the task-labeled capacity--assignment decomposition, its routing-margin specialization, and
the matched interventions that independently vary capacity and assignment.

The novelty is not the thesis that attention concentration matters.

The standard softmax/free-energy identities, variance identity, rearrangement inequality, and Taylor
remainder are not novel and are cited compactly.

The paper-specific mathematics is the way these tools are assembled into a source-labeled routing theorem,
non-identifiability result for global concentration statistics, and a measurable nonlinear utility-gap
condition.

## Key Files

Trainer:

`colab/length_gen_colab.py`

The trainer is self-contained and intended to run on GPU.

Important flags:

`--tasks`

`--seeds`

`--attn-scale {none|loglen|fixedK}`

`--attn-ref`

`--n-layers`

`--d-model`

`--batch`

`--outdir`

Tasks:

`argmax`: argmax retrieval.

`pairadd`: two independently marked digits whose answer is their sum modulo ten; both evidence positions are required.

`flagret`: flag retrieval.

`addition`: reversed decimal, order-dependent contrast.

`recall`: untrained.

Analysis scripts:

`scripts/analyze_lengthgen_json.py`

`scripts/analyze_causal.py`

`scripts/analyze_causalB.py`

`scripts/analyze_concentration_assignment.py`

`scripts/evaluate_routing_utility_gap.py`

`scripts/analyze_multievidence_routing.py`

`scripts/analyze_pretrained_causal_routing.py`

`scripts/analyze_pretrained_critical.py`

`scripts/analyze_pretrained_utility_selection.py`

`scripts/audit_lengthgen_experiment_coverage.py`

Figures:

`scripts/make_lengthgen_paper_figures.py`

`scripts/make_lengthgen_causalB_figure.py`

`scripts/make_selection_over_scale_figures.py`

Utilities:

`scripts/merge_lengthgen_json.py`

`scripts/recover_from_log.py`

Data:

`results/lengthgen/gpu_resultsA.json`

This contains baseline plus variance-fix results, 32 configs, 4 seeds.

`results/lengthgen/gpu_resultsB.json`

This contains loglen results, 16 configs.

`results/lengthgen/gpu_resultsAB.json`

This contains the merged 48 configs.

`results/lengthgen/gpu_results.json`

This contains 40 configs, including addition.

`results/lengthgen/multievidence_grid_minimal/paired_permutation_results.json`

This contains the canonical eight-model two-evidence fixed-spectrum grid.

`results/lengthgen/multievidence_summary.json`

This contains the competence gate, paired bootstrap intervals, and invariant audit for that grid.

`results/lengthgen/pretrained_causal_pythia70m/pretrained_causal_routing_results.json`

This validates the pretrained causal backend at N=128 but has weak baseline competence.

`results/lengthgen/pretrained_causal_qwen_smoke/pretrained_causal_routing_results.json`

This validates the backend on Qwen2.5-1.5B but has only eight examples per length.

`results/lengthgen/pretrained_causal_qwen1p5b/pretrained_causal_routing_results.json`

This is the paper-grade Qwen2.5-1.5B causal run with 128 paired examples at each of four lengths.

`results/lengthgen/pretrained_causal_qwen7b/pretrained_causal_routing_results.json`

This is the Qwen2.5-7B NF4/bfloat16 scale replication with 96 paired examples at each of three lengths.

`results/lengthgen/pretrained_causal_qwen7b_4bit_failed/pretrained_causal_routing_results.json`

This preserves the failed FP16 NF4 attempt, whose untouched baseline had NaN margins; it is not evidence.

`results/lengthgen/pretrained_causal_pythia1p4b/pretrained_causal_routing_results.json`

This is the Pythia-1.4B cross-family causal replication with 128 paired examples at each of three lengths.

`results/lengthgen/pretrained_causal_gemma2b/pretrained_causal_routing_results.json`

This is the Gemma-2-2B high-competence causal boundary run with 128 paired examples at each of three lengths.

`results/lengthgen/pretrained_causal_routing_summary.md`

This combines the pretrained causal runs and reports paired bootstrap intervals and invariant errors.

`results/lengthgen/pretrained_critical_summary.md`

This combines the preregistered prompt-format, pretrained utility-gap, and circuit-selection robustness audits.

`results/lengthgen/pretrained_utility_selection_summary.md`

This aggregates the three independently calibrated SmolLM2 utility-selection seeds, applies the locked competence gate, and reports paired utility-versus-source-mass effects.

`results/lengthgen/pretrained_utility_selection_preregistration.json`

This locks the utility-gain selector, disjoint calibration split, primary estimand, and success rule before the GPU outcomes.

`results/lengthgen/pretrained_critical_preregistration.json`

This freezes the critical experiment gates before the new GPU runs.

Pre-registrations:

`results/lengthgen_preregistration.md`

`results/lengthgen_causal_prereg.md`

`results/lengthgen_causalB_prereg.md`

`results/lengthgen_causalB_prereg.md` has the outcome.

## Hard Conventions

Matplotlib lives only in `.venv/Scripts/python.exe`.

Matplotlib does not live in system Python.

Run all plotting scripts with the venv Python.

Writing style is plain declarative sentences.

Use one sentence per source line.

Use concrete numbers.

Use careful hedging.

Do not use em dashes.

Do not use `---`.

Do not use constructions of the form `X, not Y`, `not X but Y`, or `X rather than Y`.

Do not use the openers `Moreover`, `Furthermore`, `Notably`, or `Crucially`.

Use no adversarial framing.

Main plots use full-width `figure*` placement so two-column text cannot wrap beside them.

Compact tables must be constrained to `\columnwidth`; wide tables use `table*`.

The current draft is 18 pages, and page-budget compression remains a submission task.

The trainer resume key is `(task, pe, post_attn_ln, seed, attn_scale)`.

The trainer resume key does not include model size.

Any different-size run must use a fresh `--outdir`.

LaTeX compiles locally with pdfLaTeX + BibTeX + pdfLaTeX twice.

## Next Steps

The Qwen2.5-1.5B, Qwen2.5-7B, Pythia-1.4B, and Gemma-2-2B paper gates have passed and are integrated into the manuscript.

Use `colab/routing_expansion_runs.ipynb` in a signed-in Colab GPU session.

The full-size natural-QA confirmation and the pair/triple/quad evidence grid are complete. The natural result passes; the variable-evidence extension supplies a clean boundary at three/four sources rather than a broader positive claim.

Do not add another model solely for family count. A larger Llama checkpoint is useful only if it has verified task competence or tests utility selection at greater scale.

Llama-3.2-3B and Gemma-2-9B are optional gated replications.

Analyze returned files with `scripts/analyze_pretrained_natural_mcqa.py`, `scripts/analyze_pretrained_selector_family.py`, and `scripts/analyze_variable_evidence.py`.

Require at least 128 paired examples per length, report paired confidence intervals, and reject cells without adequate natural baseline competence.

## First Files To Read Before Continuing

Read `paper_lengthgen_aaai/main.tex`.

Read `paper_lengthgen_aaai/README.md`.

Read `results/lengthgen_causalB_prereg.md`.

After reading those files, confirm this brief.

Then propose which next step to take.
