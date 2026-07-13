# Workshop paper: variance stabilization is decoupled from length generalization

`main.tex` — ~4-page workshop draft (decoupling-first framing).
`references.bib` — 2 citations, **both flagged to verify before submission**.
`figures/` — the two figure PDFs (regenerate with `scripts/make_lengthgen_figures.py`).

## Compile
No local LaTeX toolchain. Upload `paper_lengthgen/` to Overleaf and compile (pdfLaTeX + BibTeX), or
locally: `pdflatex main && bibtex main && pdflatex main && pdflatex main`.

To target a specific workshop: replace `\documentclass{article}` with the venue style file and drop it
in this folder. No venue-specific macros are used, so the body should port unchanged.

## Backing artifacts (for the reproducibility release)
- Data: `../results/lengthgen/gpu_results.json` (24 runs: 3 tasks x 2 PE x on/off x 2 seeds)
- Analysis: `../results/lengthgen_gpu_analysis.md` (tables + verdict) via `../scripts/analyze_lengthgen_json.py`
- Figures: `../scripts/make_lengthgen_figures.py`
- Training code: `../colab/length_gen_colab.py`
- Pre-registration (written before viewing outcomes): `../results/lengthgen_preregistration.md`

## Pre-submission checklist
- [ ] **Verify both citations** (title/authors/year) against arXiv:2504.02827 and arXiv:2404.12224.
- [ ] Re-check every number in Table 1 against `results/lengthgen_gpu_analysis.md` (all currently match).
- [ ] Pick the venue; set page limit and style; trim/expand to fit.
- [ ] Anonymize if double-blind (author block already says "Anonymous").
- [ ] Prepare an anonymized code/data snapshot for the reproducibility release.
- [ ] Optional strengthening (not required for a workshop): a faithful reproduce-their-positive-result
      run + a scale sweep would neutralize the "small-scale" limitation — see Limitations.
