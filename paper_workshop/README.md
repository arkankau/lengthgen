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
MiKTeX is installed locally, so this builds here (no Overleaf needed):

```
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

`neurips_2026.sty` in this directory is the official file, extracted from
https://media.neurips.cc/Conferences/NeurIPS2026/Formatting_Instructions_For_NeurIPS_2026.zip

The `dblblindworkshop` package option is the right one for this venue: it keeps the submission anonymous
(prints "Anonymous Author(s)" and line numbers) and registers the workshop track. The workshop title set by
`\workshoptitle{...}` only appears in the page-one notice under the `final` option, so for camera-ready swap
`dblblindworkshop` for `final,dblblindworkshop`. In submission mode the generic "Submitted to ... Do not
distribute." notice is expected and correct.

## Page budget: fits
Built with the official style: **main text pages 1-9** (limit 9), references 9-10, appendix 11, **11 pages
total, 0 overfull hboxes**. References and the appendix do not count toward the limit.

To fit, prose was compressed rather than cutting figures: the Related Work "closest interventions" and
"retrieval architectures" paragraphs were merged, the introduction's results preview was tightened, and all
six figure widths were scaled by 0.85. Every figure remains in the main text and every number is unchanged.

If a future edit pushes it over again, the next levers in order are: move the "Interventions and estimation"
statistical machinery (cluster tests, Holm family) to an appendix subsection; shrink Table 1 to the pretrained
block with the full table in the appendix. Do **not** move figures to the appendix.

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
