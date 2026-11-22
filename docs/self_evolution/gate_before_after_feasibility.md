# Before/after a dated gate: is the natural experiment there? (feasibility probe; EXPLORATORY; 2026-11-20)

Proposed in `tests_and_regressions_quick_look.md`: compare a subsystem's repair rate before and after a dated golden or crucible gate, against matched subsystems. The probe below asks whether such events exist in GitGalaxy's history. Data: `lang_gates_explore.json`.

## What the history offers
Subsystem candidates are the 79 per-language rule files (`gitgalaxy/standards/language_standards/languages/<lang>.py`). Per-language gates: 68 strict extraction tests (`tests/extraction/languages/test_<lang>_strict.py`) and 29 crucible accuracy baselines (`tests/tree_sitter_accuracy_baseline_<lang>.json`).
- The per-language files themselves are born in one refactor in August (59 of 79 first appear that month; before it the rules lived in one monolith file), so file histories have almost no pre-period (0 fix commits before the gate).
- The gates arrive with the subsystem or all at once: 46 strict tests on 2026-08-05, all 29 accuracy baselines on 2026-08-10/11, and the later ones (8 in September, 6 in October, 8 in November) are added together with a new language's file, tests and corpus. No language gets a gate later than its code except by days.
- So there is no per-file before and after and almost no staggering to compare. The one usable contrast is a single date, 2026-08-10, with 29 languages that gained an accuracy baseline and 50 that did not (they had strict tests or none), if fixes are attributed to languages by name in the commit subject.

## Descriptive attempt (not a test)
587 fix commits; 273 name exactly one language in the subject (by month: Mar 1, Apr 1, Jul 51, Aug 167, Sep 43, Oct 7, Nov 3). Fix commits naming a language, before and after 2026-08-10: languages with a baseline 38 -> 148 (per week 1.9 -> 10.1); languages without 28 -> 59 (1.4 -> 4.0). Ratio of the two before-and-after ratios 1.85, approximate 95% interval 1.04 to 3.28 (Poisson counts only).
The sign is the opposite of "gates reduce repairs": language fixes rose more for the languages that got the accuracy baseline. This is what a measurement gate does: it reports how far each language is from the reference parser and starts a fixing campaign (August has 167 of the 273 events). It also means the treated languages were chosen because a reference comparison exists. Fix commits cannot separate regressions from newly found accuracy gaps (two models judged 69-81% of bug issues pre-existing).

## Conclusion
The proposed before/after test is not identifiable here: gates and subsystems appear together, the only dated gate is a measurement gate that generates repairs, and the outcome mixes regressions with discoveries. Reported as a negative feasibility finding, not a result about tests.

## What would be informative instead
- Regression detection and repair latency by dimension: correctness is gated by tests and goldens, speed is not. Correctness repairs have a median lag of 9.9 days (cause 'fix': 2.0 days; 464 blame-derived pairs); the speed steps found (the compile-policy threshold since 2026-09-27, the comment-stripping cost since 2026-08-10) are still in the engine, and the sensitivity pass will give the share of steps that were later reversed and how long that took. The contrast is unmatched (speed is less visible, severity differs) but it is the within-repo difference a gate makes.
- Prospective data: the structured `Introduced by:` / `Regression of:` lines and the speed canary proposed in promoter-bot#124 and #125 would make regressions and their detection point countable per gate from now on.
