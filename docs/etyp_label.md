# Can the edit-type vector label fixes? Mostly no (ETYP-LABEL, EXPLORATORY, development)

**Type: exploratory.** No registration, **no p-value claimed**. Tool: `tools/etyp_label.py`. Repos: curl,
libarchive (both already burned). Run 2026-11-12. Numbers: [`etyp_label.json`](etyp_label.json).
Continues [`etyp_fix.md`](etyp_fix.md).

**This tests a recommendation made in `etyp_fix.md` and does not support most of it.** That note said the
likelier use of the edit types was labelling rather than ranking. Measured out of repo, the type vector is
a weak fix detector, useless for regressions, and moderate only for the extrinsic class.

## What was done

One commit is one row: the fraction of its function edits carrying each of the 26 named atomic labels. An
L2 logistic regression is fitted on one repo and scored on the other, in both directions. Three variants,
so the type signal cannot hide behind size: `size` (log2 function edits, log2 tokens changed), `type` (the
label fractions), `both`. Intervals are 95% bootstraps over commits, 200 draws.

**The target is the message label, not ground truth.** v3c is about 0.76 precise on `other-fix`, and the
"not a fix" group contains fixes the message did not announce. That pulls every AUC toward 0.5. It does
not rescue the result: a filter this weak could not raise a 0.76-precise label by much even against a
perfect reference.

## Result: AUC out of repo

| target | direction | n (positives) | size | type | both | both − size |
|---|---|---:|---:|---:|---:|---:|
| fix vs not a fix | curl → libarchive | 4,179 (1,088) | 0.542 | 0.587 | 0.573 | +0.032 [+0.017, +0.045] |
| fix vs not a fix | libarchive → curl | 12,119 (3,688) | 0.553 | 0.571 | 0.569 | +0.016 [+0.006, +0.028] |
| **extrinsic vs other fixes** | curl → libarchive | 1,088 (347) | 0.588 | **0.668** | 0.682 | +0.094 [+0.049, +0.136] |
| **extrinsic vs other fixes** | libarchive → curl | 3,688 (358) | 0.527 | **0.705** | 0.702 | +0.175 [+0.135, +0.216] |
| regression vs other fixes | curl → libarchive | 1,088 (60) | 0.526 | 0.468 | 0.503 | −0.022 [−0.106, +0.062] |
| regression vs other fixes | libarchive → curl | 3,688 (798) | 0.498 | 0.482 | 0.493 | −0.004 [−0.026, +0.015] |

- **Fix vs not a fix: 0.57-0.59.** Better than size by two or three points, and far too weak to relabel
  anything. The lifts in `etyp_fix.md` (LOGIC 1.18-1.28) are real averages over thousands of commits; they
  do not make an individual commit recognisable.
- **Extrinsic: 0.67-0.71, with PREPROC and TYPE the two largest weights in both directions.** This is the
  one signature that carries to an unseen repo. It is a usable cross-check on the extrinsic label, which
  otherwise rests on environment words in the subject. It is not a labeller on its own.
- **Regression: 0.47-0.50.** A regression fix has no type signature. The curl-only BUILD and
  SKELETON_MOVE lifts in `etyp_fix.md` do not transfer.

At the fixed operating point (the training repo's top third of `both` scores), 41-46% of `other-fix`
commits score above it against 28-33% of non-fixes, and v3c-dropped commits sit in between (32-39%).

## What this changes

1. **The labelling claim is withdrawn before registration.** The hand-judged samples in
   `docs/otherfix_audit.md` (libgit2, postgres, libxml2, redis) were **not** scored and remain unseen by
   ETYP. They should not be spent on a 0.58 instrument.
2. **`etyp_fix.md` section "What this says", item 3 is superseded by this note** for fix-vs-non-fix. Its
   extrinsic half stands at the moderate level measured here.
3. **Where the type vector stops.** The type of an edit says how the code changed, not whether the old
   code was wrong. "Added a branch" is a fix and a feature alike. Whatever separates the two is likely in
   what the branch tests (a null, a bound, an error code), which the taxonomy deliberately abstracts away.

## Limits

- Two C repos, message labels as the reference, one linear model. A richer model was not tried; fitting
  until the number improves on two burned repos would not be evidence.
- Commit grain. A fix that edits one function among several unrelated ones is diluted in the fractions.
