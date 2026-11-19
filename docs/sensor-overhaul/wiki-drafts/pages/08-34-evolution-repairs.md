> **Status: design and prototype, not shipped.** Draft for GitGalaxy's `docs/wiki/`, written 2026-11-19 against the evolution-report prototype (`tools/report/evolution_report.py` in the temporal-crucible `sensor-overhaul` worktree). Numbers come from `docs/sensor-overhaul/sensors/ripple_radius.md`. Exploratory unless a line says otherwise.

# Evolution report: repairs

## Matching a fix to its cause
A cause is named in the fix (`Fixes: <sha>`) or found by blame: `git blame -w -M` of the fix's removed lines at the parent, the commit owning most of them (older than the fix). Blame is run on a sample when a project names few causes.

## What the report shows
- **Lag histogram:** time from cause to fix. Median and the share over a year. The shape tells whether bugs are found in days (fuzzers, CI) or months (users).
- **Cause types:** the first verb of the causing commit's subject (feature, restructure, optimization, fix). For each, the share of fixes that land in the same function as the cause and the median lag.
- **Radius (with scans):** how much closer than chance a fix lands to the changed function, within one or two calls, against same-sized functions in the same file. See [repair radius](08-29-repair-radius.md).
- **`Cc: stable`:** where a project uses it, fixes tagged for stable took far longer than untagged ones (DPDK: 371 against 20 days since 2015): the tag marks bugs that reached a release.

## Measured behavior (exploratory unless noted)
- Repair radius 1.4 to 2.0 within two calls across large C projects and the DOOM lineages (replicated); blame-derived causes give the same radius as named ones (1.40 and 1.63 against 1.45 and 1.60).
- What clusters is the **causing** change: fixes of fixes are tight (75% in the same function, radius 2.0); fixes of features are scattered and late (41%, radius 1.36, 197 days). The fix's own kind (mechanism, shape) matters little.
- Detection regime: bugs found by fuzzers show a median lag of days (OSS-Fuzz: 3 days) and recency beats structure; bugs found by users show months and structure helps.

## Limits
- Only fixes with a findable cause are counted; fixes whose cause is outside the history are not "extrinsic" in this report, they are simply unmatched.
- Blame names where fixed lines last changed, not always the cause.
