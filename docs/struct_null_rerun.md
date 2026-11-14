# Structural nulls re-run under the cascade label (2026-11-13)

`attenuation.py` argued our structural nulls were weakly identified and deserved a re-run against a better
outcome. This is that re-run. `tools/struct_null.py` compares call-graph in-degree against LOC at the same
cut, on the same files, with only the outcome label swapped.

## Result: call-graph centrality beats size in HALF the repos and loses in the other half

In-degree lift over LOC (`*` = bootstrap 95% CI excludes zero):

| repo | raw | v3c | **cascade** |
|---|---|---|---|
| commons-lang | +0.115\* | +0.051\* | **+0.051\*** |
| ndpi | +0.113\* | −0.030 | **+0.118\*** |
| prometheus | +0.064\* | +0.059\* | **+0.060\*** |
| sphinx | −0.020 | +0.037\* | **+0.037\*** |
| curl | **+0.048\*** | −0.047\* | **−0.036\*** |
| postgres | −0.030\* | −0.035\* | **−0.039\*** |
| redis | −0.048\* | −0.067\* | **−0.063\*** |
| libxml2 | −0.217\* | −0.064\* | **−0.084\*** |

Under the cascade label **all eight repos show a significant effect — four positive, four negative.** The
pooled mean is **+0.006**, a textbook null. **No repo is anywhere near it**: the smallest magnitude is 0.036.

## The standing claim was a pooling artefact

"Aggregate structural exposure reduces to size" is what you get by **averaging eight significant effects
whose signs disagree**. It is not a description of any repository in the corpus. Centrality genuinely
predicts fixes beyond size in commons-lang, ndpi, prometheus and sphinx, and is genuinely anti-predictive in
curl, postgres, redis and libxml2.

This is the same lesson arriving for the third time today from three directions: our per-repo nulls (τ
0.58–1.29), repowise's mixed-effects repo SD ≈ 1.19 on the odds scale, and now a sign split. **Pooling across
repositories is not valid in this corpus**, and every pooled estimate in this programme inherits the problem.

## A correction to yesterday's attenuation argument

I predicted that a better label would reveal structural effects **uniformly larger**. That is not what
happened. The label **changed the sign** in curl (+0.048 raw → −0.036 cascade) and rescued sphinx from a null
(−0.020 → +0.037). A pure attenuation model cannot do that — it assumes error independent of the predictor.
The data says the label error is **differential with respect to structure, and differently so per repo.**

So the attenuation estimate (~30% transmitted) stands as a *magnitude* guide and fails as a *sign* guide.
Structural results measured on the raw label cannot be trusted for direction, which is a stronger warning
than the one I gave.

## Also measured: what each label costs

LOC's own AUC rises as the label gets cleaner — curl 0.621 raw → 0.833 v3c → 0.764 cascade. The noisy
label's extra positives sit in files size does **not** predict, so raw-label studies understate how much of
the outcome is plain size.

**v3c trades away power.** On ndpi it cut positives 266 → 57 and widened the CI to [−0.092, +0.029] — ndpi's
v3c null is a power failure, not an absence of effect, and the cascade label (260 positives) recovers the
effect at +0.118. **Cascade is the better instrument**: it keeps the positive count while ranking mechanism
anchors above prose.

## Limits

- **One structural metric.** In-degree is call-graph centrality, not the crucible's full exposure suite, so
  this tests the *mechanism* behind the claim rather than retiring the claim's own numbers.
- Out-degree and function count lose to LOC in every repo under every label (−0.11 to −0.15). The positive
  result is specific to in-degree.
- LOC's AUC is already 0.76–0.91 in most repos; there is little headroom, which compresses every lift.
- ripgrep and libgit2 fell under the positives floor and are excluded.
- Cascade recall is still unmeasured, so "better label" means better precision and better anchor ranking,
  not demonstrated better recall.

## What this changes

1. **Retire the pooled structural null.** Report per-repo signs with CIs; a corpus mean over disagreeing
   signs is not a finding.
2. **The interesting question changed.** Not "does structure predict defects" — it does, in half these
   repos — but **"what distinguishes a repo where centrality predicts from one where it is
   anti-predictive?"** Four and four is a usable design.
3. **Re-run the crucible's own structural claims per repo before trusting them**, since the ones that
   reported pooled nulls are the most likely to be hiding exactly this split.
