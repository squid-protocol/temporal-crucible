# Prior-work check: where does a fix land relative to the commit that caused the bug?

Date: 2026-11-18. Adversarial: the aim was to find reasons the finding is NOT novel.

## Method and honesty notes

- Searches were web searches plus fetches. Where I could download a PDF I read the text myself (marked READ). Where I only saw an abstract or a search snippet, that is marked ABSTRACT-ONLY or SNIPPET. I did not have full-text access to several key papers (Gu 2021, Park 2012/2017, Lyu 2023 body); numbers from them are abstract-level.
- The previous scan `literature_blast_radius.md` was NOT found at the stated path (file does not exist in this worktree), so nothing from it was reused or re-checked. Nothing below depends on it.
- "Preprint" = arXiv/not peer reviewed. "Blog" = non-academic.
- Not searched / not covered: ICSE/FSE/MSR proceedings beyond what search engines surfaced; the Linux "regzbot"/stable-backport literature other than titles; Google Scholar forward citations of Wen 2019 and Park 2017 (the most likely places for a closer paper). A closer paper may exist.

## Verdict table

| # | Claim | Verdict | Closest work |
|---|---|---|---|
| 1 | 42-71% of fixes land in a function the cause changed | PARTLY (file and statement level established, function level not found with Fixes tags) | Wen et al. FSE 2019; Lyu et al. TSE 2024 |
| 2 | Fix outside the changed set sits 1-2 call edges from it, ~2x a same-file baseline | PARTLY: direction of effect is known (structural dependency), the hop-distance-vs-matched-baseline ratio is NOT FOUND | Park/Kim/Bae 2012, 2017; Wen 2019; Gu et al. 2021 |
| 3 | Same-file fixes land in callees, different-file fixes in callers | NOT FOUND (no study located that splits by direction) | Ye/Meng/Zhong ICSME 2018 (co-change callers with a shared callee; all changes, not cause-fix) |
| 4 | Fix has same diff shape as cause; locking begets locking; large causes give dispersed, slower fixes | PARTLY for "shape" (change-action overlap); NOT FOUND for locking at 2.5x and for size effect on dispersion/lag | Wen 2019 (43.1% change-action overlap) |
| 5 | Median cause-to-fix lag ~8 months; proximity fades mildly with lag | Lag magnitude ESTABLISHED in kind (but means of ~2 years are reported, not medians of 8 months); fading of proximity with lag NOT FOUND | Chou 2001; Palix 2014; Pebblebed blog (not peer reviewed) |

Short version: claims 1, 2 (qualitatively) and the existence of "fix is structurally near the cause" are known. The quantification is new in kind: function-level, hop distance, matched same-file baseline, Linux Fixes-tag scale (14,444 pairs), direction split, lag decay. I could not find a paper that does that, but see the caveat on coverage.

## Works found, with what each actually measured

### A. Closest: relation between inducing and fixing commits

1. Wen, Wu, Liu, Tian, Xie, Cheung, Su. "Exploring and Exploiting the Correlations between Bug-Inducing and Bug-Fixing Commits." ESEC/FSE 2019, pp. 326-337. DOI 10.1145/3338906.3338962. READ (full text).
   - Data: 333 bugs, 7 Java projects (incl. Defects4J subset of 91), inducing commits identified from developer knowledge (not SZZ).
   - Measured: file coverage, statement coverage, change-action coverage between inducing and fixing commits. No call graph; no hop distance; no baseline.
   - Found: 73.2% of fixed files were also modified by the inducing commit (65.6-81.5% by project). 64.6% of fixed statements were modified by the inducing commit (71.1% with data/control-flow slicing). Of the 26.8% fixes in different files, 17.9% config/log, 14.2% incomplete changes, and for 73.6% of the remaining 67.9% the files are "directly dependent" (class use, superclass/subclass, imports), i.e. 50.0% of all different-file cases. 43.1% of fix change actions can be inferred from the inducing change's actions; 52.6% via reverting them.
   - Claims: 1 at file/statement level (not function). 2 in direction only (dependent files, class-level, no hop distance or baseline). 4 partly (change-action correlation; not locking, not size).

2. Park, Kim, Ray, Bae. "An Empirical Study of Supplementary Bug Fixes." MSR 2012, pp. 40-49, DOI 10.1109/MSR.2012.6224298. SNIPPET/ABSTRACT-ONLY.
   Park, Kim, Bae. "An empirical study of supplementary patches in open source projects." Empirical Software Engineering 22(1):436-473, 2017, DOI 10.1007/s10664-016-9432-x. ABSTRACT-ONLY.
   - Not cause-vs-fix but first-fix vs follow-up-fix. Eclipse JDT, SWT, Mozilla. Reported: 67-68% of newly modified files in supplementary fixes have structural dependencies (calls, field access, subtyping) to the initial fix location; 16-46% lie beyond immediate structural dependency; co-change history predicts poorly.
   - Claim 2: the nearest published support for "follow-up change lands structurally near earlier change"; granularity file/location, immediate dependency only, no hop-distance curve, no matched baseline as far as I could see.

3. Lyu, Kang, Widyasari, Lawall, Lo. "Evaluating SZZ Implementations: An Empirical Study on the Linux Kernel." IEEE TSE (accepted; arXiv 2308.05060, v2 June 2024). Abstract READ via fetch; body not read.
   - Data: 76,046 Linux bug-fix/bug-inducing pairs from developer-labelled (Fixes) commits (as of v6.1-rc5). Same population as claim 2's kernel data, so this is the dataset a reviewer will cite.
   - Found: 34.6% of inducing commits are in the function history of the fix lines, 27.5% in file history only (rest outside file history, per the search snippet that 37.9% not in file history; abstract truncated in my fetch). 17.47% "ghost commits" SZZ cannot trace. Examples of cross-directory fixes.
   - Claim 1: the closest function-level number on the kernel. NOTE: it is the converse view (is the inducing commit in the history of the fixed function), so it is not the same quantity as "fix lands in a function the cause changed", but it brackets your 42-71% range in an obviously related way. Check this before publishing; your range and theirs must be reconciled.

4. Rosa, Pascarella, Scalabrino, Tufano, Bavota, Lanza, Oliveto. "Evaluating SZZ Implementations Through a Developer-informed Oracle." ICSE 2021, pp. 436-447, DOI 10.1109/ICSE43902.2021.00049 (arXiv 2102.03300). ABSTRACT/SNIPPET. Oracle from commits that explicitly reference the inducing commit, the same device as Fixes trailers. Evaluates SZZ recall/precision; not fix location.

5. Gu, Han, Kim, Zhang. "Do Bugs Propagate? An Empirical Analysis of Temporal Correlations among Software Bugs." ECOOP 2021 (LIPIcs 194, 11:1-11:21). ABSTRACT-ONLY (Dagstuhl page). Software graphs from artifact ties (function calls, type hierarchy, a third tie not named on the page), longitudinal logistic regression on time-lagged bug correlations, four Java projects (names from a secondary blog: HTTPClient, Jackrabbit, Lucene, Rhino). Finds bugs propagate along certain tie graphs. A secondary blog (shape-of-code.com) says call-chain neighbours improve next-release fault prediction. I could not verify granularity or effect sizes.
   - Claim 2: this is the strongest "adversarial" hit for the idea that defects are correlated along call edges over time. It does not use Fixes-tagged causal pairs, does not measure hop distance to the changed set, and (as far as I can tell) not versus a same-file matched baseline. Must be read in full before the novelty statement is final.

6. Kim, Zimmermann, Whitehead, Zeller. "Predicting Faults from Cached History." ICSE 2007, pp. 489-498, DOI 10.1109/ICSE.2007.66. ABSTRACT/SNIPPET. Bug locality: faults cluster in space (entities co-changed with, or near, a known fix) and time. Predicts 73-95% of faults at file level, 46-72% at entity level. Establishes the general principle behind claim 2 (spatial locality of faults) but with co-change, not call graphs, and for predicting new faults, not locating a fix relative to its cause.

### B. Dependency/call-graph signals for defects and change propagation

7. Zimmermann, Nagappan. "Predicting Defects using Network Analysis on Dependency Graphs." ICSE 2008, pp. 531-540, DOI 10.1145/1368088.1368161. ABSTRACT. Windows Server 2003 binaries; network measures on dependency graphs give about 10 points higher recall than complexity metrics. Centrality of a unit predicts defects; says nothing about fix location relative to a cause.

8. Hassan, Holt. "Predicting change propagation in software systems." ICSM 2004. SNIPPET (abstract only; I did not retrieve heuristics or numbers). Heuristics (including structural/call-based and co-change) validated on five open source systems. Ordinary maintenance changes, not bug causes and fixes.

9. Musco, Monperrus, Preux. "A Large-Scale Study of Call Graph-based Impact Prediction using Mutation Testing." Software Quality Journal 25(3):921-950, 2017 (arXiv 1812.06286). ABSTRACT. 17,000 mutants, 10 Java projects; the simplest call graph gives the best F-score for impact prediction. Useful as the established method for "call graph proximity predicts impact of a change", at the level of test failures rather than later fixes.

10. Ye (Wang), Meng, Zhong. "An Empirical Study of Multi-Entity Changes in Real Bug Fixes." ICSME 2018 (venue inferred from PDF filename; title/abstract READ). Aries, Cassandra, Derby, Mahout. 52-58% of bug fixes change multiple entities; co-changed pairs mostly invoke the same method, access the same field or have similar content; change dependency graphs from interprocedural analysis. Within one fix, not cause vs fix. Nearest on claim 3 flavour (callers edited alongside a shared callee) but does not give direction by same-file versus cross-file.

11. Davies, Roper, Wood. "Comparing text-based and dependence-based approaches for determining the origins of bugs." J. Software: Evolution and Process 26(1):107-139, 2014, DOI 10.1002/smr.1619. ABSTRACT. 174 manually identified bug origins in 3 projects; text-based vs dependence-based origin finding, precision 29-79%, recall 40-70%. Uses dependence to go from fix to cause, which presupposes the relation in claim 2 but does not quantify it as a radius.

### C. Fixes of fixes and incomplete fixes

12. Yin, Yuan, Zhou, Pasupathy, Bairavasundaram. "How Do Fixes Become Bugs?" ESEC/FSE 2011, pp. 26-36. ABSTRACT/SNIPPET. Linux, OpenSolaris, FreeBSD, a commercial OS: 14.8-24.4% of sampled post-release fixes were incorrect; concurrency fixes 39% incorrect. Fix-of-fix prevalence, no function/call-graph location analysis.

13. Liu, Zhang, Jiang, Wu, Zhou. "Characteristics, Root Causes, and Detection of Incomplete Security Bug Fixes in the Linux Kernel." arXiv 2511.17799, Nov 2025. PREPRINT. Only metadata and section outline readable; from search snippet: 26 incomplete security fixes analysed. Small and security-specific; I could not verify what it says about location.

14. Jiang, Jiang, Wu, Ma, Luo, Zhou. "Understanding Vulnerability Inducing Commits of the Linux Kernel." ACM TOSEM 33(7), 170, 2024, DOI 10.1145/3672452. SNIPPET. First study of kernel vulnerability-inducing commits using Fixes tags among other identification methods. Did not find findings on fix location.

15. Śliwerski, Zimmermann, Zeller. "When do changes induce fixes?" MSR 2005, pp. 24-28. ABSTRACT. Origin of the fix-inducing-change framing; large transactions are more often fix-inducing; Mozilla, Eclipse. Relevant to claim 4's size angle (large changes induce more fixes) but not to fix dispersion or lag.

16. Purushothaman, Perry. "Toward understanding the rhetoric of small source code changes." IEEE TSE 31(6):511-526, 2005. ABSTRACT/SNIPPET. Lucent 5ESS: about 50% of changes small; about 40% of fault-fixing changes caused further faults. Size and fix-inducing relation; not location.

### D. Linux lifetimes (claim 5)

17. Chou, Yang, Chelf, Hallem, Engler. "An Empirical Study of Operating Systems Errors." SOSP 2001, pp. 73-88. SNIPPET. About 1.8 years average lifetime for certain error types; roughly exponential distribution with long tail (secondary Berkeley summary).
18. Palix, Thomas, Saha, Calvès, Muller, Lawall. "Faults in Linux 2.6." ACM TOCS 32(2), 4, 2014 (arXiv 1407.4346). SNIPPET. Average fault lifespan 2.5-3.0 years; visible-impact fault kinds as short as about 1 year. Means, static-analysis faults, not Fixes-tag medians.
19. Pebblebed (Jenny Guanni Qu), blog posts "kernel bugs" and "Who writes the bugs" (Jan 2026). BLOG, NOT PEER REVIEWED. 125,183 Fixes-tag bugs; average 2.1 years; self-fix lifetime 0.88 years vs cross-fix 2.59; per-subsystem variation. Their numbers differ from your 8-month median (mean vs median and tagging coverage differ; the blog itself notes only about 28% of fix commits carry proper Fixes tags). Do not cite as evidence; cite only to explain that mean and median differ.
20. Fast Fixes and Faulty Drivers: regression bug fixing times in the Linux kernel. arXiv 2411.02091. PREPRINT, snippet only.

### E. SZZ limits (context, not direct)

- Wen 2019 (above) finds SZZ recall 63.7% / precision 68.7% in their benchmark and that 8 of 10 earlier SZZ-based findings are significantly affected (READ).
- Quach et al., EMSE 2021; Herbold et al. "Problems with SZZ and features" (Göttingen); SANER 2025 "corner cases in bug-inducing commits": SNIPPETS ONLY, titles seen in search, not read.
- Consequence for your method: because you use Fixes trailers and not SZZ, you avoid the main SZZ error source, but the trailer population is a biased subset (kernel: about 28% of fixes per the blog; self-selected by developers who know the cause). Reviewers will raise this; the Rosa 2021 and Lyu 2024 papers are the cites showing the device is accepted.

## Claim by claim

**Claim 1 (42-71% in a changed function).** PARTLY. File-level 73.2% and statement-level 64.6% are published (Wen 2019, Java, 333 bugs). Function-level on Fixes-tag data: Lyu 2024 reports the related quantity for Linux (34.6% function history, 27.5% file-only). Not found: function-level share of fixes landing in functions changed by the cause, across projects (curl, OpenSSL, FreeBSD). Closest: Wen 2019 and Lyu 2024. Weakness of novelty: low. Do not present claim 1 as new.

**Claim 2 (1-2 edges, ~2x same-file baseline).** PARTLY. That follow-up changes sit structurally near earlier ones is shown (Park 2012/2017: about two-thirds dependent; Wen 2019: 50% of cross-file cases directly dependent; Gu 2021: bugs correlate along call ties; Kim 2007: spatial locality). Not found: a hop-distance measure on call graphs, a matched same-file same-size baseline, a ratio with a confidence interval, subsystem stratification, or a Linux scale of 14,444 pairs. This quantified radius appears open. Caveat: Gu 2021 full text unread; the strongest threat.

**Claim 3 (callees same file, callers different file).** NOT FOUND. Only an adjacent observation (Ye 2018: callers co-changed with a shared callee; all edits, not cause-fix). Also note Wen 2019 finds cross-file fixes are in files that use (depend on) the buggy class, which is consistent with "callers" for different-file pairs; that supports half of claim 3 qualitatively. Treat as consistent with literature, not duplicated.

**Claim 4 (diff shape, locking 2.5x, size).** PARTLY for shape: Wen 2019 shows change-action correlation (43.1% / 52.6%). Not found: locking-adds-locking at 2.5x chance, or large causes giving slower and more dispersed fixes. Related but different: Śliwerski 2005 and Purushothaman 2005 (size and being fix-inducing). Lu et al. ASPLOS 2008 (concurrency bug fix strategies) is a plausible related paper that I did NOT locate or check.

**Claim 5 (median about 8 months; mild fade).** Lag distributions are well known in kind (Chou 2001: about 1.8 years; Palix 2014: 2.5-3.0 years; Pebblebed blog 2.1 years mean). Median figure from Fixes tags with a peer-reviewed source: not found. Dependence of call-graph proximity on lag: NOT FOUND (Gu 2021 does lagged correlations, but I could not verify whether it reports decay).

## What to cite

- For "fixes usually touch the same file or statements as the cause": Wen et al. 2019 (FSE). Lyu et al. 2024 (TSE) for Linux and Fixes tags.
- For "follow-up fixes lie in structurally dependent code": Park, Kim, Bae 2017 (EMSE), Park et al. 2012 (MSR).
- For "bugs correlate along call/dependency edges": Gu et al. 2021 (ECOOP), Zimmermann and Nagappan 2008, Kim et al. 2007.
- For "Fixes trailers are an accepted ground truth": Rosa et al. 2021, Lyu et al. 2024.

## Risks to the novelty claim

1. Wen 2019 and Park 2017 already present "different-file fixes are in dependent files". A reviewer will say claim 2 is a quantified restatement. Defence: hop distance, matched baseline, scale.
2. Gu 2021 may already contain function-level call-graph lagged effects. Read it.
3. Selection: Fixes-tagged fixes are a self-selected subset. Wen used developer-identified causes, which is also selected.
4. The same-file baseline is only one choice; a reviewer may ask for a random-pair or same-directory baseline, and for a control for call-graph density (nearby functions in the same file are close in the graph anyway).

## Plain-language summary

1. Partly known: that most fixes land in the same file or lines as the cause, and that follow-up fixes sit near it in the dependency graph, is already published.
2. Open (as far as I could find): the function-level, hop-distance measure against a same-file baseline, at 14,444 kernel pairs, with the roughly 2x ratio.
3. Open: caller versus callee direction, locking begets locking, and large causes giving slower fixes; only loose analogues exist.
4. Cite Wen et al. FSE 2019, Park et al. EMSE 2017, Lyu et al. TSE 2024, Gu et al. ECOOP 2021 (after reading it fully), and Rosa et al. ICSE 2021 for the Fixes-trailer method.
5. I did not read Gu 2021, Park 2017 or Lyu 2024 in full and did not check forward citations, so treat "open" as "not found", not "proven absent".
