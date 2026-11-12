# LAWS2 — what to build, and what LAWS 1 proves we must control

LAWS 1 is closed as a failure (`laws_postmortem.md`). It produced no law verdict, but it produced something a
second attempt can use: a working set of estimators, a scanned corpus, and — from its own development repos —
enough measurement to say which of these laws are worth testing at all, which are being reported by the
instrument rather than the code, and how many repositories each one actually needs.

Everything below is derived from runs on the **development repositories**, not from a panel. It is design
input, not a finding. The exploratory numbers are in `laws_exploratory.md`, the tables in
`laws_exploratory_tables.md`, and the run frame that executes this design is `tools/laws2.py`
(`laws2_checklist.md` is generated from it).

## 1. Select laws by whether they survive a worse call graph

This is the decision LAWS 1 never made, and it can be made **without any oracle**. Re-running every law with a
seeded fraction of resolved call edges deleted says directly whether a number describes the code or the
extractor:

| law | worst change when 44% of edges are removed | LAWS2 status |
|---|---|---|
| LAW-2 preferential attachment | 10% | **confirmatory; a compile-free graph is good enough** |
| LAW-1 heavy tails | 26% | confirmatory, but coverage reported with every number |
| LAW-4 centralisation | 30% | descriptive unless oracle-backed |
| LAW-3 hub persistence | **157%** | **drop or redesign — it is reporting the extractor** |

LAWS 1 applied one oracle gate to every law equally, and lost three of four confirmatory languages to it.
**The gate belongs per law, in proportion to that law's coverage sensitivity**, and the ladder that measures it
is cheap enough to run on everything.

## 2. Size the panel per law, not uniformly

From the between-repo variance of the development runs (`tools/laws2_size.py`, recomputed by the `sizing`
stage):

<!--SIZING-->

A single panel size is the wrong shape of decision. LAWS 1 registered 16 per confirmatory language: ample for
LAW-1 and LAW-2, marginal for LAW-4, and far short for LAW-3 and LAW-8. **A law whose required k is out of
reach should be dropped at design time, not discovered at synthesis time** — LAWS 1 pooled k=2 and published a
99% interval of −3.76 to 4.00 with a NaN prediction interval.

These are planning numbers: tau is estimated from a handful of repos, mostly one per language, so it mixes
between-repo with between-language variation. The `sizing` stage recomputes them from LAWS2's own pilot, and
the registration carries the recomputed values.

## 3. The controls — LAWS 1 had one, and it was not enough

Each control answers a question LAWS 1 could not answer about its own numbers. `tools/laws2.py controls` is the
machine-readable version; each is a first-class arm with its own stage, not an appendix.

| control | asks | why LAWS 1 needed it |
|---|---|---|
| **neg-shuffle** | If the law is absent by construction, does the pipeline still report it? | Never run end to end — only per-estimator unit tests |
| **pos-synthetic** | If the law is present at a known strength, is it recovered? | Estimators were tested on simulated data; the *pipeline* was not |
| **coverage-ladder** | Does the number describe the code or the extractor? | Measured once, late, as an amendment: LAW-3 moved 157%, LAW-2 10% |
| **size-adjust** | Is the structural effect just size? | Adjustment removed 60–90% of LAW-7's signal, and was reported second |
| **test-split** | Is the law about code or about testing conventions? | Never run; commons-lang has 363 test files against 264 source files |
| **time-split** | Does it hold in both halves of history? | Never run; a whole-span-only law is a growth artefact |
| **merge-rate** | Is the in-degree tail an artefact of collapsed identities? | Merge rate ran 0–19.2% per snapshot and was never used |
| **oracle-calibrate** | How far is compile-free from compiler-grade, where we can check? | The oracle was a *gate*, so it removed languages instead of calibrating them |

The rule that follows: **no number is published without its control row.** The `report` stage refuses
otherwise.

## 4. Measurements to add

- **The resolution profile travels with every law number** — resolved share, the per-step breakdown of what was
  dropped, and the node-merge rate. All of it already exists per snapshot; LAWS 1 kept it as an appendix.
- **Oracle agreement where the oracle genuinely runs** (C, Go after modules), used to put stated uncertainty on
  the languages where it cannot run — instead of deleting those languages.
- **Per-repo data availability checked at sampling time.** LAW-9 was evaluable in one repo of five because the
  rest had no sized OSV fix table. That is knowable before a repo is seated.
- **An expected drop rate for every evaluability gate**, registered in advance. libxml2 silently left LAW-6 for
  an in-cycle share of 0.001 against a 0.05–0.8 gate.

## 5. Estimand changes, law by law

- **LAW-3 hub persistence.** Observed persistence is 0.88–0.99 and the random-target null is almost the same,
  so the gap is −0.006 to +0.12 and swings 157% with coverage. Either condition on hubs that *could* have
  moved, or measure rank churn among hubs, or drop it. As written it is close to unfalsifiable.
- **LAW-1 heavy tails.** Fix x_min by rule or report the tail-definition sensitivity: "the tail" ranged from 8%
  of nodes (libxml2, x_min 10) to 100% (sphinx, x_min 1). Those are not the same quantity, and the power law is
  rejected outright (GOF p<0.05) in a repo whose registered effect is still positive.
- **LAW-4 centralisation.** Register a smallest effect worth caring about. With 50–100 snapshots and margin 0,
  four of five repos are "significant" at a largest Gini gap of 0.026.
- **LAW-7.** The **size-adjusted** effect becomes the registered primary; the raw effect is reported beside it.
- **LAW-8.** Compare against a strong baseline (churn, authors, prior fixes), not a weak one. Against a weak
  baseline it still moved AUC by less than 0.03 in every repo.
- **Every law** carries a registered SESOI. Margin 0 is why LAWS 1 would have reported trivia as confirmation.

## 6. Order of work, enforced by the frame

The single most expensive lesson: LAWS 1 fixed its frame, fingerprint, draw and seating **before** checking
whether the oracles could run. `tools/laws2.py` encodes the order as gates and refuses to run a later stage
until an earlier gate passes — attempting to seat before the oracle screen is an error, not a judgement call.

1. **Phase 0, feasibility (cheap, reversible):** oracle screen, data availability, and a pilot driven *all the
   way to a law statistic*. All three are gates.
2. **Phase 1, fix the design:** per-law panel sizes and SESOIs computed from the pilot, then a registration
   that is hashed.
3. **Phase 2, sampling:** frame, exclusions, draw, seat. Draw depth is set once, from the measured 5.8%
   clone-time pass rate, instead of being amended from 40 to 400 to 2,000.
4. **Phase 3, measurement:** scan, profile, oracle agreement.
5. **Phase 4, controls:** every arm above, each its own stage.
6. **Phase 5–6, laws, synthesis, figures, report.** Synthesis refuses to pool below the sized k. The twelve
   figures are declared in advance (`laws2.py figures`) so none is invented after seeing the numbers.

## 7. Sampling notes carried over

- **95% of all rejections were one bar** — fewer than 2,000 first-parent commits. Either relax it or accept
  that it, and not the research question, defines the population.
- **Never approximate a rule with a cheaper proxy that errs optimistically.** Screening on *total* commits put
  the pass rate at 20% when it is 5.8%, and mis-ranked the languages.
- **Enforce eligibility rules from the first walk.** The licence rule, applied four days late, cost 30% of the
  seats already taken.

## 8. Parameters, not constants — and a specification curve over them

LAWS 1 carried about thirty bare module constants. A research choice and a bootstrap count looked identical in
the code, and neither reached the registration. `docs/laws2/params.json` splits them into three classes
(`laws2.py params` prints it):

- **research (14)** — these change the *claim*. Each is registered and each carries a `grid` of defensible
  alternatives: 45 grid cells in all. Examples, with why each is a choice and not a fact:
  - `hub_years_apart = 5` — why five? Grid 3/5/7/10.
  - `hub_top_share = 0.01` and `hub_still_share = 0.05` — who is a hub, and how far may one fall and still
    "persist"? At 0.05 both the observation and its null sit near 0.95, which is most of why LAW-3 is empty.
  - `hub_ceiling_sd = 0.005` — silently decides *which repos the law is tested on*.
  - `tail_xmin_rule = "ks"` — a per-repo x_min means "the tail" is not the same object across repos. The grid
    includes fixed values, which are comparable but less favourable.
  - `attach_features` — dropping `log_loc` asks whether preferential attachment is size in disguise.
  - `snapshot_granularity = "quarterly"` — LAW-2 counts new edges per step, so the step length sets its input.
  - `frame_min_commits = 2000` — did 95% of all rejection work; this parameter, not the research question,
    defined the population.
- **precision (8)** — bootstrap counts, replay counts, sampled alternatives. They move error bars, not claims.
  Set by budget, report the value.
- **guard (6)** — implementation floors. None may bind silently: every exclusion is counted and published.
  LAWS 1's in-cycle gate removed libxml2 from LAW-6 at a share of 0.001 and said so only in a field.

The `ctrl-speccurve` arm walks the grid and reports the **distribution** of each law's effect rather than one
point. For a law already known to swing 157% with coverage, "does the sign survive 3/5/7/10-year windows and
1%/5%/10% hub cuts?" is a more honest question than any single setting.

## 9. Replicate the originals — as a second arm, never as the method

Every law runs **twice**:

- **`arm-as-published`** — the source paper's own estimator, its own null, and its own figure form, each citing
  the paper and equation it reproduces.
- **the registered arm** — our estimator against the hard null.

**Why the as-published arm is necessary.** A replication that uses only a modernised method can always be
answered with "you didn't do what we did." Without this arm we cannot separate *the claim was wrong* from *we
measured differently*.

**Why it must never be the headline.** The original methods are weak in known ways — the registration itself
records that "heavy-tailed versus exponential" is near-certain and uninformative, and cites Broido & Clauset. A
straight-looking log-log plot is not evidence; it is how these claims were overstated in the first place.

**The gap between the arms is the finding.** "The claim reproduces under its own method and disappears under a
proper null" is the most valuable result a many-labs replication can report — and it is already visible in the
development data, where LAW-1's effect against an exponential runs roughly double its effect against the
negative binomial.

Three figures carry this: `f13_as_published_vs_strengthened` (the two estimates side by side, per law),
`f14_original_figure_form` (each paper's own figure redrawn on our data), and `f15_specification_curve`.
