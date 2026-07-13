# Related Work

Transformer attention has increasingly been interpreted through energy-based and associative-memory frameworks. Modern Hopfield analyses show that attention updates can be viewed as retrieval dynamics over energy minima, including global, metastable, and single-pattern fixed points. Energy Transformer and related statistical-mechanics work further develop attention as an energy or thermodynamic process, while attention-path analyses show that multi-head contributions are structured and head-selective.

In parallel, attention-sink work shows that softmax attention can concentrate probability mass on stable anchors, sometimes functionally and sometimes degenerately. This motivates treating our null slot as a controlled synthetic sink rather than a naturally emergent artifact.

Safety work on intermediate hidden states and jailbreak detection suggests that adversarial prompt state is visible internally before final text generation. Our method is aligned with this internal-detection framing, but measures a thermodynamic response curve rather than only classifier outputs.

Refusal-direction work shows that safe refusal behavior has activation-space geometry. This is important for our limitations: a crude calibrated-refusal value vector is not enough to produce safe generation control.

Primary references are summarized in:

- `docs/attention_thermodynamics_knowledge.md`
- `results/related_work_literature_map.md`

