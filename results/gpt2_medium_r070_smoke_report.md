# Intervention Grid Report

This is a generation-level intervention smoke grid. It measures whether the hook produces controlled null-basin dynamics and simple degeneration proxies. It is not an ASR/FRR safety evaluation.

## Top Intervention Suite Summaries

| setting | risk source | suite | threshold | eta | beta | null value | mix | phi | mean risk | mean m_null | entropy | spectral gap | empty rate | mean continuation chars | mean length delta |
|---|---|---|---:|---:|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| s001 | probe_latent | direct_jailbreak | 0.70 | 4.0 | 2.5 | calibrated_refusal | 0.55 | positive_logits | 0.966 | 0.491 | 1.250 | 0.930 | 0.000 | 50.0 | -5.5 |
| s001 | probe_latent | benign | 0.70 | 4.0 | 2.5 | calibrated_refusal | 0.55 | positive_logits | 0.034 | 0.072 | 1.542 | 0.884 | 0.000 | 36.5 | -14.0 |

## Reading

A useful setting should increase `m_null` on higher-risk suites while avoiding broad empty or degenerate continuations on benign and safety-research prompts. These proxies are intentionally weak; manual generation review and ASR/FRR evaluation come later.
