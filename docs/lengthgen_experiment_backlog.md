# Length-Gen Experiment Backlog

This file tracks experiments that should be run when GPU access is available, plus CPU-only tasks that can be done locally.
It is intentionally scoped to reviewer-facing evidence for the current paper, `paper_lengthgen_aaai/main.tex`.

## Must Run

### 0. Paper-grade pretrained causal routing

Goal: test the fixed-spectrum assignment prediction causally inside competent pretrained models.

Current evidence:
- The backend is validated on Pythia-70M with 128 examples per length, but natural baseline competence is weak.
- Qwen2.5-1.5B is complete with 128 paired examples at 5, 20, 80, and 160 pairs. Source-max improves accuracy at every length with paired 95% intervals excluding zero; source-min lowers the answer margin at every length.
- Qwen2.5-7B is complete in NF4/bfloat16 with 96 paired examples at 5, 20, and 80 pairs. Source-max versus control margin intervals exclude zero at every length; the accuracy effect is significant at 20 pairs and floor-limited at 80.
- Pythia-1.4B is complete with 128 paired examples at 5, 20, and 80 pairs. Source-max versus control margin intervals exclude zero throughout; accuracy is identifiable at short context and floor-limited at 80.
- Gemma-2-2B is complete with 128 paired examples at 5, 20, and 80 pairs. Source-max is neutral while source-min reliably harms accuracy and margin, giving a high-competence saturation boundary.
- SmolLM2-1.7B is complete with 128 paired examples at 5, 20, and 80 pairs. It passes the Llama-family competence and backend gates, but source-max does not beat the matched control; source-min remains negative in the two competent cells. This is a negative architecture replication for source-mass-only head selection.
- Every intervention preserves the selected-head spectrum below `1e-6` numerical error.

Run next:
- Completed: use the measured first-order utility gain, rather than natural source mass alone, to select SmolLM2 intervention heads.
- Result: at five pairs, pooled over three independently calibrated seeds, utility-selected source-max minus control margin is `+0.702` (`[+0.529,+0.858]`) and accuracy rises `+0.052`; source-mass selection remains neutral. The paired utility-minus-mass effect is `+0.723` (`[+0.544,+0.882]`).
- Boundary: the 20-pair margin effect replicates but pooled baseline accuracy is `0.432`, below competence. Only seed zero runs the optional 80-pair diagnostic.
- Selector specificity: complete over ten calibration seeds. Source gradient ranks first (`+0.750`), utility gain second (`+0.600`), and utility gap third (`+0.296`). Utility gain trails source gradient by `-0.150` (`[-0.274,-0.026]`, seed bootstrap), so the preregistered unique-selector claim fails.
- Dose response: raw per-example files are restored over five calibration seeds. The hierarchical mean path is `0.000`, `0.446`, `0.817`, `1.128`, and `1.417`; every seed is nondecreasing.
- Natural QA: the locked 64/128 context-dependent multiple-choice design passes over all three seeds. Utility-selected margin is `+0.336` (`[+0.176,+0.512]`), unconstrained answer accuracy changes by `+0.008` (`[0.000,+0.021]`), and source-mass selection is significantly negative at `-0.112` (`[-0.188,-0.043]`). Greedy decoding adds no first-answer or repetition cost.
- Selector family: complete on Qwen, Pythia, and SmolLM over three seeds. The strict universal-selector rule fails because Qwen ranks utility gap above a tied utility-gain circuit; output-conditioned selectors still dominate task-agnostic mass across families.
- Variable evidence: the pair/triple/quad stage-one grid is complete over NoPE/RoPE and seeds `0,1`. Pair and triple train competence is perfect, but triple max-minus-control is `-0.001` (`[-0.009,+0.008]`); quadruple evidence fails competence with minimum train exact match `0.090`. This is a boundary result, not evidence for generalization through arity four.
- Natural-QA length ladder: complete on Qwen full seeds `0,2` (seed `1` failed the frozen competence gate at `187/192`) and one frozen SmolLM2 replication. Qwen margin and accuracy decline from 4 to 32 passages by `-1.036` (`[-1.397,-0.698]`) and `-0.047` (`[-0.074,-0.023]`), but source mass rises and rescue amplification is negative at `-0.179` (`[-0.352,-0.005]`). SmolLM2 margin and accuracy also decline, source mass falls, and rescue amplification is null at `+0.018` (`[-0.027,+0.066]`). The preregistered mechanism claim fails; the supported result is natural-QA length degradation without a general source-mass-loss/rescue account.
- Competence-matched arity: complete as a capacity search. `c1`, `c2`, and `c3` are rejected by the frozen threshold on their first required cells (`0.184`, `0.178`, and `0.748` exact match versus `0.8`). No candidate froze, no causal arity outcome was inspected, and the four-evidence experiment remains capacity-limited.

Decision target:
- Natural baseline competence at the shortest and intermediate lengths.
- Source-max improves the target-versus-competitor margin over the evidence-mass-preserving control.
- Source-min lowers the margin.
- Paired 95% intervals and invariant errors are reported.

Colab entrypoint:
- `colab/routing_expansion_runs.ipynb`

Local analysis:
- `scripts/analyze_pretrained_causal_routing.py`

### 1. Real-model family robustness

Goal: test whether the Pythia-1.4B pretrained-model result is model-specific.

Current evidence:
- Completed: `EleutherAI/pythia-1.4b`, 8 retrieval heads, 900 examples.
- Result: accuracy drops `0.68 -> 0.19`; retrieval-head attention drops `0.48 -> 0.22`; within-length correlation ranking is attention-on-source `0.194` > participation `0.122` > negative entropy `0.100`.

Run next:
- `Qwen/Qwen2.5-1.5B`, heads 8.
- `google/gemma-2-2b`, heads 8 if access is available.
- If Gemma is gated, use `TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T` as an ungated Llama-like backup.

Decision target:
- Strong: at least one non-Pythia model shows co-decline in accuracy and retrieval-head attention, and attention-on-source is the best within-length predictor.
- Mixed: co-decline holds but within-length ranking is weaker.
- Weak: model has no dynamic range or attention-on-source is not competitive.

Colab entrypoint:
- `colab/real_model_family_runs.ipynb`

Local analysis:
- `scripts/analyze_real_model_family.py`

### 2. Head-count robustness on the best real model

Goal: show that the real-model result is not an artifact of choosing exactly 8 heads.

Run:
- Best working non-Pythia model with `--heads 4`.
- Same model with `--heads 16`.
- Keep the existing `--heads 8` run as the main row.

Decision target:
- The sign of co-decline should remain stable.
- Attention-on-source should remain competitive with participation and entropy.
- It is acceptable if the exact correlation weakens as more irrelevant heads are included.

Pretrained causal selection result:
- Complete on Qwen2.5-1.5B with independent calibration and evaluation examples, seeds `0,1,2`, and `K=2,4,8`.
- All nine selected source-max versus control margin intervals exclude zero.
- The selected cells average `+0.874` margin versus `-0.059` for deterministic random-layer controls.

### 3. Larger scratch-model replication [complete]

Goal: reduce the "toy models are small" objection.

Current evidence:
- Main grid: 4 layers, width 256.
- Replication claimed in paper: 8 layers, width 512.

Completed artifact:
- `results/lengthgen/gpu_results_scale.json` contains 32 configurations across four seeds.

Decision target:
- Attention-on-source remains the best predictor.
- Variance stabilization still does not improve length generalization.

## Can Run

### 4. Real-model task-format robustness

Goal: make sure the pretrained result is not only true for the natural key-value prompt format.

Run:
- A second retrieval formatting variant, pre-registered before running.
- Keep the same source-position extraction and retrieval-head selection logic.

Decision target:
- Co-decline should remain visible if the model has task competence.
- If the model loses competence, report as format sensitivity rather than a mechanism failure.

Current result:
- The preregistered `equals_newline` variant fails the competence gate on Qwen2.5-1.5B at 5 and 20 pairs, with baseline accuracy `0.164` and `0.203`.
- Source-max versus control margin remains positive and source-min remains negative, but this is not a valid second-format causal replication.
- The 80-pair cell is complete with baseline accuracy `0.023`; it preserves the causal directions but cannot reverse the failed competence verdict.
- A blinded pilot selected `arrow_newline`, whose full seed-zero run also fails competence (`0.156`, `0.117`, `0.008`) despite positive source-max-minus-control and negative source-min margin at all three lengths.

### 5. More seeds for the causal sharpening run

Goal: strengthen the intervention result, whose cross-cell correlation is currently based on four cells.

Run:
- Additional seeds for the `loglen` attention-scaling intervention.

Decision target:
- Accuracy gain should track attention-on-source gain.
- The result should not depend on one seed.

### 6. Direct attention patching at more lengths

Goal: make the sufficiency claim visually and statistically cleaner.

Run:
- Existing patch intervention at multiple long lengths, not only the longest length.

Decision target:
- Patching attention onto the correct source should rescue accuracy monotonically or near-monotonically as length grows.

## Optional

### 7. Natural-language retrieval benchmark

Goal: bridge synthetic key-value retrieval and more natural prompts.

Run:
- A small curated natural-language lookup task where the correct source span is known.

Decision target:
- Treat as exploratory unless source extraction and answer evaluation are locked before the run.

### 8. Closed-model API comparison

Goal: compare surface behavior only.

Constraint:
- Closed APIs do not expose attention or hidden-state internals, so they cannot directly test the operative-variable claim.

Use only as:
- Motivation or external behavior context.
- Not as core mechanistic evidence.

## CPU-Only Tasks

### A. Paper claim audit

Goal: ensure the paper does not overstate completed evidence.

Run:
- `.venv/Scripts/python.exe scripts/audit_lengthgen_experiment_coverage.py`

Expected output:
- `results/lengthgen_experiment_coverage_audit.md`

### B. Figure and table consistency check

Goal: ensure every numeric claim in the paper can be traced to an existing result file.

Run:
- Inspect generated figures under `paper_lengthgen_aaai/figures/`.
- Cross-check key values against `results/lengthgen/*.json` and `results/lengthgen/*.md`.

### C. Reviewer-response prep

Goal: prepare concise answers to predictable reviewer objections.

Objections to prepare:
- "Only Pythia?"
- "Only synthetic tasks?"
- "Is attention-on-source circular?"
- "Is the variance intervention too narrow?"
- "Does logit sharpening just change temperature?"
