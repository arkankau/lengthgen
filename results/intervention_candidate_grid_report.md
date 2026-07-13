# Intervention Grid Report

This is a generation-level intervention smoke grid. It measures whether the hook produces controlled null-basin dynamics and simple degeneration proxies. It is not an ASR/FRR safety evaluation.

## Top Intervention Suite Summaries

| setting | suite | mean risk | mean m_null | empty rate | mean continuation chars | mean length delta |
|---|---|---:|---:|---:|---:|---:|
| s001 | direct_jailbreak | 0.666 | 0.864 | 0.250 | 23.2 | -24.0 |
| s002 | direct_jailbreak | 0.666 | 0.826 | 0.000 | 30.2 | -17.0 |
| s001 | obfuscated_jailbreak | 0.459 | 0.760 | 0.250 | 29.0 | -11.5 |
| s001 | long_context_jailbreak | 0.555 | 0.674 | 0.000 | 33.8 | -13.5 |
| s002 | long_context_jailbreak | 0.555 | 0.558 | 0.000 | 35.5 | -11.8 |
| s002 | obfuscated_jailbreak | 0.459 | 0.476 | 0.250 | 27.2 | -13.2 |
| s001 | many_shot_jailbreak | 0.226 | 0.310 | 0.167 | 23.8 | -22.0 |
| s001 | paraphrased_adversarial | 0.169 | 0.192 | 0.333 | 24.8 | -20.7 |
| s001 | safety_research | 0.129 | 0.143 | 0.000 | 39.3 | -13.8 |
| s001 | benign | 0.110 | 0.091 | 0.000 | 39.5 | -16.2 |
| s001 | benign_complex | 0.089 | 0.070 | 0.000 | 32.0 | -23.5 |
| s002 | many_shot_jailbreak | 0.226 | 0.067 | 0.333 | 21.2 | -24.7 |
| s002 | benign | 0.110 | 0.063 | 0.000 | 39.5 | -16.2 |
| s002 | paraphrased_adversarial | 0.169 | 0.062 | 0.333 | 24.0 | -21.5 |
| s002 | safety_research | 0.129 | 0.056 | 0.000 | 33.3 | -19.8 |
| s002 | benign_complex | 0.089 | 0.053 | 0.000 | 38.8 | -16.8 |

## Reading

A useful setting should increase `m_null` on higher-risk suites while avoiding broad empty or degenerate continuations on benign and safety-research prompts. These proxies are intentionally weak; manual generation review and ASR/FRR evaluation come later.
