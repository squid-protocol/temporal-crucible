# ACC — compile-free call-graph accuracy per language (SCORED)

**Type:** confirmatory measurement study
**Registered:** 2026-11-08 22:26 (4a44e9a, `docs/acc_hypotheses.md`); scorer committed 23:30 (2608551,
`tools/acc_eval.py`, with a pre-run clarification of precision and recall) before its one run.
**Oracles as installed:**
- libclang 18.1.1;
- java-callgraph `da81eeb` on commons-lang compiled from the pinned sources (`javac --release 8`; its Maven build
  needs Maven ≥ 3.9);
- go1.27.3 with x/tools `callgraph` v0.52.0;
- PyCG 0.0.8.

Engine: gitgalaxy 8f96d76ba. Raw output: `gitgalaxy/acc-study/acc_result.json` (outside the repo).

> ## ⚠ Correction notice, 2026-11-11: the C rows below are not trustworthy as measured
>
> ACC-P's D1 diagnostic (`docs/accp.md` §3, `docs/accp_diagnostics.json`) re-ran this study's own C oracle and
> counted how many translation units libclang parsed **without fatal diagnostics**:
>
> | repo | parsed clean | of the engine's .c files |
> |---|---|---:|
> | redis | **0 / 476** | 193 |
> | libgit2 | **0 / 792** | 684 |
>
> **Not one file in either repo parsed cleanly.** The dominant error is `'stddef.h' file not found` (247 in redis,
> 121 in libgit2): the pip `libclang` wheel ships `libclang.so` but **no clang resource headers**, and
> `acc_eval.oracle_c` never supplied them. libclang still returns an AST when a header is missing, so edges were
> extracted and the numbers below are not noise — but they were produced from source the compiler front end could
> not fully resolve, and the error rate was never measured at the time.
>
> **It is also a conformance failure against this registration.** The Data table above specifies "compile flags
> from the repo's build where it can generate them without cmake (**redis `make` dry-run**), else `-I` heuristics".
> `oracle_c` implements only the fallback: the build-derived path was never written, for redis least of all, the
> repo named for it.
>
> **Status of the C claims:** the precision, recall, ρ, hub Jaccard and κ figures in the C rows **stand as the
> record of what was computed** and are not edited or withdrawn here. They should not be cited as the engine's C
> accuracy until the oracle is run per the registration — build-derived flags — and the parse coverage is reported
> beside the result. ACC-H1 and ACC-H3's C verdicts inherit that caveat.
>
> Nothing in this notice affects the Java, Go or Python rows.


## Results

| repo | language | matched functions | precision | recall (direct) | in-degree ρ | hub Jaccard | coupling κ |
|---|---|---:|---:|---:|---:|---:|---:|
| libgit2 | C | 7,180 | 0.76 | 0.81 | 0.83 | 0.67 | 0.87 |
| redis | C | 4,960 | 0.84 | 0.94 | 0.87 | 0.69 | 0.92 |
| commons-lang | Java | 1,942 of 8,734 engine nodes | 0.78 | 0.78 | 0.80 | **0.29** | 0.62 |
| prometheus | Go | — | — | — | — | — | — |
| sphinx | Python | — | — | — | — | — | — |

- **Go not evaluable.** The scorer set `GOFLAGS=-mod=mod`; prometheus is a Go workspace (`go.work`), where `-mod=mod`
  is refused. This was a scorer configuration error, not an oracle limit. Per the registration, Go is reported as
  not evaluable in this run.
- **Python not evaluable.** PyCG 0.0.8 stops on sphinx's imports (`ImportManagerError: Can't add edge to a non
  existing node`).
- **C indirect calls:** 9.7% (libgit2) and 17.3% (redis) of call sites go through function pointers; neither side
  resolves them.

## Verdicts

| claim | result | verdict |
|---|---|---|
| **ACC-H1** precision and recall ≥ 0.80 on direct calls, every language | C: redis ✓, libgit2 precision 0.76 ✗; Java 0.78 / 0.78 ✗ | **✗** |
| **ACC-H2** disagreements are mostly dynamic dispatch | Java: 27% of oracle-only edges are virtual / interface / dynamic; C and Python not evaluable (libclang cannot resolve function pointers; PyCG failed) | **✗** |
| **ACC-H3** network statistics survive (ρ ≥ 0.80, hub Jaccard ≥ 0.50, κ ≥ 0.60), every repo | C ✓ in both repos; Java ✗ (hub Jaccard 0.29; ρ 0.797) | **✗ overall; ✓ for C** |

## Reading

- **C call networks are trustworthy for network science.** Precision and recall are 0.76–0.94 against libclang, and
  the statistics the studies use (in-degree ranks, hub sets, file coupling) agree well. The call-network results on
  C (CGT, CGN, CGK, CGR's C repos) stand on a validated instrument.
- **Java is not yet:**
  - edge-level agreement is fair (0.78), but the hub set disagrees (Jaccard 0.29);
  - only 1,942 of the engine's 8,734 Java functions match an oracle method;
  - identity by (file, name) merges overloads and same-named methods of different classes, which concentrates
    in-degree on a few names and changes who the hubs are. The LAWS review predicted this (M4).
- **The disagreements are not mainly dynamic dispatch** (H2): most Java oracle-only edges are static or special
  invocations the name matcher misses or merges.
- **For LAWS (the ACC gate):** as registered, only C qualifies as confirmatory; Java fails H3; Go and Python are not
  evaluable. A many-labs claim across languages needs ACC-2: class-aware node identity, the Go workspace setting
  fixed, and a Python oracle run that completes.

## Follow-ups

**ACC-2** (to be registered before running): node identity (file, enclosing class, name) on the engine side; Go with
`GOWORK` honoured; PyCG run per sphinx subpackage (or a second Python oracle); a larger Java sample (2 repos).
