# Core-algorithm area vs the rest (research code), pre-registered 2026-11-19

Question (owner): in research code (OpenFold, ColabFold), where is the core algorithm, and do function-structure changes happen there?

## Area definitions (fixed BEFORE looking at any area-level result)
Decided from the repo layout and domain knowledge of what each project's contribution is, not from edit counts.

OpenFold (reimplementation of the AlphaFold 2 network)
- core: `openfold/model/**` (Evoformer, structure module, attention primitives, triangular updates, heads), `openfold/utils/geometry/**`, `openfold/utils/rigid_utils.py`, `openfold/utils/loss.py`
- data: `openfold/data/**`, `openfold/np/**`
- support: other `openfold/**`
- entry: top-level scripts and `scripts/**`, `experiments/**`
- tests: tests and test-named files

ColabFold (fast MSA search + AlphaFold driver)
- core: `colabfold/batch.py`, `colabfold/colabfold.py`, `colabfold/mmseqs/**`, `colabfold/alphafold/**`, `colabfold/pairmsa.py`
- support: other `colabfold/**` (including `colabfold/rgi/**`, a later sampler add-on)
- entry: top-level scripts, `beta/**`
- tests: tests

## Hypotheses (directional, per repo; compared with the non-core, non-test code of the same repo)
- H1 stable core: core's share of function edits is below its share of functions.
- H2 core functions live longer (share of functions alive after 4 quarters, among functions at least 4 quarters old at the last scan).
- H3 structural change (functions born + died per year, divided by functions now) is lower in core than outside.
- H4 fixes land more per function in entry/support code than in core.
- Descriptive: when do core structure changes (births, deaths) happen, and which commits.
Descriptive for the call graph: share of core functions with at least one resolved incoming call edge (PyTorch calls submodules through instance attributes, so this is expected to be low; it bounds what a call-graph reading of the core can say).

## Limits stated in advance
Two repos, one language, one core definition each; names are identity (a renamed function counts as a death and a birth); edits are attributed through diff-header function names; ColabFold's notebooks are not seen.

## CORRECTION 2026-11-19 (same day, before any publication): Python method edits were being dropped
The evolution generator read function names from git's hunk headers WITHOUT the language diff drivers. Git names a hunk's function only for lines at column 0 unless `diff=python` / `diff=rust` is set, so an edit inside a Python or Rust METHOD got the class name (or nothing) and was lost. On OpenFold (first 300 commits, 2,437 hunks) 37% of hunks had a `def` header without the driver and 87% with it. The generator now writes an attributes file (`ATTRIBUTES` in `evolution_report.py`, PARSER_VERSION 3, so old caches are not reused). The sensor tools (`ripple_forward.py`) already used the drivers, so the radius machinery itself was right; the categories and pairs built by the generator were not.

Effect, OpenFold: function edits 1,492 -> 3,556; named pairs 122 -> 181; median lag 40 -> 27 days. ColabFold: edits 1,218 -> 1,341 (few classes). C reports (DPDK, nDPI, curl; the only ones published) are unaffected. The Python and Rust reference runs (scapy, sqlmap, sphinx, ripgrep) predate the fix and understate edits.

Revised area results (same pre-registered definitions):
- OpenFold: core 29% of edits vs 33% of functions (H1 holds, weakly); core 99% alive after a year vs 76% support (H2 holds); structural change 0.24 vs 0.38/1.55/0.33 (H3 holds); fixes per function core 0.84 vs support 0.52, entry 1.44, data 4.28 (H4 is MIXED: core is fixed more than support, less than entry and data).
- ColabFold: core 55% of edits vs 32% of functions (H1 not supported); H2, H4 not supported as before; H3 holds weakly.
- Shape moves among edited functions: OpenFold 10.5% (was 6.3%), ColabFold 11.3% (was 13.2%); family changes 1.7% / 0.5%.
- Repair radius, OpenFold: 128 measured (was 83), within 1 call 1.32x [0.94, 1.79], callees 1.44x [1.01, 2.08]; ColabFold unchanged (56 measured, 15 outside the function, no ratio).
