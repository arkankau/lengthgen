# HF Null-Attractor Calibration

This is a post-hoc hidden-state calibration sweep. It searches for null-attractor parameters that increase jailbreak-suite collapse while preserving benign-complex prompts.

## Best By Risk Source

| risk source | R_c | eta | kappa | lambda | beta collapse | benign collapse | benign-complex collapse | jailbreak collapse | score | mean m_null benign-complex | mean m_null jailbreak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mixed | 0.10 | 4.0 | 8.0 | 0.00 | 2.5 | 1.00 | 1.00 | 1.00 | -0.25 | 0.999 | 0.999 |
| probe_all | 0.34 | 4.0 | 18.0 | 0.00 | 2.5 | 0.29 | 0.50 | 1.00 | 0.43 | 0.540 | 0.992 |
| probe_latent | 0.34 | 4.0 | 18.0 | 0.00 | 2.5 | 0.57 | 0.75 | 0.92 | 0.02 | 0.770 | 0.906 |
| surface | 0.26 | 4.0 | 18.0 | 0.00 | 4.0 | 0.14 | 0.00 | 0.75 | 0.71 | 0.103 | 0.718 |
| trajectory | 0.10 | 4.0 | 8.0 | 0.00 | 2.5 | 1.00 | 1.00 | 1.00 | -0.25 | 0.999 | 0.999 |

## Global Top Settings

| rank | risk source | R_c | eta | kappa | lambda | beta collapse | benign collapse | benign-complex collapse | jailbreak collapse | score | mean m_null benign-complex | mean m_null jailbreak |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | surface | 0.26 | 4.0 | 18.0 | 0.00 | 4.0 | 0.14 | 0.00 | 0.75 | 0.71 | 0.103 | 0.718 |
| 2 | surface | 0.26 | 4.0 | 18.0 | 0.10 | 4.0 | 0.14 | 0.00 | 0.75 | 0.71 | 0.104 | 0.720 |
| 3 | surface | 0.26 | 4.0 | 18.0 | 0.25 | 4.0 | 0.14 | 0.00 | 0.75 | 0.71 | 0.107 | 0.724 |
| 4 | surface | 0.26 | 8.0 | 30.0 | 0.00 | 2.5 | 0.14 | 0.00 | 0.75 | 0.71 | 0.083 | 0.736 |
| 5 | surface | 0.26 | 8.0 | 30.0 | 0.00 | 4.0 | 0.14 | 0.00 | 0.75 | 0.71 | 0.087 | 0.757 |
| 6 | surface | 0.26 | 8.0 | 30.0 | 0.10 | 2.5 | 0.14 | 0.00 | 0.75 | 0.71 | 0.084 | 0.737 |
| 7 | surface | 0.26 | 8.0 | 30.0 | 0.10 | 4.0 | 0.14 | 0.00 | 0.75 | 0.71 | 0.088 | 0.758 |
| 8 | surface | 0.26 | 8.0 | 30.0 | 0.25 | 2.5 | 0.14 | 0.00 | 0.75 | 0.71 | 0.085 | 0.738 |
| 9 | surface | 0.26 | 8.0 | 30.0 | 0.25 | 4.0 | 0.14 | 0.00 | 0.75 | 0.71 | 0.089 | 0.759 |
| 10 | surface | 0.26 | 12.0 | 30.0 | 0.00 | 2.5 | 0.14 | 0.00 | 0.75 | 0.71 | 0.100 | 0.764 |

## Reading

A high score means the null slot can be made selective under the current diagnostic setup. If the best points require very large `eta_null` or collapse benign-complex prompts, that argues for a better trajectory risk probe rather than stronger hand-tuned bias.
