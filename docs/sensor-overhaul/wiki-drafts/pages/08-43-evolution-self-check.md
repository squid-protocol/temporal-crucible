> **Status: design and prototype, not shipped.** Draft for GitGalaxy's `docs/wiki/`, written 2026-11-19 against the evolution-report prototype. Exploratory.

# Evolution report: self-check

The report checks itself and prints the result in "How far to trust this report". The checks never change a figure; they say how far to trust it.

## Checks that need only git
- **Commit count** matches `git rev-list --no-merges`.
- **Every function edit is in exactly one category**, and the work-mix shares add up to 100%.
- **Fixes matched to a cause:** at least 30 pairs for repair timing to be shown, 100 or more for stable figures.

## Checks that need the scan (compared with an independent tree-sitter parse of the same snapshot)
- **Code files the scan read.** Files in the repository at the scanned commit that the scan did not read, grouped by directory. Vendored directories left out on purpose (`third_party`, `vendor`, `node_modules`, ...) are counted separately; other missing directories are flagged, and a missing directory whose name is on the scanner's default ignore list (`log`, `logs`, `docs`, `classes`, `tmp`, ...) is called out (#8708).
- **Functions found vs a tree-sitter parse:** recall (share of the parse's function definitions that are in the scan) and precision (share of the scan's functions the parse also finds; the rest are macro-generated or renamed forms).
- **Call edges vs a name-matching baseline:** each call to a name that exactly one function defines (or exactly one in the same file) is an edge. Recall is the share of the baseline's edges GitGalaxy found; precision is the share of GitGalaxy's edges the baseline has. The baseline cannot see calls through function pointers, fields or macros, which GitGalaxy can.
- **Cross-file call pairs** (what `gitgalaxy reach` counts): the same comparison at file level.
- **Import graph:** each `#include` (C family) or `import` (Python) that names exactly one file of the repository (relative path first, then a unique match by trailing path), against the scan's import edges. Edges only GitGalaxy has are usually includes it resolved among several same-named files. Go and Rust imports are not checked yet.

Ratings: pass at 85% recall or better (90% for functions and imports), warning from 65% (75%), fail below. These cut points are defaults, not validated.

## Two ratings, and why they differ
1. **Agreement on this repository** with the name-matching parse. This is a consistency check against a cheap tool of the same kind; high agreement (96 to 99% in the first runs on DPDK and nDPI) means the two do not contradict each other, not that either is right.
2. **Standing rating against a compiler-grade reference**, measured in our research on pinned repositories (`reach_vs_treesitter.md`): C against libclang, strict call edges, precision 89% and recall 70% (61% on seven small repositories where libclang could not parse every file); Python against pyan3 53% and 65%; Go against golang.org/x/tools VTA 81% and 64%; Rust against rust-analyzer 58% and 67%. These are not measured on the repository shown. A tree-sitter name matcher recovered 83% of the C edges, more than GitGalaxy's strict set, while GitGalaxy found calls hidden inside macros that a name matcher misses (52% against 1%).

Because every standing recall is below 85%, the report always shows a note that hub lists, repair radius and call counts are lower bounds, and a warning when the live agreement is not good.

## Limits
- A per-repository comparison against libclang or another compiler-grade tool is not run by the report: it needs a build configuration, and libclang parsed only part of the files in our tests. An optional `--reference` is possible later.
- The baseline is a minimal implementation of ours, not a specific product.
- Function names in `edge_data` and `fcall_data` are matched by path and name; C++ qualified names are reduced to the last component.
