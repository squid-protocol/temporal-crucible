# Evolution report, accuracy by language, and research-code studies (2026-11-19 / 20)

Status: **exploratory** except where a pre-registration is named. Numbers come from the tools in `tools/report/`; every table here can be regenerated. Scratch outputs live under `/tmp/gitgalaxy-scratch/claude/report/` (persistent disk via the scratch symlink).

## 1. What was built

- **`gitgalaxy evolution` prototype** (`tools/report/evolution_report.py`, `template.html`, `self_check.py`, `make_gif.py`): a one-page "Evolution of X" report with git-only and with-scans modes. Sections: at a glance, where it stands now (facts first, stage label, hubs by callers and by centrality), growth (size, call-graph GIF, births and deaths, language mix, age layers), function lifetimes, function kinds, where the work goes (organic / sweeps / fixes / mechanical), repairs, repeat spots, comments, and a self-check. Engine port is tracked by epic gitgalaxy#8715 (#8716-#8720); wiki drafts are `wiki-drafts/pages/08-30` to `08-43`.
- **Self-check** (`self_check.py`): git consistency, scan coverage (vendored directories counted apart), function agreement, call-edge agreement, import-graph agreement, and since this session a per-repository **libclang** comparison (C) and **Go / Rust import** baselines.
- **Fortran support** (`ATTRIBUTES`, `FORTRAN_EXTS`, comment and name rules in `evolution_report.py`; `ripple_forward.py`, `lang_validation.py`): free- and fixed-form, upper-case extensions. 15 unit tests pass (`tools/report/test_evolution.py`; 5 new).

## 2. A correction that matters: Python and Rust method edits were dropped

The generator read function names from git hunk headers **without the language diff drivers**. Git names a hunk's function only for lines at column 0 unless `diff=python` / `diff=rust` is set, so an edit inside a method got the class name (or nothing) and was lost. On OpenFold's first 300 commits 37% of hunks had a `def` header without the driver and 87% with it.

| Repo | function edits before | after |
|---|---:|---:|
| scapy (Python) | 5,021 | 20,413 (4.1x) |
| ripgrep (Rust) | 862 | 4,875 (5.7x) |
| sqlmap (Python) | 12,909 | 23,092 (1.8x) |
| OpenFold (Python) | 1,492 | 3,556 (2.4x); named pairs 122 -> 181; median lag 40 -> 27 d |
| ColabFold (Python) | 1,218 | 1,341 |
| sphinx (Python) | 55,491 | 55,491 (its `.gitattributes` already sets the drivers) |

Fixed in `301f820` (PARSER_VERSION 3 invalidates old caches). The sensor tools (`ripple_forward.py`) already used the drivers; only the generator's categories and pairs were affected. **Published pages (DPDK, nDPI, curl, all C) are unaffected.** Any earlier Python or Rust figure from the generator, including the first OpenFold and ColabFold results, is superseded by this document and `core_area.md`.

## 3. Accuracy by language (how far to trust the call graph)

Two different questions get conflated, and the numbers differ a lot:

| Question | Source | C | Go | Rust |
|---|---|---:|---:|---:|
| Did we find the right callee **names**? (engine "Level 1") | `tests/call_graph_accuracy_baseline.json` | 96-98% | n/a here | n/a here |
| Is a **confident link** to the right definition? (precision) | `call_graph_resolution_*_baseline.json` | 100% | 96.7% strict | 92% strict |
| Share of the reference's edges we link confidently (recall) | same | 50.8% | 77.8% | 81.5% |

Main's gates run on pinned, curated crucible repos with a configured reference. Our per-repo libclang comparison on arbitrary C repos (engine's own adapter, no build system):

| Repo | edges found vs libclang | share of ours libclang has | files where libclang found functions |
|---|---:|---:|---:|
| DPDK | 90% | 83% | 89% |
| nDPI | 88% | 92% | 78% |
| redis | 85% | 87% | 61% (not rated) |
| curl | 81% | 55% | 73% |
| libxml2 | 83% | 23% | 46% (not rated) |
| libgit2 | 69% | 95% | 93% |
| expat | 71% | 99% | 53% (not rated) |

Reading: **precision-first, recall moderate** (consistent with main's baselines). Where libclang could not parse a repo without its build configuration, "precision" is a lower bound. Rated only when libclang found functions in at least 70% of the files the scan did.

**The cheap check does not predict the compiler-grade one.** A tree-sitter name matcher agrees with GitGalaxy at 98-99% on every C repo while libclang recall ranges from 69% to 90% (same status in 2 of 7; correlation +0.06). Any self-check built on a name matcher alone is misleading; the report now says so and labels the cheap check "consistency with a name matcher". Detail: `report-design/threshold_validation_output.txt`, tool `tools/report/threshold_validation.py`. Pass / warning cut points (85% / 65%) mean: a repo at 100% recall turns to a warning after losing about 20% of its edges.

Other languages (name-matcher agreement only; no per-repo compiler reference): Python 75-84% (scapy, sphinx, sqlmap), Go 86% (prometheus), **Rust 10% (ripgrep; 17 call edges: unexplained, either an engine gap on a many-crate workspace or a stale scan)**. Go and Rust import baselines gave 54% and 67% and are **unvalidated** (my baselines are rough). Scan coverage gaps: curl 143 and sphinx 59 unexplained code files (engine bug class #8708 explains some).

## 4. Research code vs mature systems code

Git-only reports (corrected data): OpenFold 1,422 commits, ColabFold 1,392, AlphaFold 209 (public history is exported snapshots, not development: not comparable), WRF 6,731 (Fortran, 2006-2026), OpenCV 24,776.

| | OpenFold | ColabFold | WRF | curl |
|---|---:|---:|---:|---:|
| median time to a fix | 27 d | 33 d | 356 d | 244 d |
| fixes landing in the causing function | 68% | 88% | 69% | 65% |
| fix edits in functions fixed 2+ times | 66% | 86% | 67% | 77% |
| authors per quarter | 6 | 6 | n/a | 29 |

Fix speed follows project age and size, not whether the code is scientific. Concentration of fixes and "bigger commits get repaired more" (WRF: 4% of one-function commits later repaired, 10%, 23%, 40%, 53% for 2-3 / 4-10 / 11-30 / 31-60 functions) hold everywhere. The concentration has **no baseline yet**.

### Core vs the rest (pre-registered: `core_area.md`, tool `core_area.py`)
Definitions were fixed before any area result. OpenFold: core 29% of edits vs 33% of functions; 99% alive after a year (support 76%); fewer births and deaths; fixes per function core 0.84 vs support 0.52, entry 1.44, data 4.28 (H4 mixed). ColabFold: core 55% of edits vs 32% of functions (its "core" is the orchestration script `batch.py`: `run` 131 edits). **How stable the core is depends on what the repo's core is.** Caveat: a function moved between files looks like a death (ColabFold's six "core deaths" in 2025 Q2 moved to `input.py`).

### Keyword-shape lattice moves (tool `shape_moves.py`, frozen lattice `a27d2c93f817`)
Shape moves are rare in research code as in C: about 1% of function-intervals (OpenFold 1.1%, ColabFold 1.0%, sqlmap 1.0%, libgit2 1.0%, curl 3.0%); among edited functions 10.5% (OpenFold) and 11.3% (ColabFold) vs 17.8% in the CHG-2 units; moves are mostly one signal at a time, and in research code they are nearly all climbs (OpenFold 0.9% climb vs 0.2% descent; curl 1.6% vs 1.2%). Limits: lattice built on C (Python families unvalidated), edited-only counts are 200-500 units, scan spacing differs.

### Repair radius
| | measured | outside the function | within 1 call | within 2 calls |
|---|---:|---:|---:|---:|
| WRF | 766 | 442 | 1.42x (1.25-1.59) | 1.31x (1.22-1.42) |
| OpenFold | 128 | 62 | 1.32x (0.94-1.79) | 1.02x |
| ColabFold | 56 | 15 | not computable | |
| nDPI / DPDK (C) | 846 / 10,149 | | 1.87x / 1.67x | 1.55x / 1.44x |

The radius is present in Fortran science code (interval excludes 1) but weaker than in the C network projects. The Fortran call graph is unvalidated. PyTorch calls submodules through instance attributes, so OpenFold's model structure is largely invisible to the resolver. **OpenCV is unusable for this method**: no `Fixes:` trailers (1 named pair), blame found a cause for 4.5% of 3,000 sampled fix-like commits, so 15 pairs measured; C++ call recall 64% of a name matcher.

### Issue/PR-based cause linking (prototype `issue_causes.py`)
Cited-cause text in fix PRs and their issues yielded 3 usable pairs across OpenFold and ColabFold (111 and 95 merged PRs for about 1,400 commits each; most fixes are direct pushes; only 14 of 91 fix-like PRs cite an earlier change). Not viable for these repos; the better route is pooling blame-based pairs over many repos.

### Parameter tuning (tool `constant_tweaks.py`)
Constant-only hunks: WRF 9.1%, nDPI 13.3%, DPDK 11.9%, curl 8.3%, OpenFold 12.1%, ColabFold 7.1%, sqlmap 13.0%. Science code is **not** more of a tuning codebase at this resolution (C numbers include array sizes and enums).

### How new code arrives (tool `arrival.py`)
New functions arriving in brand-new files: WRF 85%, ColabFold 68%, DPDK 63%, libgit2 60%, OpenFold 55%, redis 53%, sqlmap/scapy 51%, nDPI 48%, curl 42%. Share of births in the busiest 10% of quarters: WRF 51%, ColabFold 62%, OpenFold 58%, sqlmap 60%, curl 45%, DPDK 22%. **WRF's largest bursts are whole components imported at once**: 2008 Q1 2,081 births (WRFDA `var/da`, `var/obsproc`), 2006 Q4 1,492 (`chem/KPP`, generated chemistry kernels), 2010 Q3 859 (`var/external`), 2009 Q1 662 (WRFDA plus RRTMG radiation). curl's largest bursts are tests (`tests/libtest`, `tests/http`) and new library layers (`lib/vquic`, `lib/vssh`), mostly inside existing files. Caveats: Fortran often keeps one routine per file (median new file = 1 function), the KPP burst is generated, early 2006 quarters sit at a converted-history start, scans are quarterly so same-quarter churn is invisible, and one science model beside two research-code repos does not make a "science" pattern.

## 5. Not-yet-supported ideas
- Side branches: nothing was measured. Prediction: large for squash-merge GitHub projects, near zero for linear mailing-list projects (DPDK, Linux). A cheap test would fetch `refs/pull/*` for one squash-merge repo and measure fixes made before merge; needs de-duplication by `git patch-id`.

## 6. Open leads, ranked
1. Pool blame-based pairs over 15-20 research-code repos for a Python-wide (and per-repo) radius with intervals.
2. Check whether the Rust call graph on ripgrep is an engine gap (main reports 81.5% recall on its crucible): re-scan with current main and score with the engine's own scorer.
3. Coverage gaps: curl (143), sphinx (59), nDPI (14) unscanned code files; classify against #8708.
4. Repeat-spot baseline (does concentration beat chance?); re-measure the fix-rule miss rate for the shipped rule.
5. Notebook-aware history (ColabFold touches `.ipynb` 648 times); move-aware function identity (a move is not a death).
6. Regime self-scan (recency vs neighbourhood ranker) and size as the only per-change risk signal: both still research-only (see `ripple_radius.md`).
7. Engine port of the generator: vendor Chart.js, drop numpy/pandas, split blame and radius into plugins; stage-label cut points were set on the same 19 repos and need a maintainer or held-out check.
8. E3SM (72k commits) would test whether import-heavy arrival is general to big scientific codes.
