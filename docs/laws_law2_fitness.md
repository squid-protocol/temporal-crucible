# LAW-2 beyond fitness: what alpha is actually measuring

Development data (the CGR practice repos), never panel results. Tools: `laws_attach.fit_fixed_effects`,
`laws_attach.fitness_null`, `laws_attach.kernel`. Numbers: `.../laws-study/pilot/law2_fitness.json`.

LAW-2 is the strongest signal in the study: alpha positive and large in every repo, 20 to 60 times its SE, and
robust to losing 43% of the edges (`docs/laws_coverage.md`). `laws_attach.py` listed two checks as not done -- the
function-fixed-effects sensitivity ("beyond fitness") and a PAFit cross-check. Both are now done, and the first
one does not work.

## The registered test cannot tell attachment from fitness

An intrinsically useful function is both already-called and keeps attracting calls. Preferential attachment says
a target's chance depends on its degree **now**; fitness heterogeneity says it depends on how attractive the
target is, full stop. Both produce a positive alpha.

How much? On a generator where attachment is switched off entirely and a target's chance depends only on a fixed
intrinsic fitness, the registered estimator reports **alpha = +1.09** -- larger than it reports for a true
attachment exponent of 1.0. So LAW-2's registered test, alpha against a margin of 0, does not test preferential
attachment. It tests whether calls concentrate at all.

alpha itself is fine: on the same generator it recovers a known exponent closely (true 0.0 -> -0.03,
0.5 -> +0.44, 1.0 -> +0.93, 1.5 -> +1.46). The problem is the margin, not the estimator.

## The fixed-effects sensitivity does not work at this data size

`fit_fixed_effects` puts a fixed effect on every target chosen at least twice, so alpha is identified only by
variation in a target's **own** degree over time. It is the textbook answer and it fails here:

| true alpha | alpha_plain | alpha_fe |
|---|---|---|
| 0.0 | −0.03 | **−0.84** |
| 0.5 | +0.44 | −0.21 |
| 1.0 | +0.93 | +0.25 |
| 1.5 | +1.46 | +0.86 |
| pure fitness (true 0.0) | +1.09 | **+0.23** |

Two things kill it. The bias is near −0.8, far larger than the effect under test; and **pure fitness and a true
exponent of 1.0 give the same alpha_fe** (+0.23 against +0.25), so it cannot discriminate at all. This is the
incidental-parameters problem: about 400 to 500 fixed effects against about 3,400 choices is roughly seven
observations each. The ridge penalty is not the cause -- the reading holds at 0.1, 1 and 10. The function is kept
because the registration asks for it, with its calibration in the tests, and **alpha_fe must never be read as an
exponent**.

## What works: a fitness-only null

`fitness_null` is the same idiom LAW-3, LAW-4 and LAW-5 already use. It keeps everything the observed history has
except the timing: each target's propensity is fixed at its **observed total intake** of new edges over the whole
history -- a fitness that by construction reproduces who ends up popular -- and the same callers make the same
number of choices in the same quarters, with the target redrawn from that fitness. Under the null a target's
chance never depends on its degree now. alpha is re-estimated on each simulated history with the same (unbiased)
estimator, and the observed alpha is read against that distribution. On the synthetic check it separates the two
cases cleanly: true attachment p < 0.05, pure fitness p > 0.05.

### On the pilot repos, 50 simulated histories each

| repo | language | alpha observed | null mean (sd) | excess | p | beyond fitness |
|---|---|---|---|---|---|---|
| sphinx | python | +1.788 ± 0.077 | +1.356 (0.013) | **+0.431** | 0.020 | yes |
| prometheus | go | +1.492 ± 0.168 | +1.271 (0.017) | **+0.221** | 0.020 | yes |
| libgit2 | c | +1.310 ± 0.030 | +1.090 (0.007) | **+0.220** | 0.020 | yes |
| libxml2 | c | +1.272 ± 0.037 | +1.139 (0.008) | **+0.133** | 0.020 | yes |
| commons-lang | java | +1.237 ± 0.066 | +1.170 (0.032) | **+0.066** | 0.039 | yes |

**Fitness explains most of alpha, and a real attachment component survives.** The null reproduces 1.09 to 1.36 of
an observed 1.24 to 1.79, so the part attributable to a target's degree *now* is only **+0.07 to +0.43 -- roughly
5% to 25% of the headline number**. It is positive in all five repos and exceeds the null in all five.

Two caveats pulling opposite ways:

- **The p-values are at their floor.** With 50 reps the smallest attainable p is 1/51 = 0.0196, and in four of the
  five repos *no* simulated history reached the observed alpha. More reps would sharpen them, not weaken them.
- **The null is conservative.** It calibrates each target's fitness to its *realised* intake, which attachment
  itself inflates -- fitness is credited with concentration that attachment may have produced. The excess is
  therefore a **lower bound** on the true attachment component.

## The kernel's shape holds up

`kernel` measures A(k) non-parametrically -- new edges to targets of degree k, over functions of degree k, pooled
over quarters -- then regresses log A on log(k + 1) with a quadratic term. It controls for nothing, so it is a
check on the functional form, not a rival estimate, and PAFit proper (the joint Bayesian kernel-and-fitness
estimate) is still owed.

| repo | slope | curvature | r² (log-linear) |
|---|---|---|---|
| commons-lang | +1.86 | +0.29 | 0.87 |
| sphinx | +1.66 | −0.16 | 0.96 |
| libgit2 | +1.46 | −0.07 | 0.91 |
| prometheus | +1.41 | +0.00 | 0.96 |
| libxml2 | +1.19 | −0.09 | 0.93 |

Slopes sit above the logit alpha, as they should when size and locality are uncontrolled. Curvature is small and
r² is 0.87 to 0.96, so `(k + 1)^alpha` is not badly misspecified; commons-lang is the weakest.

## What this means for the registration

1. **LAW-2's margin should be the fitness null, not zero.** As registered, a repo passes LAW-2 by having calls
   concentrate at all, which fitness alone achieves. The effect that answers the hypothesis is the excess over
   the null, and on this evidence it is an order of magnitude smaller than the raw alpha. This is the most
   consequential change on the pre-freeze list.
2. **alpha should not be reported as "the preferential attachment exponent."** 1.24 to 1.79 is mostly a statement
   that popular functions are popular. The paper should lead with the excess.
3. **The fixed-effects sensitivity should be recorded as attempted and uninformative**, with the calibration
   table, rather than quietly dropped.
4. Raise the null's reps above 50 so the p-values are not floored, and say so in the amendment.
5. PAFit proper is still owed if the owner wants a joint kernel-and-fitness estimate; `kernel` covers the shape
   question only.

Not wired into `tools/laws_run.py`: that file is changed by the open driver PR and this would conflict. The
driver should call `fitness_null` for LAW-2 once that merges.
