# TURN v3: hypotheses written from the lineage-ledger data (PROPOSAL; unregistered; discovery repos = curl, impacket, sqlmap, ripgrep, tigerbeetle)

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

## Change inside survivors (sweeps)
* **SWP-1 / SWP-2 / SWP-3** as in hypotheses_v2_proposal.md (coordinated directional keyword sweeps among survivors, a sweep sets the norm for later births, sweeps follow tooling events), now measured on lineage survivors so moved or renamed functions are no longer mistaken for new code.

## Derived functions (split, merge, extract, inline)
* **DER-1** These events are rare but real: at most 2% of births and at most 5% of deaths, and clustered in refactoring quarters. [0.3-1.6% of unlinked births; 0.4-5.1% of unlinked deaths; same-file only]

## Owed before any of this is registered
Literature check (done at survey depth), power statement from the first seated repos, ledger held-out accuracy and chain accuracy, two independent design reviews
(the owner has waived the second reviewer; PR #186 is stale and should be closed or rewritten).
