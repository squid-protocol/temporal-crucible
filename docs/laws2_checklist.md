# LAWS2 — the run checklist

**Generated from `tools/laws2.py`. Do not hand-edit:** the checklist and the pipeline are the same
object, so they cannot drift apart. Regenerate with `python tools/laws2.py checklist --write`.

A stage marked **GATE** blocks every later phase until it passes. `laws2.py run` enforces it; this is
the single rule LAWS 1 most needed, because its irreversible steps ran before its decisive one.


## Phase 0

- [ ] **oracle-screen** — Can each language's oracle run on OLD snapshots?  **(GATE)**
  - why: THE lesson of LAWS 1. Java 0/4 and Python 0/4 because their oracles must build the snapshot. Run this on a throwaway sample before any frame, draw or seat exists.
  - controls: oracle-calibrate
  - outputs: docs/laws2/oracle_availability.json
  - TO BUILD: tools/laws2_oracle_screen.py: N throwaway repos per language x 2 boundaries, record run/parse/fail
- [ ] **data-availability** — Does the per-repo side data exist?  **(GATE)**
  - why: LAW-9 was evaluable in 1 of 5 repos because the rest had no sized OSV fix table. Knowable up front.
  - outputs: docs/laws2/data_availability.json
  - TO BUILD: tools/laws2_data_screen.py: OSV/CVE tables, issue labels, build files, per candidate
- [ ] **pilot-e2e** — One repo per language, all the way to a law statistic  **(GATE)**
  - why: A pilot that stops before the last step hides the failure that killed LAWS 1.
  - needs: oracle-screen, data-availability
  - controls: neg-shuffle, pos-synthetic, coverage-ladder
  - outputs: docs/laws2/pilot_e2e.json
  - command: `python tools/laws_run.py --out {study} --repos {pilot_repos} --tag laws2_pilot`

## Phase 1

- [ ] **sizing** — Panel size PER LAW from the pilot's between-repo variance
  - why: One uniform panel size is wrong: the pilot puts LAW-2 at ~2 repos per language and LAW-3 at ~30.
  - needs: pilot-e2e
  - outputs: docs/laws2/panel_sizes.json
  - command: `python tools/laws2_size.py --run {run} --out docs/laws2/panel_sizes.json --md docs/laws2/panel_sizes.md`
- [ ] **sesoi** — A smallest effect size worth caring about, per law
  - why: Margin 0 plus 100 snapshots makes everything significant: LAW-4 was 'detected' at a Gini gap of 0.026.
  - needs: pilot-e2e
  - outputs: docs/laws2/sesoi.json
  - TO BUILD: a registered table: law -> SESOI, direction, and the tolerance for the coverage ladder
- [ ] **register** — Freeze the registration and hash it  **(GATE)**
  - why: Fewer bars, all of them met once end to end. One editor; the hash is the anti-collision device.
  - needs: sizing, sesoi
  - outputs: docs/laws2/registration.md, docs/laws2/registration.sha256
  - TO BUILD: write it, then `sha256sum` it into the manifest

## Phase 2

- [ ] **frame** — Build the sampling frame
  - why: Unchanged from LAWS 1; it worked.
  - needs: register
  - outputs: docs/laws2/frame/
  - command: `python tools/laws_frame.py search --language {lang} --out {study} --confirm`
- [ ] **exclude** — Apply the registered exclusions before the draw
  - why: LAWS 1 Amendment 9: exclusions must precede the draw and be logged.
  - needs: frame
  - outputs: docs/laws2/panel/
  - command: `python tools/laws_exclude.py --out docs/laws2/panel`
- [ ] **draw** — Seeded draw, deep enough on the FIRST pass
  - why: LAWS 1 went 40 -> 400 -> 2,000 in three amendments. Measured pass rate is 5.8%, so draw depth is repos_needed / 0.058 with headroom, once.
  - needs: exclude
  - outputs: docs/laws2/draw/
  - command: `python tools/laws_frame.py draw --language {lang} --n {draw_depth} --eligible docs/laws2/panel --record docs/laws2/draw/{lang}.json`
- [ ] **seat** — Walk the draw and seat the panel
  - why: Licence rule enforced from the start this time; it cost 30% of seats when applied late.
  - needs: draw
  - outputs: docs/laws2/seating/
  - command: `python tools/laws_seat.py --want {want} --language {lang}`

## Phase 3

- [ ] **scan** — Scan every seated repo at every boundary
  - why: The engine was never the problem: 18/18 scans succeeded in LAWS 1.
  - needs: seat
  - outputs: docs/laws2/scans/
  - TO BUILD: tools/laws2_scan.py: quarterly walk per seated repo into one walk DB, resumable
- [ ] **profile** — Resolution profile per snapshot
  - why: Resolved share, per-step drops and merge rate become INPUTS, not an appendix.
  - needs: scan
  - controls: merge-rate
  - outputs: docs/laws2/profiles.json
  - TO BUILD: tools/laws2_profile.py: one row per snapshot
- [ ] **oracle-agree** — Agreement where the oracle genuinely runs
  - why: Calibration, not a gate. C and post-modules Go can carry uncertainty for the rest.
  - needs: scan
  - controls: oracle-calibrate
  - outputs: docs/laws2/oracle_agreement.json
  - command: `python tools/accp_eval.py score --langs {oracle_langs}`

## Phase 4

- [ ] **ctrl-negative** — Negative control: shuffled graphs
  - why: If the law is absent by construction, does the pipeline still report it?
  - needs: scan
  - controls: neg-shuffle
  - outputs: docs/laws2/arms/negative.json
  - TO BUILD: tools/laws2_arms.py negative: degree-preserving shuffle, then the full law run
- [ ] **ctrl-positive** — Positive control: planted effects
  - why: If the law is present at a KNOWN strength, does the pipeline recover it?
  - needs: pilot-e2e
  - controls: pos-synthetic
  - outputs: docs/laws2/arms/positive.json
  - TO BUILD: tools/laws2_arms.py positive: grow graphs with a known exponent, run the real pipeline
- [ ] **ctrl-coverage** — Coverage ladder 100/75/50/25
  - why: Does the number describe the code or the extractor?
  - needs: scan
  - controls: coverage-ladder
  - outputs: docs/laws2/arms/coverage.json
  - command: `python tools/laws_run.py --out {study} --repos {panel_repos} --thin {share} --tag cov{share}`
- [ ] **ctrl-testsplit** — Tests and vendored code excluded
  - why: Is the law about the code or about testing conventions?
  - needs: scan
  - controls: test-split
  - outputs: docs/laws2/arms/no_tests.json
  - TO BUILD: tools/laws2_arms.py no-tests: drop test/vendored files, re-run
- [ ] **ctrl-timesplit** — First half vs second half of history
  - why: Does the law hold in both halves of history, or only across the whole span?
  - needs: scan
  - controls: time-split
  - outputs: docs/laws2/arms/time_split.json
  - TO BUILD: tools/laws2_arms.py time-split
- [ ] **ctrl-speccurve** — Specification curve over every research parameter
  - why: Is the result a property of the data, or of one defensible choice among many?
  - needs: scan
  - controls: spec-curve
  - outputs: docs/laws2/arms/spec_curve.json
  - TO BUILD: tools/laws2_arms.py spec-curve: walk params.json grids, re-estimate, keep the effect distribution

## Phase 5

- [ ] **laws-main** — Every law on the main arm
  - why: Unchanged estimators: 182 tests, never the weak link in LAWS 1.
  - needs: scan, profile
  - controls: size-adjust
  - outputs: docs/laws2/laws_main.json
  - command: `python tools/laws_run.py --out {study} --repos {panel_repos} --matched-coverage --tag laws2_main`
- [ ] **arm-as-published** — Every law ALSO under its source paper's own method
  - why: A replication that only uses a modernised method can be answered with 'you did not do what we did'. The gap between the two arms is the most valuable thing this study can report.
  - needs: scan
  - controls: as-published
  - outputs: docs/laws2/arms/as_published.json
  - TO BUILD: tools/laws2_as_published.py: per law, the source estimator + null + original figure form, each citing the paper and equation it reproduces

## Phase 6

- [ ] **synthesis** — Pool per language, refusing to pool below the sized k
  - why: LAWS 1 pooled k=2 and returned a 99% interval of -3.76 to 4.00 with a NaN prediction interval.
  - needs: laws-main, sizing
  - outputs: docs/laws2/synthesis.json
  - TO BUILD: tools/laws2_synth.py: refuse, loudly, when k < panel_sizes[law]
- [ ] **figures** — Every figure that has its inputs
  - why: The graphs are declared up front and render themselves as the arms land.
  - needs: laws-main
  - outputs: docs/laws2/figs/
  - command: `python tools/laws_explore.py --run docs/laws2/laws_main.json --figs docs/laws2/figs --md docs/laws2/tables.md`
- [ ] **report** — The write-up, with every arm beside the main number
  - why: A result is the main number AND what the controls did to it.
  - needs: synthesis, figures, ctrl-negative, ctrl-coverage, arm-as-published
  - outputs: docs/laws2/report.md
  - TO BUILD: assembled from the arms; no number is published without its control row

## Controls

| control | asks | covers | LAWS 1 |
|---|---|---|---|
| `neg-shuffle` | If the law is absent by construction, does the pipeline still report it? | LAW-1..LAW-9 | never run end to end; only per-estimator unit tests existed |
| `pos-synthetic` | If the law is present at a KNOWN strength, does the pipeline recover it? | LAW-1..LAW-5 | estimators were tested on simulated data, the PIPELINE was not |
| `coverage-ladder` | Does the number describe the code or the extractor? | LAW-1..LAW-5 | measured once, late, as an amendment: LAW-3 moved 157%, LAW-2 only 10% |
| `size-adjust` | Is the structural effect just size? | LAW-6..LAW-8 | adjustment removed 60-90% of LAW-7's signal, and was secondary |
| `test-split` | Is the law about the code or about testing conventions? | LAW-1..LAW-8 | never run; commons-lang has 363 test files against 264 unit files |
| `time-split` | Does the law hold in both halves of history, or only across the whole span? | LAW-1..LAW-5 | never run |
| `merge-rate` | Is the in-degree tail an artefact of collapsed identities? | LAW-1, LAW-3, LAW-4 | merge rate ran 0-19.2% per snapshot and was never used |
| `spec-curve` | Is the result a property of the data, or of one defensible choice among many? | LAW-1..LAW-5 | research choices (5-year hub window, top-1%, x_min rule) sat as bare module constants, indistinguishable in the code from a bootstrap count |
| `as-published` | Does the ORIGINAL claim reproduce under the ORIGINAL method? | LAW-1..LAW-9 | only the strengthened method was registered, so a null result could always be answered with 'you did not do what we did' |
| `oracle-calibrate` | How far is the compile-free graph from a compiler-grade one, where we can check? | all | the oracle was a gate, so 3 of 4 confirmatory languages were removed |

## Registered research parameters

Each changes the claim, so each is registered with a grid of defensible alternatives that the
`ctrl-speccurve` arm walks. Precision knobs and guards are in `docs/laws2/params.json`.

| parameter | value | grid | laws | why it is a research choice |
|---|---|---|---|---|
| `hub_years_apart` | `5` | `[3, 5, 7, 10]` | LAW-3 | 'still a hub five years later' - five is arbitrary, and LAW-3 is already the most fragile law |
| `hub_top_share` | `0.01` | `[0.005, 0.01, 0.05, 0.1]` | LAW-3 | who counts as a hub; a narrow cut puts the test on a handful of nodes |
| `hub_still_share` | `0.05` | `[0.01, 0.05, 0.1, 0.25]` | LAW-3 | how far a hub may fall and still 'persist'. With 0.05 the observed and null both sit near 0.95 |
| `hub_ceiling_sd` | `0.005` | `[0.0, 0.005, 0.02]` | LAW-3 | declares a repo 'not evaluable (ceiling)'. It silently decides WHICH repos the law is tested on |
| `tail_min_fraction` | `0.05` | `[0.0, 0.05, 0.1, 0.25]` | LAW-1 | the floor under 'the tail'. Observed tails ran 8% to 100% of nodes between repos |
| `tail_min_nodes` | `50` | `[30, 50, 100]` | LAW-1 | a 30-node tail is too easy; the registration says so and then fixes one value |
| `tail_xmin_rule` | `ks` | `['ks', 'fixed_1', 'fixed_2', 'fixed_5']` | LAW-1 | KS-chosen x_min is per-repo, so 'the tail' is not the same object across repos. A fixed x_min is comparable but less favourable |
| `attach_features` | `['log_k', 'same_file', 'same_dir', 'log_loc', 'log_age']` | `[['log_k'], ['log_k', 'log_loc'], ['log_k', 'same_file', 'same_dir', 'log_loc', 'log_age']]` | LAW-2 | a modelling choice written as a constant. Dropping log_loc tests whether attachment is size in disguise |
| `snapshot_granularity` | `quarterly` | `['monthly', 'quarterly', 'yearly']` | LAW-1, LAW-2, LAW-4, LAW-5 | LAW-2 counts 'new edges per step'; the step length sets how many edges are new |
| `frame_min_commits` | `2000` | `[500, 1000, 2000]` | sampling | did 95% of all rejection work in LAWS 1 - this parameter, not the research question, defined the population |
| `frame_min_files` | `50` | `[20, 50, 100]` | sampling | sets when a repo's history is judged to have started |
| `frame_quarter_coverage` | `0.75` | `[0.5, 0.75, 0.9]` | sampling | how gappy a history may be and still count |
| `frame_language_share` | `0.6` | `[0.5, 0.6, 0.8]` | sampling | how monolingual a repo must be to represent its language |
| `coverage_ladder` | `[1.0, 0.75, 0.5, 0.25]` | `[[1.0, 0.75, 0.5, 0.25]]` | all | the instrument control. 44% removal already moved LAW-3 by 157% and LAW-2 by 10% |

## Figures declared in advance

Each renders as soon as its stage lands, so no figure is invented after seeing the numbers.

| figure | needs | shows |
|---|---|---|
| `f1_network_laws` | laws-main | each law's effect vs its SESOI, per repo |
| `f2_law1_tail` | laws-main | what share of nodes each fit calls 'the tail' |
| `f3_law3_ceiling` | laws-main | observed persistence against its null |
| `f4_law5_decay` | laws-main | modularity slope per year against zero |
| `f5_law7_size` | laws-main | effect before and after size adjustment |
| `f6_law8_auc` | laws-main | AUC with and without network metrics |
| `f7_coverage_sensitivity` | ctrl-coverage | % change in each law across the ladder |
| `f8_negative_control` | ctrl-negative | every law on shuffled graphs; must be ~0 |
| `f9_positive_recovery` | ctrl-positive | recovered vs planted effect |
| `f10_time_split` | ctrl-timesplit | first half vs second half, per law |
| `f11_test_split` | ctrl-testsplit | with and without test code |
| `f12_oracle_agreement` | oracle-agree | compile-free vs oracle, where it runs |
| `f13_as_published_vs_strengthened` | arm-as-published | per law, the source paper's own estimate beside ours - the gap IS the result |
| `f14_original_figure_form` | arm-as-published | each paper's own figure redrawn on our data (log-log CCDF, modularity-over-time) |
| `f15_specification_curve` | ctrl-speccurve | every law's effect across all defensible parameter choices, sorted |
