# SA3 — Amendment 5, DRAFT for the owner (not in force, not in the registration)

**Status: draft, 2026-11-14.** Step 2 of `docs/process/research_codebase_spec.md`. It becomes an amendment
only when the owner accepts it and it has had its two independent reviews (checklist item 15). Nothing here
has been applied to `docs/sa3_registration.md` or to any SA3 tool. SA3 is still unscored.

## Why an amendment is needed

Amendment 4 says the three confirmatory tests are reported as "pre-registered; point estimates partly seen
before scoring" **only if** everything it lists as frozen runs exactly as at commit `edc5c53`, and that
anything changed afterwards that could move a result is a post-unblinding sensitivity.

Since then SA3's unmodified code has been run on repositories with a known answer
(`docs/process/harness_report.md`). That found six faults (defect log 55–60) and four behaviours the text does
not state, on top of the seven from the pre-scoring code review (42–48) and the text-against-code fault (54).
The owner has also ruled on four points. This amendment says, for each, which side of Amendment 4's line it
falls on.

**The rule this draft applies.** A change is made to the confirmatory run only if it cannot move a
confirmatory number, or if it makes the code do what the registered text already says. Everything else is run
beside it as a named post-unblinding sensitivity (`PU_…`), never in place of it.

## 1. The confirmatory run stays as frozen

| item | what the confirmatory run does | why |
|---|---|---|
| Universe | the registered rule as the code applies it, including GitHub's vendored list | frozen |
| Matching later commits to files | equal path | frozen; rename following is sensitivity S8 |
| Missing predictor values | as the code reads them (the branch-state primary and `in_degree` read absent as 0) | frozen |
| Snapshot and window | the scanned snapshot; the window from the code's own cut | frozen |
| Fix references | a tracker key counts only after a fix word; a revert quoting a ticket counts through it | frozen; the text is made exact (section 3) |
| Tainted merges | counted when they inherit a fix reference | owner ruling of 2026-11-14; the text is corrected |
| Keyword rules | two, as the code has them | owner ruling |
| List of scored repos | the frozen list | registered |
| Random draws | seed 2982, the streams and the repo order of `edc5c53` | frozen: named streams would change the drawn numbers |

## 2. Changes to the confirmatory run that cannot move a number, or that make the code match the text

| defect | change | kind |
|---|---|---|
| 42 | Holm step-down stops only at a test that fails to be supported, as the registration says | code to text |
| 43 | "Not robust to the statistic" whenever the two statistics differ | code to text |
| 47 | One vocabulary for the three confirmatory tests; "supported" is never printed for anything else | output only |
| 48 | The all-reverts comparison uses one named repo set on both sides | a secondary reading; reported as corrected |
| 44, 57 | The seal covers every input (scans, labels, history, all rule code) and refuses when git fails | no number |
| 45 | — | see section 4: reported beside, not in place |
| 56 | Completeness is measured against the snapshot's tree with the exclusion reasons stored, not against the pipeline's own unit rule | a check, no number |
| 58 | The nesting scan fails when it measures under 95% of the files it should | exploratory secondary; no confirmatory number |
| 59 | A window that ends before it starts, or a repo with no usable commits, is an exclusion with a reason on every route | none of the scored repos is affected; verified by a public count before scoring |
| 60 | The placebo stage reports "no repository clears the floor" instead of crashing | no number |
| 46 | The scored-cell table is diffed before and after any rule change and the diff is published | disclosure |

## 3. The text is made exact where the code was already doing something specific

These do not change what runs. They change the consolidated text so that a second builder would write the same
code.

- A fix reference is an issue, pull-request or tracker key **preceded by a fix word** ("fixes", "fixed",
  "resolves" …), or a `Fixes:` trailer naming a hash, or the GnuPG bug trailer, or a CVE id.
- A revert whose target was made after the cut does not qualify as a revert. If its message quotes a fix
  reference from its target's subject, it qualifies through that reference.
- A tainted merge is kept out of the keyword outcome and the control pool. It is a positive if it inherits a
  fix reference and its first-parent diff shares a file with the linking commit.
- The window starts at the later of the cut and the scanned snapshot and ends at the cut plus 730 days.

## 4. Post-unblinding sensitivities added

Each is run beside the confirmatory result and reported with it. None can turn a reading into "supported".

| name | what | from |
|---|---|---|
| `PU_reachable_universe` | files that are ranked but can never be positive (a `.gitattributes` line switches an exclusion off) removed | owner ruling of 2026-11-14; the per-repo count is published first |
| `PU_generic_dirs_restored` | first-party files under directories GitHub's list matches by name alone (`cache/`, `dist/`, …) ranked again | defect 55; the per-repo count is published first |
| `PU_named_streams` | one random stream per repo and purpose, seeded from 2982 | defect 45 |
| `PU_bare_tracker_keys` | a tracker key without a fix word counted | harness report |
| `PU_late_revert_ticket_dropped` | a late revert that quotes a ticket not counted | harness report |
| S8 | rename following | registered, not yet run |

**On the owner's ruling about unreachable files.** The ruling was to remove them from the universe after
counting. Under Amendment 4 that removal can move a confirmatory number, so this draft carries it out as
`PU_reachable_universe`, beside the frozen run. If the count is zero in every scored repo, the two are the
same run. If the owner wants the removal in the confirmatory run itself, the confirmatory label changes from
"pre-registered; point estimates partly seen" to a post-unblinding analysis. That is the owner's choice and
this draft does not make it.

## 5. What is reported with the result that was not planned before

- Per repo: files excluded as vendored by pattern, with the five patterns that excluded most; files ranked
  that the history cannot touch; fixes lost to renames after the snapshot.
- From the control repositories: how much of a planted effect the pipeline recovers. Ten positive controls
  gave +0.066 against +0.133 on true fixes; about 40% is lost in the label rule and about 20% of the rest in
  the pipeline. The share lost in the label rule depends on the mix of commit conventions the generator
  assumes, which was not measured from real repositories. This goes in the power statement as a caution: the
  smallest detectable effect of 0.05 to 0.08 is on the **label**, and a true effect has to be larger than that
  to show.

## 6. How the run is made

Through the stored tables and generated seal of `research_codebase_spec.md` (steps 3 to 7), built by moving
SA3's functions, not rewriting them. Before any real label is read:

1. the stored tables reproduce every public count of the existing outcome files, or each difference is
   explained;
2. the control suite passes;
3. the frozen run and each sensitivity are named in the seal.

## Owner decisions, 2026-11-14 (evening)

The owner accepted both recommendations: the unreachable-file removal runs beside the frozen run as
`PU_reachable_universe`, and the confirmatory run keeps the registered random streams. Still required before
this is in force: two independent reviews (checklist item 15). The two questions as put:

1. Accept section 4's handling of the unreachable-files ruling (beside the frozen run), or move it into the
   confirmatory run and accept the changed label.
2. Accept keeping the registered random streams for the confirmatory run, with named streams as a sensitivity.
   The architecture specification's step 4 said the opposite; this draft is the more conservative reading of
   Amendment 4 and the specification will be changed to match if accepted.
