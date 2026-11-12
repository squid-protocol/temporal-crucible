# Every fix as a vector of edit types: class, impact, cause, follow-up (ETYP-FIX, EXPLORATORY)

**Type: exploratory.** No registration, no hypothesis fixed in advance, **no p-value claimed**. About 30
labels by 10 groups are compared with **no multiplicity correction**: read this as a map. Tool:
`tools/etyp_fix.py`. Repos: curl, libarchive. Run 2026-11-12. Numbers: [`etyp_fix_curl.json`](etyp_fix_curl.json),
[`etyp_fix_libarchive.json`](etyp_fix_libarchive.json). Continues [`etyp.md`](etyp.md).

**This is the first place an outcome is joined to the edit types, and it burns curl and libarchive for any
confirmatory ETYP claim.** openssl and nDPI were not touched. The classifier (`tools/edit_types.py`) still
reads no outcome; the join lives in a separate tool.

## What was done

Each commit becomes a vector: for every atomic label and primary family, the fraction of the commit's
function edits that carry it. Outcomes come from files already in the repo: fix class
(`events/<repo>_xc.json`, other-fix kept by FIXLIKE v3c), CVE severity and matched controls
(`events/<repo>.json`), regression-inducing links (`events/<repo>_reg_links.json`), and whether the
message carries a `Reported-by:`, `Bug:` or `Fixes #n` line.

| | curl | libarchive |
|---|---:|---:|
| commits with function edits, in the labelled window | 14,357 | 4,754 |
| fix commits | 3,688 | 1,088 |
| non-fix commits (reference) | 8,123 | 3,091 |
| dropped by v3c (in neither group) | 2,546 | 575 |

A **lift** is the group's mean fraction over the non-fix reference re-weighted to the group's own
distribution of commit size, both by function edits (1, 2-3, 4-9, 10+) and by tokens changed (<=8, <=32,
<=128, more). `*` marks a 95% bootstrap interval (300 draws, commits resampled) that excludes 1.

**The first run controlled function-edit count only, and that mattered.** Adding the changed-token control
cut the defect-introducing lifts roughly in half (curl CVE-introducing BRANCH_ADD 2.22 to 1.49, STMT_ADD
2.03 to 1.42, LOOP_CHANGE 2.39 to 1.10, LOCAL_DECL 1.85 to 1.06). Much of what looked like "type" was "a
bigger edit". The top token bin is open-ended, so some of what remains is probably still size.

## A. What a fix is made of

All fixes against non-fix commits of the same size and magnitude, curl / libarchive:

| | curl | libarchive | |
|---|---:|---:|---|
| LOGIC (primary) | 1.18* | 1.28* | more |
| OPERATOR | 1.23* | 1.37* | more |
| COND_EDIT | 1.10* | 1.25* | more |
| BRANCH_ADD | 1.10* | 1.17* | more |
| WIRING (primary) | 0.81* | 0.67* | less |
| CALL_RETARGET | 0.64* | 0.62* | less |
| SIGNATURE | 0.71* | 0.70* | less |
| CALL_DEL | 0.81* | 0.64* | less |
| STMT_DEL | 0.72* | 0.52* | less |

**A fix edits a condition or an operator in place, or adds a branch. It does not rewire, re-sign or
delete.** This holds in both repos with intervals excluding 1.

**The fix classes have different signatures, and the extrinsic one replicates:**

| extrinsic fixes | curl (358) | libarchive (347) |
|---|---:|---:|
| TYPE | 1.96* | 2.21* |
| PREPROC | 2.39* | 1.48* |
| LOGIC (primary) | 1.44* | 1.30* |
| STRUCTURE (primary) | 0.69* | 0.87 |
| CALL_DEL | 0.58* | 0.58* |

An extrinsic fix changes types and preprocessor conditions and leaves control flow alone, which is what
"the outside world moved" should look like. Regression fixes in curl (798) lean BUILD 2.61* and
SKELETON_MOVE 1.79*; libarchive has 60 and does not confirm either. Latent fixes exist only in curl (172):
BRANCH_ADD 1.26*, STMT_ADD 1.23*, TYPE 0.07*, NAMING 0.05*.

## A. Impact and reports

- **CVE fixes against their matched controls (curl, 172 vs 115).** On structure the two are the same:
  BRANCH_ADD 1.26* vs 1.35*, STRUCTURE 1.16* vs 1.24*. The controls are matched on files and diff size, so
  the "CVE fixes add guards" reading is a property of that kind of commit, not of security. What does
  separate them is purity: TYPE 0.07* vs 0.53*, NAMING 0.05* vs 1.08, COSMETIC 0.21* vs 0.87. A CVE fix
  carries almost nothing but the fix.
- **Severity.** High+ has 26 commits, Low and Medium 73 each. No gradient can be read at that size and
  none is claimed.
- **Reported vs unreported fixes (curl, 960 vs 2,728).** Reported fixes are also purer (NAMING 0.03*,
  FORMAT 0.18*, TYPE 0.49*) and slightly more guard-shaped (BRANCH_ADD 1.13* vs 1.08*). libarchive has 51
  reported fixes, too few to check.

## B. What defect-introducing commits are made of (curl only)

| | CVE-introducing (113) | regression-inducing (437) |
|---|---:|---:|
| BRANCH_ADD | 1.49* | 1.04 |
| EXIT_CHANGE | 1.42* | 0.99 |
| STMT_ADD | 1.42* | 1.14* |
| CALL_ADD | 1.34* | 1.13* |
| PREPROC | 1.38* | 1.18 |
| CALL_RETARGET | 0.86 | 1.34* |
| COND_EDIT | 0.61* | 1.16 |
| TYPE | 0.48* | 0.71* |

Commits later named as introducing a CVE add new control paths. Regression-inducing commits are close to
flat once magnitude is controlled; the one distinct mark is CALL_RETARGET. Neither has a second repo.

## C. Does the type of an edit say whether the function gets fixed next?

After a **non-fix** edit, is the same function edited by a fix within 365 days? Relative to other non-fix
edits to functions of the same size, the same prior edit count, and the same edit magnitude; functions
resampled for the interval.

| | curl (30,324 edits, base 35.2%) | libarchive (9,580 edits, base 24.9%) |
|---|---:|---:|
| STRUCTURE (primary) | 1.05* | 1.14* |
| BRANCH_ADD | 1.09* | 1.14* |
| STMT_ADD | 1.12* | 1.06* |
| PREPROC | 1.08* | 1.19* |
| SKELETON_MOVE | 1.10* | 1.54* |
| COMMENT | 1.10* | 1.20* |
| LOGIC (primary) | 0.99 | 1.00 |
| WIRING (primary) | 0.98 | 0.76* |
| COSMETIC (primary) | 0.92* | 1.55* |
| SIGNATURE | 0.79* | 0.93 |

**The effect is real in both repos and small.** An edit that adds a branch or a statement is followed by
a fix about 5-15% more often than size, history and magnitude predict. In-place LOGIC edits, the mark of a
fix, predict nothing about the next fix. COSMETIC and WIRING point in opposite directions in the two
repos and are not findings.

## What this says

1. **The types describe fixes well.** The fix signature and the extrinsic signature replicate across two
   repos. That is new: until now fix class came only from the commit message.
2. **As a forward predictor the types are weak.** About 1.1x after the controls. This will not close the
   22-point gap in `ceil.md` on its own, and it lowers the odds for the draft ETYP-H1 as written
   (STRUCTURE-or-LOGIC edit count): LOGIC carries no forward signal here.
3. **Superseded for fix-vs-non-fix by [`etyp_label.md`](etyp_label.md): out of repo the vector reaches
   AUC 0.57-0.59, too weak to relabel. The extrinsic half stands at AUC 0.67-0.71.** As first written:
   **The likelier use is labelling, not ranking.** `other-fix` is 85-97% of outcome mass and its label is
   0.76 precise from message text alone. A commit's type vector is independent of its message. A fix that
   is LOGIC-heavy and carries no rename, format or type change looks like a fix; the extrinsic class can
   be recognised by TYPE and PREPROC.

## Limits

- Exploratory, uncorrected, two C repos. Sections B, the CVE comparison and latent fixes are curl only.
- Magnitude is four token bins with an open top; residual size confounding is likely in B.
- Fix labels are v3c message labels (0.761 precise pooled). A wrong label blurs every lift toward 1.
- C counts a fix to the same function by name; a fix that lands in a neighbouring function is missed.
- 16.9% (curl) and 5.9% (libarchive) of edits parsed with an ERROR node and are included.
