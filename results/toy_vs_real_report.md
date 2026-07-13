# Toy vs Real Hidden-State Diagnostics

This comparison is post-hoc diagnostic analysis. It does not patch model attention logits or demonstrate a generation-time defense.

| source | suite | n | mean risk | mean m_null | collapse rate | entropy | spectral gap |
|---|---|---:|---:|---:|---:|---:|---:|
| toy | benign | 4 | 0.110 | 0.094 | 0.000 | 2.370 | 0.963 |
| toy | benign_complex | 4 | 0.089 | 0.082 | 0.000 | 2.496 | 0.968 |
| toy | direct_jailbreak | 4 | 0.666 | 0.917 | 1.000 | 0.353 | 0.926 |
| toy | long_context_jailbreak | 4 | 0.555 | 0.553 | 0.500 | 1.522 | 0.948 |
| toy | obfuscated_jailbreak | 4 | 0.459 | 0.498 | 0.500 | 1.625 | 0.951 |
| real_hidden | benign | 4 | 0.076 | 0.044 | 0.000 | 2.223 | 0.192 |
| real_hidden | benign_complex | 4 | 0.063 | 0.035 | 0.000 | 2.392 | 0.183 |
| real_hidden | direct_jailbreak | 4 | 0.360 | 0.046 | 0.000 | 2.357 | 0.222 |
| real_hidden | long_context_jailbreak | 4 | 0.282 | 0.024 | 0.000 | 2.892 | 0.164 |
| real_hidden | obfuscated_jailbreak | 4 | 0.262 | 0.028 | 0.000 | 2.687 | 0.182 |

## Interpretation

The useful question is whether the same risk-conditioned null mass ordering appears when the query/key/value states come from an actual language model rather than deterministic toy embeddings.

If separation weakens on real hidden states, the next step is to replace the heuristic risk score with a learned trajectory probe using hidden-state drift, unsafe-direction alignment, native attention entropy, and instruction-conflict features.
