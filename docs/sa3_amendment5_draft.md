# SA3 — Amendment 5, DRAFT (Revision 2; not in force, not in the registration)

**Status: draft, 2026-11-14, revised after one independent review.** Step 2 of
`docs/process/research_codebase_spec.md`. It becomes an amendment only when it has had its second independent
review (checklist item 15) and the owner accepts it. Nothing here has been applied to
`docs/sa3_registration.md` or to any SA3 tool. SA3 is unscored.

**What Revision 2 changed.** The first draft was reviewed by an independent session
(`docs/process/reviews/sa3_amendment5_review_claude.md`: 3 blockers, 7 major, 9 minor). The author reproduced
the blockers before changing anything (section 9). The main corrections:

- the first draft named the wrong reference commit and so understated what has already changed;
- it moved two reading-rule fixes into the confirmatory run that Amendment 4 had frozen by name;
- it proposed matching public counts as the proof that new code gives the old numbers, which proves nothing
  about the scorer;
- its sentence defining a fix reference was not what the code does, and the review found a new fault there.

## 1. What has already changed since the estimates were seen — a disclosure

Amendment 4 says the confirmatory tests keep the label "pre-registered; point estimates partly seen before
scoring" only if the frozen items run "exactly as at `edc5c53`". **That is not true of the code today, and was
not true from the moment Amendment 4 was committed.** Its own commit, `8fb7fe0`, made after the leak, changed
the scorer (222 lines) and the outcome builder (8 lines). Amendment 4 listed those changes under "scorer faults
fixed — none depends on an outcome". One of them matters to the confirmatory tests:

- the "instrument silent" rule was narrowed so that count predictors are exempt from the "fewer than 20
  distinct values" clause. Two of the three confirmatory primaries are counts. Defect log 46 records that this
  un-silenced three count measures in 14 repo cells. **How many of the 14 are confirmatory cells is not yet
  counted.** It is counted from the scans alone, with no outcome, and published before scoring.
- the same change alters how many random draws earlier cells consume, so the shared stream of `8fb7fe0` is not
  the stream of `edc5c53`.

So the reference for "as frozen" is **the file contents at `8fb7fe0`** for `tools/sa3_score.py` and
`tools/sa3_outcomes.py`, and at `edc5c53` for `tools/sa3_stats.py` and `tools/mod1_lift.py` (unchanged since).
This amendment says so in place of Amendment 4's shorter wording, and lists every difference between the two
commits in a deviation table (section 8).

## 2. The rule this amendment applies

**The confirmatory run is the reference code, run once, unchanged.** Not a rewrite, not the stored tables.
Every correction and every new rule runs **beside** it and is printed beside it. Where a correction changes a
reading, both readings are printed, and a hypothesis whose reading differs between the two is not called
confirmatory.

## 3. The confirmatory run

| item | what it does |
|---|---|
| Code | the reference contents of section 1, sealed by hash |
| Universe | the registered rule as coded, including GitHub's vendored list |
| Completeness | the registered measure (unit files in the scan over unit files in the archive, both under the registered unit rule) decides exclusion, as now |
| Matching later commits to files | equal path |
| Missing predictor values | as the code reads them |
| Snapshot and window | the scanned snapshot; the window from the code's own cut |
| Fix references | exactly as coded (section 5) |
| Tainted merges | counted when they inherit; owner ruling of 2026-11-14 |
| Keyword rules | two, as coded; owner ruling |
| List of scored repos | the frozen list |
| Random draws | seed 2982, the shared stream and the repo order of the reference code |
| Nesting inputs | the existing nesting files, sealed as they are |
| Holm step and "not robust" | as coded in the reference (see section 4) |

## 4. Corrections, each printed beside the confirmatory reading

| defect | the correction | where it shows |
|---|---|---|
| 42 | Holm step-down: a primary whose interval lies wholly below zero does not stop the step-down for the others | **both readings printed** for B, C and D. On the reviewer's truth table of 729 input combinations (not re-run by the author) the corrected rule reads "supported" more often than the reference in 51. Where the two differ for a hypothesis, that hypothesis is reported as "reading depends on a rule corrected after the estimates were partly seen" |
| 43 | "Not robust to the statistic" whenever the two statistics differ | both readings printed, same treatment |
| 47 | "Supported" is printed only for the three confirmatory tests | output wording; the numbers are unchanged |
| 48 | The all-reverts comparison uses one named repo set on both sides | a secondary reading, printed as coded and as corrected |

The registration gives the Holm levels and no stopping rule; the consolidated text's "stopping at the first
that fails" was written from the code. So this is a correction of a rule the registration left open, made after
the estimates were seen, and it is presented as that.

## 5. What the code counts as a fix reference, stated exactly

This does not change what runs. It replaces a loose sentence in the consolidated text. Where it differs from
what a reader would expect, that is said.

- After one of the words fix, fixes, fixed, resolve, resolves, resolved: `#N`, `GH-N`, `bug N`, `bpo-N`,
  `PR N` (the BSD problem report), or a tracker key.
- **A tracker key is matched without regard to case**: a letter, then 1 to 15 letters, digits or underscores,
  a hyphen, digits. So "Fix UTF-8 decoding", "fix x86-64 build" and "Fixed sha-1 fallback" are fix references.
  The registration writes the key in capitals. **This is a fault (defect log 61), found by the review of this
  draft.** Under section 2 it stays in the confirmatory run; its size is counted and a sensitivity removes it.
- Any `Fixes:`, `Bug:` or `Reported-by:` trailer, whatever follows the colon.
- A `Fixes:` line naming a hash; the GnuPG bug trailer; a CVE id.
- A revert whose target existed at the cut. A revert of later code does not qualify as a revert; if its message
  quotes a fix reference from its target's subject, it qualifies through that.
- A tainted merge is kept out of the keyword outcome and the control pool, and is a positive if it inherits a
  fix reference and its first-parent diff shares a file with the linking commit.
- The window starts at the later of the cut and the scanned snapshot and ends at the cut plus 730 days.

The registration's body already says tracker patterns follow a fix verb; only its outcome table and the
consolidated text left that out.

## 6. Sensitivities — the list is closed by this amendment

Every one is run and reported whatever it shows. None uses the words of the confirmatory tests or a Holm
level. Any added later is dated and labelled as later. Each is first run on a control repository with a known
answer.

| name | definition | from |
|---|---|---|
| `PU_reachable_universe` | remove files that are in the universe **and** that the history walk's own unit rule excludes (the walk applies the unit rule without the snapshot's `.gitattributes`). Defined by rule, never by "has no touch" | owner ruling of 2026-11-14 |
| `PU_unreachable_made_reachable` | the other repair: rebuild the touches with the snapshot's attributes so those files can be positive | the review; the registered universe includes them |
| `PU_generic_dirs_restored` | files excluded only by one of these GitHub patterns are ranked again: `(^|/)cache/`, `(^|/)dist/`, `(^|/)[Ee]xtern(als?)?/`, `(^|/)env/`. The list is fixed here, before any per-repo count is seen | defect 55 |
| `PU_tracker_keys_case_sensitive` | a tracker key must be in capitals, as the registration writes it | defect 61 |
| `PU_named_streams` | one random stream per repo and purpose, seeded from 2982 | defect 45 |
| `PU_late_revert_ticket_dropped` | a late revert that quotes a ticket not counted | harness report |
| `PU_new_completeness` | completeness measured against the snapshot's tree with stored reasons; repos under 90% dropped | defect 56 |
| `PU_nesting_floor` | a repo whose nesting file covers under 95% of its files has its nesting cells dropped | defect 58 |
| `PU_window_assertion` | a repo whose window ends before it starts, or with no usable commits, dropped | defect 59 |
| S8 | rename following | registered, not yet run |

Dropped from the first draft: counting bare tracker keys. A bare key matches "UTF-8" and "SHA-1" in every repo
and would mostly add noise.

## 7. Counts published before scoring — none reads an outcome against a predictor

1. Of defect 46's 14 cells, how many are confirmatory, and which repos.
2. Per repo: window start, window end, usable commits (defect 59). **To be made.** If a scored repo fails, it
   stays in the confirmatory run and its removal is `PU_window_assertion`.
3. Per repo: completeness on the registered measure and on the new one.
4. Per repo: files excluded by each pattern of `PU_generic_dirs_restored`; universe files the history cannot
   touch; qualifying commits that qualify only through a lower-case tracker key.
5. Per repo: the share of files with a nesting value.

## 8. What a reader is told with the result

- **The label:** "pre-registered design; point estimates partly seen before scoring; scoring code corrected
  afterwards in N listed places; readings given as coded and as corrected."
- **A deviation table:** every difference between the registration and the reference code, and between the
  reference code and each correction: what, when, who decided it, whether it can move a confirmatory number.
- **What was seen and when** (Amendment 4), unchanged.
- **How much of a planted effect the pipeline recovers on generated repositories** (`docs/process/harness_report.md`,
  20 seeds per case): with an effect planted on true fixes of +0.138, the labels the written rule gives carry
  +0.077 and the Python pipeline reports +0.075; in generated C the pipeline reports +0.062 against +0.081.
  With no effect planted every predictor reads zero. **These are properties of generated repositories.** The
  share lost in the label rule depends on the mix of commit conventions the generator was given; it has not
  been measured on real repositories and is not a correction factor.

## 9. How the run is shown to be the frozen run

Matching public counts would not show it: counts say nothing about which files are positive, or about the
scorer. Three layers, none of which shows an outcome to a session:

1. **Inputs.** The label and universe tables rebuilt from the stored tables are hashed and compared with the
   hashes of what the reference code reads. Printed as equal or not equal, per repo.
2. **A known output.** The existing placebo output is regenerated by the reference code and compared byte for
   byte.
3. **The run itself.** The sealed reference scorer is run once, by the owner, as the confirmatory run. The
   stored-tables scorer is run beside it and a per-cell map of equal / not equal is printed. Any "not equal"
   is investigated on control repositories, never on the real cells.

The check is itself tested first: five one-line faults are seeded into copies of the code on control
repositories, and all three layers must report each. **None of this is built yet.**

## 10. Review record and owner decisions

| | |
|---|---|
| Owner, 2026-11-14 | tainted merges follow the code; two keyword rules stay; unreachable-file removal runs beside the frozen run; the confirmatory run keeps the registered random streams |
| Review 1 | Claude Fable 5.2, independent session: 3 blockers, 7 major, 9 minor |
| Reproduced by the author | the scorer and outcome builder changed in `8fb7fe0` (`git diff --stat edc5c53`: 222 and 8 lines); Amendment 4's "Frozen" paragraph names the Holm family and the reading words; the tracker-key pattern matches "Fix UTF-8 decoding", "fix x86-64 build", "Fixed sha-1 fallback" and "Resolve http-2 stream reset" |
| Adopted on the reviewer's citations | the nesting floor shifts the shared stream; the registered text defines the completeness measure; the count for defect 59 was claimed and not made; trailers with any content qualify; sensitivities defined by rule and closed; the label wording |
| Not adopted | — |
| Still owed | the second independent review (a different model, on the pull request); the count of section 7 item 1 |

## Open, for the owner

1. **The label.** Section 8's wording is longer and less flattering than Amendment 4's. The reviewer's view,
   which the author shares: "pre-registered" is still true of the hypotheses, the statistic and the family,
   and no longer true, unqualified, of the scoring code.
2. **The confirmatory run is the old scorer, run once, as it stands** (section 2). That means SA3's
   confirmatory numbers come from code with known faults, each of them shown beside it. The alternative —
   fixing first — makes the whole analysis post-unblinding.
