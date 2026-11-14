# SA3 — Amendment 5, DRAFT (Revision 3; not in force, not in the registration)

**Status: draft, 2026-11-14, revised after two independent reviews.** Step 2 of
`docs/process/research_codebase_spec.md`. It has had the two reviews checklist item 15 requires
(`docs/process/reviews/sa3_amendment5_review_claude.md`, `…_gemini.md`), reconciled here. It becomes an
amendment when the owner accepts this revision. Nothing here has been applied to `docs/sa3_registration.md` or
to any SA3 tool. SA3 is unscored.

**What Revision 3 changed** (the second review: 2 blockers, 9 further gaps; reconciliation in section 10):

- running the old scorer unchanged would also have meant relying on its weak seal; an **external seal** now
  surrounds the run (section 2);
- the disclosure covers **all** cells whose silence changed, because any of them shifts the shared random
  stream for every later repo (section 1);
- what counts as a fix reference is now given by the code's patterns **verbatim**, not by a paraphrase
  (section 5);
- two sensitivities say what data they need; the closed list includes Amendment 4's; the equality check has a
  tolerance and clean copies.

## 1. What has already changed since the estimates were seen — a disclosure

Amendment 4 says the confirmatory tests keep the label "pre-registered; point estimates partly seen before
scoring" only if the frozen items run "exactly as at `edc5c53`". **That is not true of the code today, and was
not true from the moment Amendment 4 was committed.** Its own commit, `8fb7fe0`, made after the leak, changed
the scorer (222 lines) and the outcome builder (8 lines). Amendment 4 listed those changes under "scorer faults
fixed — none depends on an outcome". Two matter here:

- **The "instrument silent" rule was narrowed** so that count predictors are exempt from the "fewer than 20
  distinct values" clause. Defect log 46 records that this un-silenced three count measures in 14 repo cells.
  Two of the three confirmatory primaries are counts. And the scorer draws from **one** random stream across
  all repos, outcomes and predictors, so **any** un-silenced cell — confirmatory or not, primary outcome or
  keyword — moves the draws of every later repo's matched control, which decides between "supported,
  defect-specific" and "supported, but tracks activity". **All 14 cells are published before scoring**
  (repo, outcome, measure), from the scans alone.
- **The window start** became the later of the cut and the scanned snapshot. Amendment 4 reported the effect on
  the earlier eight repos. That it moves **none of the 15 drawn repos** is verified before scoring from the
  scans and the frame, not assumed.

So the reference for "as frozen" is **the file contents at `8fb7fe0`** for `tools/sa3_score.py` and
`tools/sa3_outcomes.py`, and at `edc5c53` for `tools/sa3_stats.py` and `tools/mod1_lift.py`. None of these
files, nor `hist_meta.py`, `laws_units.py`, `laws_history.py` or `hist_fixlabel.py`, has changed since
`8fb7fe0` (checked with `git log 8fb7fe0..HEAD`).

## 2. The rule this amendment applies

**The confirmatory run is the reference code, run once, with its scoring logic unchanged.** Not a rewrite, not
the stored tables. Every correction and every new rule runs **beside** it and is printed beside it. Where a
correction changes a reading, both readings are printed, and a hypothesis whose reading differs between the
two is not called confirmatory.

**The run is sealed from outside.** The reference scorer's own seal covers nine files, omits every data input
and most rule code, and does not notice when git fails (defect log 44, 57). Fixing it would mean editing the
reference. Instead:

1. The run happens in a sandbox of the kind `tools/harness/sandbox.py` builds: the root read-only, **only the
   declared inputs bound in**, read-only, and one new output directory.
2. An external seal lists the SHA-256 of every declared input — every scan, history and harvest database,
   outcome and nesting file, GitHub's two lists; every code file the run loads, including the reference
   scripts and the modules they import; this amendment; the registration — with interpreter and package
   versions. The owner's job recomputes the seal and stops on any difference.
3. The reference scorer's own `lock` is still run, as it is, inside that sandbox.

**Order of operations**, because the reference `lock` hashes the consolidated text and requires a committed
code review: (a) this amendment is accepted and entered in `docs/sa3_registration.md`; (b) the consolidated
text is regenerated from it; (c) the code review document is committed; (d) the counts of section 7 are
published; (e) the checks of section 9 pass on control repositories; (f) the external seal is written;
(g) the owner runs `lock`, then `score`, once.

## 3. The confirmatory run

| item | what it does |
|---|---|
| Code | the reference contents of section 1, inside the external seal |
| Universe | the registered rule as coded, including GitHub's vendored list |
| Completeness | the registered measure decides exclusion, as now |
| Matching later commits to files | equal path |
| Missing predictor values | as the code reads them |
| Snapshot and window | the scanned snapshot; the window from the code's own cut |
| Fix references | exactly as coded (section 5) |
| Tainted merges | counted when they inherit; owner ruling of 2026-11-14 |
| Keyword rules | two, as coded; owner ruling |
| List of scored repos | the frozen list |
| Random draws | seed 2982, the shared stream and the repo order of the reference code |
| Nesting inputs | the existing nesting files, sealed as they are |
| Holm step and "not robust" | as coded in the reference (section 4) |

## 4. Corrections, each printed beside the coded reading — four of them

| defect | the correction | where it shows |
|---|---|---|
| 42 | Holm step-down: a primary whose interval lies wholly below zero does not stop the step-down for the others | both readings printed for B, C and D |
| 43 | "Not robust to the statistic" whenever the two statistics differ | both readings printed |
| 47 | "Supported" is printed only for the three confirmatory tests | output wording; numbers unchanged |
| 48 | The all-reverts comparison uses one named repo set on both sides | printed as coded and as corrected |

**How often 42 matters, computed by the author and equal to the first reviewer's figure.** Give each of the
three tests, in the order the code takes them, one of three readings for the primary statistic and one of
three for the co-reported one: 729 combinations. The coded and corrected rules give a different reading in
135. The corrected rule reads "supported" more often in 51. Every one of them has a contradicted primary
ahead of a supported one; there are five such patterns among the 27 for the primary statistic.

Where the two rules differ for a hypothesis, it is reported as "reading depends on a rule corrected after the
estimates were partly seen". The registration gives the Holm levels and no stopping rule; this is a correction
of a rule the registration left open.

## 5. What the code counts as a fix reference — the patterns govern

The reference file `tools/hist_meta.py` holds these patterns, reproduced verbatim. **Where the prose below and
a pattern differ, the pattern is what runs.**

```
revert_sha     This reverts commit ([0-9a-f]{7,40})                                   (case-insensitive)
issue_fix_sa3  \b(?:fix(?:es|ed)?|resolve[sd]?)\s+(?:#|\bGH-|\bbug\s*#?|\bbpo-|\bPR\s*#?)(\d{1,7})\b
             | \b(?:fix(?:es|ed)?|resolve[sd]?)\s*:?\s+([A-Z][A-Z0-9_]{1,15}-\d{1,7})\b
             | ^GnuPG-bug-id:\s*(\d+)\b
             | ^Fixes:\s*([0-9a-f]{7,40})\b                                 (case-insensitive, multi-line)
cve            \bCVE-\d{4}-\d{4,7}\b                                                  (case-insensitive)
trailer        ^(Co-authored-by|Reported-by|Reviewed-by|Signed-off-by|Tested-by|Closes|Fixes|Bug):\s*(.+)$
                                                                            (case-insensitive, multi-line)
```

In words, with the points a reader would not guess:

- The fix words are exactly fix, fixes, fixed, resolve, resolves, resolved. Not "closes".
- After a fix word and white space: `#N`, `GH-N`, `bug N` or `bug #N`, `bpo-N`, `PR N` or `PR #N` (the BSD
  problem report), N of 1 to 7 digits. No colon is allowed here.
- After a fix word, an optional colon and white space: a tracker key — one letter, then 1 to 15 letters,
  digits or underscores, a hyphen, 1 to 7 digits. **Case is ignored**, so "Fix UTF-8 decoding" and
  "fix x86-64 build" are fix references (defect log 61). It stays in the confirmatory run; a sensitivity
  removes it.
- The patterns above are applied to the subject and body together. **Trailers are read from the body only**,
  not the subject, and need at least one character after the colon. Of the trailers, `Fixes:`, `Bug:` and
  `Reported-by:` count as fix references, whatever follows.
- **Reverts.** A revert qualifies under the primary outcome only if its message has "This reverts commit" and
  a hash of at least 7 characters that resolves to one reachable commit, and that commit existed at the cut.
  For a commit brought in by a merge, "existed at the cut" is judged by the **owning merge's** time. A revert
  that does not resolve, or whose target is later, counts only under the all-reverts outcome — unless its own
  message carries a fix reference or CVE (for example by quoting its target's subject), in which case it
  qualifies through that.
- **Merges.** A merge inherits a fix reference, CVE or qualifying revert from a commit it brings in, never
  from a bot's commit, never a revert of a commit brought in by the same merge, and its positives are its
  first-parent diff ∩ the linking commit's files. A merge bringing in more than 50 commits inherits nothing
  and is tainted. A merge is tainted if any commit it brings in — **a bot's included** — carries a link or fix
  wording. Tainted merges are kept out of the keyword outcome and the control pool; a tainted merge that
  inherits is still a positive.
- The window starts at the later of the cut and the scanned snapshot and ends at the cut plus 730 days.

## 6. Sensitivities — the list is closed by this amendment

**The closed list is Amendment 4's** (S1 to S9 with S5 and S8 as registered, go and django removed, the
earlier eight reported apart, the descriptive sub-pools, `PU_django_circuitpython_removed`,
`PU_mediawiki_freebsd_removed`) **plus the ten below.** Every one is run and reported whatever it shows. None
uses the words of the confirmatory tests or a Holm level. Any added later is dated and labelled as later. Each
is first run on a control repository with a known answer.

| name | definition | needs |
|---|---|---|
| `PU_reachable_universe` | remove files that are in the universe **and** that the history walk's own unit rule excludes. Defined by rule, never by "has no touch" | the `file` table |
| `PU_unreachable_made_reachable` | the other repair: those files stay ranked and can be positive | **a new extraction of touches for those paths from the clone**; the stored history cannot supply them |
| `PU_generic_dirs_restored` | files excluded only by `(^|/)cache/`, `(^|/)dist/`, `(^|/)[Ee]xtern(als?)?/` or `(^|/)env/` are ranked again — **only those the frozen engine scanned**. No new scan is made; restored files without scan rows are counted and left out | the existing scans |
| `PU_tracker_keys_case_sensitive` | a tracker key must be in capitals | the stored links |
| `PU_named_streams` | one random stream per repo and purpose, seeded from 2982 | — |
| `PU_late_revert_ticket_dropped` | a late revert that quotes a ticket not counted | the stored links |
| `PU_new_completeness` | completeness against the snapshot's tree with stored reasons; repos under 90% dropped | the `file` table |
| `PU_nesting_floor` | a repo whose nesting file covers under 95% of its files has its nesting cells dropped | — |
| `PU_window_assertion` | a repo whose window ends before it starts, or with no usable commits, dropped | — |
| S8 | rename following | registered, not yet run |

## 7. Counts published before scoring — none reads an outcome against a predictor

1. **All 14** cells of defect 46, as (repo, outcome, measure), marking which are confirmatory.
2. For each of the 15 drawn repos: that the window start equals the cut.
3. Per repo: window start, window end, usable commits. If a scored repo fails, it stays in the confirmatory
   run and its removal is `PU_window_assertion`.
4. Per repo: completeness on the registered measure and on the new one.
5. Per repo: files excluded by each pattern of `PU_generic_dirs_restored`, **and how many of them have scan
   rows**; universe files the history cannot touch; qualifying commits that qualify only through a lower-case
   tracker key.
6. Per repo: the share of files with a nesting value.

## 8. What a reader is told with the result

- **The label:** "pre-registered design; point estimates partly seen before scoring; scoring code corrected
  afterwards in four listed places; readings given as coded and as corrected."
- **A deviation table:** every difference between the registration and the reference code, and between the
  reference code and each correction: what, when, who decided it, whether it can move a confirmatory number.
- **What was seen and when** (Amendment 4), unchanged.
- **How much of a planted effect the pipeline recovers on generated repositories**
  (`docs/process/harness_report.md`, 20 seeds per case): with an effect of +0.138 on true fixes, the labels the
  written rule gives carry +0.077 and the Python pipeline reports +0.075; in generated C, +0.062 against
  +0.081. With no effect planted every predictor reads zero. **These are properties of generated
  repositories.** The share lost in the label rule depends on the mix of commit conventions the generator was
  given; it has not been measured on real repositories and is not a correction factor.

## 9. How the run is shown to be the frozen run

Three layers, none of which shows an outcome to a session:

1. **Inputs.** The label and universe tables rebuilt from the stored tables are hashed and compared with the
   hashes of what the reference code reads. Printed as equal or not equal, per repo.
2. **A known output.** The existing placebo output is regenerated by the reference code **in the sandbox, into
   the output directory** (the reference would otherwise write over the committed file). Compared byte for byte
   when the interpreter, numpy and its linear-algebra library are the versions recorded with the original; if
   any differs, compared number by number within 1e-9, and the versions and the largest difference reported.
3. **The run itself.** The sealed reference scorer is the confirmatory run. The stored-tables scorer runs
   beside it and a per-cell map is printed: **exactly equal** for counts, readings and repo sets; **within
   1e-12** for real numbers. Any "not equal" is investigated on control repositories, never on the real cells.
   This layer waits for the stored tables to hold derived predictors with their missing-value rules.

**The check is itself tested first**, blind: five copies of the code each carrying one seeded one-line fault
and five clean copies are run on control repositories; all three layers must flag each faulty copy and none
of the clean ones. **None of this is built yet.**

## 10. Review record, reconciliation and owner decisions

| point | raised by | disposition |
|---|---|---|
| Wrong reference commit; "frozen" already not true | Claude B1 | adopted (section 1); reproduced by the author |
| Holm and "not robust" mis-sorted | Claude B2 | adopted (section 4); truth table re-run by the author: 135 / 51 / 5 |
| Public counts prove nothing about the scorer | Claude B3 | adopted (section 9) |
| Nesting floor, completeness, window assertion can touch the scored set | Claude M1–M3 | adopted: each is a sensitivity |
| The fix-reference sentence was not what the code does; case-insensitive keys | Claude M4 | adopted; defect log 61 |
| Sensitivities loosely defined; list not closed | Claude M5 | adopted (section 6) |
| The label | Claude M7 | adopted; accepted by the owner |
| **The seal: "unchanged" kept the reference's weak seal** | Gemini 1 | adopted: external seal and order of operations (section 2) |
| Any un-silenced cell shifts the shared stream; verify the window on the drawn repos | Gemini 2 | adopted (sections 1, 7); the shared stream confirmed in the code |
| Pattern details: optional `#`, the colon, digit bounds | Gemini 3 | adopted: patterns verbatim (section 5) |
| Trailers are read from the body only and need a value | Gemini 4 | adopted; confirmed at `hist_meta.py:81` |
| Reverts: unresolved targets, the owning merge's time, the same-merge rule | Gemini 5 | adopted; confirmed at `sa3_outcomes.py:199-217` |
| Over-cap merges; a bot's commit taints | Gemini 6 | adopted |
| Restored files may have no scan rows | Gemini 7 | adopted: only scanned files are restored; counts published |
| The second repair needs new touches from the clone | Gemini 8 | adopted |
| The closed list must include Amendment 4's | Gemini 9 | adopted |
| Layer 2 writes over a committed file; equality needs a tolerance; clean copies | Gemini 10 | adopted (section 9) |
| Verify the truth table; pin N | Gemini 11 | done: N = 4 |
| Not adopted | — | none |

**Owner, 2026-11-14:** tainted merges follow the code; two keyword rules stay; unreachable-file removal runs
beside the frozen run; the confirmatory run keeps the registered random streams; the confirmatory run is the
reference scorer run once with every correction beside it; the label of section 8.

**What remains before this is in force:** the owner's acceptance of this revision. No question is open.
