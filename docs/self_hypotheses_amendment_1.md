# Amendment 1 to the GitGalaxy-on-itself draft: reconciliation of two independent design reviews (2026-11-20)

Status: DRAFT amendment by the author (Claude); not registered; needs the owner's acceptance. It governs `docs/self_hypotheses_draft.md` where the two differ.
Reviews: (R1) Claude (Fable), read-only, via the Agent tool; (R2) Gemini 4 Neon (high), read-only, via agy. Same brief (`docs/self_hypotheses_draft.md` + the findings note + tools + data), no author conclusions in it,
both forbidden to compute predictor-outcome associations. Their full texts are in the session transcript; this file is the reconciliation, as STUDY_CHECKLIST item 15 requires.

## Facts both reviews found (all checked by the author against the files before this amendment)
1. `--splicing-speed` prints only the top 15 regexes (`galaxyscope.py:4059 [:15]`) and never the total; regex time is 2-23% of CPU. SF-7 as written is inflated by truncation.
2. Stage timers are per-file wall time under load, not CPU: their sum exceeds total CPU in 8 of the timed runs and misses most of E1's cost (it sits in worker start-up and lazy compile).
3. No run was ever on a quiet box (`wait_quiet` has `max_wait=0`; load 3-16). The "1% spread" is within one session; no commit was timed in two sessions.
4. SF-11 is false by arithmetic (about 108 scan-path engine files at HEAD, so the top 1% is one slot; R2: under 300 non-init engine files on 144/180 snapshots).
5. Leakage: SF-1, SF-2, SF-4, SF-6, SF-7 and SF-10 were written after seeing the numbers that decide them, on one repo; nothing on the 12 slots or the 3 events can confirm them (item 11).
6. The "standards vs core" split is false for regex: core carries hundreds of `re.compile` sites and all three bisected steps were in core.
7. Function identity is (path, name): directory moves (backend/ -> gitgalaxy/ -> gitgalaxy/core/) become fake births and deaths (152/140 core births/deaths between 2026-04-13 and 05-26) and same-length edits are invisible.
8. Structure and speed use different engines (one fixed scanner for structure; each commit's own engine for speed); the structure scanner was an unpinned live worktree (now recorded: `tools/selfhistory/ENGINE_PINS.md`, commit fc8dd7125).
9. No positive control, no null, no noise floor between sessions, no alpha/power/multiplicity rule (checklist 9-14). Decision 2 ("hold slots until first results") is optional stopping.
10. Sampling rule (every 25th commit, 3 small corpora, 1 repeat): inadequate. It starves early history and over-samples October, drops the only large corpus (E2 and E3 moved only language-crucible), and cannot see steps under about 10% without a noise floor.
11. Only R2: authoring-era confound already registered as GG-H1..H3 and FLT-H1..H3 in `docs/HYPOTHESES.md` (Gemini era, Claude era, autonomous fleet); mean function size drops mechanically when small helpers are added. The draft must cite and respect those registrations. Also only R2: `--db-only` missing on s00, file-screen composition shifts in E2 (COBOL 568 -> 99 files, TypeScript LOC up) break per-file and per-LOC normalisation.
12. Only R1: structure-scan engine unpinned (fixed above); the venv has several editable gitgalaxy finders and the provenance check only inspects modules loaded when the entry module is imported.

## Where the reviews differ and the ruling
| Item | R1 (Claude) | R2 (Neon) | Ruling |
|---|---|---|---|
| SF-3 | fix, split in two | drop | Not confirmatory. Keep settle-in/survival as a descriptive profile (exploratory) until issue labels are pulled; drop the 4-months-vs-4-quarters rescaling. |
| SF-5 | fix (engine units); confirmatory candidate | exploratory-only | Split. (a) share of births landing in existing engine files: confirmatory candidate only after units, tests/standards exclusions and numeric bounds are frozen, because births have not been looked at; (b) "fan-in rising over time" dropped (growth alone predicts it). |
| SF-6 | drop or redesign | merge with SF-1 after removing runtime telemetry from the predictors | Drop as a hypothesis (both reject the circular predictor). Any cost-driver model is exploratory and on fresh data only. |
| Merge | SF-1 + SF-2 | SF-1 + SF-6 | Merge SF-1 + SF-2 into one commit-level claim about localised steps (matches both reviews' objection to interval-level data); SF-6 not merged. |
| SF-4 | drop as confirmatory | exploratory-only, split off a fresh-files extraction test | Exploratory narrative; the extraction test is a separate hypothesis that must control authoring era (GG-H1) and use only functions born after the freeze. |
| SF-7 | exploratory-only | fix; confirmatory after total regex time is logged, on held-out corpora | Exploratory until the instrument logs total regex CPU (engine change, owner's call); confirmatory only on held-out corpora. |
| SF-11 | fix: rank within engine files vs size-matched null | fix: top-5% or top-k, exclude `standards/`, size-matched fan-in and PageRank, degree-preserving null | Combined: top-5% by size-matched fan-in and PageRank within engine files (no `__init__`, tests, vendored, `standards/`), against a degree-preserving rewired null; fan-out reported but not used to decide. |
| SF-10 | keep as a control | drop, replace by fixed-intersection-file control | Control, not a hypothesis: time a fixed list of files mapped by every engine under test. |
| Sampling | add 2 repeats, A/A anchor, language-crucible on a fixed file list | add 3 interleaved repeats, a large held-out corpus, wall + RSS + output parity, stratify by time | Both adopted (below). |
Where they disagree the choice is design, not a fact in dispute; the planted-regression control below decides whether the merged claim is testable at all, and no ruling is allowed to stand if that control fails.

## Revised set
- Confirmatory candidates (need unseen data and frozen definitions first): merged SF-1/2 on newly localised unseen steps; SF-5(a); SF-11 (revised).
- Exploratory only: SF-3 (descriptive), SF-4, SF-7, SF-8 (three tiers, all exploratory), SF-9 (undefined sweep, dead zone; needs a definition or is dropped).
- Dropped: SF-6, SF-10 as hypotheses (SF-10 becomes the fixed-intersection control), SF-5(b).
- Every confirmatory hypothesis gets: direction, alpha, a minimum detectable effect, a multiplicity rule (Holm), and refutation rules with no dead zone.

## Required before any confirmatory run (controls and instrument)
1. Positive controls: plant known costs at known commits in a mirror copy (an O(N^2) pattern-table regex, an O(N^2) loop in core, a delay in worker start-up outside the per-file timers, serialisation to one worker) at 5%, 15% and 2x; the sampler plus bisect must recover them blind.
2. Negative controls: comment-only commits, pure `git mv` commits (must show zero step and zero births/deaths), the same engine commit timed in separate sessions at low and high load (A/A) to set the step threshold, block-permuted timing labels within era blocks.
3. Fixed-intersection corpus: time only files mapped by every engine under test; keep language-crucible on that list; add one large held-out multi-language corpus.
4. Instrument: log total regex CPU or time with CPU not wall (engine-side change, owner's call), record wall, CPU, peak RSS and output counts (files, functions, edges) per run, 3 interleaved repeats, an A/A anchor re-timed every N probes, a step threshold set from the A/A noise before looking.
5. Provenance: dump the module paths of the real run (workers included) at exit; pin the structure scanner by commit (done) and re-scan a subset with a second scanner version to measure scanner-version effects.
6. Identity: rename-aware function lineage (git renames + structure + text check, as in the TURN ledger) and a body hash, before any birth/death/settle-in statistic.
7. Sampling: stratify by time and by commit count; record every sampled index; do not drop a corpus after seeing which events it detects.
8. Era: every structure claim reports within-era results (Gemini, Claude, fleet) and cites GG-H1..H3 and FLT-H1..H3.

## The dense timing run already in progress
It follows the original rule (every 25th first-parent commit, 3 small corpora, 1 repeat) and was fixed before commit text was read, so it is not optional stopping; but both reviews call the rule inadequate, so its results are labelled a PILOT: useful to find where steps cluster and to size the noise, not to confirm anything. The controlled pass (items 1-8) is a separate, later run.

## Needs the owner
Accept or change the rulings above; decide whether the engine's `--splicing-speed` truncation should be fixed in GitGalaxy (a code change to a public repo; not done); decide whether to build the planted-regression controls before anything further is scored.
