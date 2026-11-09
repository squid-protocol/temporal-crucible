# ACC-2 — does the engine's own resolved call graph agree with compiler-grade oracles? — registered 2026-11-08, before any comparison of the resolved graph

**Why.** ACC (`docs/acc.md`) scored the *name-based* call network the call-network studies built from `calls_out_to`
(callee names, same-file then unique-name resolution, node identity (file, name)). C passed; Java's hubs failed
(Jaccard 0.29); Go and Python were not evaluable. The engine also writes its **own resolved call graph**,
`fcall_data`: each call resolved to a function row by receiver, overload, class, qualified name, type, import, file
or unique name, with a candidate count. On the ACC scans it resolves 99% of C calls, 95% of Java, 84% of Go and 88%
of Python. That graph was never compared with an oracle.

**What has been seen.**
- **Seen:** the name-based graph's agreement on libgit2, redis and commons-lang (ACC), and the per-kind resolution
  counts of `fcall_data` (above).
- **Not seen:** any comparison of the resolved graph with an oracle. commons-io is new to every study.

## Prior work

As ACC (`docs/acc_hypotheses.md`): Murphy et al. 1998 [k]; Reif et al. 2019 [k]; Sui et al. 2020 [k]; Salis et al.
2021 (PyCG) [k]. Type- and receiver-based resolution is what compiler-grade Java call graphs do (class-hierarchy
analysis); this tests how close a compile-free resolver gets.

## Data

- **Repos:** the ACC repos at the same pinned snapshots and engine scans, plus **commons-io @ 05f968e913fb** (Java;
  engine 8f96d76ba; oracle jar from `javac --release 8` of the pinned sources).
- **Oracles:**
  - as ACC (libclang 18.1.1, java-callgraph da81eeb, PyCG 0.0.8, x/tools callgraph v0.52.0 / go1.27.3);
  - **Go** runs in the module's own mode (go.work honoured, no `-mod` flag);
  - **Python:** PyCG is run on the whole `sphinx` package; if it fails, once per top-level subpackage, and only
    within-subpackage edges are compared.
- **Resolved graph R:** nodes = `function_data` rows with loc ≥ 3; edges = `fcall_data` rows with kind `call` and a
  resolved `dst_func_id`, both endpoints nodes, no self-loops. A node's identity is (file, enclosing class from
  `class_data` if any, name, start line).
- **Matching to oracle functions:**
  - C and Go: (file, start line ± 3);
  - Java: (file, class simple name, method name, argument count), constructors as the class name; inner classes
    by their own simple name;
  - Python: (file, class, name).

  Unmatched functions on either side are dropped, and their counts are reported.

## Claims (measurement bars, per language)

| id | claim | supported iff |
|---|---|---|
| **ACC2-H1** | the resolved graph agrees on edges | precision (engine edges confirmed by any oracle edge) ≥ 0.80 and recall on oracle direct edges ≥ 0.80, in every evaluable repo of the language |
| **ACC2-H3** | network statistics survive | in-degree ρ ≥ 0.80, top-1% hub Jaccard ≥ 0.50, file-coupling κ ≥ 0.60 in every evaluable repo of the language |
| **ACC2-G** | **the LAWS gate** | a language passes iff ACC2-H3 holds for it. LAWS then builds its networks from the resolved graph (to be stated in a LAWS amendment before the panel draw) |

**Descriptive:** the name-based graph's numbers on commons-io; the resolution-kind mix of agreeing vs disagreeing
edges; Python per-subpackage coverage.

## Not evaluable

An oracle that fails after the steps above. No other substitution.
