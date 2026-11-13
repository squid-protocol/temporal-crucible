# Registration: do three structural instruments say where fixes land, beyond size? (SA3)

**Registered 2026-11-13, ~6:15 PM Eastern, before any tool for it exists and before any predictor named here
has been scored against any outcome defined here.** Owner decisions recorded: the three instruments below; the
high-precision label tiers are the primary outcome.

Written under `docs/STUDY_CHECKLIST.md`; every item is answered in the last section.

## What was already seen when this was written

- **Call-graph in-degree vs LOC on these repos**, cascade label, "replaces size" statistic
  (`docs/mod1_result.md`, `docs/mod1_wide.md`). Instrument A is therefore **exploratory** here.
- **Outcome marginals only** — how many unit files each label tier marks per repo
  (`docs/sa3_marginals.json`), read to size the study. No predictor was involved.
- **Nothing** about keyword families or risk vectors on the 38 drawn repos, under any label. Instruments B and
  C are **confirmatory on the drawn repos**. The eight earlier repos are reported separately as exploratory
  (they carried the earlier keyword and exposure studies).

## The question

For a file at a snapshot: within files of similar size, does a structural measure rank the files that are
later fixed above those that are not? **"Adds to size", not "replaces size".**

## Instruments and predictors, fixed now

File grain. One **primary** predictor per instrument; the secondaries are reported and never promoted.

| instrument | primary | secondary |
|---|---|---|
| **A. Call graph** *(exploratory)* | `in_degree`: resolved call edges landing in the file's functions | out-degree; engine `pagerank_score`; `betweenness_score` |
| **B. Keyword families** | `struct_branch`: the file's branch-keyword count | `state_danger`; `state_pointers + state_memory_alloc`; `def_safety`; `state_flux` |
| **C. Risk vectors** | `risk_safety_score` (0–100, higher = more exposure) | `risk_tech_debt`; `risk_cognitive_load`; `risk_state_flux`; `risk_concurrency` |

B and C are read from the engine's `file_data` at the snapshot, engine version pinned and recorded. The scans
made for MOD-1 kept only files, functions and edges, so each snapshot is rescanned at the **same commit** with
the engine output kept. **Predicted direction for every primary: higher value, more fixes.**

## Outcomes, fixed now

Universe, cut (80th percentile of commits), window (730 days), merge handling, C/C++ units and dating are
MOD-1's as amended (`tools/mod1_lift.py`). A file is positive if a qualifying commit touches it in the window.
**Tree-wide commits** (≥ 10% of unit files and ≥ 20 files) are removed from every outcome, fix or not.

| outcome | a qualifying commit is | role |
|---|---|---|
| **HP** | tier T1 revert, T2 fix-reference or T3 CVE | **primary** |
| HP-revert, HP-fixref, HP-cve | each tier alone | reported, never pooled into a claim |
| KW | tier T4 keyword only | secondary |
| **CHURN** | any other non-bot commit (no tier, or T5 bare reference) | **negative control** |

**Label-depth rule (checklist item 2), to be built before scoring:** in a merge-workflow repo the fix
reference usually sits in a commit the merge brings in, not in the merge. The marginals show it (godot and
kubernetes: zero fix-references). So **a merge inherits the links of the commits it merges**; without that a
merge-workflow repo is not scored on HP.

**What HP is not.** Its precision as "a defect" is unaudited outside the earlier repos, and it is
convention-bound: django writes "Fixed #N" for features, go writes "Fixes #N" for proposals. HP is "a change
the project tied to a revert, an issue or a CVE". The CHURN control and the per-tier rows exist because of
that.

## Statistic

Per repo, per predictor x, per outcome:

1. Put the unit files in LOC bands of equal count — 10 bands if the repo has ≥ 300 unit files, else 5.
2. **sAUC(x)** = concordant (positive, negative) pairs **within bands**, ties at half, over all within-band
   pairs. 0.5 means x says nothing among files of similar size.
3. **effect(x) = sAUC(x) − sAUC(LOC)**. LOC still varies inside a band; subtracting its own within-band
   score removes that residual. 95% CI by bootstrap over files within bands (600 reps).

Across repos: the **mean effect** with a percentile bootstrap over repos (4,000 reps), plus the count of repos
whose own CI lies above, below, and across zero. No pooled number is reported without those counts.

## Hypotheses and reading rules

- **SA3-B:** mean effect of `struct_branch` on HP over the drawn repos is > 0.
- **SA3-C:** mean effect of `risk_safety_score` on HP over the drawn repos is > 0.
- **SA3-A** *(exploratory)*: the same for `in_degree`.

Each is **supported** iff its 95% CI lies wholly above zero, **contradicted** iff wholly below, otherwise
**not detected**. B and C are two confirmatory tests: Holm-corrected, so the first needs a 97.5% CI.

**Specificity gate.** A supported result is called **defect-specific** only if effect(HP) − effect(CHURN)
also has a CI wholly above zero. If not, it is reported as **"tracks activity, not defects"**.

**Validity gate.** A **placebo predictor** (SHA-1 of the file path, read as a number) runs through the same
pipeline with 200 different salts. If the placebo's mean effect on HP is not centred on zero (its own 95%
range across salts excludes zero), **no SA3 result is reported as a finding** until the pipeline is fixed.

**Power, stated before unblinding.** The spread of the 200 placebo means is the null distribution of the
test, measured without touching a real predictor. The smallest detectable mean effect (80% power) is computed
from it and written into an amendment **before any real predictor is scored**. Label noise attenuates
structural effects (`docs/structure_claims_assessment.md`: about 30% survives the keyword label), so a null on
KW rules out little; the HP null is read against the stated number.

## Floors and exclusions, each listed with its own reason

- Scan holds < 90% of the unit files in the git tree at the snapshot → "scan incomplete". Six drawn repos fail
  today; finding and fixing the cause is allowed before scoring because it is read from structure alone.
- Fewer than 30 positives **or** fewer than 30 negatives on an outcome → not scored on that outcome.
  (Marginals today: 16 of 32 scannable drawn repos clear 30 on HP, before merge inheritance.)
- A predictor that is non-zero in < 10% of a repo's unit files → "instrument silent" for that predictor.
- No commit-body harvest; no usable merge inheritance in a merge-workflow repo; failed — each its own row.

## Sensitivities, declared now, reported, not gating

S1 the ten repos whose language was first measured on 2026-11-13 removed · S2 merge-workflow repos removed ·
S3 repos with < 730 days of window removed · S4 the old "replaces size" statistic, AUC(x) − AUC(LOC), for
continuity with MOD-1 · S5 tree-wide commits left in.

## Not in this registration

- **Function grain.** It needs a line-change harvest that exists for eight repos and holds no merges. It is
  registered separately once file grain is read.
- **Age or language as moderators.** MOD-1 did not detect one; none is tested here.
- **Any column of `file_data` not named above.** There are about 150. Looking at the rest is a different,
  explicitly exploratory exercise.

## Checklist answers

1 unit files only · 2 body harvest for every repo plus merge inheritance · 3 merges kept where they are the
unit · 4 completeness ≥ 0.90 from `git ls-tree` · 5 call coverage and per-predictor non-zero share reported
per repo · 6 language from the amended draw, C and C++ together · 7 1st-percentile dating, realised window
recorded · 8 tree-wide commits removed, S5 leaves them in · 9 direction stated, three-way reading · 10 power
from the placebo, written down before unblinding · 11 confirmatory claims on drawn repos only, earlier eight
separate · 12 per-repo intervals and side counts beside every mean · 13 this study is the "adds to size"
test; S4 is the "replaces" one · 14 gates and sensitivities above · 15 independent code review, forbidden to
compute any SA3 outcome association, after the tools are written and before the scorer runs · 16 amendments
dated with what was known · 17 exclusions listed by reason · 18 all changes to shared tools opt-in.

## What a result will and will not license

- B or C supported and defect-specific: "in this pool, among files of similar size, files with more of X are
  more often tied to a revert, issue or CVE in the next two years, by about this much." Not causal, not a
  per-file prediction, not a claim about any one language.
- Supported but not defect-specific: X marks where work happens.
- Not detected: no effect larger than the stated detectable size; nothing about smaller ones.
- The pool is hand-collected, well-known survivors. No claim beyond it.
