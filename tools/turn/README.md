# TURN discovery tools (unfinished)

Exploratory scripts behind `docs/turn_discovery_2026-11-15.md` (sections 9-10). **Not reviewed, not registered, not a tool yet.**
They belong with the study because what the edit classes and sweep definitions should be is what the study is still learning.

* `ts_edits.py` tree-sitter diff of ledger-linked surviving functions, C family (`.c`, `.h`).
* `ts_edits2.py` the same for Python, Rust and Zig (grammar differences are not yet reconciled into one category table).
* `sweeps.py` mass-migration detector: the same call or macro changed in >= max(10, 1%) of a quarter's code-edited functions; prints the sweep share and the organic residual.

Dependencies: `tree-sitter`, `tree-sitter-language-pack`, and `structural_fingerprint.ledger` (structural-fingerprint-scanner, branch `ledger`, not yet merged).
Paths to the scan databases and the repository pool are hard-coded to the discovery machine; the scans were made with `historical-call-graph-gif`.
Thresholds (10 functions, 1%, 40% co-occurrence) are discovery choices. Callee names are matched as text; macros are not resolved.
`kw_split.py`, `kw_report.py`, `kw4.py`, `turn_score.py`, `score_report.py`, `set1.py`, `heldout_eval.py` and the loaders `what_changes.py`, `cascade2.py` are the rest of the discovery harness. They import each other and a scratchpad path; read them as a record of the method, not as a tool.

`forecast.py` (branch `turn/forecast` only) builds the function-level forecast ladder; see `docs/turn_forecast_firstlook.md`.
`sweep_audit.py`, `audit_report.py`, `sweep_exp.py` (branch `turn/forecast`): fix-label audit and sweep-exposure experiment; see `docs/turn_sweeps_and_fixes.md`.
`fix_catalog.py`, `cat_report.py`, `archetypes.py` (branch `turn/forecast`): fix-edit catalog and edit archetypes; see `docs/turn_fix_catalog_and_archetypes.md`.
`sweep_forecast.py`, `intent.py`, `swap_check.py` (branch `turn/forecast`): sweep forecast tests and intent rules; see `docs/turn_sweep_forecast.md`.
