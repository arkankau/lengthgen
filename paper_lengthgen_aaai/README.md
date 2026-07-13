# AAAI build: selection over scale in transformer length generalization

AAAI 2027 style (`aaai2027.sty` / `aaai2027.bst`), two-column, submission mode.
Title: "Selection over Scale in Transformer Length Generalization".

**Framing (positive, ground-up).** The paper leads with its own thesis: the property that supports length
generalization on retrieval is attention staying concentrated on the token holding the answer (predicts
accuracy r=0.97). Attention-output variance is introduced neutrally as one *candidate* statistic we measured
and found to be a symptom (predicts r=0.59; an intervention that holds it constant does not transfer to
behavior and costs accuracy under RoPE). It never argues another paper is wrong; `\citep{vanishingvariance}`
appears only as the source of the variance candidate and its intervention. No "versus / adjudicate / remedy
/ two accounts / their fix" language.

Prose follows the vibetest paper style: plain declarative sentences, one per source line, no em-dashes,
no "X, not Y" / "X rather than Y" rhetorical constructions.

## Files
- `main.tex` — the paper (AAAI format).
- `references.bib` — 14 refs, all verified against arXiv abstract pages (title/authors/year/class), all
  cited in the text, no `[VERIFY]` placeholders. Candidate correlates: vanishingvariance (2504.02827),
  nopeentropy (2404.12224), ssmax (2501.19399), sparselong (2506.16640), zhai (2303.06296). Positional
  encoding + downstream: rope (2104.09864), kazemnejad (2305.19466), fope (2412.17739), postnorm (2510.08341).
  Length-gen task/overview: anil (2207.04901), mcleish (2405.17399).
- `figures/` — 7 figures placed inline through the story (see map below).
- `ReproducibilityChecklist.tex` — AAAI requires this; fill and include before submitting.

## Compile
No local LaTeX. Upload this folder to Overleaf and compile (pdfLaTeX + BibTeX + pdfLaTeX x2).
`\usepackage[submission]{aaai2027}` is anonymous; switch to `[camera]`/remove for camera-ready per the kit.

## Figure placement (inline through the story, in the new positive order)
The results lead with the thesis, then the co-varying statistic, then the intervention:
1. `fig:attnlen` (attention on source predicts accuracy) — §4.1, the operative variable, LEAD.
2. `fig:causal` (attention r=0.94 vs variance r=0.45 as predictors) — §4.1.
3. `fig:var` (variance also collapses) — §4.2, the co-varying candidate.
4. `fig:prepost` (intervention holds the statistic constant) — §4.3.
5. `fig:acc` (accuracy vs length, all cells) — §4.3, next to the main table.
6. `fig:benefit` (intervention effect ≤0, worse under RoPE) — §4.3.
7. `fig:attnfix` (intervention lowers attention on source under RoPE) — §4.4.

All 7 are single-column `figure[t]` at `\columnwidth`, so they flow inline with the text in column order
(no wide `figure*` floats, which in two-column can only sit at a page top and bunch away from their text).
Only Table 1 is a wide `table*`. All figures are regenerated at column-friendly (portrait/compact) sizes by
`scripts/make_lengthgen_paper_figures.py` (run with `.venv/Scripts/python.exe`; matplotlib lives in `.venv`).

## Before submitting
- Citations already verified against arXiv (2026-07-13). Re-check only if entries are added.
- Fill the ReproducibilityChecklist.
- Check the page budget for the target track and trim if needed.
- Anonymize a code/data snapshot.

The `article`-style draft in `../paper_lengthgen/` is superseded by this AAAI version.
