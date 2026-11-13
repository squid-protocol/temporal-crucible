# Registration: does a *change* in structure say where fixes land? (SA3-CH, companion to SA3)

**Registered 2026-11-13, 6:13 PM Eastern (the commit time is the authoritative record), before any tool for it
exists, before any second snapshot has been scanned, and before any predictor named here has been computed on
any repo.** Owner decision recorded: register a companion change study and put it through the same two
independent design reviews as SA3.

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
