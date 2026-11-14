# Stored tables, phase A — review

**Reviewer:** Claude Fable 5.2, 2026-11-14. **Built by:** Claude Opus from `docs/process/tables_spec.md`.
**Reviewed:** `tools/tables/`, `tests/test_tables.py`, and the 8-line `--tables` option in `tools/harness/run.py`.

**Verdict: accept.** No finding against the build. Nine corrections to the specification, all raised by the
builder and all agreed, are recorded in the specification as Revision 2.

| check | how | result |
|---|---|---|
| Tests | re-run with the harness's | 20 passed (14 + 6), 99 s |
| A fresh build by the reviewer | own control repository (C, seed 77), own work directory, through the sandbox | nine tables built in 0.6 s after the pipeline |
| Hashes | SHA-256 of each table file's bytes against the hash in its name | all 9 equal |
| `file` is the whole tree | `git ls-tree` of the snapshot by the reviewer against the table's paths | 414 = 414, same set |
| Universe | `in_universe` against the manifest's `is_unit`, every path | equal on all 414; no universe row has a reason; no other row lacks one |
| Line count | against the manifest | manifest + 1 on 309 of 309 (the engine's convention) |
| `event` | (commit, path) pairs flagged HP against the outcome file's HP list | 121 = 121, same set |
| `pool` | against the outcome file's control pool | 699 = 699, same set |
| Invariants 4 and 5, recomputed by the reviewer | every `touch`, `event`, `pool` path is in the universe; every `event` and `pool` pair has a `touch` row | both hold |
| Data card | searched for every commit hash and path of the protected tables | none present; no path at all |
| Nothing recomputed | the builder's own test reads SA3's sources for registered numbers and patterns and finds none in `tools/tables/`; the reviewer read `build.py` | calls `frame`, `universe`, `Excluder.why`, `language_of`, `harvest` unchanged; no rule of its own |

**What the data card already shows on a control repository** — the pipeline's own completeness reads 1.0
while, measured against the tree, 357 of 390 files in the repository's language were scanned (0.915) and 309
are ranked (0.792), each file left out with its reason. That is the check defect 56 asked for.

**Left out by the builder, correctly:** the resolved target of a link, the keyword tier per commit, a recount
of the floor verdict, the linking commit of an inherited positive, `in_degree` and `out_degree`, and a
tree-wide flag. Each would have needed a rule written a second time. They are the natural scope of the second,
independent build.

**For phase B** (from the second design review, `research_codebase_spec.md` section 12): `index.json` records
GitHub's list by commit and should also record the two files' SHA-256, the history walk's parameters and the
harvest's flags; `history_can_touch` should count each cause of disagreement apart; a not-a-number is refused
today, which is stricter than the specification asks and is kept.
