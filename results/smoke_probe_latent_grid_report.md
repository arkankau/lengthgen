# Intervention Grid Report

This is a generation-level intervention smoke grid. It measures whether the hook produces controlled null-basin dynamics and simple degeneration proxies. It is not an ASR/FRR safety evaluation.

## Top Intervention Suite Summaries

| setting | risk source | suite | threshold | eta | beta | null value | mix | phi | mean risk | mean m_null | entropy | spectral gap | empty rate | mean continuation chars | mean length delta |
|---|---|---|---:|---:|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| s001 | probe_latent | direct_jailbreak | 0.26 | 4.0 | 2.5 | calibrated_refusal | 0.55 | positive_logits | 0.985 | 0.521 | 1.710 | 0.787 | 0.000 | 8.0 | -2.0 |
| s001 | probe_latent | benign | 0.26 | 4.0 | 2.5 | calibrated_refusal | 0.55 | positive_logits | 0.015 | 0.023 | 2.181 | 0.757 | 0.000 | 11.0 | -1.0 |

## Reading

A useful setting should increase `m_null` on higher-risk suites while avoiding broad empty or degenerate continuations on benign and safety-research prompts. These proxies are intentionally weak; manual generation review and ASR/FRR evaluation come later.
