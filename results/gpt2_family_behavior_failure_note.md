# GPT-2 Family Behavior Failure Note

Manual inspection flagged the first `gpt2` side-by-side review as mostly repeated words and template-like continuations, especially variants of "the following".

## What We Tested

### `gpt2` at `R_c=0.70`

Initial metrics looked promising:

- positive jailbreak-vs-benign null-mass separation
- low empty-continuation rate
- shorter length loss than `distilgpt2`

However, the behavior was not acceptable. Many continuations were repetitive, generic, or list-template fragments.

### Decoding Controls

We added generation controls:

- `--repetition-penalty`
- `--no-repeat-ngram-size`
- `--ban-phrases`

The stricter `gpt2` smoke run reduced exact repeated phrases but caused empty or degraded continuations under intervention, so decoding controls did not solve the core issue.

### `gpt2-medium`

We downloaded and smoke-tested `gpt2-medium`, which is hook-compatible with the GPT-2 attention intervention.

Baseline `gpt2-medium` outputs were cleaner than `gpt2`, but the intervention still produced repeated, off-topic, or unsafe continuations.

With a stronger attractor setting:

- direct-jailbreak mean `m_null` rose to `0.990`
- entropy collapsed to `0.013`
- continuations remained unsafe or semantically poor

This is a concrete example of global/semantic degeneration rather than controlled safe attraction.

## Interpretation

The stronger local GPT-2-family runs should not be promoted as behavior-selected results. They are useful as negative evidence:

- higher model scale improves baseline fluency,
- higher null mass improves the physics proxy,
- but the current calibrated-refusal value vector does not reliably produce safe semantic redirection in GPT-2-family generation.

This supports the paper's central caution: null-attractor phase behavior is a mechanism, not a complete safety defense. Controlled thermodynamic attraction must be validated behaviorally, not inferred from `m_null` alone.

## Next Step

The next technical step is not more null mass. It is either:

1. select intervention heads by measured risk separation and behavior preservation, or
2. improve the attractor value design so the null basin carries a stable safe-redirection direction instead of merely perturbing generation.
