# LAWS development-set dry run (Amendment 2 item 5) — ACC repos, panel engine

**Status: descriptive pre-draw check. Not a gate, no verdict, and it cannot change Amendment 2 items 1–4.**
Run 2026-11-10, before the sampling frame is built and before any panel repo is selected, scanned or labelled.

- **Engine:** gitgalaxy `b873edc5b059f79e49858fa8e124f6b3e3f3e24f` (the panel engine, recorded in
  `docs/laws_hypotheses.md`), history off, the six ACC repos at their pinned snapshots.
- **Scorer:** `tools/laws_dryrun.py`. It is ACC-2's scorer (node set, matching, oracles, `compare`) with ACC-3's Go
  oracle, reading the panel engine's scans and using **confident links only** (Amendment 1 item 1).
- **Not applied:** the LAWS M3 exclusions. The node set is ACC-2's, so these numbers compare with `docs/acc2.md`
  and `docs/acc3_hypotheses.md`, not with ACC-P.
- **Not covered here:** the engine's call-graph gate corpus and the admission-survey repos (C#, Kotlin, PHP), which
  item 5 also names. Their scorer is the gitgalaxy gate's, and no committed tool computes the three statistics on
  them yet.
- Data: `docs/laws_dryrun/result_acc_repos.json`.

## Result

Bars (ACC-H3): in-degree ρ ≥ 0.80, top-1% hub Jaccard ≥ 0.50, file-coupling κ ≥ 0.60.

| repo | language | precision / recall | ρ | hub Jaccard | κ | all three met | ambiguous links not used |
|---|---|---|---|---|---|---|---|
| libgit2 | C | 0.760 / 0.816 | 0.830 | 0.694 | 0.867 | yes | 0 |
| redis | C | 0.843 / 0.955 | 0.872 | 0.700 | 0.919 | yes | 0 |
| commons-lang | Java | 0.944 / 0.953 | 0.926 | 0.667 | 0.896 | yes | 6,200 |
| commons-io | Java | 0.923 / 0.929 | 0.898 | 0.824 | 0.880 | yes | 4,493 |
| prometheus | Go | 0.925 / 0.841 | 0.113 | 0.009 | 0.450 | no | 8,623 |
| sphinx | Python | not evaluable (PyCG fails, as in ACC-2) | | | | | |

Against ACC-2 and ACC-3 (engine `8f96d76ba`, every resolved link):

- **C:** unchanged within 0.02 on every statistic.
- **Java:** commons-lang moved from ρ 0.831, Jaccard 0.270, κ 0.504 (failed) to all three met; commons-io stayed met
  and rose on all three. Edge precision rose from 0.746 / 0.808 to 0.944 / 0.923.
- **Python:** still no oracle.
- **Go:** see below.

## Go: the statistics depend on whether the oracle's CHA pass returns edges

ACC-3 scored prometheus with `callgraph -algo=static` as direct edges and `-algo=cha` minus static as dynamic
edges. In ACC-3 the CHA pass contributed **0** edges after the in-repo filter, which `docs/acc3_hypotheses.md` called
implausible for Go. In this run the same command (both passes exit 0) contributed **14,929** dynamic edges on
matched functions, beside the same 7,040 direct ones.

| reference | matched functions | ρ | hub Jaccard | κ | precision / recall |
|---|---|---|---|---|---|
| static + CHA (the registered oracle, this run) | 4,767 | 0.113 | 0.009 | 0.450 | 0.925 / 0.841 |
| static only (diagnostic, one-off, not registered) | 3,984 | 0.805 | 0.466 | 0.852 | 0.911 / 0.841 |
| ACC-3 (old engine, every link; CHA returned nothing) | 3,984 | 0.709 | 0.269 | 0.821 | 0.613 / 0.813 |

Reading: on static calls the panel engine's Go graph is close to the bars (hub Jaccard 0.466 against 0.50). CHA
adds an edge to every method that could implement an interface call, and those edges set the reference's in-degree
ranking; the engine's confident links hold none of them (8,564 `receiver` links are ambiguous and not used).

**What this means for ACC-P (not decided here).** ACC-P is the language gate. As registered, Go's result depends on
whether the CHA pass returns edges, which differed between two runs of the same command on the same snapshot. The
reference for dynamic dispatch needs to be stated before the draw (for example a named, more precise algorithm, or
direct edges only for the three statistics), by a dated amendment. Java's reference (java-callgraph) is not
affected in this run.
