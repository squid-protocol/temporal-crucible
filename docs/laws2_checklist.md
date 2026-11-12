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
  - command: `python tools/laws2_size.py --run {study}/laws_run_laws2_pilot.json --out docs/laws2/panel_sizes.json`
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

## Phase 5

- [ ] **laws-main** — Every law on the main arm
  - why: Unchanged estimators: 182 tests, never the weak link in LAWS 1.
  - needs: scan, profile
  - controls: size-adjust
  - outputs: docs/laws2/laws_main.json
  - command: `python tools/laws_run.py --out {study} --repos {panel_repos} --matched-coverage --tag laws2_main`

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
  - needs: synthesis, figures, ctrl-negative, ctrl-coverage
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
| `oracle-calibrate` | How far is the compile-free graph from a compiler-grade one, where we can check? | all | the oracle was a gate, so 3 of 4 confirmatory languages were removed |

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
