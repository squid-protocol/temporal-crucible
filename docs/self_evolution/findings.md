# Evolution of GitGalaxy's engine code, 180 daily snapshots (EXPLORATORY; nothing registered; computed 2026-11-20)

Method: lineage ledger (structural-fingerprint-scanner `ledger`, rename/move-aware) over the 180 daily scan databases, one fixed scanner (ENGINE_PINS.md). Units, declared in `tools/selfhistory/evo/analyze.py` before the results were read:
ENGINE = functions under `gitgalaxy/` or `backend/` excluding tests, `standards/` pattern tables, `__init__.py` and everything else (vendored JS, docs, site); SCAN = ENGINE minus `gitgalaxy/tools/`; TOOLS = `gitgalaxy/tools/` (translator and utilities).
Functions of 3+ lines only (ledger default). Eras from HYPOTHESES.md GG-H1/H2/FLT-H1: Gemini < 07-06, Claude 07-22..09-26, fleet >= 09-27 (07-06..07-21 transition, reported but not assigned).
Numeric bounds for SF-5 were NOT frozen before this run, so every number below is a description, not a test.

## Growth
Engine-code functions: 170 (03-21) -> 242 (05-10) -> 313 (08-22) -> 2,524 (10-12) -> 3,926 (11-20). The fleet era (from 09-27) accounts for 2,743 of 3,861 births (71%); of those, 1,981 (72%) are in the translator/tools subtree and 762 in the scanner core.
Deaths are rare: 116 engine deaths against 3,861 births (3%); 45% of deaths are a whole file removed (78% in the Gemini era, 9% in the fleet era).

## Where births land (new files vs existing files)
Engine all 51% new-file / 49% existing-file; SCAN 45% / 55%; TOOLS 54% / 46%. By era (engine): Gemini 66% new, Claude 48%, fleet 50%. The TURN held-out repos run 44-56% new-file births, so this is inside that range, not distinct from it.
Reading: the scanner core grows mostly by adding functions to files that already exist; the translator grows more by adding files.

## Settle-in (identical size and composition vector to birth; calendar days, not quarters)
Engine: after 7 days 82-87% unchanged; after 30 days 62-75%; after 90 days 26% (Gemini era, n = 164) and 52% (Claude era, n = 44, too few). Survival is high throughout (86-100% alive).
TURN reference: 83-96% unchanged after one quarter in mature repos, 83% after one quarter and 59% after four in the young fast repo (tigerbeetle). GitGalaxy functions change faster than any of them at comparable ages.
Caveats: the unchanged test here uses size plus the blind composition vector, close to but not identical to TURN's measurement tuple; the repo is eight months old and written by AI with a very high commit rate (86x monthly surge in October), so this compares authorship regimes and age as much as architecture.

## Hubs and orchestrators (file-level import graph among engine files)
- `galaxyscope.py`: fan-out rank 1 of 21..63 files through 09-10, rank 2 of 269 by November; fan-in 0 throughout (nothing imports it: it is the entry point). 718 -> 2,915 LOC, 14 -> 61 functions; mean function size 51 -> 88 (08-22) -> 48 (11-03), the peak-then-fall of the earlier note, with the fall landing in the 09-27 snapshot (25 -> 41 functions).
- `cobol_refractor_controller.py` and `cobol_to_java_controller.py` (first seen 04-17): flat for five months (9 and 4 functions), then a step on 09-28 (13 and 6); fan-out rank 2-3 early, 7-8 by November as the repo grew; fan-in 0.
- `core/detector.py`: fan-in 1-2 only; 30 -> 154 functions, 1,221 -> 6,233 LOC; mean function size 41 -> 60 (07-14) -> 40.5.
So the orchestrators are hubs by fan-out (the definitional sense the amendment warned about) and not by fan-in; as entry points they are imported by nothing. Import-edge recall is incomplete, so these ranks are lower bounds.

## What this does and does not say
Consistent with: accretive growth with few deaths; core growth by thickening existing hubs, translator growth by new files; a faster-changing, younger population than the TURN repos; hub thicken-then-split in galaxyscope.py.
Not established: anything about unseen data (every table is a description); SF-11 (fan-in hubs) is not supported in the import graph, and fan-out hubness is near-definitional; era effects are not separated from age.
