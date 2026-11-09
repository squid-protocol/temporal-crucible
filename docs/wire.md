# WIRE — COBOL → det Java call networks along the translator's map (SCORED)

**Type:** confirmatory (H1–H3), plus a labelled post-hoc diagnosis
**Registered:** 2026-11-08 20:01 (commit 02ac986, `docs/wire_hypotheses.md`); scorer committed 20:03 (2fea95b,
`tools/wire_eval.py`) before its one run.
**Data:** gitgalaxy 8f96d76ba, `det_port.py run --all-cases --translate-only`, both styles: 271 cases, 7 estates
(CardDemo, CBSA, GenApp, zECS, dbb-mortgage, cics-crucible, the CICS async credit-card example), **213 unique
programs**. Raw output: `wire-study/wire_result.json` (outside the repo; third-party source never committed).

## Registered verdicts

| id | claim | result | verdict |
|---|---|---|---|
| **WIRE-H1** | structured ports keep the COBOL call network, as GitGalaxy reads both sides | 125 evaluable; mean J 0.52 vs map-shuffled 0.08; gap +0.43 (bootstrap lo +0.33); **41%** beat their own null (bar 50%) | **✗ not supported** |
| **WIRE-H2** | dispatch ports keep it too | 124 evaluable; J = 0.00 for every program: the engine sees no paragraph-to-paragraph call | **✗ not supported** (as the prior said) |
| **WIRE-H3** | the unlabeled call network alone finds a structured port's own COBOL source | **33 of 138 first (24%)**, chance 0.7%, label permutation p = 0.0001; sfs's best was 3/124 (2.4%); top-5 41% | **✓ supported** |

## Descriptive (registered as descriptive)

- **Dispatch, `perform(a, b)` resolved by a parser** (not the engine): mean J 0.69 vs shuffled 0.09, 73% beat their
  null. The wiring is in the dispatch ports; GitGalaxy's call graph cannot see through the dispatcher.
- **Per estate (structured style):** CardDemo J 0.67 (39 programs), cics-crucible 0.80 (41), dbb-mortgage 1.00 (4),
  zECS 0.30 (5); **CBSA 0.00 (28) and GenApp 0.00 (8)**. Dispatch style: 0.00 everywhere.
- **Dropped:** structured 88 of 213 (73 with < 3 mapped units, 15 with < 2 COBOL edges); dispatch 89.
- **Model-refined B2 ports** (`docs/benchmarks/det-refine-*`): not evaluable. The model replaced the
  `/** PARAGRAPH. */` headers with its own Javadoc, so the translator's map is gone (0–1 mapped units). Their
  unrefined inputs score J = 1.0 (CBACT02C structured, 6 units; COTRN02C typed, 18 units).

## Post-hoc diagnosis of H1 (EXPLORATORY: not a verdict, found after scoring)

- **Half of the "structured" ports are not structured.** `--style structured` applies only to programs with no GO TO,
  EXEC CICS HANDLE or SECTION; the rest fall back to the dispatcher silently. 57 of the 125 evaluable programs did
  (all of CBSA and GenApp): J = 0, the H2 blind spot. The registration did not anticipate the fallback.
- **The 68 truly structured ports:** mean J **0.95**, **76%** beat their null.
- **Small programs cannot beat the null.** 16 programs match perfectly (J = 1) on 3–5 units, where a shuffled map
  reproduces the same network often enough that the null's 95th percentile is already 1.0.
- **Partial matches are PERFORM THRU.** The Java calls every paragraph of a THRU range; the COBOL scan records the
  range's ends. The Java has more edges (ZECS001: 230 vs 115), not fewer.

## Reading

- **Name-free identification works where whole-program fingerprints failed.** The paragraph call network alone, with
  no names, picks a port's own source first 24% of the time among 138, ten times sfs's best and 33 times chance. This
  is the registered, positive result: a COBOL program's *design* (which paragraph performs which) survives
  mechanical translation and is recognisable from structure.
- **GitGalaxy's call graph cannot read dispatcher ports.** Every PERFORM becomes `perform(int, int)`; the paragraph
  edges are in integer literals the engine does not resolve. That covers all dispatch-style ports and the
  structured-style fallbacks (every CBSA and GenApp program). Either the engine resolves the translator's dispatch
  idiom, or the translator emits the paragraph call graph itself (its map already names every paragraph).
- **What this does not establish:** fidelity of non-mechanical ports. The refined ports lose the map, so a fidelity
  check of a model-written port needs the map carried through refinement.

## Follow-ups (for unseen data only)

- H1 restricted to truly structured ports (no dispatcher), with a power floor (≥ 6 mapped units), on ports generated
  after this study (new cases), registered before they exist.
- Engine: resolve `perform(a, b)` to the dispatched paragraph methods (gitgalaxy issue to file).
- Translator / refine: keep the paragraph header through B2 refinement, so refined ports stay traceable.
