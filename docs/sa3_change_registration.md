# Registration: does a *change* in structure say where fixes land? (SA3-CH, companion to SA3)

**Registered 2026-11-13, 6:13 PM Eastern (the commit time is the authoritative record), before any tool for it
exists, before any second snapshot has been scanned, and before any predictor named here has been computed on
any repo.** Owner decision recorded: register a companion change study and put it through the same two
independent design reviews as SA3.

> **Read Amendment 1 at the end first.** It reconciles two independent design reviews and governs wherever it
> differs from the text below — which is most of the design: the snapshots, the activity control, the form of
> each measure, file matching, the gates and the confirmatory family.

Written under `docs/STUDY_CHECKLIST.md`. It inherits SA3 (`docs/sa3_registration.md` **as amended**) for
everything it does not restate: universe, cut, window, merge handling and inheritance, the HP outcome and its
revert rule, tree-wide commits, the matched control, floors, the pinned engine, intervals, and the reading
words. Where SA3 is amended later, this study follows the amendment unless it says otherwise.

## Why a companion

SA3 asks about the **level** of a structural measure at one moment. It cannot say whether a file whose
structure is *moving* is at more risk than one that has settled, which is the claim people actually make about
"churning" or "stabilised" code. That needs two snapshots.

## What was already seen when this was written

- **Nothing** about a change in any of the four measures against any outcome on any of the 46 repos.
- The **level** of call-graph in-degree against fixes on these repos (`docs/mod1_result.md`), and the outcome
  marginals read for SA3. Neither is a change.
- On **curl only**, with no outcome involved: a function's keyword mix is nearly constant over its life and
  what changes is naming and wiring (KWMAT / KWNEST, 2026-11-11). That is a reason to expect little variation
  in the keyword measures here, and it is stated so a null is not a surprise.
- REW (`docs/rew_hypotheses.md`) is registered at **function** grain on curl and openssl, on call-set churn,
  and has no scorer. It is a different study and is not replaced by this one.

## Design

**Two snapshots per repo**, both scanned with SA3's pinned engine and full output kept:

- **t0** — SA3's snapshot, at the cut.
- **t−1** — the last usable commit at or before **cut − 365 days**, on the same walk and unit rule as the cut.

**Files in the test:** unit files present at **both** snapshots, matched through renames by the history's
lineage id. Files born during the year have no change to measure; they are counted and reported as their own
group, never mixed in.

**Predictors — the change over the year, t0 minus t−1.** One primary per instrument, direction stated:

| instrument | primary (signed change) | why this form | secondary |
|---|---|---|---|
| **A. Call graph** | Δ `in_degree` | a file's inbound calls can change without the file being edited | \|Δ\|; Δ out-degree |
| **B. Keyword families** | Δ (`struct_branch` ÷ `total_loc`) | a count grows whenever the file grows; the per-line rate does not | raw Δ count; \|Δ\| |
| **C. Risk vectors** | Δ `risk_safety_score` | already a per-line score | became non-zero (0 → >0); \|Δ\| |
| **D. Branch-state** | Δ (`amplified_cascading_flux` ÷ `total_loc`) | as B | raw Δ count; \|Δ\| |

**Predicted direction for every primary: the measure went up, more fixes.**

**Stability, secondary and descriptive:** a file is *settled* if none of the four primaries moved over the
year. Reported: the HP rate of settled against unsettled files within the strata below. No confirmatory claim.

## The confound this design is built around

**A file whose structure changed is a file somebody was editing.** For B, C and D the change is exactly zero
unless the file was touched during the year, so an unmatched comparison would rediscover "recently edited files
get fixed" — which is prior activity, already known, and not a structural finding. Therefore:

- **Strata = LOC band × prior-activity group.** LOC bands as SA3 (10 if ≥ 300 matched files, else 5), on
  `total_loc` at t0. Prior-activity group = number of non-bot commits touching the file in the year before the
  cut, from the history: **0, 1, 2–3, 4 or more**. Fixed now.
- **Primary statistic:** SA3's `bAUC(x) − 0.5`, with pairs formed only **within a stratum** and inside the LOC
  caliper. Unedited files carry Δ = 0 for B, C and D and so contribute only ties; that is correct, not a bug —
  for those instruments the test is, in effect, among edited files with a similar amount of editing.
- **Co-reported, must agree** (SA3 Amendment 1 rule 1): the residualised statistic, residualising the
  within-stratum rank on ln(LOC) **and** ln(1 + prior commits).
- **Sensitivity "beyond level":** the same, additionally residualised on the measure's level at t0 — does the
  change say anything the level in SA3 does not.

## Hypotheses

- **CH-A, CH-B, CH-C, CH-D:** the mean effect of the primary change on HP over the **drawn** repos is > 0.

Four confirmatory tests, Holm-corrected (the first needs a 98.75% interval). Each is **supported**,
**contradicted** or **not detected** exactly as in SA3, and a supported result is **defect-specific** only if
it clears the matched control. The eight earlier repos are reported separately as exploratory.

A is confirmatory here although its *level* was seen on these repos: no change in it has been computed. This
is stated so a reviewer can disagree.

## Gates, run before any real change is read

SA3's three placebos and the unit-file assertion, with two differences: the block-permutation placebo permutes
the real change values **within a stratum**, and a fourth placebo is added — **the change computed between two
scans of the same commit**, which must be exactly zero for every file. Anything else means the two scans are
not comparable and the study stops.

**Power** is stated from the placebo spreads before unblinding, as in SA3. It will be lower than SA3's: for
B, C and D only edited files carry information.

## Floors and exclusions (in addition to SA3's)

- No usable commit at or before cut − 365 days, or the t−1 scan fails SA3's completeness rule → "no earlier
  snapshot".
- Fewer than 150 matched unit files → not scored.
- A primary change that is non-zero in < 10% of matched files, or has < 20 distinct values → "instrument
  silent" for that repo and predictor. **Predictor marginals (how many files moved, with no outcome) are read
  and published before scoring; the floors are not changed after that.**
- Engine output not comparable between the two snapshots (the same-commit placebo fails) → study stops.

## Sensitivities, declared now, reported, not gating

SA3's S1–S3 and S8 · the gap between snapshots set to 180 and to 730 days on the repos that have the history
· prior-activity groups replaced by lines changed, on the repos where a line-change harvest exists · files
born during the year added back with their t0 level as the change.

## Order of work, and what must not happen early

1. Two independent design reviews of this text; one reconciling amendment. **No tool before that.**
2. t−1 scans (outcome-blind) and the matched-file table; predictor marginals published.
3. The scorer is SA3's with the strata added; placebos; power amendment.
4. Code review. 5. Score — **after SA3 has been scored**, so the change result is read against the level one.

## Not in this registration

Function grain; more than two snapshots (trajectories, time since last change); any measure not named above;
age or language as moderators.

## What a result will and will not license

- Supported and defect-specific: "in this pool, among files of similar size and similar recent editing, a
  file whose X rose over the past year was more often tied to an issue, CVE or revert in the next two years."
- Supported but not defect-specific: the change marks where work is going on.
- Not detected: no effect larger than the stated detectable size — and for the keyword measures, possibly
  because they barely move.
- Nothing about causes, about single files, about C, or beyond this pool.

## Checklist answers

1 unit files present at both snapshots · 2, 3, 8 SA3's label rules as amended · 4 completeness on both scans ·
5 non-zero share of each change published before scoring · 6 SA3's languages · 7 SA3's dating; the realised
gap between snapshots recorded per repo · 9 direction stated · 10 power from placebos before unblinding · 11
confirmatory on drawn repos, earlier eight separate · 12 per-repo intervals and side counts beside every mean ·
13 "adds to size **and** to prior activity"; "beyond level" is a named sensitivity · 14 gates and
sensitivities above · 15 two independent design reviews before any tool, a code review before scoring · 16
dated amendments · 17 exclusions listed by reason · 18 changes to shared tools opt-in.

## Amendment 1 — 2026-11-13, 9:16 PM Eastern: two independent design reviews reconciled, before any tool or second scan exists

**State when written:** no SA3-CH tool exists; no second snapshot has been scanned; no change in any measure
has been put against any outcome on any repo. SA3 has not been scored.

- **Reviewer 1** (a separate Claude session; read-only; forbidden to compute any predictor–outcome
  association; measured predictor-versus-size and predictor-versus-activity on existing snapshots and ran
  synthetic simulations, `tools/exploratory/sa3ch_review_sim.py`): 6 blockers.
- **Reviewer 2** (Gemini 4 Argon, PR #183 comment of 2026-11-13; no in-place edits): 3 blockers, 2 majors.

**Both said, independently:** the four activity groups leave most of the activity confound in place; the
per-line rate moves whenever the file's length moves; the risk score needs conditioning on where it started;
tree-wide commits and renames corrupt the prior-activity count; and A should be exploratory. **Neither
contradicts the other anywhere.** Where one saw what the other did not, it is adopted below.

Reviewer 1's simulation is the reason this amendment is not optional. With **no real effect** and a latent
"being worked on" intensity driving both the change and later commits, the statistic as registered read
**"supported" in 33–37% of simulated studies**, and in **83–93%** when newly written code is fixed more often.
A predictor that is nothing but **lines changed** passed every registered gate, the matched control included,
in **93–100%** of studies in that scenario. With the calipers of rule 3 the false rate is 0–3%.

### 1. The two snapshots and what "prior activity" is (reviewer 1)

- **t−1** = the last commit **on the first-parent ancestry of the t0 snapshot** with committer time ≤ snapshot
  time − 365 days. If it is not an ancestor of t0 the repo is excluded as "no earlier snapshot on the line"
  (today: root and runtime).
- **Prior activity of a file** = the commits **between the two trees** (`t−1..t0`) that touch it, counted by
  the history's lineage id, **tree-wide commits removed** (SA3's rule, applied to this interval), bots included
  and reported separately. A calendar window is not used: in several repos it misses a quarter to a half of
  the commits that actually lie between the trees, and a yearly copyright commit otherwise moves every dormant
  file into the "1 commit" group (postgres: 37% of files).
- **Lines changed** per file = added + deleted from `git diff --numstat -M t−1 t0`, for every repo.

### 2. Which files are in the test (both)

- Universe = SA3's t0 unit files; unit status is judged at t0 only.
- A file is **matched** if its lineage path at t−1 is in the t−1 scan with LOC > 0; else if the identical path
  is in the t−1 scan ("path fallback", flagged); else it is **born** and reported separately.
- **B, C and D are scored on edited matched files only** (≥ 1 prior commit) — an unedited file has no change
  to rank and would only dilute the estimate by the repo's dormancy rate. A keeps unedited files, because its
  value can move without the file being touched. The all-matched version is a reported secondary.
- **Floors are recomputed on the files actually in the test:** SA3's 30 positive files from 20 commits and 30
  negatives, plus **at least 100 eligible pairs in which the two changes differ**, and at least 150 files.
  Matched, born, path-fallback and renamed counts are published per repo before scoring.

### 3. The activity control (both; reviewer 1's simulation)

The four groups are withdrawn. **A pair is eligible only if the two files are in the same LOC band and satisfy
all three calipers:** LOC ratio ≤ 1.5; (1 + prior commits) ratio ≤ 1.5; (1 + lines changed) ratio ≤ 2.
The primary statistic is SA3's bAUC over those pairs. **Co-reported, must agree:** the residualised statistic,
residualising the within-band rank on ln LOC, ln(LOC_t0 / LOC_t−1), ln(1 + prior commits), ln(1 + lines
changed), ln(1 + prior-year HP commits) and the measure's **level at t−1**. Reported only: the same with the
t0 level in place of the t−1 level (a different question: does a lower past matter given the present).

**Benchmark gate, new:** lines changed and prior commit count are run through the final pipeline as if they
were predictors. **No SA3-CH result is reported as a structural finding unless both read "not detected".**

### 4. The four measures, restated (both)

| | primary | change from the text above |
|---|---|---|
| **A** *(exploratory)* | Δ in **external, confident** inbound calls: `fcall_data` rows at steps class, qualified, file, typed, import, unique whose source file differs from the destination file, both ends from the pinned-engine scans | was "in_degree", which included a file's calls to itself (20–52% of the total) and ambiguous resolutions, and would have mixed two engine versions |
| **B** | Δ (`struct_branch` ÷ **`coding_loc`**) | comment-only edits no longer move it |
| **C** | Δ `risk_safety_score`, scored **separately for files that started at 0 and files that started above 0** and combined across the two | a file already at 80 cannot rise; one at 0 can only rise |
| **D** | Δ (`amplified_cascading_flux` ÷ **`coding_loc`**) | as B |

- The "instrument silent" floor for B and D is applied to the **raw count** change, not the rate (on curl a
  quarter of non-zero rate changes have an unchanged count), and the share of rate changes with an unchanged
  count is published per repo.
- |Δ| secondaries are labelled **"activity-like, not evidence of a structural effect"** (on curl |Δ| tracks
  commit count at 0.51–0.64; the signed change barely does). For C, "changed by ≥ 5 points" replaces "became
  non-zero", which did not happen once in a year on curl.
- The "settled" secondary is dropped: under rule 2 it is the same thing as "not edited".

### 5. Gates (reviewer 1)

Added to the placebos above. **Blob-identical gate:** for every matched file whose content hash is identical
at t−1 and t0, the changes in B, C and D must be zero. The risk score is multiplied by path rules and by a
factor that depends on the dominant language of the file's folder, so it can move without the file changing;
a same-commit rescan cannot see that. The non-zero share is published per repo and instrument, and **an
instrument is not scored on a repo where it exceeds 1% of identical files.** For A the same share is published
as "resolution drift", and A is reported separately on identical and edited files. Scans are run with a fixed
hash seed.

### 6. Confirmatory family and reading (both)

**CH-B, CH-C and CH-D are the confirmatory family, Holm-corrected (the first needs a 98.33% interval). CH-A is
exploratory** — its level was seen on these repos and its change rank-correlates with that level at up to
0.68 — and is never called "supported". **A hypothesis scored on fewer than 10 repos is reported as
"underpowered, descriptive".** HP is also reported without reverts whose target lies between the two
snapshots, since that commit is the change being measured.

### 7. Power, stated honestly now (reviewer 1)

Under the null the between-repo spread of the residualised effect is about 0.04. Detectable at 80% power on
the Holm-first interval: about **0.034 with 16 repos, 0.047 with 10**, before any heterogeneity of true
effects. For scale, risers fixed 35% more often and fallers 26% less than unchanged files gives about 0.04.
Sixteen is an upper bound. The power amendment states the number for 16, 12 and 8 scored repos.

### 8. Freeze before SA3 is scored (reviewer 1)

Each change contains the t0 level that SA3 scores against the same outcome. **This amendment, the SA3-CH
scorer, its placebo and benchmark runs, its power amendment and its code review are all committed before SA3
is scored.** Anything changed afterwards is labelled "post-SA3" and cannot support a confirmatory claim.

### 9. Limits added

Racket reorganised inside the year (4,465 unit paths at t−1, 801 at t0) and similar repos are listed. A rename
with a heavy rewrite is recorded by git as delete plus add, so the most-changed files tend to be dropped as
"born"; this biases toward the null and is stated, not fixed. SA3 and SA3-CH together put six confirmatory
tests on the same repos and outcome.

### Order of work (replaces the list above)

1. t−1 commits and ancestry check; `numstat`; matched-file table — published.
2. t−1 scans with the pinned engine and a fixed hash seed; blob-identical gate; predictor marginals published.
3. Scorer; placebos; benchmark gate; power amendment. 4. Code review. **5. Everything above committed.**
6. SA3 is scored. 7. SA3-CH is scored.
