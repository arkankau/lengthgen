# Structured Attractor Bakeoff

This compares zero-sink and structured null-attractor designs on the full local prompt set. Lower utility loss and nonsense are better; `m_null` separation should remain positive.

| candidate | null value | mix | lambda | phi | m_null sep | jailbreak m_null | benign m_null | entropy | spectral gap | ASR proxy | FRR proxy | utility loss | nonsense |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt2_r070 | calibrated_refusal | 0.55 | 0.15 | positive_logits | 0.275 | 0.397 | 0.122 | 1.704 | 0.914 | 0.417 | 0.000 | 0.143 | 0.132 |
| old_s007 | calibrated_refusal | 0.55 | 0.15 | positive_logits | 0.251 | 0.286 | 0.035 | 1.969 | 0.887 | 0.000 | 0.429 | 0.429 | 0.000 |

## Reading

The winning candidate should not be the one with maximum null mass. It should preserve a positive high-risk/benign `m_null` separation while reducing global degeneration, measured here by suggested-label utility loss and nonsense rate.
