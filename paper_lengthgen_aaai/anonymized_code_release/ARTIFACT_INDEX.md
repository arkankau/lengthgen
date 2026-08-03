# Artifact Index

This index maps the submission's claims to saved data and analysis entry points. Paths are relative to the
package root. Commands use saved artifacts and do not load a language model unless marked as a GPU rerun.

## Main-paper figures

| Paper item | Purpose | Primary saved data | Builder or analysis |
|---|---|---|---|
| Figure 1 | Illustrates a spectrum-preserving reassignment | Conceptual figure; no measured data | `scripts/make_selection_overview_figures.py` |
| Figure 2 | Defines calibration, frozen circuit selection, and paired evaluation | Protocol figure; no measured data | `scripts/make_selection_overview_figures.py` |
| Figure 3 | Controlled fixed-spectrum assignment effect | `results/lengthgen/paired_permutation_results.json`, `results/lengthgen/factorial_grid/` | `scripts/make_main_result_figure.py` |
| Figure 4 | Capacity scaling and held-out utility prediction | `results/lengthgen/paired_head_count_full_grid.json`, `results/lengthgen/controlled_utility_audit.json` | `scripts/analyze_controlled_utility_audit.py` |
| Figure 5 | Matched pretrained comparison at seed 0, 128 examples, and 5/20/80 pairs | `results/lengthgen/pretrained_causal_qwen1p5b/`, `pretrained_causal_pythia1p4b/`, `pretrained_causal_gemma2b/`, `pretrained_causal_smollm2_1p7b/` | `scripts/make_pretrained_summary_figure.py` |
| Figure 6 | Matched natural-QA ladder at seed 0 and 128 examples per model-length cell | `results/lengthgen/pretrained_natural_mcqa_ladder/qwen_seed0_summary.json`, `smollm2_seed0_summary.json` | `scripts/make_natural_length_figure.py` |

The Figure 5 and Figure 6 builders validate the matched seed and sample-count design and stop with an error if
the input artifacts violate it.

## Main-paper and supplement claims

| Claim or analysis | Saved data | Analysis entry point |
|---|---|---|
| Controlled concentration versus assignment | `results/lengthgen/factorial_grid/`, `paired_permutation_results.json` | `scripts/analyze_concentration_assignment.py` |
| Variance-control intervention | `results/lengthgen/variance_control_summary.json` and associated paired artifacts | `scripts/analyze_patch.py` |
| Multi-evidence arity boundary | `results/lengthgen/multievidence_*`, `competence_matched_arity_*` | `scripts/analyze_multievidence_routing.py` |
| Pretrained source reassignment | `results/lengthgen/pretrained_causal_*` | `scripts/analyze_pretrained_causal_routing.py` |
| Utility-selected SmolLM2 circuit | `results/lengthgen/pretrained_utility_selection_smollm2_*` | `scripts/analyze_pretrained_utility_selection.py` |
| Selector ablation and family transfer | `results/lengthgen/pretrained_selector_*` | `scripts/analyze_pretrained_selector_ablation.py`, `analyze_pretrained_selector_family.py` |
| Layer, head-budget, and calibration-seed controls | `results/lengthgen/pretrained_selection_qwen1p5b/` | `scripts/analyze_pretrained_critical.py` |
| Held-out pretrained utility analysis | `results/lengthgen/pretrained_utility_*` | `scripts/audit_pretrained_utility_review.py` |
| Activation-patching comparison | `results/lengthgen/activation_patching_qwen1p5b_*` | `scripts/analyze_activation_patching_baseline.py` |
| Exact Qwen replication | `results/lengthgen/pretrained_causal_qwen_exact_*` | `scripts/analyze_qwen_exact_replication.py` |
| Endogenous distractor-order comparison | `results/lengthgen/pretrained_endogenous_assignment_*` | `scripts/analyze_endogenous_assignment.py` |
| Natural-QA displacement matching | `results/lengthgen/natural_displacement_mismatch_summary.json` | `scripts/analyze_natural_displacement_mismatch.py` |
| Natural-QA fixed-context test | `results/lengthgen/pretrained_natural_mcqa_full/` | `scripts/analyze_pretrained_natural_mcqa.py` |
| Natural-QA length ladder | `results/lengthgen/pretrained_natural_mcqa_ladder/` | `scripts/analyze_pretrained_natural_mcqa_ladder.py` |
| Corrected inference, active-only effects, and ceiling-robust associations | `results/lengthgen/corrected_inference_analysis.json` | `scripts/analyze_corrected_inference.py` |

## Preregistrations and negative results

Files ending in `_preregistration.json` record frozen decision rules before the corresponding confirmatory runs.
Competence failures and excluded formats are retained in their original result directories. They are evidence
for scope decisions, not successful cells, and the supplement labels them accordingly.

## Integrity

`MANIFEST.sha256` records every package path, byte size, and SHA-256 digest. Run
`python scripts/verify_package.py` to verify the manifest, parse all JSON files, and repeat the anonymity scan.
