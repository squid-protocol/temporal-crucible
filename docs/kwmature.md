# What changes in a function after birth, if the shape does not? (KWMAT, EXPLORATORY)

**Type: exploratory.** No registration, no hypothesis fixed in advance, **no p-value claimed**. Tool:
`tools/kwmature_eval.py` (`freeze` / `drift` / `direction`). Repo: curl, 324 quarterly snapshots,
1999-12-29 to 2026-09-02. Run 2026-11-11.

## The question

The program's standing finding is that **about 71% of functions never change shape** — and a *shape* is the
**set** of keyword families present (`tools/lat_eval.py`: `P: bool (N x len(cols)) presence`). A set cannot
see maturation. `{branch, pointer, alloc}` is the same set whether a function holds one branch or nine, in
any order, at any nesting depth. So "born in final form" may be a fact about the measure's resolution rather
than about code.

**The engine already records counts, not flags.** `struct_branch` runs 0…1631 in the curl walk. The presence
measure thresholds that to 0/1 and discards the rest. This note uses the discarded part.

## 1 · The binary measure hides change in a quarter of "frozen" functions

13,745 curl functions seen in ≥ 2 snapshots:

| what is held fixed | never changes over the life |
|---|---|
| presence **set** (the existing measure) | **64.3%** |
| line count | 52.3% |
| **count vector** | **46.6%** |

**Of the 8,842 functions whose presence set never changes, 2,430 — 27.5% — change their counts.** The engine's
own numbers move while the binary measure calls them unchanged.

## 2 · But the *mix* is strongly conserved, and that is a real finding, not an artifact

Composition drift = cosine between the normalised count vectors at the first and last snapshot. Normalising
means **pure growth with a fixed recipe scores 1.000 by construction**, so this isolates re-proportioning from
scaling.

| | median | p25 | p10 | mix moved (cos < 0.95) |
|---|---|---|---|---|
| **a function's own life** | **0.998** | 0.973 | 0.915 | **16.5%** |
| **null: unrelated function, same mass band** | **0.741** | 0.513 | 0.303 | **92.2%** |

The null is the control that makes the number readable: a high cosine could have meant only that every C
function has a similar keyword mix. It does not. **A function's recipe is its own**, and it keeps it.

Restricted to the shape-frozen functions, drift is median **1.000** and the mix moves in only **3.6%** — so
when a shape-frozen function's counts move, they move **proportionally**.

## 3 · So what is actually changing: scale, not recipe

Among the 4,100 functions whose keyword mass grew: median growth **×1.19**, median drift **0.981**, mix moved
in **27.3%**.

**The crab keeps its shape and its proportions, and gets bigger.** A function is born with its final
*recipe*; over its life it adds more of the same ingredients. That is a sharper statement than "born in final
form", and it is the one the counts support.

The exception is real but a minority: **about one function in six re-proportions**, and one grower in four.

## 4 · Where the minority drifts to

Mean change in each family's share of a function's keyword mass, birth → last seen (13,745 functions).
Magnitudes are small — a few tenths of a percent of share — so this is a direction, not an effect size.

| gaining share | | losing share | |
|---|---|---|---|
| `state_pointers` | +0.0037 | `state_print_hits` | −0.0029 |
| `struct_branch` | +0.0032 | `state_memory_alloc` | −0.0024 |
| `def_freeze_hits` | +0.0024 | `def_cleanup` | −0.0019 |
| `struct_linear` | +0.0021 | `arch_api` | −0.0017 |

A readable story — functions accumulate pointers and branches (edge cases, indirection) and shed debug
printing, allocation and cleanup (moved out, centralised) — and one that is **not tested here**. It is a
direction in a descriptive table, offered for someone to register properly.

## 5 · Limits, and the two dimensions still unmeasured

- **Identity is `(file_path, func_name)`.** A rename or a move reads as a death and a birth, so long lives are
  undercounted and the sample leans toward survivors. That plausibly *inflates* conservation.
- **The walk is quarterly**, so a change and its reversal inside one quarter is invisible.
- **Cosine on normalised counts is mass-weighted**, so it mostly tracks the dominant families
  (`struct_branch`, `struct_linear`). A rank-based or small-family-sensitive measure would complement it.
- **Order and nesting are not measured at all.** Both need the source rather than the database, and both are
  exactly where a "same recipe, more of it" function could still be reorganising: the same keywords in a
  different sequence, or the same sequence at a different depth. **This is the obvious next cut**, and the
  one that could still overturn §3.

## 6 · What it changes

"Functions are born in their final form" should be restated as **"functions are born with their final
recipe"**. The set is frozen for 64%, the *mix* is near-frozen for almost all, and what moves is magnitude —
in more than half of all functions. Any future study that treats keyword families as present/absent is
discarding the dimension along which functions actually move.
