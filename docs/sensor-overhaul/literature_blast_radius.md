# Literature scan: the blast radius of a code change

Date: 2026-11-17. Scope: where later fixes/defects land relative to an earlier change (call graph, dependency graph, file, time), and how fix / inducing / defect labels are defined and validated.

## How to read the verification marks

This scan used web search snippets and abstract pages. I did not open full PDFs for most items. Every number below is tagged:

- **[V]** = the number appeared in a search result quoting the paper's abstract or an authoritative page (arXiv, ICSE site, author page). Still re-check against the PDF before quoting in a paper.
- **[M]** = from my memory of the literature, NOT confirmed in this session. Treat as unverified. Citations marked [M] may have wrong years/venues/numbers.
- **[S]** = secondary source (blog, slide summary, survey text, student presentation).

Nothing here was invented on purpose; where I could not confirm, I say so. The reference list at the end repeats the status per source.

---

## 1. Plain-language summary

**Established.** (a) Change coupling and call/dependency structure both carry real but modest signal for "what else must change" (Zimmermann et al. ICSE 2004: correct for 26% of further files and 15% of precise functions/variables, top-3 suggestions contain a correct location 64% of the time [V, abstract]). (b) Defects are spatially and temporally clustered: a small share of files holds most faults (Kim et al. 2007: caches of ~10% of files cover 73-95% of future faults at file level, 46-72% at entity level [V, abstract + summary]). (c) "Fix" and "inducing" labels are noisy. Herzig et al. 2013: about a third of "bug" reports are not bugs [V]; Herbold et al. 2022: only about half of SZZ-found "bug fixing commits" really are [V]; Lyu et al. 2024 on Linux: 17.47% of fixes are "ghost" commits SZZ cannot trace, and over 13% of inducing commits share no file with their fix [V, abstract snippet].

**Contested.** Whether dependency-graph metrics beat or add to code metrics (Zimmermann & Nagappan 2008 say yes on Windows; a PROMISE 2009 replication said only for large systems [V, snippet]). Whether static call graphs for C are good enough (type-based indirect-call refinement removes 86-98% more targets than earlier methods, which shows how coarse the cheap approximations are [V]).

**What looks novel about our measurements.** I found no paper that measures, with a size-matched same-file null, how far *later fixes* land in the call-graph neighbourhood of *the functions an earlier change touched*, using developer-named cause pairs (message or `Fixes:` trailer) at function granularity. Closest neighbours measure (i) file-level or entity-level co-change prediction, (ii) file/binary-level defect prediction from dependency graphs, (iii) SZZ distance at line/file level. The specific combination (function-level, same-file null removing file locality, caller vs callee split, time decay to one year, callback-edge sensitivity) appears open. Caveat: my search was breadth-first and short; absence of evidence here is not proof of absence. A targeted search of "change impact" + "bug-inducing" + "call graph" in ICSE/ESEM/EMSE 2015-2026 should be done before claiming novelty.

---

## 2. Threads

### A. Change impact analysis and ripple effect

Established:
- **Zimmermann, Weißgerber, Diehl, Zeller, "Mining version histories to guide software changes", ICSE 2004 (and TSE 2005)** [V abstract]. ROSE: association rules over co-changed entities. Figures above. Evaluates by predicting held-out co-changed entities (precision/recall style). Relevant to us: baseline for history-based prediction; recall at function level is low.
- **Hassan & Holt, "Predicting change propagation in software systems", ICSM 2004** [V bibliographic; numbers S]. Compares heuristics (historical co-change, code-layout/structural, developer, process) on five open-source systems. A later paper's summary reports hybrid pruning gave best recall and that combining co-change with code layout raised precision up to 49% with recall down to 51% [S, unverified against original]. Takeaway: structural and history signals are complementary.
- **Kagdi, Collard, Maletic, "A survey and taxonomy of approaches for mining software repositories in the context of software evolution", J. Softw. Maint. Evol. 19(2), 2007** [V]. Taxonomy including evaluation methods; useful for how impact-analysis evaluation is framed.
- **Gethers, Dit, Kagdi, Poshyvanyk, "Integrated impact analysis for managing software changes", ICSE 2012** and the conceptual+evolutionary coupling line [M; the one search for it returned nothing]. Hybrid (textual + co-change + dependency) beats single sources in their evaluation, per my memory. Unverified.
- Classic ripple-effect and impact-analysis definitions: Yau & Collofello (ripple effect, 1978-1985), Bohner & Arnold, "Software Change Impact Analysis" (IEEE CS Press, 1996) [M, not opened]. Robillard, "Automatic generation of suggestions for program investigation" / topology-based impact (2005-2008) [M]. Impact analysis surveys: Li, Sun, Leung, Zhang, "Object-oriented class-level change impact analysis" survey, STVR 2013 [M].
- Hamou-Lhadj and others on dynamic impact analysis (execute-after, PathImpact; Law & Rothermel ICSE 2003) [M]. Dynamic impact analysis gives smaller, more precise sets but depends on test coverage.

Shared pitfalls:
1. Ground truth is "what changed together in the same commit", not "what later broke". Our question (later fixes) is a different target.
2. Tangled commits inflate co-change.
3. Granularity mismatch: most evaluations are at file/class level; function-level is rarer and recall drops sharply (ROSE 15%).
4. Evaluations seldom use a size- or file-matched null; file locality is silently the dominant signal.

Where later fixes land: I found **no** paper that studies where later fixes land in an earlier change's call-graph neighbourhood. The closest is SZZ-style work (thread B) and dependency-defect work (thread C). This is the clearest gap.

Against our findings: agrees with 1-3 only weakly (co-change prediction implies structural neighbourhood matters); **silent** on the same-file null, caller/callee asymmetry and decay; silent on 6.

### B. Fix-inducing / bug-introducing changes (SZZ)

Established:
- **Sliwerski, Zimmermann, Zeller, "When do changes induce fixes?", MSR 2005** [V]. Original SZZ: link fix commits to bug reports via commit-message references, `diff`/`annotate` back to the last modifying commit of the changed lines, filter by report date. Mozilla and Eclipse. Finds fix-inducing changes differ in size and day of week.
- Kim, Zimmermann, Pan, Whitehead, "Automatic identification of bug-introducing changes", ASE 2006 (annotation graph, AG-SZZ) [M]; Williams & Spacco, "SZZ revisited", DEFECTS 2008 (line-mapping, weights) [M]; Davies, Roper, Wood, "Comparing text-based and dependence-based approaches for determining the origins of bugs", JSEP 2014 (dependence-based: V-SZZ-like) [M]; da Costa et al., "A framework for evaluating the results of the SZZ approach", TSE 2017 (R-SZZ/MA-SZZ naming, evaluation criteria) [M]; Neto, da Costa, Kulesza, "The impact of refactoring changes on the SZZ algorithm", SANER 2018 (RA-SZZ) [M]; Bao et al. V-SZZ, ASE 2022 [M]; L-SZZ (Rosa et al. / Tufano line-level) [M]. Several SZZ variants are implemented in PySZZ (Rosa et al.) [M].
- **Rosa, Pascarella, Scalabrino, Tufano, Bavota, Lanza, Oliveto, "Evaluating SZZ implementations through a developer-informed oracle", ICSE 2021** [V]. Oracle built from fix commits whose messages name the inducing commit (NLP + manual filtering): 1,115 commits (129 with issue info), nine SZZ implementations compared; large differences; "considerable room for improvement". **Closest design analogue to our named-cause pairs.**
- **Lyu, Kang, Widyasari, Lawall, Lo, "Evaluating SZZ implementations: an empirical study on the Linux kernel", TSE 2024 (arXiv 2308.05060)** [V]. KFC dataset: 78,384 candidate commits with `Fixes:`, 76,046 with at least one well-formed inducing reference, over 99% of annotations point to existing commits. SZZ variants: 17.47% ghost commits, over 13% of inducing commits share no file with their fix. TC-SZZ proposed.
- **Herbold, Trautsch, Trautsch, Ledel, "Problems with SZZ and features", EMSE 27(2022):42** [V]. 398 releases, 38 Apache projects; only about half of SZZ-identified bug-fixing commits are bug fixes; six-month release window mislabels.
- Distance inducing-to-fix: SZZ by construction is line-level (same line lineage). Lyu's 13% "no shared file" figure [V] implies that, for developer-named Linux causes, a nontrivial minority is out of file. Our curl data: 15% out-of-file, OpenSSL 42% touch the same function; this is **consistent with** Lyu's 13%, **reported by us as a distance profile, which the SZZ papers treat as a failure mode of SZZ rather than a result.** Time lag: Linux bug lifetime blog (Pebblebed, 2026, ~125k bugs from `Fixes:` tags: median 0.7 y, mean 2.1 y, right-censored) [S].

Shared pitfalls: line-based assumption (fix lines blame to cause) fails for omission/latent bugs; refactoring, formatting, tangled commits; right-censoring of time lags; selection on developer-named causes (our design shares this: pairs that are named may be systematically easier/more local than unnamed ones; Rosa and Lyu both acknowledge dataset selection).

Against our findings: finding 1 (71% function overlap, 85% same file in curl) and finding 2 (42% in OpenSSL) **agree in direction** with Lyu's out-of-file minority; the wide spread between repos is itself consistent with SZZ papers' repo-dependent recall. Finding 4 (types not separating) is **silent**-in literature; SZZ papers do not subtype.

### C. Locality of defects

Established:
- **Kim, Zimmermann, Whitehead, Zeller, "Predicting faults from cached history", ICSE 2007** [V]. Temporal locality (recently changed/fixed), spatial locality (nearby entities, via co-change/co-location), changed-entity locality. 73-95% file-level (cache of ~10% of files) and 46-72% entity-level accuracy [V, with the caveat that "accuracy" is fault-coverage].
- Hassan & Holt, "The top ten list: dynamic fault prediction", ICSM 2005 [M]; Graves, Karr, Marron, Siy, "Predicting fault incidence using software change history", TSE 2000 [M] (past changes, weighted by age, predict faults better than size); Nagappan & Ball, "Use of relative code churn measures to predict system defect density", ICSE 2005 [M]; Ostrand, Weyuker, Bell, "Predicting the location and number of faults in large software systems", TSE 2005 [M] (about 20% of files hold about 80% of faults; prior faults and changes predictive); D'Ambros, Lanza, Robbes, "Evaluating defect prediction approaches: a benchmark and an extensive comparison", EMSE 2012 and "On the relationship between change coupling and software defects", WCRE 2009 [M].
- **Zimmermann & Nagappan, "Predicting defects using network analysis on dependency graphs", ICSE 2008** [V partial]. Windows Server 2003 binaries: network measures gave recall 10 points above complexity metrics; identified 60% of binaries developers considered critical, twice complexity metrics. **Tosun, Turhan, Bener, PROMISE 2009**: network measures matter for large complex systems, not small ones [V, snippet]. Bird, Nagappan, Gall, Murphy, Devanbu, "Putting it all together: using socio-technical networks to predict failures", ISSRE 2009 [M]. Premraj & Herzig, "Network versus code metrics to predict defects: a replication study", ESEM 2011 [M] (reported to find network metrics offer little over code metrics, per my memory; verify).

Shared pitfalls: unit is file/binary, not function; "defect" is post-release bug counts, not fixes caused by a named change; size/churn confound; prediction metrics (recall at fixed effort) are not ratio-to-null effects; time-split leakage.

Agree / conflict:
- Our "fades within about a year" (finding 2): **consistent with** temporal locality that weights recent history (Graves, Kim BugCache recency, Hassan-Holt top ten) [M/V]. I found no paper reporting a one-year disappearance of a *structural* neighbourhood effect specifically.
- Our modest 1.1-1.6x vs same-file: the file-level literature's strong concentration (20/80, 10%->73-95%) is mostly **file locality**, which our same-file null deliberately removes. These are **not in conflict**; they measure different layers. Finding 3 (1.09x) says that after removing file locality, the call-graph increment is small.
- Dependency-network results (Zimmermann & Nagappan) are about *which modules are defect-prone*, not which functions neighbour a change. **Silent** on our caller/callee split. Premraj & Herzig's weak-network result [M] would be **consistent** with small increments.
- Finding 5 (size confounds everything; zero-parameter lead): **agrees** with the long-running size-confound critique (El Emam et al., "The confounding effect of class size", TSE 2001 [M]).

### D. Static call graphs for C, function pointers, callbacks

Established:
- **Murphy, Notkin, Griswold, Lan, "An empirical study of static call graph extractors", ICSE 1996 / TOSEM 7(2) 1998** [V partial]. Compared several C call-graph extractors (including cflow) on mapmaker, mosaic, gcc: significant differences in how constructs (function pointers, macros) are handled.
- **Milanova, Rountev, Ryder, "Precise call graphs for C programs with function pointers", Autom. Softw. Eng. 11, 2004** [V partial]. Pointer-analysis call graphs on test programs matched a "fully precise" call graph in all their data programs (small programs).
- **Lu & Hu, "Where does it go? Refining indirect-call targets with multi-layer type analysis" (TypeDive/MLTA), CCS 2019** [V]. Linux, FreeBSD, Firefox: 86-98% more indirect-call targets eliminated than prior type-based approaches without new false negatives. **Xia, Hu, Wu, "DeepType", USENIX Security 2024**: further 43.11% narrowing on average [V]. Shows the baseline (signature/type-matching) is very coarse, and that callback/ops-table dispatch in C systems code is the dominant source of missing/spurious edges.
- Other: KRover-style / Linux kernel indirect-call studies (Linux kernel `ops` tables, "Fine-grained CFI" literature) [M]; SVF (Sui & Xue, CC 2016) [M]; Code2flow/CScout/egypt/doxygen: I could not find an empirical comparison paper (search came up empty) [unverified].
- Tree-sitter-style syntactic approximations: I found no paper quantifying their accuracy for C. Name-based resolution with macros unexpanded is a known weakness (no preprocessing) [M].

Against our findings: finding 6 (81% of caller-less functions referenced as callbacks; adding them moved the radius 1.77 -> 1.87) is **consistent** with Murphy 1998 (tools disagree on function pointers) and with TypeDive-line (indirect calls matter) but the *small effect on the radius* is **not addressed** in literature; no impact-analysis paper I found measures sensitivity of their metric to missing indirect edges. Open.

### E. Labels: "fix", "bug", "regression"

Conventions:
- **Conventional Commits** (spec v1.0.0, conventionalcommits.org): `fix:` type, `BREAKING CHANGE:` footer; a *convention*, not a validated label [S, project spec; not opened].
- **Linux `Fixes: <12+ hex> ("subject")`**: documented in `Documentation/process/submitting-patches.rst`; introduced as common practice around Oct 2013 per Lyu [V]. Coverage: the KFC dataset has ~76k well-formed; a blog estimate says only about 28% (about 124k of about 448k "fix"-mentioning commits) carry proper `Fixes:` tags [S; crude keyword denominator]. Kernel's own `Fixes:` is peer-reviewed, which Lyu cite as quality control [V].
- `Closes #N`/`Fixes #N`: GitHub/GitLab auto-close keywords; link to *issue*, not to cause [M].
- Regression terms: "Regression from ..." / `Reported-by` / `Regzbot` (Linux regression tracker). **Ruohonen & Alami, "Fast fixes and faulty drivers: an empirical analysis of regression bug fixing times in the Linux kernel", arXiv 2411.02091 (2024)** [V snippet; arXiv preprint]: regzbot data 2021-2024, fixing times averaging under a month, drivers most prone, weak churn signal.
- **Antoniol, Ayari, Di Penta, Khomh, Guéhéneuc, "Is it a bug or an enhancement? A text-based approach to classify change requests", CASCON 2008** [M]: text classification of issue types, accuracy roughly 77-82% in my memory; unverified.
- **Herzig, Just, Zeller, ICSE 2013** [V]: manual check of >7,000 reports in five projects; about a third not bugs; 39% of files flagged defective had never had a bug (average) [V, secondary summary of abstract].
- **Herbold et al. 2022** [V]: SZZ's fix set about half correct.
- Standards: IEEE 1044 (Standard Classification for Software Anomalies, 1993/2009) and IBM ODC (Chillarege et al., TSE 1992) [M]. Both define *defect* classification schemes for tracker records; I know of no evidence they are used for commit-level mining. Mining studies use ad hoc keyword/regex rules (Mockus & Votta, ICSM 2000, commit-message classification [M]); Levin & Yehudai on commit classification [M]. Open question: no accepted cross-repo definition of "regression fix".

#### Labels and datasets table

Sizes marked [V] were quoted in search results; others [M] or unverified.

| Name | Size | Languages | Label source | Level | Inducing commit? | Known noise | Link |
|---|---|---|---|---|---|---|---|
| Linux KFC (Lyu et al.) | 78,384 candidates; 76,046 well-formed [V] | C | `Fixes:` trailers, peer-reviewed | commit | yes (named) | 17.47% ghost for SZZ; 13% no shared file [V]; only a fraction of all fixes tagged [S] | https://arxiv.org/abs/2308.05060 |
| Rosa et al. oracle | 1,115 commits (129 with issue info) [V] | multiple Java/other [M] | developer message names cause + manual filter | commit | yes | selection on named causes | https://arxiv.org/abs/2102.03300 |
| Defects4J | ~835 bugs, 17 Java projects [M; unverified count] | Java | issue tracker + manual isolation | commit/method via diff | partial (fix + buggy version; inducing not standard) | minimised patches, tests chosen | https://github.com/rjust/defects4j [M, not opened] |
| BugsInPy | 493 bugs, 17 Python projects [M] | Python | manual from fix commits | commit | no | curated | https://github.com/soarsmu/BugsInPy [M] |
| ManySStuBs4J | ~63k single-statement bugs (large variant) [M] | Java | mining + pattern | statement/commit | no | simple bugs only | [M] |
| Bugs.jar | 1,158 bugs, 8 Apache projects [M] | Java | JIRA + commit links | commit | no | JIRA linkage | [M] |
| BugSwarm | thousands of CI fail/pass pairs [M] | Java/Python | Travis CI reproduction | commit pair | no | CI flakiness | [M] |
| CVEfixes | 564 projects, 168,089 functions, 8,932 vulnerable [S survey] | many | NVD CVE -> fix commit | function (every touched function labeled vulnerable) | no | over-labels all touched functions [S] | [M] |
| Big-Vul | ~188k functions, ~10.9k vulnerable [S] | C/C++ | CVE -> fix commit | function | no | label accuracy about 25% per DiverseVul audit [S] | [M] |
| DiverseVul | 330,492 non-vulnerable + ~18.9k vulnerable, 150 CWEs, 7,514 commits [S summary of arXiv 2304.00409] | C/C++ | security-issue trackers + commits | function | no | about 60% label accuracy [S] | https://arxiv.org/abs/2304.00409 |
| CrossVul, Devign | [M] unverified sizes | many; C | CVE commits; manual labelling (Devign) | function/commit | no | not checked | [M] |
| OSV | large, ecosystem-wide [M] | many | `introduced`/`fixed` git ranges from advisories | commit ranges | yes (introduced) when provided | range quality varies; many advisories lack git ranges | https://osv.dev [M, not opened] |
| NVD / kernel CNA | kernel CNA assigns CVEs to fixing commits since 2024 [M] | C | kernel CNA ties CVE to fix commit; `Fixes:` often gives introducer | commit | often via `Fixes:` | CNA volume very high, includes minor bugs | [M] |
| GitHub Advisory DB | [M] | many | advisories + affected ranges | package/commit | partial | package-level mostly | [M] |

I did not open the Defects4J/BugsInPy/Bugs.jar/BugSwarm/ManySStuBs/CrossVul/Devign/OSV/GHSA pages; those rows are from memory and flagged for verification. Of these, only Linux KFC, Rosa's oracle and OSV (when ranges exist) carry an inducing commit; the vulnerability datasets label functions from fix commits only and are known to be over-inclusive.

Against our findings: E is the **methodological home of finding 4** (fix type separation). Herzig/Herbold imply even our "fix" pool contains non-fixes; our named-cause design sidesteps part of this (developer asserts causation) but not selection bias.

### F. Regression test selection and regression bugs

- **Rothermel & Harrold, "A safe, efficient regression test selection technique", TOSEM 1997** [V]: CFG-based safe RTS selects all tests that could expose faults in modified code under stated conditions. Empirical follow-up TSE 1998 [V snippet]. **Yoo & Harman, "Regression testing minimization, selection and prioritization: a survey", STVR 2012** [M; not confirmed in search].
- Practical RTS (Ekstazi, Gligoric et al., ISSTA 2014; STARTS) uses file/class dependency closures [M]. These use static or dynamic dependency *reachability from a change* as the safety envelope; they are the engineering counterpart of blast radius but evaluated on test-selection, not on where real regressions occurred.
- Linux regression studies: Ruohonen & Alami 2024 [V snippet, preprint] on regression fixing time. No paper found that measures *distance* of regressions from the change in the call graph.
- Chrome/Mozilla regression studies (e.g. regression-range bisection data, Mozilla `regressed_by` field) [M, not searched]: a possible label source (Bugzilla `regressed_by`).

Against our findings: RTS safety conditions assume regressions occur in code that *depends on* changed code, i.e. callers/transitively affected -> **agrees** with caller enrichment (1, 3) but our callee enrichment (OpenSSL callers=callees) and decay with time are **not covered**.

### G. Bug / defect / fault propagation; co-fixing

- Defect propagation along dependencies: Zimmermann & Nagappan 2008 [V] (dependencies of defect-prone binaries are risky; network measures). Early work on "bug propagation" and fault-proneness of dependent classes (e.g. Cataldo et al., "Software dependencies, work dependencies, and their impact on failures", TSE 2009 [M]; Nagappan/Murphy on dependency + failures [M]). These show that failure counts correlate with dependency measures, again at file/module level.
- Co-fixing / co-changing: ROSE-style co-change [V]; "bug-fix co-change" and "fix-inducing co-change" ideas (e.g. Herzig? "Impact of tangled code changes", MSR 2013, Herzig & Zeller [M]) flag that fixes touching many files are partly tangled.
- Propagation at function level with developer-named causes: not found.

Against our findings: **silent** on 1-3, and the main available evidence is correlational at coarser units.

---

## 3. Ranked gaps our design can address

1. **Function-level, call-graph distance of later fixes from a named-cause change with a same-file size-matched null** (our core). *Novel* (to my search; verify).
2. **Time decay of the structural excess (fades after about a year)**: measure across more repos with `Fixes:` trailers. *Replication* of the temporal-locality idea, *novel* for the structural neighbourhood.
3. **Caller vs callee asymmetry** (curl yes, OpenSSL no): a third and fourth repo settles it. *Replication/novel*.
4. **Sensitivity of any blast-radius metric to missing indirect/callback edges** (finding 6; radius 1.77 -> 1.87). *Novel*; no impact-analysis paper reports this.
5. **Selection bias of developer-named causes**: compare named vs SZZ-found vs unnamed fixes' locality. *Novel*; links to Rosa/Lyu "ghost" findings.
6. **Pool-ability of labels across repos**: same analysis with `Fixes:`-trailer vs message-regex vs issue-label pools; show effect sizes move or not. *Novel* (labels literature mostly measures accuracy, not effect-size stability).
7. **Fix-type taxonomy at commit level (regression/latent/extrinsic)**: replicate our non-separation using Linux `Fixes:` + `Cc: stable` and regzbot. *Replication/novel*.
8. **Per-function structure (zero-parameter lead) after size control**: replicate on larger Linux sample. *Replication of size-confound critique, novel lead*.
9. **Hybrid tests: does call-graph proximity add anything over co-change proximity for predicting *fix* locations** (Zimmermann ROSE vs structural) at function level. *Replication of hybrid-IA*, new target.
10. **Dependence of results on the git hunk-header function mapping** (our method) vs AST-based mapping; quantify misattribution. *Novel methodological check*.

### Candidate repositories / datasets (re-run named-cause design beyond curl/OpenSSL/FreeBSD)

I have NOT counted trailers in any of these; usage statements are from memory and must be confirmed by `git log --grep '^Fixes:'` counts. Recommended first step: a counting script per repo (share of commits with `Fixes:` / of commits with "fix" in subject).

1. **Linux kernel subsystems** (net, drivers/gpu, fs, mm, kernel/): `Fixes:` is documented practice since about 2013 [V via Lyu]; KFC gives 76k pairs [V]. Compare subsystems (drivers vs core). Note: C, heavy function-pointer ops tables, so finding 6 is stress-tested.
2. **DPDK**: contribution guidelines require `Fixes:` with 12-char hash; mailing-list-reviewed [M, unverified].
3. **Xen**: `Fixes:` requested for bug-fix patches [M, unverified].
4. **Mesa**: `Fixes:` used to drive stable-branch cherry-picks, so coverage is likely high [M, unverified].
5. **QEMU**: `Fixes:` used inconsistently, often for issue links (`Resolves:`/`Fixes: https://gitlab...`) as well as shas [M, unverified]; need to separate sha-form from URL-form.
6. **systemd, U-Boot**: partial/rising use [M, unverified]; systemd's `Fixes: #123` is issue-form, not a cause. Treat as low-priority until counted.
7. **Rosa et al. oracle** (1,115 named-cause commits, public) [V]: ready-made pairs across Java/other repos; function-level mapping needs rebuild. Useful as a cross-language check.
8. **OSV / kernel CVE (CNA)** pairs with `introduced` ranges [M, unverified]: security-only subset; differs in class of bug, so report separately.

---

## 4. References (status: P = primary opened abstract/page this session, Pm = primary but known from memory only, S = secondary, U = unverified)

1. Sliwerski, Zimmermann, Zeller. When do changes induce fixes? MSR 2005. https://www.st.cs.uni-saarland.de/papers/msr2005 [P, abstract page]
2. Rosa et al. Evaluating SZZ implementations through a developer-informed oracle. ICSE 2021. https://arxiv.org/abs/2102.03300 [P]
3. Lyu, Kang, Widyasari, Lawall, Lo. Evaluating SZZ implementations: an empirical study on the Linux kernel. TSE 2024. https://arxiv.org/abs/2308.05060 [P, abstract snippets]
4. Herbold, Trautsch, Trautsch, Ledel. Problems with SZZ and features. EMSE 27:42, 2022. https://arxiv.org/abs/1911.08938 [P]
5. Herzig, Just, Zeller. It's not a bug, it's a feature. ICSE 2013. https://www.st.cs.uni-saarland.de/publications/files/herzig-icse-2013.pdf [P, abstract]
6. Zimmermann, Weißgerber, Diehl, Zeller. Mining version histories to guide software changes. ICSE 2004. https://www.st.uni-trier.de/diehl/pubs/icse04.pdf [P, abstract numbers]
7. Hassan, Holt. Predicting change propagation in software systems. ICSM 2004. https://scilit.net/publications/911e9bd6100bdee97a2d96ed549f958b [bibliographic only; numbers S]
8. Kagdi, Collard, Maletic. A survey and taxonomy of approaches for mining software repositories in the context of software evolution. JSME 19(2), 2007. DOI 10.1002/smr.344 [P bibliographic]
9. Kim, Zimmermann, Whitehead, Zeller. Predicting faults from cached history. ICSE 2007. https://www.st.cs.uni-saarland.de/edu/softmine2007/Papers/kim-icse-2007.pdf [P, abstract]
10. Zimmermann, Nagappan. Predicting defects using network analysis on dependency graphs. ICSE 2008. https://www.microsoft.com/en-us/research/publication/predicting-defects-using-network-analysis-on-dependency-graphs/ [P, abstract]
11. Tosun, Turhan, Bener. Validation of network measures as indicators of defective modules. PROMISE 2009. https://research.itu.edu.tr/en/publications/validation-of-network-measures-as-indicators-of-defective-modules/ [P snippet]
12. Lu, Hu. Where does it go? (TypeDive/MLTA). CCS 2019. https://gts3.org/assets/papers/2019/lu:typedive.pdf [P]
13. Xia, Hu, Wu. DeepType. USENIX Security 2024. https://www.usenix.org/conference/usenixsecurity24/presentation/xia [P snippet]
14. Murphy, Notkin, Griswold, Lan. An empirical study of static call graph extractors. ICSE 1996 / TOSEM 7(2), 1998. https://homes.cs.washington.edu/~notkin/pubs/icse18-cg.html [P abstract page; details from search summary]
15. Milanova, Rountev, Ryder. Precise call graphs for C programs with function pointers. ASE 11, 2004. https://www.academia.edu/15894167 [P snippet]
16. Rothermel, Harrold. A safe, efficient regression test selection technique. TOSEM 1997. https://www.cs.purdue.edu/homes/xyzhang/fall07/Papers/p173-rothermel.pdf [P]
17. Ruohonen, Alami. Fast fixes and faulty drivers: regression bug fixing times in the Linux kernel. arXiv 2411.02091, 2024. https://arxiv.org/abs/2411.02091 [preprint, snippet]
18. DiverseVul (Chen et al.). arXiv 2304.00409, 2023. https://arxiv.org/abs/2304.00409 [numbers via S survey snippets]
19. Pebblebed blog, "kernel bugs" 2026. https://pebblebed.com/blog/kernel-bugs [S, blog; single author, not peer reviewed]
20. Antoniol et al., Is it a bug or an enhancement? CASCON 2008 [Pm/U]
21. Gethers et al., Integrated impact analysis for managing software changes, ICSE 2012 [Pm/U]
22. Graves, Karr, Marron, Siy, TSE 2000; Nagappan & Ball ICSE 2005; Ostrand, Weyuker, Bell TSE 2005; D'Ambros, Lanza, Robbes EMSE 2012 and WCRE 2009; Hassan & Holt "top ten list" ICSM 2005 [Pm/U]
23. Kim et al. ASE 2006 (AG-SZZ); Williams & Spacco 2008; Davies, Roper, Wood JSEP 2014; da Costa et al. TSE 2017; Neto et al. SANER 2018 (RA-SZZ); Bao et al. ASE 2022 (V-SZZ) [Pm/U]
24. Bohner & Arnold 1996; Yau & Collofello; Robillard; Law & Rothermel ICSE 2003; Li et al. STVR 2013; Yoo & Harman STVR 2012; Gligoric et al. ISSTA 2014 [Pm/U]
25. Premraj & Herzig ESEM 2011; Bird et al. ISSRE 2009; Cataldo et al. TSE 2009; El Emam et al. TSE 2001; Herzig & Zeller MSR 2013 [Pm/U]
26. IEEE 1044; Chillarege et al. ODC TSE 1992; Conventional Commits 1.0.0 (https://www.conventionalcommits.org) [Pm/U, S for the spec]
27. Datasets not opened: Defects4J, BugsInPy, ManySStuBs4J, Bugs.jar, BugSwarm, CVEfixes, Big-Vul, CrossVul, Devign, OSV, GHSA, kernel CNA [U]

Items 20-27 should be treated as leads, not citations, until opened.
