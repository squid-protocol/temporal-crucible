# What changes move the engine's output, quality and speed? (EXPLORATORY; plan `docs/self_quality_structure_plan.md`, fixed before these numbers; 2026-11-20; Q2 still running)

Questions from the owner: do structure changes we can see correlate with engine quality (functions found per language), output and speed; do we have causes for the speed-ups; can the same be done for the language-function enhancements. Data: `structure_function/` here, `docs/self_speed/`.

## Q1: does speed co-move with output volume? Declared prediction (rho at least 0.3) NOT supported
Across 283 consecutive sampled commit pairs on language-crucible (284 runs), the Spearman correlation between the change in log CPU and the change in log functions found is +0.07 (n = 279 after excluding 4 pairs where files mapped moves by more than 3%; p = 0.26); all pairs +0.10; call edges +0.03; magnitudes +0.02. Of 18 pairs with a CPU change above 10%, functions found moved by more than 2% in only 3; of 265 pairs where output was stable, 15 had a CPU change above 10%. Cost steps are mostly not "more work, more output".

## Q3: causes of the 35 speed steps (two models labelling the mechanism from the commit text and change summary, blind to direction and size; agreement 77% exact, kappa 0.72, 100% counting secondary tags)
| mechanism (Claude / Gemini) | down | up |
|---|---|---|
| optimisation | 5 / 7 | 2 / 2 |
| correctness fix | 4 / 2 | 7 / 4 |
| new feature or rule | 2 / 2 | 6 / 7 |
| screen or skip | 1 / 1 | 2 / 4 |
| infrastructure, other or unknown | 0 / 0 | 6 / 6 |
Declared rule (at least half of the 12 down-steps are optimisations): Claude 5 of 12, Gemini 7 of 12; both agree on 5 (the clear perf commits), so the conservative reading is not met. The two extra Gemini counts are fixes that remove a pathological slowdown (the ReDoS timeout fix, -64%; "fix the three red legs of the Full Suite Gate", -30%). Roughly 40-60% of speed-ups are deliberate optimisation; the rest are fixes to bad behaviour, one file-screen change and a few feature commits. Up-steps are mostly new features or rules and correctness fixes; two "optimisations" cost time (#3929 and a required-literal prefilter); 6 up-steps are non-engine commits (docs, tests, merges), probably noise or side effects of an earlier step.

## Q4-Q6: engine quality per language against tree-sitter (the repo's CI history: 9,194 rows, 53 languages, 233 measured commits since 2026-08-11)
- 149 quality steps (function recall moves by 1 pp or functions found by 5%): by month 123 in August, 22 in September, 4 in October, none after. The engine's measured accuracy was built in a campaign in August-September and has been flat since.
- POST HOC split (not declared): in 63 of the 149 steps the corpus's own real function count moved by 1% or more between the two rows, so the change is the crucible changing, not the engine; 86 steps are engine-only (net +18,388 functions found; recall steps above 1 pp with the corpus unchanged: 45, of which 42 up and 3 down; engine-only steps by month: August 67, September 18, October 1). Largest engine-only steps: COBOL +8,597 (2026-08-30) and +1,418 (08-28), assembly +1,017, LiveCode +933, Ada +922, and a COBOL drop of 832 (09-19). Net across all steps +28,790: corpus-change steps +10,402, engine-only +18,388.
- Q4a (declared: at least 60% of quality steps have a commit touching that language's own rule file in the window): NOT MET, 15 of 149 (10.1%). But 120 of the 149 steps precede the per-language rule files (first one 2026-08-31; before that all rules lived in one monolith counted as core), so they have no language-file commit by construction. Post-split only: 15 of 29 (51.7%), still below 60%; against a permutation base rate of 8.4% (4.0% for all steps) the language files are heavily over-represented.
- Windows are short (median 4 first-parent commits) but almost never a single commit (1 of 149): causes for 148 steps need localisation scans (re-running one language folder at each commit in the window, seconds each).
- Q4b: 5 measured commits move five or more languages at once (17, 6, 7, 7 and 5 languages); four touch core files (`language_lens.py`, `core/aperture.py`, `core/guidestar_lens.py`, `galaxyscope.py`, the monolith). Summing positive deltas by window composition: windows with core changes 12,164 and engine-wide commits 17,169; language-file-only windows 4. Most improvement co-occurs with core or engine-wide changes (window co-occurrence, confounded by the monolith).
- Q5: 8 of the 35 speed events lie inside a quality-step window (14 precede the first measurement); none is a measured commit itself. Up-events with functions found up 6; down-events with functions found up 2; none with found down: two "faster and finds more" cases. Counts only.
- Q6 (rule count against functions found or recall, predicted rho at least +0.2): NOT SUPPORTED, underpowered: the rule count changed in only 1 of 28 steps with a rule-count change available (77 of 1,986 consecutive pairs); pooled rho -0.01 (found) and 0.00 (recall); across languages at the tip rule count against recall -0.16 (n 29); against functions found +0.52, but the control (against the real function count) gives +0.56, so it tracks corpus size.
- The call-resolution, graph-coverage and ground-truth series do not share measured commits with the quality series (4 of 43, 0 of 13, 5 of 56).

## Q2 (pending)
Re-timing of the parent and the commit of each speed step with output counts (does a speed-up change what is found?): `speed/event_outputs.jsonl`, 26 of 140 runs at the time of writing; the result will be added to this file.

## What this says so far
Speed and output volume are decoupled at the commit level; the speed steps are a mixture of intended optimisation, fixes to pathological behaviour, and new capability; the engine's per-language accuracy gains arrived in one campaign and are carried mostly by core and engine-wide commits (before the rule files were split out), with language files over-represented once they exist; and rule counts do not predict quality across this history. The most useful next step is a localisation pass: re-scan a language folder at each commit of the window of each of the 86 engine-only quality steps to name the cause commit, then label mechanisms as for the speed steps.
