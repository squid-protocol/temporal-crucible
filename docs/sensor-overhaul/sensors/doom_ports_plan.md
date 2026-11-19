# DOOM ports as a proving ground for the repair radius (plan, 2026-11-18)

**Status: plan; nothing registered or run.** Data: the 44 pinned ports of `doom-dna` (`/srv/storage_16tb/projects/doom-dna`, `manifest/manifest.csv`), now cloned with **full history** under `/srv/storage_16tb/projects/temporal-crucible-pool/doom-ports` (outside every repository; third-party code is never committed, measurements only). Inventory: `sensors/doom_inventory_output.txt`, `tools/sensor/doom_inventory.py`.

## 1. What exists
* **Function identity across ports, name-blind:** `doom-dna` (seed-and-extend, `followups/seed-and-extend`, standalone `structural-fingerprint-scanner`): FGW reciprocal-best-hit seeds, `delta` calibration and 3-hop call-graph extension, zero names read. Name agreement of the recovered matches against `linuxdoom` (its own scorecard, `FINDING.md`): C ports **80 to 100%** (mood 95%, doomgeneric 86%, sdl-doom 84%, chocolate-doom 67%, fastdoom 55%), **Go gore 77%**, doom3-bfg 40%, **Java mochadoom 18%, C# managed-doom 16%**, Dart 9%, Scheme 5% (their subsystem placement is better: 33 to 65%); from-scratch rewrites and unrelated C 0 to 1% (the null). Also `canonical_functions.csv` (168 canonical functions and the name each port uses) in `gitgalaxy/doom-study`.
* **Within-repo identity through history:** the function ledger (`structural_fingerprint.ledger.build_ledger`: one lineage id per function across snapshots, following renames and moves).
* **Call graphs and scans:** `gitgalaxy/doom-study/scans_r2` (39 ports, round 2) and doom-dna's scans.

## 2. What the inventory says (146,225 commits in 44 ports)
| group | ports (commits) | use |
|---|---|---|
| **Long histories, C and C++** | doomretro 21,027; gzdoom 20,572; odamex 10,530; dsda-doom 9,362; crispy-doom 7,500 (4,887 shared with chocolate-doom); eternity 7,161; chocolate-doom 4,890; woof 3,306 and nugget-doom 4,613 (3,244 shared); prboom-plus 3,222 (2,966 shared with dsda); srb2 11,282; fastdoom 3,647; edge-classic 3,824; doomsday 22,764 (a large rewrite) | the experiments that need many fixes |
| **Long history, other language** | helion (C#, scratch rewrite) 5,477 | a different structure (not DOOM's call graph: 0% DNA) |
| **Short histories, faithful translations** | managed-doom (C#) 831; gore (Go) 429; rust-doom 313 (scratch); doo-cr (Crystal) 329; kocoa-doom (Kotlin) 140; mochadoom (Java) 135; dartdoom 41; doom-scheme 20; most others under 60 (many are single-shot dumps of 2026) | **too thin per port**: a pooled translation family is about 2,000 commits, perhaps 150 repair pairs |
| **Shared ancestry** | chocolate-doom with crispy-doom (4,887, 100% of the smaller history); woof with nugget-doom (3,244, 98%); prboom-plus with dsda-doom (2,966, 92%); mochadoom with kocoa-doom (129, 96%) | **not independent evidence**: treat each family as one lineage |
**Consequence.** The idea "the same neighbourhood in many languages with long histories" is limited by the data: the languages with faithful translations have histories too short for a per-port repair radius. The strong parts are (a) **independent C and C++ lineages** with long histories around the same inherited functions (vanilla, Boom, MBF/Eternity, ZDoom, DoomRetro, EDGE, SRB2, FastDoom), roughly 100,000 commits, and (b) **cross-language structure** for questions that need only a snapshot.

## 3. Experiments, ranked by what the data supports
| # | question | design | history needed | power |
|---|---|---|---|---|
| **A** | **Is the call graph right, per language?** A natural oracle. | Take `linuxdoom`'s call edges among functions matched 1-to-1 to a port (seed-and-extend matches, plus the canonical names where both exist); check whether the engine's graph of the port has the corresponding edge; recall and precision by language, port fidelity ("faithful" in the manifest) as the control. | none (scans exist) | all 44 ports; faithful ports give the cleanest reference |
| **B** | **Same neighbourhood, independent lineages: is the repair radius a property of the structure or of the people?** | For inherited functions (matched to `linuxdoom`), compute each lineage's repair radius with blame-based causes (calibrated on C: radius within 1 to 14% of trailers); compare across lineages and test whether neighbourhoods repaired together in one lineage are repaired together in the others. | yes (C and C++) | about 100,000 commits; thousands of pairs per lineage |
| **C** | **Convergent repair.** | For an inherited function repaired in port X, which neighbours were repaired with it; do **independent** lineages repair the same neighbours more often than chance (permutation null: random functions of the same size and file role); inherited fixes (shared commits or identical diffs) excluded. | yes | depends on overlap; the most informative if it works |
| **D** | **Does a sibling's history beat the local graph?** (the cross-port prior for "where to look first") | Predict where lineage X's repairs land from (a) X's own graph (the validated ranking), (b) the neighbours repaired in the other lineages, (c) both; held-out by lineage. | yes | lineages with at least 500 repair pairs |
| **E** | **Added and deleted inherited functions.** | Replicate the added and deleted function result where lineages drop or add inherited functions. | yes | thin; descriptive |
| **F** | **Known-bug case studies.** | Vanilla bugs that several ports fixed (documented in the community): compare the functions each fix touched. | yes | a handful; illustrative |
Not feasible as designed: a per-port repair radius in Java, C#, Go, Rust, Kotlin, Dart, Crystal and Scheme (histories of 20 to 830 commits), and any claim that rests on `helion`, `room4doom` or `rust-doom` being "the same neighbourhood" (they are from-scratch rewrites with 0% DNA).

## 4. Method notes
* **Function IDs through time:** align each port to `linuxdoom` at its pinned snapshot with the name-blind matcher, then carry the id backward through the port's history with the lineage ledger (quarterly snapshots; `turn_v2` scan harness). Names are used only as a check.
* **Independence:** families (above) are one lineage each; cross-lineage tests use one representative per family or a family-level random effect.
* **Cause labels:** none of these projects write `Fixes:` lines; blame-based causes (SZZ style) with the calibration already done on DPDK and curl; fix commits by subject words.
* **Pre-registration:** hypotheses written down before every run (as for every study in this log); the preregistration of record for the DOOM study is `doom-dna/preregistration/EXPERIMENTS.md` (DOOM-E1 to E6 exist); new experiments here would be DOOM-R1... and should be registered there before any scan or measurement.
* **Licences and data:** measurements only; clones live outside any repository; no source text is quoted.
