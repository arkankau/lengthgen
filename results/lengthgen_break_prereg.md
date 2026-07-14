# Pre-Registration: predicting the length-gen break point from the attention logit gap (direction B)

Locked 2026-07-13, BEFORE the GPU run. Plumbing validated on a CPU smoke (tiny 2L/64 model, 300 steps):
training runs, the retrieval head is identified, and Delta(n), g(n), a_pred=sigmoid(Delta), and observed
em are all recorded; the fit + predict + figure pipeline runs. The smoke model is undertrained (a plumbing
check, not a result). The smoke already shows the predicted FORM: Delta declines about like -ln(n) (slope
~= -1.4) while the per-key margin g stays ~constant (~1.0-1.6).

## Premise / the move
Direction B turns Proposition 2 from a description into a PREDICTION. At the answer query the softmax over
keys gives, exactly, a_j* = sigmoid(Delta(n)) with Delta(n) = z_src - logsumexp_{k != src} z_k, where z are
the effective attention logits at the retrieval head. Since logsumexp ~ ln(#keys), a_j* stays high only if
z_src grows about like ln n. Writing the per-key margin g = z_src - mean_k z_k gives Delta ~ g - ln(#keys),
so the break (a_j* -> 0.5, Delta -> 0) is predicted at n* where the fitted Delta crosses 0.

## Instrument
Small transformer (4 layers, width 256) trained on l_train=5. We capture the pre-softmax attention logits at
the answer query (colab/length_gen_colab.py, Block.z_aq_scores), identify the retrieval head once as the head
with the highest mean a_j* at the shortest length (correctness-independent), and at each length record
Delta(n), g(n), a_pred=sigmoid(Delta), and observed exact-match em. The prediction FITS Delta(n) =
intercept + slope*ln(n) on SHORT lengths only (L <= 4*l_train, in and just past the training regime), then
EXTRAPOLATES to n*_pred = exp(-intercept/slope). The observed break n*_obs is where em crosses 0.5,
interpolated in ln-length.

## Pre-registered hypotheses
- **H-B1 (the gap declines):** for baselines (attn_scale=none), Delta(n) declines with ln(n) (fitted slope
  < 0) and the per-key margin g does not grow fast enough to compensate. This is the mechanism of the break.
- **H-B2 (prediction, the headline):** the break length predicted from the SHORT-length fit tracks the
  OBSERVED break across configs (tasks x PEs x seeds). Primary statistic: corr(log n*_pred, log n*_obs) over
  the baseline configs that break, with the median ratio n*_pred / n*_obs reported. Pre-registered success:
  corr >= 0.6 and median ratio within [0.3, 3].
- **H-B3 (sharpening pushes the break out):** length-scaled logit sharpening (attn_scale=loglen) makes the
  fitted slope less negative (the gap holds up), so n*_pred moves far out or to no-break-in-range, matching
  the better observed generalization of the sharpened models. This ties the predictive law to the
  intervention already in the paper.

## Decision / how it enters the paper
- H-B1 + H-B2 hold -> the paper gains a PREDICTIVE law: the break point is forecast from a measurable model
  statistic (the logit gap), not just described. Add a short section with fig_break (predicted vs observed
  break; Delta vs ln n for a baseline and its sharpened twin) after the theory section, and a sentence in the
  intro/conclusion. This is the "formal derivation -> prediction" upgrade, distinct from the existing
  correlational and interventional evidence.
- H-B2 partial (gap declines and predicts a finite break, but pred/obs agree only loosely) -> report honestly
  as a qualitative predictor, not a calibrated one.
- H-B3 confirms the sharpening mechanism at the level of the gap.

## Honest caveats (pre-committed)
- The prediction extrapolates a short-length linear-in-ln(n) fit; if Delta(n) is not linear in ln(n) the
  point prediction will be off, and we report the fit quality.
- n* is defined at a_j* = 0.5 / em = 0.5; both thresholds are conventions and we report sensitivity.
- The retrieval head is chosen at the shortest length; if retrieval is distributed across heads the
  single-head gap understates the true concentration, which we note.
- Small synthetic models, as elsewhere in the paper; this predicts the break in THIS controlled setting.

## Run
`python colab/predict_break.py --tasks argmax,flagret --pes nope,rope --scales none,loglen --seeds 0,1
--steps 12000 --outdir /content/drive/MyDrive/lengthgen_break` -> break_results.json.
Analyze: `python scripts/analyze_break.py results/lengthgen/break_results.json`.

## INTERIM OUTCOME (2026-07-14, 9 of 16 configs; run disconnected mid-flagret)
Data results/lengthgen/break_results.json (9 configs); figure fig_break.pdf. PARTIAL, reported honestly.
- **H-B1 (gap declines): SUPPORTED, clean.** Every baseline has fitted slope < 0 (argmax nope -2.4/-0.8,
  argmax rope -3.7/-2.5, flagret nope -2.9), and within EVERY config a_pred=sigmoid(Delta) tracks em closely.
  This is a direct quantitative confirmation of Prop 2's mechanism.
- **H-B2 (calibrated prediction): FAILS the pre-registered bar.** corr(log n*_pred, log n*_obs) = +0.68
  (passes the >=0.6 rank bar) BUT median ratio n*_pred/n*_obs = 4.4 (FAILS the [0.3,3] calibration bar). The
  short-length linear-in-ln(n) fit OVERPREDICTS the break, systematically and PE-dependently: under NoPE the
  gap is ~log-linear so the fit is well-calibrated (argmax pred65/obs84; flagret pred19/obs35), but under RoPE
  the gap is FLAT-then-CRASH (Delta 14->12->8 at L<=20, then -12 at L=50), so the short fit sails past the
  cliff and overshoots (argmax rope pred 245-410 / obs ~55). The pre-registered linearity assumption is wrong
  for RoPE. Verdict: qualitative, PE-dependent predictor -- NOT a calibrated one.
- **H-B3 (sharpening flattens the gap): SUPPORTED, clean.** loglen makes the slope less negative
  (argmax nope -1.6->-0.8; argmax rope -3.1->-1.3), the sharpened gap crosses zero later, and em is sustained
  to longer lengths. A mechanistic account of the sharpening intervention already in the paper.
DECISION: per the pre-registered "H-B2 partial" branch, report honestly as a mechanism result (the logit gap
is the order parameter; sigmoid(gap) tracks accuracy; sharpening flattens the gap), NOT as break-point
forecasting. Do not feature the calibrated-prediction claim. The staging draft
paper_lengthgen_aaai/draft_break_section.tex currently oversells "predict the break" and must be rewritten to
the honest mechanism framing before any integration. Remaining 7 flagret configs would firm up the numbers but
are not expected to change the partial verdict (the RoPE non-linearity is the root cause).
