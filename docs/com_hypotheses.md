# COM-H4 — comment drift: do functions whose header comment stays frozen while their code keeps changing get more CVE fixes? — registered 2026-11-10, before any drift statistic

**Why.**
- DC-2 found that what a function's comments *say* at birth predicts its later CVE rate (danger words: rate ratio
  1.45, all four repos). CF-H1 found that CVE fixes add danger-language comments more than ordinary fixes.
- Both look at comments at one moment. Neither asks whether the comments are *kept up*. A comment that describes
  code that has since changed is the classic "stale comment"; the literature (below) links it to bugs.
- Wave A (`docs/comment_wave_a.md`, exploratory) checked the instruments this reads: the engine's C/C++ comment
  lines (CMT-G: C P 99.9% / R 98.0%; C++ 100% / 99.4%) and a header-comment definition that was about 95% precise
  on curl.
- Proposed as COM-H4 in Gemini's 2026-11-09 comment review. Owner's choices (2026-11-10): CVE fixes as the outcome;
  curl, OpenSSL, nDPI and harfbuzz.

## Prior work

- **Tan, Yuan, Krishna and Zhou, "/\* iComment: Bugs or Bad Comments? \*/", SOSP 2007.** Extracted rules from comments
  in Linux, Mozilla, Wine and Apache and found code that broke them: real bugs and many stale comments. Shows that
  comment–code inconsistency marks defects. It works on comment content; this study uses only whether the comment
  changed.
- **Fluri, Würsch and Gall, "Do Code and Comments Co-Evolve? On the Relation between Source Code and Comment
  Changes", WCRE 2007.** In three Java systems most code changes did not update the comments next to them, and
  comment changes were done mostly in the same revision as the code change when they happened at all. This gives
  the base rate: frozen comments are normal. The exposure here is therefore *repeated* edits with a frozen header,
  compared with *equally edited* functions whose header did change.
- **Ibrahim, Bettenburg, Adams and Hassan, "On the relationship between comment update practices and software
  bugs", JSS 85(10), 2012.** Across three open-source systems, changes that departed from a file's usual
  comment-update practice were more often followed by bugs. File and change grain, all bugs. **This study extends
  it** to function grain, CVE fixes, C/C++ and the program's guards (size and churn strata, file-cluster bootstrap,
  rate per function-year).
- **Wen, Nagy, Bavota and Lanza, "A Large-Scale Empirical Study on Code-Comment Inconsistencies", ICPC 2019.** Found
  that inconsistencies are fixed in many commits and catalogued their kinds. Supports the premise; no defect outcome.

The citations are from memory and are checked against the published papers before the result doc ships.

## Data

- **Repos and lives.** INT-S's: curl, OpenSSL, nDPI and harfbuzz; the quarterly snapshots and function identities of
  `ints_eval.lives()` (moves within a quarter resolved as there); C and C++ functions with loc ≥ 3.
- **Fix labels.** `chg_eval.fix_events` / `map_fix` as in DC: the `latent` class is "CVE fix"; `other-fix`,
  `regression` and `extrinsic` are reported only descriptively.
- **Comments.** Engine `Prism.split_positional_comment_stream` (CMT-G's instrument; C, or C++ for harfbuzz), on the
  file at each snapshot, with tree-sitter function spans as in DC. The engine commit used is recorded in the report.

## Definitions (fixed now)

- **Header block of a function at snapshot k.** DC's "directly above" block only (not comments inside the body): the
  engine comment lines immediately above the function's first line, at most one blank line between. It *exists*
  when its comment text has at least two words. Text is compared after collapsing whitespace.
- **Body of a function at snapshot k.** The code stream (comments removed by the same Prism split) of the function's
  span, whitespace collapsed. A body *changes* between k−1 and k when that text differs. Comment-only edits do not
  count as body changes.
- **Window.** The 8 quarterly intervals ending at snapshot k (about 2 years).
- **At risk at k.** The function has a header block at k and at every snapshot in the window where it was alive, and
  its body changed in **≥ 2** intervals of the window.
- **Exposure at k.**
  - **Drifted:** at risk, and the header text is identical at every snapshot of the window.
  - **Maintained:** at risk, and the header text changed in at least one interval of the window.
- **Unit.** A function-quarter: each at-risk function at each snapshot k contributes person-time from snapshot k to
  the earliest of the next snapshot, the function's death and the repo's label end. Exposure can change from quarter
  to quarter.
- **Outcome.** A CVE fix (`latent`) that touches the function inside that quarter.

**Strata.** repo × log₁₀ loc bin (0.1 decade, DC's) × body-change count in the window (2, 3, 4, ≥ 5) × the file had a
CVE fix before k.

## Claims

| id | claim | supported iff (α = 0.01/2; MH rate ratio over function-quarters; file-cluster bootstrap, 2,000, seed 2982) |
|---|---|---|
| **COM-H4a** | drifted functions get CVE fixes at a higher rate than equally edited, equally sized maintained ones | rate ratio > 1 and lower bound > 1. **Reversed** if < 1 and upper bound < 1 |
| **COM-H4b** | the effect is CVE-specific | RR_CVE ÷ RR_other-fix > 1, lower bound > 1 |

- **Power rule.** At least 20 CVE-fix events in each exposure group, pooled. Otherwise the claim is **underpowered**,
  not a verdict.
- **Null.** If H4a is neither supported nor reversed, the result is called a **replicated null** only if the 99% CI
  lies inside [0.80, 1.25]. Otherwise it is **inconclusive**.

## Descriptive (no verdicts)

- Per-repo rate ratios and event counts.
- Rate ratios for `other-fix`, `regression` and `extrinsic`.
- Third group: equally edited functions with **no** header block (vs maintained), as a contrast to "has a comment at
  all".
- Share of at-risk function-quarters that are drifted, per repo (the Fluri base rate on this data).
- A 30-case random audit of drifted / maintained calls (header and body diffs shown), to check the instrument.

## Priors

- **COM-H4a uncertain, leaning supported.** Ibrahim et al. found the file-grain version; DC-2 showed comment content
  carries signal here.
- **The obvious threat is churn**, which predicts fixes and also makes header edits more likely. The body-change
  count stratum and the "maintained" comparator (both groups edited ≥ 2 times) are there for that. Residual churn
  within a stratum favours maintained functions having *more* edits, which biases *against* H4a.
- **COM-H4b uncertain.** DC-H2 (danger words, CVE-specific) was not supported.

## Known limits

- Quarterly snapshots miss within-quarter header edits that were later reverted, and count a quarter with several
  body edits once.
- The header walk stops at a non-comment line, so curl's `UNITTEST` prototype idiom hides some headers (Wave A,
  COM-E2). That affects drifted and maintained alike; such functions are simply not at risk.
- An identity break (rename plus move in one quarter) restarts a function's life, as in INT-S.
