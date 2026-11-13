# What a new condition tests, and whether the new branch is a guard (ECOND, EXPLORATORY)

**Type: exploratory.** No registration, **no p-value claimed**, no multiplicity correction. Tool:
`tools/cond_content.py` (`walk` / `report` are outcome-blind; `join` reads outcomes). Repos: curl,
libarchive (both already burned). Run 2026-11-12. Numbers: [`econd.json`](econd.json). Continues
[`etyp_label.md`](etyp_label.md).

**A stop rule was set before the join: one session, and stop if condition content made a fix no more
recognisable than the edit types did. It did not, and this line stops here.**

## Why

`etyp_label.md` ended on a lead: the type of an edit ("a branch was added") does not say whether the old
code was wrong, but what the branch tests might. ETYP abstracts that away on purpose. ECOND puts it back
as a second closed taxonomy.

## Taxonomy (fixed before any outcome was read)

For every condition in the new function whose text is not in the old one: split at `&&` / `||`, peel
parentheses and `!`, and give each leaf one kind from syntax alone (NULL_CMP, ZERO_CMP, CONST_CMP, VAR_CMP,
REL_CONST, REL_VAR, BITTEST, NEGATED, TRUTHY, OTHER), plus a CALL flag. For a new `if`: GUARD_ADD when its
consequence leaves (return, goto, break, continue, alone or last in the block), otherwise ACTION_IF_ADD.
COND_NARROW marks an old condition that survives as one side of a new `&&` or `||`.

## Outcome-blind result

| | curl | libarchive |
|---|---:|---:|
| edits carrying a new condition | 30.4% | 32.0% |
| adds a guard | 6.6% | 9.3% |
| adds a non-exiting `if` | 9.1% | 10.0% |
| narrows an existing condition | 3.4% | 2.4% |
| new condition is only OTHER (residual) | 0.4% | 0.1% |

Coverage is complete. **But the kinds are house style, not meaning.** Among edits with a new condition:

| kind | curl | libarchive |
|---|---:|---:|
| NEGATED (`if(!p)`) | 36.0% | 12.0% |
| TRUTHY (`if(p)`) | 59.0% | 21.6% |
| NULL_CMP (`if (p == NULL)`) | 1.5% | 25.9% |
| ZERO_CMP (`if (n != 0)`) | 3.3% | 22.0% |

curl writes `if(!p)` where libarchive writes `if (p == NULL)`. Without type information a syntactic kind
cannot tell a null check from a flag test, so the null-ish kinds do not mean the same thing in two repos.
The comparison kinds (REL_*, VAR_CMP, CONST_CMP) are less affected.

## Join

Lifts over non-fix commits of the same size and magnitude; `*` = 95% interval excludes 1.

| new condition in a fix | curl | libarchive | |
|---|---:|---:|---|
| **REL_VAR** (`i < n`) | **1.83*** | **1.84*** | replicates |
| VAR_CMP (`a == b`) | 1.49* | 1.37* | replicates |
| COND_NARROW | 1.31* | 1.39* | replicates |
| GUARD_ADD | 1.07 | 1.36* | libarchive only |
| ACTION_IF_ADD | 1.24* | 1.01 | curl only |
| REL_CONST (`len > MAX`) | 1.01 | 1.38* | libarchive only |

- **One thing replicates cleanly: a fix adds a comparison between two variables**, most of all a relational
  one, at 1.8x in both repos. That is what a missing bounds check against a runtime length looks like.
- **"A fix adds a guard" does not replicate.** It holds in libarchive and not in curl.
- **CVE fixes (curl):** GUARD_ADD 1.57* against 1.88* for their matched controls, so guards again belong to
  that kind of commit and not to security. REL_VAR is 2.78* [1.61, 4.31] against 1.43 [0.41, 2.86] for
  controls: suggestive, 172 commits, one repo.

**Forward** (function fixed within 365 days of a non-fix edit, relative to size, history and magnitude):
REL_CONST 1.12* / 1.36*, COND_NARROW 1.12* / 1.34*, CONST_CMP 1.11* / 1.23*, ACTION_IF_ADD 1.13* / 1.21*.
Somewhat above BRANCH_ADD alone (1.09 / 1.14 in `etyp_fix.md`) in libarchive, the same in curl.

**The test the stop rule named.** Fix vs not a fix, fitted on one repo and scored on the other:

| | scored on curl | scored on libarchive |
|---|---:|---:|
| size | 0.553 | 0.542 |
| edit types + size | 0.569 | 0.573 |
| edit types + condition content + size | 0.569 | 0.579 |
| gain from condition content | +0.000 [−0.004, +0.005] | +0.005 [−0.001, +0.012] |

Condition content adds nothing to recognising an individual fix.

## What this closes

Three attempts now agree: edit types (`etyp_fix.md`), a model over them (`etyp_label.md`) and condition
content (this note) all find real, replicating **average** differences between fixes and other commits,
and none makes a single fix or a single future fix recognisable beyond about 1.1-1.3x. The syntactic
shape of a change, at the resolution an unpreprocessed parse allows, is not where the unmeasured rate in
`ceil.md` lives. A further syntactic refinement is unlikely to change that.

What is left over as a narrow, registrable claim, on repos this has not seen: **fix commits add
variable-to-variable relational conditions at a higher rate than size-matched non-fix commits** (1.8x in
two repos). It is a description of fixes, not a predictor, and is recorded here rather than registered.

## Limits

- Syntax only: no types, no macros expanded, so null checks and flag tests are not separable.
- Two C repos, message labels as the reference, uncorrected. The CVE rows are curl only.
- "New" is by condition text: a condition whose operand was renamed counts as new.
