# Real-Model Family Robustness

Each row is an in-context key-value recall probe.
The primary statistic is the mean within-length point-biserial correlation with correctness.

| model | heads | examples | lengths | acc drop | attn drop | corr attn | corr normsq | corr -entropy | winner |
|---|---:|---:|---|---:|---:|---:|---:|---:|---|
| EleutherAI/pythia-1.4b | 8 | 900 | 5,10,20,40,80,160 | 0.493 | 0.259 | 0.194 | 0.122 | 0.100 | attn |
