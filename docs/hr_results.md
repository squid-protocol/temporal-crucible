# HR-1 / HR-2 / HR-3 — results on the CGR cohort

Registered in `hist_replication.md` **before** each was run. **Replication on seen repos**: breadth or
falsification, never fresh confirmation. The eight are the CGR cohort and have already carried CGT/CGN/CGK,
LIB, CPF, DRP and CGN-CR. openssl stays the untouched holdout. Same cut, window, baseline and floors
throughout, so the three are directly comparable on the same files.

## HR-1 — recidivism at file grain: **replicates**

| repo | language | AUC(LOC) → AUC(recidivism) | lift |
|---|---|---|---|
| commons-lang | java | 0.740 → 0.884 | **+0.143** |
| sphinx | python | 0.865 → 0.981 | **+0.117** |
| postgres | c | 0.803 → 0.913 | **+0.110** |
| redis | c | 0.879 → 0.970 | **+0.091** |
| libxml2 | c | 0.946 → 0.971 | +0.025 |
| prometheus | go | 0.875 → 0.883 | +0.009 |

Pooled lift **+0.082**, 95% CI **[+0.039, +0.125]**. Six of six evaluable repos positive; at a 20% review
budget recidivism beats LOC in every one. Bar met on direction, denominator one short of the registered 6-of-8
because libgit2 (cut lands in a 4-commit desert) and ripgrep (29 positives against a floor of 30) were
excluded by floors set in advance and not moved afterwards.

## HR-2 — change entropy `HCM1_LD_30`: **does not replicate, and never beats recidivism**

| repo | AUC(LOC) | AUC(entropy) | AUC(recidivism) | lift vs LOC | lift vs recidivism |
|---|---|---|---|---|---|
| commons-lang | 0.740 | 0.708 | 0.847 | −0.032 | −0.139 |
| libxml2 | 0.946 | 0.955 | 0.961 | +0.008 | −0.007 |
| postgres | 0.804 | 0.818 | 0.912 | +0.014 | −0.094 |
| prometheus | 0.873 | 0.837 | 0.871 | −0.036 | −0.034 |
| redis | 0.867 | 0.913 | 0.973 | +0.045 | −0.061 |
| sphinx | 0.870 | 0.881 | 0.983 | +0.011 | −0.101 |

**Against LOC**: pooled **+0.002**, CI **[−0.023, +0.026]** — contains zero, 4 of 6 positive. **The registered
bar is not met.**

**Against recidivism**: pooled **−0.073**, CI **[−0.111, −0.034]** — **0 of 6 positive**. Change entropy is
worse than the plain prior-fix count in **every single repo**, and the interval excludes zero.

This is the sharper of the two readings. `HCM1_LD_30` was the program's only *feature* to beat LOC
out-of-selection, on one repo. On six repos in four languages it does not beat LOC on average, and it is
consistently beaten by a predictor that needs no line deltas at all. The one-repo result does not generalise.

## HR-3 — function-grain recidivism: **negative, and uninformative by its own registration**

| repo | functions | AUC(LOC) → AUC(recidivism) | lift | node merge |
|---|---|---|---|---|
| redis | 8097 | 0.702 → 0.725 | +0.023 | 4.1% |
| libxml2 | 4197 | 0.705 → 0.702 | −0.004 | 1.8% |
| sphinx | 5196 | 0.758 → 0.682 | −0.075 | 17.5% |
| commons-lang | 7577 | 0.681 → 0.592 | −0.090 | 21.8% |
| postgres | 26766 | 0.768 → 0.674 | −0.094 | 1.7% |
| prometheus | 6347 | 0.726 → 0.627 | −0.099 | 8.9% |
| ripgrep | 1822 | 0.750 → 0.503 | −0.247 | 13.9% |

Pooled lift **−0.084**, CI **[−0.148, −0.020]**, 1 of 7 positive.

**This does not say function-grain recidivism fails.** The registration stated in advance that the
hunk-to-function mapping is approximate — function spans come from *quarterly* snapshots while commits are
not quarterly, so a function that moved within a quarter can absorb a neighbour's hit — and that this "makes a
positive result conservative and a **null uninformative**." The result is a null, so the pre-committed reading
applies: the mapping is not sharp enough to answer tc#28 either way.

What the numbers do show is that **file-grain beats function-grain here** (+0.082 against −0.084 on the same
repos and cut), so there is no evidence that moving to function grain sharpens the program's strongest
predictor — and a real cost to trying. Note also that function-grain AUC for LOC alone (0.68–0.77) is well
below file-grain (0.74–0.95): the unit itself is harder.

**To answer tc#28 properly** the mapping must be sharpened: function spans at the *commit*, not at the nearest
quarter. That is a per-commit parse, which the harvest's hunk ranges already support but the quarterly walks do
not supply. Until then the honest status is "not answered", not "falsified".

## Standing after these three

The program's one-sentence standing was *history predicts, structure describes*. These runs tighten the first
half and narrow it: **prior fixes predict; the elaborated history metric does not add; and the file is the unit
where it works.** The simplest history predictor in the program beat the sophisticated one in every repo tested.
