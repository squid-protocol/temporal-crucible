# Stored tables, phase A

Each fact SA3's pipeline produces for a repository, in one table, written once, with a hash. Built to
`docs/process/tables_spec.md` (phase A: control repositories only, inside the harness sandbox). Every choice that
document did not make, and every column left out, is in `DECISIONS.md`.

## Use

```
python3 tools/control_repo/generate.py --out DIR --seed 11 --years 10 [--language c] [--mutation NAME]
python3 tools/harness/run.py --control DIR --work WORK --routes manifest --tables [--no-shim-lock]
python3 -m pytest -p no:cacheprovider tests/test_tables.py      # 14 tests, about 65 s
```

`--tables` adds one stage to route `manifest`, after the probe: `tools/tables/build.py --repo NAME`, run inside the
sandbox through its guard like every other stage. Its record is in `WORK/report/NAME.run.json` (stage `tables`).
Output: `WORK/manifest/study/sa3_tables/<repo>/`

```
index.json                 per table: file, hash, rows, schema version, protected; input-file hashes; code hash;
                           known gaps
datacard.json, datacard.md counts and shares only: no path, commit hash, link value or repo name
<table>.<hash16>.jsonl     repo, snapshot, file, measure, touch, marginal
protected/<table>.<hash16>.jsonl   link, event, pool
build_failed.json          instead of all the above, when an invariant fails (exit code 1)
```

`build.py` refuses to run outside the sandbox (it checks before importing any SA3 module). `schema.py`, `canon.py`,
`invariants.py` and `datacard.py` are pure and import no SA3 module.

## Files

- `schema.py`: tables, columns, types, key order; the closed reason list; which measures the scorer reads and
  what an absent value means for each.
- `canon.py`: canonical row bytes, the SHA-256, the writer (one file per build, named by hash, never written over).
- `build.py`: the stage. Reads `history/`, `sa3_scans/`, `sa3_outcomes/`, `meta_sa3/`, `sa3_nesting/` and the pool
  clone; calls `mod1_lift.frame`, `sa3_outcomes.universe`, `laws_units.Excluder.why` / `language_of` and
  `laws_history.harvest` unchanged.
- `invariants.py`: the eight invariants; each failure names its invariant and the row by key.
- `datacard.py`: the data card from the finished tables.

## The tables (key columns first)

| table | key | other columns |
|---|---|---|
| `repo` | repo | language, langs, units, unit_rule, first_parent, status, why, pool_tip, history_head, engine, hashseed, commits, bots, merges, first_parent_commits, merge_share, walk_out_of_time_order, pipeline_complete, pipeline_unit_files, pipeline_tree_unit_files, scanned_not_in_tree |
| `snapshot` | repo | sha, ct, cut_ct, window_start, window_end, usable_commits |
| `file` | repo, path | in_universe, reason, pattern, loc, language, scanned, in_archive, history_can_touch |
| `measure` | repo, path, name | value, absent_means, instrument, version |
| `touch` | repo, sha, path | ct, walk_pos |
| `link` (protected) | repo, sha, kind, value | n |
| `event` (protected) | repo, sha, path | hp, hp_allreverts, tier, how |
| `pool` (protected) | repo, sha, path | — |
| `marginal` | repo, outcome | n_files, n_commits, largest_commit_share, clears_floor |

`file.reason` (closed, in the order decided): `language`, `vendored`, `documentation`, `generated`, `test`,
`example`, `tutorial`, `gitattributes`, `not_in_archive`, `not_scanned`, `zero_loc`; `pattern` is the GitHub
linguist pattern for `vendored` and `documentation`.
