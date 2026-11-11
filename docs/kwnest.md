# Order and nesting: the skeleton is frozen too, so functions mature by rewiring (KWNEST, EXPLORATORY)

**Type: exploratory.** No registration, no hypothesis fixed in advance, **no p-value claimed**. Tool:
`tools/kwnest_eval.py` (`probe` / `run` / `what`). Repo: curl. Run 2026-11-11. Continues
[`kwmature.md`](kwmature.md).

## Why this needed a second tool

KWMAT showed a function's keyword *recipe* is conserved while its *scale* is not, and left two dimensions
unmeasured: the **order** of keywords and their **nesting depth**. Neither is in the scan database, and not by
oversight — `function_data` holds exactly one positional column, `start_line`, the function's own starting
line. Nothing records where inside a function a keyword falls. (`complexity` equals `struct_branch` in **all
809,654 rows** of the curl walk: it is the branch-keyword count, not a control-flow measure.) **From the
database you can say a function has more keywords; you cannot say one moved.**

So this is a two-instrument study, and each does what the other cannot:

| | GitGalaxy scan DB | tree-sitter |
|---|---|---|
| gives | counts per family, function identity, 324 snapshots, 27 years, cheaply | each keyword's position in sequence and its nesting depth |
| cannot give | **where** a keyword sits | scale — it must re-parse source at every snapshot |

GitGalaxy selects the population and says what and how much changed; tree-sitter says whether anything moved.

## The decisive question, and the trap in it

Among functions whose keyword **multiset** is identical at both ends — the ones every count-based measure
calls unchanged — how many have a different **order** or **depth** profile?

The first run said 0.0% and 0.7% of 692 functions, which is **not usable as stated**: a function with an
identical keyword multiset is usually a function nobody edited, and untouched code cannot reorganise. The
denominator had to be split:

| of the 692 with an identical multiset | | |
|---|---|---|
| byte-identical source | 317 | 45.8% — cannot reorganise; excluded, not evidence |
| **edited, same multiset** | **375** | **54.2% — the only functions that can answer the question** |

## Result: the skeleton does not move

Of the **375 genuinely edited** functions:

| | |
|---|---|
| control-keyword **order** changed | **0 — 0.0%** |
| **nesting depth** profile changed | **5 — 1.3%** (2 deeper, 3 shallower) |
| neither (identical arrangement) | 370 — 98.7% |

A function's control skeleton — which keywords, in what proportion, in what order, at what depth — is laid
down at birth and essentially never rearranged, **even when the function is edited**. The frozen-shape
finding is therefore not an artifact of a coarse measure: the two dimensions that could have overturned it
were examined and are frozen as well.

## So what *does* change: naming and wiring

Those 375 functions were edited. Leaf-token differences for 300 of them (4,233 token differences):

| token kind | share | | token kind | share |
|---|---|---|---|---|
| **identifier** | **41.1%** | | number_literal | 3.5% |
| field_identifier | 6.9% | | string_content | 3.0% |
| `;` | 4.7% | | comment | 2.7% |
| `(` / `)` | 3.6% each | | type_identifier | 2.6% |
| `,` | 3.5% | | primitive_type | 2.6% |

**Over half of all change is naming and wiring** — identifiers, field accesses, types. The punctuation entries
are arguments and statements being added and removed *around* an unchanged skeleton.

**Functions mature by being rewired, not by being restructured.** They keep their control flow and change
what they talk to.

## What this changes for the program

1. **"Born in final form" survives its hardest test**, and can now be stated precisely: the control skeleton
   is fixed at birth; scale grows (median ×1.19); arrangement does not move.
2. **Keyword-family analysis is measuring something that genuinely does not move.** That is why it describes
   and does not predict — not because the families are wrong, but because the quantity is near-constant over
   a life. No refinement of presence, counts, order or depth will recover a maturation signal.
3. **A maturation signal, if there is one, lives in the call graph and in naming.** GitGalaxy already stores
   `calls_out_to`, `references_to` and `func_fan_in`/`func_fan_out` per function per snapshot. That is the
   next instrument, and it needs no new scanning.

## Limits

- **First-vs-last only.** Reorganisation that happened and reverted is invisible, and the walk is quarterly,
  so intra-quarter churn is invisible too. Both push the reorganisation rate **down**: 1.3% is a floor.
- **Identity is `(file_path, func_name)`**, so renames and moves read as death and birth, biasing toward
  survivors.
- **curl only**, one C project, 1,200 sampled functions. Nothing here is replicated.
- The token-kind table counts **token differences, not edits**; one rename touching many sites counts many
  times.
