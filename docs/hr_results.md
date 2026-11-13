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

---

# HR-1b / HR-2b / HR-3b — the same three with a cleaned fix label

Registered in `hist_replication.md` **before** the re-run. Only the label changed. The raw-label results above
stay published; neither label is chosen afterwards for being more flattering.

FIXLIKE v3c drops **28–54%** of each repo's keyword fix commits.

## HR-1b — recidivism's advantage over size does **not** survive the cleaning

| repo | raw positives | raw lift | cleaned positives | cleaned lift |
|---|---|---|---|---|
| commons-lang | 108 | **+0.143** | 36 | **−0.015** |
| sphinx | 174 | +0.117 | 125 | +0.046 |
| postgres | 963 | +0.110 | 488 | +0.026 |
| redis | 91 | +0.091 | 64 | +0.020 |
| libxml2 | 104 | +0.025 | 48 | −0.010 |
| prometheus | 128 | +0.009 | 80 | −0.013 |

| | pooled lift | 95% CI | positive | verdict |
|---|---|---|---|---|
| raw label | **+0.082** | [+0.039, +0.125] | 6/6 | breadth shown |
| cleaned | **+0.009** | [−0.011, +0.029] | 3/6 | **not shown** |

**commons-lang reverses sign.** `AUC(LOC)` *rises* under cleaning in every repo (postgres 0.803→0.850, redis
0.879→0.920, libxml2 0.946→0.974): size predicts real fixes better than it predicts housekeeping, and a large
part of recidivism's measured edge was predicting repeat housekeeping — files that keep getting Javadoc and
lint touched are, unsurprisingly, repeatedly touched.

## HR-2b — entropy's inferiority was also a label artefact

| | pooled vs LOC | pooled vs recidivism |
|---|---|---|
| raw label | +0.002 [−0.023, +0.026], 4/6 | **−0.073 [−0.111, −0.034], 0/6** |
| cleaned | +0.000 [−0.016, +0.016], 3/6 | **+0.009 [−0.015, +0.033], 4/6** |

Under the raw label entropy lost to recidivism in six of six repos. Under the cleaned label the two are
statistically indistinguishable. **Neither beats LOC.**

## HR-3b — unchanged, and still uninformative

Pooled **−0.103** [−0.135, −0.070], 0 of 6 positive. The pre-registered caveat stands: the quarterly-snapshot
mapping makes a null uninformative, so tc#28 is still *not answered*.

## Which rule did the cutting — and why it matters

| rule | what it drops | count (4 repos) |
|---|---|---|
| **C** | no fix word in the subject | 5,673 |
| **B** | non-behavioural subject (lint, javadoc, typo, style) | 2,532 |
| **B2** | refactor / prose / build subject | 1,336 |
| **B3** | edits a code comment | 567 |
| **A** | test/doc paths only | 13 |

This decomposition changes the reading, and the two big repos differ:

- **commons-lang**, where the effect reverses, is cut mostly by **rule B** (357 of 460) — *genuinely cosmetic*
  commits. Its +0.143 really was substantially housekeeping.
- **postgres** is cut mostly by **rule C** (4,851), the rule with a real recall cost: a genuine fix whose
  subject never says "fix" is discarded. Postgres nonetheless stays positive (+0.026).

So the collapse is strongest exactly where the cleaning is most defensible, and weakest where the cleaning is
most aggressive. That is the opposite of what a cleaning artefact would look like.

## What this does and does not establish

**It does not refute recidivism.** v3c was audited on a different label family and inherits no precision here;
rule C certainly discards real fixes. A validated label could land anywhere between the two columns.

**What it does establish is sharper, and it is methodological:** the program's one cross-repo replicated
predictor rests on a keyword label whose precision was never audited on these repos, and its measured advantage
**does not survive a plausible cleaning of that label**. Until the label is audited here, the honest statement
is *recidivism's advantage over size is label-dependent on this cohort*, not *history predicts*.

**The cheapest next step** is the one the program already has machinery for: audit the fix label on a stratified
sample of these repos (the `otherfix_audit.md` pattern), and re-run both columns against the audited label.
