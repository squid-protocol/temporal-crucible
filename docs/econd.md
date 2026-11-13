# What a new condition tests, and whether the new branch is a guard (ECOND, EXPLORATORY)

**Type: exploratory.** No registration, **no p-value claimed**, no multiplicity correction. Tool:
`tools/cond_content.py` (`walk` / `report` read no outcome; `join` does). Repos: curl, libarchive (both
already burned). Numbers: [`econd.json`](econd.json). Continues [`etyp_label.md`](etyp_label.md).

**Revised 2026-11-12 after an independent review ([`etyp_review.md`](etyp_review.md)).** Three of the labels
were wrong in a measurable share of cases and have been fixed; the conclusion did not change.

## What this is, and what it is not

`etyp_label.md` ended on a lead: the type of an edit does not say whether the old code was wrong, but what an
added branch tests might. ECOND classifies that.

**Two things the first version claimed about its own process cannot be shown and are withdrawn.**

- It said the taxonomy was "fixed before any outcome was read". The taxonomy was designed after the same
  commits' outcomes had been seen in `etyp_fix` and `etyp_label`, and it was then corrected after its own
  join. It is a second look at burned data.
- It said a stop rule was "set before the join". The rule was stated in the working session before the join
  ran, but the tool, the results and the rule were committed together, so the record does not prove the
  order. By this repo's own standard that is not demonstrably prior.

## Taxonomy

For every condition in the new function whose text is not in the old one: split at `&&` / `||`, peel
parentheses and `!`, and give each leaf one kind from syntax alone (NULL_CMP, ZERO_CMP, CONST_CMP, VAR_CMP,
REL_CONST, REL_VAR, BITTEST, NEGATED, TRUTHY, OTHER), plus a CALL flag. GUARD_ADD: the number of exiting
`if`s grew and one of them has a new condition. ACTION_IF_ADD: the same for non-exiting `if`s. COND_NARROW: an
old condition that disappeared has all its leaves inside a new condition with more.

Corrected after review: GUARD_ADD and ACTION_IF_ADD used to key on the total `if` count (an edited guard
beside an added action was called an added guard, in about 8% of GUARD_ADD edits); COND_NARROW missed
three-conjunct narrowing and fired on unrelated conditions (33-42% of its flags); constant expressions such as
`MAX_N - 1` were read as variables (15% of REL_VAR leaves).

## Outcome-blind result

| | curl | libarchive |
|---|---:|---:|
| edits carrying a new condition | 30.4% | 37.9% |
| adds a guard | 6.5% | 10.8% |
| adds a non-exiting `if` | 9.1% | 11.9% |
| narrows an existing condition | 2.7% | 2.9% |
| new condition is only OTHER (residual) | 0.4% | 0.1% |

**The null-ish kinds are house style, not meaning.** Among edits with a new condition:

| kind | curl | libarchive |
|---|---:|---:|
| NEGATED | 36.0% | 8.6% |
| TRUTHY | 59.0% | 20.2% |
| NULL_CMP | 1.5% | 26.5% |
| ZERO_CMP | 3.2% | 21.5% |

curl writes `if(!p)` where libarchive writes `if (p == NULL)`. Without type information a syntactic kind
cannot tell a null check from a flag test.

## Join

Same groups, reference and marking rule as [`etyp_fix.md`](etyp_fix.md).

All fixes against the reference. Marked in both repos, same direction:

| new condition in a fix | curl | libarchive |
|---|---:|---:|
| REL_VAR | 1.80* [1.43, 2.22] | 1.67* [1.33, 2.10] |

Marked in one repo only: GUARD_ADD (1.02 / 1.26*), ACTION_IF_ADD (1.16* / 0.98), COND_NARROW (1.24* / 1.12), CONST_CMP (1.20* / 1.06), VAR_CMP (1.45* / 1.39), REL_CONST (1.05 / 1.22*), NEGATED (1.15* / 1.16), G:REL_VAR (0.95 / 1.75*), G:CALL (0.80* / 0.93).

- **One cell is marked in both repos: a fix adds a relational comparison between two variables (`i < n`).**
  The reviewer checked it is not a for-loop artefact and that it survives log2 size bins. On a new guard
  specifically (G:REL_VAR) it is 0.95 [0.47, 1.67] in curl and 1.75* [1.02, 2.86] in libarchive,
  so the first version's reading of it as "a missing bounds check" is not supported and is withdrawn. It is
  also the largest of about two dozen cells on the data that suggested it, so its size should be expected to
  shrink elsewhere.
- **"A fix adds a guard" differs between the repos**: 1.02 [0.91, 1.13] in curl,
  1.26* [1.08, 1.49] in libarchive.
- **CVE fixes against their matched controls** (curl, direct): nothing is marked. REL_VAR is
  5.36 [1.62, 174.65] on 11 commits; not distinguishable.

**Forward** (function fixed within 365 days of a non-fix edit; strata as in `etyp_fix.md`): marked in both
repos are REL_CONST (1.09* / 1.19*), TRUTHY (1.09* / 1.18*).
REL_VAR is 1.05 / 1.07. Nothing here is larger than what the edit types alone show.

**Does condition content help recognise a fix?** Fitted on one repo and scored on the other:

| | scored on curl | scored on libarchive |
|---|---:|---:|
| size | 0.583 | 0.577 |
| edit types + size | 0.585 | 0.594 |
| edit types + condition content + size | 0.587 | 0.595 |
| gain from condition content | +0.002 [-0.003, +0.007] | +0.001 [-0.007, +0.011] |

**No detectable gain; at most +0.011 AUC.**

## Where this line stands

Edit types, a model over them, and condition content each find average differences between fixes and other
commits, a few of which appear in both repos. None of them separates fixes from non-fixes better than commit
size does (AUC about 0.58 for all three). The forward associations are small and shared with a negative
control. The syntactic shape of a change, at the resolution an unpreprocessed parse allows, has not shown
itself to be where the unmeasured rate in `ceil.md` lives.

## Limits

- Syntax only: no types, no macros expanded.
- Two C repos, message labels as the reference, uncorrected, a second look at burned data.
- "New" is by condition text: a condition whose operand was renamed counts as new.
