# REL: does a compromised release look unlike the package's own history? (DRAFT, 2026-11-13)

**Status: DRAFT v3 (after two independent reviews and the owner's decisions of 2026-11-14). Not registered. No
outcome data has been read: no malicious sample has been downloaded, extracted or scanned.** The pre-assessment
numbers come from registry and dataset metadata only. Before registration, a **positive-control dry run** on benign
packages only (see "Positive-control dry run") must show every component can be non-zero end to end. The scorer
(`tools/rel_eval.py`) is committed after registration and before any run on positives.

## Plain-language summary

When attackers take over a popular package, they publish a new version with their code inside. GitGalaxy can read a
project's habits (which kinds of code it writes, in which combinations, importing what). REL asks whether the hacked
version looks like it was written by a stranger: is it the most unusual release in the package's recent history,
and can an alarm fire on it without also firing on ordinary releases all the time?

## Why

GitGalaxy's security layer has no measured detection rate (gitgalaxy#8426, epic gitgalaxy#8427), and its pattern
rules mostly duplicate other tools. What this program has shown is that code carries a stable, readable culture:

- a program's lattice family mix identified its authoring model 84% of the time (chance 28%; agents_lattice);
- GitGalaxy's own Gemini-era and Claude-era code separate at AUC 0.88 (gg_lattice; a within-Claude-era drift
  reference gives 0.71, so part of that is drift, not authorship);
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
- Known engine weakness that lowers expectations: the security lens misses common exec and network idioms
  (`cp.exec(...)`, `require('child_process').exec(...)`, `https.get(...)` score nothing; gitgalaxy#8433). REL runs the
  engine as pinned and does not patch the lens mid-study, so C3 is expected to be near zero for many payloads.
- The two reviewers' forecasts for the v2 design differed widely (H-REL-1: 72% vs 15%; H-REL-2: 28% vs 4%; H-REL-3:
  18% vs 6%). Both are recorded in the review log to be scored against the outcome.

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
  packages. Packages are also merged when their compromise dates fall within the same 3-day window and either (a) the
  dataset notes name the same incident, or (b) each added a file with the same basename whose sizes are within 5%
  (so a worm that mutates its payload is one campaign, not many). Otherwise a package is its own campaign. The number
  of campaigns under "3-day window only" is reported as a lower bound on G. Campaign assignment is computed by script
  (file hashes, names and sizes only; no scan, no score) and committed before scoring.
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
- **Artifact-source check (stop rule):** every positive comes from a DataDog zip and every benign artifact from a
  registry tarball, so any packaging difference is perfectly confounded with the label. For each npm positive whose
  compromised version is still in the registry (about 25), the zip's and the registry tarball's file-hash sets must be
  identical after root normalization; **if any differ, the study stops** and the zip handling is fixed and
  re-registered. For every positive, the share of B's files present byte-identical in A is reported; positives below
  50% are excluded and counted.

### D2. History: each positive package's own previous releases

- From the registry's version list and publish times: the last **20** release transitions before the first
  compromised version (fewer if the package has fewer), plus up to **5** preceding baseline releases ($v_{-4}, \dots, v_0$)
  so that the earliest scored transition $t_1 = (v_0 \to v_1)$ has the same 5-release trailing novelty horizon as later
  transitions.
- **Predecessor rule:** a transition ends at release A; its predecessor B is the highest version (by semver for npm,
  PEP 440 for PyPI) below A **within the same major line**, published before A. This stops a 1.x backport published
  after 3.x from being diffed against 3.x. If A starts a new major line, B is the highest earlier version overall.
  Pre-releases are included. The same rule applies to positives, histories, D3 and D3b.
- A package with fewer than **8** prior transitions is excluded and counted.
- Artifact type matches the positive's: the npm tarball; for PyPI, the same kind (sdist or wheel) as the sample.
- A history release that fails to download or scan drops both transitions that touch it, counted. A positive whose B
  fails is excluded and counted.

### D3. Calibration: ordinary packages with no known compromise

Needed because ranking within a package always crowns one "most unusual" release, so a within-package rule alarms on
about 1 in 21 ordinary releases. D3 sets an absolute alarm threshold.
- The top **450 npm** and top **300 PyPI** packages by downloads (lists frozen in `docs/rel_inputs.json`), minus any
  package that appears in the DataDog manifests, a fixed list of publicly known compromises, or OSV malicious-package
  reports. Sources: npm, `wooorm/npm-high-impact` (MIT, commit 9e29478); PyPI, downloads from **2026-10-01 to
  2026-10-30** from ClickHouse's public mirror of PyPI's download logs (`pypi.pypi_downloads_per_day`), counted per
  project with explicit name filters, and cross-checked against pypistats.org (boto3 and requests within 5%). The
  set was enlarged from 300 + 200 after the 29-release recount. With the v3 design (46 releases, scale and threshold
  halves, primary α = 1/200) the counts are recounted before registration.
- **History length matched to D1:** for each package, up to the last **46** releases: 5 baseline releases (novelty
  horizon), 20 burn-in transitions (standardization history), and up to 20 scored transitions, so a scored D3
  transition has the same horizons as a D1 positive. Packages with fewer releases score the transitions that have at
  least 8 earlier transitions, as for D1. The share of scored transitions by number of predecessors is reported for D1
  and D3 side by side.
- **Two halves by package-name sha256:** the **scale half** sets each component's reference distribution for D
  (see "Alarm score"); the **threshold half** sets the alarm threshold. Neither half is used to choose components.
- **Ecosystem thresholds:** the npm threshold is primary for npm positives and the PyPI threshold for PyPI positives;
  the pooled threshold is reported.
- Any single artifact over 250 MB is skipped and its transitions counted as unscored (none is expected: no D3
  package averages over 100 MB per release).

### D3b. Matched controls: ordinary packages that look like the positives

D3 is popular, well-maintained packages; the positives are mostly long-tail, often scoped npm packages. A threshold
set on D3 alone may not hold for them. For each positive, **5 controls** are drawn from the same registry, in the same
release-count bin (8–19, 20–45, 46+) and unpacked-size bin (quartiles of the positives), excluding any package in
the DataDog manifests or OSV malicious reports, chosen in sha256 order of the package name from the registry's full
name list. Controls are scored exactly as D3. **H-REL-3 is judged on D3 and reported on D3b**; if the D3b alarm rate
at the D3 threshold exceeds twice the target, that is stated in the headline.

### D4. Prospective confirmation: attacks found after registration

Compromised-library samples that DataDog adds after the registration date, through **2027-05-13**, are scored once
with the frozen score and threshold, under the same eligibility rules. This is the cleanest test of "would it catch
an attack nobody had seen when the method was fixed". Reported as its own result. D4 is **descriptive unless it
reaches at least 10 campaigns**; if it has not by 2027-05-13, collection extends to 2027-11-13, and then is reported
as descriptive whatever its size.

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
- Extraction and scanning run as an unprivileged user with networking disabled for the process (a network namespace
  with no interfaces), into a directory mounted `noexec`, **outside any git work tree** (inside one, the engine lists
  files with `git ls-files` and sees none of them).
- Extraction refuses symlinks, hard links, absolute paths and `..` components, and caps total extracted size.
- Samples are never opened in an editor or any tool with plugins; only the scanner and hashing read them.
- File hashes are published only for files already listed in DataDog's public manifest.
- The engine is the owner's own (PolyForm Noncommercial without a key); scans run with the owner's
  `GITGALAXY_LICENSE_KEY`, which also skips the 5-second unlicensed delay.

## Scan

- **Engine:** gitgalaxy pinned at the commit current when this is registered (recorded in the scorer), full install
  (all optional engines present; the install mode is recorded), `GITGALAXY_DISABLE_GIT_HISTORY=1`, run outside any
  git work tree, with the owner's licence key.
- **One declared non-default setting (owner decision, 2026-11-14):** a committed config
  (`docs/rel_engine_config.*`, referenced by hash) that
  1. removes `dist`, `build` and `out` from the ignored directories, because most published npm code lives there and
     the default engine silently drops it;
  2. empties the filename denylist for JS bundles (`*.min.js`, `*bundle.js`, `chunk-*.js`, `jquery*.js`), so these
     files are judged by the engine's content gates instead of by name. A name rule would "detect" Shai-Hulud 1, whose
     payload was called `bundle.js`, by knowing its name.

  Everything else is the default. The dry run must show both changes take effect.
- **Default-config sensitivity:** positives and their histories are also scored with the unmodified default
  configuration, and the result is reported beside the main one, so the cost of the engine's default blind spots is
  visible.
- **Hidden share:** for each positive, the share of `.js/.mjs/.cjs/.ts/.py` bytes under directory names the engine
  still ignores (for example `vendor`, `docs`, `coverage`) is computed from the archive and reported. Packages with
  more than 50% hidden form a required slice.
- **Known engine limits accepted as they are:** the security lens's blind spots (gitgalaxy#8433) and blanking of lines
  of 250+ characters (gitgalaxy#8429). These are not patched during the study.
- An artifact the engine fails to scan scores as not detected for a positive (the conservative direction) and drops
  the adjacent transitions for history; both are counted.

## The fixed score (decided now, no tuning)

For a transition from release B to release A of package p, with $H_L$ the last 5 releases ending at B (the novelty
horizon) and $H_{\text{clean}}$ the transitions before this one (up to 20, at least 8; the standardization history):

**Units.**
- **Function units:** rows of `function_data` keyed by (normalized relative path, enclosing class name or empty,
  function name, ordinal by start line among rows with the same first three fields). A unit is *changed* if its key
  is new in A or its signature (loc, complexity, args, and the counts of `REL_SHAPE_SIGNALS`) differs from B.
  `token_mass` is not used (it is NULL in zero-dependency installs).
- **Residual unit** `__rel_residual__` per file (renamed so it is not confused with the engine's own
  `__global_context__` rows): residual LOC = max(0, file coding LOC − sum of its function units' LOC); residual counts
  = max(0, file count − sum of function counts) per signal. It is changed if the file is new or its residual tuple
  differs from B, and it is used only when residual LOC ≥ 3. It holds top-level code, anonymous callbacks and
  default-exported functions the extractor does not name. Nested functions can double-subtract; the max(0, ·) clamp
  absorbs that, and it is stated here as a known imprecision.
- **F(A)** = the changed function units and residual units of A.

**`REL_SHAPE_SIGNALS`** (the signals that define a "shape"): the numeric columns of `function_data` whose names start
with `struct_`, `arch_`, `state_` or `def_`, minus the columns absent at function level (gitgalaxy#8012), minus
`kw_eval.STYLE`. The list is computed from the pinned engine's schema and committed in `docs/rel_inputs.json`. The
scorer asserts each column exists and is numeric (`PRAGMA table_info`) and aborts otherwise. No `threat_*` or `sec_*`
column is in it.

**Components.**
- **C1, new shapes** = |{u ∈ F(A) : shape(u) ∉ shapes of all units in releases of $H_L$}| / (max(1, |F(A)|) + 2),
  with shape(u) = the set of `REL_SHAPE_SIGNALS` with count > 0. Residual units are compared only with residual units.
- **C2, grammar breaks** = the share of F(A) (units with loc ≥ 3 and ≥ 2 shape signals), smoothed the same way, whose
  grammar-fit percentile is ≤ 0.10.
  - Grammar fit is computed by `tools/rel_grammar.py`, committed with its sha256 before registration. It reuses the
    pairwise observed/expected scoring of `tools/gr_eval.py`.
  - Its **reference population** is the function units of the D3 scale-half packages at their first in-window
    release, scanned with the pinned engine, for each language with at least 2,000 such units (expected: JavaScript,
    TypeScript, Python). Units in any other language get no C2 contribution, counted.
  - Strata are (language, size bin, signal-count bin), merged to the nearest size bin until each has at least 200
    units.
  - Residual units are scored against a separate population of residual units.
- **C3, new security hits** = $\sum_{f \in A}\sum_{s} \max(0, \text{count}_{A,f,s} - \text{count}_{B,f,s})$ (per file,
  0 for new files' B counts) over these `file_data` columns:
  - `threat_obfuscated`, `threat_eval_exec`, `threat_bypasses`, `threat_private_info`, `threat_homoglyphs`;
  - `threat_entropy`, `threat_network_hooks`, `threat_stego_imports`, `threat_extension_mismatch`;
  - `threat_env_mutation`, `sec_self_propagation`, `sec_unicode_steganography`.

  Excluded, with reasons:
  - `threat_tainted_injection`: retired, always 0 (#3101).
  - `threat_crypto_math`: bitwise math, common in benign code and already a structural habit in C1.
  - `threat_db_sinks`, `threat_api_near_db_sink`: about 0% precision (#3018/#3019).
  - dead code: commented-out, not executable.

  The scorer asserts each column exists. A renamed file counts all its hits as new; renames are reported.
- **C4, new content-refused files** = files in A, at a normalized path where no file was refused in $H_L$, whose
  `excluded_artifacts.exclusion_reason` starts with one of:
  - `Blocked (Saturation:`, `Blocked (Binary Format Detected)`, `Blocked (Embedded Hex Payload`;
  - `Blocked (Embedded Array/Matrix Payload`, `Blocked (Monolithic Amalgamation`;
  - `Blocked (Machine-Generated Source Code Signature`, `Blocked (Lexical Monotony`, `Blocked (File size exceeds`;
  - `Packed Payload Guard (`, `Unparsable (`, `Thread Timeout (`.

  These are judgments about a file's **content**. Refusals by extension, path or filename (`Blocked (Explicitly
  Denied Extension`, `Blocked (Unsupported Extension`, `Blocked (System Exclusion…`) are not in C4. They are reported
  separately as **C4-path**, outside every score. The archetype, `binary_anomaly` and `obfuscation_flag` columns are
  not used: the first is overwritten for any file with code, and the other two are derived from C3's signals.
- **C5, new imports** = the number of distinct normalized module names in A's `file_data.raw_imports` that appear in
  no release of $H_L$. Normalization:
  - strip a `node:` prefix;
  - a scoped JS name keeps `@scope/name`;
  - otherwise keep the first `/`-separated segment (JS) or the first `.`-separated segment (Python);
  - drop names starting with `.`, `/`, `#`, `~` or `@/`, and drop the package's own module names.
- **Size placebos:**
  - **Z** = changed coding lines from B to A in files the engine reads;
  - **Z_bytes** = total bytes of files in A whose sha256 is not among B's files;
  - **Z_files** = the number of such files.

  Z_bytes and Z_files come from the archives, not the engine, so they see refused and ignored files too.

**Within-package rank.** For each component, all of the package's scored transitions (malicious one included) are
ranked, average ranks for ties, scaled to [0, 1]: $r_c = (\text{rank} - 1)/(n_p - 1)$.

- **S** $= \frac{1}{5}\sum_{c=1}^{5}\max(0,\, 2r_c - 1)$. A component at or below its package median contributes 0
  instead of pulling the score down, so a payload that moves one or two components is not penalized for leaving the
  others quiet. (The v2 mean of ranks is reported as a sensitivity.)
- **S_culture** $= \frac{1}{2}\big[\max(0, 2r_{C1} - 1) + \max(0, 2r_{C2} - 1)\big]$.
- **S_culture_imports** adds C5 the same way. Reported, not judged.
- **Percentile:** $P_X(p) = (\#\{b : X(b) < X(m)\} + \tfrac12\#\{b : X(b) = X(m)\})/K_p$ over the $K_p$ benign
  transitions b.
- **Top-1 (integers):** $\text{Top1}_X(p) = 1$ iff $\#\{b : X(b) > X(m)\} = 0$ and $\#\{b : X(b) = X(m)\} \le 1$.

**Alarm score D (H-REL-3).**
- Each count component and placebo is log-stabilized, $\tilde c = \ln(1 + c)$; C1 and C2 are used as they are.
- **Deviation:** $e_c(t) = \tilde c(t) - \text{median}_{H_{\text{clean}}(t)}(\tilde c)$, against predecessors only.
- **Reference:** the deviations of all scored transitions in the D3 **scale half**, per ecosystem.
- **Survival:** $q_c(t) = \big(\#\{\text{ref} > e_c(t)\} + \tfrac12\#\{\text{ref} = e_c(t)\} + \tfrac12\big)/(N_{\text{ref}} + 1)$.
- **D** $= \max_{c \in C1..C5} -\log_{10} q_c(t)$; **D_culture** = the same over C1 and C2.

The maximum means one extreme component is enough. No scale floor or weight is chosen by hand.

**Threshold.**
- $\tau_\alpha$ is the smallest value with $\#\{t \in \text{threshold half} : D(t) > \tau\}/N \le \alpha$, per ecosystem.
- Alarm iff $D > \tau_\alpha$.
- **Primary α = 1/200** (owner decision, 2026-11-14); α = 1/1,000 is reported.

## Hypotheses

- **H-REL-1 (primary):** compromised releases rank first in their own package's history on S, beyond release size,
  chance, **and a one-line install-hook rule**.
- **H-REL-2 (culture):** the same for S_culture (shape and grammar only).
- **H-REL-3 (alarm):** at the 1-in-200 threshold, D catches at least half of the compromised releases.

## Verdict rules (decided now)

G is the number of campaigns with at least one eligible positive. For campaign g:
- $\overline{\text{Top1}}_X(g)$ and $\bar P_X(g)$ are the means over its packages;
- $T_X = \frac1G\sum_g \overline{\text{Top1}}_X(g)$ is the campaign-equal Top-1 share.

**Minimum sample:** at least 20 eligible packages from at least **10 campaigns**. Below that, REL is descriptive
only. (With 5 campaigns the smallest possible one-sided sign-flip p is $2^{-5} = 0.031$, so rule 2 could never
pass.)

**Intervals.**
- For G ≥ 20: a campaign-clustered bootstrap (2,000 draws, seed 2026).
- For G < 20: an exact Clopper–Pearson lower bound on the share of campaigns with $\overline{\text{Top1}}_X(g) \ge 0.5$.

**Sign-flip tests.**
- One-sided, over campaigns.
- All $2^G$ flips are enumerated when G ≤ 20.
- Otherwise 100,000 random flips, with $p = (b + 1)/(B + 1)$.

**H-REL-1 and H-REL-2 pass** only if all hold:
1. **Rank:** $T_X \ge 0.50$, and its lower bound (per "Intervals") is $\ge 0.35$.
2. **Beats size:** against **each** of Z, Z_bytes and Z_files, the campaign-equal mean of
   $\Delta_g = \bar P_X(g) - \bar P_{\text{placebo}}(g)$ is > 0, with sign-flip p < 0.025. For G ≥ 20 the bootstrap
   interval must also exclude 0.
3. **Beats chance:** a permutation test with 2,000 draws.
   - In each draw, one $u \sim U(0,1)$ is drawn per campaign.
   - In every package of that campaign, the label moves to the transition at position $\lfloor u(K_p + 1)\rfloor$ in
     time order.
   - The observed $T_X$ must exceed the 99th percentile of the permuted $T_X$.
4. **Beats the install-hook rule (H-REL-1 only; owner decision, 2026-11-14):**
   - The rule fires when an npm `preinstall`/`install`/`postinstall` script is added or changed, or a PyPI
     `setup.py` / `pyproject.toml` build hook gains network or process-exec calls.
   - Its Top-1 uses the same integer definition: it fires on m and on at most one benign transition.
   - The campaign-equal mean of $\overline{\text{Top1}}_S(g) - \overline{\text{Top1}}_{\text{hook}}(g)$ must be > 0,
     with sign-flip p < 0.025.

**H-REL-3 passes** if campaign-equal recall of D at $\tau_{1/200}$ is ≥ 0.50, with a lower bound ≥ 0.30.
- For G ≥ 20 the lower bound comes from a joint bootstrap. Each draw resamples the D3 scale half and threshold half
  by package, and D1 by campaign. Each draw recomputes the reference distributions and $\tau^*$.
- For G < 20 it is the Clopper–Pearson lower bound on campaigns with mean recall ≥ 0.5.
- Recall is also reported at 1/100, 1/1,000 and 1/2,000, on D3b, and per ecosystem.
- A D3 diagnostic reports whether any single package holds more than 2 of the top 10 D3 values.

**Kill rule.**
- **H-REL-1 fails, including by not beating the install-hook rule:** "release unlike its history" is dropped as a
  GitGalaxy security claim. If it fails only on rule 4, the conclusion is that GitGalaxy adds nothing over a one-line
  rule.
- **H-REL-1 passes and H-REL-2 fails:** the culture signal adds nothing here.
- **H-REL-1 passes and H-REL-3 fails:** the method can rank but cannot alarm at a usable rate. It may still serve to
  order a review queue.

## The numbers behind the bars

- **Top-1 and chance.** Top-1 means the hacked release is strictly first among its package's $K_p + 1$
  transitions, or tied for first with one benign one. Under the null its chance lies between $1/(K_p+1)$ and
  $2/(K_p+1)$: about 0.05–0.10 at K = 20 and 0.11–0.22 at K = 8. Results are reported by K.
- **Binomial.** For 20 independent units at p = 1/21, $P(\ge 10 \text{ first}) = 7.12\times10^{-9}$; at p = 2/21,
  $4.60\times10^{-6}$. Significance is not the hard part; the bars are on effect size.
- **Power** (reviewer 2's simulation).
  - With G = 33 the bootstrap's one-sided coverage is 0.975, and the chance of passing rule 1 when the true $T_X$ is
    0.50 is about 0.43. In effect, rule 1 needs a true $T_X$ of about 0.6.
  - Clopper–Pearson lower bounds ≥ 0.35 need 18 of 33, 12 of 20, 10 of 15 or 8 of 10 campaigns.
- **Alarm rate.**
  - About 10,000 scored D3 transitions split into halves of about 5,000: 1/200 rests on about 25 exceedances per
    half, and 1/1,000 on about 5. That is why 1/200 is primary and 1/1,000 only reported.
  - At 1/200, a registry with 50,000 new releases a day would see about 250 alarms a day. That is a review queue,
    not a stand-alone gate, and it is described that way.

## Exploratory: does the whole fingerprint add anything? (labelled, never a verdict)

- **Features:** everything the engine records, as within-package deviations against predecessors: all numeric signal
  columns, call-graph changes (new outbound edges, new callees to I/O, process or eval functions), complexity,
  nesting, size, comments, naming and dependency-graph changes.
- **Split:**
  - campaigns split in two by sha256 of the campaign id;
  - D3 split in two by package-name sha256, so the threshold is set on the training half's D3 and evaluated on the
    test half's.
- **Model:** L2-regularized logistic regression, with strength chosen by campaign-grouped inner cross-validation on
  the training half.
- **Comparison:** on the same test halves, against the fixed S and D **and** against a three-feature logistic model
  (Z_bytes, Z_files, install-hook). A win over the fixed score that is not also a win over the three-feature model is
  reported as "size and install hooks", not as fingerprint signal.
- **Swap:** the halves swap and both results are reported. A win on both halves leads to a separate registration
  tested on D4.

## Comparators (reported at matched alarm rates; the install-hook rule is also in rule 4)

- **Install-hook rule:** as defined in rule 4.
- **GuardDog** (Apache-2.0), run on B and A: new findings in A, $\max(0, \text{hits}_A - \text{hits}_B)$ per rule.
- **Size baselines:** Z_bytes and Z_files.
- **"New file at the package root".**
- **"New executable-language file plus a changed manifest script".**

## Sensitivity (labelled, never verdicts)

- The default engine configuration (no `dist/build/out` change, filename denylist on).
- The v2 aggregation (mean of ranks) for S.
- All compromised versions per package; no per-campaign cap; package-weighted pooling.
- Each component alone; S_culture_imports.
- Unsmoothed C1/C2 denominators; a cumulative novelty horizon; windows of 10 and of all history.
- Campaigns by 3-day window only (the lower bound on G).
- npm and PyPI separately.

## Required slices (reported with the verdicts, so a pass cannot hide where it comes from)

- **Quiet compromises (primary definition):** positives where GuardDog's new findings are 0. Also reported:
  C3 = 0 and C4 = 0.
- **Manifest-only compromises:** the only change is in `package.json` / `setup.cfg` / `pyproject.toml`. These are
  invisible to the engine by design; their count and the install-hook rule's result on them are reported.
- **Name-only leakage check:** Top-1 excluding positives whose only new content-refused file has a name matching the
  default filename denylist.
- **Hidden share > 50%** (see "Scan").
- **By component:** which components put each positive at the top.
- **By K_p:** because the chance level varies with history length.

## Positive-control dry run (before registration; benign data only)

The four schema errors found in review would each have made a component silently zero. The dry run proves every
component can fire end to end before anything is registered.

**Data.**
- 20 D3 packages (10 npm, 10 PyPI, by sha256 order), with their last 8 releases from the registry.
- No positive sample is touched.

**Synthetic variants.** These are written by the author, are inert, have no network target, and are never executed.
Each is applied to the latest release of each package:
1. A new readable source file in the package's language, with new function shapes and new imports (for example
   `child_process`, `subprocess` or `socket`).
2. A top-level-only injection into the package's main file.
3. One line of `eval(atob("…"))` (JS) or `exec(base64.b64decode("…"))` (Python).
4. A minified one-line file under `dist/`.
5. A binary blob file.
6. A `package.json`-only `postinstall` addition (npm) or a `setup.py` hook change (PyPI).
7. The unchanged release, re-packed as a zip, to test the zip-vs-tarball normalization (the hash sets must be
   identical).

**Pass criteria.**
- C1, C2 and C5 fire on variant 1.
- The residual unit fires on variant 2.
- C3 fires on variant 3 (JS), and its result on the Python form is recorded.
- C4 fires on variants 4 and 5, with the `dist/` file reaching the content gates.
- The install-hook rule fires on variant 6.
- Z_bytes and Z_files are non-zero on variants 1–6.
- Variant 7 shows identical hash sets and all components at 0.
- All column assertions pass.
- D, the thresholds and every test statistic compute without error on the dry-run data.

**Outcome.** Results go to `docs/rel_dryrun.md`. Any failure is fixed in the definitions and the dry run is repeated
before registration. Variants 1–6 are never used to tune weights or thresholds; they only prove the plumbing.

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

### Second review: Claude Fable 5.2 (2026-11-14) and the owner's decisions

An independent subagent read only the review packet and the draft at `adc1958`. It checked definitions against
gitgalaxy `origin/main` 868bedc9 and ran the engine on small benign synthetic packages. Its verdict was **redesign
(targeted)**; the full review is on PR #184.

The author re-verified its central claims in code or by running the engine:
- the database renames the security columns to `threat_*` (`record_keeper.SHORT_KEY_MAP`). The first author response
  had wrongly said the `sec_*` names were verified: it had checked the internal schema, not the database;
- `dist`, `build`, `out` and `vendor` are ignored directories;
- the filename denylist includes `*bundle.js`, and path gates share the `Blocked (` prefix;
- `Packed Payload Guard` is a separate refusal reason;
- the security lens scores nothing for `cp.exec`, `require('child_process').exec` and `https.get` (added to
  gitgalaxy#8433).

Reviewer 2's forecasts for v2: H-REL-1 15%, H-REL-2 4%, H-REL-3 6%, exploratory model beats the fixed score 35%;
median P 0.80 for S and 0.55 for S_culture.

**Owner decisions (2026-11-14):**
1. Scan `dist`, `build` and `out` (declared config; the default-config result is reported alongside).
2. Primary alarm rate 1/200, with 1/1,000 reported.
3. H-REL-1 must also beat the install-hook rule (rule 4).
4. Adopt the reviewer's improvements.

**What changed in v3** (reviewer finding → change):

| Finding | Change |
|---|---|
| F1 | C3 uses the real `threat_*` / `sec_*` database columns, with existence assertions; exclusions are stated with reasons. |
| F2 | Shapes use a committed allowlist, `REL_SHAPE_SIGNALS`; no security column is in it. |
| F3 | C4 counts only content-based refusals by explicit reason list. Name and path refusals are reported as C4-path. The archetype and derived flags are dropped. The filename denylist is emptied in the REL config. |
| F4 | `dist/build/out` are scanned via the declared config. Scans run outside any git tree. The hidden share is reported. The install mode is recorded. |
| F5 | S and S_culture use $\max(0, 2r - 1)$; the mean of ranks becomes a sensitivity. |
| F6 | Z_bytes and Z_files are added; rule 2 must hold against all three placebos. |
| F7 | C2 gets its own committed code and JS/TS/Python populations from the D3 scale half at the pin, with merged strata and a separate residual population. |
| F8 | Function key (path, class, name, ordinal). The residual unit is renamed `__rel_residual__`; its known imprecision is stated. |
| F9 | D = max of −log10 empirical survival per component, with a scale half and a threshold half. D3 fetches 46 releases. Ecosystem thresholds are primary. D3b matched controls are added. |
| F10 | Minimum of 10 campaigns. Exact sign-flip enumeration for G ≤ 20. Clopper–Pearson for G < 20. Shared-u permutation defined. |
| F11 | Artifact-source stop rule. Byte-identical B-share gate. Same-major-line predecessor rule. |
| F12 | C5 normalization fixed. |
| F13 | Integer Top-1. Pinned quantile rule. Scan-failure handling. Drift reference in "Why". |
| Q4–Q10 | Name-only leakage slice. Campaign merging for mutating worms. GuardDog-delta quiet slice. D4 descriptive unless G ≥ 10. Exploratory model compared with a 3-feature baseline. New comparators. Safety handling. |
| §5 | **Positive-control dry run** before registration. |

## Order of work

1. **Recount** D3 and D3b for 46 releases and the scale/threshold split, from metadata only.
2. **Build and run the positive-control dry run** (benign packages and synthetic variants only), including
   `tools/rel_grammar.py`, the REL engine config and the column assertions. Results go to `docs/rel_dryrun.md`. Fix
   and repeat until it passes.
3. **Owner approval of v3** with the dry-run report. Registration: the status line becomes REGISTERED with the
   engine pin and the config and grammar-code hashes.
4. **Inputs committed** (`docs/rel_inputs.json`): positives, history windows, D3, D3b, and campaigns. Campaigns use
   file hashes, names and sizes from inside the samples, with no scan and no score, committed before step 5.
5. **`tools/rel_eval.py` committed.**
6. **Run.** Samples are fetched, extracted in isolation and scanned, and the scorer runs once. Results go to
   `docs/rel.md` and the journal. D4 is scored on or after 2027-05-13 (2027-11-13 if extended).
