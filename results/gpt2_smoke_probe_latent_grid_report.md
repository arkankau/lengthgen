# Intervention Grid Report

This is a generation-level intervention smoke grid. It measures whether the hook produces controlled null-basin dynamics and simple degeneration proxies. It is not an ASR/FRR safety evaluation.

## Top Intervention Suite Summaries

| setting | risk source | suite | threshold | eta | beta | null value | mix | phi | mean risk | mean m_null | entropy | spectral gap | empty rate | mean continuation chars | mean length delta |
|---|---|---|---:|---:|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| s001 | probe_latent | direct_jailbreak | 0.60 | 4.0 | 2.5 | calibrated_refusal | 0.55 | positive_logits | 0.985 | 0.547 | 1.596 | 0.859 | 0.000 | 11.0 | 1.0 |
| s001 | probe_latent | benign | 0.60 | 4.0 | 2.5 | calibrated_refusal | 0.55 | positive_logits | 0.015 | 0.102 | 1.865 | 0.835 | 0.000 | 9.0 | 5.0 |

## Reading

A useful setting should increase `m_null` on higher-risk suites while avoiding broad empty or degenerate continuations on benign and safety-research prompts. These proxies are intentionally weak; manual generation review and ASR/FRR evaluation come later.
