# REL: does a compromised release look unlike the package's own history? (DRAFT, 2026-11-13)

**Status: DRAFT for owner approval. Not registered. No outcome data has been read: no malicious sample has been
downloaded, extracted or scanned.** The scorer (`tools/rel_eval.py`) is committed after registration and before any
run, as with LAT.

## Why

GitGalaxy's security layer has no measured detection rate (gitgalaxy#8426, epic gitgalaxy#8427), and its pattern
rules mostly duplicate other tools. What this program has shown is that code carries a stable, readable culture:

- a program's lattice family mix identified its authoring model 84% of the time (chance 28%; agents_lattice);
- GitGalaxy's own Gemini-era and Claude-era code separate at AUC 0.88 (gg_lattice);
- 88% of functions never change shape over their observed life, and about 3% of function-weeks move.

The best-known recent supply-chain attacks put foreign code inside a trusted package: chalk/debug, nx, the
Shai-Hulud worm, @solana/web3.js, Ultralytics. REL asks whether the release that carried the attack stands out from
that package's ordinary releases, which no pattern rule needs to know in advance.

## Priors (stated so the bar is honest)

- Per-file structural risk does not predict CVEs or defects (H3, N-H3: AUC 0.479 vs LOC 0.531).
- Lattice moves add nothing to churn for regressions (LAT-M1 ✗).
- Malicious changes are often small; ordinary releases are often large. A size effect in either direction is
  expected, which is why the size placebo below is part of the verdict, not a footnote.
- Expectation: H-REL-1 is plausible because compromised releases often add install hooks, minified bundles or
  obfuscated code that a package's history never had. H-REL-2 (culture alone) is the real test and could easily fail.

## Data

**Positives.** Compromised releases of previously legitimate packages from DataDog's
`malicious-software-packages-dataset` (Apache-2.0), category `compromised_lib`, npm and PyPI.
- Typosquats and new malicious packages (category `malicious_intent`) are out: they have no clean history.
- One positive per package: its **earliest** compromised version. Later compromised versions of the same package
  are a sensitivity analysis.
- **Campaign:** compromised versions are grouped by shared payload, meaning a byte-identical added or changed file
  across packages, or the same DataDog campaign note. Shai-Hulud alone spans hundreds of packages, so all
  inference is campaign-clustered and at most 10 packages per campaign enter the primary sample (chosen by the
  lowest sha256 of the package name, not by inspection).

**History (negatives).** For each positive package, the version list and publish times come from the registry.
- The window is the last **20** release transitions before the first compromised version (fewer if the package has
  fewer).
- A package with fewer than **8** prior transitions is excluded and counted.
- A transition is consecutive versions by publish time, pre-releases included, as published.
- The artifact type matches the positive's: npm tarball; for PyPI, the same kind (sdist or wheel) as the
  DataDog sample.

**Selection bias, stated.** DataDog's samples were mostly found by GuardDog, so they may over-represent
compromises that already look malicious to a pattern scanner. A pass here does not show REL catches the quiet ones.
The 2018 to 2022 classics (event-stream, ua-parser-js, coa, rc, eslint-scope, ctx, xz) have no obtainable malicious
artifact from this source and are not in the sample.

**Handling.** Samples are encrypted zips. They are extracted only into an isolated local directory, never installed,
imported or executed, and never committed, cached in CI, or quoted in this public repo. Only aggregate results and
package names and versions (already public in the dataset and in news reports) are published.

## Scan

- Engine: gitgalaxy pinned at the commit current when this is registered (recorded in the scorer), default
  configuration, `GITGALAXY_DISABLE_GIT_HISTORY=1`. The default engine is the point: this is what a user would run.
- Known engine limits that will cost recall, accepted rather than patched: the minification gate skips files with
  very long lines (aperture Gate 4.1), and the security lens blanks lines of 250+ characters (gitgalaxy#8429).
  Skipped files are still recorded in `excluded_artifacts`, which component C4 uses.
- An artifact the engine fails to scan scores as not detected (the conservative direction) and is reported.

## The score (fixed now, no tuning)

For a transition from release B to release A, computed on A's published contents compared with B and with all
earlier releases in the package's window:

- **Changed functions:** functions in A whose key (relative path, qualified name) is new, or whose normalized body
  hash differs from B.
- **C1, shape novelty:** the share of changed functions whose signal set (function-level signals, gitgalaxy#8012
  absent signals dropped) never occurs in any function of any earlier release in the window.
- **C2, grammar break:** the share of changed functions in the bottom 10% of population grammar fit for their
  language, size and signal count (the GR strata used in agents_lattice).
- **C3, security mass:** the increase from B to A in file-level threat signal counts. The counted signals are
  `reflection_metaprogramming`, `high_risk_execution`, `safety_bypasses`, `self_propagation`, `hardcoded_secrets`,
  `unicode_steganography`, `homoglyphs` and `entropy`, plus network I/O; decreases count as 0.
- **C4, refused files:** the number of files in A that the engine excluded as `oversized_minified`, `binary_payload`
  or `generated_noise` and that are new (no file at that path was excluded in any earlier release in the window).
- Each component is ranked within its own package across that package's transitions, malicious one included
  (average ranks for ties, scaled to 0–1).
- **S (composite)** = the mean of the four within-package ranks.
- **S_culture** = the mean of the C1 and C2 ranks.
- **Within-package percentile** of the malicious transition = the share of the package's benign transitions with a
  strictly lower score, plus half of the ties.

## Hypotheses

- **H-REL-1 (primary, the practical tool):** the malicious transition ranks high on S within its own package.
- **H-REL-2 (key secondary, the culture question):** the same for S_culture, the lattice and grammar alone.

Each is tested and judged separately; H-REL-2 has its own bar so a pass on S carried only by C3 or C4 cannot be read
as a culture result.

## Verdict rules (decided now)

A hypothesis **passes** only if all three hold:
1. **Rank:** the median within-package percentile of malicious transitions is ≥ 0.95.
2. **Beats size:** within-package percentile of the score exceeds the within-package percentile of a **size
   placebo** (changed lines of code, same ranking) on the paired comparison. The campaign-clustered bootstrap 95%
   interval of the mean paired difference (2,000 draws, seed 2026) excludes 0.
3. **Beats chance:** a permutation control (the malicious label moved to a random transition within each package,
   2,000 draws) puts the observed median above the permutation's 99th percentile.

**Kill rule.** If H-REL-1 fails, the "release unlike its history" line is dropped as a security product claim. If
H-REL-1 passes but H-REL-2 fails, GitGalaxy's culture signal adds nothing here and the result is credited to C3 and
C4 only.

**Minimum sample.** At least 20 eligible positive packages from at least 5 campaigns. Below that, REL is reported as
descriptive only.

## Comparators (reported, not part of the verdict)

- **Install-hook rule:** an npm `preinstall`/`install`/`postinstall` script added or changed, or a PyPI `setup.py`
  that gains network or exec calls. A one-line heuristic that many tools already use.
- **GuardDog** (Apache-2.0), run on A, using the same within-package ranking by number of rules hit.
- **Alarm burden:** at the threshold "top-ranked transition in its package", the share of benign transitions across
  all packages that would alarm.

## Sensitivity and exploratory (labelled, never verdicts)

- All compromised versions per package, not just the earliest.
- No per-campaign cap.
- Each component alone (C1 to C4).
- Window of 10 and of all available history.
- npm and PyPI separately.

## Order of work

1. Owner approves this draft; it is registered with the engine pin and committed.
2. The candidate list, campaign assignment and history windows are built from metadata alone and committed
   (`docs/rel_inputs.json`), before any sample is extracted.
3. `tools/rel_eval.py` is committed.
4. Samples are fetched, extracted in isolation and scanned; the scorer runs once; results go to `docs/rel.md` and the
   journal.
