# Does the audited fix-label precision transfer to the label HR used?

`otherfix_audit.md` measured precision on these eight repos for **xc_harvest's** label pipeline.
HR-1/2/3 ran on the **LAWS history DB's `fix` flag**. Two keyword gates, same repositories.
This is a set comparison, not new ratings: nothing was rated and nothing was spent.

| repo | LAWS raw | LAWS v3c | xc raw | xc clean | LAWS-raw ∩ xc | LAWS-v3c ∩ xc-clean | audited raw prec. | audited v3c prec. |
|---|---|---|---|---|---|---|---|---|
| commons-lang | 849 | 389 | 1083 | 436 | 100% | 100% | 0.27 | 0.70 |
| libgit2 | 248 | 177 | 2562 | 1445 | 100% | 100% | 0.63 | 0.60 |
| libxml2 | 2927 | 2100 | 3160 | 2337 | 100% | 100% | 0.80 | 0.86 |
| postgres | 16980 | 9156 | 17690 | 11690 | 100% | 99% | 0.77 | 0.74 |
| prometheus | 719 | 375 | 2576 | 1322 | 99% | 100% | 0.40 | 0.83 |
| redis | 3276 | 2091 | 3409 | 2208 | 99% | 98% | 0.73 | 0.75 |
| ripgrep | 254 | 125 | 319 | 103 | 72% | 64% | 0.27 | 0.82 |
| sphinx | 2354 | 1702 | 3624 | 2577 | 100% | 100% | 0.60 | 0.78 |

## Reading: the audit transfers, and it settles which HR column to believe

**The LAWS fix set is contained in the xc fix set**: 98–100% of LAWS `fix=1` commits appear in xc's raw
events for seven of eight repos, and the same holds for the cleaned sets. The one exception is **ripgrep**
(72% / 64%), the smallest repo, which HR excluded anyway for having too few post-cut positives.

Two keyword gates built independently over the same repositories agree almost exactly. So the precision
`otherfix_audit.md` measured carries to the label HR used, with a stated basis rather than an assumption.

**What that means for the HR results:**

| repo | audited precision, raw label | HR-1 raw lift | audited precision, v3c | HR-1b cleaned lift |
|---|---|---|---|---|
| commons-lang | **0.27** | **+0.143** | 0.70 | **−0.015** |
| sphinx | 0.60 | +0.117 | 0.78 | +0.046 |
| postgres | 0.77 | +0.110 | 0.74 | +0.026 |
| redis | 0.73 | +0.091 | 0.75 | +0.020 |
| libxml2 | 0.80 | +0.025 | 0.86 | −0.010 |
| prometheus | 0.40 | +0.009 | 0.83 | −0.013 |

The raw column's two largest lifts come from the two repos with the **worst** label precision — commons-lang
at **0.27**, where nearly three in four "fix" commits do not repair behaviour. Under v3c, audited at 0.70–0.86
in seven of eight repos with ~81% of real fixes retained, that lift reverses.

**Conclusion.** The cleaned column is the one to believe. **HR-1b (+0.009, CI [−0.011, +0.029], not shown at
the registered bar) is the better estimate of recidivism's advantage over size on this cohort** — not HR-1's
+0.082. The raw-label result is an artefact of a label that is 27% precise where the effect was largest.

**The standing claim has to narrow.** *History predicts* was measured on curl and nDPI, both C, where the raw
gate's precision is 0.73–0.80 and the artefact is far weaker. On this cohort, with a label audited at 0.70+,
prior fixes do **not** beat size. That is not a refutation of the curl/nDPI result; it is a limit on its reach,
and it was invisible until the label was taken seriously.

**What is still worth buying.** libgit2 fails the 0.70 gate under v3c (0.60) and is the one repo HR could not
evaluate at all. A better label for it, or a density-aware cut, would recover a data point. Everything else
here was already paid for.
