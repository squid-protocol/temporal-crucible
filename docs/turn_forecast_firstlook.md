# TURN forecast: first look (work branch `turn/forecast`; not part of PR #186)

**Question.** How predictable is a function's next change? Target: a surviving function changes (identical engine measurements to its current state) or dies within h quarters, h = 1 and 4. Six held-out repos, quarterly, forward-in-time split (train on the first 60% of snapshots with the target window closed before the test period; test on the rest). Gradient-boosted trees, strongly regularised, one split, one model: a first look, not a ceiling.

**Ladder.** R0 age and size; R1 + persistence (changed last quarter, quarters since last change, the repo's recent event rate); R2 + structure (complexity, arguments, keyword densities, in/out degree); R3 + git process (commits and authors on the function's file in the last quarter, share of the file's functions that changed, file size).
Skill = Brier skill over the repo's most recent observed event rate (a persistence baseline); AUC = ranking quality.

**Result (tools/turn/forecast.py, 2026-11-16).**
* Ranking is above chance but modest: AUC 0.5-0.8 (best: libxml2 0.79 with persistence; prometheus 0.72; expat, scapy, sphinx and commons-io 0.5-0.68).
* Skill over the recent-rate baseline is small and inconsistent: roughly -10% to +16% at h = 1 and -29% to +35% at h = 4, with no rung that wins in every repo. Most positive values come from calibrating a stale training-period rate, not from added features.
* Against the constant training-period rate (the first run) most models scored below zero: event rates are bursty (sweeps), so the base rate in the training window is a poor guide to the test window. The repo-level event rate carries most of the predictable signal; function-level features add little on top in this first pass.

**Caveats.** One split per repo; no hyperparameter search; targets mix changes caused by sweeps with organic edits; git features are file-level, not function-level; six repos; events are rare (4-11% per quarter) so intervals on skill are wide and were not computed. Treat the AUC ranges as a first estimate of how hard the problem is, not a ceiling.

**Next.** Separate sweep-caused from organic changes as targets; add function-level authorship; leave-one-repo-out transfer; bootstrap intervals; a learning curve (rows and repos) to estimate where skill stops improving; horizon curve (1, 2, 4, 8 quarters).
