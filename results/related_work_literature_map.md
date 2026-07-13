# Related Work Literature Map

This map positions the project as a mechanistic diagnostic paper about thermodynamic attention dynamics, not as a finished generation-time jailbreak defense.

## Core Attention-as-Energy / Thermodynamics Papers

1. **Hopfield Networks is All You Need**  
   Ramsauer et al., 2020.  
   https://arxiv.org/abs/2008.02217  
   Key connection: modern Hopfield updates are equivalent to transformer attention. The paper explicitly describes attention in terms of energy minima/fixed points, including global averaging, metastable subset averaging, and single-pattern retrieval. This is probably the strongest foundation for our “attention attractor basin” framing.

2. **Energy Transformer**  
   Hoover et al., 2023.  
   https://arxiv.org/abs/2302.07253  
   Key connection: combines attention, energy-based models, and associative memory. It designs attention layers to minimize an engineered energy function. Useful for saying our work also treats attention as an energy process, but our focus is diagnostic null-attractor behavior under safety-relevant prompts.

3. **Dissecting the Interplay of Attention Paths in a Statistical Mechanics Theory of Transformers**  
   Tiberi, Mignacco, Irie, Sompolinsky, 2024.  
   https://arxiv.org/abs/2405.15926  
   Key connection: develops a statistical mechanics theory of deep multi-head self-attention in a finite-width thermodynamic limit. It gives us language for attention paths, head-level contributions, and pruning/selection by relevance.

4. **Thermodynamic Isomorphism of Transformers: A Lagrangian Approach to Attention Dynamics**  
   Kim, 2026.  
   https://arxiv.org/abs/2602.08216  
   Key connection: explicitly maps softmax to thermodynamic equilibrium/free-energy minimization. This is very close to our physics vocabulary, but it is broad/theoretical. Our angle is narrower and empirical: safety-relevant detection via null-attractor diagnostics.

5. **A Framework for Non-Linear Attention via Modern Hopfield Networks**  
   Farooq, 2025.  
   https://arxiv.org/abs/2506.11043  
   Key connection: frames attention through an energy landscape with “context wells.” Useful vocabulary for our basin/attractor explanation.

## Attention Sink / Null-Attractor Adjacent Work

1. **Attention Sink in Transformers: A Survey on Utilization, Interpretation, and Mitigation**  
   Su et al., 2026.  
   https://arxiv.org/abs/2604.10098  
   Key connection: surveys attention sink behavior where disproportionate attention mass lands on uninformative tokens. Our null slot is an artificial, risk-conditioned sink, so we should distinguish natural attention sinks from our controlled diagnostic sink.

2. **Attention Sinks Are Provably Necessary in Softmax Transformers: Evidence from Trigger-Conditional Tasks**  
   Ran-Milo, 2026.  
   https://arxiv.org/abs/2603.11487  
   Key connection: argues softmax attention naturally forms sinks under trigger/default-state tasks. This is directly relevant to our claim that softmax normalization can support attractor-like collapse.

3. **The Spike, the Sparse and the Sink: Anatomy of Massive Activations and Attention Sinks**  
   Sun, Canziani, LeCun, Zhu, 2026.  
   https://arxiv.org/abs/2603.05498  
   Key connection: separates local attention-sink behavior from global massive activation behavior. This fits our distinction between controlled head-local attraction and global semantic degeneration.

4. **When Sinks Help or Hurt: Unified Framework for Attention Sink in Large Vision-Language Models**  
   Choi et al., 2026.  
   https://arxiv.org/abs/2604.03316  
   Key connection: sink dominance can help or hurt depending on whether it preserves useful evidence. Good analogy for our result: null mass can be measurable but behaviorally harmful if it suppresses semantics.

## Safety / Jailbreak Internal-State Detection

1. **How Alignment and Jailbreak Work: Explain LLM Safety through Intermediate Hidden States**  
   Zhou et al., 2024.  
   https://arxiv.org/abs/2406.05644  
   Key connection: uses intermediate hidden states to explain alignment and jailbreak. This supports our move from surface risk to latent trajectory risk.

2. **ALERT: Zero-shot LLM Jailbreak Detection via Internal Discrepancy Amplification**  
   Lin et al., 2026.  
   https://arxiv.org/abs/2601.03600  
   Key connection: detects jailbreaks from internal representations using layer/module/token-wise discrepancy amplification. This is close to our diagnostic goal, though our detection statistic is thermodynamic/attention-based rather than classifier-only.

3. **Refusal in Language Models Is Mediated by a Single Direction**  
   Arditi et al., 2024.  
   https://arxiv.org/abs/2406.11717  
   Key connection: refusal/compliance can be modulated by activation-space directions. This motivates why our current crude calibrated-refusal value vector is insufficient: safe refusal has semantic geometry, not just a null sink.

4. **There Is More to Refusal in Large Language Models than a Single Direction**  
   Joad et al., 2026.  
   https://arxiv.org/abs/2602.02132  
   Key connection: refusal is not monolithic; different refusal categories have distinct directions. This strengthens our limitation: a single refusal anchor vector is too crude.

## Mechanistic Interpretability / Head-Level Circuits

1. **A Mathematical Framework for Transformer Circuits**  
   Anthropic Transformer Circuits, 2021.  
   https://transformer-circuits.pub/2021/framework/index.html  
   Key connection: treats attention heads as decomposable QK/OV circuits. Supports our head-level analysis and measured head selection.

2. **Towards Automated Circuit Discovery for Mechanistic Interpretability**  
   Conmy et al., 2023.  
   https://arxiv.org/abs/2304.14997  
   Key connection: causal discovery of relevant circuits. Our selected-head experiment is a lightweight version: rank heads by measured risk separation and benign penalty.

## Best Positioning for Our Paper

Our strongest claim should be:

> We introduce a thermodynamic diagnostic for transformer attention in which safety-relevant prompts induce measurable null-attractor phase behavior; entropy, spectral gap, and head-local null mass distinguish controlled attraction from global degeneration.

The paper should not claim:

> The current generation-time null intervention is a jailbreak defense.

Instead, it should argue:

- attention can be studied as an energy/attractor process,
- jailbreak-like prompts can be detected through latent thermodynamic response,
- naive null attraction can fail behaviorally even when the physical proxy looks strong,
- this failure is itself useful because it separates diagnostic phase change from safe generation.

## How We Differ

- Compared with Hopfield/Energy Transformer papers: we use the energy/attractor view as a safety diagnostic, not as a general architecture.
- Compared with attention-sink papers: our null sink is controlled and risk-conditioned, not merely naturally occurring.
- Compared with jailbreak detectors: our signal is thermodynamic and mechanistic, using null mass, entropy, spectral gap, and head-local separation rather than only classifier outputs.
- Compared with refusal-direction work: our failed generation tests show why a crude refusal vector is not enough; safe redirection requires richer attractor semantics.
