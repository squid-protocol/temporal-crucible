# Independent review of ETYP / ETYP-FIX / ETYP-LABEL / ECOND, and what it changed

**2026-11-12.** The four notes and their tools were written in one session by one author. Before the PR was
marked ready, two reviewers that had not seen the author's conclusions were given the branch: one to find
logic errors in the code, one to check every claim against the data and test alternative explanations. Both
could run code and neither could change the repo. This note records what they found and what was done. The
first versions of the notes are in the branch history (commits `24cb2d8`, `9a851a2`, `e0fc915`, `0aca88e`).

**The review overturned or weakened most of the interpretive claims and confirmed one description.** That is
the result of this note, and the reason it exists: the same author, unreviewed, had published all of them.

## Defects in the code

| # | defect | effect | disposition |
|---|---|---|---|
| 1 | libarchive's source roots included its test trees | 31% of libarchive edits were test code; it flipped the mark on 9 of 36 columns for "all fixes" | fixed: test trees excluded, a test pins it |
| 2 | the follow-up analysis did not drop sweep commits, against its own docstring | 27% / 20% of its edits came from sweeps; libarchive COSMETIC 1.55x was a sweep artefact | fixed |
| 3 | the follow-up base included the type being tested | every relative rate pulled toward 1 | fixed: each type against the others in its stratum |
| 4 | a group with zero occurrences got a significance mark | 41 marked cells meant "no occurrences in a small group" | fixed: a mark needs 5 commits on both sides |
| 5 | defect-introducing groups contained fixes and v3c-dropped commits | section B partly measured "is a fix" | fixed: non-fix members only |
| 6 | GUARD_ADD / ACTION_IF_ADD keyed on the total `if` count | about 8% of GUARD_ADD edits mislabelled | fixed |
| 7 | COND_NARROW missed three-conjunct narrowing and fired on unrelated conditions | 33-42% of its flags wrong | fixed |
| 8 | constant expressions read as variables | 15% of REL_VAR leaves | fixed |
| 9 | structure labels compared group totals, not keywords | 0.4% of edits | fixed; changes the taxonomy after outcomes were seen, disclosed in `etyp.md` |
| 10 | a stratum with no reference members lost its weight | none on the published numbers | fixed, with a test |
| 11 | a path recreated after a rename shared an identity with the renamed file | 86 curl rows | fixed, with a test |
| 12 | the label model counted 308 post-harvest commits as "not a fix" | small | fixed |
| 13 | a CVE fix with no kept event counted as a non-fix | 1 libarchive commit | not fixed |

Left as stated limits: brace-only edits read as SKELETON_MOVE; CALL_RETARGET fires for any equal-count add
and delete; SIGNATURE compares squashed text.

## Claims that did not survive

| claim in the first version | what the review showed | now |
|---|---|---|
| a function's next edit resembles its last at 1.70x / 1.96x | half is patch series, same author, same file | about 1.3x on labels, 1.1x on families (`etyp.md`) |
| "at least as strongly" as KWFLUX | different null; family ratio is below KWFLUX | withdrawn |
| the stickiest types "are the same in both repos" | the table omitted labels that outranked its rows | full list with counts; five of the top eight shared |
| a fix "adds a branch"; fixes are "pure" | BRANCH_ADD marginal; purity produced by filtering fixes and not the reference | withdrawn; the reference is filtered the same way |
| extrinsic fixes have a signature (TYPE, PREPROC) | the label is assigned from platform words; platform-named commits edit `#if` regardless | reported with a platform-named reference; PREPROC is lower there |
| latent fixes and CVE fixes, two findings | the same 172 commits | reported once |
| CVE fixes differ from controls in purity | one to nine commits per cell; no direct test | tested directly: nothing marked |
| reported fixes are "slightly more guard-shaped" | direct test 1.05 [0.96, 1.16] | withdrawn |
| edit type moves the one-year fix rate; LOGIC predicts nothing, STRUCTURE does | sweeps; COMMENT shows the same association; a negative-control outcome moves too | "small and not specific to edit type" |
| the type vector beats size by two or three AUC points | margin came from cosmetic commits in the negatives | no detectable gain over size |
| the extrinsic model is "a usable cross-check" on the label | it recovers the subject rule through its code correlate | withdrawn |
| REL_VAR is "what a missing bounds check looks like" | not marked on new guards in curl | the lift is kept, the mechanism is withdrawn |
| ECOND's taxonomy was fixed before any outcome; its stop rule was set before the join | both first appear in the same commit as the results | withdrawn as unprovable |
| the draft registration | no alpha, no sidedness, a negative control that passes when underpowered, a predictor that depends on the priority order | withdrawn (`etyp_hypotheses.md`) |

## What held up

- **A fix is in-place logic, not rewiring or deletion.** LOGIC and OPERATOR up; WIRING, CALL_RETARGET,
  SIGNATURE, CALL_DEL and STMT_DEL down. Stable in both repos under a symmetric message filter, with
  v3c-dropped commits folded back, without ERROR-node edits, with log2 size bins, with an era control, and
  again after the test code was removed.
- **Fixes add relational comparisons between two variables** (1.80 and 1.67), not a for-loop artefact.
- **The type vector does not recognise fixes, and regression fixes have no type signature.**
- The walk reproduces row for row; the fix-versus-reference masks, the bootstrap units, the AUC and the
  logistic fit were checked and are correct.
- No sign that openssl or nDPI were walked or scored.

## What this says about process

Every withdrawn claim above was written, with numbers and intervals, in documents that were honestly
labelled exploratory. The label did not stop the claims from being wrong. Three habits produced them:

1. **Reading a mark in one repo as a finding.** With hundreds of uncorrected cells, single-repo marks are
   expected by chance.
2. **Comparing two intervals by eye** instead of testing the contrast.
3. **Trusting a docstring.** "Sweeps are dropped everywhere" was false for one function, and nothing tested
   it.

The notes now interpret only cells marked in both repos, test contrasts directly, and carry tests for the
defects found.
