# ACC-P — the LAWS language gate: first run, and why it does not yet decide anything

**Type: confirmatory measurement gate** (`docs/laws_hypotheses.md` Amendments 0–2, 4 and **11**). Panel engine
`b873edc5b`. Repos are draws 1 and 2 of each language's seeded order. Run 2026-11-11.
Raw: `docs/accp_result.json`, `docs/accp_diagnostics.json`. Tool: `tools/accp_eval.py`.

**Read this first.** ACC-P run 1 is reported as **a pilot** (LAWS Amendment 12 item 3), not as a clean
pre-registered gate: two post-result amendments were needed, the C oracle was found never to have run as its
own registration specified, and three of ten candidate languages have no oracle at all.

Within that, the pilot now has a result. **C clears ACC-P's agreement bars on both repos at both snapshots,
with valid parse coverage everywhere** (§8). Go has one scored snapshot and one repo that cannot be oracled;
Java and Python cannot run their oracles at all. Every non-C failure is a property of an oracle's
prerequisites, each now measured and named.

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
- **D3, corrected 2026-11-11.** The first pass concluded "`callgraph` refuses to emit anything when any
  loaded package has errors, so syzkaller is not evaluable". **The mechanism was right and the attribution was
  wrong, and it was my own exclusion that was broken.** Dropping the 4 packages `go list` marks as cgo, or the
  5 directories holding an `import "C"`, is not enough: `pkg/clangtool/tooltest` and `pkg/ifuzz/x86` remained in
  the list and **depend** on cgo packages, so the loader pulled those in regardless.

  Excluding packages whose dependency closure reaches a cgo package — the same rule applied transitively, which
  is what "cannot be loaded without C" actually means — **callgraph runs and emits 1,175 in-repo edges.** The
  oracle works.

  But the closure is enormous: **209 of syzkaller's 243 own packages are transitively cgo-tainted, leaving 34
  — 14%.** syzkaller is a kernel fuzzer and cgo is load-bearing throughout it. So syzkaller is **not evaluable,
  for the same reason C's vulkan-loader nearly was not: coverage.** 14% of a repository is a small and
  non-random slice, and that is exactly what the coverage bar exists to reject. The verdict is unchanged; the
  reason for it is now the right one.

Go therefore has at most **one** evaluable repo, and Amendment 2 requires both. Go cannot be confirmatory in
this run however its snapshots are chosen.

### The primary universality test cannot pass, and that is now arithmetic

The primary test (Amendment 2 item 1, M2) is a partial conjunction over **C, Java, Go and Python**: at least
**3 of those 4**. After this run:

| language | can it still become confirmatory in this run? |
|---|---|
| C | **yes** — clears ACC-P's agreement bars (§8) |
| Python | **no** — PyCG fails on every snapshot and Amendment 2 item 4 forbids a substitute oracle |
| Go | **no** — syzkaller is not evaluable at 14% package coverage, and Amendment 2 requires both repos |
| Java | unknown — blocked on a build, not yet ruled out |

**The maximum reachable is 2 of 4, so the primary test cannot pass whatever happens to Java.** This is not a
result about software laws; it is a consequence of two of the four named languages having oracles that cannot
be run on their drawn repositories.

The **extended** universality test — Amendment 2 item 3, fixed in advance, `r = ⌈2n/3⌉` of the `n` languages
entering ACC-P — is therefore the operative headline for every law, and it was pre-registered for exactly this
kind of shortfall. With three of ten candidate languages lacking an oracle entirely, `n ≤ 7` and `r = 5`, so
the path runs through C#, Kotlin and PHP, whose references are pinned but not installed here.

## 5 · Where that leaves the gate

| language | status after this run |
|---|---|
| C | **clears the agreement bars** on both repos at both snapshots with valid coverage (§8). Outstanding before confirmatory status: Amendment 2's resolution-profile condition (\|Kendall τ\| < 0.3 in ≥ 6 of 8 repos), which needs the panel scan, not ACC-P |
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

## 8 · C clears the gate's agreement bars

Two changes, both made under rules fixed before they were applied:

- **Amendment 12 item 1** replaced "the oracle runs" with "the oracle parses ≥ 80%" as the early-snapshot
  test, and the search (`tools/accp_eval.py feasible`, `docs/accp_feasibility.json`) is blind to the engine by
  construction: it never opens a scan database. pure-data's earliest qualifying boundary is **2018Q4** (123/149
  = 82.6%) after 45 boundaries tried; vulkan-loader's is **2023Q1** (17/21 = 81.0%) after 5.
- **Amendment 12 item 2** supplied vulkan-loader's external headers (KhronosGroup/Vulkan-Headers,
  date-matched to each boundary by one recorded rule, not a version picked by trying several). Its coverage
  went from ~10% to 75–85%, and **its H1/H3 failures disappeared entirely**: they were the missing headers.

| gate snapshot | coverage | precision | recall | ρ | hub J | κ | H1 | H3 |
|---|---:|---:|---:|---:|---:|---:|---|---|
| pure-data @2018Q4 (early) | 109.8% | 0.995 | 0.946 | 0.974 | 0.867 | 1.000 | pass | pass |
| pure-data @2026Q4 (late) | 102.3% | 0.971 | 0.889 | 0.955 | 0.763 | 0.923 | pass | pass |
| vulkan-loader @2023Q1 (early) | 85.0% | 0.999 | 0.964 | 0.983 | 1.000 | 1.000 | pass | pass |
| vulkan-loader @2026Q4 (late) | 81.0% | 0.993 | 0.973 | 0.985 | 0.714 | 1.000 | pass | pass |

Coverage is engine-relative here (clean parses over the `.c` files the engine scanned), which is D1's validity
ratio and the one that governs whether a comparison may be read; it exceeds 100% where the oracle sees more
`.c` files than the engine kept. **The two denominators disagree in one place and it is close:** pure-data
@2026Q4 is 102.3% engine-relative and **79.8%** over the oracle's own file list. The feasibility search uses
the stricter oracle-relative figure, the validity report uses the engine-relative one, and this snapshot
passes on the rule that governs it while missing the other by 0.2 points. A reader who prefers the stricter
denominator throughout should treat that snapshot as unproven.

**What this does and does not establish.** It establishes that on two C repositories, at four snapshots, the
engine's confident-link call graph agrees with libclang on direct calls at precision 0.971–0.999 and recall
0.889–0.973, and that its in-degree ordering, hub set and file coupling track the oracle's closely. It does
**not** make C confirmatory on its own: Amendment 2 also requires the resolution-profile condition over the
panel, which this run does not compute. And both early snapshots were selected by a post-result amendment,
which a reader is entitled to discount.

**Still owed:** registered output (a), the oracle-vs-engine difference in each law statistic's year-on-year
change. It needs two valid snapshots of one repo — which now exist, twice over, so this is no longer blocked
by data. It is simply not done.
