# Key Paper Move

## One-Sentence Move

Null attraction reveals the thermodynamic response, but safe control requires structured attractors or barriers that reshape the energy landscape without destroying benign task basins.

## Why This Saves the Paper

The failed generation intervention does not erase the research contribution. It tells us that the null attractor and the safety controller are different objects.

The null attractor answers:

```text
Does a risky latent state change the attention energy landscape in a measurable way?
```

The answer is diagnostic. We measure this through:

```text
m_null, entropy, spectral gap, susceptibility, head-local separation
```

Safe generation control asks a harder question:

```text
Can we reshape the model's trajectory toward safe semantics while preserving useful generation?
```

The null attractor fails this harder test because it is semantically empty. It can create attraction without creating safety.

## Paper Logic

1. Attention can be interpreted as energy-style retrieval.
2. A synthetic null basin is a controlled perturbation of that energy landscape.
3. Jailbreak-like states show measurable susceptibility to this perturbation.
4. Entropy, spectral gap, and head-local null mass separate selective phase response from global degeneration.
5. Generation-time null intervention fails because the basin has no safety semantics.
6. Therefore, the next control object must be a structured safe attractor or unsafe free-energy barrier, not a stronger null sink.
7. The null-attractor mechanism itself contained a confound (the null slot's logit was hardcoded to `0`, so its baseline competitiveness tracked each layer's absolute logit scale, not risk). A risk=0 ablation exposed this; fixing it (computing the null logit from the mean of real logits instead) removed the confound and *also* measurably improved generation-time risk-selectivity, which is evidence the underlying mechanism has real signal once the artifact is removed, not just a cleaner number.
8. Cross-model validation (GPT-2-family vs. Qwen2.5-0.5B-Instruct) turned an ambiguous result into an interpretable one: flat, noisy signal on a model with no trained refusal behavior, and a real, structured, depth-dependent signal on an aligned model, is itself evidence the diagnostics measure something about learned refusal semantics rather than an arbitrary property of attention.

## Methodological Beat Worth Its Own Paragraph

A negative result inside the negative result: the paper's own null-attractor diagnostic had a hidden confound for most of this project's runtime, and it was only caught by applying the same discipline the paper argues for elsewhere -- do not trust a raw observable without a baseline ablation. This is worth stating explicitly rather than quietly folding into a methods footnote, because it is a concrete demonstration of the paper's broader argument: thermodynamic-flavored observables (`m_null`, basin energy, etc.) are easy to compute and easy to over-trust, and a risk=0 (or otherwise null-hypothesis) control should be treated as mandatory, not optional, before reporting any depth-selectivity or layer-selection result built on them.

## Contribution Framing

Claim:

> We introduce a thermodynamic diagnostic for jailbreak-like latent states by measuring risk-conditioned attention response to a controlled attractor perturbation.

Negative control:

> Naive null-attractor intervention shows that physical attraction is not equivalent to safe semantic redirection.

Future control hypothesis:

> Safe control likely requires semantic attractors, high-entropy safety shells, or free-energy barriers that alter basin depths without causing global collapse.

## What To Show In The Paper

The paper should show a progression:

```text
energy view of attention
    -> null attractor perturbation
    -> phase-response diagnostics
    -> baseline threshold comparison
    -> head-local selectivity
    -> basin-energy diagnostic (single-model, then cross-model validation)
    -> null intervention failure (pre-fix)
    -> mechanism confound found via risk=0 ablation, and fixed
    -> null intervention rerun (post-fix): better selectivity, still not solved
    -> structured attractor/barrier derivation
```

This makes the failure result useful instead of embarrassing. It becomes the reason the paper distinguishes detection from control. The confound-and-fix beat additionally becomes the reason the paper argues for baseline-controlled diagnostics as a general methodological requirement, not just a footnote about this one experiment.

## Language To Use

Use:

> The null attractor is a diagnostic probe of the energy landscape.

Use:

> High null mass is an order-parameter response, not evidence of safe generation.

Use:

> The failure of null intervention motivates structured attractors and free-energy barriers.

Avoid:

> The null attractor defends against jailbreaks.

Avoid:

> The intervention works when `m_null` is high.

Avoid:

> Refusal behavior follows automatically from attention collapse.

Use:

> A risk=0 ablation on the null-attractor mechanism found and let us fix a layer-scale confound in the null slot's baseline logit; the fix improved generation-time risk-selectivity, not just internal consistency.

Avoid:

> Two independent diagnostics agree on a depth-wise structural boundary at layers 22-23 of Qwen. (Retracted: the null-attractor half of this claim was downstream of the confound fixed above; see Claim 8's retraction in `docs/paper/claims_and_evidence.md`.)

