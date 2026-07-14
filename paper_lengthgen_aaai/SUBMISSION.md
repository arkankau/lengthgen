# Submission checklist — AAAI Main Technical Track

## Files
- `main.tex` — the paper. 6 figures + 1 table in the body (attn-vs-length, causal, intervention, patch, realmodel, decouple).
- `supplement.tex` — separate supplementary PDF. 5 supporting figures, numbered S1–S5, referenced from the body.
- `ReproducibilityChecklist.tex` — filled. Compile standalone or `\input` before `\end{document}` (check the CFP for which the track wants).
- `references.bib` — 14 verified entries, no placeholders.
- `figures/` — all 11 PDFs (6 used by main, 5 by supplement).

## Compile (no local LaTeX — use Overleaf)
1. New Overleaf project → upload the whole `paper_lengthgen_aaai/` directory (keep `figures/` as a subfolder).
2. Set the main document to `main.tex`. Menu → Compiler: **pdfLaTeX**. Bibliography runs via BibTeX automatically on recompile (or Recompile twice).
3. Build `supplement.tex` as a second output (switch the main document, or a second project). It needs the same `figures/` and `aaai2027.sty`.

## The binding constraint: 7 content pages (pages 8–9 references only)
The figure triage moved 5 figures to the supplement to fit. **You must verify the page count on Overleaf.** If `main.tex` is still over 7 pages after compiling:
- First lever: move `fig_intervention` (Section 6) or `fig_realmodel` to the supplement too — the numbers are all in the text.
- Second lever: the theory section (Section 5, Propositions 1–2) can be compressed; proofs can move to the supplement.
- Do **not** shrink figures below `\columnwidth` or drop numerical claims to save space.

## Before freezing (double-blind)
- No author names/affiliations in `main.tex` (currently none) or in the compiled PDF metadata.
- Anonymize the code snapshot for the supplement: fresh export with no git history / author identity (e.g. an anonymized mirror), and confirm no author handle in file paths or docstrings.
- Grayscale check: AAAI proceedings may print B&W — confirm every figure is legible without color (the decouple stacked bars and the co-decline lines rely on color; add hatching or markers if needed).
- Cross-check every number in the draft against its source in `results/lengthgen/*.json` one final time.

## Status
- Hygiene: braces balanced, 0 em-dashes, no "X not Y"/"rather than"/"moreover" tells, all `\ref`s resolve, S1–S5 all referenced.
- Bibliography: verified, no `[VERIFY]` placeholders.
- Open: Overleaf compile + page-count verification; grayscale legibility; anonymized code snapshot; ethics statement if the final CFP requires one.
