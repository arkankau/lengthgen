# Workshop submission — InterpScience @ NeurIPS 2026 (Sydney)

Non-archival workshop version of the AAAI submission (`../paper_lengthgen_aaai/main_submission.tex`).
The AAAI source is **untouched**; this is a separate copy so the two never diverge by accident.

## Venue facts (verified 2026-08)
- **Deadline: September 1, 2026 (AoE)** — the Aug 28 date on the CFP page is struck through.
- **Non-archival**, poster presentation, Dec 11–12, Sydney. This is what makes concurrent AAAI review
  compliant: AAAI-27 explicitly permits "preprint servers (such as arXiv) and non-archival workshops."
- **Long track: 9 pages main text.** References and appendices do **not** count.
- Double-blind. NeurIPS or ICLR format for submission; NeurIPS format required for camera-ready.
- Their dual-submission rule bars only (a) work already *published* at an ML conference and (b) work under
  review at *another workshop*. Concurrent AAAI review is neither.
- Fabricated citations are an automatic desk reject. The bibliography was verified entry by entry
  (all 20 used citations resolve to real papers with correct metadata).

## How to compile
There is no local LaTeX toolchain, so use Overleaf:
1. Start from the official NeurIPS 2026 template (it supplies `neurips_2026.sty`), or download the style
   file from https://neurips.cc/Conferences/2026/CallForPapers.
2. Upload `main.tex`, `references.bib`, and `figures/`.
3. Compile with pdfLaTeX. `\usepackage[final]{neurips_2026}` is set; for the anonymous submission build use
   the style's submission mode so author identity is suppressed.

## The one open risk: page count
Main text is roughly 4,400 words plus 5 figures and 1 wide table, which lands near **10–11 pages** in
single-column NeurIPS format against a **9-page limit**. This must be checked on the first compile.

Cut levers, in the order I would apply them (each loses no result — content moves to the appendix, which is
unlimited):
1. Move `fig_routing_overview` (the Paris/Tokyo illustration) to the appendix. Saves ~1 page.
2. Compress **Related Work** from four paragraphs to two; the "Closest attention interventions" paragraph can
   keep its citations while dropping per-method description.
3. Move the "Interventions and estimation" statistical machinery (matched-control equation, cluster tests,
   Holm family) to an appendix subsection, leaving three sentences in the main text.
4. Move `fig_natural_length_ladder` to the appendix and describe the divergence in text.
5. Shrink Table 1 to the pretrained block only, full table to appendix.

Already applied: the replication audits and the paired-protocol schematic are in the appendix
(Appendices A and B).

## Differences from the AAAI version
- **The method is named here: SPS, the spectrum-preserving swap.** Defined at first use in the abstract and
  again in the introduction, then used as shorthand. The name states the invariant the method holds fixed
  (the sorted weight multiset) rather than anything about a mean, which would be both wrong and vacuous since
  an attention row always sums to one. Adjectival uses ("fixed-spectrum condition", "fixed-spectrum
  assignment") are left as they were.
- Retitled to lead with identification: *Attention Concentration Does Not Identify Routing:
  Spectrum-Preserving Swaps Separate Capacity from Assignment.*
- Abstract gained a measurement-validity framing sentence (permutation-invariant statistics cannot vary with
  the quantity a routing claim is about).
- "Background" became "Introduction" and now opens on the identification problem rather than the
  length-generalization phenomenon, matching the workshop's call (measurement validity, identifiability,
  falsifiability, evaluation design).
- Two-column floats converted to single-column; `\columnwidth` to `\linewidth`.
- No new experiments and no changed numbers. Every statistic is the AAAI value.

## Before submitting — human action required
- [ ] **Reciprocal reviewer**: at least one author must sign up (2–3 papers, Sept 3–17) at
      https://forms.gle/DCUMr9WMWwn3pN6FA, or file an exception on the submission form. Mandatory.
- [ ] Verify page count ≤ 9 on Overleaf; apply cut levers above if over.
- [ ] Upload `../paper_lengthgen_aaai/supplement_submission.pdf` as supplementary material so the 12
      "supplementary material" references in the text resolve.
- [ ] Confirm no author-identifying text or PDF metadata (double-blind).
- [ ] Decide Sydney attendance — remote slots are not promised, though a colleague may present the poster.
- [ ] Submit on OpenReview.
