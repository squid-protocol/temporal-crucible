# SA3 — code review record for the reference code

**2026-11-14.** This is the document `tools/sa3_score.py lock` requires before it will seal. It records every
fault found in the code the confirmatory run uses, who found it, and what Amendment 5 does with it.

**The code reviewed** is the reference code of Amendment 5: `tools/sa3_score.py` and `tools/sa3_outcomes.py`
as at `8fb7fe0`, `tools/sa3_stats.py` and `tools/mod1_lift.py` as at `edc5c53`, and the modules they load
(`hist_meta.py`, `laws_units.py`, `laws_history.py`, `hist_fixlabel.py`, `sa3_nest_scan.py`). None has changed
since `8fb7fe0`.

**What this record is, and is not.** It is compiled from `docs/STUDY_DEFECT_LOG.md`, whose entries were
written when each fault was found, and from the review files under `docs/process/reviews/`. The fourth
reviewer's own report (entries 42–48) was delivered in a session and was not saved as a file; its findings
survive as those seven log entries. **This is not a statement that the code is correct.** It is a statement of
what is known to be wrong with it, shown beside the result.

## Reviews of this code

| review | by | method | found |
|---|---|---|---|
| Code review on the pull request | Gemini | reading | log 22, 23 |
| Third review, whole built system | Claude, independent session | reading, and synthetic data | log 25–33 |
| Fourth review, before scoring | Claude, independent session | an end-to-end run on synthetic data with a known answer | log 42–48 |
| The harness | the unmodified pipeline run on generated repositories with a known answer (`docs/process/harness_report.md`) | running | log 54–60 |
| Reviews of Amendment 5 | Claude and Gemini, independent sessions | reading the code against the amendment's text; made-up commit subjects | log 61, 62; the exact pattern and trailer behaviour of Amendment 5 section 5 |

## Faults in the reference code, and what happens to each

"Beside" means: the confirmatory run keeps the code as it is, and the correction or sensitivity is run and
printed next to it (Amendment 5 sections 4 and 6).

| log | fault | can it move a confirmatory number or reading | disposition |
|---|---|---|---|
| 42 | The Holm step-down stops at a contradicted primary, so later primaries with intervals above zero read "not detected" | a reading, in 135 of 729 input combinations | beside: both readings printed; a hypothesis whose readings differ is not called confirmatory |
| 43 | "Not robust to the statistic" fires only when the primary reads "supported" | a reading | beside: both readings printed |
| 44 | The scorer's seal omits the labels, the scans, the universe rule and most rule code | no | the run is sealed from outside (Amendment 5 section 2) |
| 45 | One random stream shared across repos and predictors | the matched-control draws and the per-repo reference distributions | stays, as registered; beside: `PU_named_streams` |
| 46 | The narrowing of the "instrument silent" rule in `8fb7fe0` un-silenced count measures in 14 repo cells | yes: two confirmatory primaries are counts, and any un-silenced cell shifts the shared stream | disclosed (Amendment 5 section 1); all 14 cells published before scoring |
| 47 | Outside the three confirmatory tests the output prints "supported" at an unadjusted level | no number | beside: corrected wording |
| 48 | The "tracks reverted changes" reading compares 18 repos with 15 | a secondary reading | beside: printed as coded and as corrected |
| 54 | Text said tainted merges are in no outcome; the code counts one that inherits | no: the code is unchanged | owner ruling: the code governs; text corrected |
| 55 | GitHub's vendored list matches directory names such as `cache/`; first-party code there is unranked | the universe | stays; beside: `PU_generic_dirs_restored`; per-repo counts published |
| 56 | The completeness check uses the pipeline's own unit rule on both sides | which repos are excluded | stays, as registered; beside: `PU_new_completeness`; both measures published |
| 57 | `lock` seals outside a git checkout | no | the run is sealed from outside |
| 58 | The nesting scan swallows every per-file error | the exploratory nesting cells, and through the shared stream the draws after them | stays: the existing nesting files are sealed as they are; beside: `PU_nesting_floor`; coverage published |
| 59 | With a supplied snapshot, a repo whose merges are all bot-authored gets a window that ends before it starts and is marked "ok" | a repo's presence | window start, end and usable commits published for every repo; a scored repo that fails stays in the confirmatory run; beside: `PU_window_assertion` |
| 60 | The placebo stage crashes when no repo clears the floor | no | not applicable to the frozen list |
| 61 | The tracker-key pattern ignores case: "Fix UTF-8 decoding" is a fix reference | the primary outcome's positives | stays; beside: `PU_tracker_keys_case_sensitive`; per-repo count published |
| 62 | Amendment 4 named `edc5c53` as the frozen commit; its own commit changed the scorer | the record | corrected by Amendment 5 section 1 |

Also known and unchanged in the confirmatory run: a file renamed after the snapshot is no longer matched
(equal-path matching; sensitivity S8); a universe file the history walk cannot touch can never be positive
(`PU_reachable_universe`, `PU_unreachable_made_reachable`); a revert of later code that quotes a ticket counts
through the ticket (`PU_late_revert_ticket_dropped`).

## Faults fixed before the reference commit

Amendment 3 and Amendment 4 list the faults fixed in the code up to `8fb7fe0` (log 22, 31 and the items under
"Scorer faults fixed" in Amendment 4). They are part of the reference code.

## What has not been reviewed

- No review has compared the reference code's numbers with an independent implementation. The second,
  independent build (`docs/process/research_codebase_spec.md` section 9) and the three-layer check of
  Amendment 5 section 9 are not built.
- The statistics module was checked against a brute-force loop on 400 random cases by the third review, and
  against planted effects on generated repositories by the harness. The logistic sensitivity, the
  random-effects summary and the bootstrap intervals have had no check of their own.
- No estimate exists of how many faults remain. Five rounds of review each found new ones.
