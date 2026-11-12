# How an oracle is chosen for a language (ORACLE-CRIT), fixed 2026-11-11

**Type: methods rule, not a hypothesis.** It binds every study in this repo that compares the engine against a
reference tool — ACC, ACC-2, ACC-3, ACC-P, and anything after them. It was written **after** ACC-P's four
runnable languages were identified but **before** any oracle was chosen for the languages that lack one, and
before any ACC-P statistic was computed. That ordering is the point: see §4.

## 1 · Why this exists

LAWS Amendment 2 says ACC-P runs for ten languages. Seven have a named, pinned reference: C (libclang), Java
(java-callgraph), Go (`callgraph`), Python (PyCG), C# (scip-dotnet), Kotlin (scip-java with the Kotlin
compiler plugin), PHP (scip-php). **Three — C++, Rust and JS/TS — have none**, and that was discovered after
the panel had been drawn and seated.

Discovering it then is the failure. Once the sample exists, any oracle chosen for a language is chosen in the
knowledge of which repositories it will be judged on, and nothing in the write-up can prove otherwise. The
cost is not that the choice *would* be biased; it is that its independence is no longer demonstrable. The rule
below exists so the next language is settled before it can be contaminated, and so the gap is visible while it
is still cheap to close.

## 2 · The criteria

An oracle for a language must satisfy all of these. They are properties of the **language and the tool**, never
of a repository, so that one decision covers every repo of that language.

1. **Resolution by a front end, not by a heuristic.** The tool must resolve a call through a parser plus a type
   or symbol table — a compiler front end, a language server, or an indexer built on one. A regex or
   tags-style matcher is not an oracle; it is another approximation of the same kind as the engine.
2. **Function-grain edges with source positions.** It must emit caller → callee at function grain with a file
   path and a line for each endpoint, so that the registered matcher — (path, name, start line ± 3) — can run.
   A tool that emits only file-level or module-level edges fails.
3. **One fixed command line per language.** The tool must run from the repository's own build, or from no
   build, under a command fixed in advance for the language. Per-repo flag hunting is allowed only as a
   recorded deviation for that repo, never as grounds for a different oracle.
4. **A documented unsoundness.** There must be a published evaluation, or the tool's own documentation, stating
   what it misses — reflection, dynamic dispatch, native calls, dynamic imports. An oracle whose recall is
   unknown cannot bound the engine's recall. Oracle recall is below 1 and is reported as such.
5. **A pin.** A released version or an exact commit, recorded in the registration before the run, with the
   version printed by the run itself.
6. **Runnable without contaminating the project.** Install and run under this repo's third-party rule: the
   oracle's output may be measured against, its code is never vendored or adapted.

## 3 · More than one oracle for a language

Permitted, and sometimes required, under one condition: **the division of labour is fixed before the run.**

Go is the worked example and the precedent. `callgraph -algo=static` supplies direct edges; a second algorithm
supplies dynamic ones, because no single algorithm gives both at usable precision (LAWS Amendment 4 replaced
the CHA pass with VTA for exactly this reason). That is legitimate because each pass is pinned to an edge kind
in advance.

What is forbidden is a **best-of**: running two oracles and reporting the one that agrees with the engine more.
If two candidate tools both satisfy §2 and neither is assigned to a distinct edge kind, the tie is broken by
§5 before any comparison, and the loser is named in the registration as the one not used.

## 4 · When the oracle must be chosen

**Before that language's sampling frame is built**, and therefore before any repository of that language is
drawn, cloned or scanned. A language with no oracle meeting §2 at that moment is declared **oracle-less by
name** in the registration, stays descriptive, and is not quietly left blank.

This is the rule the present gap violates. C++, Rust and JS/TS should have been settled or declared before
seating; they were not, so for them the panel exists first. Two consequences, both accepted here rather than
argued away:

- any oracle adopted for those three from now on is **post-draw**, is labelled as such wherever its result
  appears, and cannot make the language confirmatory under the primary test;
- the per-language decision still gets made under §2 and §3, because a post-draw choice made against fixed
  criteria is weaker than a pre-draw one but far better than one made against a result.

## 5 · Tie-break order

When several tools satisfy §2:

1. the one with an **independent published evaluation** of its precision and recall;
2. the one whose resolution is closest to the compiler's own (a front end over a language server over an
   indexer);
3. the one with a **stable release** rather than a main-branch pin;
4. the one that runs **without building the repository** (fewer repos lost to build failure — and a build
   failure removes a repo from the sample, which is a sampling effect, not a measurement one);
5. the simpler to run, recorded as a judgement call.

## 6 · What is recorded per language

| field | why |
|---|---|
| tool, pin, install source | reproducibility |
| the fixed command line | §3 |
| which edge kinds this oracle supplies | multi-oracle division of labour |
| the published evaluation of its unsoundness | §2.4 |
| tools considered and rejected, with the clause that rejected them | prevents a silent best-of |
| whether the choice was pre-draw or post-draw | §4 |

## 7 · Status at the time of writing

| language | oracle | pin | pre-draw? |
|---|---|---|---|
| C | libclang | 18.1.1 | yes (ACC) |
| Java | java-callgraph | `da81eeb` | yes (ACC) |
| Go | `callgraph`, static + VTA | x/tools v0.52.0, go1.27.3 | yes (ACC, Amendment 4) |
| Python | PyCG | 0.0.8 | yes (ACC) |
| C# | scip-dotnet | 0.2.16 | yes (admission survey, pre-draw) |
| Kotlin | scip-java (scip-kotlinc) | v0.13.2 | yes (admission survey, pre-draw) |
| PHP | scip-php | v0.0.2 | yes (admission survey, pre-draw) |
| **C++** | **none chosen** | — | **gap: post-draw from here** |
| **Rust** | **none chosen** (ACC called it "no practical oracle" and excluded it by name) | — | **gap: post-draw from here** |
| **JS/TS** | **none chosen** | — | **gap: post-draw from here** |

ACC-P proceeds on the seven that have one, starting with the four whose oracles are installed and already
exercised — C, Java, Go and Python, which are also the four languages of the primary universality test.
