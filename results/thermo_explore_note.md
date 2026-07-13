# Axis D: Thermodynamic Alignment Signature -- Result (Null, with one real shared feature)

Source: `scripts/thermo_explore_loop.py`, `thermosafety/thermo_observables.py`,
`results/thermo_explore_{state,profiles}.csv`. Same-architecture ablation: Qwen2.5-0.5B **base** vs
Qwen2.5-0.5B-**Instruct** (24 layers each; alignment is the only variable). Per-layer specific heat
`C = Var_p(-log p)` and entropy, over 22 prompts, with 2000-sample bootstrap 95% CIs. Frozen verifier:
an observable "passes" only if base and instruct CIs are non-overlapping at some layer.

## Result: no alignment signature

| observable | significant layers (CI-separated) | max abs effect | verdict |
|---|---:|---:|---|
| specific_heat | 0 / 24 | 0.032 | fail |
| entropy | 0 / 24 | 0.036 | fail |

Base and instruct per-layer profiles are statistically indistinguishable at **every** layer -- the two
curves track each other within bootstrap noise (e.g. L21 specific heat: base 1.026 [0.949, 1.114] vs
instruct 1.042 [0.969, 1.126]). Alignment does not leave a detectable fingerprint in these
thermodynamic observables. (Caveat: n=22; a *large* alignment effect is clearly excluded, a tiny one
cannot be. But the curves are so close that no useful signal is present at this scale.)

## One real, shared structural feature (not alignment)

Specific heat rises from ~0.55 (embedding) to a clean interior **peak of ~1.03 at layer 21**, then
drops sharply at layers 22--23 (0.74, 0.72). This peak-then-collapse is:

- reproducible and identical in base and instruct (so it is architectural/computational, not alignment);
- coincident with where basin separation peaked (L21) and where the attention sink dissolves (L22--23)
  in our earlier diagnostics.

So three independent observables -- basin separation, attention-sink mass, and now attention specific
heat -- agree that **layer 21 is a critically-poised layer and layers 22--23 are a distinct final
regime**. This is a genuine, if modest, descriptive characterization of the late-layer transition
(and overlaps with the known compression-valley phenomenon).

## Conclusion for the project

This is the fourth rigorous negative result for a *positive headline*, after Path C (defense degrades
generation), Axis B (basin detection non-competitive), and Axis B2 (no cross-template generalization
niche). The consistent lesson across all four: our thermodynamic observables are real and
well-behaved, but they neither help a downstream task nor reveal a property (like alignment) that a
standard tool misses. The specific-heat peak at L21 is a real observation but modest and partly known.

Durable contributions remain: (1) the verified two-level Boltzmann theory; (2) the confound-as-theorem
+ mandatory null/baseline-control methodology, now itself demonstrated a second time (this very
experiment's frozen CI verifier is that methodology in action); (3) a multi-observable characterization
of the late-layer critical transition. Further empirical swings for a positive headline are not
warranted. The honest paper is theory + methodology + the mapped boundary of what thermodynamic
attractor/observable methods do and do not reveal.
