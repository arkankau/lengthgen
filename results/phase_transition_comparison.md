# Phase-Transition Comparison

This table compares mechanism-test evidence across toy embeddings and post-hoc real hidden-state diagnostics. It is not an in-layer intervention result.

| setting | critical R | max slope | susceptibility peak | low-risk m_null | high-risk m_null | jump | universality gap |
|---|---:|---:|---:|---:|---:|---:|---:|
| toy | 0.504 | 6.723 | 0.0166 | 0.075 | 0.999 | 0.924 | 0.019 |
| tiny-gpt2 diagnostic | 0.349 | 0.272 | 0.0002 | 0.035 | 0.033 | -0.002 | 0.007 |
| distilgpt2 normalized diagnostic | 0.495 | 9.032 | 0.0077 | 0.558 | 0.999 | 0.441 | 0.022 |

## Reading

The toy mechanism shows the intended order-parameter jump. The tiny-GPT2 diagnostic does not. The normalized distilGPT2 diagnostic shows a steep transition but starts with excessive low-risk null mass, so it is not yet a useful defense-like operating point.
