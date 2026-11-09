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
