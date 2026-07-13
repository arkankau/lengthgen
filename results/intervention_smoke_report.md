# Phase 4 Intervention Smoke Report

This is a mechanics smoke test for in-layer GPT-2 attention intervention. It does not evaluate safety or prove jailbreak defense.

| case | suite | risk | selected layers | row mean m_null | log mean m_null |
|---|---|---:|---|---:|---:|
| benign | benign | 0.080 | 4,5 | 0.106 | 0.106 |
| direct jailbreak | direct_jailbreak | 0.727 | 4,5 | 0.919 | 0.919 |

## Reading

The hook fires inside selected GPT-2 attention layers and records per-layer/head null mass. In this smoke run, higher risk produces much larger null mass, which verifies the intervention plumbing and logging path. Generation-quality and safety behavior remain untested.
