# Can every function edit be reduced to a discrete type? (ETYP, EXPLORATORY, outcome-blind)

**Type: exploratory.** No registration, no hypothesis fixed in advance, **no p-value claimed**. Tool:
`tools/edit_types.py` (`walk` / `report` / `show`). Repos: curl, libarchive. Run 2026-11-12. Numbers:
[`etyp.json`](etyp.json). Continues [`kwnest.md`](kwnest.md) and [`ceil.md`](ceil.md).

**The tool reads no fix label, event file or commit message, and a test pins that.** Nothing here says
anything about defects. That is the point of doing this step first: the taxonomy is fixed before any
outcome is joined to it. The outcome question is drafted, unapproved, in
[`etyp_hypotheses.md`](etyp_hypotheses.md).

## Why

KWNEST found a function's control skeleton is laid down at birth and almost never rearranged. CEIL found
about 22 points of review-budget performance sit in fix-rate differences between functions that nothing we
measure explains. If structure is static, what differs between functions is the *kind* of edit they
receive. KWNEST compared a function's first and last snapshot and counted differing tokens; this drops to
the unit that actually happens: **one commit changing one function**.

## Unit and taxonomy

An edit is a (commit, file, function) where the function has the same name on both sides of a non-merge
commit and its text differs. git supplies every modified `.c` file under the source roots with blob ids;
tree-sitter parses both sides. No scan database is used.

Each edit gets a set of atomic labels (26 named, 2 residual), grouped in 8 families, and one **primary
family** by a fixed priority order (the order of the table).

| family | atomic labels |
|---|---|
| STRUCTURE | BRANCH_ADD, BRANCH_DEL, LOOP_CHANGE, EXIT_CHANGE, SKELETON_MOVE |
| WIRING | CALL_ADD, CALL_DEL, CALL_RETARGET, ARG_ARITY, SIGNATURE |
| LOGIC | COND_EDIT, OPERATOR, RETURN_VALUE, ARG_VALUE |
| DATA | NUM_LITERAL, STRING_LITERAL, TYPE, FIELD, LOCAL_DECL, REF_SWAP, STMT_ADD, STMT_DEL |
| BUILD | PREPROC |
| NAMING | RENAME_LOCAL |
| COSMETIC | COMMENT, FORMAT |
| RESIDUAL | EXPR_EDIT, UNCLASSIFIED |

**One rule was changed after the first run, before the full run, and is recorded here.** Version 0 let the
token-kind labels (OPERATOR, FIELD, TYPE, the literals) fire on any edit. On the first 3,000 modified
files that gave 4.40 labels per edit with OPERATOR on 51% of edits, because every added statement brings
its own operators and fields with it. The labels now fire only on **in-place** edits (statement,
declaration, control-keyword and call counts all unchanged); an edit that adds or removes units is
described by the units. This was decided from label counts alone.

## Result 1: coverage is nearly complete

| | curl | libarchive |
|---|---:|---:|
| modified files walked | 38,239 | 11,929 |
| function edits | 54,890 | 16,746 |
| functions edited | 6,277 | 3,663 |
| **UNCLASSIFIED** | **0.8%** | **0.7%** |
| EXPR_EDIT or UNCLASSIFIED (no named type) | 1.0% | 0.9% |
| parsed with an ERROR node on either side | 16.9% | 5.9% |

A closed set of 26 named types covers 99% of function edits in both repos.

## Result 2: an edit is a compound, not a single atom, but its family is nearly discrete

| | curl | libarchive |
|---|---:|---:|
| mean atomic labels per edit | 2.61 | 2.74 |
| edits with exactly one atomic label | 31.7% | 23.9% |
| distinct atomic label sets | 3,869 | 1,722 |
| atomic label sets needed for 80% of edits | 274 | 218 |
| distinct family sets | 67 | 66 |
| **family sets needed for 80% / 95% of edits** | **14 / 31** | **15 / 30** |

So the honest answer to "can every change be reduced to one discrete type" is: **to one of 26 atoms, no;
to one of 8 primary families, yes by construction; to one of about 15 family combinations, for 80% of
edits, yes as measured.**

Primary family shares are close across the two repos:

| primary family | curl | libarchive |
|---|---:|---:|
| WIRING | 32.1% | 34.8% |
| STRUCTURE | 24.6% | 26.8% |
| LOGIC | 19.0% | 19.6% |
| DATA | 9.8% | 10.3% |
| COSMETIC | 11.8% | 5.8% |
| BUILD | 1.1% | 0.7% |
| NAMING | 0.8% | 1.2% |
| RESIDUAL | 0.9% | 0.9% |

**A quarter of edits do touch the skeleton.** This does not contradict KWNEST: KWNEST conditioned on
functions whose keyword multiset was identical at both ends, and asked whether those were rearranged.
Here BRANCH_ADD is on 14.7% / 17.1% of edits and SKELETON_MOVE (same keywords, different order or depth)
on 1.3% / 1.2%. The skeleton grows; it is not rearranged.

## Result 3: a function's next edit resembles its last

For every pair of consecutive edits to the same function, compared with the same edit paired to a
size-matched stranger's edit (same log2 token-count bin, 20 draws, seed 2982):

| | curl (48,613 pairs) | libarchive (13,083 pairs) |
|---|---:|---:|
| atomic label-set Jaccard, observed / null | 0.148 / 0.087 = **1.70x** | 0.198 / 0.102 = **1.95x** |
| family-set Jaccard, observed / null | 0.364 / 0.303 = 1.20x | 0.438 / 0.341 = 1.28x |
| same primary family, observed / null | 0.298 / 0.231 = 1.29x | 0.368 / 0.249 = 1.48x |

KWFLUX measured 1.45-1.66x on keyword families; edit types repeat at least as strongly.

The stickiest named types, as P(next edit has it | last edit had it) over the base rate, are the same in
both repos:

| label | curl | libarchive |
|---|---:|---:|
| RETURN_VALUE | 5.83x | 6.74x |
| SKELETON_MOVE | 3.88x | 6.09x |
| LOOP_CHANGE | 3.81x | 3.76x |
| PREPROC | 3.12x | 3.95x |
| STRING_LITERAL | 3.59x | 2.76x |
| ARG_ARITY | 2.41x | 3.76x |
| SIGNATURE | 2.02x | 3.85x |

The common additions (CALL_ADD 1.26x / 1.29x, STMT_ADD 1.36x / 1.23x) barely repeat: any function can
gain a statement. The types that repeat are the specific ones.

## What this does and does not show

- **Shows:** function edits fall into a small closed set of types, the mix is similar across two
  projects, and edit type is partly a property of the function rather than of the commit.
- **Does not show:** that edit type predicts anything. No outcome was read.
- Part of the repeat is composition: a function with no loop cannot receive LOOP_CHANGE. The size-matched
  null does not remove that. It is still a property of the function, which is what the next step needs.

## Limits

- tree-sitter parses unpreprocessed C: 16.9% of curl edits and 5.9% of libarchive edits have an ERROR node
  on one side. They are kept and flagged, not dropped; results were not recomputed without them.
- Identity is (path with renames followed, function name). A renamed function is a death and a birth.
- A name defined more than once in a file (`#ifdef` variants) is skipped: 14,244 such definitions across
  curl's file visits, 8,471 across libarchive's.
- The taxonomy was developed looking at curl and libarchive edits. Both are burned for taxonomy design.
- Two repos, both C. harfbuzz (C++) needs its own parser and is not run.
- The primary-family priority order is a choice. It is fixed in the tool before any outcome is read.
