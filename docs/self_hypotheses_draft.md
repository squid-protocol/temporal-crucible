# GitGalaxy-on-itself: structure-function hypotheses (DRAFT, unregistered, local only)

Status: EXPLORATORY DRAFT, NOT REGISTERED. Nothing here is in `docs/HYPOTHESES.md`; no verdict is claimed. Draft for the hypothesis-first register (temporal-crucible `docs/HYPOTHESES.md`). Pushed as a draft PR on 2026-11-20 at the owner's request.
Per STUDY_CHECKLIST item 15 it needs two independent design reviews and a dated amendment before it is registered.
Written 2026-11-20 by Claude from owner direction in session; owner supplied the domain claims marked [owner].

## Data and what has already been seen (exploratory, labelled so)
- 180 daily full scans of GitGalaxy (checkout scans, engine at HEAD of the scan day's tree), `dbs/`; 12-slot engine speed runs
  on three fixed targets (keyword-rosetta, cics-crucible, language-crucible), per-stage and per-regex timers, CPU seconds
  (`docs/self_speed/runs.jsonl`, summary in `docs/self_speed/rep_summary.md`); full commit list, commit messages and PR/bot comments (not yet pulled).
- Already looked at before drafting (so these are discovery, not confirmatory): speed table rep 1 (keyword-rosetta 0.79 s -> 4.61 s
  between the 2026-09-16 and 2026-10-02 engines; language-crucible Optical Detector 118 s -> 35 s between 10-02 and 10-18; files mapped
  3,366 -> 991 over the same window); pattern-table code (`standards/`) 37% of code lines on 03-21 and 7% on 11-20 with 0-7 functions
  per kLOC vs 30-70 elsewhere; `detector.py` 1,014 LOC / 29 functions -> 6,995 / 180, mean function size 35 -> 59 -> 39;
  `galaxyscope.py` 51 -> 87 -> 47; translator code 0 -> ~9% of lines; tests 0 -> 71%.
- Known instrument facts: delta scans are NOT used (they differ from full scans; fix is gitgalaxy PR #8775, issue #8774, not yet merged); daily scans were run four at a
  time so their wall times are not speed data; the engine screens files differently over time, so repo-level times are not comparable
  without per-file normalisation.

## Claims from the owner [owner], to be tested rather than assumed
GitGalaxy's function structure changes fast and is fluid; most speed regressions live in regexes, which are data in pattern tables
and not functions, so function-structure measures are blind to them [owner]; fixes therefore show low structural change [owner];
feature growth gives many function births and features change scope [owner]; the system moved from scanner to translator plus
structural fingerprinting, so growth lands on an established hub [owner].

## Hypotheses (each: claim, measure, prediction, what would refute it)
SF-1 REGEX BLINDNESS. Speed step changes localise to commits that touch pattern tables / rule definitions, not to commits that change
  function structure. Measure: for each pair of adjacent speed slots, share of the change in stage cost explained by (a) functions
  born/changed in the engine code vs (b) lines changed under `standards/` and rule files. Predict (b) explains more than (a) in a
  majority of intervals with a >25% step. Refuted if function-structure change explains at least as much.
SF-2 FIXES ARE STRUCTURALLY QUIET. Commits labelled as perf/regex fixes (message + PR label) change fewer functions than feature
  commits (median <= 2 functions) while changing as many or more lines in pattern tables. Refuted if fix commits touch as many
  functions as feature commits.
SF-3 FLUID, FEATURE-DRIVEN. Function births track feature issues opened; survivors settle in more slowly than the 13 TURN repos.
  Measure: share of functions identical to birth after 4 quarters-equivalent (use 4 months; unit to be justified) vs TURN range
  59-89%. Predict below 60%, near tigerbeetle (59% at 4 quarters, young and fast). Refuted if within 75-90%.
SF-4 HUB THICKENS THEN SPLITS. Established hub files (`detector.py`, `galaxyscope.py`) first gain mean function size, then lose it
  as functions are extracted, at feature-scale thresholds; WRF (Fortran) thickens without splitting (79 -> 120 LOC per function,
  complexity 9.9 -> 15.7) and the large C repos hold size flat (mesa 27 -> 28). Predict GitGalaxy hubs peak then fall (as seen on
  two files; confirm on the ledger and on all files above a size bar). Refuted if hub mean size rises monotonically like WRF.
SF-5 GROWTH ON AN ESTABLISHED HUB. A larger share of births land in existing files than in TURN (27-33%), and new translator code
  wires into the scanner core at birth (cross-file callers at birth above the LAW-2 kernel; TURN H4 median 1.37). Predict
  existing-file births > 40% and translator-to-core fan-in rising over time. Refuted if births in new files stay 66-73%.
SF-6 STRUCTURE ADDS LITTLE TO SPEED BEYOND SIZE, UNTIL PATTERN TABLES ARE COUNTED. Model stage cost per mapped LOC on code size and
  function complexity; then add pattern-table descriptors (regex count, alternation size, nested quantifiers, per-regex telemetry
  from `--splicing-speed`). Predict function structure adds < 0.05 R^2 over size; pattern-table descriptors add >= 0.15. Refuted
  otherwise. (This is the size-confound wall; same control as repowise-bench.)
SF-7 CONCENTRATION IN FEW REGEXES. The top 3 regexes hold > 50% of regex time per target (keyword-rosetta today: one regex holds
  about half). Predict stable across engine versions, with the identity of the top regex changing at speed steps.
SF-8 O(N^2) -> O(N) DETECTABILITY, THREE TIERS. (a) Timing: fit stage cost against repo size at 2-3 target sizes per engine version;
  a refactor shows as a drop in the exponent. (b) Structure only: no current column carries loop nesting, so predict structure-only
  detection AUC <= 0.6. (c) History text: commit messages / bot comments mentioning O(N), quadratic, precompute, set/dict lookup
  precede exponent drops with high recall, low precision. Ground truth: the owner's list of known refactors (needed; not yet
  collected). Refuted if (b) already finds them, or if the exponent fit misses most of the owner's list.
SF-9 SCOPE CHANGE SHOWS AS IN-PLACE CHANGE. Features that changed scope show as keyword-family change at unchanged function length
  (TURN: 11-62% of first changes), and as mass migrations (sweeps) in the engine; predict sweep share of code edits above the TURN
  median (22%) because rule definitions are renamed and re-tiered together. Refuted if below 10%.
SF-10 INSTRUMENT CONTROL. Cost per mapped LOC (CPU seconds) varies less across engine versions than raw pipeline seconds, because the
  file screen changed; report both and never compare raw times across a screen change.

## Controls required before any of this is scored
Repeat runs (3) with CPU seconds as the load-robust measure; provenance check per engine (no module from the live checkout);
targets pinned; full-vs-delta scans never mixed; sweeps removed or reported beside every in-place-change estimate; two independent
design reviews; the exploratory numbers above are not reused as confirmation.

SF-11 ORCHESTRATORS ARE HUBS [owner prediction]. GitGalaxy's orchestrator module(s) are hubs, and the owner's two other orchestrators
  (names to be confirmed by the owner when the second and third repos are added) will be hubs in their own repos. Measure: file-level
  fan-in and fan-out concentration (top-1% share, as in the TURN hub tables) and hub persistence (top-5% a year later; TURN range
  94-98%) for each orchestrator file against the repo's other files, size-matched. Predict each orchestrator is in the top 1% by
  fan-out and top 5% by pagerank for most snapshots, with persistence at or above the TURN range. Refuted if an orchestrator is
  not in the top 5% on either measure, or if hub rank is explained by size alone. Note the quick pagerank check on 2026-11-20 picked a
  re-export `__init__.py` or a vendored script as the top hub, so hub rank must be computed over engine code with re-exports and
  vendored files excluded (a declared exclusion, set before scoring).

## Decisions and open inputs (owner, 2026-11-20)
1. No remembered dates for the speed-up refactors. Ground truth for SF-1/SF-8 therefore has to come from the data: candidate steps are
   the speed-step intervals found by the exponent fit plus commits whose message or bot comment names an algorithmic change; the owner
   confirms or rejects each candidate afterwards. This makes the ground truth post-hoc: SF-8 is exploratory unless the candidate list is
   frozen before the commit text is read.
2. No new time slots yet. Hold at the 12 slots and 3 repeats until the first results are read; more time points later.
3. Hub files assumed `detector.py` and `galaxyscope.py` until the owner says otherwise (SF-11 adds the two other orchestrators).
