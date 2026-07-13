# Attention Thermodynamics Knowledge File

Purpose: collect the papers most relevant to our thermodynamic-jailbreak-detection framing, and translate each one into concrete claims we can use. This file treats our current work as **detection/diagnosis**, not as a finished generation-time defense.

## Our Current Claim Boundary

Strong claim:

> Jailbreak-like prompts can be studied as a thermodynamic attention phenomenon: they induce measurable changes in null-attractor mass, entropy, spectral gap, and head-local attention response.

Careful claim:

> These signals can support detection and diagnosis of adversarial prompt states, and can distinguish controlled head-local attraction from global degeneration.

Do not claim yet:

> The current null-attractor generation intervention is a jailbreak defense.

Why: our generation probes showed that higher null mass can make outputs worse. That is not a failure of the detection frame; it is evidence that thermodynamic diagnostics and safe generation control are different problems.

## Concept Map

### Attention as Energy / Associative Retrieval

Core idea: transformer attention is not just “weighted averaging.” It can be interpreted as an energy-minimizing retrieval/update process. This gives us the vocabulary of attractors, basins, fixed points, metastability, and phase-like transitions.

Our use:

- null slot = artificial attractor state
- risk-conditioned null mass = order parameter
- entropy/spectral gap = collapse/phase diagnostics
- selected heads = attention paths that participate in the phase response

### Attention Sinks

Core idea: transformers naturally develop tokens or positions that absorb disproportionate attention mass. Some sinks are useful; some are degenerate.

Our use:

- our null attractor is a controlled, synthetic sink
- natural sink literature explains why softmax attention can collapse to stable anchors
- sink literature warns that sink dominance can suppress useful semantic evidence

### Internal Safety/Jailbreak Detection

Core idea: jailbreak and refusal behavior are visible in hidden states and internal modules before final text output.

Our use:

- supports replacing surface keyword risk with latent trajectory risk
- supports treating our method as an internal detector rather than text-output judge
- aligns with head/layer/module-wise safety signal localization

### Refusal Geometry

Core idea: refusal is represented in activation-space directions, but the geometry may be richer than a single universal vector.

Our use:

- explains why our crude calibrated-refusal value vector is not enough for generation control
- supports future work on richer safe-redirection attractors
- helps us frame failed generation intervention as expected, not embarrassing

## Paper Notes

### 1. Hopfield Networks is All You Need

Ramsauer et al., 2020  
URL: https://arxiv.org/abs/2008.02217

What it says:

- Introduces modern Hopfield networks with continuous states.
- Gives an update rule equivalent to transformer attention.
- Describes three energy-minimum/fixed-point regimes:
  - global averaging over all patterns,
  - metastable averaging over a subset,
  - single-pattern retrieval.
- Characterizes transformer heads through this attention-as-retrieval lens.

Why it matters to us:

- This is the strongest theoretical ancestor for our thermodynamic attractor framing.
- It gives us permission to talk about attention heads as moving toward fixed points/energy minima.
- Our “null attractor” can be framed as adding an extra stored pattern / basin and measuring whether attention dynamics retrieve it.

How to cite in our argument:

> Following the modern Hopfield interpretation of transformer attention, we treat attention updates as attractor-seeking retrieval dynamics and introduce a risk-conditioned null state as a diagnostic basin.

What not to overclaim:

- Hopfield equivalence does not imply jailbreak detection by itself.
- Their work is architectural/theoretical; our contribution is applying attractor diagnostics to safety-relevant prompt states.

### 2. Energy Transformer

Hoover et al., 2023  
URL: https://arxiv.org/abs/2302.07253

What it says:

- Combines attention, energy-based models, and associative memory.
- Proposes attention layers designed to minimize an engineered energy function.
- Uses the energy function to represent relationships between tokens.

Why it matters to us:

- Reinforces that attention can be designed/analyzed as an energy-minimizing system.
- Helps distinguish our approach from ordinary attention visualization: we are measuring thermodynamic response variables, not just looking at heatmaps.

How to cite in our argument:

> Prior energy-based transformer work motivates viewing attention as an energy process; our work instead uses a null-attractor perturbation to diagnose prompt-induced phase behavior in an existing transformer.

What not to overclaim:

- Energy Transformer is an architecture; our current implementation is a diagnostic patch/probe on pretrained GPT-style attention.

### 3. Dissecting the Interplay of Attention Paths in a Statistical Mechanics Theory of Transformers

Tiberi, Mignacco, Irie, Sompolinsky, 2024  
URL: https://arxiv.org/abs/2405.15926

What it says:

- Develops a statistical-mechanics theory of deep multi-head self-attention.
- Works in a finite-width thermodynamic limit.
- Represents predictor statistics as sums of kernels pairing different attention paths.
- Shows task-relevant combinations of attention paths matter for generalization.
- Demonstrates pruning heads deemed less relevant by the theory.

Why it matters to us:

- Directly supports head-level decomposition.
- Our selected-head experiment fits this: not all heads should be forced into the null basin.
- Gives theoretical backing for “all-head collapse is not controlled phase transition.”

How to cite in our argument:

> Statistical-mechanics analyses of attention paths suggest that task-relevant behavior is carried by combinations of heads; our measured head selection similarly finds that null-attractor response is head-local rather than globally beneficial.

What not to overclaim:

- Their model is analytically tractable and not identical to our GPT-2-family experiments.
- Their pruning is theory-driven; ours is empirical risk-separation ranking.

### 4. Thermodynamic Isomorphism of Transformers

Kim, 2026  
URL: https://arxiv.org/abs/2602.08216

What it says:

- Broadly maps transformer attention to thermodynamic and Lagrangian dynamics.
- Frames softmax as an equilibrium/free-energy object.
- Uses a large physics vocabulary: free energy, Fisher geometry, phase transitions, scaling laws.

Why it matters to us:

- Helps show that “attention thermodynamics” is an active theoretical framing.
- Gives language for softmax equilibrium and free-energy minimization.

How to cite in our argument:

> Recent theoretical work has proposed thermodynamic interpretations of softmax attention; our contribution is an empirical diagnostic that operationalizes this view through null mass, entropy, and spectral gap under safety-relevant prompts.

What not to overclaim:

- This paper is broad and speculative/theoretical. We should not depend on its strongest physics claims.
- Our paper should be more modest: operational diagnostics, measurable signals, careful limitations.

### 5. A Framework for Non-Linear Attention via Modern Hopfield Networks

Farooq, 2025  
URL: https://arxiv.org/abs/2506.11043

What it says:

- Frames attention through an energy functional based on modern Hopfield networks.
- Describes energy-landscape “context wells.”
- Proposes non-linear attention variants.

Why it matters to us:

- “Context wells” is close to our basin language.
- Supports the idea that attention configurations can be understood as landscape minima.

How to cite in our argument:

> Energy-landscape views of attention motivate our null-basin diagnostic: we ask whether adversarial prompts alter the model's susceptibility to a controlled attractor well.

What not to overclaim:

- We are not proposing a new attention architecture in this paper.

## Attention Sink Papers

### 6. Attention Sink in Transformers: A Survey

Su et al., 2026  
URL: https://arxiv.org/abs/2604.10098

What it says:

- Surveys attention sink behavior, where mass concentrates on specific often-uninformative tokens.
- Organizes the field around utilization, interpretation, and mitigation.
- Connects sinks to inference dynamics, interpretability, and possible failure modes.

Why it matters to us:

- Our null slot is basically a controlled sink.
- The survey helps us situate our work relative to natural attention sinks.

How to cite in our argument:

> Unlike naturally emergent attention sinks, our null sink is introduced as a controlled diagnostic perturbation whose mass is measured as an order parameter.

What not to overclaim:

- Natural attention sinks are not equivalent to jailbreak signals.
- Sink mass can be useful, harmful, or meaningless depending on context.

### 7. Attention Sinks Are Provably Necessary in Softmax Transformers

Ran-Milo, 2026  
URL: https://arxiv.org/abs/2603.11487

What it says:

- Shows that, for some trigger-conditional tasks, softmax transformers necessarily develop attention sinks.
- Argues that normalization over a probability simplex can force attention to collapse onto a stable anchor for default/ignore-input behavior.
- Contrasts softmax with non-normalized ReLU attention, which can solve the task without a sink.

Why it matters to us:

- Very relevant to our “null attractor” construction.
- It supports the idea that softmax attention naturally supports anchor collapse.
- It also explains why collapse can occur without semantic understanding.

How to cite in our argument:

> Softmax normalization itself can induce sink-like collapse under trigger/default-state computations; our null-attractor diagnostic exploits this susceptibility while measuring whether the collapse is selective or globally degenerate.

What not to overclaim:

- Provable sink necessity for toy trigger tasks does not prove jailbreak detection.
- It supports mechanism plausibility, not safety efficacy.

### 8. The Spike, the Sparse and the Sink

Sun, Canziani, LeCun, Zhu, 2026  
URL: https://arxiv.org/abs/2603.05498

What it says:

- Studies massive activations and attention sinks in transformer language models.
- Finds they often co-occur but play different roles.
- Massive activations are described as global, persistent hidden-state effects.
- Attention sinks are local, head-level modulators of attention outputs.

Why it matters to us:

- This is almost perfectly aligned with our controlled-vs-global distinction.
- It gives external support for separating head-local sink behavior from global hidden-state degeneration.

How to cite in our argument:

> Recent sink analyses distinguish local attention-sink effects from global activation phenomena; our entropy/spectral-gap diagnostics similarly separate head-local null attraction from global degeneration.

What not to overclaim:

- Their sink/massive-activation analysis is not jailbreak-specific.
- We should use it to justify diagnostics, not detection labels.

### 9. When Sinks Help or Hurt

Choi et al., 2026  
URL: https://arxiv.org/abs/2604.03316

What it says:

- Studies visual and language attention sinks in large vision-language models.
- Argues sink dominance creates tradeoffs: global priors can help, but excessive sink dominance can suppress local evidence.
- Proposes layer-wise sink gating.

Why it matters to us:

- Supports the idea that sink strength is not automatically good.
- This mirrors our generation failure: high null mass can suppress semantic content and worsen output.

How to cite in our argument:

> Sink dominance is known to create tradeoffs between global priors and local evidence; our generation probes show the same principle in safety diagnostics, where high null mass can degrade semantic behavior.

What not to overclaim:

- Their domain is vision-language, not jailbreak detection.

## Safety / Jailbreak Internal-State Papers

### 10. How Alignment and Jailbreak Work: Explain LLM Safety through Intermediate Hidden States

Zhou et al., 2024  
URL: https://arxiv.org/abs/2406.05644

What it says:

- Uses weak classifiers on intermediate hidden states to explain alignment and jailbreak.
- Finds models can identify malicious vs normal inputs in early layers.
- Argues alignment transforms early unethical concepts into emotion/rejection-related intermediate states and finally reject tokens.
- Claims jailbreaks disturb that transformation.

Why it matters to us:

- Strong support for using latent trajectory risk instead of keyword risk.
- Supports our idea that safety status is visible before output text.
- Gives a safety-specific internal-state precedent.

How to cite in our argument:

> Prior work shows jailbreak and alignment status can be decoded from intermediate hidden states; our risk functional similarly moves from surface keywords toward latent trajectory features, but measures thermodynamic attention response rather than only classifier accuracy.

What not to overclaim:

- Their models are larger/aligned models; our local GPT-2-family experiments are diagnostic and limited.

### 11. ALERT: Zero-shot LLM Jailbreak Detection via Internal Discrepancy Amplification

Lin et al., 2026  
URL: https://arxiv.org/abs/2601.03600

What it says:

- Targets zero-shot jailbreak detection.
- Amplifies internal feature discrepancies across layers/modules/tokens.
- Identifies safety-relevant layers, modules, and informative safety tokens.
- Builds classifiers on amplified representations.

Why it matters to us:

- Very close to our detection framing.
- Their method is internal-representation detection; ours is thermodynamic response detection.
- Supports the idea that detection should focus on internal dynamics rather than jailbreak templates.

How to cite in our argument:

> Like internal-discrepancy jailbreak detectors, our method aims at template-robust internal detection; unlike classifier-only approaches, we measure a thermodynamic response curve through null mass, entropy, and spectral gap.

What not to overclaim:

- We have not yet matched ALERT-scale benchmark evaluation.
- Our current contribution is mechanistic instrumentation, not SOTA detection.

## Refusal Geometry Papers

### 12. Refusal in Language Models Is Mediated by a Single Direction

Arditi et al., 2024  
URL: https://arxiv.org/abs/2406.11717

What it says:

- Finds a one-dimensional refusal direction across multiple open-source chat models.
- Erasing the direction reduces refusal; adding it can elicit refusal.
- Analyzes adversarial suffixes suppressing refusal-direction propagation.

Why it matters to us:

- Supports the idea that safe/refusal behavior has activation-space geometry.
- Explains why a value-vector attractor might need to be built from actual refusal directions, not a naive anchor phrase.
- Connects jailbreaks to suppression of internal refusal dynamics.

How to cite in our argument:

> Refusal-direction work shows that safety behavior is mediated by structured activation-space geometry; our failed calibrated-refusal attractor suggests that a crude null value vector is insufficient for controlled generation.

What not to overclaim:

- Their intervention is residual-stream steering/ablation, not attention null-slot attraction.
- Our current paper should use this as motivation for future attractor design.

### 13. There Is More to Refusal in Large Language Models than a Single Direction

Joad et al., 2026  
URL: https://arxiv.org/abs/2602.02132

What it says:

- Argues refusal is not fully explained by one direction.
- Finds distinct refusal/non-compliance categories correspond to geometrically distinct directions.
- Suggests different directions may affect “how” the model refuses more than whether it refuses.

Why it matters to us:

- Reinforces that safe redirection is semantically complex.
- Explains why one calibrated refusal anchor does not produce stable safe generation.

How to cite in our argument:

> Later refusal-geometry work suggests refusal is multi-directional and category-dependent, strengthening our conclusion that safe null-attractor design requires richer semantic structure than a single anchor vector.

What not to overclaim:

- This is a reason to limit our current generation claims, not a fix by itself.

## Mechanistic Interpretability / Circuit Papers

### 14. A Mathematical Framework for Transformer Circuits

Anthropic Transformer Circuits, 2021  
URL: https://transformer-circuits.pub/2021/framework/index.html

What it says:

- Decomposes transformer computation through residual stream, attention heads, and MLPs.
- Treats attention heads as QK and OV circuits.
- Provides a basis for head-level causal/mechanistic analysis.

Why it matters to us:

- Our head-selection result should be framed as a head-level mechanism, not a monolithic layer effect.
- QK/OV decomposition is important for future attractor work:
  - QK controls where null attraction happens,
  - OV/value geometry controls what semantic content the attractor writes.

How to cite in our argument:

> Transformer-circuit analysis motivates separating the attention-location effect of the null slot from the value/output content it writes into the residual stream.

What not to overclaim:

- We have not yet decomposed our null attractor into full QK/OV circuits.

### 15. Towards Automated Circuit Discovery for Mechanistic Interpretability

Conmy et al., 2023  
URL: https://arxiv.org/abs/2304.14997

What it says:

- Systematizes mechanistic interpretability workflows.
- Researchers choose a dataset/metric, then use activation patching to find units involved in behavior.
- Introduces ACDC for identifying circuits in computational graphs.

Why it matters to us:

- Validates our workflow: choose safety-relevant prompt sets and thermodynamic metrics, then identify relevant heads.
- Our head ranking is a simple metric-based precursor to fuller circuit discovery.

How to cite in our argument:

> Our measured head selection follows the mechanistic-interpretability pattern of defining a behavior metric and localizing responsible components, though a full causal circuit analysis remains future work.

What not to overclaim:

- Our head ranking is correlational/diagnostic, not a full causal circuit discovery.

## How These Papers Support Our Sections

### Introduction

Use:

- Hopfield Networks is All You Need
- Energy Transformer
- attention sink papers

Core narrative:

> Attention is increasingly understood as energy-based retrieval over attractor-like states. We ask whether jailbreak prompts produce detectable thermodynamic response signatures in this attention system.

### Method

Use:

- Hopfield equivalence
- sink necessity
- internal hidden-state safety work

Core narrative:

> We add a controlled null state to the attention simplex and measure risk-conditioned attraction. The main observables are null mass, entropy, spectral gap, and head-local separation.

### Experiments

Use:

- statistical mechanics attention paths
- circuit discovery
- sink local/global distinction

Core narrative:

> We show that all-head attraction can degenerate, while selected heads preserve a more controlled diagnostic response.

### Limitations

Use:

- refusal-direction papers
- sinks-help/hurt papers
- our generation failure notes

Core narrative:

> Detection and generation control are separate. A null attractor can detect a phase response without carrying the semantic structure needed for safe redirection.

## Suggested Related-Work Paragraph

Transformer attention has increasingly been interpreted through energy-based and associative-memory frameworks. Modern Hopfield analyses show that attention updates can be viewed as retrieval dynamics over energy minima, including global, metastable, and single-pattern fixed points. Energy Transformer and related statistical-mechanics work further develop attention as an energy or thermodynamic process, while attention-path analyses show that multi-head contributions are structured and head-selective. In parallel, attention-sink work shows that softmax attention can concentrate probability mass on stable anchors, sometimes functionally and sometimes degenerately. Safety work on intermediate hidden states and jailbreak detection suggests that adversarial prompt state is visible internally before final text generation. Our work combines these threads by introducing a controlled null attractor as a diagnostic perturbation and measuring whether safety-relevant prompts induce selective thermodynamic response through null mass, entropy, spectral gap, and head-local separation. Unlike refusal-steering or generation-control methods, our current contribution is a diagnostic framework; our intervention failures show that high null mass does not by itself imply safe semantic redirection.

## One-Sentence Positioning

We turn attention-as-energy theory into a safety diagnostic: a controlled null attractor exposes jailbreak-sensitive phase behavior in transformer attention, while entropy, spectral gap, and head-local null mass distinguish selective detection from global degeneration.
