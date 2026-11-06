# REG-H1..H2 — do regressions come from commits that leave co-change partners behind? — registered 2026-11-06, before any co-change statistic

**Why.** Regressions are not a property of files: XC-H5 found they never recur in place, and SC found no file metric
for them. They are a property of **changes**.

**Mechanism (designed first).** Files that historically change together share an unstated contract. A commit that
edits one side of that contract but not the other is more likely to break something. The predictor: the co-change
partners the commit *should* have touched but did not.

**What has been looked at.**
- The XC regression labels (curl 0.87, nDPI 0.77, openssl 0.73, harfbuzz 0.77 audited precision; libarchive withheld
  at 0.43).
- Their harvest reasons.
- **Never computed:** any co-change statistic, any commit-level predictor, or any inducing-commit join.

## Repos and labels

- **Repos:** curl, openssl, harfbuzz, nDPI. libarchive is excluded (regression labels withheld).
- **Inducing links.** From each XC regression event:
  - **(a) SHA reference:** the harvester's `references <sha>` reason. That is a fix-like commit naming a commit ≤ 90 d
    older that is its ancestor.
  - **(b) Revert:** the `This reverts commit <sha>` target in the event's body.
  - Regression-word-only events give no link and are not used.
- **Link gate (binding, before scoring).** The author audits 30 seeded (2982) links per repo, or all if fewer: does the
  fix repair (or revert) the linked commit? Below 0.70, the repo is withheld.
- **Positive.** A candidate commit linked as inducing by a regression event dated within 90 d after it.

## Unit and predictors

- **Candidates.** Non-merge commits reachable from the walk head that touch 1–50 C/C++ files (the repo's extensions).
  - From the first commit date + 730 d (so two years of history exist) to head − 90 d.
- **Co-change model, history only.** Over the 730 days before commit c, from candidate-qualifying commits:
  - n(f) = commits touching file f;
  - n(f, g) = commits touching both f and g;
  - conf(f → g) = n(f, g) / n(f).
  - A **strong partner** of f has n(f, g) ≥ 3 and conf(f → g) ≥ 0.5.
- **Scores for commit c with touched set T:**
  - **CCO (co-change omission)** = mean over f ∈ T of Σ conf(f → g), over strong partners g ∉ T. That is the expected
    number of missing partners per touched file.
  - **DEG (placebo: "touches coupled files")** = mean over f ∈ T of Σ conf(f → g), over *all* strong partners g, touched
    or not.
  - **Size** = lines added + deleted (git numstat, candidate files only).

## Claims

Stratified AUC: pairs compared only within the same one of 20 equal-count bins of commit size, pooled by pair count
(ties ½).

| id | claim | quantity | supported iff |
|---|---|---|---|
| **REG-H1** | omission predicts regression-inducing commits beyond size | stratAUC(CCO) − stratAUC(size), within 20 size bins | mean > 0, one-sided lo > 0 |
| **REG-H2** | it is the *omission*, not merely touching coupled files | stratAUC(CCO) − stratAUC(DEG), same bins | mean > 0, lo > 0 |

**Tests.**
- Per repo: commit bootstrap (5,000 rounds, seed 2982); the size bins are fixed on the full sample.
- Pooled: the mean of per-repo values with equal weight; the bootstrap resamples within repos.
- α = 0.01 / 2 one-sided, on the **pooled** claim. Per-repo results are descriptive.
- A repo with < 30 positives is not evaluable.
- Equivalence null: 90% CI inside [−0.02, +0.02].

**Headline.** The mechanism is **shown** iff REG-H1 and REG-H2 are both SUPPORTED, pooled, with no evaluable repo's
REG-H1 point estimate below 0.

**Descriptive.**
- Raw AUCs of size, number of files touched, CCO and DEG.
- The share of inducing commits with CCO > 0, against non-inducing.

## Priors

- REG-H1 **uncertain**: commit size is a strong JIT predictor, and omission may track it.
- REG-H2 **uncertain**.
- The literature has co-change "missed partner" heuristics (logical coupling, the ROSE line of work). The test here is
  whether they predict regressions beyond size, out of history alone.

---

## Results — 2026-11-06 (labels `c533b67`; scorer `176bcb6` committed before running; report `reg.md`)

**Data.** 64,820 candidate commits; 1,199 regression-inducing (curl 681, openssl 229, harfbuzz 243, nDPI 46). All four
repos are evaluable; the link audit passed at 0.77–0.87 (`reg_link_audit.md`).

| claim | pooled mean | lo (α = 0.005) | 90% CI | verdict |
|---|---:|---:|---|---|
| **REG-H1** omission − size, within size bins | −0.012 | −0.051 | [−0.037, +0.015] | **not supported (inconclusive)** |
| **REG-H2** omission − coupled-files placebo | −0.002 | −0.020 | [−0.013, +0.009] | **replicated null (equivalence)** |

Per repo, H1 is −0.005 (curl), −0.029 (openssl), −0.035 (harfbuzz) and +0.023 (nDPI). The headline's extra condition
(no evaluable repo below 0) is not met either.

**Headline → the co-change-omission mechanism is NOT shown.**
- Omission adds nothing over commit size.
- Omission is indistinguishable from simply touching well-coupled files. H2 is an equivalence null: proven ≈ 0, not
  just unproven.
- Inducing commits do more often leave a partner behind (curl 38% vs 27%; openssl 40% vs 35%), but that is because
  they are bigger. Within size bins the difference vanishes.

**What does predict them (descriptive).** Commit size, the just-in-time defect-prediction staple: raw AUC 0.70 on curl
and 0.64 on openssl. Files touched is close behind. harfbuzz's labels are mostly reverts of optimisation attempts, and
nothing predicts them (size 0.52).

**What it means for the method.** Designing from a mechanism is necessary, not sufficient. "Unstated contracts between
co-changing files" was a plausible cause, but at commit grain it carries no information beyond how big the change is.
Two mechanism-first designs held (ENV, LIB), one did not (REG). That is what a real method looks like.
