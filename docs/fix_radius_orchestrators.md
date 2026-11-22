<!--
Exploratory write-up, following docs/_experiment_template.md. Claims no p-values as confirmatory verdicts.
-->

# Call-graph position vs fix history: orchestrators, fan-out and the fix radius (30 repos, C / Go / Java)

**Type:** exploratory (no registration in `docs/HYPOTHESES.md`; see "What this is not")
**Registered:** informally. Hypotheses were written to a session text file before each wave's analysis ran (archived at `docs/fix_radius_orchestrators/PREREGISTERED.txt` and `PREREGISTERED_EXT.txt`). They were **not committed before the analysis**, so there is no external timestamp, and they did not go through the two-review process (checklist item 15).
**Predictor(s):** function call-graph position from GitGalaxy 981e9ec (fan-in, fan-out, fan-in ratio, betweenness, PageRank, chain depth and height, cycle membership), plus file-level producer ratio and role.
**Outcome:** per-function fix touches and per-file fix counts from commit-subject keywords, with an **any-commit** control (label-free).
**Repos:** wave 1, 8 C (curl, redis, nginx, openssl; libuv, libgit2, git, haproxy). Wave 2, 22 more: C (memcached, tmux, lua, libssh2, mbedtls, zstd), Go (caddy, prometheus, hugo, fzf, cli, traefik, grpc-go, gin), Java (commons-lang, commons-io, jsoup, jackson-databind, guava, mockito, maven; okhttp skipped, Kotlin).
**Tool:** `tools/fixgraph/` (numpy and networkx; **not** stdlib-only, see its README)   **Data:** none committed. Results: `docs/fix_radius_orchestrators/results/`.
**Companion work in gitgalaxy:** issues #8955 (neighbourhood view), #8956 (C indirect calls), #8957 (metric caveats), #8958 (this study as a committed tool).

## What this is not

- **Not a registered study and not confirmatory.** The label is below this repo's own bar (next section). Every fix-specific number is descriptive.
- **Not a bug predictor.** Effects are 10-25% over a size baseline. Programme standing (`PROGRAMME_call_networks.md`: *history predicts, structure describes*) is unchanged; this reads as consistent with it.
- **Not run through `docs/STUDY_CHECKLIST.md`.** The checklist status is below, item by item, including the items that were not done.

## The label problem (read this first)

`docs/LABEL_CARD.md`: no study may use a fix label whose precision on that repo is unpublished; below 0.70 a label is descriptive. This study used commit-subject keywords:

- **orig:** `fix|bug|CVE-|crash|overflow|leak|use-after|uaf|segfault|regression|out-of-bounds|oob|null deref|double free|heap|stack`.
- **B** (primary): `fix|bug|regression`, minus any subject mentioning leak, free, overflow, heap, stack, oob, null, double, memory, alloc, dangling, refcount.
- **D** (control): every non-merge commit that touches the language's source files. **Label-free.**

Neither orig nor B is the card's raw or v3c label, and **their precision was not measured on any of the 30 repos**. Where the card has numbers for a repo in this study, the raw-label precision it publishes is below the bar for curl (0.63), libgit2 (0.63), openssl (0.50), prometheus (0.40) and commons-lang (0.27), and clears it for redis (0.73); v3c clears it for all of those except libgit2 (0.60). The other 24 repos are not on the card.

Consequence for reading: **the D control is the result that does not depend on the label.** Where D and B agree, the effect is change-proneness, not specifically fixes (that is what the data show, below). Where they differ (the lifecycle result), the difference is the label.

## Prior work

From `PROGRAMME_call_networks.md` and from memory; **not re-read for this write-up, verify before relying**: Zimmermann and Nagappan 2008 (network measures on dependency graphs predict defects), Premraj and Herzig 2011 (replication; network measures add little over code measures), El Emam et al. 2001 (size confounds object-oriented metric-to-fault results), Henry and Kafura 1981 (fan-in times fan-out as a complexity measure), Li and Paxson 2017 (security patches are local). This study asks a narrower question than those: *after a size-and-complexity baseline, does call-graph position still carry change or fix-proneness, and does it hold across languages and a time split?* It extends rather than replicates, and its size control is the same idea as El Emam's.

Inside this repo: `EXPERIMENTS.md` already records Centrality/PageRank as "small-file dead; mid-band open candidate". The file-level PageRank and betweenness result here (below) is consistent with the first half and does not test the second (no size-band analysis). `docs/self_evolution/repair_radius_variants_results.md` found that on GitGalaxy's own history a repo-wide random null overstates the repair radius, and that a null drawn from recently touched functions (null C) removes the excess. **That is the same failure mode this study's repo-wide null had, and this study's directory-matched null is weaker than null C.**

## Registered claim

None. The informal pre-registration text (verbatim files in this directory) stated, per language stratum: orchestrators (fan-in < 8, fan-out >= 8) lift > 1; fan-out partial correlation > 0 in a majority of repos; consumer-ish (fan-in ratio < 0.2) lift above producer-ish (> 0.8); fix radius >= 1.5x a directory-matched null in a majority of repos.

## Guards (what applies, and what was not done)

- [x] Temporal ablation: every scan ran with `GITGALAXY_DISABLE_GIT_HISTORY=1`.
- [x] Size-matched control: per repo, a Poisson regression of fix touches on log(1+LOC) and log(1+complexity); the effect is the lift over the prediction. This answers "does it **add** to size" (checklist 13), not "does it replace size".
- [ ] Rename tracking: **not done.** Functions and files are matched by name at HEAD, so renamed ones are dropped.
- [ ] >= 20-positive power rule per cell: **not applied.** Cells with fewer than 8 functions or fewer than 3 expected touches are skipped, which is weaker.
- [ ] Multiple-comparison correction: **not applied.** Roughly forty comparisons were made; four per wave were pre-stated. Everything beyond those is exploratory.
- [~] Defect-lift-over-LOC bar: the lift is over size and complexity, as a ratio of observed to predicted counts, not an AUC against LOC.

## Results

All lifts are observed fix touches over the size-baseline prediction (1.0 means as expected). Pooled by sum of observed over sum of expected with a within-repo bootstrap CI (wave 1) or by DerSimonian-Laird random effects (wave 2). `I2` is between-repo heterogeneity.

### 1. Orchestrators and consumers change more than their size predicts (the robust result)

| set (fix label B) | orchestrators | consumer-ish | producer-ish | fan-out partial rho |
|---|---|---|---|---|
| wave 1, development (4 C) | 1.20x (1.13-1.26) | 1.11x (1.06-1.16) | 0.95x (0.86-1.04) | +0.09..+0.11, 4 of 4 |
| wave 1, fresh (4 C) | 1.23x (1.14-1.32); per repo 0.85, 1.02, 1.20, 1.24 | 1.14x (1.08-1.21) | 0.73x (0.62-0.84) | +0.05..+0.19, 4 of 4 |
| wave 2, C (6) | 1.19x (1.04-1.36) | 1.09x (0.97-1.23) | 0.76x (0.64-0.90) | 6 of 6 |
| wave 2, Go (8) | 1.21x (1.12-1.30) | 1.14x (1.07-1.22) | 1.01x (0.89-1.15) | 8 of 8 |
| wave 2, Java (7) | 1.25x (1.09-1.42) | 1.25x (1.10-1.41) | 0.71x (0.64-0.79) | 7 of 7 |
| wave 2, all 21 usable | 1.22x (1.15-1.29), I2 0.20 | 1.16x (1.09-1.24), I2 0.64 | 0.82x (0.74-0.91), I2 0.43 | 21 of 21, median +0.10 |

The **D (any-commit) control gives the same size of effect** (orchestrators 1.23x development, 1.29x fresh, 1.19x wave 2; fan-out partial rho larger, median +0.20). So this is general change-proneness, not specifically fixes, and it does not depend on the label. Time split (development set, B): orchestrators 1.24x older half, 1.17x newer; consumer-ish 1.14x, 1.09x; fan-out positive 4 of 4 in both halves. Orchestrators are 7-11% of functions and take 26-40% of fix touches, mostly because they are large (about 100-200 lines, complexity 24-32).

Outliers and failures, as pre-stated: libuv orchestrators 0.85x (wave 1 fresh); Go consumer/producer separation fails (producer 1.01x); `cli` (Go) is a clear outlier (orchestrators 0.41x, producers 1.91x), probably many near-identical command functions.

### 2. Metrics that did not hold up (8 C repos)

- **Betweenness and PageRank, file level.** Raw rho with fix count 0.25-0.48, but fix count correlates with LOC at 0.59-0.72. Partial rho after LOC: betweenness -0.06..+0.10 (only openssl significant), PageRank +0.03..+0.06 (not significant). Fix **share** (fixes per commit) falls with PageRank in redis (-0.26, p=0.003). Function-level betweenness partial rho 0.00..+0.05. The top 5% of functions by betweenness hold 7-9% of LOC and take 6-13% of fix touches.
- **File-level producer ratio / ecosystem role.** Size-adjusted lift has no consistent direction: consumer files 0.75-1.11x, producer files 0.69-1.21x.
- **Fan-in.** Partial rho with fix touches -0.05..+0.02 in wave 1 and median -0.03 in wave 2 (positive in 6 of 21). Fan-in reads as a change cost, not a bug predictor: when a function with 30 or more callers is touched, the mean number of its callers changed in the same commit is 5.5 (curl), 5.1 (redis), 0.9 (openssl), but the median for 10 or more callers is 0.
- **Utility quadrant** (fan-in >= 8, fan-out < 8) is inconsistent: 1.12x development, 0.80x fresh (CI 0.66-0.97), 1.26x in Go and 0.79x in Java. **Hubs** (both high) are too rare for a claim (5-27 per repo).
- **Chain length.** Depth from entry has partial rho -0.10..+0.04 (flat); height (longest chain below a function) +0.03..+0.17 (weak).

### 3. The fix radius is smaller than first reported

Pairs of functions changed in the same fix commit (up to 12 functions), share within 2 undirected call hops:

- **Repo-wide null** (random fix-touched pairs): 2x to 18x on the four development repos. **This is mostly directory adjacency and recurrence of hot functions.**
- **Directory-matched null** (one member of the pair replaced by a random fix-touched function from the same directory; same file for same-file pairs): median about 1.5x across 28 repos, at or above 1.5x in 15 of 28 (C wave 1: 5 of 8, range 1.4-2.0x; C wave 2: 5 of 6; Go: 2 of 8, range 1.1-1.7x; Java: 3 of 6). Never below 1.1x.
- Null C from `repair_radius_variants_results.md` (functions recently touched by any fix, weighted by recurrence) was **not** run, and on that repo it removed the excess. Expect these numbers to shrink further.

### 4. Withdrawn

"Lifecycle-named functions (free, close, destroy, cleanup, finalize, done, remove ...) with fan-in >= 8 get about twice the fixes" came from reading top-excess lists, then testing on the same data. Original label 1.89x (1.46-2.31); label B 1.53x (1.05-2.04) with openssl flipping from 1.56x to 0.22x; fresh repos 1.26x (0.72-1.91), fail; **any-commit control 1.64x (1.35-2.00)**; older half 0.87-0.99x, newer half 2.08-2.57x under fix labels but stable at 1.55-1.77x under D. It is a churn effect and unstable over time. Retracted.

### 5. Engine version

The full set was rescanned after pulling gitgalaxy `main` (8972b2f to 981e9ec, which changed aperture pruning and a Python rule only). Function, edge and file counts were identical on all 8 wave-1 repos and the results are byte-identical.

## STUDY_CHECKLIST status

| # | item | status |
|---|---|---|
| 1 | rank only what can be positive | **partial**: test, doc, vendored, example and benchmark directories were removed before scanning, but `laws_units` was not used |
| 2 | same label depth for every repo | yes (subject keywords for all) |
| 3 | keep merges where the merge is the unit | **not done**: `--no-merges` for every repo; no merge-workflow sensitivity |
| 4 | scan completeness >= 0.90 | **not computed** |
| 5 | instrument check per language (inbound-call share) | **not reported**; Go and Java call-graph resolution quality was not measured |
| 6 | one language rule per repo | yes (C `.c/.h`, Go `.go`, Java `.java`) |
| 7 | date repos robustly | n/a (window fixed at 2021-01-01) |
| 8 | tree-wide commits in the label | **not checked** |
| 9 | state the direction | yes, in the informal pre-registration |
| 10 | state the power | **not stated** |
| 11 | never confirm on the repos that suggested the idea | yes: wave 1 fresh set and all of wave 2 are separate from the development set; pre-stated hypotheses from wave 1 were judged on wave 2 only |
| 12 | per-repo results with intervals | **partial**: per-repo lifts printed everywhere; per-repo CIs printed only for wave 1 fresh |
| 13 | size, "adds" vs "replaces" | the "adds" test was run |
| 14 | sensitivities declared | yes: labels orig, B, D and the two time halves |
| 15 | two independent reviews | **not done** |
| 16 | amend in the open | the retraction (section 4) and the radius correction (section 3) are recorded above |
| 17 | every exclusion has its reason | okhttp (Kotlin, the miner reads only `.java`); mockito radius (too few pairs); `skip` cells listed in the result files |
| 18 | corrections opt-in on shared tools | n/a (standalone scripts) |

## Reading

- **Supported at the descriptive level:** functions that call many others, and functions that mostly call rather than get called, are changed (and, under a keyword label, fixed) about 10-25% more than their size and complexity predict. This is consistent across C, Go and Java, across a time split, and it appears under the label-free control. Fan-out is the one scalar that carries it.
- **Not supported:** betweenness, PageRank, file-level producer role and fan-in as fix predictors beyond size; any lifecycle-function claim; a fix radius much beyond "nearby".
- **Does not establish:** that these functions are buggier (the control says they are changed more), that anything here predicts the next fix (the study is cross-sectional against a HEAD graph, not forward-validated, which the programme requires for prediction claims), or anything about languages other than C, Go and Java.
- **Open threats:** keyword label with unmeasured precision; HEAD-only graph with unresolved function-pointer calls (gitgalaxy#8956, so C numbers are lower bounds); hunk-header function attribution through git's built-in drivers (Java overloads credited together); the size baseline uses LOC and complexity only; no merge-workflow sensitivity.

## Follow-ups registered (for unseen data only)

None registered here. Candidates, each to be registered before it runs and on data this study has not seen: (1) forward-validated fan-out lift using the quarterly walks and the audited v3c label; (2) the fix radius against null C on the LAWS panel; (3) a size-banded version of the PageRank and betweenness result, to test the mid-band candidate in `EXPERIMENTS.md`.
