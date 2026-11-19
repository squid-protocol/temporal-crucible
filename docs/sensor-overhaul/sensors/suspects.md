# Sensor design: where to look first (the repair radius as a worklist)

**Status: design with evidence and a real-change mock-up (section 6); exploratory; nothing built. Owner decisions 2026-11-18 recorded in section 13.** Extends the change report (`gitgalaxy change`, section "REACH OF WHAT CHANGED"). Evidence: `sensors/ripple_radius.md` (the log, with a prediction written before every run), `sensors/lang_validation_output.txt`, `sensors/callgraph_audit_output.txt`, `sensors/retrieval_added_deleted_output.txt`, `sensors/retrieval_lift_output.txt`. Public write-up: `docs/wiki/08-29-repair-radius.md` (engine PR #8636). Mock-up: `tools/sensor/suspects_mockup.py`.

## 1. The question the sensor answers
*If something breaks after this change, which functions and files should I look at first?*
Not "will this change break something". Everything below is measured on changes that **were** later repaired; the research found that whether a change needs a repair is predicted by its size and by nothing else tested that is usable (section 3). The sensor is a **worklist for after a failure**, ordered by where past repairs landed, not a risk score. That fits the guide: one construct, plain units, a drill-down by construction, "no risk score".

## 2. What exists today
| Source | Says |
|---|---|
| `gitgalaxy change` (`gitgalaxy/tools/sensors/change.py`, wiki 08-26) | per touched function: callers (named, up to 5), "more one hop out", size and complexity change; debt markers; mechanical share. **No list of functions that are not directly called or calling.** |
| Reach sensor (`sensors/reach.md`) | callers, files depending, 1 to 2 hop ripple, header flag: a property of a function, not of a change |
| Scan database | `function_data` (name, file, size), `fcall_data` (call edges with resolution `step` and number of `candidates`), `file_data` |
| Third-party | repowise describes a symbol-level blast radius built from callers and from files that historically change with the diff's files; I found no published accuracy for it. In our data historical co-change was **not** the better locator (DPDK and OpenSSL: co-change partners less often repaired than same-file functions of similar size, 0.76 and 0.36; Mesa 1.04) while the call-graph neighbourhood was 1.4 to 1.8. Ideas only; their code is AGPL and is not read. |

## 3. What the research says
| Finding | Numbers | Where |
|---|---|---|
| **A ranking finds the repaired function** (same file as a changed function, then call distance, then size) | modified functions, kernel, DPDK and Mesa pooled (22,532 pairs): repaired function in the **top 20 of about 30,000 to 110,000 for 45%** (size alone 0.2%); added or deleted functions (DPDK, Mesa): **44 to 53%** (size alone 0.2 to 0.4%) | `retrieval_lift_output.txt`, `retrieval_added_deleted_output.txt` |
| **Not only size** | among functions of the same size: call distance alone AUC 0.73 (0.66 to 0.70 for added or deleted), with the file 0.85 | same |
| **Files** | a repaired file among the top 20 files for 67 to 80% of added or deleted functions (random 0.5 to 1.3%); counting only repairs in **other** files 39 to 50% | same |
| **The neighbourhood absorbs added and deleted functions too** | radius within 2 calls: added 2.2 (DPDK) and 3.0 (Mesa), deleted 2.8 to 3.2 and 2.9 to 3.1 (modified: 1.6 and 1.8); unchanged by six rename filters | `added_deleted_sensitivity_output.txt` |
| **Size sets the shape** | radius by size of the change, under 20 lines to 500 or more: kernel 3.06 to 1.31, Mesa 2.16 to 1.34, DPDK 2.09 to 1.23; repeated repairs: 14% of small changes against 49 to 78% of 500+ line changes | `ripple_radius.md` |
| **What the repair does** | callers add a check on a changed result 8 to 14 times as often; repairs share a specific name with the change 80% (same function) to 45% (no call path), 6.7 times an area-matched baseline | same |
| **Other languages** | radius within 2 calls with blame-based causes: Python 1.70, Go 1.50 (C with the same method 1.50); callers-first **not** replicated; Java underpowered (110 pairs), Rust uninformative | `lang_validation_output.txt` |
| **The call graph** | edge recorded for 96 to 99% of name-resolvable calls in C, 86 to 97% in Python, Go and Java, **34% in Rust**; resolved to one target 93 to 99% (C) against 33 to 62%; admitting ambiguous edges leaves the Python radius unchanged | `callgraph_audit_output.txt` |
| **What it cannot say** | whether a change will need a repair: size alone, AUC 0.72 to 0.77; neighbourhood and process add 0.00 to 0.003; the kind of change adds 0.016 to 0.027 but vanishes on a label without trailers | `ripple_radius.md` |

## 4. Design stance (inspired, not copied)
Our own vocabulary and construction. The list is built from our measured radius (a ranking by file, call distance and size), not from co-change or churn scores; it ships with its evidence and, optionally, its **track record in this repository** (the guide's "a flag without a measured record is not shipped").

## 5. The sensor
**Input:** a change (commit, range or working-tree diff) and the engine scan of the commit and of its parent, as `gitgalaxy change` already uses.
**Events** (the "changed set"): functions modified (as the change report finds them); functions **added** (graph of the commit); functions **deleted** (graph of the **parent**: the former neighbours). Moves and renames are excluded when recognised (token overlap 0.7 recovers 77% of git-confirmed moves; the result does not depend on it).
**Candidates and order.** Every function of the graph except the changed ones. Sort key: (1) in the same file as an event function; (2) call distance to the nearest event function, 1, 2 or 3 calls, either direction; (3) function size, largest first. **Only candidates with a reason are listed** (same file, or within 3 calls): below that the list is size alone, which finds 0.2% in its top 20 (section 3).
**Reason tags** on each suspect (plain words): *same file as X*; *calls X*; *called by X*; *N calls from X*. Version 2: *uses a name this change touched* (needs the diff text; the research finds a shared name in 45 to 80% of repairs, 6.7 times an area-matched baseline).
**Size note** from the lines changed: under 20 lines, repairs after changes this small stay close and are usually single; 100 to 499, they spread (radius 1.7 to 1.9 against 3 for small); 500 or more, "expect repeated, scattered repairs" (half to three quarters needed two or more repairs). Numbers per band in the output, with their source.
**Output sizes:** top **20 functions** and top **10 files** (files ranked by their best-ranked function), with "N more candidates with a reason".
**Graph used:** unique-target edges only (the default of every result); the report says how many ambiguous call edges it did not follow ("k of the n calls at these functions have several possible targets"). Admitting them is neutral in Python and costs 0.1 to 0.2 of radius in Go and Java.
**Per-language state** (rule 7, "not measured" is a state): **C: measured**. **Python, Go: shown with a note** (the radius is validated; whether callers or callees come first is not, so both are tagged; the share of calls resolved to one target is printed). **Java, Rust, anything else: "not measured"**, with the reason (call graph resolves too few calls). The gate is a property of the scan, not of the language name: the list is shown only if the scan resolves at least a stated share of call sites (threshold to be fixed against the call-graph benchmark in section 11).
**Other "not measured" cases:** a changed function that is not in the graph; a sweep (more than 60 changed functions or a repeated call swap): "mechanical change of N functions: no suspect list" (sweeps carry no consistent signal); no scan of the parent.
**Optional track record (version 2):** `gitgalaxy backtest` replays the sensor on the repository's own history: for fix commits (subject contains "fix"), the cause is found by blame (SZZ style, calibrated against trailers on C: radius within 1% and 14%) and the report says "in this repository, the top 20 contained a later-repaired function for X% of N past fixes". Costs about 200 ms of blame per fix hunk.

## 6. Mock-up from real changes (DPDK; pairs drawn with a fixed seed, causes under 100 lines; `suspects_mockup_output.txt`)
Four changes, the whole list and what happened, not selected by outcome:
| change | the actual repair | rank of the repaired function (of about 26,000 to 47,000) | rank of its file |
|---|---|---|---|
| bnxt RSS table ops (3 functions, 93 lines) | `bnxt_rss_hash_update_op`, 575 days later | **2** | **2** |
| iavf command after PF reset (4 functions, 15 lines) | `iavf_dev_close`, `iavf_hash_destroy`, `iavf_handle_pf_event_msg`, 21 days later | **49, 45, 59** | **1, 3, 2** |
| virtio-user control queue (1 function, 4 lines) | four functions in the **sibling file** `virtio_user_dev.c`, 398 days later | **1,346 to 20,680** (a miss) | **638** of 813 |
| graph stats for mcore dispatch (5+ functions) | `rte_graph_cluster_stats_get`, `..._create`, `stats_mem_init`, 365 days later | **1, 5, 9** | **1** |
Two of the four are near the top, one has the file first but the functions between 45 and 59 (the file is right, the list of functions is long), one misses entirely because the repair was in a **sibling file of the same directory** that neither calls nor is called by the changed function. Two lessons carried into the spec: (a) cut the list where reasons run out: the file list beyond the first two or three files in example 1 is size noise (`bnx2x.c`, `eal_memory.c`, `t4_hw.c`); (b) a candidate improvement, **same directory**, is untested (section 10).

## 7. What it does not claim
- That the change will break anything, or that a function in the list is buggy. The list is ordered by where past repairs landed.
- That the repaired function is in the list: about half of the time it is in the top 20 (C), the other half it is not.
- Anything for languages whose call graph resolves too few calls.
- A cause: shared files and call links are associations (a shared feature, interface or author explains much of them).
- That the neighbourhood predicts whether a repair is needed: size does; the neighbourhood adds nothing (+0.00 to +0.003 AUC).

## 8. Engine work
Section in the change report after "REACH OF WHAT CHANGED" (`gitgalaxy/tools/sensors/change.py`); data from the scan database tables above; a breadth-first search over the call graph for distance 1 to 3 (sparse matrices, tens of milliseconds for 60,000 functions); a `--suspects N` option; JSON and SARIF-free (it is a worklist, not a finding). Tests: a synthetic graph with known ranking, the gating rules, the sweep rule, the "not measured" states, deleted functions from the parent graph; the golden output for the change report fixtures; wiki page and the change report page updated; baseline-gated audits as for every engine change. Related engine issue: call-graph resolution of method calls (Python, Go, Java) and Rust receiver and path calls (section 11).

## 9. Acceptance status (guide section 5)
| # | Test | Status |
|---|---|---|
| 1 | Not degenerate | not applicable (per change) |
| 2 | Construct validity | **met for C**: top-20 hit rates and within-size AUC (section 3); Python and Go: radius yes, direction no; not for Java and Rust |
| 3 | Not redundant | **to check**: overlaps the Reach list (callers one hop); rule: one worklist (a section of the change report), no new file-level gauge; measure the share of the top 20 that are not callers or callees of a changed function (candidates from the same file only) |
| 4 | Not just a keyword density | not applicable |
| 5 to 6 | Stable, role | not applicable |
| 7 | Actionable | by construction (ranked functions and files with reasons) |
| 8 | Outcome relation reported, never claimed | **met**: where (ranking), not whether (size), stated in the output |
| 9 | Replicates on the population | **not yet**: DPDK, Mesa and the kernel for C; sphinx, scapy, sqlmap and prometheus for the radius only |

## 10. Open questions
1. **Same directory** as a candidate feature (mock-up example 3): untested; cheap with the existing harness.
2. The "uses a name this change touched" tag: the evidence is on repairs (45 to 80% share a name), not yet a ranking feature; test whether it improves the top 20.
3. **Gating threshold** on the share of resolved call sites: needs the call-graph benchmark below.
4. Kernel scale and Python/Go ranking numbers (only the radius was measured there).
5. Whether the track record belongs in version 1 (cost, and SZZ noise).
6. The name of the section: "Suspects", "Where to look first", or "Repair radius".
7. Sweeps and large changes: the list is long and the repairs scatter; the cut rule and size note decide.

## 11. Back-test gate and the call-graph benchmark (fixed before any engine work)
**Gate before shipping.** Held-out repositories, not used to design the ranking: C: **libgit2, redis, libxml2** (quarterly scans exist; causes by blame, the label calibrated on DPDK and curl); Python: **sphinx, scapy, sqlmap** (used only for the radius, not for ranking). Per repository, the same ranking test as `retrieval_lift.py` (function top 20 and top 100, file top 10 and 20, AUC, within-size AUC), against size alone. **Ship for a language if, pooled over its held-out repositories:** function top-20 share **at least 30%** for C (the trailer value is 45 to 53%; blame labels and a weaker repository mix are allowed some loss) and **at least 25%** for Python and Go; at least **50 times** the share of size alone; within-size AUC of call distance **at least 0.65** (C) and 0.60 (Python, Go). A language that misses stays "not measured".
**Call-graph benchmark.** The same ranking test, repeated for any new call graph (the other call-graph effort, a changed resolver, ambiguous edges admitted), measures the **downstream** value of the graph without an oracle: the top-20 hit rate by language, before and after. Rust and Java currently cannot be measured at all (graph recall 34%, unique 9% for Rust; 33 to 34% unique for Java); that is the number to move.

## 12. Plan
1. Owner decisions (below).
2. Run the held-out back-test; record it against the gate (pre-registered above).
3. Test the same-directory feature and the shared-name tag (two small experiments on the existing harness); include only what raises the top 20.
4. Engine issue and pull request: the section, tests, wiki; C first, Python and Go next if they pass.
5. Track record (`gitgalaxy backtest`) as a second pull request.
**Owner decisions needed:** the name; the gate numbers (section 11); whether the track record is in version 1; whether it appears only in `gitgalaxy change` or also as a `suspects` subcommand; the order against the open wiki PR #8636 (the page this sensor would link to).

## 13. Owner decisions (2026-11-18)
1. **Name: "Where to look first"** (the section and the subcommand; "repair radius" remains the name of the finding).
2. **Gate numbers (section 11) approved as written.**
3. **Two pull requests**: the first with the list (functions and files, reason tags, size note, per-language states); the second with the per-repository track record (`gitgalaxy backtest`).
4. **A subcommand** of its own (it is not only a section of `gitgalaxy change`; the change report may link to it).
5. **Wiki PR #8636 merges first** (label `shepherd:merge` added 2026-11-18); the sensor's documentation links to that page.
**Next:** run the held-out back-test against the gate; test the same-directory feature; then the engine issue.

## 14. Back-test result against the gate (2026-11-18; `sensors/backtest_gate_output.txt`; `tools/sensor/backtest_gate.py`)
Held-out repositories, causes by blame (SZZ style, 2,500 fix-like commits per repository at most), the validated ranking against size alone, repaired functions outside the changed set; the call graph of the nearest quarterly scan at or after the cause.
| language (repositories) | pairs ranked | candidate functions per pair (median) | **function top 20: size alone / call distance alone / same file, distance, then size** | within-size AUC of call distance | **files, top 20** (size alone / the ranking); top 10 of the ranking |
|---|---|---|---|---|---|
| **C** (libgit2, redis, libxml2) | 1,604 | 2,605 to 4,444 | **5.4% / 31.3% / 47.3%** | **0.737** | 61.4% / **92.1%**; **83.6%** |
| **Python** (sphinx, scapy, sqlmap) | 1,513 | 1,912 to 4,402 | **6.6% / 26.1% / 35.7%** | **0.644** (scapy 0.589) | 47.7% / **70.7%**; **60.9%** |
| **Go** (prometheus) | 380 | 3,295 | **4.5% / 31.9% / 42.4%** | **0.692** | 32.0% / **78.7%**; **70.3%** |
Per repository, function top 20 of the ranking: libgit2 53.4%, redis 43.5%, libxml2 46.9%; sphinx 44.1%, scapy 43.9%, sqlmap 27.9%; prometheus 42.4%.
| gate criterion (section 11) | C | Python | Go |
|---|---|---|---|
| function top 20: at least 30% (C), 25% (Python, Go) | **47.3% pass** | **35.7% pass** | **42.4% pass** |
| at least 50 times size alone | 9 times **fail** | 5 times **fail** | 9 times **fail** |
| within-size AUC of call distance: at least 0.65 (C), 0.60 (Python, Go) | **0.737 pass** | **0.644 pass** | **0.692 pass** |
**By the letter of the gate every language fails, on one criterion only: "at least 50 times the share of size alone".** That criterion was badly specified, and it is recorded as it came out. Size alone finds 4 to 8% in the top 20 of these repositories (2,000 to 4,400 candidate functions) where it found 0.2 to 0.4% in the research repositories (30,000 to 110,000 candidates): a ratio to size alone depends on how many candidates there are (117 to 290 times in the large repositories, 5 to 9 times here), not on the quality of the ranking. The same ranking is **29 to 42 percentage points above size alone** in every language here (C +41.9, Python +29.1, Go +37.9), and clears the absolute top-20 and the within-size criteria by 10 to 17 points and 0.04 to 0.09 AUC.
**Proposed amendment (not applied; needs the owner's approval, and is proposed after seeing these numbers):** replace "at least 50 times size alone" with a scale-free pair: **the ranking's top-20 share at least 15 percentage points above size alone's and at least 3 times size alone's**. Under it all three languages pass (differences 41.9, 29.1 and 37.9 points; ratios 9, 5 and 9). An alternative without post-hoc risk is to re-run the gate on repositories of the research repositories' size (tens of thousands of functions: not available among the held-out ones).
**Reading.** The sensor's core claim holds out of sample and out of language for C, Python and Go: the repaired function is in the top 20 for about half (C 47%) to a third (Python 36%) of the cases, and the file is in the top 10 for 61 to 84%. Python is weakest (the call graph resolves fewer calls: scapy's within-size AUC of 0.589 would fail the 0.60 bar on its own). Caveats: blame labels; small repositories flatter the top-20 figures; sqlmap (27.9%) shows a project where the list is much less effective; the files are fewer in these repositories (100 to 900), which inflates the file figures.

## 15. Gate amendment (owner approval 2026-11-18)
**Approved.** The criterion "at least 50 times the share of size alone" (section 11) is replaced by: **the ranking's function top-20 share at least 15 percentage points above size alone's and at least 3 times size alone's.** The other two criteria stand (absolute top-20 of at least 30% for C and 25% for Python and Go; within-size AUC of call distance at least 0.65 for C and 0.60 for Python and Go). The amendment was proposed after the back-test numbers of section 14 were seen; the owner approved it knowing that. **With the amendment the gate is met by C (+41.9 points, 9 times), Python (+29.1, 5 times) and Go (+37.9, 9 times).** Python has the thinnest margin (within-size AUC 0.644 against 0.60; scapy alone 0.589). The original criterion's failure and the reason (it depends on the number of candidates) stay recorded in section 14.

## 16. Same-directory test and its design consequence (2026-11-18; `ripple_radius.md`, `same_directory_output.txt`)
Directory proximity as a tie-break within each call distance raises the **file** ranking for repairs in other files (top 10 files: DPDK 51.7% to 63.0%, Mesa 30.9% to 37.3%, Go 42.4% to 46.6%, Python 34.0% to 38.6%, C held-out 51.0% to 52.7%) and the top 100 functions for those repairs (DPDK 20% to 39%), but barely moves the top 20 functions (+0.0 to +2.4 points); nothing changes for repairs in the changed files. **Change to the spec (section 5):** the **file list** is ranked by (a changed file, call distance of its nearest function, same directory as a changed file, file size); a suspect file may carry the reason "same directory as X's file"; the function list is unchanged. The graded directory category adds nothing over the binary one.
