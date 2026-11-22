# WCC — within-commit comparison: are the files a fix touches structurally unlike their neighbours?

**Status: DRAFT for two independent design reviews and owner approval. Not registered. No tool exists and
nothing has been computed.** Written 2026-11-14, before SA3 is scored, so that SA3's result cannot shape it.

Written under `docs/STUDY_CHECKLIST.md`. Reviewers: findings as comments, not in-place edits; no
predictor–outcome association may be computed; synthetic simulations and the placebos named here are fine.

## Why this design

SA3 asks whether a structural measure ranks later-fixed files above others of similar size across a whole
repo. Three independent reviews showed how much that comparison has to control by hand: size, directory,
recent activity, repo composition (imported third-party code, test fixtures), and a label that means
different things in different projects. SA3 can only detect a mean effect above about 0.05 to 0.08, and its
companion change study was withdrawn because its activity confound needed more machinery than it could carry.

This design makes the comparison local. **For each fix commit: the files it touched, against files in the same
directory, of about the same size, that it did not touch.** Whatever is common to a directory at that moment
— the subsystem, its owners, how busy it is, whether it is vendored — is the same on both sides.

## What was already seen when this was written

- **SA3's point estimates on these repos were partly seen** (SA3 Amendment 4): the level of the four
  primaries against "file tied to a fix", to about ±0.005–0.01. They looked at or below about +0.04.
- MOD-1's in-degree results, and the label audit of the third review (73–81% of sampled HP commits are fixes).
- **Therefore nothing computed on the 46 repos already in use can be confirmatory here.** They are the
  development set. Confirmation is on repos that have never been scanned for any of these studies (below).

## Data

**Development set (exploratory):** the 40 repos with complete SA3 scans.

**Confirmation set:** the repos of the corpus pool not drawn for MOD-1 — 33 by the draw record
(`docs/draw40.json`: 31 young managed, 2 young C). They are scanned once each at the SA3 snapshot rule with
the pinned engine, and nothing about them is looked at until the development analysis, the gates, the power
statement and the code review are sealed. *Open for review: 33 is all there is, and it is one corner of the
age × language table; is that an acceptable confirmation set, or should new repos be cloned by a stated rule?*

Snapshot, universe, engine, tree-wide rule, merge inheritance, the HP definition and the tainted-merge rule
are SA3's as consolidated (`docs/sa3_registration_consolidated.md`), unchanged.

## Design

**A set** is one qualifying commit in the 730 days after the snapshot.

- **Cases:** the unit files the commit touches that existed at the snapshot.
- **Referents:** unit files at the snapshot **in the same directory as a case**, not touched by that commit,
  with LOC within a factor 1.5 of that case. A referent may be a case of another commit.
- A set counts only if it yields at least one (case, referent) pair. A commit touching more than 10 unit
  files is excluded (it is a sweep, not a fix to a place), stricter than the tree-wide rule.
- Structure is read at the snapshot, so a fix up to two years later is compared on stale structure.
  **Sensitivity:** sets in the first 365 days only.

**Two kinds of set, and the estimand is their difference.**

| kind | qualifying commit |
|---|---|
| **fix sets** | an HP commit (SA3's primary outcome) |
| **ordinary sets** | a commit from SA3's control pool, drawn so that the number of sets and their distribution of files-touched match the fix sets (200 draws, fixed seed) |

A hub file is touched by everything. Comparing touched with untouched files therefore measures "where work
lands" for any commit. **The effect is concordance in fix sets minus concordance in ordinary sets:** what
distinguishes the files a *fix* touches beyond what distinguishes the files *any* commit touches.

## Statistic

Per repo and predictor x:

1. For each pair, concordance = 1 if x(case) > x(referent), ½ if equal, 0 otherwise.
2. Pairs are weighted so that **each set counts once**, and — as in SA3's bAUC — pairs where the case is the
   larger file and pairs where it is the smaller are scored separately and weighted equally.
3. c_fix = that weighted concordance over fix sets; c_ord = the same over ordinary sets, averaged over draws.
4. **effect = c_fix − c_ord.** Reported beside it: c_fix − 0.5 (labelled "includes where work lands").

Per-repo uncertainty: bootstrap over **sets**, never files or pairs. Across repos: the unweighted mean with a
t-interval over repos; the random-effects mean, τ, the sign test and per-repo side counts beside it.

**Floor per repo:** at least 30 fix sets and 30 ordinary sets with a pair, at least 200 pairs on each side,
and no single file appearing as a case in more than 10% of fix sets.

## Predictors

SA3's, read from the same scans: `in_degree`, `struct_branch`, `risk_safety_score`,
`amplified_cascading_flux` as primaries, direction "higher in the case". Secondaries as in SA3, including
nesting depth.

**Change arm, exploratory in both sets:** for repos with an earlier snapshot, the change over the prior year
in each measure (per code line for the two counts; external confident inbound calls for the call graph),
compared between case and referent the same way. Same-directory matching does part of the work the withdrawn
change study did with calipers; whether it does enough is exactly what the benchmark below tests.

## Gates, before any real predictor is compared

1. **Size surrogate** of each primary (SA3 Amendment 4): c_fix − c_ord within 0.005 of zero.
2. **Path hash:** the same.
3. **Activity benchmark:** the file's count of commits in the year before the snapshot, run as a predictor.
   Its c_fix − 0.5 is expected to be clearly positive (touched files are busy files); its **effect**
   c_fix − c_ord must read "not detected". If it does not, the ordinary sets are not absorbing activity and no
   structural result is reported. *This gate, and every gate, is simulated on synthetic data before it is
   adopted* (checklist item 15; the SA3 block-permutation gate was not, and failed a correct pipeline 71% of
   the time).
4. **Label audit:** 100 fix commits sampled across the confirmation repos are read at diff level by a reviewer
   who sees no predictor; precision is reported with the result and, if under 0.6 in a repo, that repo is
   reported separately.

## Hypotheses (confirmation set only)

- **WCC-B, WCC-C, WCC-D:** the mean effect of `struct_branch`, `risk_safety_score`,
  `amplified_cascading_flux` is > 0. Holm-corrected, three tests.
- **WCC-A** (`in_degree`): exploratory.

Supported / contradicted / not detected by the Holm-level interval, as in SA3. Power is stated from
simulation and from the development set's between-repo spread **before** the confirmation repos are scanned;
if the detectable effect exceeds 0.05 the study says so then and the owner decides whether to proceed.

## Known weaknesses, for the reviewers to attack

- Files in a fix commit's directory are not independent of the fix: the referent may hold the same bug, or
  the fix may be a rename that touches one of two near-identical files.
- A commit that touches one file contributes little; a repo of one-file fixes will have few pairs per set.
- Directory is a crude neighbourhood. Flat repos (one directory) get no local control at all; deep ones get
  tiny sets. *Open: use the parent directory when the directory has fewer than five unit files?*
- "Existed at the snapshot" drops fixes to new code, which may be where most defects are.
- The ordinary-set draw matches on files-touched only. If fix commits and ordinary commits differ in who
  writes them or when, the difference carries that.
- The confirmation set is small and almost all young managed-language repos.
- HP remains "tied to a ticket" where projects use tickets for everything (django, mediawiki).

## What is not in this draft

Function grain (the natural next step: the functions a fix hunk touches against the other functions of the
same file — the tightest size and context control available, but it needs a line-level harvest for every
repo); a hand-audited label as the primary outcome; any measure not named above.

## Checklist answers (draft)

1 cases and referents are unit files at the snapshot · 2, 3, 8 SA3's label rules · 4 completeness per scan ·
5 per-predictor non-zero share and call coverage published per repo · 6 SA3's languages · 7 SA3's dating ·
9 direction stated · 10 power before the confirmation scans · 11 confirmation on never-scanned repos only ·
12 per-repo intervals and side counts · 13 the comparison is within directory and size, and net of ordinary
commits · 14 gates and the 365-day sensitivity above · 15 two design reviews of this draft, every gate
simulated first, a code review before the seal · 16 dated amendments after registration · 17 exclusions
listed by reason · 18 changes to shared tools opt-in.
