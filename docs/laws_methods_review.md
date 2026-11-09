# LAWS registration: methods review (pre-data)

Reviewer: independent methods review, 2026-11-08 (US Eastern), of `docs/laws_hypotheses.md` at temporal-crucible
`a2c2c9c`, read with `cgt_hypotheses.md`, `cgn_hypotheses.md`, `acc_hypotheses.md` (branch `acc/registration`,
`4a44e9a`), `tools/cgt_eval.py` (`parse_calls`, `network`) and `tools/xc_harvest.py` (the fix-label rules).
No data exist yet, so everything below can still go in as a pre-data amendment.

**Overall assessment.** The study is worth doing, and some of its choices would satisfy a Registered Reports panel
as they stand: registering before the draw, a frozen engine, null models attached to the network claims, forward
validation, and publishing every per-repo estimate. A Stage-1 panel at MSR or TSE would still return it as **major
revision**, for three reasons:

1. The synthesis has no defined per-repo sampling variances. It uses DerSimonian–Laird with k = 8, and the
   "universal" and Holm rules are not formally defined, so most laws have low and unstated power.
2. The instrument (name-based resolution) and the labels (keyword rules) have errors that are likely to differ by
   language, by era and by file size. The ACC gate as designed cannot detect them: it is one repo per language, one
   snapshot, and a development repo.
3. Several nulls cannot separate the law from a trivial artefact. LAW-1 is tested against an exponential. LAW-4's
   uniform-growth null is beaten by any LAW-2 result. LAW-3 compares two measures that differ in volatility, not
   in "importance". The defect laws also include test files as units.

All of these can be fixed before data collection. Section (a) lists them in rank order, each with amendment text
ready to paste.

---

## (a) Must-fix before data collection (ranked)

### M1. Every per-repo effect needs a defined estimator and sampling variance; replace DL with REML + Hartung–Knapp; register a power analysis

**Problem.** A random-effects model needs a within-repo variance v_i for each effect. None is registered.

- LAW-1's effect ("the ratio favouring the better heavy-tailed fit") is not defined at all. If it means the
  normalised Vuong statistic, that is a z-score that grows with √n_tail, so pooling it measures how big the repos
  are, not how heavy their tails are.
- LAW-3 and LAW-4 (differences of shares and Ginis), LAW-5 (Kendall τ over 8–30 autocorrelated yearly points),
  LAW-7 (a ratio of log ORs) and LAW-8 (a mean over test years) all lack a stated SE.
- With k ≈ 8, DL underestimates τ² and its Wald CIs are anti-conservative (IntHout, Ioannidis & Borm 2014 BMC Med
  Res Methodol [k]; Langan et al. 2019 Res Synth Methods [k]).

**Rough power at the registered 99% two-sided bar** (normal-theory, k repos; δ = pooled mean / √(τ² + v̄), i.e. the
mean effect in units of the total between-repo spread):

| k | δ = 0.5 | 0.8 | 1.0 | 1.25 | 1.5 | 2.0 |
|---|---|---|---|---|---|---|
| 5 (min evaluable) | 0.03 | 0.08 | 0.13 | 0.21 | 0.31 | 0.55 |
| **8** | 0.07 | 0.21 | 0.35 | 0.55 | 0.74 | 0.95 |
| 16 | 0.21 | 0.61 | 0.83 | 0.97 | 1.00 | 1.00 |
| 32 | 0.54 | 0.96 | 1.00 | 1.00 | 1.00 | 1.00 |

(Hartung–Knapp t_{k−1}. Under DL's z the k = 8 row reads 0.12 / 0.38 / 0.60 / 0.83, which is exactly the
anti-conservatism problem.)

What this means:

- With 8 repos, a law "holds in a language" with ≥ 80% power only if its mean effect is about 1.6 or more times the
  between-repo SD. That is plausible for LAW-1 and maybe LAW-2. It is implausible for the defect laws, where this
  programme has already found project-specific effects (CPL, CEN, the size wall).
- If each language holds with probability p, the universal rule (≥ 3 of 4) passes with probability 4p³(1−p) + p⁴:
  0.31 at p = 0.5, 0.48 at p = 0.6, 0.82 at p = 0.8.
- So a null "universal" verdict on LAW-6 to LAW-9 will be uninformative unless this is said in advance.

**Amendment text.**
> *Synthesis (replaces "DerSimonian–Laird").* Within each language, repo effects are pooled with a random-effects
> model, τ² by REML (Paule–Mandel if REML fails to converge), and CIs by Hartung–Knapp–Sidik–Jonkman with the
> ad-hoc variance correction (no HKSJ CI narrower than the DL CI). The 95% prediction interval is reported with
> every pooled effect. Each law's per-repo estimator and its variance are fixed as follows: LAW-1 per M5; LAW-2 the
> discrete-choice α̂ with its model-based SE (M5); LAW-3, LAW-4 and LAW-5 a stratified bootstrap over snapshot pairs
> / simulation replicates / blocks of 2 years (1,000 resamples, seed 2982); LAW-6 and LAW-7 the cluster-robust
> SE (M7); LAW-8 the SD of the per-test-year gains divided by √(number of test years), inflated by the lag-1
> autocorrelation factor √((1+ρ̂)/(1−ρ̂)). A repo with no finite variance for a law is not evaluable for that law.
> The registration includes, before the draw, a power table (as above) and the smallest effect each law can detect
> at 80% power with k = 8. Any law whose plausible effect is below that is labelled *descriptive* now, not after
> the data. As a sensitivity analysis, DL and a Bayesian half-normal(τ) prior on the log scale are reported.

**Also consider (strongly):** 12 repos per confirmatory language instead of 8. The δ = 1.0 column goes from 0.35 to
about 0.65. The cost is 16 more repos, and the panel is the cheap part next to labels.

### M2. The universal rule and Holm are not defined as tests; replace them with a partial-conjunction p-value per law

**Problem.** "Holds in ≥ 3 of 4 languages and none significantly opposite" is a rule, not a p-value, so Holm
cannot be applied to it. It is also unspecified what counts when a language is not evaluable (< 5 repos) or is
ACC-failed and therefore descriptive. Several thresholds are not zero (LAW-7's 0.5, LAW-8's 0.02), but the text
says "excludes the null". And LAW-8 is predicted to *fail*, yet the registered test can only fail to reject.
That is absence of evidence, not evidence of absence.

**Amendment text.**
> For each law and confirmatory language, p_ℓ is the one-sided HKSJ p-value of the pooled effect against the law's
> stated margin (0 unless stated; LAW-7: 0.5; LAW-8: 0.02). A law is **universal** iff the Benjamini–Heller (2008)
> partial-conjunction p-value for "at least 3 of the 4 confirmatory languages", p^{3/4} = 2·p_(3) (Bonferroni
> combining, valid under any dependence), survives Holm at family-wise α = 0.01 across the nine laws, **and** no
> language's pooled effect is opposite at one-sided p < 0.01. A language that is not evaluable or ACC-failed for a
> law contributes p_ℓ = 1 (it counts against universality); the analysis is not re-scaled to "3 of 3".
> Per-language "holds" verdicts use one-sided α = 0.005 (≡ the registered 99% CI). They are reported with the
> count of language × law tests (36), and the expected number of false positives (0.18) is stated beside them.
> **Absence claims** (LAW-8 "fails", any law reported as "does not hold") require an equivalence test: TOST with
> margins registered now (LAW-8: gain in recall@20% LOC within ±0.02; LAW-6 and LAW-7: |log OR| < 0.10). Otherwise
> the verdict is "inconclusive", never "fails".
> Within-law conjunctions (LAW-5 "both", LAW-9 "each") are intersection-union tests and need no correction.
> LAW-7's three metrics are a conjunction (all three must exceed the margin).

### M3. Exclude tests, vendored, generated and example code, and define the node set per language

**Problem.** The registration inherits CGT's network, whose node set is "functions with loc ≥ 3 in C/C++ files".
LAWS never states the per-language extension sets or exclusions.

- **Tests:** test functions (Go `_test.go`, Java `src/test/`, Python `tests/`, `test_*.py`) are the heaviest
  callers of production code. They inflate in-degree, create hubs (assertion helpers), and add cross-directory
  edges, which lowers Q.
- **Fix commits:** most fix commits add or edit a test. Test files therefore become positive file-years in LAW-6
  to LAW-8, and LAW-9's "files touched" counts test files.
- **Vendored and generated code:** vendored trees (`vendor/`, `third_party/`, `node_modules/`, linguist-vendored)
  and generated code (`*.pb.go`, `*_pb2.py`, ANTLR/yacc output, `// Code generated … DO NOT EDIT.`) arrive and
  leave in jumps. They manufacture rewiring, centralisation and "decay" events.
- **Engine scope:** the 60% language share is computed by linguist, which already excludes vendored and generated
  files. The engine does not.

**Amendment text.**
> **Units.** Per language, source files are: C `.c .h`; C++ `.cc .cpp .cxx .hh .hpp .h` (a `.h` belongs to the
> language that is the majority in its directory); Java `.java`; Go `.go`; Python `.py`; JS/TS
> `.js .jsx .mjs .cjs .ts .tsx`; C# `.cs`. Excluded from every network, unit and fix-size count:
>
> - (i) paths matched by GitHub linguist's `vendor.yml` and `documentation.yml` at the pinned linguist version, plus
>   the repo's own `.gitattributes` `linguist-vendored` / `linguist-generated` at each snapshot;
> - (ii) generated files (linguist `generated.rb` heuristics, plus any file whose first 5 lines match
>   `(?i)(code generated|autogenerated|do not edit)`);
> - (iii) test code: files under any path component `test`, `tests`, `testing`, `__tests__`, `spec`, `testdata`,
>   `src/test`, or named `*_test.go`, `test_*.py`, `*_test.py`, `*Test.java`, `*Tests.java`, `*.test.[jt]s`,
>   `*.spec.[jt]s`;
> - (iv) `examples/`, `example/`, `samples/`, `benchmarks/`, `bench/`, `docs/`.
>
> A **sensitivity analysis with test code included as callers only** (edges from tests count, test files are never
> units) is reported for LAW-1 to LAW-5. Fix commits whose changed source files are all excluded files do not
> count as fixes.

### M4. The ACC gate cannot vouch for the panel; re-specify ACC for the panel and for change over time

**Problem.**

- **One development repo per language, one snapshot.** ACC-H3 is run on one repo for Java, Go and Python, and two
  for C, all from the *excluded* development set, each at its latest snapshot. Its "in every repo evaluated" is
  then n = 1. A gate measured on prometheus @ 2026 says little about a random Go repo in 2016.
- **Error that drifts with language features.** Several laws (LAW-2, LAW-4, LAW-5, the rewiring covariate in LAW-8)
  are about *change*. For those the threat is extractor error that drifts as the language evolves: Java 8
  lambdas/method references (2014+), Python decorators, async and type hints, Go generics (1.18, 2022), TS
  adoption, C++11 lambdas. A rising unresolved-call share produces a spurious "decay" or "centralisation" trend.
  ACC-H3 does not measure this.
- **Resolution artefacts visible in `tools/cgt_eval.py`.**
  - `parse_calls` keeps only the last token after `.`, `::` or `->`. `network` resolves same-file first, else only
    names unique in the snapshot.
  - Node identity is (path, name). This merges Java overloads, same-named methods of different classes in one file,
    and Go methods with one name on different receivers (`String`, `Error`).
  - Same-file-first sends `list.add(x)` in a Java file that defines its own `add` to that local method. That is a
    false intra-file edge, and it inflates directory modularity (LAW-5).
  - The unique-name rule drops exactly the most-called names in OO code (`get`, `add`, `run`, `close`, `__init__`,
    `toString`, `New`). The in-degree tail is truncated where OO hubs live.
  - Cross-language differences in LAW-1, LAW-3 and LAW-4 may therefore be differences in resolution, not in
    languages.

**Amendment text.**
> **ACC-P (panel accuracy, run before any law statistic, results blind to law outcomes).** For each confirmatory
> language, 2 panel repos are drawn at random (seed 2982) from the 8. For each, the language's ACC oracle is run on
> the snapshot nearest the panel's first quarter and the 2026-10-01 snapshot (4 oracle runs per language). The ACC
> statistics are computed: direct-call P/R, in-degree Spearman, hub Jaccard, file-coupling κ. Additionally:
>
> - (a) the oracle-vs-engine **difference in the year-on-year change** of each law statistic (Gini, Q − Q_null,
>   propagation cost, α), with the ratio |Δ_engine − Δ_oracle| / |Δ_oracle| reported;
> - (b) per snapshot and per language for the whole panel, the **resolution profile**: share of call tokens
>   resolved, dropped as ambiguous, dropped as external, and the share of nodes merged by (path, name).
>
> A language is confirmatory for LAW-2/4/5 only if ACC-H3 holds on ACC-P as well as on the development repos,
> **and** the resolution-profile share resolved has |Kendall τ over time| < 0.3 in ≥ 6 of 8 repos (otherwise the
> resolved share is entered as a covariate and the law is descriptive). Only agreement statistics are output from
> ACC-P; no law statistic is computed on oracle graphs.
> **Node identity** is (path, enclosing class/receiver if the engine emits it, name). If the engine at `8f96d76ba`
> cannot emit the enclosing scope for a language, the merge rate is reported and LAW-1/3 are descriptive for that
> language when the merge rate > 10%.
> Where Python's PyCG cannot run on a panel snapshot, the failure is recorded and Python is descriptive for every
> network law. No substitute oracle is chosen after the fact.

### M5. Replace the nulls in LAW-1, LAW-2, LAW-3 and LAW-4 with tests that a trivial artefact cannot pass

**LAW-1 (heavy tails).** Almost any over-dispersed count distribution beats an exponential on a likelihood ratio.
"Heavy-tailed vs exponential" is near-certain and uninformative. CSN on discrete data also needs a discrete MLE,
an x_min chosen by KS, and a bootstrap goodness-of-fit. With a free x_min, a "tail" of 30 nodes is too easy.
Broido & Clauset (2019, Nat. Commun. [k]) give a graded classification that reviewers will expect.

> *LAW-1 amended.* Per repo, latest snapshot, in-degree k ≥ 1:
>
> - Fit a discrete power law by CSN (x_min by KS, n_tail ≥ 50 required, else not evaluable).
> - Run a goodness-of-fit bootstrap (1,000, seed 2982) and Vuong LR tests of the power law against exponential,
>   log-normal, stretched exponential and power law with exponential cutoff.
> - **Effect** = per-node LR of the better of {log-normal, power law, truncated power law} vs exponential,
>   ℓ̂ = LR / n_tail, with bootstrap SE. Margin 0.
> - **Strength class** (descriptive, Broido–Clauset): *weak* = PL GOF p ≥ 0.1; *strong* = weak + n_tail ≥ 50 +
>   2 < α̂ < 3 + PL not worse than any alternative.
> - Also report the tail fraction n_tail / n. The confirmatory claim adds a coverage condition: tail fraction ≥ 0.05.
> - The confirmatory effect is ℓ̂ of the better heavy tail vs a zero-truncated **negative binomial** (the
>   standard over-dispersed but light-tailed count model), not vs the exponential. The exponential comparison is
>   descriptive.

**LAW-2 (preferential attachment).** A Jeong-style binned kernel fitted with α against 0 has three known problems:

- Heterogeneous intrinsic fitness (a utility function is born attractive) yields α̂ > 0 with no preferential
  mechanism at all (Pham, Sheridan & Shimodaira 2015, PLoS ONE / PAFit [k]).
- Binning and k = 0 handling bias α̂. Removed edges are ignored.
- Locality is a large competing driver: new calls go mostly to the same file or directory, and hubs sit in large
  files.

> *LAW-2 amended.* Each new edge (u → v) between consecutive quarterly snapshots, with v persisting, is a choice
> among all persisting candidate targets at t (sampled: v plus 50 random non-targets, Overgoor, Benson & Ugander
> 2019 WWW "Choosing to grow a graph" [k]). Conditional logit:
> P(v) ∝ exp(α·log(k_v,t + 1) + β₁·same-file(u,v) + β₂·same-directory(u,v) + β₃·log LOC_v + β₄·log(1 + age_v)).
> In-degree k_v,t is at snapshot t (start of the interval).
> **Effect** = α̂ (SE from the model, clustered by quarter). Null margin 0. α ≈ 1 descriptive.
> **Fitness control (sensitivity, confirmatory for "beyond fitness"):** add function fixed effects (within-function
> identification: does a given function attract more edges when its own in-degree is higher?). Report both. The
> law is "preferential attachment beyond fitness" only if the fixed-effect α̂ > 0.
> PAFit joint estimates are reported for 2 repos per language as a cross-check.

**LAW-3 (hubs persist beyond size).** Comparing in-degree rank persistence with LOC rank persistence compares two
measures of very different volatility. LAT found that 71% of functions never change shape, so a LOC rank is close
to a fixed attribute and LOC persistence will be near 1 whatever hubs do. The sign of the effect is close to
pre-determined (≤ 0), and it says nothing about "importance".

Two further problems:

- The 1% / 5% cut-offs on integer in-degree have heavy ties and no registered tie rule.
- In small repos, "top 1%" is three functions.

> *LAW-3 amended.*
>
> - Per repo, yearly snapshot pairs 5 years apart, persisting functions only: **effect** = observed share of top-1%
>   hubs (≥ 10 functions, else not evaluable; ties at the cut broken by including all tied, with the share weighted
>   1/tie-size) still in the top 5% at t + 5, **minus** the same share under a **target-randomised null**.
> - The null takes the observed edge additions and removals among persisting functions between t and t + 5 and
>   reassigns each *added* edge's target uniformly among persisting functions (removals kept). Then hub status is
>   recomputed (200 replicates).
> - Hub survival (hub vs non-hub, matched on LOC decile) is reported separately as descriptive, so "persistence" is
>   not conditioned on a selection the claim then ignores.
> - The LOC comparison is reported as descriptive.

**LAW-4 (centralisation beyond growth).** The simulation starts from the first snapshot's (already unequal) graph
and adds edges uniformly. That dilutes inequality, so *any* preferential mechanism, i.e. LAW-2, makes observed
Gini > simulated. LAW-4 is then not a separate law, and its "pass" is implied by LAW-2.

The simulation also does not say how removals, new nodes' out-degree and edges from persisting callers are
handled. Gini over in-degree is dominated by the zero mass, which depends on resolution (M4).

> *LAW-4 amended.* Effect = observed Gini(k ≥ 1 and k ≥ 0 both reported; k ≥ 1 headline) at the last snapshot minus
> mean Gini of 200 simulations from the first snapshot that replay, per quarter, the **observed** node births and
> deaths, edge removals (same edges), and edge additions with each new edge's source fixed and its target drawn by
> the repo's **own fitted LAW-2 kernel** (α̂, with locality terms). The claim is "centralisation beyond the repo's
> own attachment process"; the uniform-attachment version is reported as descriptive (it is implied by LAW-2).
> SE = SD of simulated Gini.

### M6. Fix-label validity: measure recall as well as precision, size the audit for the gate, and handle GitHub workflows

**Problem.**

- **Labeller tuned for C mailing-list projects.** `xc_harvest.py` labels a non-merge commit as a fix if its
  message matches `fix(es|ed)?|bug|broke|…|leak|overflow|oops|restore`. In GitHub-workflow repos (most Java, Go,
  Python and JS panel repos), `Fixes #123` / `Closes #123` closes *any* issue type, features included. Conventional
  commits put `fix:` on lint, docs and test fixes.
- **Merge and squash workflows.** `--no-merges` drops merge commits. For merge-commit workflows it keeps the
  branch's commits, whose messages ("address review") carry no keyword. This is differential recall by workflow,
  and so by language.
- **Extrinsic rules are C-specific.** The extrinsic class's `_DEPS` list is C-library-specific (openssl, zlib, …),
  and the regression rule (revert, or the word "regress", or a SHA reference ≤ 90 d) is untested outside C.
- **The 70% gate is too noisy at n = 25.** The gate passes a class whose true precision is 60% with probability
  0.15, and fails a class at 80% with probability 0.11. The 95% CI at 18/25 is [0.51, 0.88].
- **Recall is never measured.** If recall varies with file size or activity, which keyword rules make likely, the
  defect laws inherit a size-correlated misclassification. That pushes towards exactly the "size confound" that
  LAW-7 tests.
- **The latent class is new and unvalidated.** OSV.dev "fixed" events are often bisection-derived (OSS-Fuzz) or
  point at a merge, a release-branch backport or a commit outside the default branch. That mapping needs its own
  validation.

**Amendment text.**
> **Label audit (before any network statistic).**
>
> - Per language and class, **50** commits (or all) are hand-labelled. The gate is the **lower 90% Clopper–Pearson
>   bound ≥ 0.60** with point estimate ≥ 0.70.
> - **Recall audit:** per language, 100 randomly drawn *unlabelled* commits touching source files are hand-labelled.
>   Fix recall is estimated, and recall is reported by file-size tercile of the files touched. If recall differs
>   between top and bottom terciles by > 15 points, LAW-6 and LAW-7 are descriptive in that language.
> - A second rater labels 20% of each audit set, blind to the first; Cohen's κ is reported. If raters are LLMs, the
>   model id, prompt and temperature are registered with the scorer.
>
> **Workflow handling.**
>
> - For repos where ≥ 30% of first-parent commits are merges, the unit is the **first-parent commit** (merge
>   or squash), labelled from the merge commit message plus the PR title and body. Where available, the linked
>   issue's labels are used (an issue labelled `bug`, `type: bug`, `kind/bug` or `defect` makes the fix label;
>   an issue with a `feature` / `enhancement` label suppresses a keyword-only fix label).
> - `Fixes|Closes|Resolves #N` alone is not a fix keyword.
> - Commits by bots (author/committer matching `\[bot\]|dependabot|renovate|github-actions`) are excluded from fix
>   labels, churn, author counts and change coupling.
>
> **Extrinsic** is descriptive outside C/C++ (its dependency list is C-specific).
> **OSV latent class:** a fix commit counts only if it is reachable from the default branch head (or is the
> default-branch commit that cherry-picks it, matched by patch-id). All 20+ such commits in two repos per language
> are hand-checked as security fixes, and OSV's precision is reported.
> **Time-varying label sensitivity:** OSV coverage before ~2016 is sparse. Defect models include calendar-year fixed
> effects, and LAW-9 reports CVE-fix counts by year.

### M7. Defect-model specification: censoring, deaths, clustering, the repo fixed-effect contradiction, separation, size-mechanical metrics

**Problems.**

- **Right-censoring and deaths.** File-years whose 365-day window runs past the last labelled commit are not
  stated to be dropped. Files deleted or renamed inside the window are a competing risk: a deleted file cannot be
  fixed.
- **First year.** The first snapshot year has no prior-year controls.
- **Non-independence.** The same file appears in up to ~30 file-years. One fix commit touches several files, so
  outcomes are correlated across files. Naive logistic SEs are too small by an unknown factor. They then feed the
  meta-analysis as v_i and over-weight large repos.
- **Repo fixed effects.** "Repo fixed effects within language" contradicts "unit = repository, one effect per
  repo": inside a per-repo model a repo FE is a constant.
- **Size-mechanical metrics.** "In-degree sum" over a file scales mechanically with the file's function count. The
  size confound in LAW-7 is then partly a definition.
- **Missing static coupling control.** LAW-6's controls omit static coupling. In-cycle membership is largely a
  proxy for having both in- and out-edges, and in Java the file-level SCC is often a giant component covering a
  majority of files. The binary exposure is then near-constant and confounded with coupling.
- **Collinearity.** log LOC and log functions are collinear (r ≈ 0.9), and so are churn, authors and prior fixes.
  This inflates SEs (harmless) but makes LAW-7's attenuation depend on which proxies are in.
- **Odds-ratio non-collapsibility.** Adding a covariate that predicts the outcome but is uncorrelated with the
  exposure still moves the OR. "1 − adjusted/unadjusted" therefore mixes confounding with non-collapsibility, and
  the ratio is undefined or sign-flipping when the unadjusted log OR is near 0.
- **Rare outcomes.** Small repos risk separation.

**Amendment text.**
> **Defect panel.** Unit = (non-test source file, yearly snapshot t). A file-year is kept iff:
>
> - t ≥ first snapshot + 1 year;
> - t + 365 d ≤ the last commit date covered by labels (OSV and keyword);
> - the file exists at t.
>
> Outcome = ≥ 1 fix touching the file (path carried through renames by `git log --follow`-equivalent per-commit
> `-M` with `diff.renameLimit=0`) in (t, t + 365 d]. A file deleted in the window without a fix is kept with
> outcome 0, and the deletion share is reported. A sensitivity analysis with a discrete-time competing-risk model
> (fix vs deletion) is reported for LAW-6.
> **Per-repo model:** Firth-penalised logistic regression (no repo FE; calendar-year FE).
>
> - SEs are cluster-robust two-way by file and by fix commit (Cameron–Gelbach–Miller). If that is not estimable,
>   use a cluster bootstrap by file, 1,000 resamples.
> - Controls: log(1+LOC), log(1+functions), log(1+churn prior year), log(1+prior fixes), log(1+distinct
>   non-bot authors, mailmap-resolved), log(1+change-coupled files) with commits touching > 50 source files
>   excluded from change coupling, and calendar year.
> - VIFs are reported.
>
> **Network metrics per file** are size-neutral: *max* and *mean* function in-degree, *distinct external caller
> files*, *distinct external callee files*, in-cycle, and the size of the file's SCC.
> **LAW-6** adds static fan-in and fan-out files to its controls. A file is *in-cycle* if its SCC has size 2–⌈0.2n⌉;
> files in a giant SCC (> 20% of files) are a separate category, reported, not pooled into the exposure. A repo
> where < 5% or > 80% of file-years are in-cycle is not evaluable.
> **LAW-7** effect = attenuation on the **average marginal effect** scale (risk difference per SD of the metric),
> 1 − AME_adj / AME_unadj. It is computed only where the unadjusted AME's one-sided p < 0.05; otherwise the repo is
> "not evaluable for attenuation" and counted. A paired bootstrap supplies the SE. The log-OR version is descriptive.
> A repo with < 50 positive file-years **or** < 50 negative file-years, or with separation after Firth, is not
> evaluable for that law.

### M8. LAW-8 prediction design: define ranking, metric, model and leakage rules

**Problem.**

- **Ranking.** "Recall@20% LOC" depends on whether files are ranked by predicted probability (which favours large
  files and penalises effort-aware recall) or by predicted risk density p̂ / LOC, the effort-aware norm (Kamei et
  al. 2013; Mende & Koschke 2010 [k]). The two can reverse the sign of the network gain.
- **Metric.** Popt is the standard effort-aware metric and should be reported.
- **Model.** Unregularised logistic with ~10 collinear features and few positives per year is unstable.
- **Threshold.** The 0.02 margin is not justified.
- **Train/test timing.** Snapshot t + 1's features use fixes in (t, t + 1], which are also the outcomes of training
  rows at t. That is legitimate in forward time but must be stated, and the training outcome windows must close
  before the test snapshot.

**Amendment text.**
> **LAW-8.** For each test year t+1 with ≥ 3 training years and ≥ 10 positives in the test year:
>
> - Training rows are file-years with snapshot ≤ t whose outcome windows close ≤ snapshot t+1.
> - Models (a) and (b) are L2-penalised logistic regression, λ chosen by 5-fold CV *within* the training years
>   (time-blocked folds). Features are standardised on training data only.
> - Files are ranked by **p̂ / LOC** (effort-aware), ties broken by smaller LOC first.
> - **Effect** = mean over test years of recall@20% LOC (b) − (a). Popt and AUC are reported as secondary metrics.
> - Margin 0.02, justified as about one extra fix-touched file per 50 inspected; equivalence margin ±0.02 (M2).
> - Sensitivity: ranking by p̂, and a random-forest version, both descriptive.

### M9. Sampling frame: GitHub search cannot enumerate the eligible population; make the draw reproducible

**Problem.**

- **The 1,000-result cap.** GitHub search returns at most 1,000 results per query, ranked by "best match". For
  Java, Python, JS and Go, the population with ≥ 500 stars and history from before 2018 is several thousand, so
  "uniform from the eligible list" silently becomes "uniform from the top-1,000 best-match". That biases the
  sample towards popular repos.
- **Primary language vs share.** `language:` filters on the *primary* language, while the 60% share needs the
  languages API per repo.
- **Undefined details.** The JS/TS share is undefined (combined or each). The order of the candidate list (which
  `seed 2982` acts on) is undefined, so the draw is not reproducible.
- **Commit and history checks.** The commit count must be taken on the default branch's first-parent history
  (merge-heavy repos double-count). "First commit ≤ 2018-10-01" can be met by SVN imports, or by a single
  ancient commit before a 2019 real start.

**Amendment text.**
> **Frame.** Candidates come from GitHub search sliced by `created:` month windows (each slice < 1,000 results;
> slices that hit 1,000 are split further) with `stars:>=500 fork:false archived:false language:<L>`. Every
> candidate's languages API share is then checked. Equivalently, the SEART GitHub Search dataset (Dabić et al.
> 2021 [k]) at a dated dump can be used, cross-checked against the API. The frame is complete when no slice is
> truncated; the frame size per language is reported.
> **Share:** JS/TS = JavaScript + TypeScript bytes combined ≥ 60%; C++ includes linguist "C++" only (`.h`
> attributed by linguist).
> **History rules:**
>
> - ≥ 2,000 commits on `git rev-list --first-parent --count` of the default branch;
> - the quarterly snapshot rule must give ≥ 20 snapshots with ≥ 50 source files *and* ≥ 1 commit in ≥ 75% of
>   quarters from the first eligible quarter to 2026-10-01;
> - "first commit" = first quarter with ≥ 50 source files of the language, not the root commit date.
>
> **Draw:** candidates sorted by `full_name` (lower-case, byte order). The draw is
> `random.Random(2982).sample(list, len(list))` (Python 3.12), taking eligible repos in that order until 8 (or 12,
> M1) pass the clone-time checks. The SHA-256 of the candidate file is committed and pushed **before** the draw.
> Clone-time checks are exactly the eligibility rules above plus "the engine scans the 2026-10-01 snapshot without
> error". Failures after the first law statistic is computed never cause replacement.

---

## (b) Should-fix

1. **Survivorship and dormancy (state as a threat; add one guard).**
   - All repos are alive, unarchived, popular, and at least 8 years old. Decay (LAW-5) and hub persistence (LAW-3)
     are estimated in *survivors*, which likely underestimates decay. Survivors are projects whose architecture
     held up, and the effect is conditional on survival.
   - Not-archived ≠ active. Add "≥ 50 commits in the 12 months before 2026-10-01" so that a dormant tail does not
     flatten τ.
   - Report each repo's age at first snapshot. Add "project age" as a meta-regression moderator.
2. **Star floor.** It is fine as an activity floor, but it correlates with the presence of OSV advisories and with
   PR workflows. Report stars as a moderator. Do not interpret language differences as language effects; they are
   confounded with ecosystem norms (an explicit threat).
3. **LAW-5 (decay).**
   - **Q and directory structure.** Q over the *directory* partition changes when directories are reorganised.
     Use the partition at a fixed depth (top-two directory levels below the source root) and report Q/Q_max.
     Same-file-first resolution inflates intra-file, hence intra-directory, edges (M4). Report Q − Q_null with
     intra-file edges removed as a sensitivity analysis.
   - **Propagation cost and size.** Propagation cost mechanically falls as N grows (MacCormack et al. note this).
     Use propagation cost minus its degree-preserving-rewired null (20 rewirings) as the second effect, not raw PC.
   - **Trend test.** Use Sen's slope with a block bootstrap (blocks of 2 yearly points) or Mann–Kendall with the
     Hamed–Rao autocorrelation correction, not raw Kendall τ.
   - **Prior.** CGN-B1 found rising Q in 4 of 5 C repos by the reverse reading, which makes LAW-5's "both" unlikely.
     State it as the prior.
4. **Renames.**
   - `git diff -M` on quarterly diffs with more than `diff.renameLimit` (default 1,000) candidate files silently
     turns off rename detection. Set `-c diff.renameLimit=0` (or a high value) and record when it triggers.
   - Function-level renames are deaths plus births. Report the share of hub "deaths" whose body is ≥ 80%
     token-similar to a same-quarter birth, and run LAW-3 with those carried as a sensitivity analysis.
5. **The 365-day window.** Run 180 d and 730 d as sensitivity analyses for LAW-6 and LAW-7. Release cadence differs
   by ecosystem, and a fixed window favours fast-release languages.
6. **LAW-9.**
   - With a random draw, very few panel repos will have ≥ 20 default-branch OSV fix commits. Expect 0–3 of 8 per
     language, so LAW-9 will almost surely be "not evaluable" under the < 5-repo rule.
   - Either (i) register a separate random draw of 8 repos per language from repos with ≥ 20 OSV-linked
     default-branch fix commits (same other rules, seed 2983), or (ii) make LAW-9 descriptive now. Option (i) is
     the honest replication of Li & Paxson.
   - Fix size counts only non-test source lines (M3).
   - The 50-file sweep cap in `xc_harvest.py` truncates the other-fix distribution. That is conservative; say so.
7. **Overall (cross-language) pooling.** Use a three-level model (repos within languages) rather than pooling
   32 repos as if exchangeable. Q-between with 4 languages has almost no power. Report it, but do not interpret a
   non-significant Q-between as "no language effect".
8. **Not-evaluable dropout.** Law-specific non-evaluability (e.g. < 50 positives) removes small and quiet repos
   non-randomly. Report the characteristics of dropped vs kept repos per law, and run the pooled estimate with
   dropped repos imputed at 0 (with the median v) as a sensitivity analysis.
9. **Pilot.** The "development set" is named but no pilot run is required before the scorer is frozen. Require the
   full scorer (all nine laws, all null models, the synthesis) to run end-to-end on the development repos: at
   least commons-lang, prometheus and sphinx, plus 2 of the 5 C history repos. Publish run time, failure modes and
   the resolution profile, then freeze the scorer hash. Changes after the pilot are allowed only before the panel
   draw.
10. **Compute budget and stopping rule.** Roughly 64 repos × up to ~32 quarters × up to 2 MLOC, plus 200
    simulations (LAW-3/4) and 20 rewirings per yearly snapshot (LAW-5), is substantial. Register the budget, the
    order of laws if the budget is hit (LAW-1/2/6 first), and a rule for snapshots the engine fails on: skip that
    snapshot; a repo with > 10% failed snapshots is not evaluable for LAW-2/3/4/5.
11. **Deviations plan.** Add a section stating that any deviation is logged in a dated amendment table with
    reason, timing relative to data, and expected effect. Analyses changed after data are reported as exploratory
    beside the registered ones.
12. **Threats to validity section.** Required at Stage 1 at MSR RR:
    - construct validity: names as calls, fixes as defects, fix location ≠ defect origin;
    - internal validity: time-varying label coverage and instrument drift;
    - external validity: popular OSS survivors, GitHub only, no industrial code;
    - conclusion validity: k = 8, the power table.
13. **Data and code availability.** Commit to publishing:
    - candidate frames with their hashes;
    - the per-repo pinned SHAs;
    - all fix labels and audit sheets;
    - per-snapshot network edge lists, or the engine DBs if licences permit (all OSI, so yes, with attribution);
    - the scorer;
    - all per-repo estimates with variances.
14. **Holm vs per-family split.** CGT and CGN split α within families. LAWS uses Holm across laws. Say why the
    programme changes conventions (fine, but explain).
15. **Engine version.** `8f96d76ba` predates any non-C/C++ use in this programme. Confirm its parsers for
    Java, Go, Python, JS/TS and C# emit `calls_out_to` at all; the pilot (b9) will show this.

## (c) Fine as is

- Registering the panel rule and the law claims together, before the draw, with the draw logged. Seed fixed (once
  made reproducible, M9).
- One engine for every repo and snapshot (this fixes the CGT-5 caveat). History off.
- Quarterly first-parent snapshots, from the first quarter with ≥ 50 source files.
- Excluding every repo used in the programme so far, and using them as a development set.
- Repo as the unit of synthesis, with every repo-level estimate published "either way".
- Splitting confirmatory and descriptive languages, and the principle of an accuracy gate ahead of claims (the
  design needs M4, the principle is right).
- Degree-preserving rewiring as the modularity null (LAW-5). That is the right null, given the partition fixes in b3.
- Forward-in-time, effort-aware validation for LAW-8, and stating the expected failure in advance (it now needs the
  equivalence test, M2).
- Process controls (churn, prior fixes, authors, change coupling) on every defect law.
- Blind hand-labelling of fixes before any network statistic (it now needs the M6 sizes and a recall audit).
- Power law vs log-normal reported with no direction. CSN as the method (the alternatives need extending, M5).
- Reporting I² and τ² (add prediction intervals, M1).
- Excluding Rust from ACC by name rather than substituting.
