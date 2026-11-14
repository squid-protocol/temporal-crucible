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
  compromised release across packages, excluding standard boilerplate filenames (`LICENSE*`, `README*`, `.gitignore`,
  empty `__init__.py`) and any file sha256 already present in the package's clean baseline $B$ or in D3 calibration
  packages. Packages with no shared payload whose compromise dates fall within the same 3-day window and whose dataset
  notes name the same incident join that campaign; otherwise a package is its own campaign. Campaign assignment is
  computed by script and committed before scoring.
- **Cap:** at most 10 packages per campaign enter the primary sample, chosen by the lowest sha256 of the package name.
  All inference is campaign-clustered, with **campaign-equal weighting** (each campaign $g$ weighted equally via its
  mean across its $n_g \le 10$ packages) as primary and package-weighted pooling reported alongside.
- **Archive completeness and root normalization gate:** DataDog samples are zips while registry history artifacts are
  tarballs. Before scanning, each archive is normalized to its package root (the directory containing the root
  `package.json` for npm, or `PKG-INFO` / `pyproject.toml` / `setup.py` for PyPI). A positive sample is eligible only
  if it is a full release archive (contains the root manifest and, when the immediately preceding clean release $B$ has
  $\ge 2$ files, shares at least 50% of normalized relative file paths with $B$). Partial file-only extracts (where only
  the injected file was archived) are excluded and counted separately so a 1-file extract is never diffed against a
  multi-file tarball.

### D2. History: each positive package's own previous releases

- From the registry's version list and publish times: the last **20** release transitions before the first
  compromised version (fewer if the package has fewer), plus up to **5** preceding baseline releases ($v_{-4}, \dots, v_0$)
  so that the earliest scored transition $t_1 = (v_0 \to v_1)$ has the same 5-release trailing novelty horizon as later
  transitions. A transition is a pair of consecutive versions by publish time, pre-releases included, as published.
- A package with fewer than **8** prior transitions is excluded and counted.
- Artifact type matches the positive's: the npm tarball; for PyPI, the same kind (sdist or wheel) as the sample.

### D3. Calibration: ordinary packages with no known compromise

Needed because ranking within a package always crowns one "most unusual" release, so a within-package rule alarms on
about 1 in 21 ordinary releases. D3 sets an absolute alarm threshold.
- The top **450 npm** and top **300 PyPI** packages by downloads (lists frozen in `docs/rel_inputs.json`), minus any
  package that appears in the DataDog manifests, a fixed list of publicly known compromises, or OSV malicious-package
  reports. Sources: npm, `wooorm/npm-high-impact` (MIT, commit 9e29478); PyPI, downloads from **2026-10-01 to
  2026-10-30** from ClickHouse's public mirror of PyPI's download logs (`pypi.pypi_downloads_per_day`), counted per
  project with explicit name filters, and cross-checked against pypistats.org (boto3 and requests within 5%). The
  set was enlarged from 300 + 200 after the recount so the 1-in-1,000 threshold rests on about 11 exceedances.
- For each, the last 29 releases: of the transitions in that window, those with at least 8 earlier transitions are
  scored (at most 20 per package) exactly as D2, each standardized against its own predecessors (see "Absolute
  score").
- Any single artifact over 250 MB is skipped and its transitions counted as unscored (none is expected: no D3
  package averages over 100 MB per release).
- D3 is never used to choose or weight components; it only sets the threshold in H-REL-3.

### D4. Prospective confirmation: attacks found after registration

Compromised-library samples that DataDog adds after the registration date, through **2027-05-13**, are scored once
with the frozen score and threshold, under the same eligibility rules. This is the cleanest test of "would it catch
an attack nobody had seen when the method was fixed". Reported as its own result.

### Pre-assessment (metadata only)

Counted on 2026-11-13 from the DataDog repository file listing and npm/PyPI registry metadata. No sample was
downloaded or opened.

- **Samples:** 1,477 `compromised_lib` zips (npm 1,448, PyPI 29) across 1,004 npm and 17 PyPI packages, dated
  2024-12-03 to 2026-10-08. No two zips are byte-identical, so payload grouping needs file hashes from inside them.
- **Registry:** the compromised version is gone from registry metadata for 952 of 977 npm packages found and for all
  16 PyPI packages found; 27 npm packages and 1 PyPI package are gone entirely. Positive artifacts therefore come from
  the DataDog zips; their history comes from the registry. For npm the cutoff is the registry publish time of the
  earliest compromised version (still in the `time` map for all 977); for PyPI it is the zip date.
- **History before the compromise** (release transitions):

  | | packages | min | median | max | ≥ 8 (eligible) | ≥ 20 |
  |---|---:|---:|---:|---:|---:|---:|
  | npm | 977 | 0 | 20 | 2,907 | 652 | 495 |
  | PyPI | 16 | 1 | 108 | 726 | 14 | 13 |

- **Campaigns (date proxy, 3-day windows):** 35 groups, 33 with an eligible package. Five groups hold 83% of
  packages:

  | first compromise | packages | eligible |
  |---|---:|---:|
  | 2025-11-24 (Shai-Hulud 2) | 349 | 147 |
  | 2025-09-14 (Shai-Hulud 1) | 178 | 115 |
  | 2026-05-11 | 123 | 82 |
  | 2026-06-17 | 119 | 115 |
  | 2026-03-20 | 60 | 42 |

  chalk/debug (2025-09-08) is 18 packages, 14 eligible; nx (2025-08-26) is 7. 20 of the 35 groups have 2 or fewer
  packages. The real campaign assignment (shared payload) may merge or split these.
- **Primary sample after the cap of 10 per campaign:** 158 positives (147 npm, 11 PyPI) in about **33 campaigns**.
  PyPI results will be anecdotal and are reported but not judged separately.
- **D3 calibration (recounted 2026-11-14 for the reviewed design):** 450 npm packages (17 excluded on the way) and 300
  PyPI packages (13 excluded). With the last 29 releases and at least 8 predecessors per scored transition: npm 359
  packages contribute **5,576** scored transitions, PyPI 290 contribute **5,205**, **≈ 10,800 in all**.
  - PyPI ranking note: a single large `GROUP BY` on the public ClickHouse account silently dropped projects
    (numpy, packaging and others were missing from a "top 400"), so the ranking was rebuilt from 1,500 candidates with
    exact per-project October counts. Top ten: boto3, packaging, typing-extensions, certifi, idna, urllib3,
    charset-normalizer, requests, cryptography, cffi.
  - The earlier `hugovk/top-pypi-packages` list (no licence file) is no longer used.
- **Volume:**
  - Calibration: about 16,600 artifacts, about 22 GB (PyPI about 17.7 GB, led by pymupdf, pillow, scipy, playwright and
    matplotlib sdists).
  - Positives: about 158 × 26 ≈ 4,100 registry artifacts with the 5 extra baseline releases, plus 158 compromised zips
    (≈ 355 MB).
  - In all, roughly 21,000 artifacts and 25 GB.

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

For a transition $t_k = (B \to A)$ of package $p$:
- **Stationary novelty horizon $H_L(t_k)$:** To avoid expanding-window non-stationarity (where $t_1$ checks novelty
  against 1 release while $t_{21}$ checks against 21), novelty in `C1`, `C4` and `C5` is evaluated against the **fixed
  trailing window of the last $L = 5$ clean releases** ending at $B$ ($H_L(t_k) = \{v_{k-5}, \dots, v_{k-1}\}$, or all
  available clean predecessors when $k < 5$; full cumulative history $H \cup \{B\}$ is reported as a sensitivity
  check).

- **Changed units $F(A)$:**
  1. Named/callable functions in `function_data` of $A$ whose key `(normalized_relative_path, func_name)` is new in $A$
     (and whose `(func_name, body_signature)` does not match a moved function in $B$), or whose `body_signature`
     (`(loc, complexity, args, token_mass, hit_vector)`) differs from $B$.
  2. **Module-scope synthetic unit `(normalized_relative_path, "__global_context__")`:** Because import-time / top-level
     code in Python (`__init__.py`, `setup.py`) and JS/TS (`index.js`) has no `function_data` row (`gitgalaxy#2691`),
     each file $f$ in `file_data` also contributes a synthetic top-level unit with residual LOC
     $\text{loc}_{\text{top}}(f) = \max(0, \text{coding\_loc}_f - \sum_{u \in f} \text{loc}_u)$ and residual signal
     counts $\text{hit}_{\text{top}}(f, s) = \max(0, \text{file\_hit}_{f, s} - \sum_{u \in f} \text{func\_hit}_{u, s})$.
     It enters $F(A)$ when $\text{loc}_{\text{top}}(f) \ge 3$ and either $f$ is new or its top-level residual tuple
     $(\text{loc}_{\text{top}}(f), \text{hit}_{\text{top}}(f, \cdot))$ differs from $B$.
- **C1, new shapes** $= |\{f \in F(A) : \text{shape}(f) \notin \text{shapes}(H_L(t_k))\}| / (\max(1, |F(A)|) + 2)$,
  where $\text{shape}(f)$ is the set of function-level structural signals present in $f$ (signals absent at function
  level, `gitgalaxy#8012`, and `sec_*` slots dropped; the $+2$ Laplace denominator prevents a 1-unit typo edit from
  jumping to $1.0$ ahead of a multi-function implant; unsmoothed $/ \max(1, |F(A)|)$ is reported in sensitivity).
- **C2, grammar breaks** $= |\{f \in F(A) : \text{gfit\_pct}(f) \le 0.10\}| / (\max(1, |F(A)|) + 2)$, the smoothed share
  of $F(A)$ (with $\text{loc} \ge 3$ and $\ge 2$ present signals) in the bottom 10% of population grammar fit for their
  language, size and signal-count stratum, exactly as computed by the existing grammar-fit code
  (`agents_lattice.gfit` / `tools/gr_eval.py`; if a formula written here disagrees with that code, the code is the
  definition) (`tools/gr_eval.py` consensus weights $w$ and
  stratum deciles frozen on the population + D3 calibration corpus, never D1).
- **C3, new security hits** $= \sum_{f \in \text{files}(A)} \sum_{s \in S_{\text{sec}}} \max(0, \text{count}_{A,f,s} - \text{count}_{B,f,s})$
  (summed per file $f$ with $\text{count}_{B,f,s} = 0$ for new files, so deleting a test file in $A$ cannot mask a new
  hit in another file). The pinned `file_data` columns $S_{\text{sec}}$ are:
  `sec_reflection_metaprogramming`, `sec_high_risk_execution`, `sec_safety_bypasses`, `sec_self_propagation`,
  `sec_hardcoded_secrets`, `sec_unicode_steganography`, `sec_homoglyphs`, `sec_entropy`, `sec_io`,
  `sec_shadow_imports`, and `sec_extension_mismatch`. The `sec_*` columns only: the structural columns of the same
  names count the keyword family, not the security rule, and are not added (author decision; avoids double counting).
  A renamed file counts all its hits as new; renames are reported.
- **C4, new refused or opaque files** = the number of files in $A$ at a normalized relative path not refused/opaque in
  $H_L(t_k)$ that either (a) appear in `excluded_artifacts` with content-gate `exclusion_reason LIKE 'Blocked (%'`
  (which is how `record_keeper.py` persists `aperture.py`'s `oversized_minified`, `binary_payload`, and
  `generated_noise` gates) or (b) appear in `file_data` with `file_archetype LIKE 'Static: Minified & Vendor Opaque%'`
  (prefix match: the engine has both a "Mass" and a "Footprint" label), `binary_anomaly = 1`, or
  `obfuscation_flag = 1`.
- **C5, new imports** = the number of distinct imported module names in $A$ (`file_data.raw_imports`, excluding
  relative imports starting with `.` and internal module stems of $p$, normalized to the top-level package/module
  identifier) that appear in no release in $H_L(t_k)$.
- **Size placebo Z** = changed lines of code from $B$ to $A$ ($\sum_{f \in A \cup B} |\text{coding\_loc}_{A,f} - \text{coding\_loc}_{B,f}|$
  across files the engine reads).

**Within-package rank.** For each component, transitions of $p$ are ranked against each other (malicious one
included), average ranks for ties, scaled to $[0, 1]$: $r_c(t) = (\text{rank} - 1) / (n_p - 1)$.

- **S (composite)** $= (r_{C1} + r_{C2} + r_{C3} + r_{C4} + r_{C5}) / 5$.
- **S_culture (pure structural culture, primary for H-REL-2)** $= (r_{C1} + r_{C2}) / 2$, testing shape and grammar
  fit directly without import heuristics. **S_culture_imports** $= (r_{C1} + r_{C2} + r_{C5}) / 3$ (adding habitual
  dependencies `C5`) is reported alongside it.
- **Percentile and Top-1 indicator** of the malicious transition $m$ in package $p$, for a score $X$ with $K_p$ benign
  transitions:
  - $P_X(p) = (\#\{\text{benign } b : X(b) < X(m)\} + \tfrac{1}{2}\cdot\#\{\text{benign } b : X(b) = X(m)\}) / K_p$.
  - $\text{Top1}_X(p) = \mathbf{1}\!\left[P_X(p) \ge 1 - \frac{1}{2 K_p}\right]$, which holds if and only if $m$ ranks
    strictly 1st among all $K_p + 1$ transitions or is tied for 1st with at most one benign transition, for **every**
    $K_p \in [8, 20]$ (whereas a fixed $P_X(p) \ge 0.95$ cutoff would admit rank 2 at $K_p = 20$, $19/20 = 0.95$, while
    rejecting a 2-way tie for 1st at $K_p = 8$, $7.5/8 = 0.9375$).

**Absolute score for an alarm (H-REL-3).** Ranks cannot set a cross-package threshold, so count components
($C3, C4, C5$, and $Z$) are first log-stabilized as $\tilde{c}(t) = \ln(1 + c(t))$ (while $C1, C2 \in [0, 1]$ stay as
$\tilde{c}(t) = c(t)$), and each component is standardized out-of-sample against the package's clean history
$H_{\text{clean}}(p, t)$, which is always the transitions **before** $t$ in the package's window (at least 8, at most
20). For a D1 positive $m$ that is its $K_p$ benign predecessors. For a D3 calibration transition it is its own
predecessors, never later releases: a leave-one-out baseline would standardize D3 against neighbours on both sides
in time, shrink D3's tail, lower the threshold and flatter recall. D3 therefore fetches each package's last 29
releases and scores the last 20 transitions, each against its predecessors (packages with fewer releases score the
transitions that have at least 8 predecessors):
$$z_c^+(t) = \max\!\left(0,\; \frac{\tilde{c}(t) - \text{median}_{H_{\text{clean}}}(\tilde{c})}{\max(\text{MAD}_{H_{\text{clean}}}(\tilde{c}),\, \delta_c)}\right)$$
Because sparse components ($C3, C4, C5$) have $\text{MAD} = 0$ in $>50\%$ of packages (making the naive D3 median of
MAD equal to $0$), the scale floor $\delta_c$ is defined strictly positively as
$\delta_c = \max\!\big(\text{median}_{p \in D3,\, \text{MAD}_H(\tilde{c}) > 0}\text{MAD}_H(\tilde{c}),\; Q_{0.90, t \in D3}(|\tilde{c}(t) - \text{median}_H(\tilde{c})|),\; \epsilon_c\big)$
with $\epsilon_{C1} = \epsilon_{C2} = 0.05$ and $\epsilon_{C3} = \epsilon_{C4} = \epsilon_{C5} = \ln(2) \approx 0.693$.
Truncation at $0$ ($z_c^+$) ensures a quiet component does not cancel a positive alarm spike on another component.
**D** = mean of the five $z_c^+$, and **D_culture** = mean of $z_{C1}^+, z_{C2}^+$ (with mean of $z_{C1}^+, z_{C2}^+, z_{C5}^+$
also reported).

## Hypotheses

- **H-REL-1 (primary, the practical score):** compromised releases rank at the top of their own package's history
  on S.
- **H-REL-2 (key secondary, the culture question):** the same for S_culture.
- **H-REL-3 (deployment):** at the threshold where D alarms on 1 in 1,000 D3 ordinary releases, D catches at least
  half of the compromised releases.

Each is judged separately. H-REL-2 has its own bar, so a pass on S carried only by C3 and C4 cannot be read as a
culture result.

## Verdict rules (decided now)

For each campaign $g \in \{1, \dots, G\}$ with $n_g \le 10$ eligible packages, let $\bar{P}_X(g)$ and
$\overline{\text{Top1}}_X(g)$ denote the campaign mean of $P_X(p)$ and $\text{Top1}_X(p)$.

**H-REL-1 and H-REL-2 pass** only if all three hold:
1. **Rank:** the campaign-equal Top-1 share $T_X = \frac{1}{G}\sum_{g=1}^G \overline{\text{Top1}}_X(g)$ is $\ge 0.50$
   (at least half of the hacked releases rank first in their package), and its campaign-clustered bootstrap 95%
   interval (2,000 draws over the $G$ campaigns, seed 2026) has a lower bound $\ge 0.35$. The campaign-weighted median
   of $P_X(p)$ and the share with $P_X(p) \ge 0.95$ are reported alongside but are not the bar: a 0.95 cutoff admits
   rank 2 at $K_p = 20$ and is inconsistent across $K_p$.
2. **Beats size:** the campaign-equal mean paired difference $\frac{1}{G}\sum_{g=1}^G (\bar{P}_X(g) - \bar{P}_Z(g))$ is
   $> 0$, with **both** the campaign-clustered bootstrap 95% interval excluding $0$ **and** the exact campaign-level
   sign-flip randomization test (2,000 draws flipping the sign of $\Delta_g = \bar{P}_X(g) - \bar{P}_Z(g)$ per campaign)
   giving one-sided $p < 0.025$.
3. **Beats chance:** a within-package permutation control (the malicious label moved to a random transition within each
   package, shared within each campaign draw, 2,000 draws) puts the observed $T_X$ above the permutation
   distribution's 99th percentile.

**H-REL-3 passes** if campaign-equal recall at the D3 1-in-1,000 threshold is $\ge 0.50$ with a **joint (D3 + D1)
cluster-bootstrap** 95% lower bound $\ge 0.30$ (in each of the 2,000 draws, D3 packages are resampled by package cluster
to recompute the $99.9\text{th}$-percentile threshold $\hat{\tau}^*_{0.999}$ and D1 campaigns are resampled to score
recall at $\hat{\tau}^*_{0.999}$, propagating threshold estimation error into the interval). Both the pooled D3
threshold and ecosystem-stratified (`npm` vs `PyPI`) thresholds are reported, along with a D3 per-package diagnostic
verifying whether any single D3 package contributes $> 2$ of the top 10 exceedances.

**Kill rule.** If H-REL-1 fails, "release unlike its history" is dropped as a security product claim. If H-REL-1
passes and H-REL-2 fails, the culture signal adds nothing here and the result is credited to C3, C4 and C5 only. If
H-REL-1 passes and H-REL-3 fails, the method can rank but not alarm at a usable rate; it may still serve as a
review-priority signal.

**Minimum sample.** At least 20 eligible positive packages from at least 5 campaigns. Below that, REL is reported as
descriptive only.

## The numbers behind the bars

- **What Top-1 and $P_X(p) \ge 0.95$ mean.** With $K_p = 20$ benign transitions and no ties, ranking 1st gives
  $P_X(p) = 20/20 = 1.00$ and ranking 2nd gives $P_X(p) = 19/20 = 0.95$, whereas for $K_p = 8$ a 2-way tie for 1st gives
  $7.5/8 = 0.9375 < 0.95$. Using $\text{Top1}_X(p) = \mathbf{1}[P_X(p) \ge 1 - 1/(2 K_p)]$ makes "outright 1st or
  2-way tie for 1st" exact across all $K_p \in [8, 20]$, while reporting $P_X(p) \ge 0.95$ alongside it preserves the
  top-5% interpretation.
- **Chance level.** Under the null (the malicious transition is exchangeable with the package's others and no ties),
  the chance of ranking strictly first at $K_p = 20$ is $1/21 \approx 0.0476$ (and of $P_X(p) \ge 0.95$, i.e. rank 1 or
  2, is $2/21 \approx 0.0952$). For $n = 20$ independent campaigns, the upper-tail binomial probability that at least
  10 rank strictly first is $\sum_{k=10}^{20} \binom{20}{k}(1/21)^k(20/21)^{20-k} = 7.12 \times 10^{-9}$ (and for rank
  1 or 2 at $p = 2/21$, $4.60 \times 10^{-6}$; recomputed by the author, the review gave 7.16e-9 and 5.07e-6). Significance is not the hard part; the bar is set on effect size.
- **Precision.** Campaigns are the units. With about 33 campaigns, the standard error of a campaign-equal share near
  $0.5$ is $\sqrt{0.25/33} \approx 0.087$ (95% interval $\approx \pm 0.17$). Weighting campaigns equally prevents the
  five large campaigns (capped at 10 packages each, 50 of 158 packages) from getting $10\times$ the influence of
  single-package compromises, and the campaign-level sign-flip test for `Beats size` is exact even if real payload
  grouping leaves fewer than 15 campaigns.
- **Alarm rate.** At 1 in 1,000, a registry with 50,000 new releases a day would raise about 50 alarms a day before
  any other filter. That is the order of magnitude a triage team can review; 1 in 21 is not.
- **D3 size.** About 10,800 transitions (recount), so the 1-in-1,000 threshold rests on about 11 exceedances (Poisson
  95% range $\approx [5.5, 19.7]$, i.e. true FPR $\approx 0.05\%$ to $0.18\%$, plus within-package clustering across
  the 649 contributing D3 packages). The joint D3 + D1 cluster bootstrap folds this threshold variance directly
  into the H-REL-3 lower bound, and recall is also reported at 1 in 100, 1 in 500, and 1 in 2,000.

## Exploratory: does the whole fingerprint add anything? (labelled, never a verdict)

Uses everything the engine records, not just the five components: the full file-level and function-level signal
sets as within-package z-scores, call-graph changes (new outbound edges, new callees to I/O, process or eval
functions), complexity, nesting, size, comment and naming features, and dependency-graph changes.

- **Split:** campaigns (not packages) are split into two halves by the lowest sha256 of the campaign id, so no
  campaign's payload appears on both sides. D3 calibration packages are split into two halves by package-name sha256
  in the same way so the learned model's 1-in-1,000 threshold is set on the training half's D3 packages and evaluated
  on the test half's D3 packages.
- **Model:** L2-regularized logistic regression on within-package z-scores against predecessors only (as for D) (positive class = D1
  compromised transitions in the training half; negative class = benign history transitions and training-half D3
  transitions). The regularization strength and top-$k$ variance/prevalence feature filter are chosen by
  campaign-grouped inner cross-validation on the training half only.
- **Test:** on the other half, the campaign-weighted median within-package percentile and campaign-equal recall at the
  held-out D3 1-in-1,000 threshold, next to the fixed score S and D on the same half. Then the halves swap and both
  results are reported.
- **Reading:** if the learned model beats the fixed score on both test halves, the fingerprint holds signal the five
  components miss, and a follow-up registration tests it on D4. If not, the fixed score is enough.

## Comparators (reported, not part of the verdict)

- **Install-hook delta rule:** an npm `package.json` `preinstall`/`install`/`postinstall` script added or changed from
  $B$ to $A$, or a PyPI `setup.py` / `pyproject.toml` build hook that gains network or process-exec calls from $B$ to $A$.
- **GuardDog** (Apache-2.0): run on both $B$ and $A$, scored by **new findings** in $A$ not present in $B$
  ($\max(0, \text{hits}_A - \text{hits}_B)$ per rule), ranked within package and evaluated on D3 at both its native
  trigger rate ($\ge 1$ new rule hit) and at the matched D3 alarm rate alongside `D`.

## Sensitivity (labelled, never verdicts)

- All compromised versions per package, not just the earliest.
- No per-campaign cap, and package-weighted vs campaign-equal pooling.
- Each component alone (C1 to C5), and `S_culture` (`C1 + C2`) vs `S_culture_imports` (`C1 + C2 + C5`).
- Unsmoothed `C1`, `C2` denominators ($/ \max(1, |F(A)|)$) and cumulative novelty horizon $H \cup \{B\}$ vs trailing
  $L = 5$.
- Windows of 10 and of all available history.
- npm and PyPI separately.

## Required slices (reported with the verdicts, so a pass cannot hide where it comes from)

- **Quiet compromises:** positives with C3 = 0 and C4 = 0 (no new security hit and no new refused file). Top-1 share of
  S and S_culture on this slice is the closest this sample comes to "attacks a pattern scanner would miss".
- **Manifest-only compromises:** positives whose only change is in `package.json` / `setup.cfg` / `pyproject.toml`.
  The engine treats JSON, YAML and plain text as inert (no security rules, no functions, no imports), so S scores these
  near zero by design. Their count and the install-hook rule's result on them are reported.
- **By component:** for each positive, which components put it in the top rank, so the share carried by C3/C4 versus
  C1/C2/C5 is visible.

## Review log (incorporated into draft, 2026-11-13)

Reviewed by **Gemini 4 Argon** (full review packet response posted on PR #184):
1. **Engine schema alignment (`C3`, `C4`):** Pinned `C3` to the exact `file_data` `sec_*` columns (`sec_self_propagation`,
   `sec_hardcoded_secrets`, `sec_unicode_steganography`, `sec_homoglyphs`, `sec_entropy`, `sec_io`, etc., which do not
   exist unprefixed in `SIGNAL_SCHEMA`) summed as per-file positive deltas $\max(0, \text{count}_{A,f,s} - \text{count}_{B,f,s})$.
   Pinned `C4` to `excluded_artifacts` content-gate rows (`exclusion_reason LIKE 'Blocked (%'`, how `record_keeper.py`
   persists `aperture.py` refusals) plus `file_data` rows with `file_archetype = 'Static: Minified & Vendor Opaque Mass'`,
   `binary_anomaly = 1`, or `obfuscation_flag = 1`.
2. **Module-scope import-time code (`F(A)`):** Added the per-file synthetic top-level unit `(__global_context__)` from
   the `file_data` minus `function_data` residual so `C1` and `C2` are not blind to top-level payloads in `__init__.py`,
   `setup.py`, or `index.js` (`gitgalaxy#2691`), and added $+2$ Laplace denominator smoothing to `C1` and `C2`.
3. **Stationary novelty horizon ($H_L(t_k)$):** Fixed the novelty reference window for `C1`, `C4`, `C5` to the trailing
   $L = 5$ clean releases (with up to 5 extra baseline releases fetched before $t_1$) so early transitions in the
   20-transition window are not evaluated against a smaller history than the compromised release.
4. **Division-by-zero & tail scaling in `D` (`H-REL-3`):** Log-stabilized count components ($\ln(1 + c)$), replaced the
   naive D3 median of MAD (which is $0$ for sparse components `C3`, `C4`, `C5`) with a strictly positive scale floor
   $\delta_c \ge \epsilon_c > 0$, truncated $z_c$ at $0$ ($z_c^+$), and specified leave-one-out baselines for D3
   transitions to match D1's out-of-sample standardization.
5. **Top-1 rank parity across $K_p \in [8, 20]$ & campaign-equal inference:** Defined $\text{Top1}_X(p) = \mathbf{1}[P_X(p) \ge 1 - 1/(2 K_p)]$,
   separated pure structural culture `S_culture = (r_C1 + r_C2)/2` from `S_culture_imports = (r_C1 + r_C2 + r_C5)/3`,
   adopted campaign-equal weighting with an exact campaign-level sign-flip test for `Beats size`, and specified a joint
   (D3 + D1) cluster bootstrap for `H-REL-3` threshold uncertainty.
6. **Archive root & completeness gate (`D1`):** Promoted Open Question 6 into a mandatory pre-scan package-root
   canonicalization and 50% path-overlap completeness gate.

Gemini's forecasts before data (recorded so they can be scored later): H-REL-1 72%, H-REL-2 28% (48% for
S_culture_imports), H-REL-3 18%, exploratory model beating the fixed score on both halves 35%; median within-package
percentile 0.96 for S and 0.82 for S_culture.

### Author response (2026-11-14)

Gemini edited this draft directly (commit 98f945c) rather than only commenting. The author checked every factual claim
against gitgalaxy `origin/main` and recomputed the maths before accepting anything:

- **Verified and accepted:** the `sec_*` column names; `excluded_artifacts` stores `exclusion_reason` ("Blocked (…"
  for content gates), not the aperture classification; top-level code has no `function_data` row (gitgalaxy#2691);
  JSON/YAML/plain text are inert (`galaxyscope.py:910`); `P ≥ 0.95` admits rank 2 at K = 20; the MAD floor was zero
  for sparse components; the expanding novelty horizon; campaign-equal weighting; the joint threshold bootstrap;
  GuardDog on deltas; the D3 split in the exploratory model.
- **Changed by the author after review:**
  1. The rank bar now uses the Top-1 share (≥ 0.50, lower bound ≥ 0.35) instead of a median P ≥ 0.95. The reviewed
     text fixed Top-1 but kept the 0.95 median as the bar, which still admits rank 2.
  2. "Beats chance" now names its statistic (T_X).
  3. D's baseline is predecessors only, for D1 and D3 alike. The reviewed leave-one-out baseline would let a D3
     transition be standardized against later releases, shrinking D3's tail and flattering recall. D3 now fetches 29
     releases per package.
  4. C3 uses the `sec_*` columns only; the reviewed text also added structural columns "where not already counted",
     which was ambiguous.
  5. C4's archetype match is a prefix: the engine has both "…Opaque Mass" and "…Opaque Footprint" labels.
  6. The binomial figures are 7.12e-9 and 4.60e-6 (review: 7.16e-9 and 5.07e-6; same order, slips in the digits).
  7. C2's strata are whatever the existing grammar-fit code computes; the written formula is descriptive.
  8. Added required slices: quiet compromises (C3 = 0 and C4 = 0), manifest-only compromises (invisible to the
     engine by design), and which component carried each positive.
- **Not adopted without checking:** the review says OSV `MAL-*` advisories distinguish compromised versions from
  typosquats. That is unverified and is not used.
- **Independence:** the second reviewer (a different Claude model) will see this post-review draft, not Gemini's
  comment.

## Order of work

1. Independent review (another Claude model and Gemini), then owner approval. Changes from review are recorded here.
2. Registration: the status line becomes REGISTERED with the engine pin.
3. Inputs committed (`docs/rel_inputs.json`): positives, history windows, D3 package list and versions (from
   metadata), and campaigns. Campaigns need file hashes from inside the samples; a script computes only sha256 of
   each file in each extracted sample, with no scan and no score, and its output is committed before step 4.
4. `tools/rel_eval.py` committed.
5. Samples fetched, extracted in isolation and scanned; the scorer runs once; results go to `docs/rel.md` and the
   journal. D4 is scored on or after 2027-05-13.
