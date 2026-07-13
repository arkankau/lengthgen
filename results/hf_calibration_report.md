# HF Null-Attractor Calibration

This is a post-hoc hidden-state calibration sweep. It searches for null-attractor parameters that increase jailbreak-suite collapse while preserving benign-complex prompts.

## Best By Risk Source

| risk source | R_c | eta | kappa | lambda | beta collapse | benign-complex collapse | jailbreak collapse | score | mean m_null benign-complex | mean m_null jailbreak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mixed | 0.18 | 8.0 | 30.0 | 0.00 | 2.5 | 0.00 | 1.00 | 1.00 | 0.052 | 0.976 |
| probe_all | 0.18 | 4.0 | 8.0 | 0.00 | 2.5 | 0.50 | 1.00 | 0.38 | 0.588 | 0.973 |
| probe_latent | 0.42 | 4.0 | 8.0 | 0.00 | 2.5 | 0.50 | 0.83 | 0.21 | 0.636 | 0.807 |
| surface | 0.26 | 8.0 | 18.0 | 0.00 | 2.5 | 0.00 | 1.00 | 1.00 | 0.089 | 0.975 |
| trajectory | 0.10 | 8.0 | 18.0 | 0.00 | 2.5 | 0.25 | 0.83 | 0.46 | 0.389 | 0.781 |

## Global Top Settings

| rank | risk source | R_c | eta | kappa | lambda | beta collapse | benign-complex collapse | jailbreak collapse | score | mean m_null benign-complex | mean m_null jailbreak |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | surface | 0.26 | 8.0 | 18.0 | 0.00 | 2.5 | 0.00 | 1.00 | 1.00 | 0.089 | 0.975 |
| 2 | surface | 0.26 | 8.0 | 18.0 | 0.00 | 4.0 | 0.00 | 1.00 | 1.00 | 0.100 | 0.991 |
| 3 | surface | 0.26 | 8.0 | 18.0 | 0.10 | 2.5 | 0.00 | 1.00 | 1.00 | 0.090 | 0.975 |
| 4 | surface | 0.26 | 8.0 | 18.0 | 0.10 | 4.0 | 0.00 | 1.00 | 1.00 | 0.102 | 0.991 |
| 5 | surface | 0.26 | 8.0 | 18.0 | 0.25 | 2.5 | 0.00 | 1.00 | 1.00 | 0.092 | 0.976 |
| 6 | surface | 0.26 | 8.0 | 18.0 | 0.25 | 4.0 | 0.00 | 1.00 | 1.00 | 0.105 | 0.992 |
| 7 | surface | 0.26 | 8.0 | 30.0 | 0.00 | 4.0 | 0.00 | 1.00 | 1.00 | 0.047 | 0.975 |
| 8 | surface | 0.26 | 8.0 | 30.0 | 0.10 | 2.5 | 0.00 | 1.00 | 1.00 | 0.048 | 0.959 |
| 9 | surface | 0.26 | 8.0 | 30.0 | 0.10 | 4.0 | 0.00 | 1.00 | 1.00 | 0.048 | 0.976 |
| 10 | surface | 0.26 | 8.0 | 30.0 | 0.25 | 2.5 | 0.00 | 1.00 | 1.00 | 0.049 | 0.960 |

## Reading

A high score means the null slot can be made selective under the current diagnostic setup. If the best points require very large `eta_null` or collapse benign-complex prompts, that argues for a better trajectory risk probe rather than stronger hand-tuned bias.
