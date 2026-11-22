# Registration 1: GitGalaxy-on-itself (2026-11-20, 5:45 PM Eastern)

Status: REGISTRATION RECORD, written by Claude at the owner's instruction ("lets do it", 2026-11-20). It freezes what was fixed before the
sensitivity pass finished. It governs `docs/self_hypotheses_draft.md`, `docs/self_hypotheses_amendment_1.md` and
`docs/self_sensitivity_plan.md` (Amendments 1 and 2) where they differ. Any later change is a dated amendment (checklist item 16).
The design reviews (item 15) are the two reconciled in Amendment 1 (Claude Fable, Gemini 4 Neon); no new review was run for this record.

## What is frozen, and the hashes
Frozen files, copied to `docs/self_speed/frozen_2026-11-20/` (SHA256SUMS in that folder):
- `steps_detected.json` (4343b9bc...): the detector output, 75 candidates on four corpora, thresholds T per corpus, 5 unresolved crash commits.
  Produced 2026-11-20 3:41 PM Eastern from the sampling, detection and refinement rules in `self_sensitivity_plan.md`. THIS IS THE CANDIDATE LIST.
- `steps_detected_before_refine.md` (79e8ea8f...): the same list as read by a person.
- `refined_first_pass_partial.jsonl` (244f0ade...): first-pass bisection results at registration, 68 of 75 candidates. The pass was still running; the
  remaining 7 and the second pass (Amendment 2) will be reported as a continuation, not edits to this file.
- Engine scanner for structure data: `engine-main` at fc8dd7125 (`tools/selfhistory/ENGINE_PINS.md`). Timing engine: each commit's own engine.
- Data cut-off ("the freeze"): GitGalaxy first-parent tip `7203d2555753ca2b29e180de3cb8d7845aca6a06` (2026-11-20 7:37 AM Eastern).
  Every commit up to and including it is DISCOVERY data. Every first-parent commit after it is HOLDOUT data.

## What was already seen (disclosure; item 11)
- Everything listed under "Already looked at" in the draft (speed table rep 1, hub function sizes, the 288 s -> 65 s language-crucible drop).
- The dense pilot and stage-2 timings, the 49-event partial refinement output (Amendment 2 says so), and `docs/self_speed/step_join_findings.md`, which joins
  steps to the files changed. So the commit-file mix of the localised steps (the SF-1/2 outcome) has been seen on all discovery data.
- 2026-11-20 evening, by the author before this record: of 40 localised commits, 34 touch `.py`, 11 touch language-definition files, 9 touch `.yml`
  (none only YAML). This is outcome-adjacent and is the only reason a YAML-settings idea exists; it is exploratory and is not registered as a hypothesis.
- Not seen by the author at registration: file-level fan-in and PageRank ranks of the orchestrator modules. The evolution report
  (`evolution_artifact/real/gitgalaxy_evolution.html`) contains the word "hub" and "orchestrator"; the author did not check whether it prints
  file-level ranks. See SF-11 below.

## Status of each hypothesis (the table that governs)
| id | status | data it may be scored on |
|---|---|---|
| SF-1/2 merged (steps localise to quiet or pattern-table commits) | CONFIRMATORY, prospective | HOLDOUT steps only; discovery data is descriptive |
| SF-11 (orchestrators are hubs, revised in Amendment 1) | CONFIRMATORY if the check below passes, else exploratory | discovery snapshots, fixed definitions |
| SF-5(a) (births landing in existing engine files) | EXPLORATORY until item 6 (rename-aware lineage) exists | any; no verdict |
| SF-3, SF-4, SF-7, SF-8 (all tiers), SF-9 | EXPLORATORY | any; nothing here is confirmation |
| SF-6, SF-10 as hypotheses; SF-5(b) | DROPPED (SF-10 stays as a control) | none |

### SF-1/2 merged: the confirmatory claim
- Claim: a localised speed step is more often a quiet commit than the base rate of engine-path commits. Quiet = mechanism bucket (a) only `standards/` files changed, or (b) core
  changed with at most 3 engine functions touched (bucket rules in Amendment 1 of the plan).
- Unit: a LOCALISED event, one per commit (several corpora naming one commit count once); only HOLDOUT commits.
- Direction: share of events in (a)+(b) is HIGHER than the share of (a)+(b) among all holdout first-parent commits that touch core or standards (era-stratified base rate).
- Test: one-sided Fisher exact test, events against other engine-path commits. Alpha 0.05, Holm over the confirmatory family of SF-1/2 and SF-11 (two tests).
- Smallest detectable effect: with 20 holdout events and a base rate near 50%, only an odds ratio of about 4 or more is detectable at this alpha; with fewer than 10 events the
  result is INCONCLUSIVE regardless of the value. A null is read only as "no effect above that size".
- Evaluation rule: score ONCE, at 20 localised holdout events or 2027-03-31, whichever comes first; no peeking before. Detection, refinement and bucket rules are exactly those in the plan and
  Amendments 1-2, using the corrected v2 refinement code. Refuted if the confidence interval for the share difference lies wholly at or below zero.
- Honest limit: the holdout is the same repo, later in time; item 11 asks for fresh repos. This design removes the discovery data from the test but does not give an independent repo. Say so in any write-up.
  Registered defaults (alpha, 20 events, 2027-03-31, OR 4) were chosen by the author under the "take the registered default" rule; the owner can change them before the first holdout event is seen.

### SF-11: the revised claim
- Claim: `gitgalaxy/galaxyscope.py`, `gitgalaxy/cobol_refractor_controller.py`, `gitgalaxy/cobol_to_java_controller.py` are each in the top 5% of engine files by size-matched fan-in AND by size-matched PageRank,
  in most snapshots after they exist, against a degree-preserving rewired null. Engine files exclude `__init__.py`, tests, vendored trees and `standards/` (exclusion set frozen now).
  Fan-out is reported, not decisive. The unit is the file, not the repo. Refuted if any of the three is outside the top 5% on both measures in most snapshots, or if size alone explains rank.
- Conditional: before scoring, the author or the owner greps the evolution report for file-level fan-in, fan-out or PageRank rankings. If any are displayed for these three files, SF-11 is downgraded to EXPLORATORY and says so.
- Alpha 0.05 inside the Holm family above.

## Controls still owed before any confirmatory score (from Amendment 1, unchanged)
Planted-regression positive controls, negative controls (comment-only, pure `git mv`, A/A across sessions), fixed-intersection file list, total regex CPU logging (an engine change, owner's call), module-path provenance, rename-aware identity, era reporting against GG-H1..H3 and FLT-H1..H3.
Until the planted-regression control recovers its plants blind, the SF-1/2 holdout test is run but its verdict is flagged "control not yet passed".

## Not registered
YAML or settings tracking (post hoc, exploratory); any hypothesis about speed caused by CI workflow files; new time slots (still on hold per the owner's decision 2).

## Addendum 1 (2026-11-20, evening): result of the SF-11 report check
Checked `evolution_artifact/real/gitgalaxy_evolution.html` and `gitgalaxy_evolution_whole_repo.html` (both written 2026-11-20 1:59 PM Eastern; the 'hubs' blocks in each).
- The reports print FUNCTION-level hubs only: top ten functions by callers and by centrality (`hubs.now`), top five (`most_called`, `most_central`), and former hubs. No file-level fan-in, fan-out or PageRank ranking is printed.
- Orchestrator files appear in four other places, none a hub rank: fix counts per function (`_process_file_worker` in `galaxyscope.py`, 24 fixes), oldest-alive functions (all of `galaxyscope.py`), function counts per top-level module (`galaxyscope.py` 60, `cobol_refractor_controller.py` 13, `cobol_to_java_controller.py` 6), and import-edge examples (`cobol_refractor_controller.py` to `cobol_jcl_forge.py` and `cobol_microservice_slicer.py`).
- The registered downgrade condition (file-level rankings displayed for the three files) is NOT met, so SF-11 stays CONFIRMATORY.
- Disclosure: none of the three orchestrator files holds a function in the top-ten hub lists (those are in `core/detector.py`, `core/source_text.py`, `core/prism.py`, `core/call_resolver.py`, `core/mainframe_boundary.py`, `cobolrt/Cobol.java`, and a tools file). That is a function-level measure, not the registered file-level one, but it was seen before scoring; any SF-11 write-up states it.
