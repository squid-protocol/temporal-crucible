# ACC — how accurate is GitGalaxy's compile-free call graph, per language, and do the network statistics survive the difference? — registered 2026-11-08, before any oracle is installed or run

**Programme step 1** (`docs/PROGRAMME_call_networks.md`). Every cross-language call-network claim (CGR, the
evolution panel, the many-labs replications) depends on this.

## Prior work

*From the analyst's knowledge; verify titles, venues and DOIs before citing externally (2026-11-08).*

- **Murphy, Notkin, Griswold, Lan, "An empirical study of static call graph extractors", ACM TOSEM 7(2), 1998.**
  Different C call-graph extractors produce substantially different graphs for the same code. Our engine is one more
  extractor; the point is to measure its differences, not to assume an oracle is truth.
- **Reif, Kübler, Michael, Eichberg, Mezini, "Judge: identifying, understanding, and evaluating sources of
  unsoundness in call graphs", ISSTA 2019,** and **Sui, Dietrich, Tahir, Fourtounis, "On the recall of static call
  graph construction in practice", ICSE 2020.** Even compiler-grade Java call graphs miss reflection, dynamic
  dispatch edge cases and native calls: oracle recall is itself below 1.
- **Salis, Sotiropoulos, Louridas, Spinellis, Mitropoulos, "PyCG: practical call graph generation in Python", ICSE
  2021.** Reports PyCG's own precision and recall on a micro-benchmark; PyCG is an approximation, not ground truth.
- **Antal et al., "Static JavaScript call graphs: a comparative study", SCAM 2018.** Tools disagree widely in dynamic
  languages.
- **Relation to this study:** prior work compares extractors within one language. This study compares one
  multi-language, compile-free extractor against the best available per-language oracle, and asks the question the
  call-network studies need: do the *network statistics* (hubs, in-degree ranks, file coupling) survive the
  extractor's differences?

## Data (fixed now)

| language | repo @ pinned snapshot (CGR's latest walk revision) | oracle | edges compared |
|---|---|---|---|
| C | libgit2 @ 0551dfd4ad98, redis @ b540ca49cba8 | **libclang** (pip `libclang`, version recorded at run): each `CallExpr` with a referenced `FunctionDecl` defined in the repo; compile flags from the repo's build where it can generate them without cmake (redis `make` dry-run), else `-I` heuristics as in gitgalaxy `doom_clang.py` | direct calls; calls through function pointers counted separately (no referenced decl) |
| Java | commons-lang @ 7b6048b7a9d1 | **java-callgraph** (static, CHA, from the `mvn -DskipTests package` jar) | static invocations; virtual and interface invocations as a separate kind |
| Go | prometheus @ c45b13bbdd96 | **`golang.org/x/tools/cmd/callgraph -algo=static`** (Go toolchain downloaded for this study), and `-algo=cha` for interface calls | static vs interface |
| Python | sphinx @ b04a2101295a | **PyCG** (pip, version recorded) | all |
| Rust | — | no practical oracle; excluded and named | — |

- **Engine:** gitgalaxy `8f96d76ba` (as CGR), history off.
- **Matching:** functions by (file path, name, start line ± 3). Edges between matched functions only. Calls into code
  outside the repo are dropped on both sides.

## Claims (per language with an oracle; α not applicable: these are measurement bars)

| id | claim | supported iff |
|---|---|---|
| **ACC-H1** | on **direct / statically dispatched** calls the engine agrees with the oracle | precision ≥ 0.80 **and** recall ≥ 0.80 in every language evaluated |
| **ACC-H2** | where they disagree, it is **dynamic dispatch** | ≥ 50% of oracle-only edges are virtual / interface / function-pointer / dynamic in every language evaluated |
| **ACC-H3** | the **network statistics survive** | per repo: in-degree Spearman over matched functions ≥ 0.80, **and** top-1% hub-set Jaccard ≥ 0.50, **and** top-quintile file-coupling agreement Cohen's κ ≥ 0.60; in every repo evaluated |

**Descriptive:** the share of C call sites through function pointers (the CGN-E1 caveat); per-language unmatched
function rate; edge kinds the engine finds that the oracle does not (by language).

## Not evaluable

A language whose oracle fails to run on its pinned repo is reported as such, with the error, and its claims are not
evaluable (never replaced by a different repo after seeing results).

## Guards

Registration before any oracle install or run; one run per oracle; numbers either way. Oracles are not treated as
ground truth: disagreements are classified, not scored as engine errors by default.
