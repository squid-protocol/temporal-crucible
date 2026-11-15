# TURN discovery phase: closing record (2026-11-16)

This closes the discovery phase that began as the TURN draft registration (PR #186). It records what was measured, what was learned, the tools, and what is still owed. **Nothing here is registered or scored; every number is discovery, from 13 repositories.**

## What was done
* **A function ledger** (persistent lineage ID per function across quarterly snapshots; structure proposes, body text or comments verify). Packaged in structural-fingerprint-scanner (branch `ledger`). Held-out check on six unseen repos: moves 98.9% right / 0.11% wrong; renames 84.4% right / 5.9% wrong (2.9% without one libxml2 reorganisation quarter); quarterly chain vs direct jump disagree 0-2% over four years.
* **13 repositories, one engine, quarterly:** 7 discovery (curl, redis, libgit2, impacket, sqlmap, ripgrep, tigerbeetle) and 6 held-out (expat, libxml2, scapy, sphinx, commons-io, prometheus). Languages: C, Python, Rust, Zig, Java, Go.
* **A tree-sitter edit classifier and a mass-migration ("sweep") detector** on the survivors the ledger links (C, Python, Rust, Zig, Java, Go).
* **A per-repo scorer** with bootstrap intervals for the identity, growth, settling-in, derived-function and print hypotheses, run on all 13 repos.

## What we learned about how repositories change
1. **Path-and-name identity mislabels code.** It overcounts deaths by 28-463% against lineage identity. Moves are near-perfectly recoverable.
2. **Growth is mostly new files** (births in new files 44-73%); **deaths are mostly whole files** (35-78%) or functions removed from surviving files.
3. **Most quarters are quiet** (median quarterly deaths well under 1% of functions in mature repos); young fast repos (tigerbeetle) are noisier. Moves/renames are bursty in about half the repos.
4. **Functions are mostly born finished.** Share still identical to birth (engine measurements): about 90% after a quarter, 59-89% after a year, 46-80% after two, 15-73% after four. The chance of a first change is highest in the first quarter (4-19%) and falls to 1-5% by quarter 8. Among first changes, 11-62% change keywords at the same length (in-place edits).
5. **Wiring is set at birth.** A function born with no callers still has none a year later in 95-100% of cases (12 of 13 repos); hubs stay hubs (94-99% in most repos, 79-81% in the two fast repos).
6. **Code changes in sweeps.** 4-44% of edits to surviving functions (median about 22%) are one call or macro swapped across many functions in one quarter; 84-98% of migrations take a single quarter, test-framework moves take 4-7. Organic edits change signatures more often than sweep edits (12 of 13 repos; redis is the exception).
7. **Sweeps explain the "retrofit" signal.** Alloc/cleanup/print families look rewritten in place only because of sweeps; with sweep edits removed the H6 gap vanishes in curl, libgit2 and libxml2.
8. **Keywords over time:** print density falls in 4 of 5 C repos; safety keywords have no common direction across 13 repos; branch and flux density fall in most repos.
9. **Pointer edits** change an if-guard in 43-51% of pointer edits versus 10-23% of other edits in 4 of 5 C repos (not libxml2); pointer-density change is not a rewrite effect (contradicted in redis and libxml2: surviving code and the repo moved in opposite directions).
10. **Several bounds set from the first repos did not replicate** (births in new files > 60%, 80% unchanged after four quarters, top-10% burstiness > 60%). The ranges across 13 repos are the finding; the proposal now states ranges, not tuned thresholds.

## Tools (all in `tools/turn/`; unfinished discovery code, hard-coded paths, see its README)
`ts_edits.py` / `ts_edits2.py` tree-sitter edit classifier (C family; Python, Rust, Zig, Java, Go); `sweeps.py` sweep detector; `kw_split.py`, `kw_report.py` keyword trends and births/deaths/drift split; `kw4.py` retrofit gap with sweeps removed; `turn_score.py`, `score_report.py` per-repo scorer; `set1.py` settling-in by age; `heldout_eval.py` ledger accuracy; `what_changes.py`, `cascade2.py` shared loaders. Ledger: structural-fingerprint-scanner, branch `ledger`.

## Documents
`docs/turn_discovery_2026-11-15.md` (sections 1-15, all measurements), `docs/turn_v3_proposal.md` (hypotheses, ledger gate and sensitivities, ranges note). `docs/turn_hypotheses.md` is the original draft and is superseded by the v3 proposal.

## Not done / owed before any registration
* The **LAWS seated panel** is not in the local pool; the confirmatory run needs it seated and scanned. No confirmatory test has run.
* **Power statement** from the first seated repos (checklist 10); **second design review** (waived by the owner for the original draft; the v3 proposal has had none); **code review** of the tools before any scorer runs on panel data.
* Held-out gaps: Rust/Zig have two discovery repos only; ledger rename recall is 84% and the wrong-link rate is 3-6%, concentrated in near-duplicate siblings (test methods, API wrappers).
* **Follow-on, on its own branch:** forecasting how much of a function's next change is predictable (ladder from climatology to git process); not part of this PR.
