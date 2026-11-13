# Can every function edit be reduced to a discrete type? (ETYP, EXPLORATORY, outcome-blind)

**Type: exploratory.** No registration, no hypothesis fixed in advance, **no p-value claimed**. Tool:
`tools/edit_types.py` (`walk` / `report` / `show`). Repos: curl, libarchive. Numbers: [`etyp.json`](etyp.json).
Continues [`kwnest.md`](kwnest.md) and [`ceil.md`](ceil.md).

**Revised 2026-11-12 after an independent review ([`etyp_review.md`](etyp_review.md)).** The first version of
this note overstated its third result and included libarchive's test code. What changed is marked below.

**The tool reads no fix label, event file or commit message, and a test pins that.** Nothing here says
anything about defects.

## Why

KWNEST found a function's control skeleton is laid down at birth and almost never rearranged. CEIL found a
large gap between achieved and attainable fix prediction that nothing measured explains. If structure is
static, what differs between functions may be the *kind* of edit they receive. KWNEST compared a function's
first and last snapshot; this drops to the unit that actually happens: **one commit changing one function**.

## Unit and taxonomy

An edit is a (commit, file, function) where the function has the same name on both sides of a non-merge
commit and its text differs. git supplies every modified `.c` file under the source roots, test trees
excluded; tree-sitter parses both sides. No scan database is used.

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

**The taxonomy was changed twice, and neither change was blind to everything.**

1. After a 3,000-file smoke run and before the first full run: token-kind labels (OPERATOR, FIELD, TYPE, the
   literals) fire only on **in-place** edits. Version 0 gave 4.40 labels per edit with OPERATOR on 51%,
   because every added statement brings its own operators. Decided from label counts alone.
2. After the outcome joins had been run, prompted by the review: structure labels now compare each control
   keyword separately instead of a group total (a `return` swapped for a `goto` was UNCLASSIFIED; an `else`
   turned into a second `if` got no STRUCTURE label). This changed the label set of 1.16% of curl edits and
   1.2% of libarchive edits, and the primary family of 0.37% and 0.49%. **A taxonomy changed after outcomes
   were seen is not outcome-blind in the strict sense**, however small the change.

## Result 1: coverage is nearly complete

| | curl | libarchive |
|---|---:|---:|
| function edits | 54,890 | 11,541 |
| functions edited | 6,281 | 2,345 |
| **UNCLASSIFIED** | **0.8%** | **0.7%** |
| EXPR_EDIT or UNCLASSIFIED (no named type) | 1.0% | 0.8% |
| parsed with an ERROR node on either side | 16.9% | 7.1% |

A closed set of 26 named types covers 99% of function edits in both repos. (The first version reported
16,746 libarchive edits; 5,205 of those were under `libarchive/test/`, `tar/test/` and the like.)

## Result 2: an edit is a compound, not a single atom, but its family is nearly discrete

| | curl | libarchive |
|---|---:|---:|
| mean atomic labels per edit | 2.62 | 2.78 |
| edits with exactly one atomic label | 31.7% | 26.3% |
| distinct family sets | 67 | 64 |
| **family sets needed for 80% / 95% of edits** | **14 / 31** | **15 / 29** |

So: **to one of 26 atoms, no; to one of 8 primary families, yes by construction; to one of about 15 family
combinations, for 80% of edits, yes as measured.**

The mix is of the same kind in the two repos but not the same:

| primary family | curl | libarchive |
|---|---:|---:|
| STRUCTURE | 24.9% | 33.1% |
| WIRING | 31.9% | 25.0% |
| LOGIC | 18.9% | 19.6% |
| DATA | 9.7% | 12.9% |
| BUILD | 1.1% | 0.6% |
| NAMING | 0.8% | 1.7% |
| COSMETIC | 11.8% | 6.4% |
| RESIDUAL | 0.8% | 0.7% |

**A quarter to a third of edits touch the skeleton.** This does not contradict KWNEST, which conditioned on
functions whose keyword multiset was identical at both ends. BRANCH_ADD is on 15.1% /
21.1% of edits and SKELETON_MOVE (same keywords, different order or depth) on
1.3% / 1.6%. The skeleton grows; it is not rearranged.

## Result 3: a function's next edit resembles its last, but most of that is not the function

Every pair of consecutive edits to one function, against a stranger's edit. Two readings:

- **loose** (what the first version reported): all pairs; the stranger is any edit to a function of the same
  size.
- **strict**: no sweep commit (more than 50 function edits) on either side, a different author, at
  least 30 days apart; the stranger is an edit to **another function in the same file**.

39.6% / 18.6% of pairs touch a sweep,
51.2% / 50.5% are by one author, and
9.2% / 19.1% are less than a day apart.

| ratio of observed to stranger | curl loose | curl strict | libarchive loose | libarchive strict |
|---|---:|---:|---:|---:|
| pairs | 48,609 | 8,375 | 9,196 | 3,012 |
| atomic label-set Jaccard | 1.71x | **1.34x** | 1.88x | **1.26x** |
| family-set Jaccard | 1.20x | 1.09x | 1.28x | 1.10x |
| same primary family | 1.30x | 1.13x | 1.42x | 1.14x |

**Patch series, one author's habits and a file's content produce most of the loose figure.** What is left
for the function itself is about 1.3x on atomic labels and
about 1.1x on families. The first version's "1.70x and 1.96x" and its comparison with KWFLUX are withdrawn:
the family-level ratio is below KWFLUX's 1.45-1.66x, and the atomic ratio was measured against a different
null.

Which labels repeat, on the strict pairs, as P(next edit has it | last edit had it) over its base rate. Only
labels with at least 10 repeats in both repos are listed, ordered by the smaller of the two lifts:

| label | curl | libarchive |
|---|---:|---:|
| RETURN_VALUE | 4.98x (80 of 386) | 3.76x (17 of 109) |
| LOOP_CHANGE | 2.46x (11 of 170) | 3.85x (12 of 104) |
| PREPROC | 2.37x (281 of 1,007) | 3.22x (74 of 261) |
| SIGNATURE | 1.74x (95 of 641) | 3.23x (53 of 233) |
| COND_EDIT | 1.64x (243 of 1,104) | 1.56x (87 of 416) |
| ARG_ARITY | 1.46x (31 of 404) | 4.13x (19 of 110) |
| NUM_LITERAL | 2.89x (37 of 326) | 1.42x (14 of 164) |
| CALL_RETARGET | 1.32x (109 of 829) | 1.69x (36 of 260) |
| TYPE | 1.56x (130 of 853) | 1.30x (46 of 336) |
| COMMENT | 1.28x (667 of 2,031) | 1.39x (212 of 708) |

5 of each repo's top eight are shared (RETURN_VALUE, NUM_LITERAL, LOOP_CHANGE, PREPROC, SIGNATURE). The common additions barely repeat
(STMT_ADD 1.18x / 1.05x, CALL_ADD 1.12x /
1.17x).

## What this does and does not show

- **Shows:** function edits fall into a small closed set of types, and a function carries a modest tendency
  to receive the same types again (about 1.3x on labels, 1.1x on families) once series, author and file are
  taken out.
- **Does not show:** that edit type predicts anything. No outcome was read here.
- Part of what remains is composition: a function with no loop cannot receive LOOP_CHANGE.

## Limits

- tree-sitter parses unpreprocessed C: 16.9% of curl edits and 7.1% of libarchive
  edits have an ERROR node on either side. They are kept and flagged. The reviewer re-ran the headline
  numbers without them and found no change.
- Identity is (path with renames followed, function name). A renamed function is a death and a birth. A
  path recreated after a rename is a new file.
- A name defined more than once in a file (`#ifdef` variants) is skipped.
- Adding braces around a single statement changes nesting depth and reads as SKELETON_MOVE; CALL_RETARGET
  fires for any equal-count add and delete of callees, related or not.
- Both repos were used to develop the taxonomy and are burned for it. Two repos, both C.
- The primary-family priority order is a choice.
