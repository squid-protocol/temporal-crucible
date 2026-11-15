# TURN discovery tools (unfinished)

Exploratory scripts behind `docs/turn_discovery_2026-11-15.md` (sections 9-10). **Not reviewed, not registered, not a tool yet.**
They belong with the study because what the edit classes and sweep definitions should be is what the study is still learning.

* `ts_edits.py` tree-sitter diff of ledger-linked surviving functions, C family (`.c`, `.h`).
* `ts_edits2.py` the same for Python, Rust and Zig (grammar differences are not yet reconciled into one category table).
* `sweeps.py` mass-migration detector: the same call or macro changed in >= max(10, 1%) of a quarter's code-edited functions; prints the sweep share and the organic residual.

Dependencies: `tree-sitter`, `tree-sitter-language-pack`, and `structural_fingerprint.ledger` (structural-fingerprint-scanner, branch `ledger`, not yet merged).
Paths to the scan databases and the repository pool are hard-coded to the discovery machine; the scans were made with `historical-call-graph-gif`.
Thresholds (10 functions, 1%, 40% co-occurrence) are discovery choices. Callee names are matched as text; macros are not resolved.
The keyword-over-time scripts (`kw_split.py`, `kw_report.py`) are not here yet: they need the discovery harness's scan loader to be tidied first.
