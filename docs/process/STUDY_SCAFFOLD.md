# Study scaffold — DRAFT for the owner to permute

**Status: a proposal, 2026-11-14. Nothing here is adopted.** It treats a study the way this repo treats code:
a skeleton with required slots, filled in, committed, checked mechanically, reviewed, changed by diff.

Every line carries where it comes from, so it can be argued with:

- **[log]** a fault that happened here — `docs/STUDY_DEFECT_LOG.md`, with the entry number.
- **[lit]** the literature review, **as corrected by its audit** — `docs/process/litreview_agents_study_design.md`,
  `docs/process/litreview_audit.md`. Only items the audit marked "can be relied on" are used as support.
- **[untested]** my proposal, with no evidence behind it yet.

## What the evidence does and does not say

1. **Nobody has measured multi-agent review of study designs** — not in the literature, not in any of eleven
   tool repositories. Everything about how many reviews is extrapolation. [lit]
2. **One model review finds a minority of real errors and each run finds different ones.** More runs keep
   finding more, without a visible plateau, in the two studies that looked. [lit] That matches 53 log entries
   over five reviews with no decline. [log]
3. **We cannot yet tell "a deep pool of real faults" from "a stream of false alarms".** The audit's sharpest
   point: the best benchmark puts model-reviewer precision in single digits. Here most findings were
   reproduced before being acted on, but not all, and the log does not record which. **So reviewer calibration
   comes before any stopping rule.** [lit]
4. **Every statistic, control and gate fault here was found by running something, never by reading.** [log 13,
   14, 15, 25, 28, 34, 42, 50, 51]
5. **A check is not evidence until it has been tested.** The one gate adopted untested failed a correct
   pipeline 71% of the time and then leaked the result. [log 25, 26] One tool repository states the rule we
   lacked: plant one defect per copy, keep a clean copy, run the check blind, score hits and false alarms. [lit]
6. **Controls need both directions.** Placebos that must show nothing, and a known effect that must be found;
   and a planted effect is easier to find than a real one, so passing is necessary, not sufficient. [lit]
7. **Pre-registration by itself does little; undisclosed deviation is the norm.** A computed diff between
   what was registered and what ran is worth more than a promise. [lit]

## The skeleton: one directory per study

```
studies/<id>/
  claim.md            the claim in one sentence; what result would make a sceptic accept it, and reject it
  prior_work.md       who has tested this, with what design and effect size; sources opened, audited
  spec.md             ONE document, every rule stated once, each with the function that implements it
  controls.md         negative controls + why each shares the confound; positive controls + how planted
  data_card.md        per repo: what is ranked, what can be positive, label inputs present, top directories,
                      bot share, largest labelled commit, scan completeness — all computed, none typed
  seen.md             what has already been looked at, by whom, when; what can no longer be confirmatory
  power.md            smallest detectable effect, from the test's own null width
  checks/             every gate and placebo, each with its qualification record (below)
  sim/                the synthetic generator and the end-to-end run on it
  reviews/            one file per review: role, model, findings, each marked reproduced / not / false alarm
  deviations.md       GENERATED: diff of spec.md and code against the registered commit
  result/             written once, by a job that holds the outcome key
```

A slot may say "not applicable, because …". It may not be empty. A script refuses to open a review round
while any slot is empty or `data_card.md` is older than the data. [untested; the six questions it encodes are
log 1–12, 29, 30]

## The lifecycle, with what must be true to move on

| stage | who | exit condition |
|---|---|---|
| 0. Claim and prior work | Opus drafts; a second model audits every citation | a human reads `claim.md` and says the question is worth asking |
| 1. Feasibility | author | `data_card.md` computed; the count of units clearing each floor is known **before** the design is written around them [log 52] |
| 2. Design | author | `spec.md` complete; every statistic, control and gate has run on the synthetic generator under no effect, under a planted effect, and under "only size" and "only activity" [log 13, 14, 34, 50, 51] |
| 3. Design review | N independent sessions, no outcomes | findings reproduced or marked false alarm; the spec is **regenerated**, not amended [log 32] |
| 4. Build | Opus, from `spec.md` alone, on synthetic data only | tests pass; the end-to-end synthetic run recovers planted effects and nulls |
| 5. Code review | Fable; ideally a second independent build to compare numbers against | rule-to-code table has no "differs"; seeded faults found at the agreed rate |
| 6. Controls on real data | a job, not a session | negative controls within tolerance; positive controls recovered; non-structural attributes read as null [log 50] |
| 7. Seal and score | a human authorises; the job runs once | every input hashed, including labels and scans [log 44] |
| 8. Report | author | result, power, every exclusion with its reason, every deviation, the label audit |

## Rules that the log paid for

- **Failures are debugged on synthetic data only.** When a gate fails on real data, nobody looks further at
  real data. [log 26]
- **A reviewer's proposal is tested like the author's design.** Four faults came from reviewers. [log 15, 20,
  21, 25]
- **Reviews are comments; changes are a regenerated spec.** [log 20, 32]
- **Blinding is by permission, not instruction.** The outcome labels live where analysis sessions cannot read
  them; a separate job joins them to predictors. A reviewer's check that touches real outcomes is an
  unblinding. [lit; log 26] *How to do this on one machine is open.*
- **Agents run git with lazy fetch and auto-cleanup off.** [log 49]
- **Times come from commits.** [log 24]

## Controls: the control repository

**Negative controls** — values that know nothing a structural measure should know: a path hash, a size
surrogate fitted on size alone, and non-structural attributes (bytes, name length, prior commit count). Each
with one written sentence on which confound it shares. [lit; log 28, 50]

**Positive controls** — the part we have never had. Three kinds, weakest to strongest:

1. **Planted in synthetic data.** Already used by reviewers; tests the statistic only.
2. **Planted in real data:** take a real repo's files, sizes, directories and commit history, and re-draw
   which files get "fixed" with a known dependence on a structural measure, at graded strengths. Tests the
   statistic and the matching against real confounding structure. Pitfall: it keeps only the confounding that
   was measured. [lit]
3. **A control repository with real mechanics:** a small repo whose history is generated — commits that
   introduce a defect of a known kind in files with a known structural property, and later commits that fix
   them, with realistic messages, merges, renames, a licence sweep, a bot. Run through the *entire* pipeline:
   engine scan, label builder, universe rule, statistic. It tests the parts that 2 cannot: the label rules and
   the plumbing. **Mutations** of it — drop the fix references, squash the merges, vendor a directory — give a
   score: how many planted effects and planted faults the pipeline detects.

A known mechanism is also a positive control on real data: "a file's recent commit count predicts its next
fix" should always be recovered; if it is not, the instrument is blind. [untested]

## Qualifying a check before trusting it

For each gate, placebo or review procedure: N copies of a small study each with **one real past defect from
the log** re-introduced, plus at least one clean copy; run blind in fresh sessions; record hits, misses and
false alarms in `checks/ledger.md`. An unqualified check counts as no evidence. Real past defects, because
invented ones are easier. [lit; log 25]

## Reviews

- **A checklist built from the log, plus a role.** The audited literature does not show roles beating a good
  checklist; the original inspection method built its checklist from recent error types, which is this log.
  [lit] Proposed roles, one or two questions each: *universe and label* (can everything ranked be positive; is
  the label the same thing everywhere) · *simulator* (what does each number do under no effect, only size, only
  activity) · *instrument* (how is each measure computed, what else moves it) · *spec-to-code* · *claims and
  blinding* (what was seen, what can still be claimed) · *feasibility and power*.
- **Every finding is reproduced before it is logged or acted on**, and the reproduction is recorded. That is
  what will tell us our reviewers' precision. [lit]
- **How many: unknown, and to be measured, not assumed.** First experiment: seed 6 to 8 past defects into SA3's
  system and run it past k = 1, 2, 4, 6 independent sessions, mixed models; plot found against k. Second:
  a fresh review of SA3 as it stands, counting reproduced blockers. Until then the working rule is the
  owner's three, and "reviewed" means the last round produced no reproduced blocker. [untested]
- **Mixed vendors:** worth doing, not shown to help — strong models' errors are correlated across providers.
  [lit]

## Where a human is not replaceable

Deciding the question is worth asking; judging whether a negative control really shares the confound; ruling
on whether a finding is a blocker; authorising unblinding; reading 25 labelled commits per repo. [lit; log 30]

## What I would build first

1. The control repository and its mutations (kind 3), with the pipeline run on it as a test.
2. The qualification ledger, starting with SA3's size-surrogate gate.
3. The reviewer-calibration experiment on SA3.
4. Only then: the slot checker and the template, generalised from what 1–3 teach.

## Open questions for the owner

- One machine: how are outcome labels kept from analysis sessions?
- Is a second, independent build worth its cost on every study, or only on the scorer?
- Should SA3 be scored at all before 1–3 exist, given it would be the first study through an unqualified
  pipeline — or is it the natural test case to push through them?
