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
