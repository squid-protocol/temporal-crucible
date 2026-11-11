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

## Amendment 5 (2026-11-10; before the sampling frame is built or any panel repo is selected)

**Context.** The full scorer ran end to end on the development set for the first time (`tools/laws_run.py`,
`docs/laws_driver_pilot.md`: five repos, all nine laws, 635 s, no failures), and the two checks `laws_attach.py`
listed as owed were done (`docs/laws_law2_fitness.md`). Three things came out of it that change what is tested
rather than how it is reported, so they are registered here, before the frame is built. Changes after the pilot
are allowed only before the draw.

1. **LAW-2's effect is the excess over a fitness-only null, not alpha against zero.**

   The registered test cannot tell preferential attachment from fitness heterogeneity. On a generator where
   attachment is switched off entirely and a target's chance depends only on a fixed intrinsic fitness, the
   registered estimator reports alpha = +1.09 -- **larger than it reports for a true attachment exponent of
   1.0**. alpha against a margin of 0 therefore tests whether calls concentrate at all, which is not LAW-2's
   hypothesis. The estimator is not at fault: on the same generator it recovers a known exponent closely
   (true 0.0 -> -0.03, 0.5 -> +0.44, 1.0 -> +0.93, 1.5 -> +1.46).

   The null (`laws_attach.fitness_null`) keeps everything the observed history has except the timing. Each
   target's propensity is fixed at its **observed total intake** of new edges over the whole history -- a fitness
   that by construction reproduces who ends up popular -- and the same callers make the same number of choices in
   the same quarters, with the target redrawn from that fitness; a target's chance never depends on its degree
   now. alpha is re-estimated on each simulated history with the same estimator.

   - **effect** = alpha_observed − mean(alpha_null); **margin 0**, positive direction.
   - **v** = se_observed² + sd(alpha_null)², which is what the synthesis pools. The rank p is reported but is
     **not** the test: with R simulated histories it cannot fall below 1/(R + 1), and at R = 50 four of the five
     pilot repos were already at that floor.
   - **R = 100** simulated histories per repo, enough for a stable sd and the reported rank p; seed 2982.
   - The null is **conservative**: calibrating fitness to realised intake credits fitness with concentration that
     attachment may itself have produced, so the excess is a lower bound.
   - **Pilot values** (development data, descriptive): excess +0.431 sphinx, +0.221 prometheus, +0.220 libgit2,
     +0.133 libxml2, +0.066 commons-lang, against observed alpha of 1.24 to 1.79 and null means of 1.09 to 1.36.
     Fitness explains most of alpha and a real attachment component survives in all five, at 5% to 25% of the
     headline number. Mean 0.214 with a between-repo SD of 0.138 across these five, a ratio of 1.56, so on this
     spread the excess is still detectable at k = 16 under Amendment 3's power table (which needs about 1.15 to
     1.25). That is indicative only: these five are five different languages, and the within-language spread is
     not known.
   - **alpha itself stays in the record**, descriptively, and must not be reported as "the preferential
     attachment exponent".

2. **LAW-2's function-fixed-effects sensitivity is recorded as attempted and uninformative.** It is implemented
   (`laws_attach.fit_fixed_effects`) and does not work at this data size. Calibration on the same generator:
   true 0.0 -> −0.84, 0.5 -> −0.21, 1.0 -> +0.25, 1.5 -> +0.86, and **pure fitness -> +0.23**, so pure fitness
   and a true exponent of 1.0 are indistinguishable. The bias is near −0.8, larger than the effect under test,
   and the reading holds at ridge 0.1, 1 and 10, so the penalty is not the cause. This is the
   incidental-parameters problem: about 400 to 500 fixed effects against about 3,400 choices. **alpha_fe is never
   read as an exponent and never enters a synthesis.** The null in item 1 replaces it as the "beyond fitness"
   sensitivity. PAFit proper -- a joint Bayesian kernel-and-fitness estimate -- is still owed;
   `laws_attach.kernel` covers the functional-form question only and is descriptive (pilot: slopes +1.19 to
   +1.86, curvature −0.16 to +0.29, r² 0.87 to 0.96, so `(k + 1)^alpha` is not badly misspecified).

3. **LAW-9's effect is P(cve smaller), against a null of 0.5.** The registered "median difference ... each < 0"
   is read as the Hodges-Lehmann shift, and on these counts it is **exactly 0.00 with SE 0.00** for files touched
   and functions changed (median 1 file, 2 functions; most pairwise differences are 0), while the rank test on
   the same data is significant for files. Two consequences: a conjunction over an effect pinned at 0 can never
   fire, and a variance-weighted pool cannot accept a zero variance, so two of the three legs could not enter the
   synthesis at all. The effect per metric is therefore the rank test's own effect size, the probability that a
   random CVE fix is the smaller of a CVE/other pair with ties counted half, against a null of 0.5 in the
   direction "CVE smaller". The shift and the difference of medians stay in the record descriptively. The
   three-metric conjunction remains an intersection-union test needing no correction. LAW-9 stays **descriptive**
   (Amendment 0 item 2): 1 of 8 pilot repos clears 20 advisory-labelled fix commits, the bottom of the methods
   review's expected 0 to 3.

4. **Coverage is reported with every law, and every law is also run at matched coverage.**

   `share_confident_of_repo_links` is 98.9% and 99.9% on the two C pilot repos and 55.6% to 59.6% on the Java, Go
   and Python ones. Every law is computed on whatever network the engine produced, so this is a between-language
   difference in measurement quality of the same order as the effects being compared, and it runs through the
   universality test. ACC-P does not catch it: ACC-P validates the **precision** of confident links, this is
   **coverage**.

   - The figure is reported **per panel repo beside every law**, and described as a **floor, not a rate**: `conf`
     and `amb` count only edges whose both endpoints are unit functions, while the `unresolved` table is
     `(commit_hash, step, kind, n)` with no file column and so cannot be scoped the same way. Calls from test
     files, generated files and other languages inflate the denominator for exactly the repos that have them. If
     the scanner is changed to record the file with each unresolved call, the figure becomes a rate and that is a
     dated entry here.
   - Every law is additionally run with the network **thinned to the minimum per-language median coverage** among
     the languages being compared, with an **edge-persistent mask** (`laws_run.thinned`): coverage failure is a
     property of the call site, so the same edge is kept or dropped at every snapshot. A per-snapshot draw is
     wrong and was the first implementation's error -- it made a persisting edge look new to LAW-2, inflating one
     pilot repo's choice count from 16,593 to 121,112.
   - **A universality claim is qualified** where the per-language median coverage of the languages compared spans
     more than **20 percentage points**. On the pilot that span is about 40 points between C and the rest.
   - **LAW-3's evaluable repo count is reported at matched coverage.** Its failure mode under coverage loss is
     dropout, not bias: thinned libxml2 hits the estimator's documented dominant-hub ceiling and becomes not
     evaluable. Low-coverage languages will lose LAW-3 repos non-randomly, which the not-evaluable-dropout item
     of Amendment 0 covers in concept but not by this cause.
   - **LAW-4's between-language comparison becomes descriptive.** Its effect is 0.004 to 0.026 on the pilot and
     attenuates about 30% at matched coverage (libxml2 +0.026 -> +0.018, −2.4 SE). An effect that small cannot
     carry a cross-language claim at these coverage differences. LAW-4 stays confirmatory **within** a language.
   - Uniform thinning is a lower bound on the damage: real failures concentrate on dynamically dispatched calls
     rather than falling evenly. A selective null is owed only if a between-language LAW-4 claim is reinstated.

5. **A two-instrument sensitivity is registered now and run after the draw.** The laws are recomputed from the
   language-specific ACC oracle rather than the panel engine, on the **first 2 repos of each confirmatory
   language's draw order**, with the study's own definitions (overload identity, the exclusion rules, intra-repo
   only, `MIN_LOC`, the same snapshot commits). Pre-committed criterion: the two instruments **agree** for a law
   where the effects share a sign and their 95% intervals overlap. Disagreement is reported, not resolved --
   neither instrument is ground truth.

   - It is a measurement check, not a hypothesis change, so running it after the freeze is deliberate and does
     not reopen any law.
   - Go's comparison already exists and is not re-run: the dry run measured the panel engine's confident links
     against `static` + `vta` at **precision 0.924, recall 0.841** on matched functions, with **no
     interface-dispatch edges** in the engine's confident set (8,564 `receiver` links on prometheus, ambiguous
     and unused). The engine is precise on the edges it claims and incomplete by declared scope.
   - **Python has no working oracle** (PyCG crashes, `docs/laws_dryrun.md`), so no two-instrument check is
     possible for one of the four primary languages. Registered as a stated limitation rather than left to be
     discovered.

6. **Law numbers come only from `tools/laws_run.py`.** The earlier development-set figures for LAW-1 to LAW-4
   were produced by a script that was never committed and cannot be regenerated; they are superseded by the
   driver's output and are not cited.

7. **Label audit deviation (Amendment 0 item 3).** `temperature`, `top_p` and `top_k` are rejected by
   `claude-opus-5-5`, so the registered "temperature" cannot be sent. `output_config.effort` is the only depth
   control and **`effort: "low"`** is registered in its place. The prompts, the model id and the effort are
   committed in `docs/laws_audit.md` before any audit label is produced, and each label records that document's
   sha256. Whether the panel's LAW-6, LAW-7 and LAW-8 use the M6 workflow fix label or the keyword label is
   **still open** and the audit decides it (`docs/laws_defect_labels.md`: the workflow label raises prometheus's
   fix count 82% and libgit2's 32%, LAW-7 is unaffected either way, and the workflow label's precision is what
   the audit measures).

8. **Unchanged.** Every other law's effect, margin and direction; the synthesis (REML with HKSJ, the
   partial-conjunction universal tests, Holm, the equivalence tests); the panel size and the draw; ACC-P's
   design and every other language's oracle; the engine pin; the unit of labelling; and the guards.

### Amendment 5, item 8: the scorer freeze (2026-11-11; before the sampling frame is built or any panel repo is selected)

Owner OK, 2026-11-11. The methods review (should-fix 9) requires the full scorer to run end to end on the
development set, with its run time, failure modes and resolution profile published, before its hash is frozen.
That is done: `docs/laws_driver_pilot.md` (five repos — commons-lang, prometheus, sphinx, libgit2, libxml2 — all
nine laws and the synthesis, 0 failures), `docs/laws_coverage.md` (the resolution profile and the matched-coverage
pass), `docs/laws_law2_fitness.md`, `docs/laws_law9.md`, `docs/laws_defect_labels.md`,
`docs/laws_github_labels.md` and `docs/laws_imports.md`.

**The frozen scorer.**

| what | value |
|---|---|
| temporal-crucible commit | `bcd798d57f465c5a9ff7d80f34905c84b16017a0` |
| scorer modules | the **14** files below, at that commit |
| content hash | `sha256` of those 14 concatenated in name order: `87288570dc0cd43ebc48e272c01392d1618efa819a64cdf5b6ab5f8c2117997b` |
| tests | 175 passing |
| panel engine | unchanged: gitgalaxy `b873edc5b059` (Amendment 1 item 2) |

**The frozen set**, which is the scorer proper -- what turns a measured network and history into a law statistic:
`laws_units.py`, `laws_net.py`, `laws_panel.py`, `laws_logit.py`, `laws_tails.py`, `laws_attach.py`,
`laws_hubs.py`, `laws_central.py`, `laws_decay.py`, `laws_defects.py`, `laws_predict.py`, `laws_security.py`,
`laws_synth.py` and `laws_run.py`. `laws_run.py` is in the set because it holds `SPEC`: every law's margin,
direction and effect key.

**Outside the freeze, and why.** `laws_build.py`, `laws_history.py`, `laws_osv.py`, `laws_github.py` and
`laws_imports.py` harvest inputs; `laws_frame.py` selects the sample; `laws_audit.py` runs the label audit;
`laws_defect_run.py` and `laws_dryrun.py` are ad-hoc drivers. None of them computes a law statistic. What binds
them is not this hash but the engine pin, the snapshot set, the M9 frame rules and the audit's own committed
prompts -- and `laws_frame.py` in particular must still be finished, so freezing it would be a mistake. A change
to one of these does not need an amendment; a change to its *output contract*, which the frozen scorer reads,
does.

**What the freeze covers.** Every estimator, every null model, the synthesis, and the margins and directions of
all nine laws as Amendment 5 leaves them. A change to any file in the frozen set after this entry needs its own
dated amendment, and after the draw it needs a full rescan as well (Amendment 1 item 2).

**What the freeze does NOT fix, deliberately.**

1. **The fix label for LAW-6, LAW-7 and LAW-8.** `laws_run.py --labels keyword|workflow` is a runtime input and
   both paths are implemented and tested, so the frozen scorer computes either. M6 requires the label audit
   "before any network statistic", which binds the **panel run**, not this hash. The audit therefore still has to
   complete before any panel law statistic is computed, and its result selects the label. The registered default
   stays `keyword` until it does.
2. **Descriptive extras still owed**, none of which any confirmatory law depends on: PAFit proper (a joint
   Bayesian kernel-and-fitness estimate; `laws_attach.kernel` covers the functional form only), LAW-5 on the
   import graph (`docs/laws_imports.md`), and a selective rather than uniform thinning null — the last needed
   only if LAW-4's between-language comparison is ever reinstated as confirmatory, which Amendment 5 made
   descriptive. Adding any of them is a dated amendment.
3. **The `unresolved` table's missing file column**, which would turn the coverage figure from a floor into a
   rate. It is a scanner change, so it would replace the engine pin and require a full rescan; it is not taken
   before the draw.

**Known at the freeze, so that no later reading is a surprise.** LAW-2's attachment component is established in 3
of the 5 development repos under its registered variance, not 5 (the rank p is floored and more generous — see
`docs/laws_driver_pilot.md`). LAW-3 is expected to lose repos non-randomly in the worse-measured languages.
LAW-4's attenuation under coverage loss is repo-specific, not a constant. LAW-5's predicted direction holds in
none of the five. LAW-6 points against its prediction in every evaluable development repo. LAW-8 is ~0 as
predicted. LAW-9 is descriptive and evaluable in 1 of 8. Go is expected to stay descriptive (Amendment 4 item 5),
and Python has no working oracle for the two-instrument check.

**Next, in order:** the label audit; the sampling frame under M9 with its candidate fingerprint committed and
pushed; the seeded draw; ACC-P on draws 1 and 2 per language; the panel scans; one scorer run and the synthesis.

## Amendment 6 (2026-11-11, owner OK; after the frame search, before the label audit, before the candidate fingerprint is committed and before the seeded draw — no panel repo selected, scanned or labelled)

**Context.** `docs/otherfix_audit.md` measured the label precision of the residual `other-fix` class
produced by `tools/xc_harvest.py`, which this registration names as the class source (Fix labels,
item 1), over 440 hand judgments in three rounds. Under the registered v1 gate it is **0.558 pooled
and 0.383 outside C** (per repo: libxml2 0.80, postgres 0.77, redis 0.73, libgit2 0.63, sphinx 0.60,
prometheus 0.40, commons-lang 0.27, ripgrep 0.27). `other-fix` carries **85–97% of fix-event mass in
every repo**. Under the class gate (Fix labels, item 3: a class below 70% precision in a language is
descriptive-only there), `other-fix` would therefore fail in Go, Java, Python and Rust, and **LAW-6,
LAW-7 and LAW-8 would become descriptive-only across most of the panel** — the three laws Amendment 0
item 2 deliberately kept confirmatory. The cause is community vocabulary, not a defect in the
harvester: outside C, "fix" mostly introduces lint, type-checker, javadoc, formatting and typo
changes.

1. **Class rule.** The `other-fix` class is produced by `tools/xc_harvest.py` **followed by
   `tools/fixlike_v2.py --rules v3c`** (FIXLIKE v3c), which drops a commit when its touched in-scope
   files are all under test / doc / example / benchmark trees; when its subject is non-behavioural (a
   conventional-commit `docs`/`chore`/`style`/`test`/`build` type, a named linter or type checker,
   javadoc/doxygen/docstring, typo/spelling/grammar, whitespace/formatting, warning-only, changelog,
   refactor/cleanup/performance/portability/build, or an edit to a code comment — exempting operations
   *on* comments, so an XML parser's "Fix EOF handling in comments" survives); or when **no fix word
   appears in the subject**. Measured precision **0.761 pooled, 0.750 C, 0.773 non-C, 7 of 8 repos
   over the gate**, on a confirmatory sample drawn after the rule was written (seed 2984, 25 per repo,
   all 480 previously-judged commits excluded).

2. **Rule C is the operative change.** The v1 gate matched a fix word in the subject **or body**, so
   plain feature commits whose body said "fixes #123" were admitted. The path and prose exclusions
   alone reach only 0.660 pooled and still fail 5 of 8 repos; requiring the fix word in the **subject**
   is what carries the result. Rule C was designed on a 240-commit development set and tested on a
   later 200-commit sample, so 0.761 is out-of-sample. **Quote 0.761, not the development set's
   0.932** — the tuned figure was optimistic by about 0.17.

3. **Applied to `other-fix` only** — the class it was developed and audited on. `latent` (OSV-derived),
   `regression` and `extrinsic` keep their own measured precision from `docs/xc_label_audit.md`
   (regression 0.73–0.87; extrinsic v2 0.90–1.00). Two of them must not be touched by these rules in
   any case: `regression` via revert reaches its class *before* the fix-like gate, so rule C would
   discard `Revert "..."` commits, the cleanest regression signal available; and `extrinsic` is
   already gated on a subject-matched environment **and** action, so rule C would drop legitimate
   entries such as "port to AIX" that carry no fix word. Extending v3c to those classes would need an
   audit of those classes.

4. **Cost.** 43.0% of `other-fix` events and 35.7% of all events are dropped, which works out to
   roughly **22% of real fixes given up to remove roughly 69% of the noise** (development set:
   fixes-kept 0.813, noise-caught 0.925). Non-destructive: v3c event sets are written to
   `events/<repo>_xc2.json` and the v1 sets are untouched, so every published v1 result stays
   reproducible.

5. **v3c is the starting rule, not a substitute for the label audit.** `docs/otherfix_audit.md` covers
   C, Go, Java, Python and Rust — **5 of the 10 candidate languages**. PHP, C#, Kotlin, C++ and JS/TS
   are unaudited. The M6 label audit and the class gate still decide per language; this amendment only
   changes which rule that audit is run against.

6. **The sampling frame is unaffected and is not rebuilt.** `tools/laws_frame.py` admits a repo on
   `MIN_COMMITS`, `MIN_SNAPSHOTS` and `MIN_FILES` alone and reads no fix label, so the frame search
   completed 2026-11-11 stands. This amendment changes labels only, and it is filed before the label
   audit, the candidate fingerprint and the draw.

7. **Unchanged.** The scorer freeze (Amendment 5 item 8) stands — **no scorer change is made or
   needed**: LAW-8 already measures the right quantity (forward, effort-aware gain in recall@20% LOC),
   and the oracle-ladder ceiling estimator of `docs/ceil.md` is deliberately **not** added, since a new
   estimator after the freeze would force a full rescan for marginal gain. The controls are unchanged:
   distinct authors and change coupling are already registered (Controls on every defect claim), a
   choice `docs/ceil.md` independently vindicates — author count came out the strongest single term in
   its re-fit (OR 2.06 [1.92, 2.22]), ahead of prior fixes, and adding it moved prior fix 2.10 → 1.65
   and churn 1.22 → 1.10. Panel size, the draw procedure and every law's direction and bar are
   unchanged.

8. **Open, not decided here: the class gate is per language, not per repo.** libgit2 fails all three
   audit rounds (0.63 / 0.60 / 0.60) on build-and-warning churn that reads exactly like a bug fix, so a
   single weak repo can ride inside a passing language pool and add noise without tripping the gate.
   Flagged for a later decision; this amendment does not change the gate.

9. **Known residual.** Several libgit2 misses are cheap pattern gaps rather than hard cases — bare
   `Fix warnings`, plural `broken tests`, `misspelling`, `linting`, `Javadocs`, `PEP8`. They are
   deliberately left unfixed: the round-3 sample is now a test set and patching against it would repeat
   the development-set overfit noted in item 2. They are a candidate later amendment, to be validated
   on a fresh round-4 sample.

**Evidence.** `docs/otherfix_audit.md` (both rounds, all 440 verdicts listed),
`docs/fixlike_v2_impact.md`, `tools/fixlike_v2.py`, `tools/otherfix_sample.py`, journal
`docs/journal/2026-11-11-otherfix-precision.md`. Companion ceiling result, which measured the effect of
this label change on a defect model (realized share of attainable signal 0.780 → 0.823; the C/non-C gap
0.061 → 0.019): `docs/ceil.md` §5.

## Amendment 7 (2026-11-11, owner OK; before the label audit, the candidate fingerprint and the seeded draw — no panel repo selected, scanned or labelled)

**Context.** Amendment 6 item 8 left open whether the class gate (Fix labels, item 3) should apply per
**repo** as well as per language, since libgit2 fails all three audit rounds (0.63 / 0.60 / 0.60) and
could ride inside a passing C pool. It should not. The measurement does not support a per-repo binary
decision, and making one would cost more than it buys.

1. **No per-repo class gate. The gate stays per language.** Four reasons, in order of weight:
   - **The measurement cannot resolve it.** On the v3c audit, the Wilson 95% interval of **every one of
     the eight repos spans 0.70**: libxml2 0.86 [0.67, 0.95], prometheus 0.83 [0.55, 0.95], ripgrep
     0.82 [0.52, 0.95], sphinx 0.78 [0.58, 0.90], redis 0.75 [0.51, 0.90], postgres 0.74 [0.51, 0.88],
     commons-lang 0.70 [0.48, 0.85], libgit2 0.60 **[0.36, 0.80]**. The repo that prompted the question
     cannot be told apart from 0.80.
   - **Closing those intervals is prohibitive.** Telling a true 0.70 from a true 0.60 needs **136
     commits per repo** (one-sided, α = 0.05, 80% power) — **21,760 judgments** for 16 repos × 10
     languages, against 440 in the whole audit so far. At the language level the same 136 buys one
     estimate per language, **1,360 judgments**, which is affordable. The binary decision therefore
     belongs at the level where the data can support it.
   - **It would be post-hoc exclusion after seeing the labels**, a researcher degree of freedom that
     many-labs designs exist to remove. "We dropped the repos that did not work" is the most
     attackable move available in a replication, and this study's whole guard structure is built to
     avoid it.
   - **The risk direction is already safe.** Every defect law here predicts an effect > 0, and label
     noise attenuates toward the null, so a noisy repo makes the test harder, not easier. (The noise is
     not perfectly random, but v3c's path rule removes the doc/test-path concentration that was the
     specific worry.)

2. **Per-repo precision is not a stable property of a repository.** Changing the rule reshuffled it
   violently: prometheus 0.40 → 0.83, ripgrep 0.27 → 0.82, commons-lang 0.27 → 0.70, while libxml2
   stayed top (0.80 → 0.86) and libgit2 stayed bottom (0.63 → 0.60). It is largely a property of the
   rule interacting with that community's commit vocabulary, not of the project. A gate on it would be
   a gate on rule artifact.

3. **Audit size and sampling for the per-language gate (M6).** The label audit draws **≈ 136
   `other-fix` commits per language, stratified by repo in proportion to that repo's `other-fix` event
   mass** — about 1,360 judgments over 10 languages. 136 is the one-sided n above. One sample serves
   both the gate decision and the per-repo sensitivity in item 5.

4. **Per-repo precision is reported, never applied as a filter.** Every per-repo verdict is published
   beside that repo's `other-fix` precision and the n behind it, so a reader can weigh a result against
   its label quality instead of having repos silently removed.

5. **A pre-registered sensitivity, not an exclusion.** The headline runs on the full drawn panel. A
   second run, specified here before any label exists, repeats it dropping repos whose `other-fix`
   precision **point estimate** is below 0.70. Both are reported. If the two disagree, that is a result
   about label quality and is reported as one — it is not grounds for pruning the panel.

6. **Backstop — a floor, not a gate.** A repo is excluded only when the Wilson 95% **upper** bound of
   its `other-fix` precision falls below 0.70, i.e. when it is demonstrably broken rather than merely
   measured low. On the current audit this fires on **nothing** under v3c (libgit2's upper bound is
   0.80) and would have fired on ripgrep, commons-lang and prometheus under v1. It is a safety net
   against a genuinely broken label set, not a pruning rule.

7. **Unchanged.** The scorer freeze (Amendment 5 item 8), the controls, the panel size, the draw
   procedure, and every law's direction and bar.

**Evidence.** `docs/otherfix_audit.md` and `docs/otherfix_round3_summary.json` for the per-repo counts;
intervals are Wilson 95%; the 136 figure is a one-sided normal-approximation sample size for
p₀ = 0.70 vs p₁ = 0.60 at α = 0.05 and 80% power.

## Amendment 8 (2026-11-11, owner OK; before the label audit, the candidate fingerprint and the seeded draw — no panel repo selected, scanned or labelled)

**Context.** A check prompted by `docs/ceil.md` — which measured defect-model effects on the eight CGR
repos — asked whether those repos could be drawn into the panel and so compromise the replication's
independence. **They cannot: the registration already excludes them** (PANEL, "Excluded": every repo
used in any temporal-crucible study to date, naming PostgreSQL, libgit2, libxml2, redis, prometheus,
commons-lang, sphinx and ripgrep). The guard was already in place and no new exclusion is needed. This
amendment records the check, fixes the one gap it exposed, and files two items that follow from it.

1. **The exclusion is registered but not implemented — it must be applied before the draw.** The frame
   files produced by the frame search (`laws-study/pilot/frame/<lang>.json`) are **raw GitHub search
   candidates**: every one of the eight excluded repos appears among them (libgit2, postgres and
   libxml2 in `c.json`; redis in `c.json` and `go.json`; prometheus in `cpp/go/python`; commons-lang in
   `java.json`; sphinx in `cpp/python`; ripgrep in `rust.json`). No exclusion list exists anywhere in
   `tools/laws_*.py`. Since the draw is "uniformly at random from the eligible list", an unfiltered
   list would silently draw an excluded repo.

   **Required before the seeded draw:** the PANEL exclusion is applied to the candidate list, the
   removed repos are **logged by name with the draw**, and the candidate fingerprint (M9) is computed
   over the **post-exclusion** list. The exclusion list is the registration's own, unchanged.

2. **`docs/ceil.md` is development-set evidence, and is now explicitly so.** Its eight repos are
   excluded panel candidates, which the registration defines as the development set ("Development set:
   the excluded repos above (pilot tools there, never panel results)"). Its results may therefore be
   used as priors and for tooling, and **never as panel results**.

3. **Pre-draw prior for LAW-6: in-cycle is expected to fail outside C.** On the development set, with
   FIXLIKE v3c labels and the registered controls (size, churn, prior fixes, authors, change coupling,
   file-clustered SEs), the in-cycle odds ratio is **1.218 pooled** but **1.073 outside C, z = 1.0,
   95% CI [0.93, 1.24] — crossing 1**. Rewiring (1.322) and coupling (1.570) stay clear of 1 outside C;
   in-cycle does not. Cleaner labels moved it: on v1 labels the same term read 1.218 outside C.

   This is recorded **before** the draw, in the spirit of LAW-8's registered "expected to fail", so the
   outcome is interpreted against a stated expectation rather than rationalised afterwards. It changes
   **no** direction, bar or verdict rule for LAW-6, which stays confirmatory as Amendment 0 item 2 left
   it.

4. **Erratum to Amendment 6 item 7.** That item cites `docs/ceil.md`'s re-fit as showing author count
   "the strongest single term in its re-fit (OR 2.06 [1.92, 2.22]), ahead of prior fixes". That figure
   is from the **v1-label** re-fit and does not survive the label fix: under FIXLIKE v3c, prior fixes
   rise to **1.893** and authors fall to **1.774**, so recidivism is the stronger term pooled. The
   point Amendment 6 was making is unaffected — both controls earn their place, and change coupling
   (1.072) still fails to displace network coupling — but the ranking is label-dependent and the v3c
   figures are the ones to quote.

5. **Unchanged.** The PANEL exclusion list itself, the scorer freeze (Amendment 5 item 8), the
   controls, the panel size, the draw procedure and seed, and every law's direction and bar.

**Evidence.** Registration PANEL section ("Excluded", "Development set");
`laws-study/pilot/frame/<lang>.json` for the candidate lists; `docs/ceil_v3c.json` (`m1_refit`) for the
re-fit figures in items 3 and 4; `docs/ceil.md` §5.
