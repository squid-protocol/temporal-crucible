# A codebase built for research — architecture specification (for SA3 only)

**Status: Revision 3, 2026-11-14, after two independent design reviews.** Steps 0 and 1 are built and
committed; step 2 is drafted (`docs/sa3_amendment5_draft.md`, Revision 2); step 3's first phase is being built.

**What Revision 3 changed.** It reconciles the second design review (Gemini, on PR #185:
`reviews/research_codebase_review_gemini.md`, 3 blockers and 7 further points) with the first (Claude:
`reviews/research_codebase_review_claude.md`) and with Amendment 5, Revision 2. The reconciliation table is
section 12. The change that matters:

- **The stored tables are not SA3's confirmatory engine.** SA3's confirmatory run is the existing scorer, run
  once, unchanged (Amendment 5). The tables, the corrected reading rule and the named random streams are the
  **verification and sensitivity path** beside it. For the next study they are the engine.

It builds on `STUDY_SCAFFOLD.md`, `blinding_spec.md`, `control_repo_spec.md`, `harness_spec.md` and
`tables_spec.md` and does not repeat them.

## 1. What is wrong today, measured

Read-only inventory of `tools/`, 2026-11-14, counts as corrected by the first review, plus what the harness
found the same day. No study data was opened.

| what a database gives | what the code does today |
|---|---|
| One definition of each thing | The file-universe rule is written **5** ways that do not agree. The snapshot cut is recomputed in **6** places over different commit sets. The tree-wide rule is written **3** times with three denominators. SA3's keyword outcome and its tainted-merge test use two different keyword rules. |
| A schema with constraints | "Positives are ranked" is one `assert`. Nothing checks the reverse. The universe is never stored: three tools recompute it. The completeness check shares the rule it checks (defect log 56). |
| Provenance | The seal lists 9 files by hand, omits every data input and 13 rule-defining code files, and seals outside a git checkout without complaint (57). |
| Reproducibility | One random stream is shared across repos; a result depends on repo order and on which secondary measures are scored. |
| Stages with inputs and outputs | Building outcomes deletes and rebuilds one of its own inputs. SA3's snapshot is whatever a MOD-1 tool last wrote. The file that decides which repos are scored is written by no tool. |
| Configuration | 56 of 225 tool files hold a hard-coded absolute path. Per-repo exceptions are lists inside code. |
| Migrations | Five amendments. The text and the code disagree on tainted merges (54), on what a fix reference is (61), and on which commit is frozen (62). |
| Tests | None for the outcome builder or the scorer. Run on repositories with a known answer, the unmodified pipeline showed six faults in an afternoon (55–60). |

**What this architecture does not touch.** Of 20 defect-log entries walked by the first review, the design
catches 5 mechanically, makes 8 less likely and does nothing for 7. Statistic and gate design, power,
instruments, label validity and repo-level data faults are found by simulation, label audits and data cards.

## 2. Principles

1. **A rule exists once**, and later stages import it.
2. **Derived facts are stored, not recomputed.**
3. **A stage reads its declared inputs and writes its outputs, and nothing else** — enforced by what the stage
   can see, not by what it promises (section 5).
4. **A constraint fails at build time.**
5. **A result names everything it depended on,** computed, not typed.
6. **Every part runs on the control repository before it is trusted.**
7. **For each rule, the specification says whether the text or the code governs.**
8. **Move before rewriting.**
9. **After estimates have been seen, nothing replaces the frozen run; everything else runs beside it.**

## 3. The steps

| step | what | state / exit test |
|---|---|---|
| **0. Harness** | The existing SA3 pipeline run on generated repositories inside a sandbox | **Done** (`tools/harness/`). One engine scan 2.4 s; a repository 16 s |
| **1. Three-way table** | Pipeline against manifest, rule by rule | **Done** (`harness_report.md`): six faults, four unstated behaviours, effect recovery over 20 seeds |
| **2. Amendment 5** | Says what is frozen and what runs beside it | Drafted, Revision 2; one review done, the owner's decisions recorded; its second review is owed |
| **3. Stored tables** | `tables_spec.md`. Phase A: control repositories. Phase B: SA3's real data, a separate specification and a deliberate job whose outputs are the public counts of Amendment 5 section 7 | Phase A in build. **Phase B does not start until the points of section 12 marked "before phase B" are closed** |
| **4. Seal and named streams** | A generated seal (section 5). Named random streams, used by the sensitivity `PU_named_streams` | A stage that reads an undeclared input cannot (it is not visible). Under named streams, permuting repo order and the set of predictors gives identical numbers. Under the registered stream the reference numbers are untouched, because the reference scorer is not edited |
| **5. Reading rule** | One function for the family of three tests, the Holm step included, "an earlier test failed" defined; a separate vocabulary for everything else | Used for the **corrected** readings printed beside the coded ones. Defect-log entries 42, 43, 47 and 48 are each a named test case; every combination of inputs has an expected word; ties and empty pools have a stated answer |
| **6. Control suite** | Section 7 | All rows pass at the stated sizes and bounds |
| **7. The run** | The owner runs the sealed **reference scorer** once: that is the confirmatory run. The stored-tables scorer runs beside it; a per-cell equal / not-equal map is printed; the sensitivities run | Amendment 5 section 9: input hashes equal, the placebo output regenerated byte for byte, five seeded faults each reported by the check on control repositories |

**The reference code** is the file contents at `8fb7fe0` for `tools/sa3_score.py` and `tools/sa3_outcomes.py`
and at `edc5c53` for `tools/sa3_stats.py` and `tools/mod1_lift.py` (Amendment 5 section 1).

Each step is built by Opus from its specification with the SA3 code open, and reviewed before the next begins.

## 4. The tables

As `tables_spec.md`, which governs where the two differ. In summary:

| table | key | notes |
|---|---|---|
| `repo` | repo | language, unit rule, cohort, status and reason, the clone's tip, engine id; **and how each prebuilt input was made** (below) |
| `snapshot` | repo | `cut_ct`, `sha`, `ct`, `window_start`, `window_end`. The hash is an input from the scan |
| `file` | repo, path | every path of the snapshot's tree once; `in_universe`, an ordered closed reason, the GitHub pattern that matched, `loc`, `history_can_touch` |
| `measure` | repo, path, name | raw measures with `absent_means`; derived predictors only once each one's null rule is written down (below) |
| `touch` | repo, sha, path | equal-path matching, as the code does |
| `link`, `event`, `pool` | protected | `event` is keyed **(repo, unit commit, path)**: the outcome files do not record which brought-in commit gave a merge its positives. The key with a linking commit belongs to the second, independent derivation (section 9) and is never reconstructed in the moved tables |
| `marginal` | repo, outcome | public. The frozen, registered list governs; a regenerated value that differs is reported |

**Invariants that fail the build:** every tree path once; `in_universe = 1` implies no reason; every protected
path is in the universe; `marginal` equals a recount from `event`; the window ends after it starts.

**Reported in the data card, never failing, on the frozen universe:** universe files with
`history_can_touch = 0`. That column audits **every** static way the universe and the history walk can
disagree, each counted apart: the `.gitattributes` re-inclusion; a path in the archive listing spelled
differently from the history's; symbolic links and submodule entries; commits off the first-parent chain in a
repo walked first-parent. The same condition **is** a failing invariant on the `PU_reachable_universe` view,
where those files have been removed by rule.

**How prebuilt inputs were made is recorded, not only their hashes:** the SHA-256 of GitHub's two lists; the
history walk's parameters (unit rule, C-family flag); the body harvest's flags (`--with-merges`,
`--sa3-links`); the engine id and the hash seed; the grammar pack's version. Two builds over the same clone
can otherwise differ silently.

**Canonical bytes:** as `tables_spec.md`, and: negative zero is written as zero; a not-a-number is never
written — it is `null` with a reason; whether a column is whole or real comes from the schema, not the value.

**Derived predictors and missing values.** The scorer's derived predictors each treat missing differently: one
reads absent as 0, one propagates it through a sum, one maps it to missing, and one turns non-positive values
into missing — after which the scorer drops those files **and recomputes the size bands**. Before any derived
predictor is stored (phase B), each one's rule for missing is written out beside its formula and tested on a
control repository, including the band recomputation.

## 5. The seal

**Isolation is structural.** A stage runs in a sandbox of the kind `tools/harness/sandbox.py` already builds:
the root is read-only, and **only the stage's declared inputs are bound in**. An undeclared input is not
refused; it is absent. This covers what wrapping Python's `open` cannot: SQLite's side files, `os.open` and
memory maps, libraries and their caches, git's own configuration and attribute reads, and anything a
subprocess does.

The ledger records, per stage: every declared input and its hash; the hash of every code file bound in,
including code run as a subprocess; interpreter, package and git versions; the hash seed; each clone's tip.
The seal is the closure of the ledger for a result. A result carries its seal's hash. The seal refuses when
git fails (defect 57).

What it cannot do: SA3's scans were made without a fixed hash seed, so they can be hashed and not reproduced.

Mechanical checks, run with the tests: functions in moved code take every registered parameter as a required
argument and no module assigns a numeric constant at module level except the one parameter file; no absolute
path outside one `paths` module; no import of the protected tables' reader outside the scoring job.

## 6. Where text, code and tables differ — every item, with its ruling

Under Amendment 5 the confirmatory run is the reference code, so "frozen" below means "as the reference code
does". The right-hand column is what runs **beside** it.

| # | item | frozen run | beside it |
|---|---|---|---|
| a | Matching later commits to snapshot files | equal path | S8, rename following |
| b | A missing predictor value | as coded, per measure | — |
| c | Random streams | the registered shared stream | `PU_named_streams` |
| d | The snapshot | the scanned commit; the window from the code's own cut | — |
| e | Universe files the history cannot touch | ranked | `PU_reachable_universe`, `PU_unreachable_made_reachable` |
| f | The list of scored repos | the frozen list | — |
| g | The universe variant | with `.gitattributes`, tutorial exclusions, the scan's generated list, GitHub's lists | `PU_generic_dirs_restored` |
| h | Tree-wide denominator | the universe | — |
| i | Two keyword rules | both, as coded (owner) | — |
| j | Tainted merges | counted when they inherit (owner) | — |
| k | Holm step, "not robust", vocabulary | **as coded** | the corrected readings, printed beside; a hypothesis whose reading differs is not called confirmatory |
| l | Stored `.gitattributes` cut at 200,000 characters | as stored | reported per repo |
| m | Tracker keys matched without regard to case | as coded | `PU_tracker_keys_case_sensitive` |
| n | Completeness | the registered measure | `PU_new_completeness` |
| o | Nesting coverage | the existing files | `PU_nesting_floor` |

## 7. The control suite

Scan time is known (2.4 s; a repository through the pipeline in 8 to 16 s), so the sizes below are affordable:
a 20-seed row takes about three minutes.

| run | size | must hold |
|---|---|---|
| negative control, Python and C | 20 seeds, default size, a span leaving 730 days | universe equals the manifest's unit files in every seed; for each planted property the pipeline's effect minus the expected-label effect, paired by seed, **does not differ from zero by more than 3.5 standard errors and by more than 0.005 at once** (both, not either: see the simulation below); the pipeline's effect itself is within ±0.03 of zero |
| positive control, three strengths | 20 seeds each | the planted property is recovered, grows with strength, and the paired difference from the expected-label effect passes the same rule (C: against its measured reference value, see below); the others stay within the negative control's spread |
| **placebo gates** | the same 20 seeds | path hash, directory hash and each size surrogate: the **mean over the 20 repositories** is within 0.005 of zero |
| **label-convention mix** | 20 seeds each | the positive control repeated under `tickets_for_everything` and under `no_references`; the pipeline's effect against the expected-label effect, as above. Reported: how the recovered share of a true effect moves with the mix |
| each mutation | 3 seeds | a recorded expectation: universe and labels match, or the pipeline reports the repository unusable for a stated reason. A mutation the pipeline gets silently wrong fails |
| quick set, with the ordinary tests | one negative and one positive repository | universe and labels only |

Measured so far (`harness_report.md`, and the placebo outputs of the same runs):

- Paired pipeline − expected labels: Python −0.002 (standard error 0.002); C **−0.019 (0.004)** from the
  engine's branch count. The C bound is therefore not ±0.01; the row reports the number and fails only if it
  moves by more than three standard errors from −0.019.
- Placebo gates, mean over 20 repositories: every one within 0.005 in the four standard suites (largest
  +0.0020). **A single repository of 300 files exceeds 0.005 in 5% to 50% of cases**, so the gate is a suite
  mean, never a per-repository test. With files under `cache/`-style names dropped, the `in_degree` surrogate
  reads +0.0045 (standard error 0.0013): inside the tolerance and not by much.

**Each bound's false-failure rate and the smallest bias it catches, by simulation** (2026-11-14; normal draws
with the per-seed spreads measured in the five suites: paired difference 0.003 to 0.038, median 0.022;
pipeline effect 0.026 to 0.054, median 0.037; 100,000 to 200,000 simulated suites per cell).

| rule | fails a correct pipeline | bias it catches 80% of the time |
|---|---|---|
| **Rejected:** paired difference within 3 standard errors **and** within ±0.01 (Revision 3's first wording) | 0.8% for the quietest row, **4.6% for a typical row, 24% for the noisiest; at least one of 22 rows in 65% of correct runs** | — |
| **Adopted:** fail only if the paired difference is beyond 3.5 standard errors **and** beyond 0.005, 20 seeds | 0.2% per row; at least one of 22 rows in 5.5% of correct runs | 0.006 for the quietest row, 0.022 typical, 0.038 for the noisiest |
| the same at 40 seeds | 0.13% per row; 2.4% for 22 rows | 0.005, 0.016, 0.026 |
| negative control: the pipeline's mean effect within ±0.03 | 0.03% typical, 1.3% for the noisiest row | 0.037 to 0.040 |
| placebo gates: the mean over 20 repositories within 0.005 | under 0.2% at a true leak of zero; 1% to 6% when the true leak is 0.0025, as SA3's own surrogates measure | a leak of 0.0055 to 0.0064 |

The first wording was the second design review's proposal with the author's numbers, adopted without
simulation; it would have failed a correct pipeline most of the time. The suite is used as a gate at **40
seeds** with the adopted rule. What it cannot see is stated: a bias under about 0.02 in a typical row.

Two truths exist by design: true fixes, and the labels the written rule should give. Universe and label rows
are judged against the expected labels; a reported row gives the statistic against true fixes.

## 8. Blinding

Not on SA3's route. `tools/blind/` is built (phase A) and tested on the control repository. Scrambles released
to sessions permute within the size band only (`blinding_spec.md`, Revision 3).

## 9. The second, independent build — protocol

Owner-approved as an experiment. Scope: the `event` derivation from the written rule (with the linking
commit), and the reading rule.

1. A different model builds each from the specification text alone, without sight of the first build.
2. Outputs are compared on control repositories under **every mutation**, not one base repository.
3. **Blind seeding:** copies of the first build each carry **one** known fault; clean copies are mixed in; the
   comparison is scored without knowing which is which. Both the detection rate and the false-alarm rate are
   recorded, beside what a review of the same copies finds.
4. **Adjudication is fixed beforehand:** where two clean builds differ, the specification text decides; where
   the text is silent (ties in a Holm step, an empty pool, the case of a tracker key), the case is logged as a
   specification fault and neither build is called wrong.

## 10. Deferred, and what this does not do

Deferred until a second study needs it: a rewritten `defs` package; a study configuration language; plug-ins;
a generated rule-to-code table; the `prior` point and the change effect.

It does not make the other 220 tools consistent, does not change SA3's registered statistic or hypotheses, and
does not make labels unknowable on this machine.

## 11. Owner rulings, 2026-11-14

1. Tainted merges follow the code. 2. Two keyword rules stay for SA3. 3. Files the history cannot touch stay
in the frozen run; their removal is a sensitivity. 4. The confirmatory run keeps the registered random
streams. 5. The confirmatory run is the reference scorer, run once, unchanged, with every correction beside
it. 6. The result's label is Amendment 5 section 8's. 7. The second independent build goes ahead as an
experiment (section 9).

## 12. Review record and reconciliation

| point | raised by | disposition |
|---|---|---|
| The spine would change SA3's numbers in unlisted ways | Claude, B1 | adopted in Revision 2; superseded by Amendment 5: nothing replaces the frozen run |
| Invariants that fail on correct data; `label` had no path | Claude, B2–B3 | adopted in Revision 2 |
| Scrambled labels leak | Claude, B4 | adopted; `blinding_spec.md` Revisions 2 and 3 |
| "Equal to old code" needs a safe harness | Claude, B5 | adopted; the harness is step 0 |
| This document contradicts Amendment 5 Revision 2 | Gemini, 1 | adopted: sections 3, 6 (item k), status; reference commit corrected |
| Reachability: failing invariant in one section, report in another | Gemini, 2 | adopted: reported on the frozen universe, failing on the sensitivity's view |
| `event` key | Gemini, 3 | adopted: (repo, unit commit, path); the linking commit only in the independent build |
| Suite needs an absolute bound and the placebo gates | Gemini, 4 | adopted **with two changes**: the placebo gates hold as a mean over 20 repositories and fail often on one, so they are a suite mean; and the absolute bound as first written (±0.01) failed a correct pipeline in 65% of simulated runs, so the rule is now "beyond 3.5 standard errors and beyond 0.005" (section 7) |
| Convention-mix circularity | Gemini, 5 | adopted: a suite row; the two mutations already exist |
| Reachability by rule must cover every static divergence | Gemini, 6 | adopted in section 4. **Before phase B** |
| Dual-build protocol | Gemini, 7 | adopted: section 9 |
| Isolation by Python hooks is not enough | Gemini, 8 | adopted: declared inputs bound into a sandbox |
| Negative zero, not-a-number, derived-predictor missingness | Gemini, 9 | adopted. Canonical bytes: sent to the tables builder. Derived predictors: **before phase B** |
| How prebuilt inputs were made | Gemini, 10 | adopted in section 4. **Before phase B** |
| Not adopted | — | none |
