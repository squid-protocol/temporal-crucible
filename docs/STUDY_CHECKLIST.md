# Pre-scoring checklist for every study in this repo

Adopted 2026-11-13, after an independent review of MOD-1 found six ways the code measured something other
than what the registration said. Each item below changed a conclusion that day; none is hypothetical. A study
does not get scored until every item is answered in its registration — "not applicable, because …" is an
answer, silence is not.

The worked example throughout is MOD-1: `docs/moderator_registration.md` (Amendments 1–3) and
`docs/mod1_result.md`.

## Before any outcome is read

1. **Rank only what can be positive.** The set of files (or functions) being ranked must be exactly the set
   the outcome can land on. The history records a fix touch only for a *unit* file — the repo's language, not
   test, vendored, doc, example or generated (`laws_units`). Ranking every scanned file hands any predictor
   free credit for telling source from non-source.
   *What it did:* moved two of four "positive" repos to negative and dissolved the 4-and-4 sign split.
   *How:* `hist_replicate.corrected(h, units_only=True, …)`, or `mod1_lift.measure`.

2. **Same label depth for every repo.** If the label has tiers that read extra inputs (commit bodies, issue
   links, CVE lists), confirm those inputs exist for every repo in the study. A missing input must exclude the
   repo, never silently fall back to a thinner label.
   *What it did:* the 38 drawn repos would have been labelled by keyword alone; on ndpi that alone moves the
   lift from +0.119 to −0.030.

3. **Keep merges where the merge is the unit.** When a history is walked first-parent (merge share ≥ 0.30),
   the merge is the labelled commit. Filtering `merge=0` afterwards discards most of the repo — and these
   repos are mostly young, so the loss correlates with age.
   *What it did:* ghostty lost 3,550 of 5,400 commits; prometheus flipped from +0.060 to −0.066.
   *Still weak:* a GitHub merge subject is "Merge pull request …", so keyword tiers see little of it. Declare
   a merge-workflow-removed sensitivity.

4. **Check the scan is complete, from structure alone.** Unit files in the scan ÷ unit files in `git ls-tree`
   at the snapshot must be ≥ 0.90, and zero files fails. Report it per repo.
   *What it did:* six of 38 repos failed (root held half its files, macports-base none). Nobody had checked
   before.

5. **Check the instrument per language.** Report per repo the share of unit files with any inbound call. A
   language the engine has not been validated on is declared as such, with a sensitivity that removes it.

6. **One language rule per repo, by the instrument's own definition.** Call a repo's language from its unit
   files, not raw extension counts (which pick up bundled C in a Zig or Ruby project). C and C++ are harvested
   together, because a bare `.h` cannot be assigned.

7. **Date repos robustly.** Use the 1st-percentile commit time, not the first commit (go is "1972" by a joke
   commit). Record the realised outcome window; a repo whose history ends before the window does is flagged.

8. **Look for tree-wide commits in the label.** If nearly every file is positive (bugzilla: 198 of 198), one
   reformatting or licence-header commit has been labelled a fix. Report the largest fix commit's share of
   positives per repo.

## The test itself

9. **State the direction.** A directional hypothesis is supported only by a CI wholly on the predicted side.
   The other side is "contradicted". Including zero is "**not detected**" — never "no effect", never "X is not
   the moderator".

10. **State the power.** Before scoring, write down the smallest effect the design could see. A null is read
    against that number.

11. **Never confirm on the repos that suggested the idea.** Report a fresh-repos-only run beside any pooled
    one; if they disagree, the result is "not robust".

12. **Per-repo results with intervals, not a pooled mean.** A mean over repos is reported only next to the
    count of repos on each side of zero. Two repos (curl and nDPI) are not a replication; "fails to replicate
    on nDPI" is not evidence that an effect is a curl artefact.

13. **Compare with size the way the claim needs.** `AUC(x) − AUC(LOC)` asks whether x *replaces* size. Whether
    x *adds* to size is a different test (rank within size bands, or a model with both) and must be run
    separately before saying "adds nothing".

14. **Declare the sensitivities and the reading rule in advance.** Which runs gate the verdict, which are
    only reported, and what a disagreement is called.

## Process

15. **Independent review before scoring.** A reviewer with read-only access, forbidden to compute any outcome
    for the study's repos, checks the *code* against the registration and returns blockers. Blockers become a
    dated amendment before the scorer runs. Its claims are spot-checked before being acted on.

16. **Amend in the open.** Every change after registration is a dated amendment stating what was known when
    it was written (how many repos prepared, how many scored). The old tool is kept as the record of the old
    rule; the old numbers are shown beside the new ones.

17. **Every exclusion has its own reason and is listed.** Unprepared, scan incomplete, engine does not resolve
    calls, no label inputs, under the floor, nothing to rank, failed — never one bucket.

18. **Corrections are opt-in switches on shared tools**, so earlier registered runs stay reproducible and can
    be shown side by side with the corrected ones.

## Studies checked against this list

See `docs/hr_units.md` for HR-1/2/3 re-run under items 1 and 3. Label-free studies (keyword counts, order,
nesting) are untouched by items 1–3 and 8 but remain single-repo (item 12).
