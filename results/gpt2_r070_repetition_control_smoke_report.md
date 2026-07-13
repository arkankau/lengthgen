# Intervention Grid Report

This is a generation-level intervention smoke grid. It measures whether the hook produces controlled null-basin dynamics and simple degeneration proxies. It is not an ASR/FRR safety evaluation.

## Top Intervention Suite Summaries

| setting | risk source | suite | threshold | eta | beta | null value | mix | phi | mean risk | mean m_null | entropy | spectral gap | empty rate | mean continuation chars | mean length delta |
|---|---|---|---:|---:|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| s001 | probe_latent | direct_jailbreak | 0.70 | 4.0 | 2.5 | calibrated_refusal | 0.55 | positive_logits | 0.956 | 0.542 | 1.626 | 0.936 | 0.000 | 55.5 | -2.5 |
| s001 | probe_latent | benign | 0.70 | 4.0 | 2.5 | calibrated_refusal | 0.55 | positive_logits | 0.043 | 0.083 | 1.663 | 0.900 | 0.000 | 61.5 | 2.0 |

## Reading

A useful setting should increase `m_null` on higher-risk suites while avoiding broad empty or degenerate continuations on benign and safety-research prompts. These proxies are intentionally weak; manual generation review and ASR/FRR evaluation come later.
