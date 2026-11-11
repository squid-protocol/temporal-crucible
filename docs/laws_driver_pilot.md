# The full scorer, end to end on the development set

Development data (the CGR practice repos), never panel results. Tool: `tools/laws_run.py`. Numbers:
`/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot/laws_run_pilot.json`.

This is the pilot the methods review requires before the scorer hash is frozen (should-fix 9: "Require the full
scorer -- all nine laws, all null models, the synthesis -- to run end-to-end on the development repos: at least
commons-lang, prometheus and sphinx, plus 2 of the 5 C history repos. Publish run time, failure modes and the
resolution profile, then freeze the scorer hash."). The set run is exactly that minimum: commons-lang, prometheus,
sphinx, libgit2, libxml2.

Before this, the pilot's LAW-1 to LAW-4 numbers came from a script that was never committed, so the figures in the
2026-11-10 handoff could not be regenerated from the repository. That gap is what this tool closes; it is also
why the numbers below should be treated as the first reproducible ones, not as a confirmation of the earlier set.

## Run time and failure modes

| repo | language | quarterly snapshots | yearly | functions (last) | seconds |
|---|---|---|---|---|---|
| commons-lang | java | 97 | 25 | 4,315 | 227.0 |
| prometheus | go | 55 | 14 | 5,168 | 59.0 |
| sphinx | python | 75 | 19 | 3,408 | 94.1 |
| libgit2 | c | 72 | 18 | 4,204 | 116.0 |
| libxml2 | c | 108 | 27 | 3,575 | 139.0 |

**635 seconds for all nine laws over five repos, with zero failures.** No estimator raised, at the registered
bootstrap and replay counts, on any repo. Every law was evaluable everywhere except LAW-6 on libxml2 (too few
positive or negative file-years) and LAW-9 on the four repos with fewer than 20 advisory-labelled fix commits.
The panel is roughly ten times this, so the law layer is not where the panel's compute goes -- the scans are.

## The resolution profile, which is the finding

| repo | language | confident links | ambiguous (dropped) | unresolved | **share confident** |
|---|---|---|---|---|---|
| libxml2 | c | 10,178 | 8 | 8 | **99.9%** |
| libgit2 | c | 11,168 | ~0 | 129 | **98.9%** |
| prometheus | go | 7,040 | ~1,900 | 2,231 | **59.6%** |
| sphinx | python | 3,960 | ~1,400 | 1,485 | **58.1%** |
| commons-lang | java | 3,844 | ~2,000 | 1,079 | **55.6%** |

**The instrument resolves 99% of call sites in C and 56 to 60% in Java, Go and Python.** Every law is computed on
whatever network the engine produced, so the C networks are nearly complete and the others are missing roughly
two fifths of their edges. That is a between-language difference in measurement quality of the same order as any
effect the study is looking for, and it runs straight through the universality test, which compares languages.

This is not what ACC-P catches. ACC-P validates the **precision** of confident links; this is **coverage**. A
network can be 99% precise on the edges it has and still be missing 44% of them, and missing edges attenuate
degree, flatten tails, destroy hub persistence and break cycles -- the inputs to LAW-1, LAW-3, LAW-4, LAW-5 and
LAW-6. LAW-3 finding nothing is exactly what a coverage gap would produce.

Nothing here is a reason to stop, and more repos do not help: coverage is a property of the language and the
engine, not the sample. What it means is that an amendment should (a) report `share_confident_of_repo_links` per
panel repo beside every law, (b) say in advance that a between-language difference is not interpretable where
coverage differs by more than some stated margin, and (c) treat the C-versus-rest gap as a stated limitation of
the universality claim rather than something the panel averages away. I would put that in before the draw.

## Per-repo effects

| law | commons-lang (java) | prometheus (go) | sphinx (python) | libgit2 (c) | libxml2 (c) |
|---|---|---|---|---|---|
| LAW-1 heavy tails | +0.113 ± 0.058 | +0.088 ± 0.017 | +0.100 ± 0.019 | +0.184 ± 0.040 | +0.062 ± 0.034 |
| LAW-2 attachment | +1.237 ± 0.066 | +1.492 ± 0.168 | +1.788 ± 0.077 | +1.310 ± 0.030 | +1.272 ± 0.037 |
| LAW-3 hub persistence | +0.000 ± 0.002 | +0.044 ± 0.031 | +0.124 ± 0.044 | +0.013 ± 0.011 | −0.006 ± 0.005 |
| LAW-4 centralisation | +0.025 ± 0.003 | +0.015 ± 0.003 | −0.005 ± 0.006 | +0.004 ± 0.001 | +0.026 ± 0.003 |
| LAW-6 cycles → fixes | −0.019 ± 0.171 | −0.002 ± 0.171 | −0.393 ± 0.265 | −0.350 ± 0.219 | not evaluable |
| LAW-8 prediction gain | +0.001 ± 0.013 | −0.001 ± 0.007 | −0.007 ± 0.004 | +0.003 ± 0.018 | +0.022 ± 0.008 |

LAW-5's conjunction (Q excess falling **and** PC excess rising) fails in all five: the predicted direction holds
nowhere. LAW-7's coupling attenuation runs +0.51 to +0.97 across the five, the only defect-law effect with a
consistent sign and size. LAW-9 is evaluable on libxml2 alone and does not hold there (`docs/laws_law9.md`).

Readings, all descriptive on five development repos:

- **LAW-2 is the strongest signal in the study** -- positive and large in every repo, 20 to 60 times its SE, and
  superlinear (probability ∝ (k+1)^α with α from 1.24 to 1.79; α = 1 is the Barabási-Albert case). It is also
  the law whose discriminating test is missing: see "What is still owed".
- **LAW-4's replay is a check on LAW-2's kernel, and it passes.** LAW-4 replays each repo's own history with only
  edge targets redrawn from the fitted LAW-2 kernel, and reproduces the observed in-degree Gini to within 0.026
  everywhere (0.4754 → 0.4507, 0.4389 → 0.4238, 0.5121 → 0.5165, 0.6255 → 0.6219, 0.5814 → 0.5558). A kernel
  that regenerates the inequality actually present in the code is better evidence than its own p-value. It also
  answers the obvious objection to a superlinear α: if attachment really ran away, the replay would overshoot
  the observed concentration, and it does not.
- **LAW-6 points the wrong way in all four evaluable repos** (−0.019, −0.002, −0.393, −0.350) and never
  significantly. In-cycle files get *fewer* later fixes here, not more.
- **LAW-8 is ~0 as predicted**, except libxml2 at +0.022 ± 0.008, which clears the 0.02 margin in one repo.

## Two things the synthesis itself showed

1. **At k = 2 the registered interval is useless, which is the case for k = 16.** C is the only language here
   with two repos. Its pool runs, but the 99% HKSJ interval spans ±63 standard errors at one degree of freedom:
   LAW-1 pools to +0.121 with [−3.76, +3.98]. That is HKSJ behaving correctly, and it is a concrete
   demonstration of why Amendment 3 committed to 16 rather than a handful. Every other language here has one
   repo, where no random-effects pool exists at all; the record reports the repo's own one-sided p, clearly not
   as a language result, and the universality test receives 1.0 for that language (not evaluable counts against
   and is not re-scaled).
2. **Two of LAW-9's three legs cannot enter the registered synthesis at all.** Their Hodges-Lehmann shift is
   exactly 0.00 with SE 0.00 (the degeneracy in `docs/laws_law9.md`), and a variance-weighted pool cannot take a
   zero variance. So the registered effect does not merely read oddly on tied counts -- it is unpoolable. That
   strengthens the recommendation already on the table: LAW-9's effect should be `P(cve smaller)`, which is
   defined and has a usable SE. It is a scorer-freeze decision, and nothing has been changed.

## What is still owed before the scorer hash is frozen

- **LAW-2's function-fixed-effects sensitivity and the PAFit cross-check** (`laws_attach.py` lists both as not
  done). This is now the highest-value gap in the scorer. Without fixed effects, α conflates preferential
  attachment with fitness heterogeneity -- "already-popular attracts more" against "intrinsically useful
  functions are both popular and keep attracting calls". Those are different mechanisms, LAW-2 is the law most
  likely to return a positive universal result, and the distinction is the difference between an interesting
  finding and a tautology. Changes after the pilot are allowed only before the panel draw.
- The coverage amendment above.
- The label audit, on the M6 workflow label (`docs/laws_defect_labels.md`), and the LAW-9 effect decision.
- Then the scorer hash.

## Re-run under Amendment 5 (the registered effects, not the old ones)

`laws_run_amend5.json`, 5 repos, all nine laws, **0 failures, 1,285 s** (up from 635 s: each repo now also
simulates 100 fitness-only histories for LAW-2). The scorer now reads what Amendment 5 registers -- LAW-2's
effect as the excess over its fitness null with `v = se_observed² + sd(alpha_null)²`, and LAW-9's as
`P(cve smaller)` against 0.5 with a bootstrap SE.

### LAW-2: the registered variance is far more conservative than the rank p

| repo | alpha | excess | SE of excess | excess / SE | rank p |
|---|---|---|---|---|---|
| sphinx | +1.788 | +0.429 | 0.079 | **5.4** | 0.0099 |
| libgit2 | +1.310 | +0.221 | 0.031 | **7.1** | 0.0099 |
| libxml2 | +1.272 | +0.133 | 0.038 | **3.5** | 0.0099 |
| prometheus | +1.492 | +0.221 | 0.169 | 1.3 | 0.0099 |
| commons-lang | +1.237 | +0.059 | 0.074 | 0.8 | 0.0396 |

**The rank p says "beyond fitness" in all five repos; the registered effect and variance say three of five.**
The two answer different questions. The rank p asks only whether any simulated history reached the observed
alpha -- and with 100 reps, four repos are at its 1/101 floor because none did. The variance-based test asks
whether the gap is large relative to the observed alpha's own uncertainty, which is the question the synthesis
pools. Where they disagree, the registered quantity governs, and it is the conservative one.

The gap is dominated by `se_observed`, not by the null: prometheus's alpha carries SE 0.168 against a null SD of
0.017, so its imprecision is in the attachment estimate itself. commons-lang is simply a small effect (+0.059).
So LAW-2's attachment component is clear in sphinx, libgit2 and libxml2, and not established in prometheus or
commons-lang -- a materially more cautious reading than `docs/laws_law2_fitness.md` gave from the rank p alone,
and the one the panel will be scored on.

### LAW-9: all three legs now enter the synthesis

With `se_p_smaller` from the same bootstrap, libxml2's three metrics are files 0.584 ± 0.022, functions
0.545 ± 0.031 and lines 0.516 ± 0.032. Under the old registered shift, two of the three had SE exactly 0 and
could not be pooled at all. Against the 0.5 null, files is 3.8 SE above it and the other two are not -- the law
is a conjunction, so it still does not hold, but it now fails for a readable reason rather than an undefined one.

### Matched coverage is now automatic

`--matched-coverage` adds a second pass over every law with each network thinned to `matched_share(repos)`: the
**minimum over languages of that language's median** `share_confident_of_repo_links`. A language is represented
by its typical repo, and the comparison is made at the quality of the worst-measured language, because that is
the only level every language can actually be measured at. On the pilot that is java's 0.556.
