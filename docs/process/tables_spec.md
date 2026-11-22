# Stored tables, phase A — build specification

**Status: specification, 2026-11-14. Nothing built.** Step 3 of `research_codebase_spec.md`. Built by one
session from this document; reviewed by a different model.

**Revision 2, 2026-11-14, as built** (review: `reviews/tables_review_fable.md`). The builder found nine places
where this document asked for something the tools cannot give without a rule being written twice, or was
loose. All are accepted; `tools/tables/DECISIONS.md` entries 24–31 give each in full. In short: the reason order
is language first, then the Excluder's own order (vendored, documentation, generated, test, example), then
not-in-archive, not-scanned, zero-LOC; `event.how` is inferred (a non-merge is "own", a merge with no link of
its own is "inherited") because the outcome file does not say; `marginal` is recounted for the HP tiers and
the pool only, not for the keyword outcome or the floor verdict; `link` has no resolved target; the
branch-state value is `amplified_cascading_flux`; the data-card leak test means "no commit hash, path or link
value from a protected table", not "no string"; the largest-directory share is reported with the share of its
files untouched in the window, which is what shows imported code; and the manifest comparison needs two more
named causes (ambiguous in the manifest; a revert whose target lies between the two snapshots).

**Phase A is control repositories only.** It builds the tables, their invariants, their hashes and the data
card, and proves them against manifests, inside the harness sandbox. Building the same tables from SA3's real
data is phase B: a separate specification and a separate, deliberate job. Nothing in phase A opens the real
study directory.

## The idea

SA3's tools recompute derived facts live and keep them in files of mixed shape. Phase A puts each fact in one
table, written once, with a hash, so that later stages read tables and never call git or recompute a rule.

**No rule is re-implemented here.** A table is built from what SA3's own tools already produce (the scan
database and its sidecar, the history database, the body harvest, the outcome file, the nesting file) or by
calling SA3's own functions unchanged (`sa3_outcomes.universe`, `laws_units.Excluder`, `mod1_lift.frame`).
If a fact the table needs is not available without re-deriving a rule, the column is left out and the gap is
written down. A second, independent derivation of the label events from the written rule is a later, separate
build, compared against these tables; it is not part of this one.

## Where it runs

Inside the harness sandbox (`tools/harness/sandbox.py`), after the harness has run the pipeline on a control
repository (`tools/harness/run.py`, route `manifest`). The table builder is one more stage of that run: it
reads `WORK/study/…` and the pool copy, and writes `WORK/study/sa3_tables/<repo>/`. Any code that imports an
SA3 module that touches the study path runs only inside the sandbox.

## Storage

- One file per table build: `<table>.<first 16 hex of its hash>.jsonl`, one JSON object per row, rows in
  byte order of the key columns, never written over.
- **Canonical row bytes:** UTF-8; keys in a fixed column order given by the schema; integers as integers;
  every real number written as the string of Python's `float.hex()`; missing as `null`; a path that is not
  valid UTF-8 escaped by a stated, reversible rule; no spaces. The hash is SHA-256 over the rows' bytes, each
  followed by a newline.
- `index.json` per repo: for each table its hash, row count, schema version, whether it is protected, the
  hashes of every input file read, and the builder's own code hash.
- Protected tables (`link`, `event`, `pool`) go in a `protected/` subdirectory. For SA3 that is separation
  only; a blinded study will encrypt them (`blinding_spec.md`).

## The tables

Column types are fixed in a schema module. Key columns first.

| table | key | other columns | built from |
|---|---|---|---|
| `repo` | `repo` | language, unit rule (first-parent or not), status and reason, the pool clone's tip hash, engine id, the hash seed if recorded | history `meta`, scan sidecar |
| `snapshot` | `repo` | `cut_ct`, `sha`, `ct`, `window_start`, `window_end`, usable commits | `mod1_lift.frame`, outcome file |
| `file` | `repo, path` | `in_universe`, `reason`, `loc`, language, `scanned`, `in_archive`, `history_can_touch` | the snapshot's `git ls-tree` (every path, once), the scan, `universe()`, `Excluder.why` |
| `measure` | `repo, path, name` | value, `absent_means` (`zero` or `missing`), instrument, version | the scan columns the scorer reads (`sa3_score.COLS` and the branch-state value), the nesting file. Raw measures only; derived predictors are not stored in phase A |
| `touch` | `repo, sha, path` | commit time, first-parent position | the history's `touch` table, restricted to the window and the universe exactly as `sa3_outcomes` restricts it |
| `link` | `repo, sha, kind, value` | resolved target, if any | the body harvest's `link` table |
| `event` | `repo, sha, path` | outcome tiers the commit counts under (HP, HP_allreverts, the exclusive tier), own or inherited where the outcome file says | the outcome file's per-outcome commit lists |
| `pool` | `repo, sha, path` | — | the outcome file's control pool |
| `marginal` | `repo, outcome` | positive files, qualifying commits, largest commit's share, clears-floor | the outcome file; compared with a recount from `event` |

`file.reason` is one of a closed, ordered list, the order being the order `laws_units` tries them: not the
repo's language · test · vendored · documentation · example · tutorial · generated · excluded by
`.gitattributes` · not in the archive · not scanned by the engine · zero LOC. Where the reason is "vendored"
or "documentation" by GitHub's list, the row also carries the pattern that matched.

`file.history_can_touch` is true when the history walk's own unit rule (`laws_history`) would record a touch
of this path. It exists for the reverse check below.

**Known gap, stated in the index:** the outcome file does not record which brought-in commit gave a merge its
positives, so `event` has no linking-commit column. Do not reconstruct it.

## Invariants (the build fails, naming the rows)

1. Every path of the snapshot's tree is in `file` exactly once.
2. `in_universe = 1` implies `reason` is null, `loc > 0`, `scanned = 1`.
3. `in_universe = 0` implies a reason from the closed list.
4. Every `touch`, `event` and `pool` path is in `file` with `in_universe = 1`.
5. Every `event` and `pool` commit has a `touch` row for each of its paths.
6. `marginal` equals the recount from `event`, for every outcome.
7. `window_end > window_start`; usable commits > 0. (Defect log 59.)
8. Every `measure` row's path is in `file`; a measure the scorer reads has a row for every universe file,
   with a value or with `absent_means`.

Reported in the data card, not failing: universe files with `history_can_touch = 0` (defect log 2, section 6
item e); files excluded by a GitHub pattern, by pattern (defect log 55); commits out of time order; the share
of universe files with a nesting value (defect log 58).

## The data card

`datacard.json` and `datacard.md` per repo, computed from the tables only, **containing no path and no commit
hash from a protected table**: files by reason; the five GitHub patterns that excluded most files, with
counts; universe files the history cannot touch; scan completeness measured against the tree (not against the
pipeline's own unit rule — defect log 56); usable commits, bot share, merge share; window start, end and
length; per outcome the marginals; the largest directory's share of the universe; the share of universe files
with each measure present.

## Tests (part of the deliverable), all on control repositories through the sandbox

1. **Against the manifest, base repository** (Python and C, generator 1.3.0): `file.in_universe` equals the
   manifest's `is_unit` on every path; `file.loc` equals the manifest's line count plus one (the engine's
   convention, reported in `harness_report.md`); `event` under HP equals the outcome file's own list exactly,
   and differs from the manifest's expected positives only in rows whose cause is one the harness report
   already names (window offset, rename after the snapshot, no file at the snapshot) — each difference
   classified, none unexplained.
2. **Mutations:** `generic_dir_names` — the dropped files appear in `file` with reason "vendored" and the
   matching pattern, and the data card counts them; `vendored_half` — the imported files are in the universe
   and the data card's largest-directory share shows it; `bot_merges` with a supplied snapshot — invariant 7
   fails the build; `merge_workflow` — `event` rows marked inherited exist.
3. **Hash stability:** the same table built from rows in reverse order, and with whole numbers supplied as
   reals, has the same hash; changing one value changes it.
4. **Invariants bite:** for each invariant, a table with one planted violation fails the build and the message
   names the row.
5. **Determinism:** two runs on the same control repository give identical hashes for every table.
6. **No leak in the data card:** no string from a protected table's key columns appears in it.
7. **Nothing is recomputed:** the builder contains no fix-reference pattern, no keyword list, no floor number
   and no tree-wide threshold of its own (a test greps for the registered values and the pattern strings).

## Deliverables

```
tools/tables/
  schema.py       columns, types, key order, the closed reason list
  canon.py        canonical rows and the hash
  build.py        the stage: python tools/tables/build.py --repo NAME   (run inside the sandbox by the harness)
  invariants.py
  datacard.py
  README.md
  DECISIONS.md    every choice this document did not make; every column left out and why
tests/test_tables.py
```

One small, listed change to the harness is allowed so that it can run the new stage: a `--tables` option in
`tools/harness/run.py`. No other file outside `tools/tables/` and `tests/test_tables.py` is edited, and no SA3
tool at all.

## Rules for the builder

- Everything in `harness_spec.md`'s rules applies: SA3 code only inside the sandbox; never the real study
  directory, the rest of laws-study except the engine export, the corpus, the pool or `~/.blind`; no network;
  one pipeline run at a time; no commits.
- Read `tools/harness/README.md` and `DECISIONS.md` first: they say how the pipeline is run and which shims
  exist. Read `docs/process/harness_report.md` for what is already known to differ and why.
- Do not make a row agree by changing what is compared. A difference without a named cause is a finding.
- When finished, report: what was built; the test results; for a base Python and a base C repository the row
  count and hash of every table and the data card's numbers; every column left out and why; every difference
  from the manifest by cause; anything in this document that is wrong, ambiguous or impossible.
