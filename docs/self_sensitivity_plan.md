# Sensitivity pass: did the sampling of GitGalaxy's history miss important changes? (plan fixed 2026-11-20, before the data below was collected)

Context: owner decision 2026-11-20 after Amendment 1: no control repo; spend the effort sampling more of GitGalaxy itself. EXPLORATORY; nothing here confirms a hypothesis.
Everything in this file is declared before stage 2 data exists. The pilot (stage 1: every 25th first-parent commit, three small corpora, 1 repeat) is still running when this is written.

## Why the pilot is not enough
The three small corpora cannot see steps like E2 (file screen, vendored trees) or E3 (comment stripping), which only moved language-crucible. The grid is by commit index, so early history is thin (about 9 points before July) and October is dense. One repeat gives no noise floor.

## Stage 2: sampling rule (deterministic, fixed now)
Sample set S2 = {first-parent index i : i mod 25 = 0} U {the last first-parent commit of each calendar week, US Eastern, Monday-Sunday} U {the last commit}.
- language-crucible (full repo, as in the steps already found): every commit in S2, 1 repeat.
- keyword-rosetta, cics-crucible, the one-file-per-language control: the weekly commits not already in the pilot, 1 repeat.
- A/A anchor: every 20th probe, re-time the anchor commit 7203d25 (2026-11-20 tip) on all four corpora in the same session. These give the within-session drift and noise floor per corpus.
- Each run records wall, CPU seconds, files mapped, function and edge counts of the output (parity), box load.
Order: interleaved by index, one scan at a time.

## Detection rule (fixed now)
For each corpus, order the successfully timed commits by index. A pair of consecutive timed commits is a CANDIDATE if |dCPU| / CPU_prev > T or |dfiles| / files_prev > 3%, with T = max(10%, 4 x the largest relative deviation of that corpus's A/A anchor runs from their median).
Pairs with a failed run on either side are reported as UNRESOLVED (the engine could not be timed), not as clean.
RAMP check: within every window of 10 consecutive timed commits, if cumulative |dCPU| > 2T and no single pair exceeds T, the window is reported as a RAMP.

## Refinement rule (fixed now)
Each candidate pair is bisected to a single first-parent commit (`tools/selfhistory/bisect_cost.py`, the corpus that flagged it, threshold at the midpoint), then the boundary pair is re-timed with 2 repeats. A step is LOCALISED if the boundary pair differs by more than T in the same direction; otherwise it is reported as UNCONFIRMED. No further sampling is added based on what looks interesting; the pass ends after refinement unless the owner asks.

## Sensitivity report (what this pass is for)
1. Recall on the known events: of the five steps already found (E1 #3929, E2 #5512, E3 #1234, the earlier 07-27..08-13 step, the 11-04..11-20 drift), how many does the stage 1+2 sample flag, and on which corpus.
2. New localised steps, each with commit, corpus, size, direction, and the commit's files by kind.
3. Counts: candidates, localised, unconfirmed, unresolved, ramps; engine crash commits.
4. The detection floor implied by the A/A noise (T), stated per corpus.
5. What the sample cannot see: steps in corpora not used, wall-only or memory effects, regressions and reverts inside a sampling gap.

## Amendment 1 (2026-11-20, evening; stage 2 and detection are done, 25 of 75 refinements seen; rules for the final analysis fixed before the remaining refinements finish)
Written so the final analysis is mechanical. Nothing here changes the sampling, detection or refinement rules above.
- Events: a LOCALISED refinement (class LOCALISED in `refined.jsonl`) names one first-parent commit; several corpora naming the same commit are one event with per-corpus sizes. UNCONFIRMED and UNEVALUABLE candidates are counted and listed, not analysed as steps.
- Commit facts for every event: the squash subject and PR number/title/labels (from `gh/items.jsonl` and the `(#N)` in the subject), files changed by kind (core, standards, translator_tools, tests, docs, other: the `kind()` rule of `tools/selfhistory/join_steps.py`), engine Python functions touched (the evolution generator's diff cache; a commit not in the cache touched none), lines added and deleted.
- Mechanism buckets (declared): (a) only `standards/` files changed (pattern tables, rules); (b) core changed with at most 3 engine functions touched ("quiet"); (c) core changed with more than 3 functions; (d) only translator_tools, tests, docs or other files changed (the step is probably misattributed or a side effect of an earlier commit; flagged); (e) no files in the engine path.
- Quiet-step test (the merged SF-1/SF-2 claim): the share of events in buckets (a)+(b) against the share of the same buckets among ALL first-parent commits that touch core or standards (the base rate), with an exact binomial interval for the events and a Fisher exact test between event commits and the other engine-path commits. Reported both for all events and for events with size above 25%.
- Persistence: for each UP step on a corpus, the pre-step level is the median CPU of the 3 timed commits before it and the post level the median of the 3 after; the step is REVERSED if a later run of 3 consecutive timed commits returns within the corpus threshold T of the pre-step level; otherwise PERSISTENT to the last timed commit. Report the share reversed, the median time to reversal in days and in commits, and the share still elevated at the tip. DOWN steps are listed with their size.
- Text screen (SF-8 tier c): precision and recall of a performance-word screen on the commit subject and PR title (the keyword list in `join_steps.py`) for the events, against its hit rate among all engine-path commits.
- Sensitivity report items from the plan, plus: events by month and by corpus, step-size distribution, steps seen by only one corpus, the commits where the engine crashed (unresolved), and the detection floor T per corpus.
- Known events: recall of E1 (#3929), E2 (#5512), E3 (#1234), the first 2026-07-27..08-13 step and the 2026-11 drift, each reported as flagged, localised, unconfirmed or missed.

## Amendment 2 (2026-11-20, evening; after independent review 1 of the final-analysis scripts; 51 of 75 first-pass refinements seen: 29 localised, 21 unconfirmed, 1 unevaluable). Declared before any second-pass result exists.
The Claude review found two defects in the refinement code, both verified by the author against the data:
1. `bisect_cost.py` assumed the first commit after the lower bracket was uncrossed and never probed it, so a step there was named at the second commit and then compared with the first (flat, hence UNCONFIRMED). Of the 22 non-localised refinements, 8 ended exactly at the second commit.
2. `refine_candidates.py` tested the rounded `dcpu` stored by the detector against T. The E1 bracket on cics-crucible (raw -10.038%, T 10%) was routed to the files-mapped metric and UNCONFIRMED by construction; 2 of 75 candidates change metric when the raw value is used.
Fix and re-run rule: `bisect_cost_v2.py` (the lower bracket commit is index 0, the known-uncrossed endpoint; one-commit windows get the boundary check) and `refine_candidates_v2.py` (raw dcpu). After the first pass finishes, every candidate the first pass left UNCONFIRMED or UNEVALUABLE, plus the 2 whose metric changes, is refined again (`refined_pass2.jsonl`). A second-pass result supersedes the first for that candidate; first-pass LOCALISED results otherwise stand. Both passes are kept in the record and the report states how many results changed.
Changes to the Amendment 1 analysis rules adopted from the same review (made before the final data; the author had seen the 49-event partial output, so these are not blind): (i) persistence is evaluated only for steps whose post-level median is outside T; REVERSED = the median of 3 consecutive later timed commits (after the post window) is within T of the pre level or beyond it in the reversing direction; a step removed by a named later DOWN event is reported separately; ELEVATED AT TIP is independent of REVERSED (median of the last 3 timed commits above pre x (1+T)); steps with fewer than 6 timed commits after them are excluded; steps whose pre or post window contains another localised step on the same corpus are reported as overlapping and excluded from the pooled figures; pooled persistence is counted per commit as well as per corpus. (ii) The quiet-step test stratifies the base rate by era (Gemini, Claude, fleet by the commit's date), is shown at cutoffs of 3 and 5 functions and for strict bucket (a) alone, excludes files-mapped events from the primary, and pairs the share and the p-value on the same population. (iii) Known-event recall requires direction and metric to match, and reports UNCONFIRMED as a status. (iv) POST HOC sensitivity: an absolute floor (a candidate counts only if the change is at least 0.5 CPU seconds), because T was measured on the tip's long scans and applied to 0.3-3 second early scans. (v) `run_all.sh` stops on a failed script and stamps outputs with the input snapshot hash.
