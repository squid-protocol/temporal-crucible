# Registration: do structural instruments say where fixes land, beyond size? (SA3)

**Registered 2026-11-13, ~6:15 PM Eastern; pre-implementation design review completed 2026-11-13 before any SA3
tool exists and before any predictor named here has been scored against any outcome defined here.** Owner
decisions recorded: the instruments below; the high-precision label tiers are the primary outcome.

Written under `docs/STUDY_CHECKLIST.md`; every item is answered in the last section.

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
