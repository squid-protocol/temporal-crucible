# TURN v3: hypotheses written from the lineage-ledger data (PROPOSAL; unregistered; discovery repos = curl, redis, libgit2, impacket, sqlmap, ripgrep, tigerbeetle; revised 2026-11-16)

Every test below is run per repo with an interval, on the LAWS panel only, under the v2 lineage ledger as the registered identity instrument
(the ledger itself needs code review and a held-out accuracy report first). Numbers in brackets are discovery values, not evidence.

## Identity (validity gates)
* **ID-1** Path-and-name identity overcounts deaths by at least 40% against lineage identity; median lifetime lengthens by at least 1.3x. [deaths overcounted 40-78%; median life x1.6-2.8]
* **ID-2** Moves and renames are event-driven: the top 10% of quarters hold at least 60% of them in mature repos. [78-92%; the young repo 23%, so test maturity as a moderator]

## How repos grow
* **GRO-1** Growth is by new files: at least 60% of function births land in files that did not exist in the previous snapshot. [66-73%]
* **GRO-2** Deaths are mostly whole files disappearing: at least 45% of true deaths. [47-77%]
* **GRO-3** A typical quarter is quiet and change is concentrated: median quarterly true deaths below 0.5% of the population, with the top 10% of quarters holding at least 60% of deaths in mature repos. [0.0-0.1%; 69-85%]

## What happens after a function is born (settling in)
* **SET-1** Functions are born finished: at least 80% have identical measurements after 4 quarters in mature repos. [83-89%]
* **SET-2** The chance of change falls with age: per-quarter change at age 1 exceeds age 8 in mature repos (rank test across ages, per repo). [9->3, 7->2, 4->5(!)]; young repos stay volatile. [17->14]
* **SET-3** Wiring is set at birth: at least 95% of functions born with no callers still have none a year later. [96-100%] (the preferential-attachment kernel at degree 0 predicts exactly this; ties to LAW-2)
* **SET-4** Hub lineages persist beyond what naive identity shows: top-1% hubs remain top-5% after a year at least 90% of the time under lineage identity, and the naive figure is lower by at least 3 points. [94-98% vs 80-96%]

## Change inside survivors: sweeps are the unit (replaces SWP-1..3 of the v2 proposal)
A **sweep** is one call or macro name removed or added in at least max(10, 1%) of a quarter's code-edited surviving functions (tree-sitter diff of the function text at the two commits, ledger-linked
survivors only). A **migration** is a sweep where an old name disappears and a new one appears in the same functions (co-occurrence >= 40% of the smaller side). Thresholds are discovery choices and become
registered constants; a sensitivity at 5 and 20 functions is declared.
* **SWP-1** Sweeps carry a material share of in-place change: at least 20% of code edits to surviving functions fall inside a sweep, per repo, lower CI > 0.15. [libgit2 44%, tigerbeetle 38%, impacket 27%, sqlmap 22%, redis 22%, curl 21%; ripgrep 4% (2,465 edits: low power)]
* **SWP-2** Sweeps are one-quarter events: at least 80% of migrations (old -> new pair) complete inside a single quarter. [libgit2 135 distinct pairs in 138 migration-quarters; curl 121 in 128; redis 91 in 94]
* **SWP-3** Organic edits (outside sweeps) change signatures more often than sweep edits: difference > 0, per repo. [libgit2 20 vs 9%, impacket 14 vs 4%, tigerbeetle 31 vs 23%, curl 21 vs 15%, sqlmap 9 vs 6%; redis 21 vs 22% contradicts]
* **SWP-4 (exploratory, not gated)** The share of code edits inside sweeps rises over a repo's life. [curl 4% (2000s) -> 36% (2025s), libgit2 40% -> 52%; impacket 12% -> 10%, sqlmap 3% -> 0%: mixed, so no bound is set]
* **KW-1** Print-call density falls in C and C++ seats: per-repo slope of the yearly density curve < 0, upper CI < 0. [curl 8.8 -> 2.1 per kLOC, redis 10.2 -> 6.9, libgit2 4.8 -> 3.4; falls in 5 of 7 discovery repos, rises in the two Python tools]
* **KW-2 (descriptive, not tested)** "Safety keywords rise as repos mature" is not assumed: per-repo slopes of `def_safety` and `state_safety_neg` are reported with their sign. [def_safety rising in 3 of 7 repos, falling in 4; safety_neg falling in 4 of 7]
* **KW-3** Pointer-density change in C seats comes from turnover, not rewriting: |density change inside surviving functions| < 0.5 x |repo density change| over a repo's life. [libgit2 9 vs 216, curl 4 vs 81; redis contradicts: survivors -107 against repo +108, so births were denser while old code thinned]
* **KW-4 (prediction, not yet measured)** Sweeps explain H6's retrofit: with sweep quarters' edits removed, the H6 gap (alloc/cleanup/print vs branch/pointer/args retrofit share) shrinks by at least half.

## What organic edits are (tree-sitter, C family first)
* **EDT-1** Pointer edits are null-safety edits: P(an if-statement is added or removed | the edit changes pointer syntax) minus the same probability for other code edits > 0.10, per repo; reported with and without sweeps. [libgit2 43 vs 10%, redis 49 vs 23%, curl 51 vs 16% (+25 to +36 points); outside sweeps 44/12, 48/24, 47/16]
* **EDT-2 (descriptive)** For each repo: share of changed survivors whose text change is comments/whitespace only (4-12% in discovery), signature changes (15-22% of code edits), and the callee names most often added and removed.
* Python and Zig edit classes (try/raise, comprehension, `try`/unsafe) are discovery-only until their category definitions are fixed in a registered table.

## Derived functions (split, merge, extract, inline)
* **DER-1** These events are rare but real: at most 2% of births and at most 5% of deaths, and clustered in refactoring quarters. [0.3-1.6% of unlinked births; 0.4-5.1% of unlinked deaths; same-file only]

## Instruments (validity)
The edit classifier and sweep detector run on ledger-linked survivors; a link error becomes an edit error, so the ledger held-out accuracy gates every SWP, KW and EDT test.
Tree-sitter parses the function slice given by the engine's `start_line` and `loc`; a parse-error rate per repo is reported and repos above 5% are excluded.

## Owed before any of this is registered
Literature check (done at survey depth), power statement from the first seated repos, ledger held-out accuracy and chain accuracy, two independent design reviews
(the owner has waived the second reviewer; PR #186 is stale and should be closed or rewritten).
