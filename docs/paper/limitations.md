# Limitations

## Diagnostic, Not Defense

The current work is a thermodynamic diagnostic framework. It is not a deployed jailbreak defense and should not be described as one.

The evidence supports:

- risk-conditioned null-attractor response,
- phase-transition-like order-parameter behavior,
- entropy and spectral-gap diagnostics,
- head-local selectivity,
- failure modes where null mass rises without safe semantic redirection.

The evidence does not yet support:

- robust attack success reduction,
- low false-refusal deployment behavior,
- safe generation across realistic jailbreak suites,
- compatibility with black-box API models,
- a validated production safety policy.

## Null Mass Is Not Safe Semantics

Generation probes showed that increasing `m_null` can worsen continuations. In GPT2/GPT2-medium tests, stronger null attraction improved the physics proxy while producing repeated, empty, off-topic, or unsafe text.

This is a central limitation and should be framed as a finding:

> A thermodynamic attractor can be physically active without carrying the semantic structure needed for safe redirection.

This supports the key paper move:

> Null attraction reveals the thermodynamic response, but safe control requires structured attractors or barriers that reshape the energy landscape without destroying benign task basins.

## Current Attractor Value Is Crude

The calibrated-refusal value vector is based on a short anchor phrase. Refusal-geometry literature suggests refusal and non-compliance are structured activation-space phenomena, possibly multi-directional and category-dependent.

Future work should learn richer safe-redirection attractor values from aligned model internals, refusal directions, or activation-difference methods.

The next intervention target should compare semantic attractors and unsafe-coupling barriers against the null diagnostic, rather than simply increasing `eta_null`.

## Current Risk Functional Is a Scaffold

`probe_latent` moves beyond surface keywords, but it remains a small-batch calibration scaffold. It should be described as a latent trajectory probe candidate, not a validated jailbreak detector.

## Local Model Scope

The main generation ablations use GPT2-family local models. These are useful for mechanistic tests because their attention can be patched, but they are not representative of modern aligned chat systems.

## Head Selection Is Partial

Selected heads reduce benign null attraction and global degeneration, but they do not solve unsafe continuations. Head-local response supports the diagnostic story, not a finished intervention policy.
