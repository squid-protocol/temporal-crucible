# Review of the SA3 Amendment 5 draft (independent, Claude)

**2026-11-14.** Reviewed: `docs/sa3_amendment5_draft.md` at `3f0b7f6`, against `docs/sa3_registration.md`
(Amendments 1–4), the consolidated text, defect log 42–60, the harness report, `research_codebase_spec.md`
sections 3–6, and the code at `edc5c53` and at HEAD. Read-only. No SA3 tool was run. No study data, outcome
file or estimate was opened. Synthetic checks are in
`/home/joe/.claude/jobs/24bf9d40/tmp/amend_review/synthetic_checks.py` (made-up strings and numbers only).

Each finding is marked: **[code]** verified in code · **[text]** verified in the registration text ·
**[reasoned]** reasoned, not run · **[synthetic]** run on synthetic data.

## Verdict

**Ready after changes. Not ready to adopt as written.** The draft's main decision is right: the frozen run
keeps the registered universe and streams, and the owner's unreachable-file ruling runs beside it. But three
things stop adoption. First, "frozen as at `edc5c53`" is not true of the code today, and the draft does not
say so: Amendment 4's own commit changed the scorer in ways that can change which repos enter a confirmatory
mean and that shift the random stream the draft says it keeps. Second, the Holm and "not robust" fixes are
filed as changes that cannot matter; they change confirmatory readings, they touch items Amendment 4 froze by
name, and the Holm one can produce a "supported" the frozen code would not. Third, the proof that the moved
code gives the frozen code's numbers (matching public counts) is too weak to carry the word "frozen". All
three have cheap fixes, given below with a test for each.

Findings: **3 blockers, 7 major, 9 minor.**

---

## Blockers

### B1. "Frozen as at `edc5c53`" does not hold today, and the draft does not name the code it freezes — [code]

`git diff edc5c53 -- tools/` shows two frozen files changed, both in `8fb7fe0` (the Amendment 4 commit, made
after the leak at `5ffa330`): `tools/sa3_score.py` (222 lines) and `tools/sa3_outcomes.py` (8 lines).
`sa3_stats.py` and `mod1_lift.py` are unchanged. Amendment 4 lists these changes under "Scorer faults fixed"
and in the same breath says the frozen items run "exactly as it stood at commit `edc5c53`". Both cannot be
true. The draft inherits the sentence and adds a row that depends on it ("seed 2982, the streams and the repo
order of `edc5c53`"). What changed that can move a confirmatory number or reading:

1. **The "instrument silent" rule** (`sa3_score.py:183-190`). At `edc5c53` any predictor with fewer than 20
   distinct values was silent. That was also the registered text (Amendment 1 rule 9, registration lines
   359-360). At HEAD counts are exempt. Two of the three confirmatory primaries are counts
   (`struct_branch`, `amplified_cascading_flux`; `PREDICTORS`, lines 56 and 64). Defect 46 says the change
   "un-silenced three count measures in 14 repo cells". If any of those 14 is a confirmatory primary on HP in
   a drawn repo, the confirmatory mean has a repo in it that the frozen code would have left out. The draft
   files defect 46 as "disclosure" and does not say which measures or cells.
2. **The random stream.** `stage_score` uses one stream (`sa3_score.py:361`). Every scored cell draws 200
   block shuffles from it (line 385) before the matched control draws from it (line 406). Un-silencing a cell
   therefore moves every later draw: the matched control (frozen by name in Amendment 4: "the matched control
   and its 200 draws, the seeds"), `perm_p` (side counts) and `null_sd` (random-effects mean). **[synthetic]**
   one extra cell changes the first control draw. So the stream of HEAD is not the stream of `edc5c53`, and
   the draft's section 1 row "Random draws" is false for whichever of the two the run does not use.
3. **The control's handling of missing values** (`sa3_score.py:305-329`). At `edc5c53` it filled with zero;
   now it drops the rows. This moves the specificity number, which decides "supported, defect-specific".
4. **The window start** (`sa3_outcomes.py:162-169`). Now `max(cut, snapshot time)`. See minor finding m4 for
   the drawn repos.

**Change needed.** The amendment names one reference: the blob hashes of the four frozen files at `8fb7fe0`
("`edc5c53` plus the five fixes Amendment 4 lists"). It says plainly that Amendment 4's phrase was inexact. It
states, for the 14 un-silenced cells, how many are (confirmatory primary, HP, drawn repo). If that number is
not zero, the paper reports the confirmatory means under both silent rules.
**How to test / cost.** The cell count needs no label: it is the number of distinct values of a predictor per
repo, plus the existing scored-cell table (defect 46's own diff). Minutes. The stream claim is tested by step
4's exit test, which must name `8fb7fe0`, not `edc5c53`.

### B2. The Holm fix (42) and the "not robust" fix (43) are mis-sorted and mis-described — [code] [text] [synthetic]

- **Amendment 4 froze both by name**: "the 'must agree' rule … the Holm family (B, C, D) and its levels, the
  reading words" (registration lines 474-476). They are not in Amendment 4's "Scorer faults fixed" table. The
  review that found them (R4) came after Amendment 4. The Holm code is unchanged since `edc5c53`
  (`sa3_score.py:424-444` is not in the diff). So these two rows change frozen items after the leak.
- **The draft's sorting rule is wider than Amendment 4's.** Amendment 4: "Anything changed after `5ffa330`
  that could move a result is a post-unblinding sensitivity". It has no exception for "makes the code do what
  the text says". The draft adds that exception in its own rule paragraph and then applies it. That is an
  amendment of Amendment 4, not an application of it. It may be a fair one. It must be said.
- **42 is not "as the registration says".** The registration (lines 159-161) gives the three levels and no
  stopping rule at all. Only the consolidated text says "stopping at the first that fails", and that text
  "adds nothing". The defect log entry itself says "the registration does not say that". So three rules are
  on the table: (a) the literal text, no stopping; (b) the code, stop at the first test that is not
  "supported"; (c) the fix, stop only at an interval that includes zero. (c) is ordinary two-sided Holm, and
  is the best reading of "Holm–Bonferroni". It is still a choice made after the estimates were partly seen.
- **The draft's wording describes the bug.** "Stops only at a test that fails to be supported": a
  contradicted test fails to be supported. Read literally this is rule (b).
- **42 can create a "supported".** **[synthetic]** Over all 729 combinations of three primary and three
  residual readings, rule (c) gives more "supported" readings than the code in 51. Example: primary readings
  contradicted, supported, supported give code: contradicted, not detected, not detected; fix: contradicted,
  supported, supported. The author knows the point estimates to about ±0.01 and so has some idea whether one
  primary is clearly negative. That is exactly the case where this fix matters.
- **43 is a real code-to-text fix** (Amendment 1 rule 1, lines 268-269: "different readings … never as
  supported"; code line 437 tests only when the primary reads "supported"). It can never add a "supported".
  It can turn "contradicted" or "not detected" into "not robust". It still changes a confirmatory reading.
- **The combined rule is not defined.** The draft does not say: whether a contradicted reading after a stop
  is still printed (the code prints it, line 432-434); whether "not robust" is applied before or after the
  step-down; at what level the residual interval is read (the code uses the primary's Holm level, line 430).

**Change needed.** (1) Write the reading rule as a complete table: every combination of (earlier tests,
primary interval, residual interval, control interval, gate) with one word. (2) Say that 42 and 43 change
frozen items and are adopted as corrections under a stated exception. (3) Print two readings per hypothesis in
the result: "as coded at the freeze" and "as corrected". If they agree, nothing more. If they differ, the
hypothesis is reported as "reading depends on a correction made after the estimates were partly seen", and
never as plainly "supported".
**How to test / cost.** Both readings are pure functions of at most nine intervals; computing both costs
nothing. Test: the truth table, cell by cell (this is spec step 5's exit test), plus the old function kept
verbatim and run on the same table so that every differing cell is listed in the amendment before scoring.

### B3. Matching public counts does not show the moved code gives the frozen code's numbers — [reasoned] [code]

Section 6 calls the run "frozen" on the strength of "the stored tables reproduce every public count … or each
difference is explained". Problems:

- Counts (files, commits, largest share) can match while the files differ. They say nothing about the scorer:
  bands, ties, missing values, the silent rule, the stream order.
- "Or each difference is explained" is open-ended. An explained difference in a scored repo means that repo
  is not scored as frozen.
- Spec step 4's exit test says "the frozen numbers are reproduced exactly". There are no frozen numbers to
  reproduce: SA3 is unscored. The only stored numbers are the placebo output.
- "Moved, not rewritten" is a hope until tested. Moving a function behind a table changes iteration order,
  float types and set ordering; `stage_score` depends on dict order (`PREDICTORS`), on repo order, and on
  sorted paths.

**Cheapest sufficient check, in three layers.**

1. *Labels and universe, no label seen.* For each repo and outcome, a job prints only "equal / not equal" for
   the SHA-256 of the sorted positive-file list, of the `HP` commit-to-files map and of the control-pool map,
   old outcome file against new tables; and of the sorted universe paths with LOC. Cost: one small script.
   Rule: any "not equal" in a scored repo stops the run. No explaining.
2. *The placebo output, already on disk.* `docs/sa3_placebo.json` was made by the `8fb7fe0` code on the real
   HP labels with no real predictor scored. The placebo stage restarts its stream per repo
   (`sa3_score.py:247`), so it does not depend on repo order. The moved code must regenerate it **byte for
   byte** (compare hashes; do not read it). This exercises the universe, LOC, bands, pairs, `Design.effect`,
   the HP labels and the reading of all four primaries (the surrogate fit) on all 20 repos. Cost: one placebo
   run, no new exposure.
3. *The score stage.* The honest way to run "the frozen code" is to run it. Make the confirmatory numbers by
   running the sealed old scorer once, inside the new runner's ledger (so its inputs are hashed). The
   stored-tables scorer runs in the same job. The job publishes a per-cell "equal / not equal" map (repo ×
   outcome × predictor × statistic), no values, before either result is opened. If all cells are equal, the
   two are the same run and the label stands. If not, the old code's numbers are the confirmatory ones and
   the differing cells are listed. Cost: one extra scorer run.

**How the check itself is tested.** On control repositories: (i) old and new scorer give byte-identical result
files across the suite, mutations included; (ii) seeded faults — five one-line changes planted in a copy of
the moved code (swap two entries of `PREDICTORS`; reverse the repo order; change the band tie-break from path
to index; fill a missing value with zero; restore the old silent rule) — must each flip the map to "not
equal". A check that passes a seeded fault is not a check. Cost: about the size of spec step 1's seeded-rule
test, which already exists in design. Weakness to state: byte identity needs the same numpy and scipy
versions on both sides; the ledger records them.

---

## Major

### M1. Row 58 (nesting floor) conflicts with the frozen shared stream — [code]

The draft says the nesting scan "is an exploratory secondary; no confirmatory number". Under the shared
stream that is not so. `nest_max` and `nest_mean` sit before `risk_safety_score` and
`amplified_cascading_flux` in `PREDICTORS` (lines 59-64), and each scored nesting cell takes 200 shuffles from
the stream (line 385). If the floor makes a nesting file fail, be rebuilt, or lose files, the stream shifts
for the C and D primaries' `perm_p` and `null_sd` in that repo and for the matched control in that repo and
every later one. The Holm intervals do not move (the means are deterministic). The specificity reading, the
side counts and the random-effects mean can. This is defect 45 again.
**Change.** The frozen run seals the nesting outputs as they are. The 95% floor is computed and reported. A
repo under the floor is handled in a `PU_` run, not by changing the frozen run's inputs.
**Test / cost.** With named streams (already planned), show on a control repository that deleting the nesting
file changes no number outside the nesting cells; with the registered stream, show that it does. One test.

### M2. Row 56 (completeness) is not "a check, no number": the registered text defines the old measure — [text] [code]

The registration defines the floor "under `U.Excluder(attrs, include_tutorials=True)`" (lines 181-184), and
Amendment 3 item 4 sets the denominator to the archive's list. The code does that
(`sa3_outcomes.py:63-89`), and excludes a repo under 90% (line 148). So text and code agree, and the fault
(the check shares the rule it checks) is a fault of the registered design. A new measure "against the
snapshot's tree" is a new rule. If it can exclude a repo, it changes the scored set. freebsd-src (half
imported code) is an obvious candidate to read under 90% on a rule that does not share the vendored list.
**Change.** Say in the row: the registered measure still decides exclusion in the frozen run; the new measure
is reported per repo and excludes nothing; a `PU_` cut may drop repos under it. Define its denominator.
**Test / cost.** A control repository with the `cache/` placement must read 100% on the old measure and
252/306 on the new. Already available from the harness.

### M3. Row 59 says "verified" for a count that has not been made, and has no rule for the bad case — [text] [reasoned]

"None of the scored repos is affected; verified by a public count before scoring." The count is a future
step. The harness report ties this fault to mediawiki, which is on the frozen list. If a scored repo trips
the new assertion, excluding it changes the confirmatory set.
**Change.** "To be verified. If a scored repo trips it, the frozen run keeps the repo and the exclusion runs
as `PU_`." **Test / cost.** The count is outcome-free (window start, window end, usable commits per repo).
Minutes.

### M4. Section 3's first sentence is not what the code does; two builders would write different labels — [code] [text] [synthetic]

"A fix reference is an issue, pull-request or tracker key preceded by a fix word ("fixes", "fixed",
"resolves" …), or a `Fixes:` trailer naming a hash, or the GnuPG bug trailer, or a CVE id." Against
`hist_meta.py:46-52`, `:54`, `:81-82` and `sa3_outcomes.py:180-184`:

- **Trailers are left out.** Any `Fixes:`, `Bug:` or `Reported-by:` trailer, with any content, is a fix
  reference (`sa3_outcomes.py:183`). **[synthetic]** "Reported-by: A User" and "Fixes: typo in comment"
  qualify. The registration says so (HP row; label-depth rule 2). The draft's sentence would drop them.
- **"…" is not a rule.** The fix words are exactly: fix, fixes, fixed, resolve, resolves, resolved. Not
  "closes".
- **"Pull-request" is wrong.** The pattern is `PR 123` after a fix word, registered as the BSD problem report.
- **The tracker key is matched without regard to case.** The pattern is compiled with `re.I`, allows
  underscores, and caps the prefix at 16 characters. The registration writes `[A-Z][A-Z0-9]+-\d+`.
  **[synthetic]** "Fix UTF-8 decoding", "fix x86-64 build", "Fixed sha-1 fallback", "fixes rfc-2822 dates",
  "Fix: python-3 compatibility" each produce a fix reference. **This is a new fault, not in the defect log
  or the harness report.** It moves fix-worded commits from the keyword outcome into HP. Size on SA3's repos
  unknown. Under Amendment 4 it stays in the frozen run. It needs a log entry, a public count, and a
  sensitivity (`PU_tracker_keys_case_sensitive`).
- **The harness's premise is half right.** The registration body already says the tracker patterns are matched
  after "fix verbs" (lines 110-112). Only the HP table row and the consolidated text leave it out. So this
  bullet corrects the consolidated text; it does not change the registered rule. The draft should say that.

**Test / cost.** The control repository gets one commit per form above, with the expected label. The count
on real repos re-applies two regexes to stored commit messages and prints, per repo, how many HP commits
qualify only through a lower-case key. That reads messages, not labels against predictors.

### M5. Three of the new sensitivities are not defined closely enough to run one way — [reasoned] [code]

- `PU_generic_dirs_restored`: "(`cache/`, `dist/`, …)". The list of patterns must be written out now. The
  draft also plans to publish "the five patterns that excluded most" per repo. Picking the patterns after
  seeing those counts is a fork, even though no outcome is involved.
- `PU_bare_tracker_keys`: which key shape, and in which repos. A bare `[A-Z][A-Z0-9]+-\d+` matches UTF-8,
  SHA-1, ISO-8859 and so on in every repo. Without a per-repo tracker prefix this sensitivity mostly adds
  noise positives.
- `PU_reachable_universe`: "can never be positive" must be defined by rule, not by history. The mechanism is
  in the code: the history walk uses `U.Excluder()` with no `.gitattributes` (`laws_history.py:118`) and the
  universe uses `U.Excluder(attrs, include_tutorials=True)` (`sa3_outcomes.py:65`). So the set is "in the
  universe, and excluded by the bare rule". If it were instead built as "files with no touch in the history"
  it would remove true negatives selectively and bias the statistic upward. Say which.
- The text-faithful repair is the other one: the registered universe includes these files, so rebuild the
  touches with the snapshot's attributes and let them be positive. The owner ruled removal. Run both
  (`PU_reachable_universe`, `PU_unreachable_made_reachable`), or say why not.

**Why this matters more than usual.** The author knows the estimates sit at or below what the study can
detect, and every sensitivity added here except the late-revert one was shown by the harness to recover part
of a planted effect. That is selection in a favourable direction, even though it came from control
repositories. The draft's guard ("none can turn a reading into supported") is right. Add: the list is closed
by this amendment; every `PU_` result is reported whatever it shows; none uses the words of the confirmatory
tests or a Holm level; any later addition is dated and labelled as later.
**Test / cost.** Each sensitivity gets a control-repository mutation with a known answer before it is run on
real data. Three already exist (`cache/`, bare Jira, renames).

### M6. The corrections have no "as coded" comparator — [reasoned]

Section 4 lists what happens if a rule is changed in the direction of a fix. It does not list the reverse for
the fixes the draft puts into the confirmatory run. Missing rows: the readings under the Holm and "not robust"
code of the freeze (B2); the confirmatory means under the registered silent rule (B1, if any primary cell is
affected); the all-reverts comparison as coded (m1). Without them a reader cannot see what the
post-unblinding corrections did. Cost: three extra columns in the result; no new run.

### M7. The draft does not give an outside reader what they need to judge the label — [reasoned]

Missing, and needed in the amendment so that the paper can copy it:

- **A deviation table.** One row per change since registration: what, when (commit time), before or after
  the leak at `5ffa330`, who proposed it, who decided it (owner / author / reviewer), and whether it can move
  a confirmatory number, a reading, or the scored set. By my count there are four amendments in force, about
  35 SA3 entries in the defect log (13–33, 42–48, 54–60), and at least nine code changes to frozen files
  after the leak (five in Amendment 4, four here).
- **What was seen, in one place.** The two diagnostic numbers per primary; the bracket published in
  `docs/sa3_build_status.md`; 48 HP commits read at diff level; the placebo output; since then, only control
  repositories. And a statement that nothing else was seen, if that is true.
- **The owner's rulings, listed.** The draft says "four points" in the opening and then describes rulings in
  several places (tainted merges, two keyword rules, unreachable files, streams, the second build). List
  them with date and the question as put.

**My view on the label.** "Pre-registered" is still true of the hypotheses, the primaries, the direction, the
statistic and the family: all were fixed before any data, and git shows it. It is no longer true, without
qualification, of the code that turns data into the confirmatory numbers and words. After five amendments the
honest label is longer: **"Pre-registered design. Point estimates partly seen before scoring. Scoring code
corrected after that in N listed places; readings given as frozen and as corrected."** The paper should lead
with the estimates and their intervals against the stated detectable effect, and give the three-way word
second. If the frozen and corrected readings of a hypothesis differ, that hypothesis is not a confirmatory
result and should not be called one. If they agree — which is likely, given estimates near zero — the label
is honest and the long history costs the study little. The draft should say this conditional out loud.

---

## Minor

- **m1. Row 48 names no set — [code].** "One named repo set on both sides" — which? The code compares
  all-reverts over its own floor-clearing drawn repos with HP over its own (`sa3_score.py:477-481`). That code
  was written in `8fb7fe0`, after the leak. Amendment 1 rule 3 names no set. Choose (the intersection is the
  natural one), say it, and report the as-coded value beside it. Cost: none.
- **m2. Section 3, tainted merges — [code].** "Inherits a fix reference" should read "a fix reference, a CVE
  id or a qualifying revert" (`classify`, lines 206-217; 249-252). On the ruling itself: Amendment 3 item 2
  in context taints merges that were "in neither HP nor KW", so the code agrees with the registration and only
  the consolidated text was wrong. "Code governs" is justified here.
- **m3. Section 3, late reverts — [code] [text].** The sentence matches the code. But Amendment 1 rule 3
  gives its reason: "the snapshot's code had no defect in those cases". Counting such a revert through a
  quoted ticket goes against that reason. The draft keeps it only because it is frozen, and should say so,
  not "the code was already doing something specific". The sentence also omits that reverts with no hash, an
  unresolved hash or an ambiguous 7-character prefix do not qualify (`resolve`, lines 193-198), and that the
  test is against the cut, not the snapshot (line 204).
- **m4. Section 3, the window — [code].** The sentence matches HEAD, not `edc5c53` (where the window started
  at the cut). The code comment says that for drawn repos the snapshot "is the cut itself". The snapshot is
  the scan MOD-1 chose as nearest in time to the cut (`mod1_lift.py:86-96`), which need not be the cut commit.
  If any drawn repo's snapshot is later than its cut, `8fb7fe0` moved a confirmatory window after the leak.
  Defect 44 says a side calculation showed the drawn files unchanged; the amendment should carry that as a
  public per-repo table (snapshot time minus cut, in days). Outcome-free; minutes.
- **m5. Items of spec section 6 not carried over — [text].** The spec says the amendment "lists every item of
  section 6 with its ruling and which of text or code governs". Missing: (g) the universe variant, (h) the
  tree-wide denominator, (l) `.gitattributes` cut at 200,000 characters; and the "governed by" column. Also
  unstated behaviours from the harness report that section 3 skips: the cut is position `int(0.8 n)` of
  non-bot (and, off merge-workflow, non-merge) commits (`mod1_lift.py:54-58`), where the text says "80th
  percentile of commits"; a delete counts toward tree-wide only for files in the universe; the keyword
  outcome is empty by construction in a merge-workflow repo.
- **m6. S5 and S8 — [text].** S8 will now be run with code written after the leak: label it "registered;
  implemented after unblinding". Say whether S5 stays not run.
- **m7. The gate and the changed universes — [code].** Nothing in section 2 changes the recorded
  size-surrogate result, provided the repo list and universe do not move (M2, M3). But the two universe
  sensitivities change the files, and `minus_surrogate` (line 399-400) reads per-repo surrogate means made on
  the frozen universe. Say either that the surrogate is recomputed by the job for each `PU_` universe with
  nobody reading it first, or that those runs do not report `minus_surrogate`. Do not debug a failed gate on
  real data again (defect 26).
- **m8. Row 47 touches strings that decide readings — [code].** Lines 440 and 480 test
  `reading == "supported"` on summaries outside the Holm loop. Changing the vocabulary there can silently
  switch off "defect-specific" or "tracks reverted changes". Covered if the truth table of B2 includes the
  control and all-reverts columns.
- **m9. Section 5, power — [text].** The numbers match the harness report (+0.133 → +0.081 → +0.066; 39% and
  19%). Three gaps. (i) No standard errors: ten seeds, 0.010 to 0.014 each, so the share recovered is
  roughly 0.3 to 0.7, not "half". (ii) Only the label share is flagged as a generator assumption; the 20%
  "pipeline" share depends just as much on how many files the generator put under `cache/` and how many Jira
  keys it wrote bare. (iii) The control repository has since changed exactly those two things (revision 4),
  and the harness itself was changed after the report (commit `76f7ff1`, made while this review was being
  written, adds 20-seed suites on the corrected control repository). So the report's figures are from a
  superseded generator and harness; the draft should quote the newer suites or say which version. The caution itself ("the detectable effect is on the label; a true effect must be larger")
  is fair and already in Amendment 1 rule 7. Keep the sentence, drop the percentages from the power
  statement or mark them "one generator configuration, not real repositories", and do not print a correction
  factor. The real-repo anchor that exists is Amendment 4's audit (35 of 48 clear fixes); cite it for
  precision. `docs/sa3_power.md` is a sealed input: add the caution as a dated addendum, do not edit the
  stated number.

---

## Row by row

### Section 1 — "stays as frozen"

| row | my verdict | note |
|---|---|---|
| Universe | **agree** | Registered by reference to `U.Excluder`; code matches (`sa3_outcomes.py:65`). |
| Matching by equal path | **agree** | `touch` join on path, line 168-170. |
| Missing predictor values | **agree, with B1** | Absent reads 0 for `amplified_cascading_flux` (line 103) and `in_degree` (125-130). The control's handling changed after `edc5c53`. |
| Snapshot and window | **agree for HEAD; not `edc5c53`** | m4. |
| Fix references | **agree to freeze; text in section 3 is wrong** | M4. |
| Tainted merges | **agree** | Code matches Amendment 3 in context; m2. |
| Keyword rules | **agree** | Two rules (`fix_shas` v3c, line 172; `is_fix_message`, line 269). Text is silent; owner ruled. |
| List of scored repos | **agree; not checked** | The list file changed between `edc5c53` and HEAD; I did not open it. M2 and M3 must not alter it. |
| Random draws | **disagree as worded** | B1: the stream of HEAD is not that of `edc5c53`. M1: later rows can shift it. |

### Section 2 — "cannot move a number, or code to text"

| defect | draft says | my verdict | can it move a confirmatory number, reading or the scored set? |
|---|---|---|---|
| 42 | code to text | **disagree** | Reading: yes, and can add "supported". Text is silent on stopping. Frozen by name. B2. |
| 43 | code to text | **agree it is code to text; disagree it is free** | Reading: yes (never adds "supported"). Frozen by name. B2. |
| 47 | output only | **agree, with a test** | Not if the gates at lines 440 and 480 are kept. m8. |
| 48 | secondary; corrected | **partly** | Changes the "tracks reverted changes" word, a registered reading. Set not named. m1. |
| 44, 57 | no number | **agree** | The stronger seal is what makes B3's check possible. |
| 45 | see section 4 | **agree** | Right call: named streams would change the draws. |
| 56 | a check, no number | **disagree as worded** | Scored set: yes if the new measure excludes. Text defines the old one. M2. |
| 58 | no confirmatory number | **disagree under the shared stream** | Specificity, side counts, random-effects mean: yes. M1. |
| 59 | none affected; verified | **not yet verified** | Scored set: yes if a scored repo trips it. M3. |
| 60 | no number | **agree** | Do not rerun the placebo on real data except as B3 layer 2. |
| 46 | disclosure | **disagree: under-stated** | The rule it discloses can change which repos are in a confirmatory mean. B1. |

### Section 4 — sensitivities

| name | my verdict | note |
|---|---|---|
| `PU_reachable_universe` | **right place; define by rule** | M5. Not conditioned on outcomes if defined as "excluded by the bare rule". Add the make-reachable twin. |
| `PU_generic_dirs_restored` | **right place; list the patterns now** | M5. Restored files need the same reachability check. |
| `PU_named_streams` | **agree** | Must give identical numbers under any repo order and predictor set (spec step 4). |
| `PU_bare_tracker_keys` | **right place; under-defined** | M5. Direction: adds positives. |
| `PU_late_revert_ticket_dropped` | **agree** | Direction: removes positives. The only one that follows the registered reason (m3). |
| S8 | **agree; relabel** | m6. |
| *missing* | | As-coded readings for 42/43; registered silent rule; all-reverts as coded (M6). `PU_tracker_keys_case_sensitive` (M4). New completeness cut (M2). Nesting under the floor (M1). Window/usable-commit exclusion if it bites (M3). |
| *should not be a sensitivity* | none | Nothing listed should be an exclusion or a correction in the frozen run. The draft's handling of the owner's unreachable-file ruling is correct under Amendment 4. |

---

## What I did not check

- Any study data, outcome file, scan, history database or estimate. I did not open
  `docs/sa3_placebo.json`, `docs/sa3_outcome_marginals.json` or `.md`, or `docs/sa3_power.md`.
- Whether the frozen list or any drawn repo's marginals changed between `edc5c53` and HEAD (the file's diff
  stat shows 94 changed lines; I did not read them).
- Which measures and cells defect 46's "14 repo cells" are, and whether any is a confirmatory primary.
- Whether any drawn repo's snapshot is later than its cut (m4).
- How many real commits the case-insensitive tracker key matches (M4). The fault is shown on made-up strings
  only.
- The harness's numbers. I compared the draft with the report; I did not rerun the harness, and I did not
  read the newer suites committed at `76f7ff1` during this review.
- `tools/sa3_nesting.py`, `label_cascade.py`, `fixlike_v2.py`, `sa3_scan.py` beyond the lines cited, and the
  `tools/blind/` and `tools/control_repo/` code.
- That R4's review file exists in the tree: `docs/sa3_code_review.md`, which `lock` requires, is not
  committed.
- My own proposals have not been built. B3 layer 3 in particular rests on the old scorer being runnable
  inside the new ledger; that should be tried on a control repository before it is written into the
  amendment.
