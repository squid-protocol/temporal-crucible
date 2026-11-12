# Can the edit-type vector label fixes? No (ETYP-LABEL, EXPLORATORY, development)

**Type: exploratory.** No registration, **no p-value claimed**. Tool: `tools/etyp_label.py`. Repos: curl,
libarchive (both already burned). Numbers: [`etyp_label.json`](etyp_label.json). Continues
[`etyp_fix.md`](etyp_fix.md).

**Revised 2026-11-12 after an independent review ([`etyp_review.md`](etyp_review.md)).** The conclusion is the
same and stronger: with the corrected groups the type vector adds nothing detectable over commit size.

**This tests a recommendation made in the first version of `etyp_fix.md`** (use the type vector to improve
fix labels) **and does not support it.**

## What was done

One commit is one row: the fraction of its function edits carrying each of the 26 named atomic labels. An L2
logistic regression is fitted on one repo and scored on the other, in both directions. Three variants: `size`
(log2 function edits, log2 tokens changed), `type` (the label fractions), `both`. Intervals are 95%
bootstraps over commits, 200 draws. Groups are the ones `etyp_fix.py` uses: fixes against the filtered
non-fix reference, inside the labelled window.

**The target is the message label, not ground truth.**

## Result: AUC out of repo

| target | direction | n (positives) | size | type | both | both − size |
|---|---|---:|---:|---:|---:|---:|
| fix | curl → libarchive | 3,183 (1,005) | 0.577 | 0.590 | 0.594 | +0.016 [-0.002, +0.032] |
| fix | libarchive → curl | 10,902 (3,688) | 0.583 | 0.570 | 0.585 | +0.002 [-0.008, +0.012] |
| extrinsic | curl → libarchive | 1,005 (275) | 0.585 | 0.648 | 0.663 | +0.078 [+0.037, +0.127] |
| extrinsic | libarchive → curl | 3,688 (358) | 0.527 | 0.690 | 0.684 | +0.157 [+0.119, +0.196] |
| regression | curl → libarchive | 1,005 (52) | 0.501 | 0.489 | 0.503 | +0.002 [-0.087, +0.098] |
| regression | libarchive → curl | 3,688 (798) | 0.498 | 0.491 | 0.498 | +0.000 [-0.024, +0.019] |

- **Fix vs not a fix: no detectable gain over size.** The edit types add +0.016 and
  +0.002 AUC to commit size, and both intervals include zero. The first version reported
  "+0.016 to +0.032, better than size by two or three points"; that margin came from cosmetic-subject commits
  sitting in the negatives, which made size look worse than it is.
- **Extrinsic vs other fixes: 0.65 and 0.69, above size.** But
  `etyp_fix.md` shows why this is not independent evidence for the label: extrinsic is assigned from platform
  words in the subject, and platform-named commits edit preprocessor conditions regardless. The model largely
  recovers the subject rule through its code correlate. The first version called this "a usable cross-check on
  the extrinsic label"; that is withdrawn.
- **Regression vs other fixes: at chance** in both directions.

At the fixed operating point (the training repo's top third of `both` scores), 44% and 41%
of `other-fix` commits score above it, against 29% and 28% of the reference and
35% and 37% of v3c-dropped commits. Extrinsic fixes score above it 32%
and 39% of the time: the fix model does not rank them above non-fixes.

## What this changes

1. **The labelling claim is withdrawn.** The hand-judged samples in `docs/otherfix_audit.md` (libgit2,
   postgres, libxml2, redis) were **not** scored and remain unseen by ETYP.
2. **Where the type vector stops.** The type of an edit says how the code changed, not whether the old code
   was wrong. "Added a branch" is a fix and a feature alike.

## Limits

- Two C repos, message labels as the reference, one linear model. A richer model was not tried; fitting until
  the number improves on two burned repos would not be evidence.
- Commit grain. A fix that edits one function among several unrelated ones is diluted in the fractions.
