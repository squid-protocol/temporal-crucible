# Design: `gitgalaxy lookfirst` ("Where to look first"; engine command, not yet built)

**Status:** design, 2026-11-18; owner decisions recorded (name, gate, two pull requests, a subcommand of its own, wiki 08-29 merged first). Research behind it: `sensors/suspects.md` (the sensor design and the real-change mock-up), `sensors/ripple_radius.md` (the evidence log, a prediction before every run), the public page `docs/wiki/08-29-repair-radius.md` (merged). Prototypes: `tools/sensor/suspects_mockup.py`, `backtest_gate.py`, `retrieval_lift.py`, `same_directory.py`. Tracking issue to file when approved. **CLI name `lookfirst` is a proposal** (one word, like `reach`, `change`, `libsurface`); the section title is "Where to look first".

## What it does
A read-only post-scan command, like `gitgalaxy change`, that answers one question for a change (a commit, a range, or the working-tree diff): *if something breaks after this change, which functions and files should I look at first?* Counts and ranked lists only; no score, no claim that anything will break.
`gitgalaxy lookfirst [REV | A..B] [--repo PATH] [--functions N=20] [--files N=10] [--json]`. It reads the engine scan of the commit and of its parent, as `gitgalaxy change` does (same inputs, same "not measured" handling).

## Measure
**Changed set** (the engine's own, from the change report): functions **modified**, **added**, **deleted**. Added functions use the call graph of the commit; **deleted functions use the graph of the parent** (their former neighbours). Moves and renames recognised by token overlap 0.7 are left out (the result does not depend on it).
**Candidate functions:** every function of the graph except the changed ones. **Order:** (1) in the same file as a changed function; (2) call distance to the nearest changed function, 1, 2 or 3 calls, either direction; (3) function size, largest first. **Only candidates with a reason are listed** (same file, or within 3 calls); the rest is size alone, which finds 0.2 to 0.4% in the top 20 in the research data.
**Candidate files:** ranked by (a changed file; the call distance of the file's nearest function; **same directory as a changed file**; file size). The directory tie-break matters for repairs in other files (top 10 files: DPDK +11.3, Mesa +6.4, Go +4.2, Python +4.6, C held-out +1.7 points; `suspects.md` section 16).
**Reason tags** (plain words): *same file as X*; *calls X*; *called by X*; *N calls from X*; for files *same directory as X's file*.
**Size note** from the lines changed: under 20 lines, repairs stay close and are usually single; 100 to 499, they spread; 500 or more, expect repeated, scattered repairs, with the numbers and their source.
**Graph:** unique-target call edges only; the report states how many call edges at the changed functions have several possible targets and were not followed.
**Per-language state:** C measured; Python and Go shown with a note (the radius is validated; whether callers or callees come first is not, so both are tagged); anything else, and any scan whose call graph resolves too few calls (initial rule, provisional: fewer than 20% of functions have a recorded caller), prints "not measured" with the reason. The threshold lives in one named constant, to be revised against the call-graph benchmark (below).
**Not measured / no list:** a changed function not in the graph; a sweep (more than 60 changed functions, or a repeated call swap: "mechanical change of N functions: no suspect list"); no scan of the parent.
**Output** (real example, DPDK; `sensors/suspects_mockup_output.txt`):
```
CHANGE 358ff83fe8  graph: add stats for mcore dispatch model
WHERE TO LOOK FIRST (ranked: same file, then call distance, then size)
   1. rte_graph_cluster_stats_get   lib/graph/graph_stats.c   20 lines | same file as a changed function; calls a changed function
   2. __rte_graph_mcore_dispatch_sched_node_enqueue ...        13 lines | same file ...; calls a changed function
   ...
FILES: graph_stats.c; rte_graph_model_mcore_dispatch.c; graph_debug.c; rte_graph_worker.c; ...
```

## Validation required before it ships (registered gate, owner approved; amended 2026-11-18)
Held-out repositories not used to design the ranking: **C** libgit2, redis, libxml2; **Python** sphinx, scapy, sqlmap; Go prometheus; causes by blame (SZZ style), the same ranking test as `retrieval_lift.py`. Pooled per language: function top-20 share **at least 30% (C), 25% (Python, Go)**; **at least 15 percentage points and 3 times** size alone's top-20; within-size AUC of call distance **at least 0.65 (C), 0.60 (Python, Go)**. A language that misses stays "not measured". Back-test result already recorded (`backtest_gate_output.txt`): C 47.3% (+41.9 points), Python 35.7% (+29.1), Go 42.4% (+37.9); the gate is met.
**Parity check for the pull request:** the engine implementation, run on the same held-out repositories, reproduces the research harness's function top-20 within 1 point (it is the same ranking).

## Slices (five hand-written files each at most)
1. **Pull request 1, the list:** `gitgalaxy/tools/sensors/lookfirst.py` (changed set from the change report, graph search to distance 3 with sparse matrices, the two orderings, reason tags, size note, per-language states), `cli.py` registration, `tests/tools/test_lookfirst.py` (a synthetic graph with a known ranking, the gating rules, the sweep rule, the "not measured" states, deleted functions from the parent graph, the directory tie-break), the wiki page `08-30-where-to-look-first.md`; nav and index in a docs follow-up; the change report links to it.
2. **Pull request 2, the track record:** `gitgalaxy backtest`: replays the sensor on the repository's own history (fix commits by subject, causes by blame) and prints "in this repository, the top 20 contained a later-repaired function for X% of N past fixes". Costs about 200 ms of blame per fix hunk. Separate because it is slow and has its own failure modes (SZZ noise).

## Not in scope (stated so it is not asked for)
* A risk score, or any statement that a change will break something: whether a change needs a repair is predicted by its size and by nothing else tested; the neighbourhood adds nothing (+0.00 to +0.003 AUC).
* Co-change or churn as a ranking input (the call graph beat co-change as a locator in the research data).
* **A sibling-project prior** (the repair history of related projects as a second ranking, DOOM-R3: a real signal, 28.5% in the top 20 on its own, but only a post hoc rule improved the local ranking, and it is not yet confirmed): a possible later phase, research only.

## Dependencies and risks
* **Call-graph quality bounds the sensor.** Python, Go and Java record most calls but resolve only 33 to 62% to one target; Rust records about a third. The engine's call resolver work (method calls through receivers; Rust receiver and path calls) lifts the ceiling; the same ranking test is the benchmark (top-20 hit rate by language before and after) and needs no oracle tool.
* Quarterly-scan-based research graphs differ slightly from the graph of the commit itself (calls added between the commit and the scan); the engine uses the commit's own graph, so the parity check is on the ranking, not on the graph.

## Open questions
* The CLI name `lookfirst`; whether `gitgalaxy change` prints a one-line pointer to it.
* JSON schema for `--json` (functions, files, reasons, notes, state).
* The provisional graph-quality threshold (20% of functions with a recorded caller) against the call-graph benchmark.
* Kernel-scale and Java/Rust measurements; the sibling-prior confirmation set (DOOM C++ lineages).

## Tracking issue (text to file when approved)
**Title:** `lookfirst`: a "where to look first" worklist after a change (design `docs/sensor-overhaul/engine-issues/where-to-look-first-design.md`)
**Body:** the "What it does", "Measure", "Validation", "Slices" and "Not in scope" sections above; **Class / Sibling gaps:** the class is post-change worklists built from the call graph; sibling gaps are the track-record command (pull request 2), call-graph resolution of method calls (Python, Go, Java) and Rust, and the sibling-project prior (research).
