# Model Calibration Comparison

Best setting per risk source. These are post-hoc diagnostics, not in-layer generation interventions.

| model | risk source | score | benign collapse | benign-complex collapse | jailbreak collapse | mean m_null benign-complex | mean m_null jailbreak | R_c | eta | kappa | normalized |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tiny-gpt2 | mixed | 0.74 | 0.21 | 0.00 | 0.79 | 0.211 | 0.828 | 0.18 | 12.0 | 18.0 | 0 |
| tiny-gpt2 | probe_all | 0.58 | 0.36 | 0.25 | 0.92 | 0.378 | 0.888 | 0.34 | 4.0 | 8.0 | 0 |
| tiny-gpt2 | probe_latent | 0.25 | 0.50 | 0.50 | 0.88 | 0.611 | 0.835 | 0.42 | 4.0 | 8.0 | 0 |
| tiny-gpt2 | surface | 0.71 | 0.14 | 0.00 | 0.75 | 0.089 | 0.729 | 0.26 | 8.0 | 18.0 | 0 |
| tiny-gpt2 | trajectory | 0.52 | 0.43 | 0.25 | 0.88 | 0.389 | 0.790 | 0.10 | 8.0 | 18.0 | 0 |
| distilgpt2-normalized | mixed | -0.25 | 1.00 | 1.00 | 1.00 | 0.999 | 0.999 | 0.10 | 4.0 | 8.0 | 1 |
| distilgpt2-normalized | probe_all | 0.43 | 0.29 | 0.50 | 1.00 | 0.540 | 0.992 | 0.34 | 4.0 | 18.0 | 1 |
| distilgpt2-normalized | probe_latent | 0.02 | 0.57 | 0.75 | 0.92 | 0.770 | 0.906 | 0.34 | 4.0 | 18.0 | 1 |
| distilgpt2-normalized | surface | 0.71 | 0.14 | 0.00 | 0.75 | 0.103 | 0.718 | 0.26 | 4.0 | 18.0 | 1 |
| distilgpt2-normalized | trajectory | -0.25 | 1.00 | 1.00 | 1.00 | 0.999 | 0.999 | 0.10 | 4.0 | 8.0 | 1 |

## Takeaway

Expanding the prompt suite makes the task harder. Surface and mixed risk remain strongest, while latent-only probes still over-collapse benign safety-research prompts and miss paraphrased or many-shot adversarial prompts.
