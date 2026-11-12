# ACC-P — the LAWS language gate: first run, and why it does not yet decide anything

**Type: confirmatory measurement gate** (`docs/laws_hypotheses.md` Amendments 0–2, 4 and **11**). Panel engine
`b873edc5b`. Repos are draws 1 and 2 of each language's seeded order. Run 2026-11-11.
Raw: `docs/accp_result.json`, `docs/accp_diagnostics.json`. Tool: `tools/accp_eval.py`.

**Read this first: no language is gated by this run**, but C is now one snapshot short rather than
unmeasurable. After D1 showed the C oracle was never running as its own registration specifies, the oracle was
fixed (§7) and C re-run: **pure-data @2026Q4 is a valid pass on every statistic** — precision 0.971, recall
0.889, ρ 0.955, hub Jaccard 0.763, κ 0.923, with parse coverage 102% of the engine's `.c` files. Its 2007
snapshot lands at **79.5%** against the 80% coverage bar, half a point short, and the bar is not moved. Go has
one scored snapshot and one repo that cannot be oracled at all; Java and Python cannot run their oracles.
Amendment 11 (made **after** this run, marked post-result in the register) moved the early-snapshot rule, and
§7 shows why that was necessary but **not sufficient**.

## 1 · What ran

16 of 16 snapshots exported and scanned with the panel engine. Evaluable by the oracle:

| language | evaluable | why the rest failed |
|---|---|---|
| C | 4 / 4 | — (but see §3: the comparisons are invalid) |
| Go | 1 / 4 | 2016 snapshots: `no modules specified` — Go modules did not exist. syzkaller 2026: cgo |
| Java | 0 / 4 | 2011/2022: no build file. 2026: gradle fails, `mvn rc=1` (D2) |
| Python | 0 / 4 | PyCG `ImportManagerError` on all four |

## 2 · The statistics, as measured

| snapshot | prec | recall | ρ | hub J | κ | H1 | H3 |
|---|---:|---:|---:|---:|---:|---|---|
| pure-data @2007Q4 (C, **coverage 79.5% — invalid**) | 0.986 | 0.953 | 0.957 | 0.963 | 0.973 | pass | pass |
| **pure-data @2026Q4 (C, coverage 102% — valid)** | **0.971** | **0.889** | **0.955** | **0.763** | **0.923** | **pass** | **pass** |
| vulkan-loader @2021Q4 (C, coverage 10.5% — invalid) | 0.766 | 0.936 | 0.757 | 0.500 | 0.645 | fail | fail |
| vulkan-loader @2026Q4 (C, coverage 9.5% — invalid) | 0.771 | 0.942 | 0.638 | 1.000 | 1.000 | fail | fail |
| **yagpdb @2026Q4 (Go)** | **0.843** | **0.981** | **0.636** | **0.250** | **0.469** | **pass** | **fail** |

**The Go row is the one substantive result.** Its edges agree with the oracle very well — precision 0.843,
recall 0.981 — while its *network* statistics do not: hub Jaccard 0.250, κ 0.469, ρ 0.636. The engine finds
the right calls and builds a measurably different graph. **The network statistics are the half LAWS depends
on**, so this is the finding to take seriously, from one snapshot, pending replication.

## 3 · Why C's four rows do not count (D1)

Amendment 11 fixed the threshold before it was measured: fatal-diagnostic-free parses on **< 80%** of the
`.c` files the engine scanned means the comparison was **invalid rather than unfavourable**.

| repo | clean parses | share of the engine's .c files | verdict |
|---|---|---:|---|
| vulkan-loader @2021Q4 | 1 / 20 | **5.3%** | invalid |
| pure-data @2007Q4 | — | **10.2%** | invalid |
| pure-data @2026Q4 | 17 / 168 | **13.0%** | invalid |

Both repos fail, **including the one that passed the gate**. Running the diagnostic only on the failing repo
would have confirmed a convenient story; running it on both is what showed the pass was equally unfounded.

The cause is a defect in the oracle, not the repos: **the pip `libclang` wheel ships `libclang.so` but no
clang resource headers**, so `stddef.h` was not found in 16 of 20 vulkan-loader and 135 of 168 pure-data
translation units. That code path is `acc_eval.oracle_c` and it predates ACC-P — **ACC's own published C
numbers (libgit2 0.76, redis 0.84) were produced by it and need the same diagnostic before they are trusted.**

Supplying the missing headers (`-isystem` the GCC freestanding include dir and the system dirs) lifts
pure-data from 13.0% to **71.0%** — a real fix, and still short of 80%, so the threshold is not moved and C
stays invalid. The remaining failures are a deliberate `#error` in a private header (31 files), Windows-only
sources (10) and similar. vulkan-loader goes from 1/20 to 2/20 only, because **its headers live in a separate
repository** (Vulkan-Headers, fetched by CMake): it cannot be parsed from its own tree at all.

**What C needs:** the oracle run from a compile database (`compile_commands.json`), which is the per-repo
deviation `docs/oracle_criteria.md` §3 permits. Until then C has no gate verdict — neither pass nor fail.

## 4 · Java (D2) and syzkaller (D3)

- **D2.** Neither Java repo's late snapshot builds to a jar with a fixed invocation: `fastasyncworldedit`
  fails under `./gradlew --no-daemon -x test jar`, `openaev` under the recorded Maven command (`rc=1`). Java is
  **not evaluable by build failure**, which is a statement about the oracle's prerequisites — java-callgraph
  reads a compiled jar — and is reported as such.
- **D3.** Excluding the 4 packages `go list` marks as cgo leaves 239; excluding every package holding an
  `import "C"` in any file (the general rule, since build tags hide them from `go list`) leaves 238. Both still
  give 0 edges: `callgraph` refuses to emit anything when **any** loaded package has errors, and syzkaller
  carries cgo tooling needing LLVM headers it does not vendor. **syzkaller is not evaluable with this oracle.**
  No further pruning was attempted — pruning a package list until the tool succeeds is fishing, and the rule
  would stop being a language-level one.

Go therefore has at most **one** evaluable repo, and Amendment 2 requires both. Go cannot be confirmatory in
this run however its snapshots are chosen.

## 5 · Where that leaves the gate

| language | status after this run |
|---|---|
| C | **one valid snapshot short of a verdict** — pure-data @2026Q4 is a clean pass (§7); its 2007 snapshot is at 79.5% coverage and vulkan-loader cannot be parsed from its own tree |
| Go | **cannot be confirmatory** — syzkaller not evaluable (D3); the one scored snapshot fails H3 |
| Java | **not evaluable** — build failure both repos (D2) |
| Python | **descriptive** — PyCG fails; Amendment 2 item 4 forbids a substitute oracle |

So the primary universality test (3 of 4 among C, Java, Go, Python) currently has **no language that can pass**,
and every law would contribute p = 1. That number is a measurement of oracle prerequisites, and it is not
reported as a result about the engine.

**Owed, and named rather than skipped:** registered output (a), the oracle-vs-engine difference in the
year-on-year change of each law statistic (Gini, Q − Q_null, propagation cost, α), is not computed. It needs
two evaluable snapshots of the same repo, which only pure-data has — and pure-data's are invalid.

## 6 · Limits

- Every number in §2 comes from one run of one oracle per language; oracle recall is itself below 1 (ACC's
  prior-work section).
- The engine side is the panel engine's **confident links only**, as Amendment 1 item 1 requires; ambiguous
  links are reported by the engine and never used as edges.
- `H2` is not evaluated here: it needs the oracle's dynamic-dispatch edges, which only Go's VTA pass supplies,
  and that pass produced no evaluable repo.
- Amendment 11 is a **post-result** amendment. Its feasibility search is blind to agreement by construction —
  the code path does not load the engine's graph — but it was written after this run, and the register says so.

## 7 · The C oracle was never run as registered — and fixing it changed the answer

D1 found **0 of 476** redis and **0 of 792** libgit2 translation units parsed cleanly in ACC's own published
run (correction notices now stand on `docs/acc.md` and `docs/acc2.md`). Two separate causes:

1. **The pip `libclang` wheel ships no clang resource headers**, so `<stddef.h>` is missing and almost every
   parse fails. `acc_eval.oracle_c` never supplied substitutes.
2. **The registered primary flag path was never implemented.** ACC's Data table says "compile flags from the
   repo's build where it can generate them without cmake (redis `make` dry-run), else `-I` heuristics".
   `oracle_c` implements only the fallback — including for redis, the repo named for the dry run.

`accp_eval.c_oracle` implements the registered path: a `make -n` dry run over the repo's own makefile, `-I`/`-D`/
`-std` flags extracted and resolved, plus the system include dirs the wheel lacks. The effect on pure-data
@2026Q4, same engine, same matcher, same budget — only the oracle's flags changed:

| | before | after |
|---|---:|---:|
| parse coverage (of the engine's `.c` files) | 13.0% | **102.3%** |
| precision | 0.921 | **0.971** |
| recall | 0.930 | 0.889 |
| hub Jaccard | 0.806 | **0.763** |
| κ | 0.949 | 0.923 |

`-DPD_INTERNAL` alone removed 31 `m_private_utils.h is a PRIVATE header` failures. Precision rose because
edges the oracle previously could not see were being counted against the engine.

**Why Amendment 11 was necessary but not sufficient.** It made the early snapshot the earliest boundary where
the oracle *runs* — exit zero, at least one edge. C's oracle *runs* on pure-data @2007Q4 and returns 6,944
edges; it simply does not **parse enough** of the snapshot (79.5%), because the 2007 tree has only
`src/makefile.in`, an autoconf template, and no configure script. The same class of problem that stopped Go
and Java at the early boundary reaches C through coverage instead of through failure.

**The rule this suggests, not adopted here:** Amendment 11's feasibility test should be stated in terms of
**parse coverage**, not a zero exit code — the earliest boundary at which the oracle covers ≥ 80%. It keeps
the integrity property that matters, because coverage is measurable without looking at a single agreement
statistic. That is an owner decision and a further post-result amendment, so it is proposed and left unmade.

**Not done, deliberately:** pure-data @2007Q4 is 0.5 points under the bar. Hand-tuning its flags to cross that
gap is exactly the fishing this threshold exists to prevent. The threshold stands and the snapshot stays
invalid.
