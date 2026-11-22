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
277 of 6,695 commit subjects (4.1%) match a performance keyword list; 72 of those (26%) touch scan-path code or pattern tables, the rest are CI, docs and test-timing commits. CORRECTION (2026-11-20, from an independent review): the keyword pattern lacked a closing word boundary (it matched PERFORM, FastAPI and the lint rule PERF401) and had a trailing-space bug; with a corrected pattern ('batch' also dropped as noise) the count is 209 subjects (3.1%), 54 of them (26%) touching scan-path code or pattern tables. The culprit commit of the 7.6x step is still not flagged.
The commit that caused the 7.6x step (`6b604f91a`) is NOT among the matches (its subject says pre-compile, small scans, 30% win; no keyword fires). One miss, so no recall estimate.

## Method notes
Provenance of every engine run is checked (no module loaded from the live checkout); March-2026 engines needed their hard-coded output directory redirected; the 2026-05-26 engine prints "files mapped" where others print "stars mapped" (parser fixed in this branch).
Reproduce: `tools/selfhistory/join_steps.py`, `bisect_cost.py` (needs the private mirror and targets described in the README; the one-file-per-language corpus is built from keyword-rosetta `data/<lang>/` by taking the first file of each).

## 5. The other three bisections (language-crucible CPU seconds, one probe per commit, boundary re-checked with 2 repeats)
- **2026-10-02 -> 10-18, CPU 332 s -> 93 s at the boundary:** commit `14fc9c7a5` (#5512, "aperture: vendored trees under any name"; +39 lines in `aperture.py` and two small edits).
  Files mapped fall 3,389 -> 991 at that commit. This is the engine scanning less, not scanning faster: it blocks 2,757 files of the benchmark corpus itself as "Hidden Directory, or Dynamic Ignored Dir"
  (each `data/<language>/` folder holds a cloned third-party project, which the new rule treats as vendored). A whole-repo scan of language-crucible now sees 43 of 66 language folders.
- **2026-07-27 -> 08-13, CPU 130 s -> 176 s:** two steps of about 15% each, files mapped unchanged within each. One is pinned to `89d86da58` (2026-08-10, #1234, "prevent Prism from swallowing code due to quotes in comments"):
  parent 149.9 s vs commit 173.3 s (2 repeats each), files mapped 2,945 both. A correctness fix that makes the engine read code it previously skipped, so cost rises. The first step (131.7 -> 150.6 s) lies between two probes 42 commits apart and is not localised.
- **2026-11-04 -> 11-20, CPU 68 s -> 96 s:** NOT localised. Probes rise gradually (72.7 -> 80.2 s over 2026-11-09..11) and the boundary check did not confirm a step (parent 84.7 s vs found commit 79.1 s; the threshold crossing is inside the noise, about 4-6% at this load). Treat as drift.

## 6. Functions and files per language in language-crucible (pinned v1.7.0; today's engine, each `data/<language>/` folder scanned as its own target)
The whole-repo scan is screen-dependent (section 5), so the per-language counts use one scan per folder: 66 folders, 3,736 files on disk, 3,364 mapped, 52,820 functions, 1,047,248 code lines, 372 excluded.
Largest by functions: cobol 11,430 (585 files mapped), typescript 8,471 (52), python 3,905 (305), zig 3,542 (41), rust 2,127 (57), c 2,096 (40), cpp 1,765 (45), dart 1,750 (8), php 1,707 (42), assembly 1,525 (236).
Functions per mapped file range from 3.6 (groovy) and 3.8 (powershell) to 162.9 (typescript) and 218.8 (dart). 13 folders yield zero functions (blueprint, db2_sql, hlo, json, markdown, mlir, plaintext, proto, protobuf, sqlite, tabular, td, text): data and markup, as expected.
Detection quirks visible in the table: the `dockerfile` folder is mostly detected as go (55 of 61 mapped files); several folders carry a few markdown/plaintext files. Full table: `join/language_crucible_perdir.json` (also per detected language); the whole-repo comparison for the 2026-10-02 and 2026-11-20 engines is `join/language_crucible_by_language.json`.

## 7. Dense timing and structure around each found commit (EXPLORATORY; 15 commits: parent, commit, +1, +3, +10 per event; 4 corpora x 2 repeats; repeat spread 1.2% median, 5.4% max)
CPU seconds, median of 2 (keyword-rosetta / cics-crucible / one-file-per-language / language-crucible):
- E1 #3929 (`6b604f91a`): parent 10.9 / 9.4 / 5.3 / 283; commit 35.8 / 9.5 / 30.2 / 283; held through +10 (36.1 / 9.7 / 30.2 / 284). Only many-language small scans move (x3.3 and x5.7); the 763-file and 3,366-file corpora do not.
- E2 #5512 (`14fc9c7a5`): language-crucible 330.5 -> 92.5, files mapped 3,389 -> 991, held through +10; the other three corpora move by under 7%.
- E3 #1234 (`89d86da58`): language-crucible 149.4 -> 171.8 (+15%), files mapped unchanged; the other three corpora do not move.
Each event is one sharp, persistent step at exactly the named commit with nothing before or after it, and each affects only the corpus class its mechanism touches.

Structure at the same commits (full scans of the parent and the commit; `join/event_structure_pairs.json`):
- E1: one engine function changed, `_extract_features_parallel`: 203 lines -> 203 lines, complexity 28 -> 29 (+9/-1 source lines); 0 engine functions born.
- E2: 3 engine files, +31/-18 lines; 2 engine functions born (`_license_family`, `is_container_name`), 3 changed by -3 to +2 lines.
- E3: one engine file (`prism.py`); `_strip_segment_comments` went 74 -> 64 lines (complexity 9 -> 10) and a callback 4 -> 9 lines. The function shrank by 10 lines while the cost of a scan rose 15%.
Reading (n = 3, selected because each was a large step, so no rate is implied): the size of the speed step bears no relation to the size or direction of the function-level change (a +1 complexity edit gave x3.3-x5.7; a 10-line shrink gave +15%; two new helpers
gave a 70% cut in files scanned). In all three the cause is policy or data reaching the code (a threshold, a screen, a comment-stripping rule), not function structure. This is a descriptive observation that motivated SF-1, SF-2 and SF-6, not a test of them.

## 8. What has been scanned (as of this note)
Structure scans (full scan of a commit, today's engine): 195 distinct commits (180 daily + 15 around the events). Timing (each commit's own engine on the pinned corpora): 58 distinct commits (12 grid + 15 events + 38 bisection probes, with overlaps),
256 logged runs plus 44 bisection probes; 27 commits have both. Of 6,700 first-parent commits: 0.87% timed, 2.91% structure-scanned.
