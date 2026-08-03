# Reproduction Guide

Run commands from the package root. Saved-artifact analysis is CPU-only and does not download a model.

## 1. Environment

Create a fresh Python environment, then install:

```bash
python -m pip install -r requirements.txt
```

The original later pretrained runs used a Linux Google Colab runtime with one NVIDIA T4 GPU. Earlier
controlled artifacts did not retain a complete package-version and accelerator snapshot, so exact
infrastructure reproduction is partial. The saved per-example outputs are included so the reported analysis
does not depend on recreating that environment.

## 2. Verify the package

```bash
python scripts/verify_package.py
pytest -q tests
```

The verifier checks required files, JSON validity, anonymity-sensitive strings, and `MANIFEST.sha256`.

## 3. Reproduce reported analyses from saved outputs

```bash
python scripts/analyze_corrected_inference.py
python scripts/analyze_controlled_utility_audit.py
python scripts/analyze_natural_displacement_mismatch.py
python scripts/analyze_activation_patching_baseline.py
python scripts/analyze_qwen_exact_replication.py
python scripts/analyze_endogenous_assignment.py
python scripts/analyze_pretrained_selector_family.py
```

These commands regenerate machine-readable JSON summaries and human-readable Markdown reports under
`results/lengthgen/`.

## 4. Regenerate main-paper figures

```bash
python scripts/make_selection_overview_figures.py
python scripts/make_main_result_figure.py
python scripts/analyze_controlled_utility_audit.py
python scripts/make_pretrained_summary_figure.py
python scripts/make_natural_length_figure.py
```

The pretrained and natural-length builders enforce the matched seed and sample-count designs used in the
main paper.

## 5. Optional GPU reruns

The `colab/` directory contains the experiment runners and runbooks. Each runner exposes model ID, seed,
precision, sample count, and output directory through command-line arguments. Inspect the exact interface
before launching:

```bash
python colab/pretrained_causal_routing.py --help
python colab/pretrained_natural_mcqa.py --help
python colab/pretrained_natural_mcqa_ladder.py --help
python colab/pretrained_activation_patching_baseline.py --help
python colab/run_reviewer_critical_suite.py --help
```

GPU reruns download public checkpoints and, for natural QA, the public SQuAD dataset. Authentication may be
required for gated model checkpoints. No credential is included in this package.

## 6. Paper sources

The anonymous LaTeX sources and generated figures are under `paper_lengthgen_aaai/`. The submitted main and
supplement PDFs are separate upload artifacts and are intentionally omitted from the code/data ZIP.
