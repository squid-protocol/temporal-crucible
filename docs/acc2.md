# ACC-2 — the engine's resolved call graph vs compiler-grade oracles (SCORED)

**Registered:** 2026-11-08 23:38 (eb3c20c); scorer committed 23:39 (72a682f) before its one run. Raw output:
`gitgalaxy/acc-study/acc2_result.json` (outside the repo).

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


| repo | language | precision | recall (direct) | in-degree ρ | hub Jaccard | coupling κ | H1 | H3 |
|---|---|---:|---:|---:|---:|---:|---|---|
| libgit2 | C | 0.76 | 0.81 | 0.83 | 0.69 | 0.87 | ✗ | ✓ |
| redis | C | 0.84 | 0.94 | 0.87 | 0.69 | 0.90 | ✓ | ✓ |
| commons-lang | Java | 0.75 | 0.92 | 0.83 | 0.27 | 0.50 | ✗ | ✗ |
| **commons-io** (unseen) | Java | 0.81 | 0.84 | 0.81 | **0.67** | 0.60 | ✓ | ✓ |
| prometheus | Go | — | — | — | — | — | not evaluable | |
| sphinx | Python | — | — | — | — | — | not evaluable | |

- **Agreeing Java edges** are mostly resolved by class (1,340 / 782), qualified name and type: the resolver's
  type-aware steps carry the agreement.
- **commons-io, name-based graph (descriptive):** hub Jaccard 0.26 against 0.67 for the resolved graph. Resolution
  fixes Java hubs where overloads differ in arity.
- **commons-lang still fails:** its hubs are heavily overloaded utility methods (`StringUtils`, `ArrayUtils`) with
  the same arity and different types, which (file, class, name, argument count) cannot tell apart.
- **Go not evaluable.** The scorer's output template printed `{{.Caller.Pos}}`, an integer offset, not a
  file:line, so no edge could be matched (diagnosed after scoring; the oracle itself ran, rc 0).
- **Python not evaluable.** PyCG 0.0.8 fails on sphinx as a whole and in every subpackage
  (`ImportManagerError`).

## Verdicts

- **ACC2-H1:** C ✗ (libgit2 precision 0.76), Java ✗ (commons-lang 0.75); Go and Python not evaluable.
- **ACC2-H3:** **C ✓**; Java ✗ (commons-io ✓, commons-lang ✗); Go and Python not evaluable.
- **ACC2-G** (the LAWS gate): **C only**.

## Reading

C call networks are validated twice. The engine's resolver fixes Java hubs on an unseen repo but not on an
overload-heavy one, so Java is close but not through the gate. Go needs a correct oracle run (ACC-3). Python needs
an oracle that handles a large package.
