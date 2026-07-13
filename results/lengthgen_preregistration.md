# Pre-Registration: Vanishing-Variance × Positional-Encoding on Length Generalization

**Locked before viewing any 2×2 outcome.** Written 2026-07-10.

## Gap (verified, novelty 0.78)

Source paper arXiv:2504.02827 ("On Vanishing Variance in Transformer Length Generalization") shows
attention-output variance collapses as sequence length grows, and that a post-attention normalization
fixes it. Verified by reading the source: it tested **only order-invariant** tasks (argmax retrieval,
dictionary lookup), **deliberately removed positional encoding** ("independent of any effects introduced
by positional encodings"), and **never crossed the fix with {NoPE, RoPE}** or any order-dependent task.

Secondary paper arXiv:2404.12224 found "softmax temperature helps NoPE but not RoPE" → predicts the
variance fix may be **PE-asymmetric**.

## Open question

Does a cheap post-attention LayerNorm restore length extrapolation on an **order-dependent** task
(reversed multi-digit addition, where position is load-bearing), and is the effect **PE-dependent**?

## Design (2×2, ≥2 seeds/cell)

- Task: reversed-format decimal addition, operands 1..L_train digits (L_train=5).
- Model: 2-layer pre-LN decoder, d_model=128, 4 heads, d_mlp=512, vocab=14.
- Factors: **PE ∈ {nope, rope}** × **post_attn_ln ∈ {0, 1}**.
- Training: 4000 steps, AdamW lr=3e-4, wd=0.1, betas=(0.9,0.98), batch=256.
- Seeds: {0, 1} (add more if a cell is borderline).
- Eval lengths: train L=5, 2×=10, 3×=15, plus fine ladder 1..15.
- Observables: (a) exact-match accuracy (teacher-forced, answer positions) per length;
  (b) attention-output variance per layer per length (captured BEFORE post-LN).

## Pre-registered hypotheses

- **H1 (main):** post_attn_ln improves extrapolation accuracy at 2×/3× vs no-LN, within a PE.
- **H2 (interaction):** the improvement is PE-dependent (predicted: helps NoPE more than RoPE).
- **H3 (mechanism):** extrapolation accuracy tracks attention-output variance stability across length
  (cells whose variance collapses less with length extrapolate better).

## Pre-registered interpretation (every outcome is reportable)

1. **Fix helps both PEs** → the variance fix transfers to order-dependent tasks; extends 2504.02827. (novel positive)
2. **Fix helps one PE only** → clean PE×variance interaction, matches 2404.12224 asymmetry. (novel interaction)
3. **Fix helps neither** → the variance mechanism does NOT govern length-gen on order-dependent tasks;
   the 2504.02827 result is specific to order-invariant retrieval. (novel negative — still reportable)

## Kill / validity conditions

- A cell with train-length accuracy < 0.8 is **uninformative for extrapolation** (can't extrapolate what
  it didn't learn) — report the train-length failure, do not read its 2×/3× numbers as an extrapolation result.
- Baseline (no-LN) extrapolation is ~0.00 (confirmed in pilot: RoPE/no-LN → L10=0.00, L15=0.00), so the
  task is not trivially solved — there is headroom.
- Teacher-forced exact-match is an upper bound on free-generation accuracy; noted as a limitation.

---

## AMENDMENT (2026-07-10, logged before any recall result exists)

The first 2×2 (addition) returned a 0-vs-0 RoPE null with no proof the harness can detect an
extrapolation gain, and NoPE failed to learn the task. To make the negative interpretable, we add an
internal **positive control**: the SAME 2×2 on an ORDER-INVARIANT task (associative recall / dictionary
lookup — the source paper 2504.02827's own task family), where pilot shows the baseline has graded
length-degradation (L5=0.39, L10=0.25, L15=0.15 at 300 steps) — i.e. real dynamic range, and visible
variance collapse (L0 var 0.080->0.044 across length).

**Pre-registered contrast verdict:**
- If post-LN rescues extrapolation on recall (order-invariant) but NOT on addition (order-dependent):
  CONTRAST CONFIRMED — variance collapse governs order-invariant length-gen but is not the binding
  constraint when position is load-bearing. (the contribution)
- If post-LN rescues both: the fix transfers to order-dependent tasks too (stronger positive).
- If post-LN rescues NEITHER (incl. recall): POSITIVE CONTROL FAILED — the harness cannot reproduce
  2504.02827, so the addition null is about the setup, not the science. Do NOT publish the contrast.

Recall runs at 8000 steps (vs addition's 4000) so train-length accuracy saturates; the validity gate is
train-length acc >= 0.8, not equal step budgets.

---

## AMENDMENT 2 (2026-07-10, logged before any GPU result exists) — port to GPU + robust control

CPU verdict: addition fails at CHANCE past train length (no dynamic range); tiny model never MASTERS
associative recall. Both block a clean test. Resolution = GPU (bigger model + LR warmup/cosine + more
steps) via colab/length_gen_colab.py, plus an EASIER order-invariant positive control:

- **flagret** (flag-retrieval): output the single MARKed value in a sequence. Order-invariant (marked
  position varies), 1-hop, not guessable (chance 0.1). CPU smoke shows it MASTERS train length (em=1.00)
  AND degrades gradually with length (em 1.00 -> 0.86 at 3x; per-token 1.00 -> 0.93) -> real dynamic
  range on a mastered baseline. This is the primary positive control; recall is an optional harder one.

GPU config: 4 layers, d=256, 8 heads, batch 512, 15-20k steps, warmup 500 + cosine. Metric for the
contrast = per-token (graded) extrapolation benefit of post-LN, averaged over 2x & 3x, only on cells
whose no-LN train-length em >= 0.8. Contrast verdict logic is in colab/length_gen_colab.py summarize().
Pre-registered outcomes unchanged from Amendment 1 (confirmed / both-improve / control-failed).

---

## AMENDMENT 3 (2026-07-10) — reproduce the paper's OWN tasks; benefit-at-break metric

GPU smoke (small model) showed flagret is easy but DOES break at long length (10x), and post-LN
stabilizes variance without rescuing accuracy. Two upgrades, logged before the big-model run:

1. **Verified the fix = the paper's fix.** WebFetch of arXiv:2504.02827: their remedy is "applying
   layer normalization after the attention outputs" — exactly our `post_ln` on z after W_O, before the
   residual. So a null here contests THEIR fix, not a strawman. Their tasks: argmax retrieval + dict
   lookup (order-invariant).
2. **Added the paper's own tasks**: `recall` (= dictionary lookup) and `argmax` (= argmax retrieval),
   256 distinct keys/scores so long lengths draw distinct symbols. Eval ladder extended to 20x; the
   **benefit is measured at the longest length where the no-LN baseline BREAKS (per-token < 0.9)** — a
   control that never breaks is reported as "never broke", NOT as a null (separates genuine negative
   from uninformative). Metric = per-token; both PEs reported (NoPE is closest to the paper's PE-removed
   setup).

**Emerging (small-model) result — to be confirmed on the big model + 2 seeds:** across flagret, argmax,
(and dict-lookup pending mastery), post-LN raises variance-stability (varStab up, as the paper claims)
but yields ~0 length-gen benefit at the break point (argmax +0.016). => GENUINE NULL that scopes/contests
2504.02827: stabilizing attention-output variance is decoupled from length generalization.

**Honest alternative to rule out:** their specific model/config might show the benefit. The big-model run
(4L/256, warmup+cosine, NoPE and RoPE) is the fairest reproduction we can do; if the null holds there,
the result is a credible reproduction-and-scoping. Decisive command:
`!python length_gen_colab.py --tasks addition,flagret,recall,argmax --seeds 0,1`

---

## AMENDMENT 4 (2026-07-11) — strengthening measurements (no change to pre-registered verdict)

Post-hoc additions that add evidence but do not change any pre-registered hypothesis or decision rule:
1. **Post-fix variance** logged alongside pre-fix variance, to SHOW the fix mechanically stabilizes
   downstream variance (post-collapse ratio ~1.0) even though accuracy does not improve — closing the
   "is the LN even working?" gap. (pre-fix variance still reported as the raw collapse.)
2. **Longer eval ladder** to 50x training length (was 20x), so the baseline reaches a deeper break.
3. **Paired per-seed benefit** at the break point, reported as mean [min,max] with sign-consistency
   (n/n seeds negative), and more seeds for error bars.
The GENUINE-NULL verdict and its threshold are unchanged; these only harden the reporting.
