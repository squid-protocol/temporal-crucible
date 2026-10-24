# Self-scan DB as agent context: the #4479 A/B, logged (gitgalaxy#4479)

**Type:** exploratory. **EXPLORATORY: nothing here was registered in this register before its runs; no hypothesis
tests, no p-values.** The patterns are candidates for registration on unseen tasks (see the last section), never claims.
**Predictor:** agent access to GitGalaxy's self-scan DB (`tests/tools/self_scan.py`, `self-scan-query`,
`context_pack.py`) versus grep + Read only. **Outcome:** agent cost (tokens, tool calls, wall-clock) and fix quality.
**Repo:** gitgalaxy itself (the agent's working repo, not a defect corpus).
**Source of record:** gitgalaxy [`docs/agents/self-scan-ab-protocol.md`](https://github.com/squid-protocol/gitgalaxy/blob/main/docs/agents/self-scan-ab-protocol.md)
(the protocol, results ledger and the gitgalaxy-side verdict; gitgalaxy#4479, closed 2026-10-24).

This is off the program's main axis. Every other row in [`EXPERIMENTS.md`](EXPERIMENTS.md) asks whether a GitGalaxy
measurement predicts real defects beyond a line count. This one asks whether GitGalaxy's *output* makes an AI agent
better or cheaper at fixing issues in a codebase. It is logged here because it is a validation of the product's claimed
use, and because it went wrong in the ways this register exists to catch.

## What was run

Paired runs on the gitgalaxy repo. Per pair: same model, same base commit, same brief, each arm in its own worktree,
launched together. **Arm A** regenerated the self-scan DB (~25 s) and queried it first. **Arm B** could use only grep
and Read. Each arm opened a draft PR. Cost is the harness's numbers (self-reported time was off by ~5× in round 1).

| Round | Date | Task | A tokens | B tokens | Δ tokens | A calls | B calls | A min | B min | Δ time | Recorded outcome | PRs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-05 | #4472 (names its files) | 75,795 | 69,568 | +9.0% | 26 | 25 | 5.2 | 4.7 | +11% | same result; **A also found the inverted `--corpus` filter** | #4481 A merged, #4480 closed |
| 2 | 2026-10-24 | #4548 (item 1) | 50,705 | 49,817 | +1.8% | 14 | 11 | 1.4 | 0.75 | +87% | no PR: item already fixed on main; both confirmed it | none |
| 2 | 2026-10-24 | #4991 | 69,991 | 71,193 | −1.7% | 19 | 26 | 2.3 | 1.7 | +35% | same root cause and lists; same sibling gaps | #6388 A, #6387 B, both closed (superseded on main by #6466) |
| 2 | 2026-10-24 | #3303 | 71,435 | 90,827 | −21.4% | 35 | 27 | 2.7 | 2.4 | +13% | same rule fix; **A also found the `script:` scope-name audit artifact** (474 vs 460 of 487 exact) | #6386 A kept, #6385 B closed |
| 3 | 2026-10-24 | #138 (names no file or function) | 62,792 | 54,783 | +14.6% | 18 | 20 | 1.9 | 1.2 | +58% | same root cause and fix; **A also excluded the engine's `.gitgalaxy/` cache** and kept the list on the scope; B wrote 8 tests to A's 7 | #6394 A kept, #6393 B closed |

Δ = (A − B) / B. A's minutes include the DB regeneration.

**Timeline of the rule.** Round 1 ran 2026-10-05 with no written decision rule. The protocol doc carrying the decision
rule and the task-qualification rule landed 2026-10-24T05:49Z (gitgalaxy#6373). Rounds 2 and 3 ran after it, between
06:34Z and 07:01Z, and the gitgalaxy verdict, labelled "firm", landed at 07:13Z (gitgalaxy#6395). So for 4 of 5 pairs the
rule was stated in advance. It was never registered here, and the agent that ran the arms also wrote the verdict.

**Gitgalaxy's verdict rule:** "Arm A wins only if it uses fewer tokens or less time AND its outcome is no worse. A worse
outcome at lower cost is a loss. Differences under 10% are inconclusive until a third paired run." Gitgalaxy's verdict:
1 win (#3303), 3 inconclusive, 1 loss on cost (#138). The self-scan DB does not make an agent cheaper or faster, so it
stays optional in agent briefs.

## Descriptive patterns (no tests)

1. **Time: A slower in 5 of 5 pairs** (+11% to +87%). The ~25 s regeneration is a fixed cost that tasks of 1–5 minutes
   do not recover. This is the most consistent pattern, and partly a design artifact: in real use the DB would be built
   once per main commit and shared, not rebuilt per task.
2. **Tokens: no consistent direction.** −21% to +15%, and four of five gaps are under the 10% band. With one run per
   arm per task, within-arm variance was never measured, so nobody knows whether 10% is inside run-to-run noise.
3. **Extra findings: A found something B missed in 3 of 5 pairs** (#4472, #3303, #138). The ledger records no case of
   B finding something A missed, apart from one extra test in #138. The verdict credits only #3303, the one pair where
   A was also cheaper. This is the pattern the cost-first verdict hides, and it is where the next experiment should look.
4. **Qualification: 1 of 5 tasks met the experiment's own rule** (the issue names no file or function, checked with
   `context_pack.py`). Round 1 predates the rule, and all three round-2 issues resolved paths from their bodies. On the
   one qualifying task (#138), both arms found the code unaided, and A's three DB queries confirmed what two greps showed.

## Why the quality rubric was the weak part

The cost side was measured by the harness. The quality side, which the verdict rule uses as a veto, was not specified:

- **"No worse" was never operationalised.** The ledger judges it from "same root cause", diff size and test counts,
  written up by the agent that ran both arms. There was no pre-stated scale and no second reviewer.
- **Correctness was never measured.** Golden bless, `crucible_check` and `pr_gates` were skipped in every arm (cost
  cap). Neither arm's fix was known to be correct or regression-free when the verdict was written; the kept arms are
  only now (2026-10-24) going through the full gates.
- **Asymmetric rule.** Under "fewer tokens or less time AND no worse", a better outcome at a higher cost can never be a
  win, so the rule cannot see a thoroughness benefit. Pattern 3 is exactly that case.
- **No blinding.** Arms were labelled `[experiment A]` / `[experiment B]` in their PR titles, and the reviewer knew the
  hypothesis. The extra findings were recorded for A; nobody searched B's diffs for findings A missed with the same care.
- **No ground truth for the fix.** "Same root cause" was the reviewer's opinion. No reference fix, hidden test or
  pre-enumerated list of sibling gaps existed to score against.
- **n = 1 per arm per task, five tasks, three task types.** That is anecdote-scale by the protocol's own standard (its
  first line says one run per arm is an anecdote), and the 10% band was not tied to measured noise.

What the experiment does establish: per-task DB regeneration costs time on small tasks; and on a well-named codebase,
grep finds the fault about as fast as the DB. What it does not establish: whether the DB changes fix quality, which is
the open question.

## Proposed follow-up: a quality-first replay experiment (proposed, NOT registered)

To be registered (three places, same session: epic comment, a `tc#` issue's `Register:` line, a section in
[`HYPOTHESES.md`](HYPOTHESES.md)) only after the owner agrees the rubric. It runs on **unseen tasks only**: none of
#4472, #4548, #4991, #3303 or #138.

**Design: historical replay, so quality has a ground truth.** Draw closed gitgalaxy issues whose fix merged with tests.
For each one, check out the fix's first parent, give both arms the issue text as written, and keep the merged fix as
the hidden reference. This is the event-pair method of this repo applied to agents: the "event" is a real fix, the
"parent" is where the agent starts.

- **Task pool:** ≥ 12 tasks, listed in the registration before any run, in two pre-declared strata:
  (a) *vague*: the issue names no file or function (`context_pack.py` resolves nothing from the body);
  (b) *impact*: the fix spans ≥ 3 files or needed a "who calls this / what breaks" question, which is the DB's claimed strength.
- **Replicates:** 3 runs per arm per task, so within-arm variance is measured. The equivalence band δ for cost is set
  from the pilot replicates before the comparison is unblinded, and stated in the result doc.
- **DB cost amortised:** the DB is pre-built at the base commit, as it would be in real use. Regeneration time is
  reported separately, not added to arm A.
- **Blinding:** arms get neutral labels (`[run X]` / `[run Y]`, randomised per task). Scoring is done by a reviewer
  session that never sees the label map, using only the rubric below. The map is opened after all scores are recorded.
- **Every run passes through the full gates** (`pr_gates`, golden check, `crucible_check`) before it is scored.

**Rubric (per run, pre-specified):**
- **R1 correct:** the reference fix's tests pass on the run's code. 0/1, or the fraction for multi-test fixes.
- **R2 no regression:** full gates and golden check green. 0/1.
- **R3 localisation:** the run's diff touches the function(s) the reference fix changed. Function-grain overlap, scored mechanically.
- **R4 sibling-gap recall:** the share of a pre-enumerated sibling list found by the run. The list is the reference
  fix's follow-up issues, plus the union of findings from all runs, adjudicated blind after scoring.
- **R5 economy:** the run's changed lines relative to the reference. Penalise runs over 2× the reference.

**Proposed claims (ids reserved, scope `AG-` = agent utility):**
- **AG-H1:** the correct, non-regressing fix rate (R1 ∧ R2) is higher in arm A than arm B, paired by task (McNemar on
  discordant pairs, or a mixed logistic regression with task as a random effect).
- **AG-H2:** mean sibling-gap recall (R4) is higher in arm A, with the effect concentrated in the *impact* stratum
  (Wilcoxon signed-rank on per-task means).
- **AG-H3:** cost is equivalent: the paired token log-ratio's 90% CI falls within ±δ (TOST), δ fixed from the replicates.

Bonferroni across the three claims (α = 0.05 / 3 ≈ 0.0167 each), and a power floor in the repo's spirit: at least 20
discordant run pairs for AG-H1 to be evaluable, else reported as not evaluable. The verdict is published either way.
Reading the outcomes: AG-H1 or AG-H2 supported with AG-H3 holding means the DB buys quality at equal cost and earns a
place in briefs for impact-stratum tasks. All three null, with the gates actually run, would turn "optional" into "not
worth it".

## Guards (template checklist)

- [x] Paired design (same model, base commit, brief): the agent analogue of size-matched controls.
- [ ] Temporal ablation, rename tracking, defect-lift over LOC: not applicable (no history scan, no defect labels).
- [ ] ≥ 20-positive power rule: **failed** (5 pairs, one run each). This is why the doc is exploratory.
- [ ] Multiple-comparison correction: not applicable (no tests run here); built into the proposed follow-up.
- [ ] Pre-registration: **failed** for this register. Partly met on the gitgalaxy side, where the rule was written
  before rounds 2–3.
