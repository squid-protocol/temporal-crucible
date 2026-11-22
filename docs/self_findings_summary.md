# GitGalaxy studied with GitGalaxy: what we learned (2026-11-20)

One day of work on one repository (squid-protocol/gitgalaxy, eight months old, 6,919 commits, mostly agent-written). Everything here is exploratory and unregistered; where a test was declared before its numbers existed, the text says so. Detailed notes and data are in `docs/self_evolution/`, `docs/self_speed/` and the plans in `docs/self_*_plan.md`.

## 1. The short version
1. **Structure is born solid and growth is new functions.** 86% of functions do not move on the lattice in their first week, 71% are identical to birth after 30 days, about 3% ever die; births land half in new files; only 12.5% of code edits are sweeps. The same shapes as curl and the other repos, on a clock that runs about 14 times faster (37 function edits per function-year against at most 2.6).
2. **The engine's speed moves in steps, about one a week, and most steps come from ordinary code commits, not from "quiet" edits and not from pattern tables alone.** 35 localised steps from 75 candidates (23 up, 12 down). Speed steps are less often small changes than other engine commits are (52% touch 3 or fewer functions, against 82%; p = 0.0003). No step came from a commit that changed only pattern tables (0 of 29). This reverses the picture the first three traced steps gave us.
3. **Speed regressions are not caught by the tests, but 7 of 10 evaluable up-steps were later undone.** The compile-policy step of 2026-09-27 (x3.3 to x5.7 on small many-language scans) is still in the engine.
4. **Repairs concentrate on hot functions and there is no call-graph ripple beyond that.** 428 functions take all fix touches; against a baseline that matches how often each function is fixed, the "radius" of successive repairs disappears (0.88x). A same-day follow-up effect (1.2-1.3x) is all that remains.
5. **We cannot show that the test pipeline lowers regressions, and the data could not have shown it.** Tests accompany 92% of engine-code changes, there is one revert in 6,363 commits, real failures are stopped before merge, and the fix rate per week stayed flat while the code grew tenfold; but there was never an era without tests, and the one before/after gate comparison available is not identifiable.
6. **Causes of bugs are mostly not findable from the text.** Two models reading issues name a recent causing PR for 15 of 100 bug issues, agree 93% on whether there is one and 10 of 10 on which; but both failed the recall bar we set on the few verified cause statements. Regex search for causes was only 33% precise. The route to better data is to record the cause when the issue is filed (promoter-bot#124).
7. **The measuring instruments were wrong in ways that mattered, and independent review found most of it.** Three reviews found bugs in the scanner-delta path, the timing rules and the analysis code; two published numbers were corrected.

## 2. What we built and measured
| | Count |
|---|---|
| Structure scans of GitGalaxy (full scans, one fixed scanner) | 195 commits (180 daily + 15 around the speed steps) |
| Timing runs (each commit's own engine, pinned corpora) | 1,516 logged (1,472 with real CPU data, 20 real failures); 320 distinct commits timed; about 2,000 engine scans with bisection probes |
| History analysed | 6,919 commits, 22,144 function edits, 8,779 issues and PRs |
| Models labelling causes | 2 (Claude, Gemini 4 Neon) on 100 bug issues |
| Independent reviews | 3 (design review by two models; code review of the analysis scripts by two models) |
Instruments: a daily-scan driver, a timing probe that runs each commit's own engine (CPU seconds, because wall time repeats at 18% spread and CPU at 1%), a bisector, a lineage ledger for function identity, the epic-#8715 evolution-report generator, and the call-graph film tool.

## 3. Hypothesis scorecard
Evidence level: PRE = rule and bounds declared before the numbers; EXP = exploratory, seen or built after looking.

| Claim | Verdict | Evidence | Level |
|---|---|---|---|
| **SF-1/2 (merged)**: speed steps come from quiet commits (few functions, tables or policy) | **Not supported; direction reversed** | Quiet (3 or fewer functions): 15 of 29 CPU events (52%) vs 81.7% of other engine commits; Fisher p 0.0003, era-stratified Mantel-Haenszel p 0.0021 (OR 0.28); steps above 25%: 38% quiet. Pattern-table-only commits: 0 of 29 events. | PRE |
| SF-2 direct: fix commits change fewer functions than feature commits | Not tested as stated; partial | Fix-subject commits are 10 of 35 events (29%), the base rate of fix commits among engine commits is 27.5%: no enrichment; 7 of the 10 made the engine slower (correctness fixes cost time) | EXP |
| SF-3: functions settle more slowly than in the 13 TURN repos | **Supported in direction, descriptive** | Identical to birth after 7/30/90 days: 82-87% / 62-75% / 26% (Gemini era, n 164); TURN repos 83-96% per quarter. Confounded by age and agent authorship | EXP |
| SF-4: hub files thicken then split (WRF thickens, C repos flat) | Pattern holds on two files; stays exploratory | galaxyscope.py mean function size 51 -> 88 -> 48; detector.py 35 -> 59 -> 39; WRF 79 -> 120; mesa 27 -> 28 | EXP (seen first) |
| SF-5(a): births land in existing files above 40% | Direction right, not distinct | 49% existing-file births (scanner core 55%, translator 46%); the other repos' held-out range is 44-56% | EXP |
| SF-5(b): fan-in rises over time | Dropped (growth alone predicts it) | | |
| SF-6: function structure adds little to speed beyond size until pattern tables are counted | Dropped (circular predictor) | | |
| SF-7: a few regexes hold most of the regex time | Not tested; premise weak | The engine reports only its top 15 regexes; regex time is 2-23% of CPU | EXP |
| SF-8: an O(N^2) -> O(N) change is detectable (a) by timing exponent, (b) from structure, (c) from commit text | (a) not run; (b) true by construction (no loop-nesting column); **(c) weak** | A corrected performance-word screen finds 5 of 34 steps (recall 15%), precision about 9%; the commit that caused the biggest step has no performance word; "perf:" commits gave 4 down-steps and 1 up-step | EXP |
| SF-9: scope change shows as sweeps above the other repos' median | Neither supported nor refuted | 12.5% of code edits in weekly sweeps (declared: above 22% predicted, below 10% refuting); table renames are invisible to a function-level method | EXP |
| SF-10: cost per mapped file is stable across engine versions | Not as stated | A file-screen change (3,389 -> 991 files mapped) changes the mix, so per-file normalisation fails; CPU is robust (1% spread), wall is not (18%) | EXP |
| SF-11: the three orchestrator files are hubs | **Not supported as fan-in hubs** | All three have fan-in 0 (entry points); galaxyscope.py is top fan-out (#1-#2); the controllers were #2-#3 and fell to #7-#8 as the repo grew | EXP |
| L1 (lattice): median displacement settles by 30 days | Degenerate by the declared rule; post hoc movers-only ratio 1.02 | 86% / 71% / 32% do not move at 7 / 30 / 90 days; movers jump once (about 0.4, three nearest-neighbour spacings) | PRE (rule), post hoc (fix) |
| L2: larger functions move more | Supported in direction | rank correlation +0.23 to +0.32 in each era; partly mechanical | PRE |
| L3: more movement in the Gemini era | Modest, direction supported | 66% stay put at 30 days (Gemini) vs 75% (fleet) | PRE |
| V1-R1 successive repairs land within 2 hops far more than random (above 3x) | **Not met** | 1.91x [1.66, 2.16] | PRE |
| V1-R2 beyond file locality (above 1.5x file-mates) | **Not met** | 1.29x [1.21, 1.37] | PRE |
| V1-R3 callers more than callees (above 1.5x) | Not met on raw rates (0.88); met as excess over file-mates (2.85) | wording ambiguous, both shown | PRE |
| V1-R4 decay with distance | **Not met** | 1.91, 1.91, 1.80 | PRE |
| V1 post hoc: the excess is hot-spot recurrence | **Supported** | against a null that matches fix frequency: 0.88x [0.75, 1.00]; permutation about 0.95; only same-day follow-ups keep 1.15-1.32x | EXP (added after the shuffle check) |
| T1: files with attached unit tests have a lower fix share | **Not supported** | OR 0.57 [0.29, 1.13]; raw shares go the other way (19% vs 10%) | PRE |
| T2: dose of tests | Passes its rule, but see T3a | OR 0.56 [0.40, 0.79] | PRE |
| T3a/T3b: direction | Tests are added after bugs; the lead model is as strong as the lag | lead OR 0.31 vs lag 0.52; attachment rises after a fix in 36% vs 14% (OR 3.56) | PRE |
| Before/after a dated test gate | **Not identifiable** | gates arrive with their subsystem; the one dated gate (29 accuracy baselines) is a measurement gate and fixes rose more (ratio 1.85) | EXP |
| Model labeller: gold recall at least 85% | **Failed (3/5, 2/5)** | agreement gates passed (93%, 10/10); yield 15% | PRE |
| Regex cause links are usable labels | **No (33% precise)** | 5 of 15 checked sentences assert a cause | EXP |

## 4. The owner's picture, point by point
- **"A set of conserved features across time, the pipes."** Supported at the function level: born solid, few deaths, movers move once. Conserved per unit, not in aggregate (the repo grew 22x in eight months).
- **"Growth corresponds to new functions."** Supported: births dominate (3,861 births, 116 deaths); the scanner core grows by thickening existing hubs, the translator by new files (72% of fleet-era births).
- **"The system moved from scanner to translator."** Supported: translator code 0% -> 9% of lines, tests 0% -> 71%.
- **"What drives behaviour is the configs and regexes, the structure is blind to them."** Half supported. Cost steps do not follow function structure by size or direction (a +1 complexity edit gave x3.3-x5.7; a 10-line shrink gave +15%), and no step came from a pure pattern-table commit. But the steps are not quiet in the sense we expected: most come from code commits touching several functions. Regexes also live in code (hundreds of `re.compile` sites in the scan path), which we could not separate from other code. YAML and config files were not in the scan path and showed nothing.
- **"Most regressions are in the regex, so we are blind to them."** Not supported as stated; see above.
- **"Fixes have low structural change."** Not supported: fix commits cause steps at their base rate and usually make the engine slower.
- **"The testing pipeline makes it less likely to regress."** Consistent, not demonstrated (section 5).

## 5. Tests and regressions
Descriptive support: tests accompany 92% of engine-code PRs (93% of fix PRs); 1 revert in 6,363 commits; 114 merged PRs (1.8%) were flagged with a real failure at the PR stage; fix edits per week stayed flat (about 146 in July-September, 153 in October-November) while the engine grew from about 330 to 4,079 functions, roughly an 8-fold fall per function (confounded: young code has had little time to be repaired); two models judged 69-81% of bug issues pre-existing, so bugs found are mostly latent gaps in a heuristic engine, not recent regressions.
Against, or unanswered: 161 checks failed on `main` in October-November (flakes included); 37% of repairs were fixes of fixes within about 2 days; there was never an era without tests; unit-test attachment is near-universal, so the test-attachment comparison has little power and the lead model is as strong as the lag; and speed is not gated at all: 35 steps in eight months, 21 of 46 step pairs above 25%, 13 above 50%, 4 above 100%.

## 6. What surprised us, and what we got wrong
- The three steps we traced first (a threshold in a function, a file-screening rule, a comment-stripping rule) looked like quiet policy edits; over 35 steps the opposite holds.
- The "7.6x step" is the largest piece of a cluster: on 2026-09-26..28 at least five steps (UAX #31 identifier classes +79%, a partial repair -22%, a precompile change -12% on the mainframe corpus, then #3929 +230% to +487%).
- The November "drift" is one +12% step at one commit.
- A large part of the apparent change in cost is the engine scanning less: the vendored-tree screen cut files mapped from 3,389 to 991 (-72% CPU on language-crucible) as an intended output change.
- The engine was broken for a stretch on these inputs (a TypeError at five commits, 2026-04-19 to 05-01); across that window the cost moved +13% to +30% on all four corpora and cannot be attributed.
- Corrections made along the way: "26 independent cause pairs" was about 8-10 (regex precision 33%); the performance-word count fell from 277 to 209 subjects (a missing word boundary); the blame-derived repair pairs are circular and were not used for the radius; scans of a `git archive` and of a git checkout differ (the archive loses `pyproject.toml`); delta scans differed from full scans in file set, folder grouping and excluded artifacts (fixed in gitgalaxy#8775, merged main, all checks passing); the engine's stage timers are wall time, its regex report lists only the top 15, and neither covers where the biggest step lived.

## 7. What the reviews changed
A design review (Claude and Gemini 4 Neon) dropped three hypotheses as hypotheses, merged two, and required a noise floor, provenance and fresh data. A code review of the analysis scripts (both models) found two defects in the refinement code (a bisection that never probed the first commit after the lower bracket: 8 of 22 non-localised results ended there; a rounded threshold that sent the E1 bracket to the wrong metric), a persistence rule that counted invisible steps and made "elevated at tip" automatic, a stratification gap in the quiet test, and the keyword-regex flaw. A second refinement pass flipped 7 results to localised. All three reviews found things the author's own checks missed.

## 8. What this means for the engine
- A speed canary on engine-core PRs would have flagged most of the 23 up-steps (promoter-bot#125): CPU seconds, three small corpora plus language-crucible, 10% threshold above a measured 5% noise.
- Write the cause when the issue is filed (promoter-bot#124); free-text causes are rare and the retrospective labelling is conservative.
- Repair effort concentrates in a few places (`_slice_by_braces` in `core/detector.py`, 41 fix commits); these are the accuracy frontier of a heuristic parser, not ripple from earlier changes.
- The unit tests and golden masters turn output changes into explicit decisions (the screen change was one), but say nothing about cost.

## 9. What we still do not know
Whether tests lower regressions (needs an era or a design that varies the pipeline); how many of the 23 cost increases were intended; the cost across the April crash window; whether the compile-policy cost in small many-language scans matters to any user; anything about steps below 10% or in corpora we did not time; whether the structural patterns (born solid, hubs persist) survive past eight months and outside agent-written code. The labelled causes (10 agreed pairs) are too few for a radius test, and the owner's own labels of about 50 issues would be the real gold.

## 10. Where things are
Temporal-crucible draft PR #187 (branch `self/gitgalaxy-history-draft`): `docs/self_hypotheses_draft.md` and `_amendment_1.md`; plans `self_sensitivity_plan.md` (with Amendments 1-2), `self_lattice_and_radius_plan.md`, `self_test_attachment_plan.md`, `self_cause_labeller_pilot_plan.md`; results under `docs/self_evolution/` (report, comparison with the 19 reference repos and DPDK, lattice, radius, test attachment, gate feasibility, labelling) and `docs/self_speed/` (grid, events, pilot, final report with figures). Instruments: `tools/selfhistory/`. Issues: gitgalaxy#8774 / PR #8775, gitgalaxy#8715 (the evolution epic), promoter-bot#124 and #125.
