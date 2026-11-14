# Registration: do structural instruments say where fixes land, beyond size? (SA3)

**Registered 2026-11-13, 5:06 PM Eastern; pre-implementation design review completed 2026-11-13 before any SA3
tool exists and before any predictor named here has been scored against any outcome defined here.** Owner
decisions recorded: the instruments below; the high-precision label tiers are the primary outcome.

Written under `docs/STUDY_CHECKLIST.md`; every item is answered in the last section.

> **Read Amendment 1 at the end first.** It reconciles two independent reviews and **governs wherever it differs
> from the text below** (the control outcome, the revert tier, merge inheritance, floors, gates, power). The text
> as first registered is commit `3ead6bd`; the second reviewer edited it in place at `7204100`.

## Pre-implementation design review (2026-11-13, before any tool or scoring)

An independent review (Gemini 4 Argon) of the initial draft before code was written identified five design bugs
that would have invalidated the gates or masked real signal. Because zero SA3 tools exist and zero SA3
predictors have been scored, all five are corrected in this registration:

1. **Placebo validity gate & size-subtraction bias (`sAUC(x) − sAUC(LOC)` → `bAUC(x) − 0.5`).** Within 5- or
   10-decile LOC bands (especially the unbounded top decile), `LOC` still predicts fixes (`sAUC(LOC) ≈ 0.55–0.61`
   in `docs/nm_exploratory_size_checks.md`). Under the draft formula `effect(x) = sAUC(x) − sAUC(LOC)`, the
   SHA-1 placebo predictor has `E[sAUC(placebo)] = 0.500`, so `E[effect(placebo)] = 0.500 − sAUC(LOC) < 0`: the
   200-salt placebo distribution is guaranteed to lie below zero and **trip the validity gate automatically**.
   Worse, subtracting `sAUC(LOC)` asks whether `x` *beats residual within-band LOC*, not whether `x` adds to
   LOC: a genuinely size-independent predictor (e.g. `risk_safety_score` or branch density) with true lift
   `sAUC(x) = 0.54` in a repo where `sAUC(LOC) = 0.56` is scored as **`−0.02` ("contradicted")**, while raw
   extensive counts get free credit from correlating with within-band `LOC`. Replaced below with **Size-Balanced
   Caliper Concordance (`bAUC(x) − 0.5`)**, which centres both `LOC` and the SHA-1 placebo at `0.000`
   identically while cancelling linear residual size correlation; `sAUC(x) − sAUC(LOC)` is kept as Sensitivity S6.
2. **Extensive vs. intensive scaling & missing interaction instrument.** `struct_branch` is an extensive count
   that scales with `total_loc`. Meanwhile, the earlier exploratory screen (`docs/nm_exploratory_size_checks.md`)
   found that **`amplified_cascading_flux`** (state writes nested inside control-flow branches, `AMP-H1`) was
   the *only* file metric to survive 10-bin, 50-bin, and density size controls (`+0.105` on nDPI, `+0.113` on
   openssl), and it has **never been examined on the 38 drawn repos**. Instrument D (`amplified_cascading_flux`)
   and branch density (`struct_branch / total_loc`) are added below.
3. **Cascade trailer leakage into `CHURN` & non-GitHub issue trackers.** In `tools/label_cascade.py`,
   `trailer:fixes`, `trailer:bug`, and `trailer:reported-by` were routed into `link["trailer"]` → `T5_bareref`.
   Because SA3 defines `CHURN` as `no tier, or T5 bare reference`, commits carrying explicit `Fixes:` / `Bug:` /
   `Reported-by:` trailers were placed into the **negative control**. Furthermore, `tools/hist_meta.py` matched
   only `#\d+` / `GH-\d+` / `bug \d+` for `issue_fix`, missing Jira (`LANG-1234` in commons-lang, where HP was
   1), Python (`bpo-\d+`), FreeBSD (`PR \d+`), GnuPG (`GnuPG-bug-id`), and kernel/C `Fixes: <sha>` trailers.
   Finally, at file grain over 730 days, almost every `HP`-positive file is also touched by routine commits, so
   an unconditioned `CHURN` outcome overlaps heavily with `HP`. Opt-in fixes (`--sa3-tiers`, `--sa3-links`) and
   an exclusive `CHURN` definition are fixed below.
4. **Root cause of the 6 `scan_incomplete` drawn repos.** Tracing `tools/mod1_lift.py` against
   `tools/laws_build.py` and `gitgalaxy/core/aperture.py` showed three structural mismatches: (a) `mod1_lift.py`
   called `U.Excluder()` without passing the snapshot's `.gitattributes` (`attrs` table in the scan DB);
   (b) `aperture.py` excludes `"tutorials"` / `"tutorial"` (e.g. `root`), foreign-licensed subtrees, and
   `KNOWN_LIBRARY_NAMES` (`zlib`, `sqlite3`, `lz4`, `freetype`), whereas `laws_units.py` omitted `"tutorials"`
   from `EXAMPLE_PARTS`; and (c) `macports-base` (`0 of 128` C files) is a Tcl repo whose C files sit in a
   subpackage. Opt-in unit alignment (`attrs` + `include_tutorials=True`) is added to `tools/laws_units.py`.
5. **Between-repo heterogeneity & stratified bootstrap.** In small-positive repos, unstratified bootstrap over
   files drops entire LOC bands in ~37% of replicates whenever a band has 1 positive. Within-repo bootstrap is
   now stratified by `(band, y)`, and across-repo summaries add $\tau^2$ heterogeneity and `C_family` vs.
   `managed` sub-pool means alongside the grand mean and sign counts.

## What was already seen when this was written

- **Call-graph in-degree vs LOC on these repos**, cascade label, "replaces size" statistic
  (`docs/mod1_result.md`, `docs/mod1_wide.md`). Instrument A is therefore **exploratory** here.
- **Outcome marginals only** — how many unit files each label tier marks per repo
  (`docs/sa3_marginals.json`), read to size the study. No predictor was involved.
- **Nothing** about keyword families, risk vectors, or branch-state interaction (`amplified_cascading_flux`) on
  the 38 drawn repos, under any label. Instruments B, C, and D are **confirmatory on the drawn repos**. The
  eight earlier repos are reported separately as exploratory (they carried the earlier keyword, size-check, and
  exposure studies).

## The question

For a file at a snapshot: within files of similar size, does a structural measure rank the files that are
later fixed above those that are not? **"Adds to size", not "replaces size".**

## Instruments and predictors, fixed now

File grain. One **primary** predictor per instrument; the secondaries (including explicit density ratios
`count / total_loc`) are reported and never promoted.

| instrument | primary | secondary |
|---|---|---|
| **A. Call graph** *(exploratory)* | `in_degree`: resolved call edges landing in the file's functions | `in_degree / total_loc`; out-degree; engine `pagerank_score`; `betweenness_score` |
| **B. Keyword families** *(confirmatory)* | `struct_branch`: the file's branch-keyword count | `struct_branch / total_loc`; `state_danger`; `state_pointers + state_memory_alloc`; `def_safety`; `state_flux` |
| **C. Risk vectors** *(confirmatory)* | `risk_safety_score` (0–100, higher = more exposure) | `risk_tech_debt`; `risk_cognitive_load`; `risk_state_flux`; `risk_concurrency` |
| **D. Branch-state interaction** *(confirmatory)* | `amplified_cascading_flux`: state writes nested inside control-flow branches (`AMP-H1`) | `amplified_cascading_flux / total_loc`; `state_heat_triggers` (`DYN-H1`); `dampened_flux` |

B, C, and D are read from the engine's `file_data` at the snapshot, engine version pinned and recorded. The
scans made for MOD-1 kept only files, functions and edges, so each snapshot is rescanned at the **same commit**
with the engine output kept. **Predicted direction for every primary: higher value, more fixes.**

## Outcomes, fixed now

Universe, cut (80th percentile of commits), window (730 days), merge handling, C/C++ units and dating are
MOD-1's as amended (`tools/mod1_lift.py`), with the snapshot's `.gitattributes` (`attrs`) and tutorial-directory
exclusions applied (`U.Excluder(attrs, include_tutorials=True)`). A file is positive if a qualifying commit
touches it in the window. **Tree-wide commits** (≥ 10% of unit files and ≥ 20 files) are removed from every
outcome, fix or not.

| outcome | a qualifying commit is | role |
|---|---|---|
| **HP** | tier T1 revert, T2 fix-reference (including `Fixes:` / `Bug:` / `Reported-by:` trailers and Jira / `bpo-` / `PR` / `Fixes: <sha>` links via `--sa3-links` and `--sa3-tiers`) or T3 CVE | **primary** |
| HP-revert, HP-fixref, HP-cve | each tier alone | reported, never pooled into a claim |
| KW | tier T4 keyword only (and not touched by HP) | secondary |
| **CHURN** | touched by a non-bot non-fix commit (no tier, or T5 bare reference / `Closes:`) **and not touched by HP or KW** (`CHURN_any` without the exclusion is reported alongside) | **negative control** |

**Label-depth rule (checklist item 2), to be built before scoring:**
1. **Merge inheritance:** in a merge-workflow repo the fix reference usually sits in a commit the merge brings
   in, not in the merge. The marginals show it (godot and kubernetes: zero fix-references). So **a merge
   inherits the links of the commits it merges**; without that a merge-workflow repo is not scored on HP.
2. **Trailer and tracker hygiene (`--sa3-links`, `--sa3-tiers`):** `trailer:fixes`, `trailer:bug`, and
   `trailer:reported-by` are routed to `T2_fixref` rather than `T5_bareref` (preventing real bug trailers from
   landing in `CHURN`), while `trailer:closes` remains `T5_bareref`. `issue_fix` matches fix verbs before
   GitHub `#123`/`GH-123`, Jira `[A-Z][A-Z0-9]+-\d+`, Python `bpo-\d+`, BSD `PR \d+`, `GnuPG-bug-id`, and
   `Fixes: <sha>`.

**What HP is not.** Its precision as "a defect" is unaudited outside the earlier repos, and it is
convention-bound: django writes "Fixed #N" for features, go writes "Fixes #N" for proposals. HP is "a change
the project tied to a revert, an issue or a CVE". The CHURN control and the per-tier rows exist because of
that.

## Statistic

Per repo, per predictor $x$, per outcome:

1. **Bands and caliper.** Put the unit files in equal-count `LOC` bands — 10 bands if the repo has ≥ 300 unit
   files, else 5. A `(positive, negative)` file pair $(i, j)$ in the same band is **eligible** iff it also
   satisfies the relative size caliper $\frac{1}{1.5} \le \frac{\text{LOC}_i}{\text{LOC}_j} \le 1.5$ (so the
   unbounded top decile cannot pair a 15,000-LOC monolith with a 500-LOC file).
2. **Size-Balanced Caliper Concordance (`bAUC(x)`).** Partition eligible within-band, within-caliper
   `(positive, negative)` pairs into $S_> = \{\text{LOC}_+ > \text{LOC}_-\}$,
   $S_< = \{\text{LOC}_+ < \text{LOC}_-\}$, and $S_= = \{\text{LOC}_+ = \text{LOC}_-\}$ (with share
   $w_= = |S_=| / |S_{\text{elig}}|$). Score concordance $\text{conc}(x \mid S)$ (ties at $\frac{1}{2}$) on
   each subset and weight $S_>$ and $S_<$ equally:
   $$\text{bAUC}(x) = (1 - w_=)\left(\frac{1}{2}\,\text{conc}(x \mid S_>) + \frac{1}{2}\,\text{conc}(x \mid S_<)\right) + w_=\,\text{conc}(x \mid S_=)$$
   *(If either $S_>$ or $S_<$ is empty in a tiny sample, only $S_=$ contributes or the repo is flagged.)*
3. **Effect and within-repo CI.**
   $$\text{effect}(x) = \text{bAUC}(x) - 0.5$$
   By construction: (a) $\text{effect}(\text{LOC}) \equiv 0$ identically; (b) for any random placebo $P$,
   $\mathbb{E}[\text{effect}(P)] \equiv 0$ identically; (c) linear residual size correlation $+\delta$ on $S_>$
   cancels $-\delta$ on $S_<$; and (d) size-independent predictors with true lift $+\gamma$ retain $+\gamma$
   without being penalized by $-(\text{sAUC}(\text{LOC}) - 0.5)$.
   The 95% CI is computed by **stratified bootstrap over files within `(band, outcome)` strata** (600 reps),
   preventing low-positive bands from randomly dropping out.

Across repos:
- the **mean effect** with a percentile bootstrap over repos (4,000 reps);
- the **count of repos** whose own 95% CI lies wholly above, wholly below, and across zero (plus a two-sided
  sign test on positive vs. negative point estimates);
- between-repo heterogeneity **$\tau^2$** (DerSimonian–Laird) and separate sub-pool means for **`C_family`**
  (`c, cpp, zig, fortran`) and **`managed`** languages, so opposite-sign cancellation across language families
  cannot hide behind a grand mean of zero.
No pooled number is reported without the per-repo CI counts and sub-pool split.

## Hypotheses and reading rules

- **SA3-B (confirmatory):** mean effect of `struct_branch` on HP over the drawn repos is > 0.
- **SA3-C (confirmatory):** mean effect of `risk_safety_score` on HP over the drawn repos is > 0.
- **SA3-D (confirmatory):** mean effect of `amplified_cascading_flux` on HP over the drawn repos is > 0.
- **SA3-A** *(exploratory)*: the same for `in_degree`.

Each is **supported** iff its Holm-adjusted CI lies wholly above zero, **contradicted** iff wholly below,
otherwise **not detected**. B, C, and D form a three-test confirmatory family under Holm–Bonferroni correction
($\alpha = 0.05$: smallest $p$ / widest CI tested at $98.33\%$, second at $97.5\%$, third at $95\%$).

**Specificity gate.** A supported result is called **defect-specific** only if $\text{effect}(\text{HP}) -
\text{effect}(\text{CHURN})$ also has a 95% CI wholly above zero (and passes under `CHURN_any` or conditional on
total commit touches). If not, it is reported as **"tracks activity, not defects"**.

**Validity gate.** A **placebo predictor** (SHA-1 of the file path + salt, read as a uniform number) runs
through the identical `bAUC(x) − 0.5` pipeline with 200 different salts. If the placebo's mean effect on HP is
not centred on zero (its 95% range across salts excludes zero, or its mean shifts by $> 0.002$), **no SA3
result is reported as a finding** until the pipeline is fixed.

**Power, stated before unblinding.** The spread of the 200 placebo means is the exact null distribution of the
test, measured without touching a real predictor. The smallest detectable mean effect ($2.8 \times \text{SD}$
for 80% power at two-sided $\alpha = 0.05$, and $3.2 \times \text{SD}$ at Holm $\alpha/3$) is computed from it
and written into an amendment **before any real predictor is scored**. Label noise attenuates structural
effects (`docs/structure_claims_assessment.md`: about 30% survives the keyword label), so a null on KW rules
out little; the HP null is read against the stated number.

## Floors and exclusions, each listed with its own reason

- Scan holds < 90% of the unit files in the git tree at the snapshot (under `U.Excluder(attrs,
  include_tutorials=True)`) → "scan incomplete". Finding and fixing remaining scanner/excluder mismatches (such
  as foreign-licensed subtrees or `KNOWN_LIBRARY_NAMES` in `aperture.py`) is allowed before scoring because it
  is read from structure alone.
- Fewer than 30 positives **or** fewer than 30 negatives on an outcome → not scored on that outcome.
  (Marginals before merge inheritance and `--sa3-links` / `--sa3-tiers`: 16 of 32 scannable drawn repos clear
  30 on HP; updated marginals after those two structural label fixes are recorded before any predictor is read.)
- Fewer than 100 eligible within-band, within-caliper pairs ($|S_>| < 25$ or $|S_<| < 25$) → "under pair floor".
- A predictor that is non-zero in < 10% of a repo's unit files → "instrument silent" for that predictor.
- No commit-body harvest; no usable merge inheritance in a merge-workflow repo; failed — each its own row.

## Sensitivities, declared now, reported, not gating

S1 the ten repos whose language was first measured on 2026-11-13 removed · S2 merge-workflow repos removed ·
S3 repos with < 730 days of window removed · S4 the old "replaces size" statistic, $\text{AUC}(x) -
\text{AUC}(\text{LOC})$, for continuity with MOD-1 · S5 tree-wide commits left in · S6 the uncalibrated
band-subtraction statistic $\text{sAUC}(x) - \text{sAUC}(\text{LOC})$ without caliper · S7 tighter relative
caliper ($\le 1.25\times$) and 20 LOC bands on repos with $\ge 600$ unit files.

## Not in this registration

- **Function grain.** It needs a line-change harvest that exists for eight repos and holds no merges. It is
  registered separately once file grain is read.
- **Age or language as formal moderator tests.** MOD-1 did not detect one globally; `C_family` vs. `managed`
  sub-pools are reported descriptively beside every pooled number so sign inversions are visible, not hidden.
- **Any column of `file_data` not named above.** There are about 150. Looking at the rest is a different,
  explicitly exploratory exercise.

## Checklist answers

1 unit files only (with `.gitattributes` `attrs` and `include_tutorials=True`) · 2 body harvest for every repo
plus merge inheritance, `--sa3-links`, and `--sa3-tiers` · 3 merges kept where they are the unit · 4
completeness ≥ 0.90 from `git ls-tree` · 5 call coverage and per-predictor non-zero share reported per repo ·
6 language from the amended draw, C and C++ together · 7 1st-percentile dating, realised window recorded · 8
tree-wide commits removed, S5 leaves them in · 9 direction stated, three-way reading, Holm across B/C/D · 10
power from the 200-salt `bAUC` placebo, written down before unblinding · 11 confirmatory claims on drawn repos
only, earlier eight separate · 12 per-repo intervals, side counts, $\tau^2$, and `C_family`/`managed` sub-pools
beside every mean · 13 this study is the "adds to size" test (`bAUC(x) − 0.5`); S4 is "replaces size"; S6 is
`sAUC(x) − sAUC(LOC)` · 14 gates and sensitivities above · 15 independent code review, forbidden to compute any
SA3 outcome association, after the tools are written and before the scorer runs · 16 amendments dated with what
was known · 17 exclusions listed by reason · 18 all changes to shared tools opt-in.

## What a result will and will not license

- B, C, or D supported and defect-specific: "in this pool, among files of closely matched size, files with more
  of X are more often tied to a revert, issue or CVE in the next two years, by about this much." Not causal,
  not a per-file prediction, not a claim about any one language unless the sub-pool intervals agree.
- Supported but not defect-specific: X marks where maintenance activity happens, not specifically defects.
- Opposite-sign sub-pools (`C_family` vs `managed` CIs on opposite sides of zero): a single global weight for X
  is invalid; direction is regime-dependent.
- Not detected: no effect larger than the stated detectable size; nothing about smaller ones.
- The pool is hand-collected, well-known survivors. No claim beyond it.

## Amendment 1 — 2026-11-13, 6:00 PM Eastern: two independent reviews reconciled, before any tool exists

**State when written:** no SA3 tool exists; no SA3 predictor has been put against any outcome on any repo.
Two reviewers worked independently on the text of `3ead6bd`:

- **Reviewer 1** (a separate Claude session, read-only, forbidden to compute any predictor–outcome
  association): a report with five blockers, backed by simulations on synthetic data and by outcome marginals
  and path-hash placebos on the study repos.
- **Reviewer 2** (Gemini 4 Argon, PR #183): edited the registration in place (`7204100`), added Instrument D,
  and added opt-in label and unit switches to the tools.

**Where they agree, independently:** the registered statistic `sAUC(x) − sAUC(LOC)` is biased negative for any
predictor not perfectly rank-tied to LOC inside a band, so the placebo gate would have failed on a correct
pipeline and a real size-independent effect would have read "contradicted"; and `Fixes:` trailers were sitting
in the negative control. Both are fixed in the text above.

**Where they differ or one saw what the other did not, the rule below governs.** Three were settled by a
synthetic simulation run for this amendment (`recon_sim.py`; 16 repos with the real size and positive-count
mix; no real predictor involved).

### 1. Statistic — both proposals are valid; one is primary, the other must agree

| predictor with no real effect | residualised rank (reviewer 1) | caliper bAUC (reviewer 2) |
|---|---|---|
| noise | +0.000, supported 5% | +0.000, supported 4% |
| noisy copy of size | +0.000, 3% | +0.002, 1% |
| count | +0.001, 1% | +0.002, 5% |
| sparse count | −0.003, 0% | +0.002, 3% |
| 0–100 score, zero in small files | −0.002, 3% | −0.001, 3% |

With a real effect both detect a count and a score about equally (modest effect: 99% / 86% against
96% / 89%). **Primary: `bAUC(x) − 0.5` as written above.** **Co-reported, with a reading rule:** the
residualised statistic — bands as above; within a band u = average rank of x ÷ band size, fitted on ln(LOC)
by least squares, r = the residual (r = u − mean u if x or LOC is constant in the band);
effect = sAUC(r) − 0.5. If the two give different readings for a hypothesis, it is reported as **"not robust
to the statistic"**, never as supported. A third, reported only: logistic y ~ band dummies + ln LOC +
standardised x (log1p for counts).

### 2. Negative control — the exclusive CHURN in the text above is withdrawn as the gate

The text defines CHURN as files touched by non-fix commits **and not touched by HP or KW**. That conditions the
control on the outcome: the busiest files are HP-positive and so become CHURN-negative. Simulated with a
predictor that tracks only how busy a file is, where fixes are a constant share of all commits:

| control | mean of effect(HP) − effect(control) | read "defect-specific" |
|---|---|---|
| CHURN_any (touched by any non-fix commit) | −0.015 | 0% of studies |
| **exclusive CHURN (text above)** | **+0.084** | **100% of studies** |
| matched control (below) | +0.003 | 10% of studies (40 simulated; nominal 2.5%) |

**The gate uses the matched control:** per repo, K commits drawn at random from non-bot commits in the window
that are in no fix tier, not tree-wide, and carry no `Fixes:`/`Bug:` trailer, with K = the number of HP commits
(if the pool is smaller, HP is subsampled to the pool size); a file is control-positive if a drawn commit
touches it; 200 draws, seed 2982; the control effect is the mean over draws. **Specificity = the mean over
repos of the paired difference effect(HP) − effect(control), t-interval over repos, on repos scored on both.**
`CHURN_any` is reported beside it. The exclusive CHURN is not computed.

### 3. Reverts — only a revert of code that existed at the snapshot is a primary positive

Reviewer 1: of in-window reverts whose target resolves, 187 of 201 (93%) undo a commit made **after** the
snapshot; the snapshot's code had no defect in those cases, and reverts supply most HP positives in 7 of the
16 floor-clearing repos. **T1 counts toward HP only when it names a sha that resolves to a commit at or before
the cut.** Sha-less and unresolvable reverts are not HP. `HP-allreverts` (every revert, as first registered)
is reported as a secondary; a hypothesis supported only there reads **"tracks reverted changes, not fixes"**.
*Owner confirmed this rule, and Instrument D as a third confirmatory test, on 2026-11-13 (~6:02 PM Eastern),
before any tool existed.*

### 4. Merge inheritance, pinned

- brought(M) = commits reachable from parents 2..k of M and not from parent 1; each off-chain commit belongs
  to the earliest first-parent merge that reaches it; octopus merges use all non-first parents.
- **No inheritance when brought(M) > 50 commits** (upstream imports; circuitpython has one of 1,185). Such
  merges are listed.
- Inherited kinds: revert (under rule 3, and never when the target is itself in brought(M)), fix-reference,
  CVE. **The keyword tier does not inherit.** Bot-authored brought-in commits are ignored.
- Positive files = the merge's first-parent diff ∩ the files the linking commit touched — the same depth as a
  non-merge repo, where only the linked commit's files are positive.
- Windowing uses the merge's time; the tree-wide rule applies to the merge's diff.
- Squash and fast-forward commits on the chain are labelled by their own message only.
- "Merge-workflow" (S2, exclusions) is the history's unit; the in-window merge share is reported per repo.

### 5. Gates — two more placebos and a hard assertion

The path hash is independent of file type, commit and directory, so it cannot see a universe mismatch or
directory clustering. Added, all run before any real predictor is read:

- **Block-permutation placebo:** the real predictor's values permuted within blocks of 4 LOC-adjacent unit
  files (keeps its zeros, ties and size relation). Only permuted values are ever scored at this stage.
- **Directory-hash placebo:** SHA-1 of the file's directory + salt.
- **Assertion:** the scorer aborts if any ranked file is not a unit file.

Validity requires the path-hash and block-permutation means to be centred on zero. Per-repo "above / below /
across zero" counts are taken from the block-permutation null, not from a file bootstrap (reviewer 1: 30
positive files in scapy come from 18 commits; a file bootstrap treats them as independent).

### 6. Floors

A repo is scored on an outcome only with **≥ 30 positive files from ≥ 20 qualifying commits, no single commit
supplying > 25% of the positives**, ≥ 30 negatives, and the pair floor above.

### 7. Power, and what a null on HP means

The detectable mean effect is stated from **both** the path-hash and the directory-hash spread (reviewer 1,
current tools: 0.0091 and 0.0179 across salts, i.e. roughly 0.028 and 0.055 at 80% power on the Holm-first
interval), and for a between-repo SD of true effects of 0, 0.02 and 0.04. With three confirmatory tests the
Holm-first interval is 98.33%. HP is not exempt from attenuation: its recall is low, so real fixes sit among
its negatives. A null is read against the larger number.

### 8. Estimand and intervals

The **unweighted mean over repos** is the primary ("a typical repo"), with a **t-interval over repos** (a
percentile bootstrap under-covers at ~16 repos). Reported beside it: the precision-weighted random-effects
mean, τ², and the result with **go and django removed** (they hold 52% of HP-positive files, and django's fix
references cover most of its ordinary work). No file-pooled number, ever. The `C_family` / `managed` sub-pools
are descriptive and are not fitted with fewer than five repos; on today's marginals C_family is godot and
freebsd-src, so **SA3 makes no claim about C**.

### 9. Instruments

- **D stays, as reviewer 2 added it** — a fourth instrument beyond the owner's three, and a third confirmatory
  test. `amplified_cascading_flux` is **not a `file_data` column**: it is read from the engine's
  `mitigation_telemetry` JSON, key `amplified_cascading_flux`, per file. Its prior evidence is C-only (nDPI,
  openssl; not curl) on security-fix outcomes, and SA3's scored set is mostly not C.
- **C, `risk_safety_score`:** it is exactly 0 when a file has no "attack" keyword and near 50 otherwise, and
  its inputs are near-absent in Python, Java and C#. Two decomposition secondaries are declared (zero vs
  non-zero; the score among non-zero files), and the per-repo non-zero share of each input is reported.
  "Instrument silent" becomes: non-zero in < 10% of unit files **or** fewer than 20 distinct values.
- **Why these primaries:** `safety_score` passed one earlier test on curl and failed on nDPI; `struct_branch`
  comes from curl's fix-grammar result; "structure adds over size" failed on curl. Different questions, on
  repos outside the draw — so the drawn-repo test is unbiased, and the prior is weak.
- SA3-A is exploratory and is never described as "supported"; only "positive / negative / not detected".

### 10. Smaller rules

- Per-tier rows use the cascade's exclusive tier, in its order: revert, CVE, fix-reference.
- **One engine SHA for all 46 rescans**, named in the scorer's output; completeness is recomputed on the
  rescans; a NULL predictor value drops that file for that predictor and is counted.
- The eight earlier repos were scanned 4.6 to 42 days after their cut: their window starts at the snapshot.
- Added sensitivities: **S8** positives followed through renames by the history's lineage id, files deleted
  inside the window flagged · **S9** the logistic model of rule 1.

### 11. Corrections to the record

- `docs/sa3_marginals.json` "other" counts commits with no tier only; the control pool also includes bare
  references (kubernetes: 0 in the JSON, 2,646 files under the earlier CHURN definition). No predictor was
  involved; nothing is compromised.
- "Nothing … on the 38" has one exception: **micropython** was in the engine's outcome-label pilot (#2720),
  where a keyword signal was put against later fixes. It has 11 HP positives and will not be scored on HP.
- Checklist answers 2, 4, 5, 10, 12 and 13 in the text above were labels rather than answers; rules 1–8 here
  are the answers.

### Order of work

1. Merge inheritance and the revert-target resolver in the body harvest. 2. Rescan the 46 snapshots at one
engine SHA with full output kept; recompute completeness. 3. Outcome marginals under the final rules, floors
applied, list frozen. 4. Scorer with the three placebos and the assertion; power amendment. 5. Independent
code review. 6. Score.

*Timestamp correction (2026-11-13, 6:10 PM Eastern): the clock times first written in this file and in
`docs/moderator_registration.md` were estimates and ran up to two hours ahead. They now match the commit times
(`git log`), which are the authoritative record of what was written before what.*

## Amendment 2 — 2026-11-13, 6:24 PM Eastern: nesting depth added as an exploratory secondary, before any scorer exists

**State when written:** rescans and the outcome builder exist; no scorer exists; no SA3 predictor has been put
against any outcome. Owner decision.

The engine has no nesting measure (its `complexity` column equals the branch-keyword count), so Instrument B
cannot tell flat branching from deep branching. Added under **Instrument B, as exploratory secondaries only**
(no confirmatory claim, no change to the Holm family, never promoted):

- `nest_max` — the deepest control-flow node in the file; `nest_mean` — the mean depth over its control nodes.
- Measured by tree-sitter on the snapshot's source (`tools/sa3_nesting.py`). A control node is a conditional,
  a loop, a multi-way branch (the statement, not its arms) or a try block; **the node kinds per language are
  the `CONTROL` table in that file at this commit, with `tree_sitter_language_pack` 1.20.0**, and are part of
  this registration. Depth = 1 + the number of control nodes among a node's ancestors.
- Validated on structure only: a self-test of hand-written code with a known depth passes in all 17 grammars.
- **Not measured:** Racket (S-expressions have no control node kinds). Ruby blocks (`each do … end`) are not
  counted as loops, so Ruby depth is understated. A file with a parse error is kept and counted.
- Predicted direction: deeper, more fixes. Same bands, statistics, placebos and control as every other
  predictor. Depth rises with size, so only the within-band result is reported as a result.

The change study (SA3-CH) does **not** get a nesting change: on curl, among 375 edited functions with an
identical keyword set, nesting changed in 1.3% and order in 0%.

## Amendment 3 — 2026-11-13, 9:15 PM Eastern: four tool defects found by the second reviewer, fixed before any scorer exists

**State when written:** rescans done; outcome builder and nesting tool exist; no scorer; no SA3 predictor has
been put against any outcome. The second reviewer (Gemini 4 Argon, PR #183) read the three new tools against
this registration and reported four defects. Each was reproduced before being fixed.

1. **Merge inheritance walked through bot commits.** The chain handed to the "what does this merge bring in"
   search left out bot-authored commits, so a merge branched from one could claim the trunk behind it. The
   chain is now every commit of the walk, in walk order.
2. **The control pool could hold fixes.** A merge over the 50-commit cap, a merge bringing in a linked commit
   with no shared file, or a merge bringing in a commit worded as a fix was in neither HP nor KW and so fell
   into the matched control's pool. Such merges are now **tainted: in no outcome and in no control.** The
   per-tier rows now take the cascade's exclusive tier per commit, after uniting the kinds of all its events.
3. **Nesting depth (Amendment 2) counted an `else if` chain as depth N in C-family grammars and depth 1 in
   Python, Ruby, Fortran and MATLAB.** Rule added to Amendment 2's definition: **an `if` hanging directly off
   the else of an enclosing `if` sits at that `if`'s depth**; an `if` inside a braced else block is still
   nesting. The self-test now checks a four-link chain in 17 grammars and a braced else in 10.
4. **Completeness was measured against the wrong denominator.** The scan reads a `git archive`, which honours
   `export-ignore`; the denominator was the raw tree. It is now the archive's file list. A body harvest is
   reused only if it records both the merges and the wider-tracker switches.

## Amendment 4 — 2026-11-14, 9:06 AM Eastern: the point estimates were partly seen before scoring; what is frozen, what is replaced

**This amendment is a disclosure first.** SA3 has not been scored. But while diagnosing a failed gate I printed
numbers from which the confirmatory point estimates can be recovered, and the study must say so.

### What happened

1. The `placebo` stage ran (commit `5ffa330`). The block-permutation placebo of Amendment 1 rule 5 came out
   at about +0.015 for three of the four primaries; the gate failed.
2. To find out why, I ran three diagnostics on shuffled values (`tools/exploratory/sa3_placebo_diag{1,2,3}.py`).
   The second printed, per primary, the study mean under a random permutation in blocks of four and under a
   cyclic shift in the same blocks.
3. A third independent review (a fresh Claude session, read-only, working on synthetic data) showed that those
   two numbers determine the real study-mean effect: **real ≈ 4 × permutation − 3 × shift**, because a random
   permutation of four leaves each file its own value one time in four. It verified the identity on synthetic
   data in four scenarios and on real outcomes with non-structural file attributes, and put the precision at
   about **±0.005 to ±0.01**.

**So the point estimates of SA3-B, SA3-C, SA3-D and SA3-A on the primary outcome are no longer blind.** I have
not done the arithmetic and neither reviewer tabulated it, but the inputs were on my screen and are in this
session's record. From what was already published in `docs/sa3_build_status.md`, the three count primaries are
bracketed at roughly 0.00 to +0.04 — at or below what the study can detect.

### What that does to the claims

- The three confirmatory tests are reported as **"pre-registered; point estimates partly seen before
  scoring"**, and only if everything below under "frozen" runs exactly as it stood at commit `edc5c53`, the
  last commit before the placebo stage ran.
- **Anything changed after `5ffa330` that could move a result is a post-unblinding sensitivity**, labelled
  `PU_` in the scorer's output, never the confirmatory result. That includes the reviewer's own
  suggestions on data faults (below).

### Frozen, exactly as at `edc5c53`

The statistic (`bAUC − 0.5`, bands, the 1.5 caliper), the co-reported residualised statistic and the "must
agree" rule, the outcome definitions, the repo list (15 drawn, 5 earlier), the floors, the Holm family
(B, C, D) and its levels, the reading words, the matched control and its 200 draws, the seeds.

### Replaced: the block-permutation gate is withdrawn

It was never simulated before it became a gate, and it is not a valid one. Every draw keeps the same blocks,
so a chance alignment between block values and block outcomes never averages out; the reviewer's synthetic
null shows the registered criterion **passes only 29% of studies with no effect at all**, and almost never
when the hypothesis is true. The block permutation stays only as the per-repo reference distribution for the
side counts, where a non-zero mean does no harm.

**New gate: a size surrogate.** Per repo and primary, a few parameters are fitted on **predictor versus LOC
only** — the chance the value is non-zero as a logistic in ln LOC and its square, and among non-zeros a
quadratic for ln x with a residual spread in three size thirds (for the risk score, its non-zero quantiles).
200 made-up predictors are drawn from that fit. Each knows a file's LOC and nothing else about it, so it
cannot carry a real effect (synthetic: its mean is +0.001 to +0.002 whether the planted effect is 0, 0.03 or
0.08). **The gate passes if every surrogate mean, and both hash-placebo means, lie within 0.005 of zero.**

Run today (`docs/sa3_placebo.json`), study mean over the 15 drawn repos:

| placebo | mean | Monte Carlo SE | |
|---|---|---|---|
| path hash | +0.0003 | 0.0006 | within tolerance |
| directory hash | +0.0005 | 0.0011 | within tolerance |
| size surrogate of `in_degree` | +0.0011 | 0.0007 | within tolerance |
| size surrogate of `struct_branch` | +0.0025 | 0.0007 | within tolerance |
| size surrogate of `risk_safety_score` | −0.0006 | 0.0008 | within tolerance |
| size surrogate of `amplified_cascading_flux` | +0.0014 | 0.0007 | within tolerance |

**The gate passes.** The surrogate means are also the measured size leak of the statistic for each shape
(the registration's claim that a size proxy scores exactly zero was wrong by this much). Each primary is
therefore reported twice: as registered, and as **effect − its surrogate mean**, beside it.

### Scorer faults fixed — none depends on an outcome

| fault | fix |
|---|---|
| The control filled a missing value with zero; the main path dropped the file | the control uses the same rows |
| "Fewer than 20 distinct values" silenced the yes/no indicator and nesting depth everywhere | the clause applies to continuous scores only |
| The lock was three file names anyone could create | `lock` seals the git hash of the scorer, statistics, outcome builder, this registration, the placebo output, the power statement and the code review; `score` recomputes them |
| Registered but not coded: `CHURN_any`, random-effects mean and τ, sign test, side counts from the block null, the "tracks reverted changes" reading, a summary of the logistic sensitivity, the engine SHA, sub-pools only at five repos | coded |
| Earlier eight: "the window starts at the snapshot" was not applied | applied; no repo's floor status changed (curl 264 → 263 files, postgres 382 → 381, prometheus 51 → 49) |

**Not run, and reported as not run:** S5 (tree-wide commits left in) and S8 (positives followed through
renames). `dampened_flux`, named as a D secondary, does not exist in the pinned engine's output.

### Data faults the review found — post-unblinding sensitivities only

- **mediawiki:** its merges are authored by an account the bot rule matches, so about 80% of its mainline
  units are in no outcome and no control.
- **freebsd-src:** half its unit files are imported third-party code (`contrib/`, `crypto/`).
- **django and circuitpython:** in django a third of the HP commits are features with a ticket; in
  circuitpython eight merges supply 233 of 393 positive files and at least four are not fixes.
- Sampled label precision, 48 HP commits read at diff level: 35 clear fixes, 4 plausible, 8 not, 1 unclear.

None of these is fixed in the confirmatory run. Two extra cuts are reported and labelled:
`PU_django_circuitpython_removed` and `PU_mediawiki_freebsd_removed`.

### Power, restated

The earlier figure (0.032) assumed repos do not differ in their true effect. With a between-repo spread of
0.05 the detectable mean effect is **0.056**; with 0.08 it is **0.080**; and a predictor that clusters by
directory roughly doubles the null spread (0.056 to 0.092). **A "not detected" here rules out mean effects
above about 0.05 to 0.08, and nothing smaller.** `docs/sa3_power.md`.

### The text in force

Four amendments and about 25 rules now sit on top of a body that was itself rewritten in place.
`docs/sa3_registration_consolidated.md` restates everything in force in one place, with the code line for
each rule. It adds nothing; where it and this file disagree, this file and its amendments govern and the
consolidated text is wrong.

## Amendment 5 — 2026-11-14, 5:05 PM Eastern: what is frozen is the code at `8fb7fe0`; the confirmatory run is that code, run once inside an outside seal, with every correction printed beside it

**SA3 is still unscored.** This amendment was drafted, reviewed twice by independent sessions of different
models (`docs/process/reviews/sa3_amendment5_review_claude.md`, `docs/process/reviews/sa3_amendment5_review_gemini.md`),
revised twice, and accepted by the owner. It follows the first run of SA3's unmodified pipeline on generated
repositories with a known answer (`docs/process/harness_report.md`), which found the faults of defect-log
entries 54 to 62.

**It corrects Amendment 4 in one respect:** Amendment 4's phrase "exactly as at `edc5c53`" did not describe
the code Amendment 4 itself committed. Section 1 below is that disclosure. Everything else in Amendment 4
stands.

### 1. What has already changed since the estimates were seen — a disclosure

Amendment 4 says the confirmatory tests keep the label "pre-registered; point estimates partly seen before
scoring" only if the frozen items run "exactly as at `edc5c53`". **That is not true of the code today, and was
not true from the moment Amendment 4 was committed.** Its own commit, `8fb7fe0`, made after the leak, changed
the scorer (222 lines) and the outcome builder (8 lines). Amendment 4 listed those changes under "scorer faults
fixed — none depends on an outcome". Two matter here:

- **The "instrument silent" rule was narrowed** so that count predictors are exempt from the "fewer than 20
  distinct values" clause. Defect log 46 records that this un-silenced three count measures in 14 repo cells.
  Two of the three confirmatory primaries are counts. And the scorer draws from **one** random stream across
  all repos, outcomes and predictors, so **any** un-silenced cell — confirmatory or not, primary outcome or
  keyword — moves the draws of every later repo's matched control, which decides between "supported,
  defect-specific" and "supported, but tracks activity". **All 14 cells are published before scoring**
  (repo, outcome, measure), from the scans alone.
- **The window start** became the later of the cut and the scanned snapshot. Amendment 4 reported the effect on
  the earlier eight repos. That it moves **none of the 15 drawn repos** is verified before scoring from the
  scans and the frame, not assumed.

So the reference for "as frozen" is **the file contents at `8fb7fe0`** for `tools/sa3_score.py` and
`tools/sa3_outcomes.py`, and at `edc5c53` for `tools/sa3_stats.py` and `tools/mod1_lift.py`. None of these
files, nor `hist_meta.py`, `laws_units.py`, `laws_history.py` or `hist_fixlabel.py`, has changed since
`8fb7fe0` (checked with `git log 8fb7fe0..HEAD` on the day of this amendment).

### 2. The rule this amendment applies

**The confirmatory run is the reference code, run once, with its scoring logic unchanged.** Not a rewrite, not
the stored tables. Every correction and every new rule runs **beside** it and is printed beside it. Where a
correction changes a reading, both readings are printed, and a hypothesis whose reading differs between the
two is not called confirmatory.

**The run is sealed from outside.** The reference scorer's own seal covers nine files, omits every data input
and most rule code, and does not notice when git fails (defect log 44, 57). Fixing it would mean editing the
reference. Instead:

1. The run happens in a sandbox of the kind `tools/harness/sandbox.py` builds: the root read-only, **only the
   declared inputs bound in**, read-only, and one new output directory.
2. An external seal lists the SHA-256 of every declared input — every scan, history and harvest database,
   outcome and nesting file, GitHub's two lists; every code file the run loads, including the reference
   scripts and the modules they import; this amendment; the registration — with interpreter and package
   versions. The owner's job recomputes the seal and stops on any difference.
3. The reference scorer's own `lock` is still run, as it is, inside that sandbox.

**Order of operations**, because the reference `lock` hashes the consolidated text and requires a committed
code review: (a) this amendment is accepted and entered in `docs/sa3_registration.md`; (b) the consolidated
text is regenerated from it; (c) the code review document is committed; (d) the counts of section 7 are
published; (e) the checks of section 9 pass on control repositories; (f) the external seal is written;
(g) the owner runs `lock`, then `score`, once.

### 3. The confirmatory run

| item | what it does |
|---|---|
| Code | the reference contents of section 1, inside the external seal |
| Universe | the registered rule as coded, including GitHub's vendored list |
| Completeness | the registered measure decides exclusion, as now |
| Matching later commits to files | equal path |
| Missing predictor values | as the code reads them |
| Snapshot and window | the scanned snapshot; the window from the code's own cut |
| Fix references | exactly as coded (section 5) |
| Tainted merges | counted when they inherit; owner ruling of 2026-11-14 |
| Keyword rules | two, as coded; owner ruling |
| List of scored repos | the frozen list |
| Random draws | seed 2982, the shared stream and the repo order of the reference code |
| Nesting inputs | the existing nesting files, sealed as they are |
| Holm step and "not robust" | as coded in the reference (section 4) |

### 4. Corrections, each printed beside the coded reading — four of them

| defect | the correction | where it shows |
|---|---|---|
| 42 | Holm step-down: a primary whose interval lies wholly below zero does not stop the step-down for the others | both readings printed for B, C and D |
| 43 | "Not robust to the statistic" whenever the two statistics differ | both readings printed |
| 47 | "Supported" is printed only for the three confirmatory tests | output wording; numbers unchanged |
| 48 | The all-reverts comparison uses one named repo set on both sides | printed as coded and as corrected |

**How often 42 matters, computed by the author and equal to the first reviewer's figure.** Give each of the
three tests, in the order the code takes them, one of three readings for the primary statistic and one of
three for the co-reported one: 729 combinations. The coded and corrected rules give a different reading in
135. The corrected rule reads "supported" more often in 51. Every one of them has a contradicted primary
ahead of a supported one; there are five such patterns among the 27 for the primary statistic.

Where the two rules differ for a hypothesis, it is reported as "reading depends on a rule corrected after the
estimates were partly seen". The registration gives the Holm levels and no stopping rule; this is a correction
of a rule the registration left open.

### 5. What the code counts as a fix reference — the patterns govern

The reference file `tools/hist_meta.py` holds these patterns, reproduced verbatim. **Where the prose below and
a pattern differ, the pattern is what runs.**

```
revert_sha     This reverts commit ([0-9a-f]{7,40})                                   (case-insensitive)
issue_fix_sa3  \b(?:fix(?:es|ed)?|resolve[sd]?)\s+(?:#|\bGH-|\bbug\s*#?|\bbpo-|\bPR\s*#?)(\d{1,7})\b
             | \b(?:fix(?:es|ed)?|resolve[sd]?)\s*:?\s+([A-Z][A-Z0-9_]{1,15}-\d{1,7})\b
             | ^GnuPG-bug-id:\s*(\d+)\b
             | ^Fixes:\s*([0-9a-f]{7,40})\b                                 (case-insensitive, multi-line)
cve            \bCVE-\d{4}-\d{4,7}\b                                                  (case-insensitive)
trailer        ^(Co-authored-by|Reported-by|Reviewed-by|Signed-off-by|Tested-by|Closes|Fixes|Bug):\s*(.+)$
                                                                            (case-insensitive, multi-line)
```

In words, with the points a reader would not guess:

- The fix words are exactly fix, fixes, fixed, resolve, resolves, resolved. Not "closes".
- After a fix word and white space: `#N`, `GH-N`, `bug N` or `bug #N`, `bpo-N`, `PR N` or `PR #N` (the BSD
  problem report), N of 1 to 7 digits. No colon is allowed here.
- After a fix word, an optional colon and white space: a tracker key — one letter, then 1 to 15 letters,
  digits or underscores, a hyphen, 1 to 7 digits. **Case is ignored**, so "Fix UTF-8 decoding" and
  "fix x86-64 build" are fix references (defect log 61). It stays in the confirmatory run; a sensitivity
  removes it.
- The patterns above are applied to the subject and body together. **Trailers are read from the body only**,
  not the subject, and need at least one character after the colon. Of the trailers, `Fixes:`, `Bug:` and
  `Reported-by:` count as fix references, whatever follows.
- **Reverts.** A revert qualifies under the primary outcome only if its message has "This reverts commit" and
  a hash of at least 7 characters that resolves to one reachable commit, and that commit existed at the cut.
  For a commit brought in by a merge, "existed at the cut" is judged by the **owning merge's** time. A revert
  that does not resolve, or whose target is later, counts only under the all-reverts outcome — unless its own
  message carries a fix reference or CVE (for example by quoting its target's subject), in which case it
  qualifies through that.
- **Merges.** A merge inherits a fix reference, CVE or qualifying revert from a commit it brings in, never
  from a bot's commit, never a revert of a commit brought in by the same merge, and its positives are its
  first-parent diff ∩ the linking commit's files. A merge bringing in more than 50 commits inherits nothing
  and is tainted. A merge is tainted if any commit it brings in — **a bot's included** — carries a link or fix
  wording. Tainted merges are kept out of the keyword outcome and the control pool; a tainted merge that
  inherits is still a positive.
- The window starts at the later of the cut and the scanned snapshot and ends at the cut plus 730 days.

### 6. Sensitivities — the list is closed by this amendment

**The closed list is Amendment 4's** (S1 to S9 with S5 and S8 as registered, go and django removed, the
earlier eight reported apart, the descriptive sub-pools, `PU_django_circuitpython_removed`,
`PU_mediawiki_freebsd_removed`) **plus the ten below.** Every one is run and reported whatever it shows. None
uses the words of the confirmatory tests or a Holm level. Any added later is dated and labelled as later. Each
is first run on a control repository with a known answer.

| name | definition | needs |
|---|---|---|
| `PU_reachable_universe` | remove files that are in the universe **and** that the history walk's own unit rule excludes. Defined by rule, never by "has no touch" | the `file` table |
| `PU_unreachable_made_reachable` | the other repair: those files stay ranked and can be positive | **a new extraction of touches for those paths from the clone**; the stored history cannot supply them |
| `PU_generic_dirs_restored` | files excluded only by `(^|/)cache/`, `(^|/)dist/`, `(^|/)[Ee]xtern(als?)?/` or `(^|/)env/` are ranked again — **only those the frozen engine scanned**. No new scan is made; restored files without scan rows are counted and left out | the existing scans |
| `PU_tracker_keys_case_sensitive` | a tracker key must be in capitals | the stored links |
| `PU_named_streams` | one random stream per repo and purpose, seeded from 2982 | — |
| `PU_late_revert_ticket_dropped` | a late revert that quotes a ticket not counted | the stored links |
| `PU_new_completeness` | completeness against the snapshot's tree with stored reasons; repos under 90% dropped | the `file` table |
| `PU_nesting_floor` | a repo whose nesting file covers under 95% of its files has its nesting cells dropped | — |
| `PU_window_assertion` | a repo whose window ends before it starts, or with no usable commits, dropped | — |
| S8 | rename following | registered, not yet run |

### 7. Counts published before scoring — none reads an outcome against a predictor

1. **All 14** cells of defect 46, as (repo, outcome, measure), marking which are confirmatory.
2. For each of the 15 drawn repos: that the window start equals the cut.
3. Per repo: window start, window end, usable commits. If a scored repo fails, it stays in the confirmatory
   run and its removal is `PU_window_assertion`.
4. Per repo: completeness on the registered measure and on the new one.
5. Per repo: files excluded by each pattern of `PU_generic_dirs_restored`, **and how many of them have scan
   rows**; universe files the history cannot touch; qualifying commits that qualify only through a lower-case
   tracker key.
6. Per repo: the share of files with a nesting value.

### 8. What a reader is told with the result

- **The label:** "pre-registered design; point estimates partly seen before scoring; scoring code corrected
  afterwards in four listed places; readings given as coded and as corrected."
- **A deviation table:** every difference between the registration and the reference code, and between the
  reference code and each correction: what, when, who decided it, whether it can move a confirmatory number.
- **What was seen and when** (Amendment 4), unchanged.
- **How much of a planted effect the pipeline recovers on generated repositories**
  (`docs/process/harness_report.md`, 20 seeds per case): with an effect of +0.138 on true fixes, the labels the
  written rule gives carry +0.077 and the Python pipeline reports +0.075; in generated C, +0.062 against
  +0.081. With no effect planted every predictor reads zero. **These are properties of generated
  repositories.** The share lost in the label rule depends on the mix of commit conventions the generator was
  given; it has not been measured on real repositories and is not a correction factor.

### 9. How the run is shown to be the frozen run

Three layers, none of which shows an outcome to a session:

1. **Inputs.** The label and universe tables rebuilt from the stored tables are hashed and compared with the
   hashes of what the reference code reads. Printed as equal or not equal, per repo.
2. **A known output.** The existing placebo output is regenerated by the reference code **in the sandbox, into
   the output directory** (the reference would otherwise write over the committed file). Compared byte for byte
   when the interpreter, numpy and its linear-algebra library are the versions recorded with the original; if
   any differs, compared number by number within 1e-9, and the versions and the largest difference reported.
3. **The run itself.** The sealed reference scorer is the confirmatory run. The stored-tables scorer runs
   beside it and a per-cell map is printed: **exactly equal** for counts, readings and repo sets; **within
   1e-12** for real numbers. Any "not equal" is investigated on control repositories, never on the real cells.
   This layer waits for the stored tables to hold derived predictors with their missing-value rules.

**The check is itself tested first**, blind: five copies of the code each carrying one seeded one-line fault
and five clean copies are run on control repositories; all three layers must flag each faulty copy and none
of the clean ones. **None of this is built yet.**

### 10. Review record, reconciliation and owner decisions

| point | raised by | disposition |
|---|---|---|
| Wrong reference commit; "frozen" already not true | Claude B1 | adopted (section 1); reproduced by the author |
| Holm and "not robust" mis-sorted | Claude B2 | adopted (section 4); truth table re-run by the author: 135 / 51 / 5 |
| Public counts prove nothing about the scorer | Claude B3 | adopted (section 9) |
| Nesting floor, completeness, window assertion can touch the scored set | Claude M1–M3 | adopted: each is a sensitivity |
| The fix-reference sentence was not what the code does; case-insensitive keys | Claude M4 | adopted; defect log 61 |
| Sensitivities loosely defined; list not closed | Claude M5 | adopted (section 6) |
| The label | Claude M7 | adopted; accepted by the owner |
| **The seal: "unchanged" kept the reference's weak seal** | Gemini 1 | adopted: external seal and order of operations (section 2) |
| Any un-silenced cell shifts the shared stream; verify the window on the drawn repos | Gemini 2 | adopted (sections 1, 7); the shared stream confirmed in the code |
| Pattern details: optional `#`, the colon, digit bounds | Gemini 3 | adopted: patterns verbatim (section 5) |
| Trailers are read from the body only and need a value | Gemini 4 | adopted; confirmed at `hist_meta.py:81` |
| Reverts: unresolved targets, the owning merge's time, the same-merge rule | Gemini 5 | adopted; confirmed at `sa3_outcomes.py:199-217` |
| Over-cap merges; a bot's commit taints | Gemini 6 | adopted |
| Restored files may have no scan rows | Gemini 7 | adopted: only scanned files are restored; counts published |
| The second repair needs new touches from the clone | Gemini 8 | adopted |
| The closed list must include Amendment 4's | Gemini 9 | adopted |
| Layer 2 writes over a committed file; equality needs a tolerance; clean copies | Gemini 10 | adopted (section 9) |
| Verify the truth table; pin N | Gemini 11 | done: N = 4 |
| Not adopted | — | none |

**Owner, 2026-11-14:** tainted merges follow the code; two keyword rules stay; unreachable-file removal runs
beside the frozen run; the confirmatory run keeps the registered random streams; the confirmatory run is the
reference scorer run once with every correction beside it; the label of section 8.

**Accepted by the owner on 2026-11-14 at about 5:05 PM Eastern** ("I accept amendment 5 revision 3"). In force from the commit that adds this section.
