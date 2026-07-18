# Fixed-Spectrum Attention Routing: Anonymous Reproduction Package

This package accompanies the anonymous submission. It contains the paper-specific training, intervention,
preprocessing, analysis, and figure code; preregistrations; competence failures; and saved result artifacts.
Model checkpoints are omitted because the controlled models can be retrained and the pretrained checkpoints
are publicly hosted.

## Layout

- `colab/`: controlled-model training and all controlled, pretrained, arity, selector, natural-QA, and
  activation-patching runners used by the paper.
- `scripts/`: analysis and figure builders, including the reviewer-hardening analysis.
- `tests/`: paper-specific intervention and analysis tests.
- `results/lengthgen/`: saved configurations, raw paired outputs, summaries, preregistrations, and negative
  competence-gate results.
- `paper_lengthgen_aaai/figures/`: generated paper figures.
- `MANIFEST.txt`: complete file listing.

## Reproduce the reviewer-hardening audit

From the package root:

```bash
python scripts/analyze_reviewer_hardening.py
python scripts/analyze_controlled_utility_audit.py
python scripts/analyze_natural_displacement_mismatch.py
python scripts/analyze_activation_patching_baseline.py
python scripts/analyze_qwen_exact_replication.py
python scripts/analyze_endogenous_assignment.py
```

The first command reproduces the exact cluster sign-flip tests with Holm correction, full-circuit vacuity
analysis, active-only effect, and ceiling-robust association statistics reported in the revision.

## Regenerate figures

```bash
python scripts/make_lengthgen_paper_figures.py
python scripts/make_selection_over_scale_figures.py
python scripts/make_pretrained_summary_figure.py
python scripts/make_natural_length_figure.py
python scripts/analyze_controlled_utility_audit.py
```

## Run tests

```bash
pytest tests
```

GPU runners expose their model identifiers, seeds, precisions, sample counts, and output directories through
command-line arguments. The included Colab runbooks cover the long controlled grid, pretrained family probes,
activation-patching comparison. `colab/run_reviewer_critical_suite.py` runs the exact Qwen replication,
six-seed natural-QA extension, and endogenous distractor-order audit. Later pretrained audits were run on an NVIDIA T4 runtime. Earlier saved
controlled artifacts did not retain the exact accelerator model or package-version snapshot; this limitation is
disclosed in the supplement and checklist rather than reconstructed after the fact.

All files are anonymized and contain no repository history or author metadata. The package will be released
under a research-friendly license upon acceptance.
