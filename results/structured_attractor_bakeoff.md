# Structured Attractor Bakeoff

This compares zero-sink and structured null-attractor designs on the full local prompt set. Lower utility loss and nonsense are better; `m_null` separation should remain positive.

| candidate | null value | mix | lambda | phi | m_null sep | jailbreak m_null | benign m_null | entropy | spectral gap | ASR proxy | FRR proxy | utility loss | nonsense |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| safe_full | safe_redirection | 1.00 | 0.00 | uniform | 0.458 | 0.510 | 0.052 | 1.499 | 0.888 | 0.000 | 0.071 | 0.714 | 0.474 |
| zero_sink | zero | 1.00 | 0.00 | uniform | 0.456 | 0.507 | 0.051 | 1.493 | 0.887 | 0.000 | 0.071 | 0.714 | 0.474 |
| safe_soft_phi | safe_redirection | 0.55 | 0.15 | positive_logits | 0.257 | 0.286 | 0.029 | 2.107 | 0.870 | 0.000 | 0.071 | 0.714 | 0.474 |

## Reading

The winning candidate should not be the one with maximum null mass. It should preserve a positive high-risk/benign `m_null` separation while reducing global degeneration, measured here by suggested-label utility loss and nonsense rate.
