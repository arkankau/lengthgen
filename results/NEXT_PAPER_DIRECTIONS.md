# Next-paper directions (seeded 2026-08-31, after the AAAI + InterpScience submissions)

Priority order chosen by the author: **C, then A, then B.** Everything below is future work; nothing here
touches `paper_lengthgen_aaai/main_submission.tex`, which is frozen.

---

## C. When is a circuit decomposable? Superadditivity of spectrum-preserving swaps

**The move:** Puzzle/Contradiction, developed as a methods critique. Not "apply SPS to a new task."

**Claim under test.** Greedy circuit-discovery methods (ACDC \citep{conmy2023acdc}, attribution patching
\citep{syed2023attribution,kramar2024atp}) build circuits from component-wise effects. That presumes roughly
additive or diminishing returns. If the effect is superadditive, a circuit cannot be found by testing its
parts, and greedy selection has no approximation guarantee.

**What the existing data already shows.** `scripts/analyze_superadditivity.py` over
`results/lengthgen/paired_head_count_full_grid.json` (16 trained models x 2 lengths x K in {1,2,4,8}):

| task | per-head effect K=1,2,4,8 | shape | greedy underestimate eff(8)/(8 eff(1)) |
|---|---|---|---|
| argmax  | +.0099 +.0107 +.0249 +.0355 | strongly superadditive | median 3.56x, max 23.2x |
| flagret | +.0037 +.0022 +.0031 +.0027 | flat / additive        | median 0.50x |

Pooled doubling ratios: 1->2 median 0.75, 2->4 median 2.04, 4->8 median 1.06 (superadditive in 16/29 cells,
i.e. chance). So the effect is **concentrated at the 2->4 transition and confined to argmax**.

**Honest correction recorded here:** an earlier reading of the paper's pooled means (0.007, 0.013, 0.056,
0.153) suggested uniform superadditivity. The per-cell data shows that is driven entirely by argmax. Do not
repeat the pooled claim.

**The hypothesis this suggests.** Argmax requires comparing across positions (find the largest key); flagret
only locates a marked position. Distributed computations should yield superadditive circuits, local ones
additive circuits. Decomposability is a property of the *task's* information flow, not of the method.

**Next steps.**
1. Shuffled-head-order control. Heads are currently ranked by source mass, so later heads are individually
   weaker and the measured superadditivity is conservative. Re-run each K with randomly ordered heads to
   confirm the interaction is not a selection-order artifact. This is the one experiment C needs.
2. Add a third task that is unambiguously distributed (two-evidence modular sum already exists) and one that
   is unambiguously local, and test the prediction in advance. Pre-register the direction.
3. Quantify the greedy failure directly: run ACDC-style greedy selection and measure what fraction of the
   K=8 effect it recovers on argmax versus flagret.
4. Note the boundary honestly: 2/16 flagret cells have zero effect at every K.

---

## A. Generalize the control, not the intervention: norm-preserving steering

**The move:** Scope Mismatch, developed by Robustification. Transfers the *control design*, not the method.

The paper's transferable contribution is a counterfactual that holds the confounded quantity exactly fixed.
Steering-vector work has the same confound and no standard control: adding `alpha * v` to a residual stream
changes both direction and magnitude. The SPS analogue is a **norm-preserving rotation** to a matched-norm
direction. If the effect survives the rotation control, it was magnitude, not direction.

Why it is worth doing: steering is widely used, the confound is real, and the control is cheap. The
identification argument is identical in form to Proposition 1 with the rotation group in place of the
permutation group.

---

## B. The invariance argument beyond attention

**The move:** Explanation Gap, developed by Formal Derivation.

Proposition 1 is an instance of a general principle: a statistic invariant under a group action cannot
identify a quantity that varies under that action. Attention rows and token permutations are one case.
Candidates to audit: sparse-autoencoder feature magnitudes versus which feature fires (index permutation),
probe accuracy versus the probe direction, neuron activation statistics versus input identity.

Deliverable: an "invariance audit" for interpretability claims, stating for each common measurement which
group it is invariant under and therefore which claims it cannot support. Most ambitious of the three and the
one that would make the framework a standard rather than a result. Hardest to make empirical.

---

## Algorithm problems that fell out of the current paper

1. **Source-max optimizes the wrong factor.** Proposition 2 gives the effect as
   `sum_h delta_h (u_hs - u_hd_h)`, a product, but source-max chooses the donor by `argmax_j a_j`, maximizing
   `delta_h` alone and ignoring the donor's utility. The utility-optimal donor solves
   `argmax_d (a_d - a_s)(u_s - u_d)`, which is O(n) per head. The two disagree whenever the largest-weight
   donor is itself high-utility, which is a candidate mechanism for the Gemma saturation regime (+.040 from
   source-max while source-min gives -1.373). Utility was used for head selection but never for donor
   selection within a head.
2. **The first-order-optimal assignment is a rearrangement problem.** The supplement already uses
   Hardy-Littlewood-Polya to bound evidence mass. The first-order margin `sum_j a_pi(j) u_j` is also a
   rearrangement objective, maximized by sorting weights in the same order as utilities, giving the
   utility-optimal spectrum-preserving assignment in O(n log n). Source-max is the single-transposition
   special case. This also yields a ceiling: what fraction of the attainable margin range does source-max
   capture?
3. **Non-submodularity** (see direction C) means greedy circuit search has no guarantee where the effect is
   superadditive.

---

## Scope note

All three directions concern the design space of an off-manifold probe. None of them claims an inference-time
improvement to models, and the next paper should keep that boundary as explicit as the current one does.
