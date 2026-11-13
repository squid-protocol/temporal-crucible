# ETYP: does a function's edit-type history predict fixes? (WITHDRAWN DRAFT, 2026-11-12)

**Status: WITHDRAWN before approval. This is not a registration, nothing in it was ever run on an eligible
repo, and it has no entry in `docs/HYPOTHESES.md`.** It is kept so the reasons are on record. The exploratory
work it would have followed is in [`etyp.md`](etyp.md), [`etyp_fix.md`](etyp_fix.md),
[`etyp_label.md`](etyp_label.md) and [`econd.md`](econd.md); the review that led to the withdrawal is in
[`etyp_review.md`](etyp_review.md).

## What the draft proposed

At function-snapshot grain, on openssl (primary) and nDPI (replication): that the count of "behavioural"
edits in the trailing 8 quarters (primary family STRUCTURE or LOGIC) ranks functions for a fix in the next
year better than the raw edit count (H1) and better than the stronger size order (H2), with a negative
control on inert edits (H3) and an ERROR-node guard (H4).

## Why it is withdrawn

**The exploratory evidence does not support the bet.**

- After a non-fix edit, the relative one-year fix rate is 1.06 (curl) and 1.10 (libarchive, not marked) for
  STRUCTURE and 0.98 and 1.07 for LOGIC. The largest association belongs to COMMENT, and a negative-control
  outcome (any later edit) moves with the same labels.
- The type vector adds no detectable AUC to commit size for telling a fix from a non-fix.

**The draft was not sound as a registration**, as the review set out:

- no alpha, no sidedness, no bootstrap unit, and no statement of which fix classes count as the outcome;
- replication defined as "same sign" only;
- H3 passed on a point estimate, so an underpowered run would pass it automatically; it needs an equivalence
  test, as REW used;
- "power stated" was only an under-20-positives flag, with no power for an effect near 1.1x;
- the predictor depended on the primary-family priority order (an edit with CALL_ADD and COND_EDIT is WIRING,
  so not "behavioural"), and it is a 44-46% subset of the count it was to be compared with;
- its motivation quoted `ceil.md` figures from mixed rows and a `rew.md` figure that holds for curl extrinsic
  fixes only;
- its prior-work list was written from memory and never checked against the sources.

## What a sound registration from this line would look like

One narrow, descriptive claim survived review in both repos: **fix commits add relational comparisons between
two variables at a higher rate than size-matched non-fix commits** (1.80 and 1.67 on the discovery data, the
largest of about two dozen cells, so expect shrinkage). Registering it would need: the tool frozen by hash at
the commit that follows the review; openssl and nDPI as the only eligible repos; one two-sided test at a
stated alpha on the lift with a commit bootstrap; a stated minimum effect; the same subject filter on fixes
and reference; and a prior-work section checked against the sources. It describes fixes and predicts nothing,
so it is worth registering only if a confirmed description is wanted on the record.

openssl and nDPI remain unwalked and unscored by any ETYP or ECOND tool.
