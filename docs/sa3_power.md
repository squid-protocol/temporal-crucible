# SA3 power statement (2026-11-14) — written before any real predictor is scored against an outcome

From `docs/sa3_placebo.json`, 15 drawn repos, primary outcome HP, Holm-first interval (98.33% two-sided), 80%
power. The smallest detectable **mean effect** (bAUC − 0.5, averaged over repos):

| null spread taken from | repos do not differ | between-repo SD 0.02 | 0.04 | 0.05 | 0.08 |
|---|---|---|---|---|---|
| path-hash placebo (a predictor with no directory structure) | 0.032 | 0.037 | 0.049 | 0.056 | 0.080 |
| directory-hash placebo (a predictor that clusters by directory) | 0.056 | 0.059 | 0.067 | 0.072 | 0.092 |

**How to read it.** The registered test is a t-interval over repos, so its width is set by how much repos
differ, not by how many files they hold. An independent review measured that spread on these same outcomes
with four non-structural file attributes (bytes, path depth, name length, directory size) and found a
standard error of the study mean of 0.012 to 0.020 — which corresponds to the right-hand columns, not the
left. That is a proxy for structural predictors, not a measurement of them.

**So: a "not detected" rules out a mean effect above roughly 0.05 to 0.08, and says nothing about smaller
ones.** For scale, 0.05 means that among two files of matched size, one later tied to a fix and one not, the
measure is higher in the fixed one 55% of the time.

The label is also low-recall and, in django and mediawiki, closer to "has a ticket" than "is a defect"
(sampled precision 73 to 81%), which shrinks any true effect before it is measured.

The gates passed (Amendment 4): all four size surrogates and both hash placebos lie within 0.005 of zero.
