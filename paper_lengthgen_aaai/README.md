# AAAI-27 submission package

This directory contains a focused AAAI-27 submission and its technical supplement.

## Canonical files

- `main_submission.tex`: page-budgeted main paper.
- `main_submission.pdf`: compiled anonymous submission.
- `supplement_submission.tex`: proofs, complete protocols, extended results, and negative replications.
- `supplement_submission.pdf`: compiled supplementary document.
- `main.tex`: preserved full research manuscript and experiment record. It is not the submission file.
- `references.bib`: shared bibliography.
- `figures/`: generated paper figures.
- `ReproducibilityChecklist.tex`: AAAI checklist source; complete it before submission.

## Framing

The main claim is the capacity--assignment--utility account of task-conditioned attention routing.
The standard Gibbs/free-energy identity appears only as cited background explaining competition for evidence
mass. Entropy, variance, norms, and related global quantities are controls or invariants, not independent
thermodynamic contributions.

The paper makes three linked claims:

1. The sorted attention spectrum determines available selective capacity but cannot identify which token
   receives it.
2. Spectrum-preserving assignment changes the output only through the utility of the moved values and the
   frozen downstream network.
3. Matched interventions support this conditional routing law on controlled and pretrained models, while
   saturation, circuit-selection, arity, and natural-length tests define its boundaries.

The four main figures follow one sequence: Figure 1 defines what changes, Figure 2 tests whether assignment
matters, Figure 3 explains the capacity and utility mechanism, and Figure 4 maps transfer and boundary
regimes. The main paper also includes seed, head-budget, layer, and cross-family identification audits.

## Build

Run PDFLaTeX, BibTeX, and PDFLaTeX twice from this directory:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error main_submission.tex
bibtex main_submission
pdflatex -interaction=nonstopmode -halt-on-error main_submission.tex
pdflatex -interaction=nonstopmode -halt-on-error main_submission.tex
```

Repeat with `supplement_submission` for the supplement.

Regenerate the submission figures from checked-in result artifacts with:

```powershell
python scripts/make_selection_overview_figures.py
python scripts/make_main_result_figure.py
python scripts/make_selection_over_scale_figures.py
python scripts/make_pretrained_summary_figure.py
python scripts/make_natural_length_figure.py
python scripts/make_lengthgen_paper_figures.py
python scripts/analyze_patch.py
```

The submission sources include the generated 600 dpi PNG copies. The PDF copies remain available as editable
research artifacts, but raster inclusion prevents figure-font incompatibilities in the submitted PDFs.

## Submission checks

- The main PDF uses the official AAAI-27 two-column submission style.
- The current main PDF has 7 technical-content pages plus 1 reference page.
- No font, margin, or line-spacing compression is used.
- Essential theorem statements, proof arguments, causal design, headline results, and boundaries remain in
  the main paper.
- The supplement contains full proofs, complete result tables, secondary figures, and negative replications.
- Complete and include the reproducibility checklist before upload.
- Anonymize the code and data package before submission.
