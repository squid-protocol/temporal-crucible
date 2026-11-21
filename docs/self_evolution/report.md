# GitGalaxy's own functions over time: evolution report (EXPLORATORY; nothing registered; 2026-11-20)

What this is: one place for how the engine's functions grew, changed and were documented over its first eight months, from 180 daily scans of GitGalaxy by one fixed scanner (ENGINE_PINS.md), with function identity tracked through renames and moves (lineage ledger). Sections 2-8 are descriptions of one repo; none tests a registered hypothesis. Units: functions of 3+ lines in `gitgalaxy/` (or early `backend/`), excluding tests, `standards/` pattern tables and `__init__.py`; "SCAN" = the scanner core, "TOOLS" = `gitgalaxy/tools/` (translator and utilities). Eras follow the registered GG-H1/H2/FLT-H1 split: Gemini < 07-06, Claude 07-22..09-26, fleet from 09-27.

## 1. Growth
Engine functions: 170 (Mar 21) -> 242 (May 10) -> 313 (Aug 22) -> 2,524 (Oct 12) -> 3,926 (Nov 20). The fleet era accounts for 71% of all births, and 72% of those are in the translator subtree. Deaths are rare: 116 against 3,861 births (3%).

## 2. Where new functions go
Births land 51% in new files and 49% in existing ones (scanner core 45/55, translator 54/46). The scanner core mostly grows by adding to files that already exist; the translator grows by adding files. The other repos' held-out range is 44-56% new-file births, so this is not unusual.

## 3. How functions change after birth
Share identical (size and composition) to birth after 7 / 30 / 90 days: 82-87% / 62-75% / 26% (Gemini era; Claude-era 90-day n = 44 only). Survival stays 86-100%. TURN repos show 83-96% unchanged after a whole quarter, so GitGalaxy's functions change faster at comparable ages; the repo is young, AI-written and had a very high commit rate, so this compares authorship regimes and age as much as architecture.
Only 2.6% of function-day pairs involve any text change. Of 4,295 text-changing edits, 262 (6.1%) touch only comments or whitespace (Gemini era 194 of 1,054, 18%; Claude 42 of 1,013, 4%; fleet 24 of 2,159, 1%): edits became almost entirely code edits as the fleet took over (cause of the early share not checked; a formatting pass would produce it).

## 4. Call network density and hubs (per-snapshot means, every 6th daily snapshot)
| | functions | calls per function | mean callers (fan-in) | uncalled | top-1% share of all callers |
|---|---|---|---|---|---|
| Gemini era | 218 | 1.14 | 1.44 | 5% | 5% |
| Claude era | 344 | 1.18 | 3.84 | 3% | 21% |
| fleet era | 2,954 | 1.76 | 3.17 | 14% | 28% |
| first / last snapshot | 189 / 3,926 | 1.08 / 1.77 | 1.13 / 3.12 | 11% / 16% | 2% / 30% |
The network gets denser (calls per function +64%) and callers concentrate in a few functions (top-1% share 2% -> 30%; at 189 functions the top 1% is a single function, so the early figure is not comparable). More functions are called by nothing in the fleet era (14-16%), consistent with the translator adding many entry points.
Hubs: `galaxyscope.py` is the top fan-out file for its whole life and nothing imports it (fan-in 0); 14 -> 61 functions, mean function size 51 -> 88 -> 48 (peak then fall, the fall at the 09-27 snapshot). `detector.py` 30 -> 154 functions. The two controllers stayed flat at 9 and 4 functions for five months, then stepped on 09-28.

## 5. Sweeps
12.5% of code edits sit inside a weekly mass-edit (the same call changed in 10+ functions that week); TURN repos run 4-44%. Only three old->new renames cleared the threshold (17, 13 and 11 functions); the bigger sweeps are guard-adding passes (`len` added to 163 functions). 51% of sweep edits add a guard against 24% of organic edits, the reverse of the TURN repos.

## 6. Comments and documentation
| | documented | has docstring | mean docstring length | header comment |
|---|---|---|---|---|
| Gemini era | 60% | 66% | 15 words | 3% |
| Claude era | 61% | 66% | 29 words | 5% |
| fleet era | 64% | 66% | 35 words | 11% |
| first / last snapshot | 55% / 64% | 61% / 67% | 15.5 / 34.6 words | 2.6% / 13.8% |
Coverage is steady (about two-thirds of functions have a docstring) but the text got more than twice as long, and header comments rose from 3% to 14%. At birth 63-71% of functions are documented, and 30 days later 66-69%: documentation arrives with the function, not afterwards (gained 0-4%, lost 0-2%). The docstring text of a documented function changed within 30 days for 19% (Gemini), 7% (Claude) and 19% (fleet) of functions.
Not measured: pull-request and bot review comments (not pulled), code comments inside function bodies other than docstrings and header comments, and whether the verbosity comes from the model era or from a style rule.

## 7. Speed (summary of the timing work, details in docs/self_speed/)
Three traced steps in the scan cost (a compile-policy threshold, a file-screening rule, a comment-stripping rule) each came from 1-3 changed functions or rules, with function-level change unrelated to the size of the step. The timing pilot shows change in events, not drift. The sensitivity pass (language-crucible on 300 commits) is still running.

## 8. What this supports and what it does not
Supports (for this repo, descriptively): accretive growth with few deaths; core growth by thickening existing hubs, translator growth by new files; a denser call network with concentrating callers; steady documentation coverage with richer text; faster change after birth than the TURN repos.
Does not establish: any registered hypothesis; that the documentation or churn differences come from authorship regime and not from age or growth; fan-in hubness of the orchestrators (they are entry points). Import and call-link recall are incomplete, so network figures are lower bounds. Artifact: the call-network film and interactive page are built by `tools/selfhistory/evo/make_artifact.py`.
