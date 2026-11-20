# Speed steps joined to commits: first findings (EXPLORATORY, not registered)

Data: `docs/self_speed/runs.jsonl` (12 engine time slots x 3 pinned corpora x 3 repeats), `join/steps.md|json` (per-interval join), controls in `join/`.
Speed = CPU seconds per mapped file (CPU seconds repeat at ~1% spread; wall seconds do not). Intervals are 11 gaps between adjacent slots (69-1,902 commits each).
Everything below was looked at to build the hypotheses in `docs/self_hypotheses_draft.md`; none of it is confirmation.

## 1. Interval-level join is weak (n = 11)
Spearman rho of |log speed step| (largest over the 3 corpora) against what changed in the interval: pattern-table lines changed +0.11 (total CPU) / +0.17 (per file);
scan-path lines changed +0.27 / +0.29; scan-path functions born +0.47 / +0.37; functions born+died+changed +0.42 / +0.34; translator lines +0.36 / +0.14; commit count -0.02 / -0.21.
With 11 intervals none is distinguishable from zero. Intervals of hundreds of commits also hide steps that cancel inside them. SF-1 is neither supported nor refuted here.

## 2. The sharpest step was traced to one 10-line change (bisect + A/B)
keyword-rosetta CPU 5 s -> 41 s between the 2026-09-16 and 2026-10-02 engines (7.6x per file) while the per-file stage totals moved by about 6 s: the cost was outside the stage timers.
Controls: a 6-file repo costs 1.8 -> 2.3 CPU s (fixed cost +0.4 s only); a 51-file repo with one file per language costs 2.3 -> 33.6 CPU s and stays at 34-37 s through the 2026-11-20 engine.
So the cost scales with the number of distinct languages, not with files. Bisect over the 685 first-parent commits (`join/bisect.out`, 2 repeats per probe) names
`6b604f91a` (2026-09-27, #3929: "pre-compile before a fork only for scans of 500+ files"; +9/-1 lines in `gitgalaxy/galaxyscope.py`, plus test-harness edits).
Direct A/B, parent vs commit (`join/ab_3929.jsonl`, 2 repeats): keyword-rosetta CPU 10.9 -> 36.4 s, wall 4.2 -> 5.0 s; one-file-per-language repo CPU 5.3 -> 29.9 s, wall 2.9 -> 4.3 s;
cics-crucible (763 files, above the threshold) unchanged (9.4 -> 9.4 s). Reading: below 500 files each worker now compiles lazily the rules for every language it meets, which for a
many-language small scan multiplies the compile work across workers. The commit's own A/B covered a 40-file C scan and a 3,280-file corpus, not a many-language small scan.
It is still present on 2026-11-20. This is a measurement of this engine on these inputs; whether it is worth changing is the owner's call.

What it shows for the draft: a change of ten lines in one function (structurally quiet: SF-2), a regex-compile policy rather than a pattern-table edit (SF-1's "regexes are where the cost is"),
invisible to `--file-speed`/`--splicing-speed`, which time per-file work only (so SF-6's blind-spot argument has a concrete instance). One instance proves nothing about rates.

## 3. The other big step is not explained
language-crucible CPU 288 s (2026-10-02) -> 65 s (2026-10-18): every stage falls to 0.1-0.3x and files mapped fall 3,366 -> 991, i.e. the file screen changed. Not bisected.
Per mapped file the cost went 0.029 s (2026-03-21) -> 0.086 s (10-02) -> ~0.07-0.1 s (11-20): per-file cost has risen about 2-3x over the period.

## 4. Commit-text screen (SF-8 tier c), one count
277 of 6,695 commit subjects (4.1%) match a performance keyword list; 72 of those (26%) touch scan-path code or pattern tables, the rest are CI, docs and test-timing commits.
The commit that caused the 7.6x step (`6b604f91a`) is NOT among the matches (its subject says pre-compile, small scans, 30% win; no keyword fires). One miss, so no recall estimate.

## Method notes
Provenance of every engine run is checked (no module loaded from the live checkout); March-2026 engines needed their hard-coded output directory redirected; the 2026-05-26 engine prints "files mapped" where others print "stars mapped" (parser fixed in this branch).
Reproduce: `tools/selfhistory/join_steps.py`, `bisect_cost.py` (needs the private mirror and targets described in the README; the one-file-per-language corpus is built from keyword-rosetta `data/<lang>/` by taking the first file of each).
