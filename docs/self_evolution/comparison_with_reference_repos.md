# GitGalaxy's own evolution against the 19 reference repositories (EXPLORATORY; 2026-11-20)

Source of the reference numbers: the stage-label calibration of the evolution-report prototype (epic gitgalaxy#8715; temporal-crucible branch `sensor-overhaul`, `docs/sensor-overhaul/report-design/stage_calibration_table.txt`: 19 repositories in C, Go, Python and Rust, 8 to 29 years old) and the DPDK mock-up data (`dpdk_report_data.json`).
GitGalaxy's numbers come from the same generator (`tools/report/evolution_report.py`) run on its own history: 6,919 non-merge commits, 10 monthly scan snapshots (the daily scans filtered to engine code for the main version), `--blame 2500` to derive causes because the project has no `Fixes:` trailers. Reports: `real_report/`.

## Head to head
| Measure | GitGalaxy (0.67 years old) | Reference repos (8-29 years) |
|---|---|---|
| Functions | 186 -> 4,079 (x21.9 in eight months) | 1,226 to 60,091; growth per year -3% to +22% (median 7.8%) |
| Stage label | cannot be computed: the generator needs years of scans | calibrated on these 19 |
| Commits per year | about 10,400 | about 1,500 (curl, OpenSSL) to 4,600 (DPDK), from the table's commit counts and ages |
| Function edits per function-year | 37 (22,144 edits; time-weighted mean 897 functions) | 0.01 to 2.57 (curl highest) |
| Organic share of edits | 57.9% | DPDK 58.5% |
| Sweep share of edits | 14.5% | 0% to 64%, median about 19% |
| Fix share of edits | 14.5% | 3% to 46%, median about 10% (DPDK 17.8%) |
| Mechanical share (formatting, docs, tests-only, reverts, comment-only) | 13.1% | DPDK 2.8% |
| Functions untouched for four quarters | 2.6% to 20.7% in the last three scan points | 40% to 99% |
| Median time from a causing change to its repair | 9.9 days (464 blame-derived pairs; 'fix' causes 2.0 days) | DPDK 235 days (feature causes 262, restructure 183) |
| Fix edits landing in a function fixed 2+ times | 52% | DPDK 60% |
| Fix edits landing in a function fixed 5+ times | 24% | DPDK 20% |
| Most-fixed function | `_slice_by_braces` (`core/detector.py`), 41 fix commits in 8 months | DPDK `flow_dv_validate`, 60 in about ten years |

## How GitGalaxy differs
1. It is on another time scale. About 22x growth, about 37 edits per function-year (about 14x curl, the most-edited reference) and about 10,000 commits a year. Almost no function stays untouched for a year.
2. Its mix of work looks like DPDK's in one respect (58% organic) and differs in two: far more mechanical edits (13% against 3%) and fewer sweeps (14.5% against 21%). Fixes sit slightly above the reference median.
3. Repairs arrive in days, not months. The 24x difference in median lag is mostly an artefact of age: a repo 245 days old cannot contain a repair lag longer than 245 days, while DPDK's pairs span ten years. Compare it as "lag relative to age", not as a rate.
4. Bug concentration looks the same: about half of fix edits land in functions fixed more than once (52% against 60%), and the share in repeatedly fixed spots (5+) is as high as DPDK's despite the repo's youth. The most-fixed functions are in `core/detector.py`, the same hub that thickened (30 -> 154 functions).
5. The generator's stage label, its untouched-for-four-quarters measure and its size-band analysis (share of changes later cited as repaired, by change size) do not work at this age or without trailer-named pairs; the size-band section is empty in the real report.

## Caveats
Young repo, AI-written, very high commit rate (an 86x monthly surge in October); every ratio above mixes age with authorship regime. Reference values are copied from the calibration table and the DPDK mock-up, not recomputed. The git-side counts (edits, fixes, sweeps) cover all Python in the repository, tests included, because the generator has no path filter; only the scan-side series (functions, hubs, ages) are engine-only. Repair causes are inferred by blame for 746 unnamed fix-like commits (552 resolved), so the repair figures are lower-confidence than the generator's trailer-based mode. Call-graph recall for Python in the self-check is 53%, so hub counts are lower bounds. Whole-repo mode also counts vendored three.js (a bump of about 7,000 functions in March and "former hubs" that are vendored files); the engine-only report removes it.
