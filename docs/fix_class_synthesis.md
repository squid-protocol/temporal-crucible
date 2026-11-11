# What predicts a fix depends on which kind of fix it is (synthesis, 2026-11-11)

A standing one-line summary of this program has been *"history predicts, structure describes"*. That is true of
the **pooled** outcome and misleading about the parts. Pooled over all fixes, structure reduces to size; split by
fix class, each class has its own predictor, and for one class the predictor **is** structure.

This note collects results already scored elsewhere. It introduces no new statistic.

## The classes are different causes, not different severities

| class | what it is | what predicts it | evidence |
|---|---|---|---|
| **extrinsic** | the outside world moved — platform, compiler, a dependency | **structure**: platform-conditional `#if` density; library-coupling surface | ENV-H1..H3, survives on unseen harfbuzz + libarchive, **+0.17 / +0.12 over the stronger size order**, and *worse* than size for every other class. LIB-H1..H3: +0.40 over size on 21 (repo, library) units — the strongest structural result in the program |
| **regression** | we broke it ourselves, recently | **recent change**: commit size; fix activity nearby. Never recurs in place | REG-H1/H2: co-change omission adds nothing over commit size |
| **latent** | a dormant defect someone finally noticed | **recurrence in place + expressed human foresight** | XC-H1..H6: CVEs recur in place 3/3. SCAR-I2: danger comments at birth predict a first CVE at 1.55× even with no CVE history. DCS: *nothing* the engine measures at birth separates them |
| **other-fix** | everything else — **85–97% of all outcome mass** | size and history, weakly | the class audit: 0.38 precise outside C before FIXLIKE v3c, 0.761 after |

**Why the pooled claim comes out as it does.** The structural signal that exists is specific to a small class,
and `other-fix` carries 85–97% of the events. Pooling drowns it. That is a property of the mixture, not of
structure.

## The ceiling is class-specific too

From `docs/ceil.md` (v1 labels; recall@20%-of-lines, out of repo):

| arm | dispersion α | realized | attainable | **rate oracle** | unexplained headroom |
|---|---|---|---|---|---|
| all classes | 1.281 | 0.366 | 0.451 | **0.661** | +0.210 |
| **regression** | **1.589** | 0.371 | 0.434 | **0.711** | **+0.277** |
| other-fix | 1.217 | 0.405 | 0.475 | 0.665 | +0.209 |

Regressions are the most concentrated class and have the highest ceiling in principle, yet are predicted no
better than anything else — **the largest unexploited gap in the program sits there**. (The ladder has no latent
or extrinsic arms: those classes are too small in that frame — curl has 185 latent events against 6,417
other-fix.)

## What this changes

1. **A single model over all fixes is the wrong shape.** Four causes, four predictors, one regression equation.
   A class-aware model can use covariates a pooled model cannot, because they only work for one class.
2. **Report structural results by class or not at all.** "Structure reduces to size" is a statement about the
   mixture; it is false for extrinsic fixes.
3. **It gives the attention hypothesis a falsifiable shape.** If the ceiling's residual is the discovery process,
   the benefit of an instrument that applies uniform attention must be **largest for latent** fixes (dormant;
   found only by looking) and **near zero for regression** (self-announcing: a test or a user reports it).
   Registered in advance as **AIAT-P7** (`docs/aiat_hypotheses.md` §8b), before any file was scored.

## What it does not establish

The class labels are themselves measured, with known precision (`docs/xc_label_audit.md`; `other-fix` 0.761 after
v3c). The per-class predictors above come from two to four repos each, not from the LAWS panel, so they are
development-set evidence. Nothing here is a new verdict.
