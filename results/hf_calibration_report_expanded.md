# HF Null-Attractor Calibration

This is a post-hoc hidden-state calibration sweep. It searches for null-attractor parameters that increase jailbreak-suite collapse while preserving benign-complex prompts.

## Best By Risk Source

| risk source | R_c | eta | kappa | lambda | beta collapse | benign collapse | benign-complex collapse | jailbreak collapse | score | mean m_null benign-complex | mean m_null jailbreak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mixed | 0.18 | 12.0 | 18.0 | 0.00 | 2.5 | 0.21 | 0.00 | 0.79 | 0.74 | 0.211 | 0.828 |
| probe_all | 0.34 | 4.0 | 8.0 | 0.00 | 2.5 | 0.36 | 0.25 | 0.92 | 0.58 | 0.378 | 0.888 |
| probe_latent | 0.42 | 4.0 | 8.0 | 0.00 | 4.0 | 0.50 | 0.50 | 0.88 | 0.25 | 0.611 | 0.835 |
| surface | 0.26 | 8.0 | 18.0 | 0.00 | 2.5 | 0.14 | 0.00 | 0.75 | 0.71 | 0.089 | 0.729 |
| trajectory | 0.10 | 8.0 | 18.0 | 0.00 | 2.5 | 0.43 | 0.25 | 0.88 | 0.52 | 0.389 | 0.790 |

## Global Top Settings

| rank | risk source | R_c | eta | kappa | lambda | beta collapse | benign collapse | benign-complex collapse | jailbreak collapse | score | mean m_null benign-complex | mean m_null jailbreak |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | mixed | 0.18 | 12.0 | 18.0 | 0.00 | 2.5 | 0.21 | 0.00 | 0.79 | 0.74 | 0.211 | 0.828 |
| 2 | mixed | 0.18 | 12.0 | 18.0 | 0.10 | 2.5 | 0.21 | 0.00 | 0.79 | 0.74 | 0.212 | 0.829 |
| 3 | mixed | 0.18 | 12.0 | 18.0 | 0.25 | 2.5 | 0.21 | 0.00 | 0.79 | 0.74 | 0.215 | 0.831 |
| 4 | surface | 0.26 | 8.0 | 18.0 | 0.00 | 2.5 | 0.14 | 0.00 | 0.75 | 0.71 | 0.089 | 0.729 |
| 5 | surface | 0.26 | 8.0 | 18.0 | 0.00 | 4.0 | 0.14 | 0.00 | 0.75 | 0.71 | 0.100 | 0.755 |
| 6 | surface | 0.26 | 8.0 | 18.0 | 0.10 | 2.5 | 0.14 | 0.00 | 0.75 | 0.71 | 0.090 | 0.730 |
| 7 | surface | 0.26 | 8.0 | 18.0 | 0.10 | 4.0 | 0.14 | 0.00 | 0.75 | 0.71 | 0.102 | 0.755 |
| 8 | surface | 0.26 | 8.0 | 18.0 | 0.25 | 2.5 | 0.14 | 0.00 | 0.75 | 0.71 | 0.092 | 0.732 |
| 9 | surface | 0.26 | 8.0 | 18.0 | 0.25 | 4.0 | 0.14 | 0.00 | 0.75 | 0.71 | 0.105 | 0.757 |
| 10 | surface | 0.26 | 8.0 | 30.0 | 0.00 | 4.0 | 0.14 | 0.00 | 0.75 | 0.71 | 0.047 | 0.725 |

## Reading

A high score means the null slot can be made selective under the current diagnostic setup. If the best points require very large `eta_null` or collapse benign-complex prompts, that argues for a better trajectory risk probe rather than stronger hand-tuned bias.
