# REW — does rewiring predict fixes, and does it predict the *right kind*? — drafted 2026-11-11

**Status: APPROVED by the owner 2026-11-11, after Amendment 1 and before any statistic.** Nothing below had
been computed when approval was given. `tools/rew_eval.py` is written against this text and follows it as
written; the only quantity it adds is the equivalence margin for REW-H4, fixed at the program's standing
**δ = 0.02** (the value used by LIB-H1..H3), likewise before any statistic.

**Unit:** a function at a quarterly snapshot. **Repos:** curl (primary), libarchive (replication, unseen for
this question). **Tool:** `tools/rew_eval.py` (to be written). **Data:** the walk databases
(`calls_out_to` is populated in all 809,654 curl function-rows) plus tree-sitter on source.

## 1 · Why

Two results from 2026-11-11 set this up.

- **`docs/kwnest.md`:** a function's control skeleton is laid down at birth and essentially never
  rearranged. Of 375 curl functions that were **edited** while keeping an identical keyword multiset, the
  keyword **order** changed in 0.0% and **nesting depth** in 1.3%. What changed instead was naming and
  wiring: identifiers were 41.1% of all leaf-token differences, field identifiers 6.9%, types ~5%.
  **Functions mature by being rewired, not restructured.**
- **`docs/fix_class_synthesis.md`:** the fix classes are different *causes* with different predictors, and
  for **extrinsic** fixes the predictor is structural — platform-conditional density and library-coupling
  surface, **+0.17 / +0.12 over the stronger size order on unseen repos, and worse than size for every other
  class** (ENV-H1..H3, LIB-H1..H3).

Coupling *surface* predicts extrinsic fixes. Rewiring is coupling *change*. So the question is not the vague
"does the call graph predict defects" but a specific, falsifiable one: **does rewiring predict the class the
coupling surface already predicts, and only that class?**

This also tests the program's own standing summary. "Structure describes, history predicts" was derived from
a pooled outcome; if rewiring works and works class-specifically, the summary needs the class split.

## 2 · Prior work (checked 2026-11-11, before any statistic)

- **Zimmermann and Nagappan, "Predicting Defects using Network Analysis on Dependency Graphs", ICSE 2008,
  pp. 531–540, doi 10.1145/1368088.1368161.** Network measures on the dependency graph of Windows Server 2003
  gave about **10 percentage points higher recall** than complexity metrics, and flagged 60% of the binaries
  developers called critical — roughly twice what complexity flagged. **This is static position, not change**,
  and at binary grain.
- **Nagappan and Ball, "Use of Relative Code Churn Measures to Predict System Defect Density", ICSE 2005,
  pp. 284–292, doi 10.1145/1062455.1062514.** On the same system, **absolute churn measures were weak
  predictors and relative ones were strong** (89.0% classification accuracy). **Consequence for this design,
  adopted below: the rewiring measure is relative by construction, and churn is a baseline to beat rather
  than a covariate to add.**
- **Nagappan and Ball, ESEM 2007** (dependencies and churn combined predict post-release failures) and
  **Zimmermann et al., ICST 2011** (a component's failures relate to how often its dependencies change) are
  the closest existing work to "dependency churn". Both are component/binary grain and neither splits the
  outcome by fix cause.
- **Nesting depth** has a thinner literature than its reputation suggests. A search surfaced one industrial
  study reporting Lines of Code and **Maximum Nesting Level** as the metrics that were commonly effective
  across its models; its venue could not be verified and it is cited here as weak support only. Most hits for
  "depth" concern inheritance depth (DIT), a different metric.
- **This program:** CGR / CGT / CGK found call-network position matters for fix classes at file grain;
  recidivism beats every static ranking (p < 1e-4) and is the baseline any new predictor must clear.
- **This study's difference:** **function grain**, **call-set change rather than position**, and an outcome
  **split by fix cause** with a prediction registered in advance about *which* class should move. No prior
  work found tests dependency churn against a cause-specific outcome.

## 3 · Measures

**Predictor A — rewiring (relative, per Nagappan and Ball).** For a function between consecutive snapshots,
from `calls_out_to`: `rewire = |added ∪ removed| / |union of both call sets|`, the Jaccard distance between
its call sets. Relative by construction, so a function that adds two callees to forty is not scored like one
that replaces two of three.

**Predictor B — nesting depth.** Maximum and mean nesting depth of control keywords within the function at
the snapshot, from tree-sitter (`tools/kwnest_eval.py:keyword_profile`). **This has never been measured in
this program**: `function_data` holds one positional column, `start_line`, and `complexity` equals
`struct_branch` in all 809,654 rows — it is the branch count, not a control-flow measure.

**Outcome.** A fix of class C (`tools/xc_harvest.py` classes; `other-fix` under the registered FIXLIKE v3c
rule) whose hunks map to this function in the following window, via `chg_eval.map_fix` — the existing
mapper, not a new one.

**Baselines the predictor must beat** (all of them, not any of them):
1. `loc`;
2. `struct_branch` (branch count) — so depth must prove it is not a count in disguise;
3. **edit count** — how many snapshots the function changed in. This is the one that matters: a rewired
   function is an edited function, and recidivism already beats every static ranking. **Without this control
   the study rediscovers "code that changes gets fixed".**
4. `func_fan_in` / `func_fan_out` level — so rewiring is not rediscovering CGR/CGT's position effects.

## 4 · Registered claims (verbatim)

> **REW-H1 (primary).** Rewiring predicts **extrinsic** fixes at a 20%-of-lines review budget beyond `loc`,
> branch count, **edit count** and fan-in/fan-out level. One-sided; the direction is that more rewiring means
> more extrinsic fixes.
>
> **REW-H2 (class specificity).** Rewiring's lift over those baselines is **larger for extrinsic fixes than
> for regression, latent and other-fix**. A lift that is flat across classes is reported as **churn in
> disguise**, not as support for REW-H1.
>
> **REW-H3.** Maximum nesting depth predicts **latent** fixes beyond `loc` and branch count. One-sided; the
> direction is that deeper nesting means more latent fixes — the reading being that deeply nested code is
> where a defect hides from review.
>
> **REW-H4 (guard, stated as a claim so it cannot be skipped).** If REW-H1 fails, the result is reported as
> an **equivalence test (TOST)** against the churn baseline with its δ, not as "inconclusive".

α = 0.01 per claim, Bonferroni across the four fix classes within REW-H2. Verdicts are read only after all
four are computed.

## 5 · Power (measured before drafting, not assumed)

curl, whole history, file grain: **extrinsic 681 events over 467 distinct files**; latent 185 over 180;
regression 1,069 over 588; other-fix 6,417 over 1,179. Extrinsic has been rising — 17–23 events a year
through 2023, then 42, 54 and 52 in 2024–26.

### Function-grain confirmation (run 2026-11-11 with `chg_eval.map_fix`; see Amendment 1)

The registration's own precondition, now met. Counts **rise** at function grain rather than falling, because a
fix commit typically touches several functions:

| class | curl: commit events | function-events | **distinct functions** | libarchive: distinct functions |
|---|---|---|---|---|
| extrinsic | 681 | 1,195 | **856** | **1,086** |
| latent | 185 | 598 | **493** | **0** |
| regression | 239 | 419 | **316** | 42 |
| other-fix | 6,417 | 16,541 | **5,714** | 2,049 |

Every curl class clears ≥ 20 comfortably, including latent — the class flagged as at risk, which is not at
risk. **libarchive holds no latent events at all**, which changes the replication plan (Amendment 1 item 2).

## 6 · Guards

- [x] Size-matched comparison, and the bar is **lift over the stronger size order**, both orderings reported
      (the convention of ENV-H1..H3; a random ranking beat big-files-first on curl earlier today, so naming
      one size order in advance hands a weak baseline to the instrument).
- [x] Edit-count control — the confound most likely to produce a false positive here.
- [x] ≥ 20-positive rule per evaluated cell; cells under it are printed UNDERPOWERED and not read.
- [x] Bonferroni across the four classes.
- [x] Rename tracking (`git diff --name-status -M`): identity is otherwise `(file_path, func_name)`, under
      which a rename reads as death and birth.
- [ ] Temporal ablation (`GITGALAXY_DISABLE_GIT_HISTORY=1`) — **not applicable and stated so**: rewiring is a
      history measure by construction. The honest equivalent is the edit-count control above.
- [x] Replication **by claim** (Amendment 1 item 2): REW-H1 and REW-H2 on **libarchive** (1,086 extrinsic
      functions, unseen for this question); REW-H3 on **openssl**, the only non-curl repo in the pool with
      substantial latent events (235). libarchive and harfbuzz have **none**.

## 7 · What this cannot establish

Rewiring is chosen by developers, not assigned: a function gets rewired because someone decided to change it,
possibly *because* they already suspected it. Confounding by indication is not closed by any control here —
the same limit AIADOPT hit this morning. A positive REW-H1 says rewiring **marks** extrinsic risk, never that
it causes it. And curl plus libarchive is two C projects, so a pass is a replicated development-set result,
not a panel result.


## Amendment 1 (2026-11-11, before any statistic; resolves the draft's own precondition)

1. **Function-grain power confirmed, and it is better than the file-grain estimate.** Measured with the
   program's own `chg_eval.map_fix`, not a new mapper. Mapping *raises* the counts — a fix commit touches
   several functions — so curl gives 856 distinct extrinsic functions, 493 latent, 316 regression and 5,714
   other-fix. **Latent, flagged in the draft as the class at risk, clears the bar by 25×.** The draft's
   clause "must be confirmed before this registration is final" is hereby discharged.

2. **The replication plan splits by claim, because libarchive has no latent events.** The draft named
   libarchive for everything. It holds **zero** latent events (harfbuzz likewise). So:
   - **REW-H1 / REW-H2** (extrinsic) replicate on **libarchive** — 1,086 distinct extrinsic functions, more
     than curl's 856.
   - **REW-H3** (nesting depth → latent) replicates on **openssl** (235 latent events), the only non-curl
     pool repo with a substantial latent class. nDPI has 105 and is the fallback.
   - If REW-H3 cannot be replicated, it is reported as **curl-only and unreplicated**, never as supported.

3. **The regression class must be named precisely.** `chg_eval.fix_events` splits the xc file's 1,069 curl
   `regression` events into `regression` (239, where `why == "regression word"`) and `regression-linked`
   (the remainder, identified through a linked inducing commit). The draft's power table quoted the
   undivided 1,069. **This study uses the union of both sub-classes as "regression"**, reports the split
   beside the result, and treats a result that holds in only one sub-class as not supported.

4. **Unchanged.** Every claim, direction, bar and α; the baselines, above all the edit-count control; the
   measures; the guards.

**Effect on what can be claimed: neutral to tightened.** No bar moved. One claim (REW-H3) lost its planned
replication site and gained a named substitute plus an explicit failure mode; one class definition that was
ambiguous is now pinned.