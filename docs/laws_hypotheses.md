# LAWS — a many-labs replication of the classic software-network laws across languages and decades — registered 2026-11-08, before any panel repository is selected, scanned or labelled

**Programme steps 2 and 3** (`docs/PROGRAMME_call_networks.md`). The panel protocol (PANEL) and the law claims
(LAW-1 … LAW-9) are registered together, so the sample cannot be chosen after seeing any network statistic.

## Prior work

[v] = details confirmed by web search on 2026-11-08 (lit review, `gitgalaxy/cgt-study/lit_review.md`);
[k] = from knowledge, to verify before external citation.

| law | prior claim | sources |
|---|---|---|
| heavy tails | software dependency and call graphs have heavy-tailed degree distributions; power law vs log-normal is contested | Myers 2003 PRE [v]; Concas et al. 2007 TSE [v]; Louridas, Spinellis, Vlachos 2008 TOSEM [v]; Clauset, Shalizi, Newman 2009 SIAM Rev. [k] (method) |
| preferential attachment | new dependencies attach to already well-connected units | Valverde & Solé 2005 EPL [v]; Wang et al. 2009 ICSM (Linux call graphs) [v]; Chaikalis & Chatzigeorgiou 2015 TSE [v] |
| hub persistence | important (central) units are stable over a system's life | Wang et al. 2009 [v]; Vasa, Schneider, Nierstrasz 2007 ICSM [v] |
| centralisation | heavy tails and growth make high coupling statistically hard to avoid | Taube-Schock, Walker, Witten 2011 ECOOP [v] |
| decay | structure degrades over time unless work is done against it; modularity erodes | Lehman 1980 [k]; Eick et al. 2001 TSE [v]; MacCormack, Rusnak, Baldwin 2006 Mgmt Sci [v] (propagation cost); Le et al. 2018 ICSA [v]; Herraiz et al. 2013 CSUR [v] |
| cycles | components in dependency cycles are more defect-prone | Melton & Tempero 2007 EMSE [v]; Oyetoyan, Cruzes, Conradi 2013 JSS [v] |
| size confound | metric–defect associations shrink or vanish after controlling for size | El Emam et al. 2001 TSE [v] |
| network metrics vs defects | network measures improve defect prediction over code metrics (Zimmermann & Nagappan 2008 ICSE [v]); the gain vanishes in forward-release, effort-aware settings (Premraj & Herzig 2011 ESEM [v]); process metrics dominate (Rahman & Devanbu 2013 ICSE [k]) | also Tantithamthavorn et al. 2017 TSE [k] (validation), Kamei et al. 2013 TSE [k] (effort-aware) |
| security-patch locality | security patches are smaller and more localised than other bug fixes | Li & Paxson 2017 CCS [v] |

**Relation:** these are replications. What is new is the design: one compile-free instrument, a frozen
multi-language panel with decades of quarterly history, null models for every network claim, and a per-language
random-effects synthesis.

## PANEL — the sample (fixed by rule now; drawn after this registration is pushed)

- **Languages:** C, Java, Go, Python (confirmatory, subject to the ACC gate below); C++, Rust, JavaScript/TypeScript,
  C# (descriptive until ACC covers them).
- **Eligibility** (GitHub metadata and git, read before any scan):
  - not a fork, not archived;
  - OSI licence read from the repo;
  - the language is ≥ 60% of the repo's source bytes (GitHub linguist);
  - first commit ≤ 2018-10-01 (≥ 8 years of history);
  - ≥ 2,000 commits on the default branch;
  - ≥ 50 source files of the language at the 2026-10-01 snapshot;
  - ≤ 2 million lines of the language (cost);
  - ≥ 500 stars (an activity floor, not a quality signal).
- **Excluded:** every repo used in any temporal-crucible study to date (curl, OpenSSL, libarchive, harfbuzz, nDPI,
  zlib, expat, the KF-R libraries, PostgreSQL, libgit2, libxml2, redis, prometheus, commons-lang, sphinx, ripgrep,
  GitGalaxy) and the gitgalaxy population-DB pilot repos.
- **Draw:** GitHub search per language with the eligibility filters, results cached to `panel/candidates_<lang>.json`;
  **8 repos per language drawn uniformly at random (seed 2982)** from the eligible list. A drawn repo that fails a
  check found only on cloning is replaced by the next draw, and the replacement is logged.
- **Snapshots:** quarterly, newest first-parent commit before each quarter boundary, from the first quarter with
  ≥ 50 source files of the language to 2026-10-01. **Engine:** gitgalaxy `8f96d76ba`, history off, one engine for all.
- **Fix labels:**
  - **Classes:** `tools/xc_harvest.py --exts <language>` for latent, regression, extrinsic and other fixes. The
    latent class (CVE fixes) comes from **OSV.dev advisories** that name a fix commit in the repo.
  - **Validation before any network statistic:** 25 commits per class per language (or all, if fewer) are drawn at
    random and hand-labelled from the commit and diff alone, blind to every network measure.
  - **Class gate:** a class whose label precision is < 70% in a language is descriptive-only there.
- **Development set:** the excluded repos above (pilot tools there, never panel results).
- **ACC gate:** a language enters a confirmatory law only if ACC-H3 holds for it (network statistics survive). If
  ACC fails for a language, its law results are descriptive and labelled so.

## Measures (as CGT / CGN unless stated)

Call network per snapshot (`docs/cgt_hypotheses.md`); function in-degree; file coupling (distinct files called or
calling); file-level SCC cycles; directory modularity Q; **propagation cost** (MacCormack: share of function pairs
connected by a directed path, sampled for large graphs); rewiring per quarter.

**Controls on every defect claim** (file-year grain, outcome: a fix touching the file in the next 365 days):
- log functions in the file and log LOC;
- churn in the prior year;
- prior fixes in the prior year;
- **number of distinct authors** in the prior year;
- **change coupling**: number of files co-changed with it in ≥ 3 commits in the prior year (Gall et al. 1998 [k];
  D'Ambros et al. 2009 [k]);
- repo fixed effects within language.

## Synthesis (all laws)

- **Unit = repository.** Each law gives one effect per repo (log OR, Kendall τ, attachment exponent α, a
  difference). Repo effects are pooled by **DerSimonian–Laird random effects** within each language and overall.
- Heterogeneity is reported as I² and τ², and language as a moderator (Q-between).
- **A law holds in a language** iff the pooled within-language effect's 99% CI excludes the null in the predicted
  direction.
- **A law is universal** iff it holds in ≥ 3 of the 4 confirmatory languages **and** no language's pooled effect is
  significantly opposite.
- **Holm correction** across the nine laws for the universal calls.
- Every repo-level estimate is published.

## The laws

| id | law (predicted direction) | per-repo effect and null | prior |
|---|---|---|---|
| **LAW-1** | **heavy tails:** function in-degree is heavy-tailed | latest snapshot: Clauset–Shalizi–Newman fit; Vuong log-likelihood ratio, power law and log-normal vs exponential; effect = the ratio favouring the better heavy-tailed fit (> 0). *Power law vs log-normal reported, no direction* | holds |
| **LAW-2** | **preferential attachment:** new calls go to well-called functions | attachment kernel A(k) ∝ k^α estimated from new edges into persisting functions per quarter (Jeong-style relative attachment over in-degree bins); effect = α; null α = 0 (uniform). α ≈ 1 (linear) descriptive | holds |
| **LAW-3** | **hubs persist beyond size:** central functions keep their rank longer than large functions keep theirs | yearly pairs 5 years apart: share of surviving top-1% hubs (in-degree) still top 5%, **minus** the same share for surviving top-1% functions by LOC; effect > 0 | holds |
| **LAW-4** | **centralisation beyond growth:** in-degree inequality rises faster than growth alone produces | Gini of in-degree at the last snapshot vs 100 simulated growths from the first snapshot with the observed per-quarter node and edge additions and **uniform** attachment; effect = observed Gini − mean simulated Gini, > 0 | holds (Taube-Schock) |
| **LAW-5** | **decay:** modularity beyond its null falls and propagation cost rises | yearly: Kendall τ over time of (Q − Q of a degree-preserving rewired network, 20 rewirings); effect τ < 0. Second effect: τ of propagation cost > 0. **Both** must hold | mixed (CGN B1: 1/5) |
| **LAW-6** | **cycles go with later fixes**, beyond all controls | file-years; logistic regression with the controls; effect = log OR of in-cycle, > 0 | holds (Oyetoyan; CGN C1) |
| **LAW-7** | **the size confound:** network metrics' associations with later fixes shrink by half or more once size is controlled | for in-degree sum, coupling and in-cycle: log OR without vs with log functions and log LOC; effect = 1 − adjusted / unadjusted; > 0.5 | holds (El Emam) |
| **LAW-8** | **network metrics add to defect prediction**, forward in time, effort-aware | per repo: train on file-years ≤ year t, test on t + 1, every t with ≥ 3 training years; logistic models (a) size + process controls vs (b) (a) + coupling, in-degree sum, in-cycle, rewiring; effect = mean gain in recall@20% LOC (b − a); > 0.02 | **expected to fail** (Premraj & Herzig) |
| **LAW-9** | **security patches are local:** CVE fixes touch fewer files and functions and change fewer lines than other fixes | repos with ≥ 20 OSV-linked fix commits; effect = median difference (CVE − other fix) in files touched, functions changed and C/language lines changed, each < 0; plus (extension, CGT-3b) call-edge rewiring rate CVE vs other at matched size, descriptive | holds (Li & Paxson) |

## Not evaluable

- A repo with < 20 quarterly snapshots; a language with < 5 evaluable repos for a law.
- A defect law in a repo with < 50 positive file-years.

## Guards

- Registration before selection, scans, labels and statistics; the panel draw is logged.
- One engine; one scorer committed before its run; verdicts per repo, per language and pooled, either way.
- Null models with every network law; size-adjusted headlines; process controls on every defect law; label
  validation and the ACC gate before confirmatory claims; forward validation for prediction.

## Amendment 0 (2026-11-08, after an independent methods review, before any panel repo is selected, scanned or labelled)

An independent methods review (`docs/laws_methods_review.md`, verdict: major revision, all fixable pre-data) found
that several tests above could be passed by trivial artefacts, that the synthesis lacked variances and a valid
"universal" test, and that tests, vendored and generated code, label workflows and the sampling frame were
unspecified. **This amendment adopts every must-fix item M1–M9 (section (a)) and every should-fix item 1–15
(section (b)) of that review, in the amendment text as written there.** Where they conflict with the text above,
they win. The following decisions complete them:

1. **Panel size.** **12 repos per confirmatory language** (C, Java, Go, Python); 8 per descriptive language
   (C++, Rust, JS/TS, C#). The power table in M1 is part of this registration. At k = 12 and the 99% bar,
   80% power needs a pooled effect of about 1.15–1.25 between-repo SDs.
2. **Laws labelled descriptive now, before any data** (M1), because their plausible effect is below what k = 12 can
   detect or the programme has already seen them be project-specific:
   - **LAW-5** (decay: CGN B1 held in 1 of 5 repos);
   - **LAW-9** (security-patch locality, whose evaluable-repo count depends on OSV coverage). It becomes
     confirmatory only if ≥ 5 repos per language are evaluable, a count checked before any LAW-9 statistic.

   LAW-6, LAW-7 and LAW-8 stay confirmatory under M2's rule that a non-significant result is "inconclusive" unless
   the registered equivalence test passes.
3. **Label raters** (M6). The first rater is Claude (`claude-opus-5-5`); the second is an independent Claude session
   given only the commit message, the diff and the class definitions (no first-rater labels, no network
   measures). Prompts, model id and temperature are committed with the scorer, before any audit label is produced.
4. **Pilot** (should-fix 9). The CGR replication set (libgit2, PostgreSQL, libxml2, redis, prometheus, commons-lang,
   sphinx, ripgrep: development data, never panel results) is the required pilot. The LAWS scorer runs end to end on
   it, and any scorer change after the pilot is committed before the panel draw.
5. **Engine** (should-fix 15): `8f96d76ba`. The pilot confirms its Go, Java, Python and Rust parsers on development
   repos (CGR). If a language fails, it is descriptive, decided before the draw.
6. **Node identity** (M4) uses the engine's `parent_class_id` (enclosing class) where it is set.
7. **Order of work:**
   1. ACC and ACC-P gates;
   2. pilot;
   3. frame build and hashed candidate list (pushed);
   4. the seeded draw;
   5. scans;
   6. label audit;
   7. scorer freeze (committed);
   8. one run.

   No law statistic is computed before step 8.

## Amendment 1 (2026-11-09, owner OK; before any panel repo is selected, scanned or labelled)

**Context.** ACC, ACC-2 and ACC-3 (`docs/acc.md`, `docs/acc2.md`, `docs/acc3_hypotheses.md`) admitted only C through
the gate. The engine is now being tuned to reach its reference tools' quality (gitgalaxy epic #8161, four PRs).
The tuning measures the engine on 20 candidate repos and the engine's own gate corpus.

1. **ACC-P is the post-tuning validation.** No separate ACC-4 study is run. ACC-P (Amendment 0, M4) runs the
   oracles on 2 randomly drawn panel repos per language, at an early and a late snapshot, before any law statistic.
   Those repos are new to every study and in the panel anyway, so no additional repos are spent. ACC-P uses the
   **engine's resolved call graph with confident links only** (as the engine's own gates score; ambiguous links are
   reported, never used as network edges), and its result is the language gate.
2. **Engine version.** The panel is scanned with the gitgalaxy commit that contains the last merged PR of epic #8161
   that is merged before the draw. That commit is recorded in this file before the draw; it replaces `8f96d76ba`.
   Engine changes after the draw need a dated amendment and a full rescan before the scorer freeze.
3. **Excluded from the panel by name** (the engine-tuning set; the engine is tuned on them, so they cannot validate
   it):
   - C++: google/leveldb, gabime/spdlog, jbeder/yaml-cpp;
   - C: jqlang/jq, facebook/zstd, jedisct1/libsodium;
   - Rust: sharkdp/fd, sharkdp/hyperfine, casey/just;
   - TypeScript: immerjs/immer, ianstormtaylor/superstruct, typestack/class-validator;
   - Python: psf/requests, pallets/click, python-attrs/attrs;
   - Java: jhy/jsoup, JodaOrg/joda-time;
   - Go: gin-gonic/gin, spf13/viper;
   - JavaScript: koajs/koa.

   Also excluded: the engine's call-graph gate corpus (`tests/import_graph_corpus.json` entries scored for call
   graphs) and the ACC repos (apache/commons-io, commons-lang, prometheus, sphinx, libgit2, redis; already excluded).

## Amendment 2 (2026-11-09, owner OK; before any panel repo is selected, scanned or labelled)

**Context.** Engine tuning (gitgalaxy epic #8161) has raised the engine's call-graph quality in languages LAWS lists
as descriptive (Rust, JS/TS, C++), and the engine parses languages no ACC study has measured (C#, Kotlin, PHP).
This amendment lets those languages earn confirmatory status through the same ACC-P gate, without changing the
primary test or re-scaling it to the languages that pass (M2).

1. **The primary test is unchanged.** "Universal" remains the M2 partial-conjunction test for at least 3 of the 4
   languages C, Java, Go and Python. An ACC-failed or non-evaluable language among those 4 still contributes
   p_ℓ = 1.
2. **ACC-P covers every candidate language.** ACC-P (Amendment 1, item 1) runs for C, Java, Go, Python, C++, Rust,
   JS/TS and C#, plus Kotlin and PHP if they are admitted under item 4. Every language that passes ACC-H3 on both
   ACC-P repos at both snapshots is **confirmatory**: 12 repos, per-language law claims at the registered 99% bar.
   A language that fails stays descriptive with 8 repos. The repos are always the first 12 or 8 of that language's
   seeded draw order; ACC-P uses draws 1 and 2.
3. **A secondary, extended universality test, fixed now.** Let n be the number of languages that enter ACC-P,
   counted before any ACC-P result, and r = ⌈2n/3⌉. A law is **universal (extended)** iff the Benjamini–Heller
   partial-conjunction p-value for "at least r of n", p^{r/n} = (n − r + 1)·p_(r), survives Holm at α = 0.01
   across the nine laws, **and** no language's pooled effect is opposite at one-sided p < 0.01. ACC-failed or
   non-evaluable languages contribute p_ℓ = 1. The extended test is reported beside the primary one and never
   replaces it. A law that fails the primary test is reported as failing it, whatever the extended test shows.
4. **Admission of new languages (C#, Kotlin, PHP).** Before the draw, a measurement-only survey runs the engine
   and a compiler-grade reference on one development repo per language. The references are scip-dotnet (C#),
   scip-java with the Kotlin compiler plugin (Kotlin) and scip-php (PHP), each pinned. A language is admitted to
   the panel and ACC-P iff:
   - the reference produces a call graph on its repo;
   - the engine's confident-link precision against it is ≥ 0.80 (the ACC-H1 bar).

   The survey also reports recall and the three ACC-H3 statistics, descriptively; they are not an admission bar.
   The admission result is recorded in this file before the draw. C#, already listed as descriptive, is in the
   panel either way and needs admission only to enter ACC-P. Ruby and Swift are not candidates.
5. **Development-set dry run.** Before the draw, the three ACC-H3 statistics are computed on development repos
   only (the ACC repos, the engine's call-graph gate corpus and the survey repos) with the panel engine. They are
   reported as a pre-draw check, not a gate, and they cannot change items 1–4.
6. **Excluded from the panel by name:** the survey repos JamesNK/Newtonsoft.Json (C#), square/kotlinpoet (Kotlin)
   and composer/composer (PHP), and any substitute the survey logs when one fails to build.

### Amendment 2, item 4: admission result (2026-11-09, before the draw)

The survey ran on the engine at gitgalaxy `19e6b9c91`. Its scoring is the gate's `call_graph_resolution._score`, used unchanged, with LAWS M3 exclusions on both sides. Precision is agree / (agree + wrong) over confident links.

| language | repo @ SHA | reference | confident precision (judged) | recall | ρ / J / κ (descriptive) | admitted |
|---|---|---|---|---|---|---|
| C# | JamesNK/Newtonsoft.Json @ 52fa3ae | scip-dotnet 0.2.16 | 0.818 (3,415) | 0.591 | 0.774 / 0.375 / 0.668 | **yes** |
| Kotlin | square/kotlinpoet @ d438267 | scip-java v0.13.2 (scip-kotlinc) | 0.819 (542; 95% CI 0.787–0.851) | 0.320 | 0.502 / 0.250 / 0.656 | **yes** (point estimate, as the bar is written) |
| PHP | composer/composer @ 3a5137b | scip-php v0.0.2 | 0.998 (2,670) | 0.871 | 0.727 / 0.458 / 0.736 | **yes** |

C#, Kotlin and PHP enter the panel and ACC-P, so n = 10 for the extended test (item 3), and r = 7.

Descriptive notes:
- 577 of C#'s 623 wrong links, and 88 of Kotlin's 98, are another overload of the right method.
- scip-php v0.0.2 has no edge for 36% of the engine's confident links. With scip-php main @ 71a5b11, precision is 0.995.
- None of the three meets ACC-H3 on its development repo.

## Amendment 3 (2026-11-09, owner OK; before the sampling frame is built or any panel repo is selected)

**Context.** Amendment 0 adopted 12 repos per confirmatory language from the methods review (M1, "also consider
strongly"). The review's power table has no k = 12 row and does not cover the universal test, which runs under
Holm across nine laws. The exact power (noncentral t, Hartung–Knapp t_{k−1}, 99% two-sided; δ = pooled mean /
√(τ² + v̄)) is:

| k per language | δ = 0.8 | δ = 1.0 | δ = 1.25 | δ = 1.5 | smallest δ at 80% |
|---|---|---|---|---|---|
| 8 | 0.21 | 0.35 | 0.55 | 0.74 | 1.60 |
| 12 | 0.41 | 0.64 | 0.86 | 0.96 | 1.17 |
| 16 | 0.61 | 0.83 | 0.97 | 1.00 | 0.96 |
| 20 | 0.75 | 0.93 | 0.99 | 1.00 | 0.84 |

Power of the primary universal test (≥ 3 of 4, partial conjunction; equal δ in every language), at the first and
last Holm step (α = 0.01/9 and α = 0.01):

| k | δ = 1.0 | δ = 1.25 | δ = 1.5 |
|---|---|---|---|
| 12 | 0.07 / 0.55 | 0.34 / 0.90 | 0.74 / 0.99 |
| 16 | 0.34 / 0.87 | 0.82 / 0.99 | 0.99 / 1.00 |

The extended test (≥ 7 of 10) at δ = 1.5 has power 0.50 / 0.99 at k = 12, and 0.99 / 1.00 at k = 16.

1. **Panel size.** **16 repos per confirmatory language** (replaces Amendment 0 item 1 and Amendment 2 item 2's
   "12"). Descriptive languages keep 8. The repos are the first 16 or 8 of the language's seeded draw order;
   ACC-P uses draws 1 and 2.
2. **Thin pools.** A language with fewer than 16 eligible repos takes all of them. A language with fewer than 12
   eligible repos is descriptive whatever ACC-P shows. Pool sizes are counted from the frame before the draw and
   recorded in this file.
3. **Unchanged:**
   - the label audit (25 commits per class per language);
   - ACC-P (2 repos per language, two snapshots);
   - every test, bar and Holm family.

   The cost of this amendment is scan compute only.
4. **What the power means for interpretation (stated before the data).**
   - The network laws LAW-1 to LAW-4 are expected to have δ well above 2, so their verdicts are informative at any
     k here.
   - For the defect laws LAW-6 to LAW-8, δ ≈ 1 is plausible. At k = 16, a non-significant universal result is
     informative only for δ ≥ 1.25, and the report says so. M2's rule that a non-significant result is
     "inconclusive" stands.
5. **Power code.** The power numbers come from `scipy.stats.nct` with ncp = δ√k and the critical t_{k−1}. A
   language passes a partial-conjunction step at level α when its one-sided p ≤ α/(n − r + 1).

### Amendment 1, item 2: panel engine (2026-11-10, before the sampling frame is built or any panel repo is selected)

**The panel engine is gitgalaxy `b873edc5b059f79e49858fa8e124f6b3e3f3e24f`.** It is the merge commit of
gitgalaxy#8202, the last PR of epic #8161, merged 2026-11-10T14:04Z. It replaces `8f96d76ba` (the PANEL section and
Amendment 0 item 5) for every panel scan, the pilot, the development-set dry run and ACC-P. No other PR of the
epic was open when this was recorded.

The epic's merged PRs, in order: #8162 (`4b23f2187`), #8175 (`18ae0dddb`), #8186 (`19e6b9c91`, the admission
survey's engine), #8190 (`a94f75eb8`), #8202 (`b873edc5b`).

What is known of this engine on development repos, descriptive only (gitgalaxy CI run 42820825390 on #8202's head
`92d4fca2c`, the gate's own scoring; not ACC-P and not a gate here):

| language | repo | reference | confident precision (judged) | recall |
|---|---|---|---|---|
| C# | JamesNK/Newtonsoft.Json | scip-dotnet | 0.997 (3,747) | 0.790 |
| Kotlin | square/kotlinpoet | scip-java (kotlin) | 0.973 (512) | 0.359 |

The PHP lane does not run in CI; its numbers in #8202's description are from a local run and are not repeated here.

Engine changes after the draw need a dated amendment and a full rescan before the scorer freeze (Amendment 1,
item 2). Nothing else in the registration changes.

## Amendment 4 (2026-11-10; before the sampling frame is built or any panel repo is selected)

Owner OK, 2026-11-10: replace the Go oracle's CHA pass with a more precise algorithm, tested on the development
repo first. The choice of algorithm below follows that test.

**Context.** The development-set dry run (`docs/laws_dryrun.md`) ran the registered Go oracle on prometheus
(`callgraph -algo=static` as direct edges, `-algo=cha` minus static as dynamic edges). In ACC-3 the CHA pass
contributed 0 in-repo edges, which ACC-3 called implausible. In the dry run the same command contributed 14,929.
Why ACC-3's pass returned none is not known. ACC-P is the language gate, so Go's reference cannot be left to
whether that pass returns edges. CHA also adds an edge to every method that could implement an interface call,
which is an upper bound, not a call graph.

Development-repo test (prometheus @ c45b13bbdd96, panel engine, confident links only, ACC-2's node set; every
pass exit 0; descriptive, not a gate):

| reference | dynamic edges on matched functions | in-degree ρ | hub Jaccard | coupling κ | precision / recall |
|---|---|---|---|---|---|
| static only | 0 | 0.805 | 0.466 | 0.852 | 0.911 / 0.841 |
| static + VTA | 6,504 | 0.262 | 0.119 | 0.642 | 0.924 / 0.841 |
| static + RTA | 10,049 | 0.211 | 0.010 | 0.466 | 0.923 / 0.841 |
| static + CHA (as registered) | 14,929 | 0.113 | 0.009 | 0.450 | 0.925 / 0.841 |

1. **Go's oracle, for ACC-P and any later Go accuracy run.** Direct edges: `callgraph -algo=static`. Dynamic
   edges: **`callgraph -algo=vta`** minus static. The in-repo filter, the position template and the matching are
   ACC-3's, unchanged. The tool and toolchain stay as ACC (x/tools callgraph v0.52.0, go1.27.3). CHA and RTA are
   not used.
2. **Not evaluable.** A Go snapshot where either pass exits non-zero, or is killed, is not evaluable. A pass that
   exits 0 is taken as it is, whatever its edge count; the edge counts of both passes are reported.
3. **Unchanged:** the three ACC-H3 statistics and their bars, confident links only (Amendment 1 item 1), every
   other language's oracle, ACC-P's design, and every law test.
4. **Why VTA.** It is the most precise of the tool's algorithms for interface and function-value calls, so its
   edges are the closest the tool gives to the calls that can happen. **Why not static only:** interface calls
   are part of a Go program's call network, which is what the laws are about; and static only is the one
   reference under which Go came near the bars, so choosing it would be choosing the reference by its outcome.
5. **Stated before the data.** Under this reference Go does not meet ACC-H3 on its development repo. The panel
   engine's confident links hold no interface-dispatch edges (8,564 `receiver` links on prometheus are ambiguous
   and not used). Go is therefore expected to stay descriptive in LAWS, with 8 repos. This is an expectation,
   not an ACC-P result: ACC-P still runs for Go. Go is one of the four languages of the primary universal test,
   where an ACC-failed language contributes p = 1 (Amendment 2 item 1), so that test would need all three of C,
   Java and Python.
6. **If the engine is changed for Go before the draw** (typed receivers resolved confidently), the panel engine
   record is replaced by a dated entry and the development-set dry run is repeated with it. After the draw,
   Amendment 1 item 2 applies.
