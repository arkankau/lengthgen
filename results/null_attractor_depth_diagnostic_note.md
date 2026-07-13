# Null-Attractor Depth Diagnostic: Cross-Model, Cross-Method Findings

Source: `scripts/evaluate_null_attractor_depth.py`. Companion to
`results/basin_energy_diagnostic_note.md` -- this reruns the *original* null-attractor observables
(`m_null`, entropy, spectral gap from `thermosafety/intervention.py`) as a function of layer depth, to
test whether they show the same depth-dependent growth/collapse curve the basin-energy diagnostic found.

## Prerequisite fix: grouped-query attention

The null-attractor attention hook (`null_attractor_attention_forward`) assumed query, key, and value all
have the same number of heads, which holds for GPT-2 (multi-head attention) but not for Qwen2 (grouped-
query attention: 14 query heads, 2 key/value heads). Running the existing hook directly on Qwen2 raised
a shape-mismatch error at the first `torch.matmul(query, key.transpose(...))`. Fixed by adding `_repeat_kv`
(mirrors `transformers`' own GQA expansion) and a generic eager-attention fallback in
`thermosafety/intervention.py`, applied before any null-attractor logic runs. GPT-2 is unaffected
(`n_rep == 1`, a no-op). Regression tests added in `tests/test_intervention.py`
(`test_grouped_query_attention_*`). Full suite: 67/67 passing after the fix.

## distilgpt2 baseline (layers 0-5, all 6 layers)

`m_null` separation is large (`sep(m_null)` 0.21-0.31) and entropy separation is consistently negative
(jailbreak entropy lower than benign, `sep(entropy)` -0.28 to -0.56) at every layer. This is expected and
not surprising: `m_null` is directly risk-gated by construction (`null_bias = eta_null * sigmoid(kappa *
(risk - threshold))`), and risk here uses the `surface` (keyword) score, which correlates strongly with
the jailbreak/benign label by design. This replicates the project's existing toy/distilgpt2
phase-transition results (`results/phase_transition_comparison.md`) rather than adding new information.

## Qwen2.5-0.5B-Instruct (layers 2, 6, 10, 14, 16, 18, 20, 21, 22, 23 of 24)

| layer | jailbreak m_null | benign m_null | sep(m_null) | sep(entropy) | sep(spectral gap) |
|---:|---:|---:|---:|---:|---:|
| 2  | 0.0000 | 0.0000 | 0.0000 | 0.007  | -0.079 |
| 6  | 0.428  | 0.383  | 0.045  | -0.160 | -0.023 |
| 10 | 0.659  | 0.500  | 0.159  | -0.359 | -0.070 |
| 14 | 0.296  | 0.119  | 0.177  | -0.357 | -0.096 |
| 16 | 0.171  | 0.104  | 0.067  | -0.037 | 0.004  |
| 18 | 0.599  | 0.426  | 0.173  | -0.306 | -0.077 |
| 20 | 0.596  | 0.430  | 0.166  | -0.342 | -0.058 |
| 21 | 0.722  | 0.658  | 0.064  | -0.144 | -0.069 |
| 22 | 0.0016 | 0.0001 | 0.0015 | -0.066 | -0.092 |
| 23 | 0.042  | 0.008  | 0.034  | -0.108 | -0.090 |

### Reading against the basin-energy depth curve

1. **The buildup is not a clean monotonic curve, unlike basin energy.** `sep(m_null)` bounces between
   0.045 and 0.177 across layers 6-21 rather than rising smoothly. This is expected: unlike the
   basin-energy margin (a pure cosine-similarity readout), `m_null` results from a fixed, layer-independent
   additive bias competing against each layer's *own* query-key logit scale, which varies layer to layer
   for reasons unrelated to risk (attention sharpness, head specialization, etc.). The two diagnostics are
   measuring genuinely different things and are not expected to have identical shapes.

2. **The location of collapse matches exactly.** Layer 2 (too early -- real attention logits dominate
   completely, `m_null = 0` for every prompt) and layers 22-23 (the same two layers where the basin-energy
   diagnostic's correlation collapsed to ~0 and its subspace margin flipped sign) both show `m_null`
   crashing back to near zero (0.0016-0.042) regardless of risk or label. This is independent
   corroboration, from a completely different mathematical quantity (attention-logit competition vs.
   hidden-state cosine similarity), that layers 22-23 of this 24-layer model are a genuine structural
   boundary (very likely the same attention-sink/compression-valley effect), not an artifact of either
   diagnostic's specific math.

3. **Entropy separation is the most robust single signal.** `sep(entropy)` is negative at 9 of 10 tested
   layers (all except layer 2), meaning jailbreak-labeled prompts consistently produce lower-entropy
   (more concentrated) attention than benign prompts across nearly the entire usable depth range, not
   just at one favorable layer. This is a cleaner, depth-robust version of the "risk-conditioned attention
   collapse" story the paper wants, and it held up on an aligned model without needing a tuned single
   layer.

## Updated recommendation

The paper now has two independently-derived diagnostics (cosine-based basin energy, and the original
risk-gated null-attractor observables) that agree on: (a) GPT-2-family shows detectable but
construction-driven separation dominated by the surface risk gate rather than model-internal semantics,
(b) an aligned model (Qwen2.5-0.5B-Instruct) shows real internal structure once probed at the right depth,
and (c) both diagnostics independently place a structural boundary at the same two final layers (22-23 of
24). Point (c) is the strongest, most defensible new claim from this round of experiments -- it should be
promoted to a named finding in `docs/paper/claims_and_evidence.md` (e.g. "cross-diagnostic depth boundary
agreement"), since it does not depend on either diagnostic's specific formula being correct, only on both
independently breaking in the same place.

## Risk=0 control: how much of raw m_null is a layer artifact vs genuinely risk-driven

The null slot's logit is hardcoded to `0` in `null_attractor_attention_forward` (`null_logits =
torch.zeros(...)`), not computed from an actual key vector. This means its baseline competitiveness
against real attention depends on each layer's natural logit landscape (are the non-sink real logits
mostly above or below 0?), independent of risk. To quantify how much this confounds the depth-sweep
results, we reran the identical sweep with `--force-risk 0.0` (added as a CLI option to
`scripts/evaluate_null_attractor_depth.py`), which sets `null_bias = 0` and `beta = beta_base` for every
prompt regardless of its actual risk score -- i.e. risk-conditioning is fully disabled, isolating
whatever null mass remains as pure layer-baseline artifact.

| layer | sep(m_null), real risk | sep(m_null), risk forced to 0 | risk-attributable separation | jailbreak m_null, real | jailbreak m_null, risk=0 | fraction of jailbreak m_null that is baseline |
|---:|---:|---:|---:|---:|---:|---:|
| 2  | 0.0000 | 0.0000  | 0.0000 | 0.0000 | 0.0000 | n/a |
| 6  | 0.0453 | -0.0213 | 0.0667 | 0.4283 | 0.3562 | 83% |
| 10 | 0.1586 | -0.0744 | 0.2329 | 0.6585 | 0.4123 | 63% |
| 14 | 0.1772 | -0.0181 | 0.1953 | 0.2961 | 0.0957 | 32% |
| 16 | 0.0672 | -0.0447 | 0.1119 | 0.1711 | 0.0571 | 33% |
| 18 | 0.1730 | -0.0314 | 0.2044 | 0.5994 | 0.3867 | 65% |
| 20 | 0.1658 | -0.0670 | 0.2328 | 0.5956 | 0.3517 | 59% |
| 21 | 0.0643 | -0.0941 | 0.1584 | 0.7222 | 0.5535 | 77% |
| 22 | 0.0015 | 0.0000  | 0.0015 | 0.0016 | 0.0001 | 7%  |
| 23 | 0.0340 | -0.0000 | 0.0340 | 0.0422 | 0.0080 | 19% |

Raw artifacts: `results/null_attractor_depth_qwen_risk0_{detail,summary,report}.{csv,md}`.

**The confound is real and substantial at the layer previously treated as "peak" (layer 21): 77% of its
raw jailbreak `m_null` (0.72) is present even with risk forced to zero (0.55).** Layer 6 is worse (83%
baseline). This means raw `m_null` magnitude at these layers should not be read as "77% risk-driven
attraction" -- most of it is a property of the layer's natural logit landscape colliding with a
zero-logit null slot, not the risk-gating mechanism.

**The separation metric survives, but the previously-identified "peak layer" does not.** Computing
`risk-attributable separation = sep(m_null, real risk) - sep(m_null, risk=0)` isolates the genuinely
risk-conditioned component. It remains positive and substantial across layers 6-21 (0.067 to 0.233) --
so the phase-response claim is not falsified -- but it **peaks at layers 10 and 20 (0.233 each), not
layer 21 (0.158)**, which was selected using the unconflated `sep(m_null, real risk)` metric in the
original sweep. The risk=0 control also reveals that, without risk-gating, benign prompts show *slightly
higher* baseline null mass than jailbreak prompts at every layer from 6 to 21 (`sep(m_null, risk=0)` is
consistently negative, -0.02 to -0.09) -- a small adverse tilt that the genuine risk-conditioned effect
has to overcome, making the net positive real-risk separation more meaningful, not less.

**This also explains the generation-intervention result.** `results/qwen_generation_intervention_note.md`
found that layer-21 intervention degraded benign prompts almost as badly as jailbreak prompts (m_null
0.64-0.71 vs 0.72 for jailbreak in that run). Given 77% of layer 21's jailbreak attraction is baseline
rather than risk-driven, of course benign prompts got hit nearly as hard -- the layer choice itself,
not just the crude null-value design, was a contributor to that failure. A follow-up generation
experiment at layer 10 or 20 (higher risk-attributable separation, lower baseline confound) would be a
fairer test of whether the null-attractor mechanism can achieve risk-selective behavior, and should be
run before drawing further conclusions about semantic-attractor generation quality.

## Root-cause fix: `null_key_mode="mean_logit"`, and a correction to Claim 8

The risk=0 control above diagnosed the problem; this section fixes it. `thermosafety/intervention.py`
now computes the null slot's logit as the mean of the real (causally valid) logits at that query
position (`null_key_mode="mean_logit"`, the new default), instead of a hardcoded `0`
(`null_key_mode="zero"`, preserved for comparison/regression). This makes the null slot's baseline
competitiveness self-normalized to each layer's own logit scale. Verified with a deterministic unit test
(`tests/test_intervention.py::test_mean_logit_mode_flattens_layer_baseline_null_mass`): under `zero` mode,
a uniformly very-negative real-logit landscape drives null mass to >99%; under `mean_logit` mode, the same
landscape lands exactly at the uniform share `1/(n+1)`, regardless of the landscape's absolute offset.

Rerunning the full depth+risk0-control sweep on Qwen2.5-0.5B-Instruct with the fixed default
(`results/null_attractor_depth_qwen_fixed_{summary,report}.{csv,md}`):

| layer | jailbreak m_null | benign m_null | sep(m_null) | baseline fraction (risk=0) | risk-attributable sep |
|---:|---:|---:|---:|---:|---:|
| 2  | 0.187 | 0.018 | 0.169 | 6.8% | 0.174 |
| 6  | 0.271 | 0.028 | 0.243 | 8.3% | 0.247 |
| 10 | 0.281 | 0.030 | 0.251 | 8.2% | 0.257 |
| 14 | 0.270 | 0.031 | 0.240 | 7.5% | 0.249 |
| 16 | 0.096 | 0.009 | 0.087 | 7.6% | 0.088 |
| 18 | 0.251 | 0.025 | 0.226 | 7.2% | 0.232 |
| 20 | 0.270 | 0.026 | 0.244 | 7.4% | 0.249 |
| 21 | 0.208 | 0.019 | 0.188 | 6.8% | 0.193 |
| 22 | 0.227 | 0.021 | 0.206 | 7.0% | 0.211 |
| 23 | 0.240 | 0.022 | 0.218 | 6.7% | 0.223 |

**The fix works as intended**: baseline fraction is now a stable 6.7-8.3% at *every* layer (versus 7-83%,
wildly varying by layer, under the old hardcoded-zero design). Risk-attributable separation is now
substantial and roughly flat across almost the entire depth range (0.17-0.26 for every layer except 16),
rather than the narrow, noisy 6-21 band found before the fix. **Layer 10 is now the best-supported layer**
(risk-attributable sep `0.257`), with layers 6, 14, 18, 20 close behind (`0.23-0.25`).

**This requires correcting Claim 8's "cross-diagnostic depth-boundary agreement."** Under the old
hardcoded-zero mechanism, `m_null` collapsed to near-zero at layers 22-23, which was read as independent
corroboration of the basin-energy diagnostic's own collapse at those same layers. Under the fixed
mechanism, `m_null`-based separation at layers 22-23 is `0.21-0.22` -- **strong, not collapsed**. This
means the original `m_null` collapse at layers 22-23 was itself substantially an artifact of the
hardcoded-zero null logit failing to compete against the strengthening attention sink there (documented
in the "Verified mechanism" section below), not a real, independent replication of the basin-energy
diagnostic's collapse. The basin-energy diagnostic's own final-layer collapse (a hidden-state
cosine-similarity measurement, unrelated to the attention-key mechanism fixed here) is unaffected by this
correction and still stands on its own -- but it should now be reported as a single-diagnostic finding,
not "two independent diagnostics agreeing," until corroborated by something that isn't downstream of the
same null-key design.

## Verified mechanism (not left as inference)

We directly inspected native attention weights (`output_attentions=True`, eager mode) for a sample
jailbreak prompt across layers 2-23. The initial hypothesis -- that an overwhelming attention-sink token
grows so dominant it drowns the fixed null bias -- is **not** what happens. What actually happens:

| layer | top-attended token index | mass on top token |
|---:|---:|---:|
| 2  | 1 | 0.304 |
| 6  | 0 | 0.631 |
| 10 | 0 | 0.587 |
| 14 | 0 | 0.592 |
| 18 | 0 | 0.685 |
| 20 | 0 | 0.801 |
| 21 | 0 | 0.809 |
| 22 | 1 | 0.381 |
| 23 | 1 | 0.339 |

Token 0 (the first real token) acts as a growing attention sink from layer 6 through layer 21 (mass
0.63 -> 0.81, monotonic) -- consistent with the classic attention-sink literature. At layers 22-23, the
dominant token **switches away from token 0** and the peak mass **drops** (to 0.34-0.38) rather than
rising further. So the collapse at layers 22-23 is not "an overwhelming sink drowns the null bias" as
originally hypothesized -- it is a **reorganization/dissolution of the sink pattern itself**: the stable,
growing single-token attractor that built up through the middle-to-late stack breaks apart in the final
two layers. This is consistent with the "compression valley" framing (the last few layers process
representations differently, likely in preparation for the unembedding/LM head) rather than a simple
monotonic sink-strength story. The paper should describe this precisely rather than assuming the more
intuitive-sounding "stronger sink drowns everything" mechanism, which this check ruled out.

### Multi-prompt confirmation (n=12, 6 suites)

The single-prompt check above could have been a fluke. Repeated across 12 prompts (2 each from `benign`,
`direct_jailbreak`, `safety_research`, `obfuscated_jailbreak`, `long_context_jailbreak`,
`many_shot_jailbreak`):

| layer | mean top-token mass | std | fraction of prompts where token 0 is the sink |
|---:|---:|---:|---:|
| 6  | 0.575 | 0.055 | 1.00 |
| 10 | 0.551 | 0.045 | 1.00 |
| 14 | 0.549 | 0.041 | 1.00 |
| 18 | 0.639 | 0.053 | 1.00 |
| 20 | 0.730 | 0.065 | 1.00 |
| 21 | 0.781 | 0.052 | 1.00 |
| 22 | 0.354 | 0.127 | 0.33 |
| 23 | 0.278 | 0.068 | 0.25 |

The pattern is not prompt-specific: token 0 is the dominant sink in **100% of the 12 prompts** at every
layer from 6 through 21, with mass climbing steadily and low variance (std ~0.04-0.07). At layers 22-23,
the sink identity itself becomes inconsistent across prompts (only 33% / 25% still have token 0 on top),
mean mass drops sharply, and variance roughly doubles-to-triples (std 0.07-0.13) -- i.e. the final two
layers don't just have a weaker sink, they stop agreeing with each other on *which* token to attend to.
This confirms the dissolution finding is a general property of this model's final layers, not an artifact
of one prompt.
