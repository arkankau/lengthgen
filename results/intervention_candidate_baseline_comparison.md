# Phase 4 Candidate Intervention vs Baseline

This note compares the generation-level null-attractor intervention candidates against the local baseline continuations. It is a Phase 4 mechanism smoke test, not an ASR/FRR safety claim.

## Setup

- Model: `distilgpt2`, local cache only
- Prompt suites: all 38 local safe/non-operational prompt cases
- Baseline generation: no attention intervention
- Intervention generation: GPT-2 attention logits patched before softmax
- Candidate layers: `4,5`
- Candidate `eta_null`: `4.0`
- Candidate thresholds: `0.26`, `0.42`
- Generation suffix: `Answer:` for measurable continuations
- Risk is scored on the original prompt, not on the generation suffix

## Baseline Check

The corrected baseline produces non-empty continuations across all suites, so length/empty-continuation deltas are now interpretable.

| suite | n | mean risk | baseline continuation chars | baseline empty rate |
|---|---:|---:|---:|---:|
| benign | 4 | 0.110 | 55.8 | 0.000 |
| benign_complex | 4 | 0.089 | 55.5 | 0.000 |
| direct_jailbreak | 4 | 0.666 | 47.2 | 0.000 |
| long_context_jailbreak | 4 | 0.555 | 47.2 | 0.000 |
| many_shot_jailbreak | 6 | 0.226 | 45.8 | 0.000 |
| obfuscated_jailbreak | 4 | 0.459 | 40.5 | 0.000 |
| paraphrased_adversarial | 6 | 0.169 | 45.5 | 0.000 |
| safety_research | 6 | 0.129 | 53.2 | 0.000 |

## Candidate Aggregate

| setting | threshold | jailbreak mean m_null | benign mean m_null | jailbreak empty rate | benign empty rate | jailbreak length delta | benign length delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| s001 | 0.26 | 0.560 | 0.101 | 0.200 | 0.000 | -18.3 | -17.9 |
| s002 | 0.42 | 0.398 | 0.057 | 0.183 | 0.000 | -17.6 | -17.6 |

## Reading

Both candidates show attention-level separation: jailbreak-labeled suites receive substantially higher null mass than benign suites, while benign empty-continuation rate stays at zero. The lower threshold (`0.26`) is the stronger mechanism setting, with higher jailbreak `m_null`; the higher threshold (`0.42`) is gentler and reduces benign null mass further.

The intervention still shortens generations broadly, including benign cases. That means the mechanism is active but not yet selective enough to call a defense. The next valid step is to tune for lower benign length impact while preserving high-risk null-mass separation, then add manual generation review and ASR/FRR-style metrics.

## Baseline Contrast

The threshold baseline in `baseline_comparison_summary.md` can produce crisp binary collapse decisions, but it does not modify attention or expose thermodynamic observables. The Phase 4 candidate result is stronger evidence for the central hypothesis only insofar as it shows an in-layer attention order parameter (`m_null`) changing more on high-risk prompt families than benign families.

Current status: mechanism smoke test passes; defense claim is not yet established.
