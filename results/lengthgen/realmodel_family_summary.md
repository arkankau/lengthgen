# Real-Model Family Robustness

Each row is an in-context key-value recall probe.
The primary statistic is the mean within-length point-biserial correlation with correctness.

| model | heads | examples | lengths | acc drop | attn drop | corr attn | corr normsq | corr -entropy | winner |
|---|---:|---:|---|---:|---:|---:|---:|---:|---|
| EleutherAI/pythia-1.4b | 8 | 900 | 5,10,20,40,80,160 | 0.493 | 0.259 | 0.194 | 0.122 | 0.100 | attn |
| Qwen/Qwen2.5-1.5B | 4 | 900 | 5,10,20,40,80,160 | 0.760 | 0.370 | 0.219 | 0.214 | 0.231 | neg_entropy |
| Qwen/Qwen2.5-1.5B | 8 | 900 | 5,10,20,40,80,160 | 0.760 | 0.356 | 0.268 | 0.223 | 0.248 | attn |
| Qwen/Qwen2.5-1.5B | 16 | 900 | 5,10,20,40,80,160 | 0.760 | 0.295 | 0.317 | 0.176 | 0.246 | attn |
| google/gemma-2-2b | 8 | 900 | 5,10,20,40,80,160 | -0.007 | 0.250 | 0.346 | 0.268 | 0.238 | attn |
