# Handoff: MOD-1 panel, stopped mid-scan 2026-11-13

**State: 5 of 38 repos prepared.** Stopped for a machine shutdown, not by a failure.

## Resume with one command

```bash
cd /srv/storage_16tb/projects/temporal-crucible-wt-seat
source /srv/storage_16tb/projects/gitgalaxy/laws-study/venv/bin/activate
python tools/mod1_run.py --draw docs/draw40.json      # resumable; skips what is done
python tools/mod1_score.py                            # the registered test
```

`mod1_run.py` reads `docs/mod1_prep.json` and skips any repo already recorded, so re-running costs nothing
for finished work. Expect **20–45 minutes** for the remaining 33; the tail is the big trees (freebsd-src
307k commits, swift 199k, tensorflow 191k, kubernetes 136k).

## Done

- `ghostty racket macports-base sqlite tcpip_historical` prepared.
- `root` errored with "database is locked" — a stale writer from the first launch. **Delete
  `pilot/history/root.db` and `pilot/dbs/root.db` before resuming** so it harvests cleanly.

## Known problem to fix before trusting the result

**The language call is wrong for some repos.** `draw40.py` picks a repo's language by counting file
extensions, which picks up **vendored C inside non-C projects**: ghostty is Zig, racket is Scheme, both were
classified `c`. They then scan only the bundled C files, which fix commits never touch:

- ghostty: 581 files, **1 positive — under the floor**
- racket: 45,567 commits but only 22,655 touches (fewer touches than commits)

The registration says sub-floor repos are excluded and listed, so this is handled honestly — but if it
knocks out much of the **young-C** cell, the registered comparison loses power on a cell already short
(old-C had only 8 available, not 10).

**Fix if that happens**: classify by the repo's own source tree rather than raw extension counts (exclude
`vendor/`, `third_party/`, `deps/`, `extern/`), re-draw, and **re-register** — the current draw is fixed in
`docs/moderator_registration.md` and must not be quietly swapped.

## What is already registered and must not drift

`docs/moderator_registration.md` (commit 2265a69), written **before any drawn repo was scanned**:

- **MOD-H1 (primary)**: in-degree lift over LOC is lower in older repos. Supported iff the `old`
  coefficient's bootstrap 95% CI excludes zero.
- Outcome: `in_degree` AUC − `loc` AUC, **cascade label**, snapshot nearest the cut.
- Sub-floor repos excluded **and listed**, never rescued with a different label.
- Falsification stated: if `old` includes zero while repos keep splitting by sign, **age is not the
  moderator** — reported as a result, not a failure.

## Why this study exists

`struct_null.py` found call-graph in-degree beating LOC in four repos and losing in four, every one with a CI
excluding zero, pooling to **+0.006** — a null no repository exhibits. In those eight, age and language are
perfectly confounded (all four anti-predictive repos are old C). The 38-repo draw exists to separate them.
