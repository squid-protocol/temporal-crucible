# `gitgalaxy backtest`: design note (separate from the evolution report)

Decision 2026-11-19 (owner): the reliability panel is not part of the evolution report; it is its own command. The report only points to it.

## What it answers
"How well do GitGalaxy's lists work on **this** repository's own history?" It replays the repository's past and scores the lists against what really happened, then states the result with an interval.

## Inputs
- Git history (required). Quarterly scans (required for the call-graph lists).
- Known causes: `Fixes:` trailers, else blame on a sample (as in the evolution report). At least about 50 pairs are needed; below that the command says so and reports nothing.

## What it measures (each with a 95% interval over pairs)
1. **Regime**: the median recency rank of the true cause (1 = most recent change). Rule from the research: at most 30 is the fast regime (use recency), otherwise the slow regime (use the neighbourhood list). In our data the two regimes were 100 times apart (7 to 11 against 1,500 to 2,200).
2. **Reverse triage**: given a repaired function, the share of repairs whose causing commit is in the top 1, 5 and 20 of the candidates, for recency, file overlap, and the neighbourhood list (research: DPDK 79.0% top 20 against 2.3% recency and 60.7% file overlap; OSS-Fuzz four projects: recency 78.1% against 34.2%).
3. **Bisect saving**: expected tests to isolate the cause with a bisect weighted by the chosen list, against plain bisect (research: 6.4 against 14.7, DPDK and Mesa pooled).
4. **Forward list ("where to look first")**: after a change, the share of later repaired functions in the top 20 (research: about 45% on C, 25 to 30% on Python and Go).
5. **Detection channel mix**: where the repository has `Cc: stable`, `Reported-by` or a fuzzing history, the lag per channel (a project can be bimodal: DPDK 371 against 20 days).

## Output
A scorecard (JSON and a short HTML section), cross-fitted by halves so the repository is not scored on data it was tuned on, with a one-line verdict per list ("use recency first", "the neighbourhood list is right 4 times in 5 here"). Never a score without its interval or the number of pairs.

## Reuse
Existing research tools: `triage_reverse.py`, `lag_window.py`, `lag_fusion.py`, `ossfuzz_triage.py`, `suspects_mockup.py`. The regime switch is `lag_fusion.py` SWITCH.

## Open
How the command is exposed (a subcommand beside `lookfirst`); whether it caches the replay; whether it publishes a repository's score to a shared reference band.
