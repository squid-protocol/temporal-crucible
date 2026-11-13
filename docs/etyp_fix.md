# Every fix as a vector of edit types: class, cause, follow-up (ETYP-FIX, EXPLORATORY)

**Type: exploratory.** No registration, no hypothesis fixed in advance, **no p-value claimed**. About 34
columns by 10 contrasts by 2 repos, **no multiplicity correction**. Tool: `tools/etyp_fix.py`. Repos: curl,
libarchive. Numbers: [`etyp_fix_curl.json`](etyp_fix_curl.json), [`etyp_fix_libarchive.json`](etyp_fix_libarchive.json).
Continues [`etyp.md`](etyp.md).

**Revised 2026-11-12 after an independent review ([`etyp_review.md`](etyp_review.md)). Several claims in the
first version did not survive and are withdrawn below.** The numbers here are from the corrected tool.

**This is the first place an outcome is joined to the edit types, and it burns curl and libarchive for any
confirmatory ETYP claim.** openssl and nDPI were not touched.

## How to read this

`*` marks a cell whose 95% bootstrap interval excludes 1 **and** where at least 5 commits carry the label
on both sides. With this many cells and no correction, a mark is a pointer, not a verdict. **Only cells
marked in both repos with the same direction are treated as descriptions worth keeping; a cell marked in one
repo is reported and not interpreted.**

## What was done

Each commit with 1-50 function edits becomes a vector: for every atomic label and primary family, the
fraction of its function edits that carry it.

| | curl | libarchive |
|---|---:|---:|
| commits with function edits | 14,665 | 3,786 |
| fix commits (v3c-kept, any class) | 3,688 | 1,005 |
| "not a fix" by message | 8,123 | 2,404 |
| **reference** (the row above, less cosmetic subjects) | 7,214 | 2,178 |
| dropped by v3c (in neither group) | 2,546 | 377 |

A **lift** is the group's mean fraction over the reference re-weighted to the group's own distribution of
commit size, by function edits (1, 2-3, 4-9, 10+) and by tokens changed (<=8, <=32, <=128, more).

Three things are different from the first version, each because the review showed the old choice biased a
result:

- **The reference gets the same subject filter the fixes got.** FIXLIKE v3c removes fix commits whose subject
  says typo, whitespace, reformat, refactor, cleanup or comment. The first version left such commits in the
  reference, so fixes looked "pure" by construction.
- **Defect-introducing groups hold non-fix commits only.** 40% of the first version's CVE-introducing and
  control commits were themselves fixes or v3c-dropped.
- **Size control.** The very first run controlled function-edit count only; adding tokens changed cut the
  CVE-introducing lifts roughly in half (BRANCH_ADD 2.22, STMT_ADD
  2.03, LOOP_CHANGE 2.39 in that run, kept in
  [`etyp_fix_curl_firstrun.json`](etyp_fix_curl_firstrun.json)). The bin edges were chosen after seeing that run.
  The reviewer replaced them with log2 bins and the fix lifts moved by 0.03 or less.

## A. What a fix is made of

All fixes against the reference. Marked in **both** repos, same direction:

| | curl | libarchive |
|---|---:|---:|
| WIRING (primary) | 0.78* [0.72, 0.83] | 0.69* [0.60, 0.80] |
| LOGIC (primary) | 1.15* [1.07, 1.22] | 1.18* [1.05, 1.31] |
| CALL_DEL | 0.84* [0.77, 0.92] | 0.71* [0.56, 0.88] |
| CALL_RETARGET | 0.62* [0.53, 0.73] | 0.71* [0.54, 0.92] |
| SIGNATURE | 0.71* [0.60, 0.82] | 0.65* [0.46, 0.88] |
| OPERATOR | 1.19* [1.09, 1.30] | 1.26* [1.04, 1.48] |
| STMT_DEL | 0.75* [0.68, 0.83] | 0.50* [0.40, 0.63] |

**A fix edits logic in place and does not rewire, re-sign or delete.** On the first version's data the
reviewer re-derived this under a symmetric message filter, with v3c-dropped commits folded back in, without
ERROR-node edits, with log2 size bins and with an era control, and it held in every variant; it holds again
here with the test code removed.

Not supported as a cross-repo description:

- Marked in both repos with **opposite** direction: TYPE (0.80* / 1.30*).
- Marked in one repo only: STRUCTURE (primary) (1.06* / 1.05), BUILD (primary) (1.20 / 0.46*), COSMETIC (primary) (0.89 / 1.82*), BRANCH_ADD (1.04 / 1.10*), BRANCH_DEL (0.89* / 0.83), EXIT_CHANGE (0.88* / 1.05), SKELETON_MOVE (1.87* / 1.07), CALL_ADD (0.99 / 0.80*), STRING_LITERAL (0.62* / 1.31), STMT_ADD (1.19* / 1.06), PREPROC (0.98 / 0.63*), RENAME_LOCAL (0.83 / 3.30*), FORMAT (0.79 / 3.77*).

The first version said a fix "adds a branch" and that fixes carry few renames and format edits. BRANCH_ADD is
1.04 [0.99, 1.11] in curl and 1.10* [1.00, 1.21] in libarchive: marginal. The "purity" was
produced by the asymmetric filter; with the same filter on both sides, COSMETIC is 0.89 in
curl and 1.82* in libarchive.

### Extrinsic fixes

| extrinsic fixes vs the reference | curl (358) | libarchive (275) |
|---|---:|---:|
| WIRING (primary) | 0.80* [0.65, 0.96] | 0.78* [0.62, 0.97] |
| EXIT_CHANGE | 0.66* [0.53, 0.82] | 0.71* [0.55, 0.89] |
| CALL_ADD | 0.83* [0.71, 0.93] | 0.77* [0.62, 0.89] |
| CALL_DEL | 0.60* [0.42, 0.82] | 0.50* [0.30, 0.71] |
| TYPE | 2.01* [1.59, 2.47] | 2.17* [1.69, 2.79] |
| STMT_DEL | 0.48* [0.32, 0.68] | 0.46* [0.30, 0.64] |

PREPROC is 2.37* [2.06, 2.70] in curl and 1.35 [0.98, 1.74] in libarchive.

**This "signature" is partly the label rule seen from the other side.** A commit is labelled extrinsic when
its subject names a platform, compiler, bitness or C standard together with an action word, and a commit
that names a platform edits `#if` blocks whether or not it fixes anything. Against non-fix commits whose
subject also names a platform (358 vs 170 in curl, 275 vs 167 in libarchive):

| extrinsic fixes vs platform-named non-fixes | curl | libarchive |
|---|---:|---:|
| PREPROC | 0.65* [0.55, 0.81] | 0.43* [0.30, 0.63] |
| TYPE | 1.44 [0.89, 2.66] | 1.52 [0.98, 2.80] |

Extrinsic fixes carry **less** PREPROC than other platform-named commits, and the TYPE excess is not marked
in either repo against that reference. The first version's sentence that the extrinsic signature "is what
'the outside world moved' should look like" is withdrawn.

### Other classes and direct contrasts

- **Regression fixes.** curl (798): BUILD 2.58* [1.81, 3.74],
  SKELETON_MOVE 1.85* [1.21, 2.52]. libarchive has 52 and marks
  nothing. One repo; not interpreted.
- **Latent fixes are the CVE fixes.** In curl the `latent` class and the security-fix events are the same
  172 commits; the first version reported them as two findings.
- **CVE fixes against their matched controls, tested directly** (172 vs 115): no label is marked.
  BRANCH_ADD 1.08 [0.80, 1.49], TYPE 0.19 [0.03, 1.56]. **CVE fixes and their
  controls are not distinguishable on any edit type at this sample size.** The first version's "purity"
  claim compared two separate intervals and rested on one to nine commits per cell.
- **Fixes that answer an outside report against fixes that do not, tested directly** (curl, 960 vs 2,728):
  marked are FORMAT 0.21*, COSMETIC (primary) 0.56*, TYPE 0.57*, STMT_DEL 1.31*, CALL_DEL 1.28*, BRANCH_DEL 1.25*, STRUCTURE (primary) 1.09*. libarchive has
  too few reported fixes to compare. One repo.
- **CVE severity** is not analysed: 26 High or Critical commits.

## B. Commits later named as introducing a defect (curl only)

Non-fix members only: 68 CVE-introducing and 289
regression-inducing commits.

| | CVE-introducing | regression-inducing |
|---|---:|---:|
| STRUCTURE (primary) | 1.22* [1.06, 1.40] | 1.01 [0.91, 1.10] |
| WIRING (primary) | 0.90 [0.69, 1.10] | 1.22* [1.04, 1.40] |
| LOGIC (primary) | 0.57* [0.32, 0.89] | 0.82 [0.64, 1.02] |
| DATA (primary) | 0.70 [0.38, 1.07] | 0.75* [0.56, 0.96] |
| BRANCH_ADD | 1.51* [1.28, 1.77] | 0.93 [0.81, 1.06] |
| BRANCH_DEL | 0.62* [0.33, 0.93] | 1.02 [0.80, 1.27] |
| EXIT_CHANGE | 1.42* [1.18, 1.72] | 0.93 [0.80, 1.06] |
| CALL_ADD | 1.38* [1.22, 1.53] | 1.10* [1.01, 1.21] |
| CALL_RETARGET | 0.78 [0.42, 1.23] | 1.50* [1.09, 1.89] |
| COND_EDIT | 0.42* [0.20, 0.64] | 1.21 [0.95, 1.48] |
| NUM_LITERAL | 0.47* [0.14, 0.95] | 1.17 [0.66, 1.77] |
| STRING_LITERAL | 0.96 [0.29, 1.85] | 0.37* [0.16, 0.66] |
| TYPE | 0.55* [0.22, 0.92] | 0.77 [0.50, 1.12] |
| LOCAL_DECL | 0.95 [0.71, 1.17] | 1.15* [1.03, 1.31] |
| STMT_ADD | 1.44* [1.27, 1.61] | 1.07 [0.94, 1.19] |
| STMT_DEL | 0.56* [0.29, 0.86] | 0.94 [0.77, 1.15] |
| PREPROC | 1.69* [1.15, 2.17] | 1.31* [1.04, 1.60] |
| FORMAT | 0.68 [0.12, 1.56] | 0.38* [0.08, 0.80] |

CVE-introducing commits add branches, exits, statements and calls and carry few in-place logic edits; they
look like feature additions. One repo, 68 commits, many cells: a description
of curl, not a finding. Regression-inducing commits are younger than the reference (median year 2020 against
2015 in the reviewer's check), and CALL_RETARGET lost its mark there under an era control.

## C. Does the type of an edit say whether the function gets fixed next?

After a **non-fix** edit, within 365 days: is the same function edited by a fix? And, as a negative control,
is it edited by any other non-fix commit? Each type is compared with the **other** non-fix edits in the same
stratum: function size, tokens changed, edits to the function in the prior year, a fix in the prior year,
four-year era. Sweep commits are excluded.

22,038 eligible edits in curl (base rates 39.4% fixed, 66.2% edited);
5,707 in libarchive (28.9%, 51.5%).

| type of the non-fix edit | fixed: curl | fixed: libarchive | edited: curl | edited: libarchive |
|---|---:|---:|---:|---:|
| STRUCTURE (primary) | 1.06* | 1.10 | 1.03 | 1.05 |
| WIRING (primary) | 1.01 | 0.79* | 1.00 | 1.00 |
| LOGIC (primary) | 0.98 | 1.07 | 0.99 | 0.99 |
| BRANCH_ADD | 1.08* | 1.08 | 1.03* | 1.06 |
| STMT_ADD | 1.11* | 1.19* | 1.07* | 1.07* |
| CALL_ADD | 1.08* | 0.99 | 1.07* | 1.09* |
| CALL_DEL | 0.93* | 0.81* | 1.02 | 0.99 |
| PREPROC | 1.08* | 1.18* | 1.05* | 1.12* |
| COMMENT | 1.12* | 1.24* | 1.03* | 1.07* |
| SIGNATURE | 0.87* | 1.11 | 0.87* | 0.84* |
| TYPE | 0.90* | 0.98 | 0.96* | 0.83* |

Marked in both repos for "fixed": CALL_DEL (0.93* / 0.81*), STMT_ADD (1.11* / 1.19*), PREPROC (1.08* / 1.18*), COMMENT (1.12* / 1.24*).

- **The association is small, and it is not specific to edit type.** COMMENT, which says nothing about what
  the code does, shows the largest "effect". The same labels also predict that the function is simply edited
  again (STMT_ADD 1.07* / 1.07*, PREPROC 1.05* /
  1.12*). A substantive edit marks a function people are working on.
- **LOGIC is 0.98 in curl and 1.07 in libarchive, neither marked.** The first version said LOGIC
  "predicts nothing" and contrasted it with STRUCTURE; that contrast came from sweep commits in libarchive
  and is withdrawn. Neither family is distinguishable from 1 in libarchive here.
- The first version did not exclude sweep commits from this section although it said it did, and compared
  each type with a base that included the type. Its libarchive "cosmetic edits are followed by fixes, 1.55x"
  was produced by sweeps: it is 1.09 now.

## What this says

1. **One description holds across both repos and every variant tried: a fix is in-place logic, not rewiring
   or deletion.**
2. **As a forward signal the types are weak and not separable from "this function is active".**
3. Whether the type vector can label fixes is tested in [`etyp_label.md`](etyp_label.md): it cannot.

## Limits

- Exploratory, uncorrected, two C repos. Section B and the CVE contrast are curl only.
- Fix labels are v3c message labels (0.761 precise pooled, `otherfix_audit.md`). The misclassification is
  **not** uniformly toward 1: it depends on which subjects the rule removes, which is why the reference is
  now filtered the same way.
- C counts a fix to the same function by name; a fix landing in a neighbouring function is missed.
- The size and magnitude bins, the 365-day windows and the strata in C were all chosen after seeing data.
