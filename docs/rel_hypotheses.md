# REL: does a compromised release look unlike the package's own history? (DRAFT, 2026-11-13)

**Status: DRAFT for owner approval and independent review. Not registered. No outcome data has been read: no
malicious sample has been downloaded, extracted or scanned.** The pre-assessment numbers below come from registry
and dataset metadata only (version lists, publish times, file listings). The scorer (`tools/rel_eval.py`) is
committed after registration and before any run, as with LAT.

## Plain-language summary

When attackers take over a popular package, they publish a new version with their code inside. GitGalaxy can read a
project's habits (which kinds of code it writes, in which combinations, importing what). REL asks whether the hacked
version looks like it was written by a stranger: is it the most unusual release in the package's recent history,
and can an alarm fire on it without also firing on ordinary releases all the time?

## Why

GitGalaxy's security layer has no measured detection rate (gitgalaxy#8426, epic gitgalaxy#8427), and its pattern
rules mostly duplicate other tools. What this program has shown is that code carries a stable, readable culture:

- a program's lattice family mix identified its authoring model 84% of the time (chance 28%; agents_lattice);
- GitGalaxy's own Gemini-era and Claude-era code separate at AUC 0.88 (gg_lattice);
- 88% of functions never change shape over their observed life, and about 3% of function-weeks move.

The best-known recent supply-chain attacks put foreign code inside a trusted package: chalk/debug, nx, the
Shai-Hulud worm, @solana/web3.js, Ultralytics. No pattern rule needs to know such an attack in advance to notice
that a release is unlike its predecessors.

## Priors (stated so the bar is honest)

- Per-file structural risk does not predict CVEs or defects (H3, N-H3: AUC 0.479 vs LOC 0.531).
- Lattice moves add nothing to churn for regressions (LAT-M1 ✗).
- Malicious changes are often small; ordinary releases are often large. A size effect in either direction is
  expected, which is why the size placebo is part of the verdict.
- Expectation: H-REL-1 is plausible, because compromised releases often add install hooks, minified bundles, new
  network or process imports, or obfuscated code that a package's history never had. H-REL-2 (culture alone) is the
  real test and could easily fail. H-REL-3 (a usable alarm rate) is the hardest.

## Data

### D1. Positives: compromised releases

Compromised releases of previously legitimate packages from DataDog's `malicious-software-packages-dataset`
(Apache-2.0), category `compromised_lib`, npm and PyPI.
- Typosquats and new malicious packages (category `malicious_intent`) are out: they have no clean history.
- One positive per package: its **earliest** compromised version (by the dataset's sample date, then version).
  Later compromised versions are a sensitivity analysis.
- **Campaign:** packages are grouped into campaigns by shared payload: a byte-identical file added or changed in the
  compromised release across packages. Packages with no shared payload whose compromise dates fall within the same
  3-day window and whose dataset notes name the same incident join that campaign; otherwise a package is its own
  campaign. Campaign assignment is computed by script and committed before scoring.
- **Cap:** at most 10 packages per campaign enter the primary sample, chosen by the lowest sha256 of the package name.
  All inference is campaign-clustered.

### D2. History: each positive package's own previous releases

- From the registry's version list and publish times: the last **20** release transitions before the first
  compromised version (fewer if the package has fewer). A transition is a pair of consecutive versions by publish
  time, pre-releases included, as published.
- A package with fewer than **8** prior transitions is excluded and counted.
- Artifact type matches the positive's: the npm tarball; for PyPI, the same kind (sdist or wheel) as the sample.

### D3. Calibration: ordinary packages with no known compromise

Needed because ranking within a package always crowns one "most unusual" release, so a within-package rule alarms on
about 1 in 21 ordinary releases. D3 sets an absolute alarm threshold.
- The top 300 npm packages and top 200 PyPI packages by downloads at registration time (lists frozen in
  `docs/rel_inputs.json`), minus any package that appears in the DataDog manifests or in OSV malicious-package reports.
- For each, the last 21 releases (20 transitions), scored exactly as D2.
- D3 is never used to choose or weight components; it only sets the threshold in H-REL-3.

### D4. Prospective confirmation: attacks found after registration

Compromised-library samples that DataDog adds after the registration date, through **2027-05-13**, are scored once
with the frozen score and threshold, under the same eligibility rules. This is the cleanest test of "would it catch
an attack nobody had seen when the method was fixed". Reported as its own result.

### Pre-assessment (metadata only)

_Filled in from the metadata scout before review: eligible positives per ecosystem, campaigns and their sizes,
eligible after the cap, history-length distribution, D3 size, and download volume._

### Selection bias and limits, stated

- DataDog's samples were mostly found by GuardDog, so they may over-represent compromises that already look
  malicious to a pattern scanner. A pass here does not show REL catches the quiet ones.
- The 2018 to 2022 classics (event-stream, ua-parser-js, coa, rc, eslint-scope, ctx, xz) have no obtainable
  malicious artifact from this source and are not in the sample.
- Campaigns, not packages, are the independent units. The effective sample size is the number of campaigns.

### Handling

Samples are encrypted zips. They are extracted only into an isolated local directory, never installed, imported or
executed, and never committed, cached in CI, or quoted in this public repo. Only aggregate results and package names
and versions (already public in the dataset and in news reports) are published.

## Scan

- Engine: gitgalaxy pinned at the commit current when this is registered (recorded in the scorer), default
  configuration, `GITGALAXY_DISABLE_GIT_HISTORY=1`. The default engine is the point: this is what a user would run.
- Known engine limits that will cost recall, accepted rather than patched: the minification gate skips files with
  very long lines (aperture Gate 4.1), and the security lens blanks lines of 250+ characters (gitgalaxy#8429).
  Skipped files are still recorded in `excluded_artifacts`, which C4 uses.
- An artifact the engine fails to scan scores as not detected (the conservative direction) and is reported.

## The fixed score (decided now, no tuning)

For a transition from release B to release A of package p, with H = all earlier releases of p in its window:

- **Changed functions** F(A): functions in A whose key (relative path, qualified name) is new, or whose normalized
  body hash differs from B.
- **C1, new shapes** = |{f ∈ F(A) : shape(f) ∉ shapes(H ∪ {B})}| / max(1, |F(A)|), where shape(f) is the set of
  function-level signals present in f (signals absent at function level, gitgalaxy#8012, dropped).
- **C2, grammar breaks** = the share of F(A) in the bottom 10% of population grammar fit for their language, size and
  signal count (the GR strata used in agents_lattice).
- **C3, new security hits** = Σ over the counted signals of max(0, count_A − count_B), with counts summed over
  files. Counted: `reflection_metaprogramming`, `high_risk_execution`, `safety_bypasses`, `self_propagation`,
  `hardcoded_secrets`, `unicode_steganography`, `homoglyphs`, `entropy`, and network I/O.
- **C4, new refused files** = the number of files in A the engine excluded as `oversized_minified`, `binary_payload`
  or `generated_noise` at a path with no excluded file in H ∪ {B}.
- **C5, new imports** = the number of distinct imported module names in A (the engine's extracted dependencies,
  normalized to the top-level module) that appear in no release in H ∪ {B}.
- **Size placebo Z** = changed lines of code from B to A (added + removed, in files the engine reads).

**Within-package rank.** For each component, transitions of p are ranked against each other (malicious one
included), average ranks for ties, scaled to [0, 1]: r_c(t) = (rank − 1) / (n_p − 1).

- **S (composite)** = (r_C1 + r_C2 + r_C3 + r_C4 + r_C5) / 5.
- **S_culture** = (r_C1 + r_C2 + r_C5) / 3. New imports count as culture: they are what a project habitually
  depends on, not a pattern rule.
- **Percentile** of the malicious transition m in package p, for a score X:
  P_X(p) = (#{benign b : X(b) < X(m)} + ½·#{benign b : X(b) = X(m)}) / K_p, with K_p benign transitions.

**Absolute score for an alarm (H-REL-3).** Ranks cannot set a cross-package threshold, so each component is also
expressed against the package's own history: z_c(t) = (c(t) − median_H(c)) / max(MAD_H(c), δ_c), where δ_c is the
D3 median of MAD for that component (a floor so a quiet package does not divide by ~0). **D** = mean of the five
z_c, and **D_culture** = mean of z_C1, z_C2, z_C5.

## Hypotheses

- **H-REL-1 (primary, the practical score):** compromised releases rank at the top of their own package's history
  on S.
- **H-REL-2 (key secondary, the culture question):** the same for S_culture.
- **H-REL-3 (deployment):** at the threshold where D alarms on 1 in 1,000 D3 ordinary releases, D catches at least
  half of the compromised releases.

Each is judged separately. H-REL-2 has its own bar, so a pass on S carried only by C3 and C4 cannot be read as a
culture result.

## Verdict rules (decided now)

**H-REL-1 and H-REL-2 pass** only if all three hold:
1. **Rank:** the median of P_X(p) over eligible packages is ≥ 0.95, and the campaign-clustered bootstrap 95% interval
   of the share of packages with P_X(p) ≥ 0.95 has a lower bound ≥ 0.35.
2. **Beats size:** the mean paired difference P_X(p) − P_Z(p) is > 0, with the campaign-clustered bootstrap 95%
   interval (2,000 draws, seed 2026) excluding 0.
3. **Beats chance:** a permutation control (the malicious label moved to a random transition within each package,
   2,000 draws) puts the observed median above the permutation's 99th percentile.

**H-REL-3 passes** if recall at the D3 1-in-1,000 threshold is ≥ 0.50 with a campaign-clustered bootstrap lower bound
≥ 0.30. The threshold is the 99.9th percentile of D over all D3 transitions, computed once.

**Kill rule.** If H-REL-1 fails, "release unlike its history" is dropped as a security product claim. If H-REL-1
passes and H-REL-2 fails, the culture signal adds nothing here and the result is credited to C3 and C4 only. If
H-REL-1 passes and H-REL-3 fails, the method can rank but not alarm at a usable rate; it may still serve as a
review-priority signal.

**Minimum sample.** At least 20 eligible positive packages from at least 5 campaigns. Below that, REL is reported as
descriptive only.

## The numbers behind the bars

- **What "median ≥ 0.95" means.** With K = 20 benign transitions, P takes values in steps of 0.05, so P ≥ 0.95
  means the malicious release is the single most unusual of the 21, or tied for top. The median bar therefore
  requires at least half of the packages to put the hacked release first.
- **Chance level.** Under the null (the malicious transition is exchangeable with the package's others), the
  chance of ranking first is 1/21 ≈ 0.048. For n = 20 independent packages, the chance that at least 10 rank first
  is about C(20,10)·(1/21)^10 ≈ 1e-8. Significance is not the hard part; the bar is set on effect size.
- **Precision.** Campaigns are the units. With about 10 campaigns, the standard error of a share near 0.5 is about
  √(0.25/10) ≈ 0.16, so a 95% interval is about ±0.3. The lower-bound clause (≥ 0.35) needs a point estimate near
  0.65 or higher at that sample size. The pre-assessment section turns this into the real campaign count.
- **Alarm rate.** At 1 in 1,000, a registry with 50,000 new releases a day would raise about 50 alarms a day before
  any other filter. That is the order of magnitude a triage team can review; 1 in 21 is not.
- **D3 size.** About 500 packages × 20 transitions ≈ 10,000 transitions, so the 1-in-1,000 threshold rests on about
  10 exceedances. Its sampling error is reported (bootstrap over D3 packages), and recall is also reported at 1 in
  500 and 1 in 2,000.

## Exploratory: does the whole fingerprint add anything? (labelled, never a verdict)

Uses everything the engine records, not just the five components: the full file-level and function-level signal
sets as within-package z-scores, call-graph changes (new outbound edges, new callees to I/O, process or eval
functions), complexity, nesting, size, comment and naming features, and dependency-graph changes.

- **Split:** campaigns (not packages) are split into two halves by the lowest sha256 of the campaign id, so no
  campaign's payload appears on both sides.
- **Model:** L2-regularized logistic regression on within-package z-scores. The regularization strength is chosen by
  inner cross-validation on the training half only.
- **Test:** on the other half, the median within-package percentile and recall at the D3 1-in-1,000 threshold, next
  to the fixed score S and D on the same half. Then the halves swap and both results are reported.
- **Reading:** if the learned model beats the fixed score on both test halves, the fingerprint holds signal the five
  components miss, and a follow-up registration tests it on D4. If not, the fixed score is enough.

## Comparators (reported, not part of the verdict)

- **Install-hook rule:** an npm `preinstall`/`install`/`postinstall` script added or changed, or a PyPI `setup.py`
  that gains network or exec calls.
- **GuardDog** (Apache-2.0), run on A, ranked within package by the number of rules hit, and its alarm rate on D3.

## Sensitivity (labelled, never verdicts)

- All compromised versions per package, not just the earliest.
- No per-campaign cap.
- Each component alone (C1 to C5).
- Windows of 10 and of all available history.
- npm and PyPI separately.

## Open questions for review

1. Is a median rank of 0.95 (most hacked releases rank first of 21) the right bar, or too strict for a first test?
2. Is the 1-in-1,000 alarm rate the right deployment target, and is ~10,000 calibration transitions enough to set it?
3. Should new imports (C5) count as culture, or as a known heuristic alongside the install-hook rule?
4. Campaign assignment by shared payload plus a date window: is that robust enough when attackers vary payloads?
5. With about 10 effective campaigns, is the study worth running as confirmatory, or should it be exploratory now
   and confirmatory on D4?
6. Are there better sources for the older attacks (event-stream, ua-parser-js, xz) whose licences allow
   commercial research use?

## Order of work

1. Independent review (another Claude model and Gemini), then owner approval. Changes from review are recorded here.
2. Registration: the status line becomes REGISTERED with the engine pin.
3. Inputs committed (`docs/rel_inputs.json`): positives, history windows, D3 package list and versions (from
   metadata), and campaigns. Campaigns need file hashes from inside the samples; a script computes only sha256 of
   each file in each extracted sample, with no scan and no score, and its output is committed before step 4.
4. `tools/rel_eval.py` committed.
5. Samples fetched, extracted in isolation and scanned; the scorer runs once; results go to `docs/rel.md` and the
   journal. D4 is scored on or after 2027-05-13.
