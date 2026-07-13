# Ranked Intervention Settings

Settings are ranked by a utility-first objective: preserve positive high-risk/benign `m_null` separation while penalizing benign utility loss, nonsense, ASR proxy, and FRR proxy.

| rank | setting | threshold | eta | mix | beta | lambda | phi | sep | jail m_null | benign m_null | entropy | ASR | FRR | utility loss | nonsense |
|---:|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | s006 | 0.26 | 4.00 | 1.00 | 2.00 | 0.15 | positive_logits | 0.436 | 0.501 | 0.065 | 1.506 | 0.000 | 0.500 | 0.500 | 0.000 |
| 2 | s008 | 0.26 | 4.00 | 1.00 | 2.50 | 0.15 | positive_logits | 0.459 | 0.525 | 0.066 | 1.376 | 0.000 | 0.571 | 0.571 | 0.000 |
| 3 | s007 | 0.26 | 4.00 | 0.55 | 2.50 | 0.15 | positive_logits | 0.251 | 0.286 | 0.035 | 1.969 | 0.000 | 0.429 | 0.429 | 0.000 |
| 4 | s005 | 0.26 | 4.00 | 0.55 | 2.00 | 0.15 | positive_logits | 0.239 | 0.274 | 0.035 | 2.016 | 0.000 | 0.429 | 0.429 | 0.000 |
| 5 | s002 | 0.26 | 3.00 | 1.00 | 2.00 | 0.15 | positive_logits | 0.283 | 0.334 | 0.051 | 1.650 | 0.000 | 0.500 | 0.500 | 0.000 |
| 6 | s003 | 0.26 | 3.00 | 0.55 | 2.50 | 0.15 | positive_logits | 0.164 | 0.191 | 0.027 | 1.961 | 0.000 | 0.429 | 0.429 | 0.000 |
| 7 | s001 | 0.26 | 3.00 | 0.55 | 2.00 | 0.15 | positive_logits | 0.153 | 0.181 | 0.028 | 2.021 | 0.000 | 0.429 | 0.429 | 0.000 |
| 8 | s004 | 0.26 | 3.00 | 1.00 | 2.50 | 0.15 | positive_logits | 0.300 | 0.350 | 0.051 | 1.511 | 0.000 | 0.571 | 0.571 | 0.026 |
