# HR-1 — recidivism at file grain, CGR cohort (replication on seen repos)

Registered in `hist_replication.md` before this ran. Breadth or falsification; never fresh confirmation.

| repo | files | positives | AUC(LOC) | AUC(recidivism) | lift | 95% CI | recall@20% LOC → recid |
|---|---|---|---|---|---|---|---|
| commons-lang | 520 | 36 | 0.865 | 0.850 | **-0.0145** | -0.079, +0.046 | 0.083 → 0.250 |
| libgit2 | — | — | — | — | — | — | *0 post-cut positives, under the registered floor of 30* |
| libxml2 | 1686 | 48 | 0.974 | 0.964 | **-0.0102** | -0.041, +0.014 | 0.062 → 0.062 |
| postgres | 4358 | 488 | 0.850 | 0.876 | **+0.0261** | +0.010, +0.043 | 0.072 → 0.160 |
| prometheus | 1179 | 80 | 0.889 | 0.876 | **-0.0129** | -0.056, +0.027 | 0.013 → 0.450 |
| redis | 954 | 64 | 0.920 | 0.940 | **+0.0204** | -0.018, +0.057 | 0.078 → 0.141 |
| ripgrep | — | — | — | — | — | — | *9 post-cut positives, under the registered floor of 30* |
| sphinx | 685 | 125 | 0.884 | 0.930 | **+0.0459** | +0.012, +0.078 | 0.024 → 0.136 |

**Pooled:** {"poolable": true, "k": 6, "mean_lift": 0.00912221433963258, "se": 0.010298044957043605, "ci95": [-0.011061953776172884, 0.029306382455438047], "positive": 3, "verdict": "NOT shown at the registered bar"}
