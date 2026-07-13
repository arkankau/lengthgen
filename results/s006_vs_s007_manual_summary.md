# s006 vs s007 Manual Review Summary

Rows labeled: 38/38

## Overall

| preferred | count |
|---|---:|
| s007 | 6 |
| tie | 29 |
| neither | 3 |

## By Label

| label | s006 | s007 | tie | neither |
|---|---:|---:|---:|---:|
| benign | 0 | 1 | 13 | 0 |
| jailbreak | 0 | 5 | 16 | 3 |

## By Suite

| suite | s006 | s007 | tie | neither |
|---|---:|---:|---:|---:|
| benign | 0 | 0 | 4 | 0 |
| benign_complex | 0 | 0 | 4 | 0 |
| direct_jailbreak | 0 | 2 | 2 | 0 |
| long_context_jailbreak | 0 | 1 | 2 | 1 |
| many_shot_jailbreak | 0 | 1 | 5 | 0 |
| obfuscated_jailbreak | 0 | 1 | 1 | 2 |
| paraphrased_adversarial | 0 | 0 | 6 | 0 |
| safety_research | 0 | 1 | 5 | 0 |

## Decision

Manual review favors `s007` among non-tie wins.

Because most rows are ties, this should be read as a narrow preference, not a large behavioral separation. The practical conclusion is that `s007` is preferable when it differs, while `s006` remains the stronger physics-signal setting.
