# Pre-Registration: Direction B — intervene on the identified cause

Locked 2026-07-11, before implementing/tuning the attention intervention.

## Premise (from Direction A)
Length-gen failure on retrieval is attention DISPERSION off the correct source (corr(acc, attn_tgt)=0.97
vs corr(acc, variance)=0.59); the variance fix leaves attention unrestored (worsens it under RoPE). If
attention dispersion is the operative cause, an intervention that keeps attention CONCENTRATED at long
length should recover length generalization -- where the variance fix does not.

## Intervention (pre-specified)
**Length-scaled attention temperature (logit sharpening).** Multiply pre-softmax logits by a per-query
factor s(q) = max(1, log(q+1) / log(n_ref)), n_ref ~= training sequence length. s=1 at train length,
grows with length -> counteracts the CLT-like dispersion as more keys compete. (This is the
"scalable-softmax" style scaling; the CONTRIBUTION here is using it as a causal test of the
attention-vs-variance question and contrasting it with the variance fix, not the scaling itself.
Prior-art check on log-length attention scaling to be done before any novelty claim.)

## Pre-registered hypotheses
- **H-B1 (it works):** the attention-temperature intervention gives a POSITIVE per-token benefit at the
  break point on argmax+flagret (both PEs), i.e. Delta > +0.05 -- where the variance fix gave <= 0.
- **H-B2 (via the mechanism):** it does so by raising attn_tgt at long length vs baseline.
- **H-B3 (causal chain):** the accuracy gain tracks the attn_tgt gain across cells.

## Decision / interpretation
- If H-B1 + H-B2 hold: CAUSAL CLINCHER -- intervening on the identified cause (attention) recovers
  length-gen while intervening on variance did not. Flips the paper to "identify the cause AND fix it"
  (beyond-workshop). 
- If it helps attn_tgt but not accuracy: attention is necessary but not sufficient; report honestly.
- If it doesn't help at all: the correlational A-result stands but the causal intervention fails; the
  cause is more than attention (readout/positional). Report honestly; do NOT overclaim.
- Gate: must not break train-length mastery (em@1x >= 0.9) -- an intervention that hurts train length is
  disqualified.

## Protocol
CPU-smoke-tune the scaling scheme (ref constant, fixed vs log-len) on flagret FIRST; only run the GPU
grid (argmax+flagret x {baseline, attn-temp} x {nope,rope} x seeds) if the smoke is promising.

---

## Amendment 1 (locked 2026-07-13, before the GPU run)

**Prior-art status (does not change the design).** Log-length attention-logit scaling is published as
scalable-softmax / SSMax (arXiv:2501.19399). We do NOT claim the operator as novel. It is used here purely
as the CAUSAL PROBE for the symptom-vs-cause question: the variance fix repairs variance and not attention
(Direction A); this arm repairs attention and lets us read the behavioral consequence. The paper's claim is
the adjudication, not the operator.

**Reference constant locked: `attn_ref = 6`** (was default 16). The scaling is s(q)=max(1, log(q)/log(ref)),
so s=1 up to length `ref` and grows beyond. Training length is 5, so ref must be ~5-6 for sharpening to act
in the 5->16 range where degradation begins; ref=16 is clamped to s=1 through 3x the training length and does
nothing there. CPU smoke on flagret (2L/128, 800 steps) confirms ref=6 dominates ref=16 while preserving
train mastery: em@5=1.00 for both; at length 250, ref=6 vs ref=16 gives NoPE tok 0.641 vs 0.605 and
attn_tgt 0.146 vs 0.104, RoPE tok 0.566 vs 0.574 and attn_tgt 0.078 vs 0.053. ref=6 is the pre-registered
primary; ref is a documented sensitivity axis, not a search space to mine for a positive cell.

**PE-specific expectation (honest, pre-committed).** The attention-dispersion literature reports that
sharpening helps NoPE more than RoPE (nopeentropy, arXiv:2404.12224), and the CPU smoke shows only a modest
long-length lift. We therefore expect the clearest positive on NoPE, and we pre-commit to reporting a RoPE
null or partial as an honest outcome rather than tuning until RoPE turns positive. H-B1 stands as written;
if only NoPE clears +0.05 the verdict is PARTIAL by the decision rules above, and we report it as such.

**Exact run (4 seeds, matches the Direction-A grid):**
`python colab/length_gen_colab.py --tasks argmax,flagret --seeds 0,1,2,3 --attn-scale loglen --attn-ref 6
--outdir /content/drive/MyDrive/lengthgenB`
produces 16 configs (argmax+flagret x nope+rope x 4 seeds, LN-off). Merge with gpu_resultsA.json (which
holds baseline+varfix) via scripts/merge_lengthgen_json.py, then scripts/analyze_causalB.py. Runbook:
colab/README_lengthgen_causalB.md.

---

## OUTCOME (2026-07-13, run complete)

Data: results/lengthgen/gpu_resultsB.json (16 loglen configs); merged results/lengthgen/gpu_resultsAB.json.
Verdict from analyze_causalB.py: **PARTIAL**. Sharpen benefit @break (var-fix benefit for contrast):
argmax nope +0.083 [4/4 seeds pos] (var -0.013); argmax rope -0.008 (var -0.033); flagret nope +0.019
(var -0.080); flagret rope +0.027 (var -0.061). attn_tgt base->sharpen: argmax nope 0.112->0.382, argmax
rope 0.246->0.215, flagret nope 0.057->0.132, flagret rope 0.016->0.119.

- **H-B1 (positive benefit > +0.05):** PARTIAL. Only argmax NoPE clears +0.05 (mean +0.030, 1/4 cells).
- **H-B2 (raises attn_tgt):** SUPPORTED in 3/4 cells (raised, large for flagret); argmax RoPE the exception
  (already the most-concentrated baseline, attn flat).
- **H-B3 (accuracy gain tracks attn gain across cells):** STRONGLY SUPPORTED, r = +1.00 (0.997) over 4 cells.
  The one cell with no attention gain (argmax RoPE) is the one cell with no accuracy gain.

Interpretation (per decision rules): the causal DIRECTION is confirmed (raise the operative variable ->
raise accuracy, in proportion; the variance fix raises neither) while the single log-length lever only
PARTIALLY rescues and clears the effect-size bar in one cell. Reported honestly in the paper: §6 "Restoring
concentration" now leads with the dissociation + r=+1.0 tracking (fig_intervention.pdf), abstract/intro/
conclusion updated, Limitations note the partial rescue + 4-cell caveat. Does NOT overclaim a full rescue.
