# The import graph as a second instrument: scoped, built, and measured

Development data, never panel results. Tool: `tools/laws_imports.py`. Numbers:
`.../laws-study/pilot/import_graph.json`.

**Why it was tried.** Every law is computed from one edge kind, the engine's confident `call` links, whose coverage
is about 99% in C and 56 to 60% in Java, Go and Python (`docs/laws_coverage.md`). An import edge is **declared,
not inferred**, so the hope was an instrument whose quality does not vary with how hard a language's dispatch is,
giving a between-language comparison the call graph cannot support.

**What it is.** A file-level import graph per snapshot, extracted independently of the pinned engine. The engine
already builds a per-file import map and uses it as its `import` resolution step, but persists only call edges;
reading it back would mean changing the scanner and rescanning all 626 snapshots, an engine change under
Amendment 1. This reads the import lines from git instead (one `git grep` per snapshot, under a second per
snapshot), and takes the snapshot list, the unit file set and each file's LOC from the existing scan databases --
so its node set is exactly the call graph's file projection and the two are directly comparable.

Resolution is per language, and an edge exists only where the target is an in-repo unit file: `#include` relative
then by unique basename; Python's absolute and relative module forms against a module index; Go's quoted paths
under the module path in go.mod (a Go import names a directory, so it yields an edge to every unit file in it);
Java's `import a.b.C;` by path suffix, dropping a static member.

## C and C++ need a header collapse, or the two graphs never meet

If `a.c` calls into `b.c` it must include `b.h`. So include edges point at **headers** and call edges point at
**implementations**, and at file granularity the two live in disjoint halves of the file set. Raw overlap on the
last snapshot was **18 of 847 edges on libxml2 and zero of 2,358 on libgit2**. `collapse_headers` maps each
header onto the implementation file(s) sharing its basename stem, after which the overlap is 59.1% and 46.1% of
the call graph's file edges. That is the one inference step in an otherwise declarative graph -- a basename match,
not type inference -- but it is an inference, and a header whose implementation has a different stem is missed.

## Agreement with the call graph, last snapshot

| repo | language | import edges | call file edges | both | agreement |
|---|---|---|---|---|---|
| sphinx | python | 1,480 | 611 | 535 | **87.6%** |
| prometheus | go | 5,228 | 981 | 632 | **64.4%** |
| libxml2 | c | 572 | 569 | 336 | **59.1%** |
| libgit2 | c | 1,358 | 1,593 | 734 | **46.1%** |
| commons-lang | java | 240 | 293 | 126 | **43.0%** |

The variation is structural, not instrumental: Java's same-package calls need no import at all, and a Go import of
a package yields an edge to every file in it (prometheus's 4,596 import-only edges are mostly that fan-out).
Import-only edges also include imports that are never called -- unused, type-only, or re-exported.

`share_in_repo` -- the share of import lines pointing at an in-repo unit file -- is 0.21 to 0.90 across the five.
**It is a property of the code, not of the instrument**: an import of the JDK or the Go standard library
correctly fails to resolve, because the target is not part of the intra-repo network. Reading it as coverage
would repeat the mistake `share_confident_of_repo_links` makes.

## The result that settles it: heavy tails do not survive aggregation to files

The tail fit run on file in-degree, on both graphs (a file-level analogue of LAW-1, not LAW-1 itself, which is
defined on function in-degree):

| repo | language | import graph | call graph (file projection) |
|---|---|---|---|
| sphinx | python | +0.057 ± 0.029 | +0.035 ± 0.028 |
| libgit2 | c | +0.028 ± 0.033 | +0.019 ± 0.019 |
| commons-lang | java | +0.007 ± 0.012 | +0.011 ± 0.014 |
| prometheus | go | +0.007 ± 0.009 | +0.036 ± 0.024 |
| libxml2 | c | not evaluable | not evaluable |

Against **+0.062 to +0.184** on the function-level call graph, these are all within one or two standard errors of
zero. The two instruments agree with each other -- their effects overlap in four of the five repos -- but they
agree on nothing much. **Heavy tails are a function-level phenomenon and do not survive aggregation to files.**

## Verdict

The import graph is cheap, independent of the pinned engine, works in all four pilot languages, and agrees with
the call graph at 43% to 88%. But it **cannot** be the coverage-robust instrument it was proposed as: being
inherently file-level, it cannot carry the degree-based laws -- LAW-1 here, and by the same argument LAW-3 and
LAW-4, which are also node-degree statistics. The proposal was tested and is not supported for that purpose.

What remains worth doing with it, in order:

1. **LAW-5 on the import graph.** LAW-5 is already computed over a directory partition rather than node degree
   (modularity excess and propagation cost), so it is the one law the import graph can carry on its own terms.
   That is a genuine second-instrument test of the one structural law whose pilot reading currently fails
   everywhere.
2. **Report the agreement figure per panel repo** beside the coverage figure. 43% to 88% is a useful, cheap
   statement about how much of the call structure is also declared, and it varies by language for reasons worth
   naming in the paper.
3. **Do not** use it to patch the call graph's missing edges. The import-only edges are dominated by Go's
   package fan-out and by imports that are never called; adding them would inject structure that no call makes.

Not registered: nothing here changes a law. If LAW-5 is to be reported on the import graph that needs an
amendment, and the header collapse would need registering with it.
