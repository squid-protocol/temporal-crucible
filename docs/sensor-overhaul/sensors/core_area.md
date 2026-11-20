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
