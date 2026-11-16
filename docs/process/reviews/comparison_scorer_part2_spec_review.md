# Comparison scorer, part 2 — review of the specification

**Reviewer:** an independent session (Claude Fable 5.2), 2026-11-15. **Reviewed:**
`docs/process/comparison_scorer_part2_spec.md` at `885bc08`, against Amendment 5 and its erratum, the
consolidated text, `tools/sa3_score.py`, `tools/sa3_outcomes.py`, `tools/hist_meta.py`, `tools/laws_units.py`,
`tools/laws_history.py`, `tools/compare/`, `tools/owner/tracker_keys.py`, `docs/sa3_prescoring_counts.md` and
defect-log entries 42, 43, 45, 47, 48, 55, 61. No SA3 tool, job or harness was run. No outcome, placebo or
marginals number was read. Experiments are synthetic and are in
`/home/joe/.claude/jobs/24bf9d40/tmp/part2_review/` (`enum.py`, `enum2.py`, `streams.py`, `misc.py`,
`order.py`, `bands.py`).

## Verdict

**Sound to build after changes. Not sound as written.** The plan is right in outline: a pure reading
function, streams keyed by use, and variants made by changing inputs and never sealed code. Three things
stop a build today. (1) The corrected reading rule of section 2.1 is not the rule whose frequency Amendment 5
published: it differs from the coded rule in 587 of the 729 combinations, not 135, and it marks two of three
hypotheses "reading depends on a corrected rule" in the plainest null result. (2) Section 2.4 contradicts
section 2.1, so its test cannot pass. (3) Section 2.1 makes three choices about confirmatory words that no
amendment made, one of them a new reading word, after the estimates were partly seen. These need an owner
ruling and a dated note, not a builder. Beyond section 2: the variants are run on the shared random stream and
on rebuilt outcome files, so a variant's difference from the frozen run is **not** "that one change and
nothing else"; two sensitivities are not what the spec says they are; and several outputs are loose enough
that two builders would write different code.

Findings: **3 blockers, 10 major, 9 minor.**

## Coded against corrected: my enumeration

I wrote the coded rule from `tools/sa3_score.py:424-444` and the rule of section 2.1 as two functions
(`enum.py`), taking the tests in Holm order. Results (run on synthetic inputs):

| input space | combinations | coded ≠ section 2.1 | section 2.1 reads "supported" more often | no rule / two rules |
|---|---|---|---|---|
| 3 primary × 3 residualised states per test, control above, gate passed (Amendment 5's space) | 729 | **587** (650 if the two Holm sentences count as different words) | 51 | 0 / 0 |
| the same space, **defect 42 only** (a "below" does not stop; all else as coded) | 729 | **135** | **51** | — |
| 3 × 3 × 3 control states, gate passed | 19,683 | 15,849 | 1,377 | 0 / 0 |
| 4 × 4 × 4 states per test, gate passed | 262,144 | 242,112 | 6,912 | 0 / 0 |
| 4 × 4 × 4, gate failed | 262,144 | 0 | 0 | 0 / 0 |

- **Amendment 5's figures are reproduced exactly — 729, 135, 51, five primary patterns — by defect 42 alone.**
  They are the frequency of the Holm correction and nothing else. Defect 43's frequency was never published.
- Section 2.1 is exhaustive and its bullets do not overlap: every input gets exactly one reading.
- Where the 587 comes from, on the 729 space: 42 alone 135; adding section 2.1's "contradicted, not robust"
  299; adding the relabelling of every test after a stop 587. On the four-state space, keeping "not fitted"
  as "not fitted", keeping the coded words after a stop and keeping plain "contradicted" brings 242,112 down to
  24,576.
- It never reads "supported" less often than the code. That part is as Amendment 5 says.

## Blockers

**B1. Section 2.1 is not the correction Amendment 5 describes, and it over-flags.** *Run on synthetic data.*
Spec lines 31-43 against `sa3_score.py:432-444` and Amendment 5 section 4 (`docs/sa3_registration.md:626-643`).
Section 2.1 changes four things the amendment does not list:
- A test after a stop that reads "across" becomes "not detected (Holm: …)". The code prints "not detected".
- A test after a stop that reads "below" becomes "not detected (Holm: …)". The code prints "contradicted"
  (`sa3_score.py:432-434`; the first Amendment 5 review raised this as undefined, B2 last bullet).
- A primary that is "not fitted" becomes "not detected". The code prints "not fitted" (`sa3_score.py:163`).
- The Holm sentence is reworded ("was not significant" for "in the family failed").

Consequence under section 2.2: **with all three tests across zero — the plain null — the coded reading is
"not detected" three times and the section 2.1 reading is "not detected", then the Holm sentence twice.** Two
of three hypotheses would be printed as "reading depends on a rule corrected after the estimates were partly
seen" and "not called confirmatory", though no correction touches them. The label would then say nothing.
**Change:** where neither 42 nor 43 applies, the corrected rule must give the coded words, letter for letter.
State each further change (below after a stop) as its own named correction or drop it. **Test:** the
enumeration above must return 135 / 51 / 5 on the 729 space for 42 alone; the count for 42 and 43 together is
published in the spec before either reading file is written; and the all-across input must compare "same".

**B2. Section 2.4 contradicts section 2.1; its test cannot pass.** *Run on synthetic data.* Spec lines 80-81.
On the inputs section 2.4 calls "the correction does not apply" (no "below" ahead of an "above"; primary and
residualised agree), section 2.1 and the code give different words in 2,880 of 3,456 four-state inputs, and
in 11 of 20 three-state inputs — for example primary readings across, below, below: code "not detected,
contradicted, contradicted"; section 2.1 "not detected" and the Holm sentence twice. The cause is B1.
**Change:** fix 2.1 first; then define "does not apply" as a predicate in the spec and assert equality on its
complement. **Test:** the same enumeration, which must find zero unequal inputs.

**B3. Three choices about confirmatory words are made here, after the estimates were seen, with no ruling.**
*Verified in text; counts run on synthetic data.*
- **"Contradicted, not robust to the statistic" is a new reading.** It is in neither the registration
  (`docs/sa3_registration.md:159-165`, `268-269`), nor the consolidated table
  (`docs/sa3_registration_consolidated.md:141-149`), nor Amendment 5. The registered words for a disagreement
  are "not robust to the statistic", with no qualifier.
- **Primary across, residualised above or below.** The registered rule is "if the two give different readings
  … not robust"; Amendment 5 says "whenever the two statistics differ". Read literally that input is "not
  robust". Section 2.1 gives "not detected" and narrows "differ" to "the residualised statistic does not also
  read above" (spec line 39). Both readings are defensible. They give different outputs.
- **Below after a stop** (B1).
Amendment 5 section 4 says the registration "left open" the stopping rule and treats closing it as a
correction. These three are further closures. **Change:** the owner rules on each; the rulings are entered as
a dated note to Amendment 5 with the truth table attached; the spec then cites the note. **Test:** none for a
ruling; the table is tested as in B1.

## Major

**M1. On the shared stream, a variant's difference from the frozen run is not "that one change and nothing
else".** *Verified in code; run on synthetic data.* Spec lines 13-16. The matched control draws
`rng.choice(len(pool), K, replace=False)` with K the number of primary-outcome commits
(`sa3_score.py:300-315`, `scorer.py:89-93`). With one commit fewer the generator's state after the repo
differs (`streams.py`: K = 40 against K = 39). So `PU_tracker_keys_case_sensitive`, which removes one commit in
bun, moves the permutation spread, p-value and matched-control value of **every repo scored after bun**. The
same holds for any variant that changes a file count, a silent cell, a floor or a repo set. This is defect 45
again, inside the tool meant to isolate changes. **Change:** every variant that changes labels or the universe
is scored on the named streams and compared with `PU_named_streams`; the shared-stream figure may be printed
beside it. **Test:** a decoy where the change touches one repo: under named streams every cell of every other
repo is bit-equal; under the shared stream later repos' R cells differ.

**M2. A rebuilt outcome file has its commits in a different order, and the control draws by position.**
*Verified in code; run on synthetic data.* The outcome builder fills its commit lists by iterating a set of
hash strings (`sa3_outcomes.py:226`, `292`, `309`). Python's string hashing changes per process (`order.py`:
three orders under three hash seeds). The scorer turns those lists into positions and draws positions
(`sa3_score.py:120-121`, `300`, `311`; `tools/compare/tables.py:18-21`). So a variant outcome file built today
orders the pool differently from the frozen file, and the control differs in **every** repo, changed or not,
even on named streams. The owner job compared commits "as a set" for this reason. **Change:** for a repo whose
harvest copy lost no row, use the frozen label tables as they are, after asserting the rebuilt file equals
the stored one as parsed JSON; for a changed repo, order commits as in the frozen file, with new ones
appended by hash. **Test:** build the variant on a decoy under two hash seeds; every cell must be identical.

**M3. The variants' output is specified in a way that breaks Amendment 5 section 6.** *Verified in text and
code.* Spec lines 134-136 give each variant "the full set of summaries the reference produces". That set
includes the `tests` block: Holm levels and the confirmatory readings (`scorer.py:246-266`). Amendment 5 says
of sensitivities: "None uses the words of the confirmatory tests or a Holm level." Test 5 (line 151) allows
"supported" inside "section 2's confirmatory readings" without saying whether a variant has any. Also, spec
lines 48-50 say no other summary "anywhere in the comparison scorer's output" prints "supported"; part 1's
output does, and must, because it equals the reference bit for bit. And "every cell equal to part 1's" (line
122) cannot hold once the words are changed. **Change:** a variant prints, per (outcome, predictor, statistic),
the 95% summary with "above zero / below zero / not detected / not fitted", and the difference of mean and
interval ends from the frozen run. No `tests` block, no Holm level, no reading. Equality with part 1 is
checked on the result before the words are mapped. The vocabulary rule applies to part 2's printed report,
not to part 1's result file. **Test:** a decoy with a planted effect: search every variant's printed block for
"supported", "contradicted", "Holm", "0.9833", "0.975"; the search must be shown to fail on an unmapped copy.

**M4. `PU_late_revert_ticket_dropped` as made is not "exactly the definition".** *Verified in code.* Spec line
115 against `sa3_outcomes.py:193-217` and `hist_meta.py:64-67`.
- A commit has a revert link whenever any line of its message starts with `Revert "` (`revert_sub`), with an
  empty value. That value never resolves (`sa3_outcomes.py:195`). So a sha-less revert, a revert whose hash is
  ambiguous or unreachable, and a non-revert commit that quotes a `Revert "…"` line all lose their ticket,
  though none is known to target code after the cut. The spec's reason — "a revert whose target is before the
  cut qualifies through the revert anyway" — holds only when the target resolves.
- "Fix-reference rows" is not defined. The builder reads `issue_fix`, `trailer:fixes`, `trailer:bug` and
  `trailer:reported-by` as fix references and `cve` separately (`sa3_outcomes.py:181-184`). A kernel-style
  revert carries `Fixes: <hash of the commit it reverts>`, stored both as `issue_fix` and as `trailer:fixes`.
  Deleting only `issue_fix` rows leaves it qualifying. Whether a CVE id in a late revert still qualifies is not
  said; Amendment 5 section 5 names "a fix reference or CVE".
- What I confirmed is right: a commit left with only a revert link is still an event (`sa3_outcomes.py:228`),
  so it stays out of the keyword outcome and the control pool; the all-reverts outcome does not change; a
  resolved pre-cut revert keeps its place and its tier; merges inherit the same way. What changes is the
  primary outcome and `HP_fixref` (and `HP_cve` if CVE rows go). The spec's "the exclusive tiers can change"
  is true and incomplete.
**Change:** name the four kinds deleted and rule on CVE; state the definition as built — "a revert that does
not qualify as a revert (late, sha-less or unresolved) does not qualify through a ticket" — or print beside the
variant how many dropped commits are sha-less or unresolved. Either needs a dated line, since it is not the
amendment's wording. **Test:** a decoy with six commits: late resolved revert with a ticket; pre-cut revert
with a ticket; sha-less revert with a ticket; late revert with only a `Fixes:` trailer; late revert with a
CVE; a fix commit whose body quotes a `Revert "…"` line. The expected primary set is written first.

**M5. `PU_generic_dirs_restored`: the spec gives the wrong reason, and "not run" is close to certain.**
*Verified in code; run on synthetic data.*
- The universe **can** be changed with no sealed file edited. `Excluder.why` skips GitHub's vendored list for
  a path that a `.gitattributes` line marks `-linguist-vendored` (`laws_units.py:141-142`). The attribute text
  is data, read from the scan sidecar (`sa3_outcomes.py:64-65`). A copy of the sidecar with one added line per
  restored path un-vendors exactly those paths and leaves test, generated and example rules in force
  (`misc.py`). The builder and the reference loader call the same `universe()` on the same sidecar
  (`sa3_score.py:83`), so they would agree. Limits: paths with spaces or glob characters; a deeper
  `.gitattributes` wins; completeness and the tree-wide threshold move with the universe.
- The labels still cannot be had. The history walk records touches only for paths its own rule accepts, and
  that rule is the vendored list with no attributes (`laws_history.py:118-131`). The stored history holds no
  touch for a file under `cache/`. Amendment 5 saw this for `PU_unreachable_made_reachable` ("a new extraction
  of touches") and missed it here ("needs: the existing scans").
- Ranking the restored files with outcome 0 is not the same thing. It adds files that could never be positive
  by construction — the fault `PU_reachable_universe` exists to remove — and biases the effect by an amount
  that depends on their predictor values.
- The table understates the size: restorable **and scanned** files in the repos scored on the primary outcome
  are go 3, freebsd-src 15, postgres 14, mediawiki 13, django 9, rails 7, moby 4 — 65 files in seven repos
  (`docs/sa3_prescoring_counts.md`, table), not "3".
**Change:** say the true reason. Then the owner chooses, before the run: "not run: the stored history holds no
touches for these paths", with the count 65; or "ranked, never positive", printed with that caveat in the same
line. "Not run" needs a dated line, because Amendment 5 says every sensitivity is run. A new touch extraction
is a new data product and is more than is needed before scoring. **Test:** for "ranked, never positive", a
decoy with scanned files under `cache/` that fix commits touch: the variant's labels for them are 0 and the
change in the effect equals a hand computation from the tables.

**M6. Which floors apply in a variant is not said.** *Verified in code.* The comparison scorer takes "clears
its floor" from the sealed marginals file (`scorer.py:69`, `179`). A variant that removes commits can take an
outcome under its floor in the variant's own outcome file (`sa3_outcomes.py:288-291`). Frozen floors or
variant floors give different cell sets. **Change:** state it; I would keep the frozen scored set and print
any cell whose variant floor fails. **Test:** a decoy outcome one commit above the 20-commit floor.

**M7. The corrected all-reverts comparison is not defined.** *Verified in text and code.* Spec lines 52-54
against `sa3_score.py:477-481`. Not said: what is printed and under which condition; whether the comparison
is with the coded or the corrected confirmatory reading; which words are used, given that "supported" is
barred. And "the drawn repos where both outcomes clear their floor" is not "one repo set on both sides": a
repo can clear both floors and still have one cell under the pair floor (`sa3_score.py:379-381`).
**Change:** the set is the drawn repos where both cells have status ok for that predictor; write the rule as
a small table. **Test:** a decoy where one repo clears both floors and is under the pair floor on one side.

**M8. Part 1 has no hook for a per-cell stream, and rule 7 forbids adding one.** *Verified in code.* The one
generator is made inside `score()` and handed to every permutation (`scorer.py:174`, `199`). The hooks are
`repo_order`, `outcome_order`, `on_silent`, `control_draw`, `finish_cell`. The control can be re-keyed through
`control_draw`; the permutations cannot. A subclass would have to copy the whole loop: a third transcription,
and no longer "part 1 with one named thing changed". **Change:** allow one edit to part 1 — a method
`cell_rng(repo, outcome, predictor, rng)` that returns `rng` — with part 1's tests and both cell maps
re-run. **Test:** those tests still pass and both maps are still all-equal.

**M9. The first named-streams test fails as written.** *Run on synthetic data.* Spec lines 98-99: reversing
the repo order changes "no other cell at all". The study summaries add repo values in loop order; the part 1
build review records this (F4). Reversing 15 synthetic values changed the mean, standard error or p bit-wise
in 1,479 of 2,000 trials (`misc.py`). **Change:** "every per-repo cell is bit-equal; study summaries are equal
within 1e-12". The dropped-predictor test does hold: the control's draws do not depend on the predictor list
(`sa3_score.py:309-315`), and each permutation cell has its own stream. **Test:** as reworded.

**M10. Section 2.3's comparison is not well defined, and the second build is the weaker check.** *Reasoned;
partly run.* The function's interface is not in the spec. The Holm level depends on the order, so "states"
and "order of p-values" are not independent inputs. The spec does not give the p of a "not fitted" summary
(1.0 in the code, `sa3_score.py:425`) or of one with zero spread (also 1.0, while its interval can still read
"above", `sa3_score.py:167-170`). "The expected six words" is not explained. Stated plainly: the reading is
decided by five things — stopped before or not, primary, residualised, control, gate — at most 256 rows, about
a dozen once collapsed, plus the order rule. **A table of those rows, written in the spec and signed by the
owner, with one test that expands it over all inputs, is the better check.** Both builders read the same
words, and the faults I found (B1, B2) are in the words; I found them by enumerating, not by a second
implementation. The second build is cheap and the owner has ruled it in; keep it if wanted, but it cannot
replace the table. **Test:** the function equals the expanded table on all 524,288 state inputs and the 13
orderings of three p-values with ties.

## Minor

1. **S8.** *Verified in text.* "Not run" agrees with Amendment 4 (`docs/sa3_registration.md:518`) and with
   Amendment 5's own table ("registered, not yet run"). It sits badly with the sentence above that table,
   "Every one is run". One dated line settles it. Nothing in Amendment 5's closed list is missing from section
   4 and nothing is added; S5 is not mentioned and should be, as "not run".
2. **Stream key details.** *Run on synthetic data.* `SeedSequence(2982, spawn_key=…)` accepts three or four
   elements, any non-negative integer size, and Python or numpy integers alike. A 64-bit value is split into
   two 32-bit words, so `(r, 7)` equals `(r_low, r_high, 7)`; a key under 2³² takes one word. Harmless here,
   but say "always four elements" and use `(r, 0, p, o)` and `(r, 1, 0, 0)`. Not said: which list the
   outcome's index comes from; which string is "the repo's name" and its encoding. `(r, 0, p, o)` and
   `(r, 0, o, p)` give different draws. `default_rng(2982)` equals the empty key, so no named stream collides
   with the registered one. The test vectors are promised in a `DECISIONS.md` that does not exist yet; put
   three in the spec.
3. **"One stream … across everything" is not exact.** *Verified in code.* The bootstrap interval makes its own
   generator from 2982 on every call (`sa3_stats.py:179-181`); the placebo stage makes one per repo
   (`sa3_score.py:247`). Neither uses the shared stream and neither changes under the variant. Also, Amendment 5
   defines the variant as "one stream per repo and purpose"; the spec keys by predictor and outcome too. That
   is finer than the closed definition and should be said.
4. **The five "equal" variants are scored in full to show they are equal.** *Reasoned.* The counts do imply
   each one (see the table below). Scoring identical inputs five times measures only that the code is
   deterministic. Cheaper and as honest: compute each variant's change set from the tables in the job; if it
   is empty, print "no input changed" with the hash of the derived inputs; score only if it is not empty.
   **Test:** a decoy with an empty set prints equal with matching hashes; one with a non-empty set is scored.
5. **`PU_nesting_floor` and racket.** *Verified in code.* With no nesting file both nesting measures are all
   missing and read "instrument silent" (`sa3_score.py:144-150`, `186-187`); in the control they yield no
   value. So the claim holds if racket is scored at all, which I did not check. "Dropped" must be written as
   the same status, or the cell-equality check fails on a word.
6. **The late-revert count is first seen with the scores.** Amendment 5 section 7 does not require it earlier.
   It could leave the scoring job as an integer per repo before any score is printed. Optional.
7. **Test 4 says "exactly".** *Verified in code.* The builder's output is not byte-stable across runs: commit
   order (M2) and, with more than 20 over-cap merges, which 20 are listed (`sa3_outcomes.py:236`, `313`). Say
   "equal as parsed JSON, the over-cap sample left out".
8. **Edge readings.** *Verified in code.* A control with fewer than three repos reads "supported, but tracks
   activity, not defects" in the code and in section 2.1; that is a statement with no evidence behind it and
   deserves a note in the output. The exploratory test can also read "not fitted"; section 2.1 lists three
   words.
9. **Test 3: who decides which cells should change.** Nobody, yet. The expected changed cells per variant and
   decoy must be written into the test file, by rule (repo, outcome, class), before the variant code exists.
   On the shared stream "exactly the cells it should" includes every R cell of every later repo (M1).

## Leakage and selective emphasis

On real data the variants run inside the owner's job, after the reference score. No session sees them, so
nothing leaks back into a choice. The risk is the reader's: ten blocks of summaries beside one result invite
picking the one that reads best. The spec's guards are the vocabulary rule and "the difference from the frozen
run in each confirmatory cell". That is not enough, and M3 shows the output as specified would carry Holm
levels and confirmatory words. Add: one table in a fixed order, the same rows for every variant, including
the ones that are equal or not run, with the reason; numbers and differences only; no ordering by size; one
sentence fixed in the spec and printed above the table — "none of these replaces the confirmatory reading;
every one is reported whatever it shows". **Test:** the output for a decoy lists all ten names exactly once,
in the spec's order; removing one variant's block makes the test fail.

## Each sensitivity

| sensitivity | verdict |
|---|---|
| `PU_reachable_universe` | Equal: implied by count 6 (no such file in any repo). No need to score (minor 4). |
| `PU_unreachable_made_reachable` | Equal for the same reason. With no such file, no new touch extraction is needed. |
| `PU_generic_dirs_restored` | Not obtainable as "ranked and able to be positive". Reason in the spec is wrong; size understated (65 scanned files, seven scored repos). Owner chooses "not run" or "ranked, never positive" (M5). |
| `PU_tracker_keys_case_sensitive` | Method sound: the owner job's own second build (`tools/owner/tracker_keys.py:44-59`). Needs M1, M2, M6 before its difference means anything beyond bun. |
| `PU_named_streams` | Construction works. Needs a hook in part 1 (M8), a corrected test (M9), the key pinned (minor 2). |
| `PU_late_revert_ticket_dropped` | Not exactly the definition: sha-less and unresolved reverts, quoted `Revert "` lines, trailers, CVE (M4). Also M1, M2, M6. |
| `PU_new_completeness` | Equal: implied by count 4. The six repos are already unscored; mediawiki passes on both measures by 0.0004. |
| `PU_nesting_floor` | Equal: coverage is 100% where a file exists; racket's cells are already silent (minor 5). |
| `PU_window_assertion` | Equal: implied by count 3 (all 46 repos pass). |
| S8 | "Not run" matches Amendment 4. Needs one dated line against "every one is run" (minor 1). |

## Is anything larger than needed before scoring

Yes: full scoring of the five equal variants (minor 4); a second model build where a signed table does more
(M10); and any new touch extraction for the generic directories (M5). Nothing in the spec needs a sealed file
edited. M8 asks for one edit to part 1, which is not sealed.

## What I did not check

- Whether racket, or any named repo, is scored on any outcome: I did not open the marginals file.
- Any real harvest, outcome file, table or clone. The size of M4's cases on SA3's repos is unknown to me.
- How `rng.choice` and `rng.permutation` consume the stream beyond the one synthetic case in `streams.py`.
- Run time of ten variants on real data. I did not time the part 1 scorer.
- The linguist lists themselves; `misc.py` uses a stand-in list of one pattern.
- `tools/compare/DECISIONS.md` and the part 1 spec in full; I read the parts on streams, classes and hooks.
- Whether the scoring job's sandbox can run the outcome builder a second and third time (it needs the clones
  and git); that is the later specification's.
- numpy versions other than 1.26.4.
