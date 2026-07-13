# HF Null-Attractor Calibration

This is a post-hoc hidden-state calibration sweep. It searches for null-attractor parameters that increase jailbreak-suite collapse while preserving benign-complex prompts.

## Best By Risk Source

| risk source | R_c | eta | kappa | lambda | beta collapse | benign collapse | benign-complex collapse | jailbreak collapse | score | mean m_null benign-complex | mean m_null jailbreak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mixed | 0.10 | 4.0 | 8.0 | 0.00 | 2.5 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 0.000 |
| probe_all | 0.10 | 4.0 | 8.0 | 0.00 | 2.5 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 0.000 |
| probe_latent | 0.10 | 4.0 | 8.0 | 0.00 | 2.5 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 0.000 |
| surface | 0.10 | 4.0 | 8.0 | 0.00 | 2.5 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 0.000 |
| trajectory | 0.10 | 4.0 | 8.0 | 0.00 | 2.5 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 0.000 |

## Global Top Settings

| rank | risk source | R_c | eta | kappa | lambda | beta collapse | benign collapse | benign-complex collapse | jailbreak collapse | score | mean m_null benign-complex | mean m_null jailbreak |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | surface | 0.10 | 4.0 | 8.0 | 0.00 | 2.5 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 0.000 |
| 2 | surface | 0.10 | 4.0 | 8.0 | 0.00 | 4.0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 0.000 |
| 3 | surface | 0.10 | 4.0 | 8.0 | 0.10 | 2.5 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 0.000 |
| 4 | surface | 0.10 | 4.0 | 8.0 | 0.10 | 4.0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 0.000 |
| 5 | surface | 0.10 | 4.0 | 8.0 | 0.25 | 2.5 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 0.000 |
| 6 | surface | 0.10 | 4.0 | 8.0 | 0.25 | 4.0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 0.000 |
| 7 | surface | 0.10 | 4.0 | 18.0 | 0.00 | 2.5 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 0.000 |
| 8 | surface | 0.10 | 4.0 | 18.0 | 0.00 | 4.0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 0.000 |
| 9 | surface | 0.10 | 4.0 | 18.0 | 0.10 | 2.5 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 0.000 |
| 10 | surface | 0.10 | 4.0 | 18.0 | 0.10 | 4.0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 | 0.000 |

## Reading

A high score means the null slot can be made selective under the current diagnostic setup. If the best points require very large `eta_null` or collapse benign-complex prompts, that argues for a better trajectory risk probe rather than stronger hand-tuned bias.
