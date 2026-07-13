# Intervention Grid Report

This is a generation-level intervention smoke grid. It measures whether the hook produces controlled null-basin dynamics and simple degeneration proxies. It is not an ASR/FRR safety evaluation.

## Top Intervention Suite Summaries

| setting | suite | mean risk | mean m_null | empty rate | mean continuation chars | mean length delta |
|---|---|---:|---:|---:|---:|---:|
| s007 | direct_jailbreak | 0.727 | 0.912 | 1.000 | 0.0 | -36.0 |
| s007 | long_context_jailbreak | 0.715 | 0.911 | 1.000 | 0.0 | -33.0 |
| s008 | direct_jailbreak | 0.727 | 0.910 | 1.000 | 0.0 | -36.0 |
| s008 | long_context_jailbreak | 0.715 | 0.909 | 1.000 | 0.0 | -33.0 |
| s007 | obfuscated_jailbreak | 0.532 | 0.908 | 1.000 | 0.0 | -24.0 |
| s003 | direct_jailbreak | 0.727 | 0.866 | 0.000 | 22.0 | -14.0 |
| s004 | direct_jailbreak | 0.727 | 0.865 | 0.000 | 22.0 | -14.0 |
| s008 | obfuscated_jailbreak | 0.532 | 0.860 | 1.000 | 0.0 | -24.0 |
| s003 | obfuscated_jailbreak | 0.532 | 0.855 | 1.000 | 0.0 | -24.0 |
| s003 | long_context_jailbreak | 0.715 | 0.825 | 0.000 | 16.0 | -17.0 |
| s004 | long_context_jailbreak | 0.715 | 0.823 | 0.000 | 16.0 | -17.0 |
| s004 | obfuscated_jailbreak | 0.532 | 0.794 | 1.000 | 0.0 | -24.0 |
| s007 | many_shot_jailbreak | 0.288 | 0.701 | 0.000 | 33.0 | 11.0 |
| s005 | direct_jailbreak | 0.727 | 0.685 | 0.000 | 23.0 | -13.0 |
| s006 | direct_jailbreak | 0.727 | 0.683 | 0.000 | 23.0 | -13.0 |
| s007 | safety_research | 0.277 | 0.668 | 1.000 | 0.0 | -22.0 |
| s005 | obfuscated_jailbreak | 0.532 | 0.646 | 0.000 | 27.0 | 3.0 |
| s005 | long_context_jailbreak | 0.715 | 0.589 | 1.000 | 0.0 | -33.0 |
| s006 | long_context_jailbreak | 0.715 | 0.587 | 1.000 | 0.0 | -33.0 |
| s006 | obfuscated_jailbreak | 0.532 | 0.580 | 1.000 | 0.0 | -24.0 |

## Reading

A useful setting should increase `m_null` on higher-risk suites while avoiding broad empty or degenerate continuations on benign and safety-research prompts. These proxies are intentionally weak; manual generation review and ASR/FRR evaluation come later.
