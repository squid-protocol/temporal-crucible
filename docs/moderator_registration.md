# Registration: what moderates the sign of the structural effect? (MOD-1)

**Registered 2026-11-13, before any drawn repository was scanned.** The draw
(`docs/draw40.json`, seed 20261113) was made first and is fixed; no result from any of the 38 new repos
existed when this was written.

## Why

`struct_null.py` found call-graph in-degree beating LOC in four repos and losing in four, every one with a
bootstrap CI excluding zero, pooling to **+0.006** — a null no repository exhibits. In those eight, **age and
language are perfectly confounded**: all four anti-predictive repos are old C. The confound is the reason for
this study.

## Draw

38 repos from `/nvme-data/gitgalaxy-data`, stratified, excluding the 10 already assessed:

| cell | available | drawn |
|---|---|---|
| old C (first commit < 2006) | 8 | **8 — the whole cell** |
| young C | 12 | 10 |
| old managed | 10 | 10 |
| young managed | 41 | 10 |

**Pre-registered deviation**: old-C is short (8, not 10) because the pool holds only 8. Recorded here rather
than back-filled from a different source.

With the 8 previously assessed repos, the analysis set is **up to 46**.

## Hypotheses

- **MOD-H1 (age).** The in-degree lift over LOC is lower (more negative) in older repositories.
  *Mechanism*: in a long-lived codebase a hub is battle-tested — its bugs were found years ago — so hubs are
  fixed less than their size predicts.
- **MOD-H2 (language family).** The lift is lower in C/C++ than in managed languages.
- **MOD-H3 (interaction).** Age and family interact.

**MOD-H1 is primary.** H2 and H3 are secondary and reported whatever they show.

## Measurement, fixed now

- **Outcome**: `in_degree` AUC minus `loc` AUC, **cascade label**, one snapshot nearest the cut
  (`CUT_Q` of commits), fix window `WINDOW_DAYS` — all exactly as `struct_null.py` already computes them.
- **Floor**: a repo needs `MIN_POSITIVES` positives, as in `hist_replicate`. Repos below it are **excluded
  and listed**, never rescued with a different label.
- **Primary test**: OLS of lift on `old` (binary) + `C_family` (binary), bootstrap CI over repos.
  MOD-H1 is supported iff the `old` coefficient's 95% CI excludes zero.
- **Secondary**: the same with the interaction term; and a sign test (positive vs negative) by cell.
- **Age cut**: first commit before 2006 = old. Fixed now. Repos whose first commit date is implausible
  (imported history, e.g. `go` dated 1972) are **re-dated from the first commit on the current default
  branch**, and if still implausible, excluded and listed.

## What would falsify

If the `old` coefficient's CI includes zero while repos continue to split by sign, **age is not the
moderator** and the split is driven by something else — which is a reportable result, not a failed study. We
report it either way, including a flat null.

## What this does not test

Label quality is unchanged: cascade precision is better than keyword but its **recall remains unmeasured**.
This study is about the *sign* across repos, not the accuracy of any single repo's estimate.

Only `in_degree` is tested. Out-degree and function count lost to LOC in all eight earlier repos under every
label and are not promoted here.

## Amendment 1 — 2026-11-13, 2:40 PM Eastern, before any drawn repository was scored

**State when written:** 5 of 38 repos prepared (history + one snapshot), **zero lifts computed** for any drawn
repo — no `docs/struct_null_<repo>.json` exists for any of the 38. Nothing below was chosen with a result in
view.

**The problem.** `draw40.py` calls a repo's language by counting file extensions over the languages the
instrument measures (c, cpp, csharp, go, java, jsts, kotlin, php, python, rust). A repo written mainly in a
language the instrument does **not** measure is therefore called by whichever measured language has the most
files — usually bundled or peripheral code. Recounted with the instrument's own unit rule
(`laws_units.language_of` + `Excluder().why`, HEAD tree), **10 of the 38** have more first-party files in one
unmeasured language than unit files in any measured language:

| repo | cell as drawn | called | unit files in called language | main language (files) |
|---|---|---|---|---|
| racket | old/C | c | 685 | Racket (1,560) |
| ghostty | young/C | c | 55 | Zig (650) |
| swift | young/C | c | 1,468 | Swift (9,283) |
| wrf-fortran | young/C | c | 179 | Fortran (1,039) |
| fieldtrip | young/C | c | 197 | MATLAB (1,860) |
| rails | old/managed | jsts | 43 | Ruby (1,487) |
| bugzilla | old/managed | jsts | 15 | Perl (205) |
| discourse | young/managed | jsts | 2,146 | Ruby (5,792) |
| tigerbeetle | young/managed | java | 36 | Zig (204) |
| bun | young/managed | jsts | 470 | Zig (1,089) |

**What does not change.** The draw, the language calls, the cells, the outcome, the floor and the primary test
all stand exactly as registered. The primary result is the registered one, on every drawn repo that clears the
floor. Nothing is re-drawn or back-filled.

**What is added — sensitivity S1, declared now.** The registered test is repeated with the ten repos above
removed (rule: *first-party files in a single unmeasured language outnumber unit files in every measured
language*). Cells for S1 are at most old/C 7, young/C 6, old/managed 8, young/managed 7 — 28 drawn plus the 8
previously assessed. **Both are reported side by side.** If the primary and S1 disagree on whether the `old`
CI excludes zero, MOD-H1 is reported as **not robust to the language call**, not as supported.

**Noted, not acted on.** Under the same unit rule cpython has slightly more C unit files (1,108) than Python
(937) because its Python tests are excluded; it stays `python`, old/managed, as drawn. `root` and `godot` are
called `c` though most of their code is C++; both languages are in the same family, so the cell is unaffected.

## Amendment 2 — 2026-11-13, 2:47 PM Eastern, before any drawn repository was scored

**State when written:** 6 of 38 repos prepared, **zero lifts computed** for any drawn repo (no
`docs/struct_null_<repo>.json` for any of the 38; `mod1_score.py` has never been run). Owner decision.

**What changes.** The ten repos of Amendment 1 are no longer measured on a minority slice. The history step
(`laws_units.EXTS`) gains their main languages — ruby, zig, swift, perl, racket (with Scheme), fortran, matlab
— and each of the ten is harvested and scored in that language (`docs/mod1_language_amend.json`):

| repo | language now | family | cell as drawn → cell now |
|---|---|---|---|
| racket | racket | managed | old/C → **old/managed** |
| ghostty | zig | C | young/C |
| swift | swift | managed | young/C → **young/managed** |
| wrf-fortran | fortran | C | young/C |
| fieldtrip | matlab | managed | young/C → **young/managed** |
| rails | ruby | managed | old/managed |
| bugzilla | perl | managed | old/managed |
| discourse | ruby | managed | young/managed |
| tigerbeetle | zig | C | young/managed → **young/C** |
| bun | zig | C | young/managed → **young/C** |

**Family rule, fixed now:** `C_family` = a language with no managed runtime or garbage collector — c, cpp, zig,
fortran. Everything else is managed (Swift's reference counting counts as managed). Cells become old/C 7,
young/C 10, old/managed 11, young/managed 10. The draw itself is unchanged: same 38 repos, none added or
removed. The other 28 keep their language and cell exactly as drawn.

**The primary test is now the registered OLS on the corrected languages.** The as-drawn language for these
ten is not computed at all, so there is no second set of numbers to choose between.

**Sensitivity S1 stays**, with the same list and the same reading rule (Amendment 1): the test is repeated
without these ten. It now asks a sharper question — does the answer depend on languages the instrument had
never been used on before today?

**Instrument check, fixed now, drawn repos only.** The engine's call resolution in the seven new languages is
unverified (spot-checked only: ghostty Zig 3,230 edges over 378 files, racket Scheme 10,904 over 1,264). An
in-degree of zero everywhere would score as a spurious negative lift. So a drawn repo is **excluded and listed
as "engine does not resolve calls"** if, at its snapshot, the call edges landing in files of its language
number fewer than one per ten such files. This is read from the scan database, before and independently of
any lift.

**Test-file patterns added** for the new languages (`*_test.rb`, `*_spec.rb`, `*.t`, `*Tests.swift`,
`*Test.swift`); the directory rules (`test/`, `tests/`, `spec/` …) already apply to every language.

**Not changed.** Outcome, label, floor, cut, window, age cut, hypotheses, and the falsification statement.

## Amendment 3 — 2026-11-13, 3:04 PM Eastern, before any drawn repository was scored

**State when written:** preparation in progress; **zero lifts computed for any of the 38 drawn repos** by any
tool. An independent reviewer, given read-only access and forbidden to compute any drawn-repo outcome, checked
the code against this registration and returned six blockers. The owner agreed to all six. The earlier eight
repos were re-measured under the new rules (their results were already known); the drawn 38 were not touched.

### What the review found, and the rule that replaces each

1. **Universe.** `struct_null.py` ranked every scanned file (docs, tests, YAML, other languages) while only
   non-test files of the repo's one language could ever be positive. Those other files mostly have no callers,
   so in-degree was credited for telling source from non-source. **Now:** the universe is the repo's unit files
   only — `laws_units.language_of(path)` in the repo's language and `Excluder().why(path) is None` — the same
   rule the history uses to record a touch.
2. **Label.** The cascade's revert, fix-reference and CVE tiers read a commit-body harvest that existed only
   for the 11 earlier repos, so the 38 would have been labelled by keyword alone. **Now:** every repo, drawn
   and earlier, gets a body harvest (`pilot/meta_mod1`, merges included); a repo without one is excluded and
   listed, never scored on a thinner label.
3. **Merges.** Where the merge share is ≥ 0.30 the history walks first-parent and makes the merge the labelled
   unit — and the scorer then filtered merges out (ghostty: 3,550 of 5,400 commits). **Now:** merges are kept
   wherever the history's unit is "first-parent commit, merges included", for the cut, the label and the
   outcome alike. Known weakness, stated now: a GitHub merge commit's subject is "Merge pull request …", so the
   keyword tier sees little of it; sensitivity S5 removes these repos.
4. **Scan completeness.** A repo whose source the scan never read (macports-base: 0 of 128 C files) passed the
   Amendment 2 check because zero files skipped it. **Now:** unit files in the scan must be ≥ 90% of unit files
   in `git ls-tree` at the snapshot, and zero files fails; such a repo is listed as "scan incomplete".
5. **C and C++.** A bare `.h` is called C, so a repo harvested as `cpp` never saw a header fixed and one
   harvested as `c` saw only headers and `.c`. **Now:** a drawn repo called `c` or `cpp` is harvested with C and
   C++ files together as its units. (The earlier C repos are pure C and keep their existing histories.)
6. **Direction.** The scorer accepted a CI excluding zero on either side. **Now:** MOD-H1 is supported only if
   the `old` coefficient's 95% CI lies wholly **below** zero; wholly above is "contradicted"; including zero is
   "**not detected**" — never "age is not the moderator".

Implemented in `tools/mod1_lift.py` (new; `struct_null.py` is left as it was, as the record of the old rule),
`tools/mod1_run.py`, `tools/mod1_score.py`, with opt-in switches in `laws_history.py`, `hist_meta.py`,
`hist_fixlabel.py` and `label_cascade.py` so no other study's behaviour changes.

### The premise changes, and is stated before the result

Under these rules the earlier eight are no longer "four up, four down, all solid":

| repo | old rule | Amendment 3 | 95% CI |
|---|---|---|---|
| commons-lang | +0.052 | −0.032 | [−0.070, +0.001] |
| curl | −0.036 | −0.147 | [−0.181, −0.112] |
| libxml2 | −0.084 | −0.029 | [−0.086, +0.020] |
| ndpi | +0.119 | +0.179 | [+0.069, +0.306] |
| postgres | −0.039 | −0.099 | [−0.116, −0.083] |
| prometheus | +0.060 | −0.066 | [−0.100, −0.027] |
| redis | −0.063 | −0.078 | [−0.132, −0.029] |
| sphinx | +0.037 | +0.100 | [+0.018, +0.189] |

Two positive, four negative, two including zero. **MOD-1 therefore asks whether there is an age or family
pattern at all, not what explains a solid split.** The sentence "all four anti-predictive repos are old C" in
the original registration was also wrong on its own terms: redis starts in 2009.

### Also fixed now (the review's "should" items)

- **Age.** Every repo, drawn or earlier, is dated by its **1st-percentile commit time** (immune to one imported
  or joke commit); `old` = that year before 2006. Expected moves: go → young, wrf-fortran → old. This replaces
  the unimplemented "re-date if implausible" rule. Language family comes from the history's language.
- **Reading rule.** The verdict is "supported" only if the primary, **S1** (ten new-language repos removed) and
  **S2** (drawn repos only — the earlier eight generated the hypothesis) all read "supported". Any
  disagreement among those three is reported as **not robust**.
- **Further sensitivities, reported, not gating:** **S3** repos with fewer than 30% of unit files having any
  caller removed; **S4** repos with less than the full 730-day window after the cut removed; **S5**
  merge-workflow repos removed.
- **Secondary, not confirmatory:** lift on continuous age at the cut (years since the 1st-percentile commit);
  the age × family interaction; `C_family` itself.
- **Power, from the reviewer's simulation at the earlier repos' spread (SD 0.071):** with 46 repos about 33%
  for a difference of 0.03, 70% for 0.05, 86% for 0.065; with 26 repos 21%, 50%, 64%. A null is "not detected
  at this power".
- **Exclusion reasons are separate and listed:** unprepared, scan incomplete, engine does not resolve calls,
  no body harvest, under the positives floor, failed.

### What a result will and will not license

- CI below zero and robust: "in this pool, repos that began before 2006 show a lower in-degree lift, by about
  X". **Not** "age is the moderator", not a per-repo prediction, not the battle-tested-hub mechanism — a binary
  cohort is also an era of tooling and commit-message habits.
- Includes zero: not detected; effects under roughly 0.05 could not have been seen.
- Many exclusions: read which repos first. If they cluster in one cell the contrast is no longer the drawn one.
- The pool is a hand-collected set of well-known survivors; old/C is a census of 7. No claim beyond it.
