# How MSR research produces high-quality bug-fix labels — review, 2026-11-13

Everything below was read from a primary source (arXiv/ar5iv full text, author-hosted PDF, extracted PDF text, or publisher abstract page) unless marked "abstract-level". Numbers from tuning sets, single projects, balanced-by-construction test sets or positives-only corpora are flagged inline — there are a lot of them, and they are the main reason this literature reads better than it performs.

**The one-paragraph answer to your situation.** Your measured keyword recall (~0.41 curl, ~0.26 commons-lang) is not anomalous — it is the published value. On 34 manually validated SmartSHARK projects a stemmed-keyword matcher scores **recall 0.394, precision 0.436** (König et al. 2026). For security fixes specifically, **only 38% of real vulnerability-fix commit messages contain any security word** (VulFixMiner, measured over 1,982 fix commits). So your instinct is right and the cascade is the right shape — but the literature says two things you should absorb before building it: (a) the *issue-reference* tier you are about to trust inherits a severe, measured, non-random bias (Bird et al. 2009), and (b) nobody in this field has shown that recovering more links removes that bias rather than amplifying it.

---

## 1. SZZ and its variants: what each fixes, measured error rates, critiques

### 1.1 The variant chain

| Variant | Base | What it changed |
|---|---|---|
| **B-SZZ** — Śliwerski, Zimmermann, Zeller, MSR 2005 | — | Original. `blame` the lines deleted by the fix. |
| **AG-SZZ** — Kim et al., ASE 2006 | B-SZZ | Annotation graph; ignores cosmetic changes (comments, whitespace, formatting). |
| **DJ-SZZ** — Williams & Spacco, 2008 | AG-SZZ | Line-number mapping + DiffJ (Java syntax-aware) to exclude non-executable changes. |
| **L-SZZ / R-SZZ** — Davies et al., 2014 | AG-SZZ | Pick *one* candidate BIC: the largest (L) or the latest (R). |
| **MA-SZZ** — da Costa et al., TSE 2017 | AG-SZZ | Excludes meta-changes (branch, merge, property changes). |
| **RA-SZZ** — Neto et al., 2018 | MA-SZZ | Excludes refactorings via RefDiff; **RA-SZZ\*** uses RefactoringMiner. Java only. |
| **SZZ@PYD** (PyDriller) / **SZZ@UNL** (SZZ Unleashed) / **SZZ@OPN** (OpenSZZ) | tools | Wrappers around B-SZZ/DJ-SZZ/B-SZZ logic respectively. |
| **HDU / HR** — Rosa et al., JSS 2023 | any | HDU: def-use chains to handle *added* lines (blame only sees deleted ones). HR: filter revert commits. |

### 1.2 The developer-informed oracle — the best numbers available

**Rosa, Pascarella, Scalabrino, Tufano, Bavota, Lanza, Oliveto. "Evaluating SZZ Implementations Through a Developer-informed Oracle." ICSE 2021, 436–447. DOI 10.1109/ICSE43902.2021.00049. arXiv:2102.03300.** Extended as **"A Comprehensive Evaluation of SZZ Variants Through a Developer-Informed Oracle," JSS 2023** (PDF: sscalabrino.github.io/files/2023/JSS2023AComprehensiveEvaluation.pdf).

Oracle construction: ~19.6M commits from GH Archive (Mar 2011 – Apr 2020) → spaCy dependency-tree filtering for commits where the developer *names the inducing commit hash* → 3,585 candidates → two of four author-evaluators per commit (7,170 evaluations, any "irrelevant" flag excludes, conflicts unresolved) → 1,930 commits (55.6% pass rate) → 1,115 after restricting to 8 languages. JSS 2023 extends to 4,585 validated → **2,304 instances** (+22%).

ICSE 2021, `oracle_all` (N=1,115), **Recall / Precision / F1**, without → with issue-date filter:

| Variant | R | P (no filter) | F1 | P (date filter) | F1 |
|---|---|---|---|---|---|
| B-SZZ | 0.69 | 0.39 | 0.50 | 0.42 | 0.53 |
| AG-SZZ | 0.60 | 0.45 | 0.52 | 0.49 | 0.54 |
| L-SZZ | 0.45 | 0.52 | 0.48 | 0.54 | 0.49 |
| **R-SZZ** | 0.57 | **0.66** | **0.61** | **0.73** | **0.64** |
| MA-SZZ | 0.64 | 0.36 | 0.46 | 0.39 | 0.48 |
| RA-SZZ\* (Java, N=80) | 0.45 | 0.35 | 0.39 | 0.43 | 0.44 |
| SZZ@PYD | 0.67 | 0.39 | 0.49 | 0.42 | 0.52 |
| SZZ@UNL | **0.72** | 0.09 | 0.16 | 0.09 | 0.16 |
| SZZ@OPN (Java, N=80) | 0.19 | 0.32 | 0.24 | 0.33 | 0.24 |

JSS 2023 on the larger oracle is essentially identical (R-SZZ 0.62R/0.73P/0.67F1 with date filter). **R-SZZ is the only variant above 0.6 F1; nothing exceeds 0.73 precision or 0.72 recall, and no variant achieves both.**

Caveats the authors state: Java-only tools were scored on 80 commits (10 with issues) — ignore RA-SZZ\* and SZZ@OPN numbers. 88% of oracle instances have no issue link, so the date filter is off by default. Most variants are the authors' re-implementations. SZZ@UNL's 0.09 precision is driven by a few outliers (excluding them gives 18–24%). Only SZZ@UNL found inducing commits no other variant found — overlap is otherwise high, meaning **many fixes defeat every variant simultaneously**.

**JSS 2023's new heuristics, and why they matter to your revert tier.** HR detects reverts by exactly the signals you have harvested: the sequence `This reverts commit` in the body, or a subject starting `Revert`. Effect (oracle_all, with date filter): R-SZZ 0.62/0.73/0.67 → R-SZZ@REV 0.63/0.74/0.68; MA-SZZ 0.63/0.39/0.48 → 0.64/0.39/0.49. **~1 point.** The authors' own conclusion is the honest one: *"HR can be safely used on top of any SZZ variant, and we found no drawbacks"* — but the gain depends entirely on how many reverts are present. HDU (def-use on added lines) is bigger: R-SZZ@DU 0.55/0.64/0.59 vs R-SZZ@A 0.51/0.54/0.53 on oracle_C (N=397, C only).

### 1.3 Independent evaluations

- **Lyu, Kang, Widyasari, Lawall, Lo. "Evaluating SZZ Implementations: An Empirical Study on the Linux Kernel." IEEE TSE 2023/24. arXiv:2308.05060.** Ground truth = **76,046 fix↔inducing pairs from Linux `Fixes:` tags** at v6.1-rc5 — developer-authored and, as the authors put it, created "entirely independently of the biases of software engineering researchers." This is by far the largest developer-produced link set in existence. Results: AG-SZZ 0.42P/0.56R, MA-SZZ 0.40/0.55, R-SZZ 0.59/0.45. **SZZ recall declines more on this dataset than prior work reported** — i.e. the oracle-based numbers above are optimistic.
- **Rodríguez-Pérez, Robles, Serebrenik, Zaidman, German, González-Barahona. "How bugs are born: a model to identify how bugs are introduced in software components." EMSE 25(2):1294–1340, 2020. DOI 10.1007/s10664-019-09781-y.** 116 manually analysed bugs, 2 projects, 4 SZZ variants: **F 0.44–0.77, true positives never above 63%.** Introduces intrinsic vs extrinsic bugs — **many bugs have no inducing commit at all**, which is a hard ceiling SZZ cannot pass.
- **da Costa, McIntosh, Shang, Kulesza, Coelho, Hassan. "A Framework for Evaluating the Results of the SZZ Approach." IEEE TSE 43(7):641–657, 2017. DOI 10.1109/TSE.2016.2616306.** Not precision/recall — three *sanity* criteria (earliest bug appearance, future impact, realism). On 5 implementations / 10 projects: under the best implementation, **29% of bug-introducing changes are blamed for multiple future bugs spanning ≥1 year**, and a single change can be blamed for hundreds of future bugs. This is the structural critique: SZZ output is not just noisy, it is pathologically concentrated.
- **Herbold, Trautsch, Trautsch, Ledel. "Problems with SZZ and features." EMSE 27:42, 2022. DOI 10.1007/s10664-021-10092-4. arXiv:1911.08938.** *Note: "Issues with SZZ" is the same paper, renamed before publication — do not cite as two.* 398 releases, 38 Apache projects, ~140k commits. **Only about half the bug-fixing commits SZZ identifies are actually bug fixes; SZZ misses about one fifth of real bug-fixing commits; about one quarter of its links are wrong. Median TPR 86.9% (MAD 18.2%), median FPR 81.1% (MAD 40.0%).** With a 6-month window, one file is incorrectly labelled defective for every correctly labelled one, and two defective files are missed. Their conclusion: label noise is a severe validity threat; feature-set size is not.

### 1.4 Recent and LLM-era SZZ

- **LLM4SZZ, arXiv:2504.01404** — context-enhanced LLM assessment of BIC candidates; F1 +6.9%–16.0% over SZZ variants without significant recall loss.
- **AgentSZZ, arXiv:2604.02665** — agentic; notes a frontier model costs ~$400 per evaluation run, which is why it wasn't run at scale.
- **WIA-SZZ, arXiv:2411.12740** — groups related commits into "work items"; compared on 821 repositories.
- **"SZZ in the Time of Pull Requests," Petrulio, Bacchelli et al., arXiv:2209.03311 (2022)** — SZZ assumes a fix is one commit; PR-based development breaks that. Mozilla ground truth; adds ML to classify commits as useful/not for linking. Relevant to curl/commons-lang, both PR-mediated.

**Tool to actually use: `pyszz` — https://github.com/grosa1/pyszz** (Rosa et al.'s implementation of all variants + HDU + HR in one place). Also SZZ Unleashed (github.com/wogscpar/SZZUnleashed), OpenSZZ (github.com/clowee/OpenSZZ — but P 0.32/R 0.19, avoid), PyDriller (github.com/ishepard/pydriller). ICSE 2021 replication: github.com/grosa1/icse2021-szz-replication-package.

**Would it work on your data?** Yes, pyszz runs on bare git history. But SZZ is downstream of your problem: it consumes fix labels and produces inducing labels. Herbold's finding — fix-label precision propagates directly into inducing-label quality — means your cascade is the right place to spend effort, and SZZ should be operated at a *high-precision* point on your cascade output (revert/CVE/trailer tiers), not on the keyword tier.

---

## 2. Issue-link recovery when commits don't reference issues

### 2.1 How bad is the gap, actually

From Bird et al. 2009 Table 1 (fixed bugs → linked):

| Project | Fixed | Linked | Rate |
|---|---|---|---|
| Eclipse (Zimmermann) | 24,119 | 10,017 | 41.5% |
| Eclipse (Bird's mining) | 113,877 | 34,914 | 30.7% |
| Apache httpd | 1,383 | 686 | 49.6% |
| Netbeans | 68,299 | 37,498 | 54.9% |
| **OpenOffice** | 33,924 | 2,754 | **8.1%** |
| Gnome | 117,021 | 45,527 | 38.9% |
| AspectJ | 1,121 | 343 | 30.6% |

- **Ruan, Chen, Peng, Zhao (JSS 2019)**: over 1,078 GitHub Java projects, **only 42.2% of issues are linked to commits**.
- **Rath, Rendall, Guo, Cleland-Huang, Mäder. "Traceability in the Wild." ICSE 2018. DOI 10.1145/3180155.3180207. arXiv:1804.02433.** Six Apache Git+Jira projects: ~48% of commits carry no issue link; per-project 15% unlinked (Derby) to 76% (Maven). *The paper is internally inconsistent — abstract says ~60% linked, Table 2 implies ~52%.*
- **Timing**: 7 days captures only **59%** of true links; 30 days 77%; 6 months 92%; **1 year 97%** (EasyLink, 20 projects). Every pre-2023 tool used a 7-day candidate window. That alone caps their achievable recall at ~0.59.
- **GitHub closing-keyword semantics** (docs.github.com): `close/closes/closed`, `fix/fixes/fixed`, `resolve/resolves/resolved`, case-insensitive. Auto-close fires **only when the PR targets the default branch**; a keyword in a PR to another branch creates no link. A keyword in a *commit message* closes the issue on merge to default, but GitHub then does **not** list the containing PR as linked. Manual sidebar linking caps at 10 issues. Practical consequence for you: `Fixes #N` in a squashed-away feature-branch commit produces no API-visible link, and GraphQL `closedByPullRequestsReferences` / timeline gives you *curated* links your regex misses, and vice versa. Worth harvesting both.

### 2.2 The tools

**ReLink** — Wu, Zhang, Kim, Cheung. ESEC/FSE 2011, 15–25. DOI 10.1145/2025113.2025120. Learns thresholds from a project's *explicit* links for three criteria: bug-resolution↔commit time interval, owner/committer identity match, bug-text↔changelog similarity. **Needs the bug tracker's full report text, resolution timestamps, and assignee — not runnable from git alone.** Reported **P 0.89 / R 0.78** averaged over 3 projects (ZXing 143 links, OpenIntents 129, Apache 1,090). ⚠️ Three projects, two tiny; thresholds learned from the same biased link sample Bird warned about. Code: cse.hkust.edu.hk/~scc/ReLink.htm (Java, 2011, "scientific use only", Google Code mirror dead).

**Bissyandé, Thung, Wang, Lo, Jiang, Réveillère. "Empirical Evaluation of Bug Linking." CSMR 2013, 89–98. DOI 10.1109/CSMR.2013.19.** ~12,000 links / 10 programs — the first independent evaluation. Finding: ReLink is accurate when it fires but **misses many links that should exist**. ⚠️ I could not retrieve the per-project table (IEEE/CORE/HAL all 403). Indirect corroboration: EasyLink (2026) re-ran ReLink under a realistic candidate pool and measured **P 0.109 / R 0.126 / F1 0.108** — an order of magnitude below the published 0.89/0.78. Different (harsher) setting, not an apples-to-apples refutation, but the direction Bissyandé pointed.

**MLink** — Nguyen, Nguyen, Nguyen, Nguyen. FSE 2012, 63:1–11. DOI 10.1145/2393596.2393671. Five cascaded layers over pattern matching: patch-hunk similarity, program-entity name overlap, TF-IDF text, learned term↔entity association. Needs bug text **+ comments + the changed source itself**. Same 3 projects: ZXing P96/R88/F93, OpenIntents P97/R85/F91, Apache P82/R90/F87. ⚠️ **Four thresholds hill-climbed on 2/3 of the pattern-detected links and then used to produce the headline numbers** — a tuning-set leak. No public code.

**RCLinker** — Le, Linares-Vásquez, Lo, Poshyvanyk. ICPC 2015, 36–47. DOI 10.1109/ICPC.2015.13. Key idea: repair the *input*, not the model — run ChangeScribe (ICSE 2015 tool demo; github.com/SEMERU-WM/ChangeScribe, Eclipse/Java only) to synthesize a rich NL description of the diff, so text similarity works when the message is empty. 385 bug reports, 3,249 commits, 6 projects. Headline is **"+138.66% F over MLink"** — a relative number over a presumably low base, which is a flag. **But**: the 2026 re-evaluation below finds RCLinker, a 2015 feature-based reranker, **matches or beats GPT-5.1**. Worth a second look.

**FRLink** — Sun, Wang, Yang. IST 84:33–47, 2017. DOI 10.1016/j.infsof.2016.11.010. Contribution: **non-source files** (config, docs, test resources) carry link evidence, and irrelevant source files are noise to prune. Headline: **+40.75% F over RCLinker at highest recall** — again relative. Independent re-measurements paint a consistent picture of a high-recall/low-precision recommender: Hybrid-Linker's eval gives FRLink **R 96.86 / P 53.61 / F 67.67**; BTLink's gives within-project F 55.89, cross-project F 49.32. No official code.

**DeepLink ×2 — a name collision, cite carefully.** (a) Xie et al., SANER 2019, 434–444, DOI 10.1109/SANER.2019.8667969 — code knowledge graph, no numbers surfaced, never replicated. (b) Ruan, Chen, Peng, Zhao, JSS 158:110406, 2019, DOI 10.1016/j.jss.2019.110406 — RNN; **+4.6% F** over prior; code at github.com/ruanhang1993/DeepLink. ⚠️ Every independent re-evaluation puts it far below reputation: Hybrid-Linker's eval F 62.87; BTLink's within-project F 38.50, cross-project F 13.92; LinkAnchor's Hit@1 **0.106**, worst of all baselines. Do not plan around it.

**Hybrid-Linker** — Rostami Mazrae, Izadi, Heydarnoori. ICSME 2021. arXiv:2107.01894. Blends a non-textual classifier (commit/author times, author+committer hashes, issue dates/type/status) with a TF-IDF textual one, α tuned per project. 12 Apache projects: **R 90.14 / P 87.78 / F 88.88**. ⚠️⚠️ **Negatives generated by a 7-day rule then down-sampled to balanced 1:1, α tuned per project.** Under a realistic candidate pool it collapses to **P@1 0.087–0.201** (Think Harder, 2026). This is the clearest documented case in the area of a balanced-dataset number not surviving contact with reality. Code: github.com/MalihehIzadi/hybrid-linker.

**LinkFormer + the data-leakage study** — Izadi, Rostami Mazrae, Mens, van Deursen. EMSE 2023; arXiv:2211.00381. RoBERTa pair classifier. Its real contribution is methodological: **random split inflates results massively.** 20 projects, >233k pairs, balanced 1:1. Random split: LinkFormer **F 0.97**, DeepLink 0.62, Hybrid-Linker 0.84, T-BERT 0.86. **Temporal split: LinkFormer F 0.90**, DeepLink 0.54, Hybrid-Linker 0.67, **T-BERT 0.61**. Cross-project: F 0.88. **Random splits inflate transformer linkers by up to 25 points.** Code: github.com/MalihehIzadi/linkformer; data DOI 10.5281/zenodo.6524460.

**BTLink** — Lan, Gong, Zhang, Zhang. EMSE 28(4), 2023. DOI 10.1007/s10664-023-10342-7. arXiv:2207.01084. RoBERTa over (issue text, commit text) + CodeBERT over (issue text, commit code), fused. Within-project **F 80.03 / R 84.34 / P 78.81**; cross-project F 62.19. ⚠️ The README doesn't state projects or negative-sampling procedure. Code: github.com/OpenSELab/BTLink.

**EALink** — Zhang et al., ASE 2023, arXiv:2308.10759. Knowledge distillation + contrastive learning. Headline "15.23%–408.65% over SOTA" with no absolute number. Independently: **P@1 53.67 / MRR 60.13 in its own setting (99 false links per issue), collapsing to P@1 14.43 / MRR 20.21 under a realistic candidate distribution.** 100.68 h training, 6.87 s/issue inference. Code: github.com/KDEGroup/EALink — the de facto baseline.

**EasyLink** — Huang, Widyasari, Zhang, Irsan, Shi, Ang, Liauw, Ouh, Shar, Kang, Lo. **"Back to the Basics: Rethinking Issue-Commit Linking with LLM-Assisted Retrieval." ICSE 2026.** arXiv:2507.09199. Deliberately simple, **no task-specific training**: embed issue summary+description and commit messages with all-MiniLM-L6-v2, FAISS cosine rank, rerank top-10 with GPT-4o zero-shot. **Inputs are light — issue summary+description; commit id, timestamp, message only. No diff, no tracker metadata, no identity resolution.** Realistic-distribution setting: 20 projects, 9,319 issues, candidates = *all* non-fix commits from issue creation to +1 year (~1,530 false links/issue). Results: **P@1 75.03, MRR 78.52, Hit@10 83.38, Recall@10 78.84**; vector-DB-only P@1 61.57; VSM 46.59; EALink 14.43; ReLink P 10.92/R 12.59/F1 10.79. Cost ~$0.009/issue, 5.42 s/issue; retrieval-only 0.87 s/issue at zero API cost. Data: figshare.com/s/d495f11c4cc5c1c72e68.

**LinkAnchor** — Akhavan, Hoseinpour, Heydarnoori, Bagheri, Keshani. FSE 2026. arXiv:2508.12232. An *agent*: GPT-4o-mini given the issue URL + repo, pulling context on demand (issue title/description/**comments**, commit history, codebase), ≤20 iterations / 200k tokens. Six Apache/Jira projects, >56k issues: **Hit@1 0.8632** vs EasyLink 0.6118, EALink 0.5390, T-BERT 0.4202, DeepLink 0.1060. GitHub check on 120 post-cutoff issues: Hit@1 0.89. ~23.6 s, ~$0.01/issue. **Ablation worth noting: dropping issue comments costs 17% accuracy; dropping codebase access only 4%.** ⚠️ Non-deterministic (averaged over 3 runs); 78% of sampled failures are LLM hallucination.

**"Think Harder and Don't Overlook Your Options"** — Morgan, Asaduzzaman, Chowdhury, Wang. arXiv:2605.00447v2 (2026). Decomposes into retrieve-then-rerank. **Reciprocal Rank Fusion of BM25 + SBERT maximises candidate recall (R@50 0.937).** And the headline you should care about: **RCLinker (2015, feature-based) matches or beats GPT-5.1 on all three datasets** — BTLink data 0.936 vs 0.920; Apache data 0.949 vs 0.953; EasyLink data 0.842 vs 0.822. Hybrid-Linker collapses to 0.087–0.201. New largest benchmark: 10 Apache projects, 208,858 true links, 2006–2025. Replication: figshare.com/s/3b9673176afe92929398. Caveat: ranking metrics only, no F1, so it doesn't tell you where to threshold for *automatic* linking.

### 2.3 What this means for you

- **Nothing in this literature works from git alone.** The minimum viable issue-side input is title + description text. You have GitHub API access, so you have that.
- **For your constraint (GitHub API, no guaranteed tracker labels), EasyLink is the fit** — it needs only issue summary/description and commit id/time/message. Its **retrieval-only variant (FAISS + MiniLM, P@1 61.6, 0.87 s/issue, zero API cost)** is the cheapest defensible thing available and is where I'd start. "Think Harder" improves the candidate stage (BM25+SBERT RRF) using identical inputs.
- **Five operational cautions**: (1) use temporal splits — random splits inflate by up to 25 points; (2) strip issue keys from commit messages before evaluating, or you measure your regex; (3) use a 1-year candidate window, not 7 days (59% → 97% capture); (4) don't use issue *close* date as a feature — unavailable at prediction time; (5) **~17% of issues are fixed by multiple commits**, so pairwise classification and P@1 both mis-frame the task for a sixth of your data.
- **The one that should worry you**: recovered links inherit the bias (§3). No tool in this literature has demonstrated bias *reduction*.

---

## 3. The bias literature — the part that matters most to you

### 3.1 Bird et al. 2009 — the governing result

**Bird, Bachmann, Aune, Duffy, Bernstein, Filkov, Devanbu. "Fair and Balanced? Bias in Bug-Fix Datasets." ESEC/FSE 2009, 121–130. DOI 10.1145/1595696.1595716.** PDF: cs.ucdavis.edu/~filkov/papers/biasbusters.pdf

Two definitions, and the distinction is load-bearing for you:
- **Bug feature bias**: p(bug features | B_fl) ≠ p(bug features | B_f) — linked bugs are not a representative sample of fixed bugs along bug-report attributes. **Observable.**
- **Commit feature bias**: the analogous statement over commit attributes. **Observation 3.3: given only a set of linked commits, there is no way to know whether commit feature bias exists.** You cannot measure it from inside your own data. This is a hard epistemic limit on your cascade's precision audit.

Their link-extraction quality (so you can calibrate against your own): manual inspection of 1,500 random *unlinked* messages found 6 true links → **false-negative rate CI 0.14%–0.78%**; 30,000 *linked* messages found 6 incorrect → **false-positive upper bound 0.05%**. That is for explicit ID references only.

Measured biases:
- **Severity.** In Apache, **63% of fixed *minor* bugs are linked but only 15% of fixed *blocker* bugs.** χ² = 94 for Apache; p ≪ .01 for Eclipse, Apache, Gnome. Direction is the *opposite* of their prior expectation. In every project with severity data except AspectJ, linkage trends upward with *decreasing* severity. **Linked data is biased toward less severe bugs.**
- **Developer experience.** One-sided KS test: linked bugs are closed by significantly more experienced developers in every dataset except AspectJ. Eclipse median prior fixes 457 (linked) vs 188 (all).
- **Verification.** A bug is **66% more likely to be verified if it is linked** (binomial point estimate 0.291, CI .289–.293). Confirmed for Eclipse_Z, Eclipse_B, Netbeans, OpenOffice; *not* for Apache or AspectJ; **reversed in Gnome**. So it is project-specific, not universal.
- **Not confirmed**: bugs closed later in project life, bugs near release dates, bugs with more people/events.
- **The AspectJ anomaly**, which is the most useful single observation for you: iBugs AspectJ showed **no bias on any dimension**. Cause: **81% of fixed bugs were closed by just 3 people**, 71% of linked bugs attributable to the same group, and **20–30% of each person's fixed bugs were linked** — uniformly. **Bias is a property of heterogeneous linking behaviour across developers, not of low link rates per se.** A project can have a 30% link rate and be unbiased if everyone links at the same rate. Your per-repo precision spread (0.27–0.86) is very likely the same phenomenon: per-developer, per-era writing conventions.

Downstream effect, demonstrated: they trained BugCache (Kim et al.) on super-biased training sets drawn from single severity classes and on severity-exaggerated sets. **BugCache performs best when trained on a set whose bug-feature bias matches the test set**; recall tracks the training bias. The honest caveat they state: *"we do not have an unbiased oracle to truly evaluate BugCache performance"* — so BugCache might be partly overcoming the bias and they cannot tell.

### 3.2 Successors

- **Nguyen, Adams, Hassan. "A Case Study of Bias in Bug-Fix Datasets." WCRE 2010.** *(Note: not "Nguyen, Bird, Bertrand" — Queen's University authors.)* Tested a near-ideal IBM Jazz dataset where linking is enforced by process. **Bias still exists.** Their conclusion: *linkage bias is not a symptom of imperfect linkage but more likely a property of the software process*. Secondary finding, narrower: tagging bias did not significantly affect bug-prediction models in their setting. **This is the most important caveat on §2 for you: better link recovery will not eliminate the bias, because the bias is upstream of the linking.**
- **Herzig, Just, Zeller. "It's Not a Bug, It's a Feature: How Misclassification Impacts Bug Prediction." ICSE 2013, 392–401.** >7,000 issue reports manually examined across 5 projects: **33.8% misclassified** — they resulted in a feature, a doc update, or a refactoring rather than a code fix. Consequence: **39% of files marked defective never had a bug.** Directly applicable to your *issue-reference tier*: a commit that correctly references an issue typed "Bug" is still only ~2/3 likely to be a bug fix. **Your issue-reference tier's precision ceiling is set by issue-tracker label quality, not by your linking.**
- **Rahman, Posnett, Herraiz, Devanbu. "Sample size vs. bias in defect prediction." ESEC/FSE 2013, 147–157.** *(Herzig is not an author.)* The counterweight: with enough data, sample size can dominate bias effects. Worth reading before over-engineering de-biasing.
- **Kochhar, Tian, Lo. "Potential Biases in Bug Localization: Do They Matter?" ASE 2014, 803–814.** Three biases on HTTPClient/Jackrabbit/Lucene-Java: misclassified reports, already-localized reports, incorrect ground-truth files. **Only one (already-localized reports) had a statistically significant and substantial impact**; the other two were negligible-to-minor. 3 Java projects only.
- **Bachmann, Bird, Rahman, Devanbu, Bernstein. "The Missing Links: Bugs and Bug-Fix Commits." FSE 2010, 97–106. DOI 10.1145/1882291.1882308.** The only true manual gold standard: the **Linkster** tool let an Apache httpd *core developer* exhaustively annotate **all ~500 commits in a six-week window**. Conclusion: "serious and consequential problems in the linked defect data." ⚠️ 500 commits, one project, one annotator — tiny, and everything calibrated on it should be treated accordingly.

### 3.3 The implication for your cascade design

Each tier of your cascade selects a *different* subpopulation, and you should expect each tier's bias profile to differ:
- **Revert tier**: selects for regressions caught fast, by people who use `git revert` rather than a forward fix. Near-certain precision, severely non-random.
- **CVE tier**: selects for security-relevant, externally reported, high-visibility fixes. Also near-certain, also severely non-random.
- **Issue-reference tier**: Bird's exact population — **biased toward less severe bugs and more experienced developers**, with precision capped by Herzig's 33.8% issue mistyping.
- **Trailer tier** (`Reported-by`, `Closes`, `Fixes:`): the Linux `Fixes:` tag is the single best developer-produced signal in this entire literature (76,046 pairs — Lyu et al.). Where your repos use kernel-style trailers, this tier should be your highest-quality non-revert evidence.
- **Keyword tier**: biased by *writing style*, which is what you already found.

**Concrete recommendation**: your cascade should carry, per tier, not only measured precision but a **recorded bias profile** — at minimum, per-tier distributions of author, year, and (where available) issue severity/type, compared against the full commit population. That turns a known-unmeasurable problem (commit feature bias) into a partly measurable one, and it is a contribution in its own right since nobody in §2 has done it.

---

## 4. Commit classification beyond keywords

### 4.1 The maintenance-taxonomy line

- **Swanson, ICSE 1976** — corrective/adaptive/perfective. The label space everyone inherits.
- **Hindle, German, Holt. "What do large commits tell us?" MSR 2008, 99–102.** Fully manual, 2000 large commits, 9 projects. Key finding for your sampling: **large commits skew perfective, small commits skew corrective** — the base rate of "is this a bug fix?" is a function of commit size.
- **Hindle, German, Godfrey, Holt. "Automatic classification of large changes into maintenance categories." ICPC 2009, 30–39. DOI 10.1109/ICPC.2009.5090025.** Classical ML over **commit metadata only** — message word distribution, **commit author identity**, modules touched. 10-fold CV accuracy "consistently above 50%" on 5 classes. Headline qualitative result: **author identity carries nearly as much signal as the message words** — a within-project shortcut that cannot transfer. Later work tabulates it as **~70% single-project / ~52% cross-project**. *(abstract-level; IEEE paywalled)*
- **Mauczka et al. FASE 2012, LNCS 7212:301–315. DOI 10.1007/978-3-642-28872-2_21** — hand-built keyword dictionary mapped to Swanson, cross-project validated. The sophisticated end of keyword matching; your cleaning rule is in this family.
- **Mauczka, Brosch, Schanes, Grechenig. "Dataset of Developer-Labeled Commit Messages." MSR 2015 data track, 490–493. DOI 10.1109/MSR.2015.71.** **967 changes labelled by their own original authors** — 7 developers, 6 projects, 3 schemes. **The only ground truth in this entire literature where the labeller wrote the commit.** Everything else is third-party inference from message + diff. Small, but uniquely clean.

### 4.2 Levin & Yehudai, and its lineage

**Levin, Yehudai. "Boosting Automatic Commit Classification Into Maintenance Activities By Utilizing Source Code Changes." PROMISE 2017, 97–106. DOI 10.1145/3127005.3127016. arXiv:1711.05340.**

Compound model: if the message contains one of 20 stemmed keywords use a keyword-only model, else use keywords + **Fluri's 48-type fine-grained AST change taxonomy** extracted with ChangeDistiller (Java only). 68 features; J48/GBM/RF.

Data: **1,151 manually labelled commits, 11 Java projects**, 33,149 source-code changes. **Naturally imbalanced: corrective 500 (43.4%), perfective 404 (35%), adaptive 247 (21.4%)** — good, not balanced by construction. 85/15 split, **test set = 172 commits**.

**Accuracy 76%, Cohen's κ 0.63** vs no-information rate 43%. Per class on the test set: **corrective P 0.75 / R 0.84**; adaptive 0.73/0.75; perfective 0.80/0.68. Baselines in the same paper: **naive keyword-only 56% acc / κ 0.29**; word-frequency compound 68–69% / κ 0.51–0.53. **So AST change features buy ~+20 pp over keywords** — that is the paper's real claim and it is fair.

⚠️ Test set is **172 commits** (±0.6 pp per commit). "Cross-project" here means *multi-project pooled*, **not leave-one-project-out**. Java-only. Labels are the authors', not the developers'. **Dataset public: Zenodo DOI 10.5281/zenodo.835534.**

Follow-ups on the same benchmark:
- **Mariano, dos Santos, Brandão. ICEIS 2021, 19–29. DOI 10.5220/0010401700190029.** +3 size features + XGBoost → **>77% acc, κ >0.64**. A +1 pp gain on a 172-commit test set is noise.
- **Ghadhab, Jenhani, Mkaouer, Ben Messaoud. Information and Software Technology 135:106566, 2021. DOI 10.1016/j.infsof.2021.106566.** BERT embeddings + fine-grained code changes + DNN. **79.66% accuracy, macro-F1 0.80** on a **balanced dataset of 1,793 commits**. ⚠️⚠️ **Balanced by construction while Levin & Yehudai's is 43/35/21** — the "+8 pp over SOTA" is not apples-to-apples (no-information rate moves 43%→33%). Discount it. Replication: zenodo.org/record/4266643.
- **Sazid, Kuri, Ahmed, Satter. ENASE/ICSOFT 2024, SciTePress 126867.** GPT-3 in-context learning: **75.7% acc, κ 61.7%** — **statistically indistinguishable from the 2017 supervised RF, with zero training data.** That equivalence, not any improvement, is the finding worth carrying.

### 4.3 Conventional Commits as ground truth

- **Zeng et al. "A First Look at Conventional Commits Classification." ICSE 2025.** Defines the 10-category standard; first study of CCS-based classification.
- **Wan, Wu, Hou, Zhao, Xia, Wang. "CommitSuite." EASE 2026. arXiv:2605.02256. Code: github.com/security-pride/CommitSuite.** 63,533 strictly CCS-compliant commits, 243 repos, **manually verified 10-category labels**, test set 1,160. Cross-project ten-category results: Zeng et al.'s classifier P 0.580/R 0.473/F1 0.457; **DeepSeek-R1 best at P 0.675/R 0.638/F1 0.621**; Claude-3.7-sonnet 0.668/0.609/0.606; GPT-4.1 0.641/0.608/0.585. **Directly relevant: `fix` is frequently misclassified as `refactor`, `perf` and `style`.** Even the best LLM is at ~0.64 on ten classes.
- **Kocak, FAU thesis 2026** — prefix-as-label, raw diff input: **71.3% accuracy but macro-F1 only 0.36** on 12 classes. The gap is the story: accuracy rides on `feat`/`fix` frequency while rare classes collapse. Honest about the core threat: **CCS conventions are applied inconsistently across projects and developers, so the "ground truth" is itself noisy.**
- **Quadir, Al Hasan, Tawhid. arXiv:2605.02033 (2026).** ⚠️ **3,200 commits from a single repository (InfluxDB), balanced by construction, no external baseline** — both red flags at once; the authors themselves disclaim comparison. Best = Mistral-7B few-shot acc 0.6154 (P 0.382 / R 0.615). Useful only as evidence that diff-only prompting without examples is weak.
- **CCSBench** (HF `CSU-OSS/CCSBench`): 93,807 CCS commits, 119 repos, Apache-2.0.
- **CommitBERT** (Jung, NLP4Prog@ACL 2021, arXiv:2105.14242) — 345K commit/diff pairs, 6 languages, weights public. **It is a message *generator*, BLEU-4 only — no classification metrics.** Useful as a dataset/weights source, not as a classifier citation.

### 4.4 Security-fix classification — the "message doesn't say fix" case

Two distinct tasks, easy to conflate: identifying vulnerability-**fixing** commits vs vulnerability-**introducing** commits. Metrics are not comparable across them.

- **Perl et al. "VCCFinder." ACM CCS 2015, 426–437. DOI 10.1145/2810103.2813604.** *(introducing commits.)* SVM over code + repo metadata. 66 C/C++ projects, 170,860 commits, 640 VCCs. **Genuinely temporal split: trained to 2010-12-31, tested on 2011–2014 CVEs — and they measured that random 10-fold CV inflates precision by ~15% at recall 0.4–0.6.** Operating points: **P 0.60 at R 0.24**; P 0.03 at R 0.66; P 0.01 at R 0.84. The "99% fewer false alarms" headline is a **false-alarm reduction at matched recall 0.24**, not high recall.
- **Sabetta, Bezzi. "A Practical Approach to the Automatic Classification of Security-Relevant Commits." ICSME 2018, 579–582. DOI 10.1109/ICSME.2018.00058. arXiv:1807.02458.** *(fixing commits.)* Two independent linear SVMs — one on the **message**, one on the **patch treated as text** — combined by OR-voting, on the argument that their errors are near-independent. **Recall at fixed precision — the right way to report this:**

  | precision | R (msg) | R (patch) | R (joint) |
  |---|---|---|---|
  | 0.95 | 0.15 | 0.14 | 0.20 |
  | 0.90 | 0.19 | 0.18 | 0.25 |
  | 0.85 | 0.21 | 0.23 | 0.31 |
  | 0.80 | 0.30 | 0.29 | **0.43** |

  **At the 0.95 precision a vulnerability database would demand, recall is 0.20.** ⚠️ Negatives are 5 *randomly sampled* commits per positive from the same repo — easy negatives, inflating the whole curve. ⚠️ The cross-language Ruby test (P 0.82 / R 0.61) is on **23 positives** — one commit is 4 pp.
- **Zhou, Pacheco, Wan, Xia, Lo, Wang, Hassan. "Finding A Needle in a Haystack: Automated Mining of Silent Vulnerability Fixes." ASE 2021, 705–716.** VulFixMiner: fine-tuned **CodeBERT on file-level code changes only — deliberately no commit message**, because silent fixes have uninformative messages. **Genuinely cross-project**: trained on 204 projects, evaluated on all 143,989 commits from 52 unseen projects, positive rate **0.1–0.3%**. **AUC 0.81 (Java) / 0.73 (Python); CostEffort@5% = 0.49** (inspect 5% of changed LOC → recover 49% of fixes). They report AUC + effort-aware metrics rather than P/R because at a 0.1% base rate precision at any threshold is meaningless — the artifact is a ranked review queue.

  **Two findings you should carry.** (1) Manual check of 82 commits flagged as fixes but not labelled as such: **29 (35%) were genuine unreported vulnerability fixes** — the ground truth itself under-counts, so measured precision is a lower bound. (2) **Only 38% (754/1,982) of actual vulnerability-fix commit messages contain security-related words.** That is the hardest number in this review for justifying "beyond keywords."
- **Zhou, Hu, Lo, Xia et al. "CoLeFunDa: Explainable Silent Vulnerability Fix Identification." ICSE 2023.** Function-level contrastive learning. vs VulFixMiner: CostEffort@5% 0.59 vs 0.52, @20% 0.72 vs 0.65, **AUC 0.80 vs 0.79 — essentially flat.** The "11–14% improvement" is relative gain on effort-aware metrics; the real gain is queue ordering, not discrimination.
- **Storhaug, Sun, Li. "Favia." arXiv:2602.12500 (Feb 2026).** ReAct agent working in the pre-commit repository state. Dataset CVEVC: >8M commits, 3,708 repos. **The methodological contribution: they evaluate under both the random-candidate setting prior work uses and a realistic all-commits setting, and show randomly sampled candidates inflate F1 by up to 95% for every method** — because real candidates are already security-relevant and mutually similar. On the realistic set Favia keeps recall up to 0.98. *(abstract-level for the exact tables.)*
- Also: VFFinder (arXiv:2309.01971, graph/AST+GNN, claims 2.0–4.0× prior recall), HERMES (commit-issue linking for VFC detection), VFDelta (arXiv:2409.16606), DUALLM (arXiv:2509.22796).

### 4.5 Who actually validates recall

**Yes, properly**: König et al. 2026 (§6.1); Sabetta & Bezzi (recall-at-fixed-precision table, though on easy negatives); VulFixMiner (held-out projects at realistic base rate); Favia (and it quantifies how much candidate-pool construction inflates everyone else). **Partially**: Levin & Yehudai (per-class recall, but on 172 pooled commits).

**Numbers to discount**: Ghadhab (balanced test set vs unbalanced baseline); Quadir (single repo + balanced + no baseline); Mariano (+1 pp on 172 commits); Sabetta's Ruby result (23 positives); VCCFinder's "99%"; **and any F1 on a positives-only corpus** (Defects4J, BugsInPy, BugsJS, PyBugHive — precision is pinned at ~1 by construction and F1 is monotone in recall).

---

## 5. Datasets and tools, with honest provenance

Provenance tiers: **T1** heuristic only (keyword/issue-ID/SZZ, never hand-checked) · **T2** automatic executable property ("buggy version fails a test, fixed passes" — *reproducibility, not a human judgment that a bug was fixed*; satisfied by reverts, deletions and disabled tests) · **T3** human-confirmed with reported procedure.

### 5.1 The direct answer: benchmarks with manually labelled positives AND negatives

**There is no canonical one.** What exists, best first:

| Resource | Positives | Negatives | Manual? | Agreement |
|---|---|---|---|---|
| **Herbold et al. (EMSE 2022) / SmartSHARK** | 11,295 linked BUG issues hand-labelled; 6,367 confirmed bugs | ~1,833 sampled non-BUG issues hand-labelled; 11,980 resolved non-bug linked issues; 1,000 no-link commits sampled | **Yes, exhaustive on the BUG class** | **Cohen's κ = 0.62, 77% raw agreement**; 23% resolved by all 3 authors |
| **Levin & Yehudai (2017)** | 500 corrective | 404 perfective + 247 adaptive | Yes, 1,151 commits / 11 projects | 79% two-rater agreement on a 110-commit subset; no κ |
| **Amit & Feitelson, CCP (SQJ 2021)** | labelled corrective | labelled non-corrective | Yes, protocols at github.com/evidencebp/commit-classification | 1,100-sample test set: R 84.1%, FPR 4.2%; no κ |
| **Berger et al., TOPLAS 2019 (arXiv:1901.10220)** | 10 keyword-labelled bug-fix commits × 20 projects | 10 non-labelled × 20 projects | **Yes — 10 industry developers, 3 experts per commit, majority rule** | the cleanest *independent audit of a keyword labeller*; found many FPs from substring/out-of-context "fix"/"error" |

**Recommendation: build your benchmark on SmartSHARK's 38 manually validated projects, and hold out Levin & Yehudai + the Berger et al. expert ratings as independent test sets.** Everything else is positives-only.

A 2026 paper states the gap in print: König et al. (arXiv:2609.21616) name BugsInPy/PyBugHive/BugsJS as confirmed-fixes-only and **SmartSHARK as the sole exception carrying both classes**.

### 5.2 Reproducible-bug benchmarks (all positives-only for your purpose)

- **Defects4J** — Just, Jalali, Ernst. ISSTA 2014, 437–440. DOI 10.1145/2610384.2628055. **T3.** Current **v3.0.1: 854 active bugs, 17 projects, MIT** (github.com/rjust/defects4j). Fix in a single issue-referencing commit; **maintainers manually minimised every patch** (hundreds of person-hours), stripping refactorings; source-only; triggering test fails pre-fix / passes post-fix, order-independent; flaky tests excluded. ⚠️ A SANER study finds **41.01% of Defects4J patches can be reduced further** (avg 4.3 lines). ⚠️ **Demonstrated LLM training-data leakage** (StarCoder); alternative: **GHRB** (Lee, Kang, Yoon, Yoo, arXiv:2310.13229 — 76 Java bugs fixed after Sep 2021, 89 by Mar 2024). **96.9% reproducible** — best of any Java dataset.
- **Bugs.jar** — Saha, Lyu, Lam, Yoshida, Prasad. MSR 2018 Data Showcase, 10–13. DOI 10.1145/3196398.3196473. **T1.5.** 1,158 bugs, 8 Apache Java projects. Labels = JIRA issue ID + `issuetype == Bug` (human-assigned type, so better than keywords — but inherits Herzig's 33.8%). ⚠️ The pipeline has a "manually verify" box but **no sample size, annotator count, κ or precision anywhere**. ⚠️ **No licence file.** ⚠️ **Only 308/1,158 (26.6%) still reproducible.**
- **BugSwarm** — Tomassi, Dmeiri, Wang, Bhowmick, Liu, Devanbu, Vasilescu, Rubio-González. ICSE 2019, 339–349. arXiv:1903.06725. BSD-3. **T2.** 10.2M Travis jobs → 447,790 fail-pass pairs → 3,091 artifacts (5.56% reproduction rate); still maintained (v1.3.1, 2026-05), ≈4,400 live. ⚠️⚠️ **Labels are purely CI-structural.** The paper itself concedes *"the supposed fix could simply delete or revert the buggy code or disable any failing tests."* **Critique: Durieux & Abreu, arXiv:1905.09375 — after 8 filters, 163 candidates → 112 bug fixes, 40 non-bug fixes, 11 unknown ⇒ 26% of a heavily pre-filtered sample were not bug fixes.** Rebuttal: arXiv:1910.13058 (disputes duplicate framing, does not claim curation).
- **BEARS** — Madeiral, Urli, Maia, Monperrus. SANER 2019, 468–478. arXiv:1901.06024. GPL-3. **T3 but single-rater.** 251 bugs / 72 projects at publication; **118 today**. ⚠️ **232 of 251 come from "case #2," where the failure is induced by retro-applying the fix commit's own new tests** — so the test evidence is partly a consequence of the label. ⚠️ First author alone; no κ. 54.6% reproducible.
- **GrowingBugs / BugBuilder** — Jiang, Liu, Niu, Zhang, Hu. ICSE 2021, arXiv:2103.00156; IEEE TSE 49(4), 2023, DOI 10.1109/TSE.2022.3177713. MIT. **T2.** README: 2,012 bugs / 257 projects. ⚠️ **The quoted "99% precision, higher than human experts" is *patch-extraction* precision against Defects4J's already-human-curated patches** on 809 commits (emits a patch for only ~43%) — **not** evidence that a mined commit is a real bug fix. ⚠️ **Worst decay: 29.8% reproducible at 15 months.**
- **Defexts** — **Benton, Ghanbari, Zhang (UT Dallas)**, ICSE '19 Companion, 47–50. DOI 10.1109/ICSE-Companion.2019.00035. *(Your brief's attribution was wrong — not "Kim & Kim".)* 654 bugs: Kotlin 225, Groovy 301, Scala 128. ⚠️⚠️ Only claim is crash-reproducibility; **the mining filter could not be verified from a primary source and no manual validation of any kind is documented**. No licence; untouched since Aug 2019.
- **GitBug-Java** — Silva, Saavedra, Monperrus. MSR 2024. DOI 10.1145/3643991.3644884. arXiv:2402.02961. MIT. **T3, best-labelled of the modern set.** 199 bugs / 55 repos, all 2023 commits. **Commit-message keywords are not used at all.** 66,042 repos → 508 candidates → **two authors independently rated 100% of candidates, third-author arbitrator; manual curation removed 29 (15 refactors, 7 features, 6 irrelevant, 1 non-English)**. ⚠️ No κ; ~130 GB download; same retro-applied-tests pattern. Companion: **GitBug-Actions**, ICSE 2024 Demos, DOI 10.1145/3639478.3640023, PyPI `gitbugactions`.

### 5.3 ManySStuBs4J — the weakest labels here

**Karampatsis, Sutton. MSR 2020 Data Showcase. DOI 10.1145/3379597.3387491. arXiv:1905.13334. Zenodo 10.5281/zenodo.3653444.** **T1.** Small: 100 projects → 115,929 "bug-fixing" commits → **10,231 SStuBs**. Large: 1,000 projects → **63,923 SStuBs**.

⚠️⚠️⚠️ **Labels are a ten-keyword commit-message filter** (*error, bug, fix, issue, mistake, incorrect, fault, defect, flaw, type*, from Ray et al. 2016) plus AST template filters. **No tests, no build, no execution; SZZ never run.** Sole validation: *"sampled 100 random commits… 94% accuracy"* — **n=100, one rater, small version only, and it validates the keyword filter, not SStuB-ness.** Other quoted accuracies (96%/300, 97.6%/384) are **borrowed from Tufano et al. 2018.**

Converging criticisms (no single refutation paper, but the pattern is damning):
1. **Latendresse, Abdalkareem, Costa, Shihab. MSR 2021. DOI 10.1109/MSR52588.2021.00062.** 318 SStuBs / 14 projects, build status checked: *"upon close manual inspection, [we] found that **none** of the failed builds actually captured SStuBs"*; only ~7.5% (18/240) of SStuB-related builds failed just before the fix. **Nothing in this dataset has been shown to break anything.**
2. **Mosolygó, Vándor, Antal, Hegedűs. MSR 2021. arXiv:2103.09604.** *"not a single SStuB was flagged by PMD"*; SpotBugs likewise.
3. Chen et al. 2022 (arXiv:2204.00963) manually re-inspected every instance they used — i.e. did not trust the shipped labels.
4. **TSSB-3M** (Richter & Wehrheim, MSR 2022, arXiv:2201.12046) criticises ManySStuBs4J's commit unrolling and entangled commits — then **uses the same keyword heuristic with no manual validation of its own.** A bigger instance of the same problem.
5. **PySStuBs** (Kamienski, Palechor, Bezemer, Hindle, MSR 2021) replicates the 10 keywords on 6.06M Python commits but had to additionally exclude "refactor" commits and name/argument changes as *"likely relate to refactoring, not bug-fixing"* — an implicit indictment of the Java version.

**Verdict: a corpus of single-statement edits whose commit message contains a bug word. Nothing stronger.**

### 5.4 SmartSHARK and the Herbold corpus — the manually validated core

**Platform**: smartshark.github.io, CC BY 4.0, MongoDB dumps. Trautsch, Trautsch, Herbold, Ledel, Grabowski, arXiv:2001.01606 (ICSE 2020 demo); Trautsch et al., EMSE 23, 2018; MSR 2021 Mining Challenge data paper arXiv:2102.11540 (77 projects, **manual validations for a 38-project subset**; 366,322 commits, 163,057 issues).

Releases: **2.2** current (740 GB full / 65 GB small; adds 21 Java projects **with no manual validations**); **2.1** (adds 28 unvalidated projects + an ML-based automated bug-fix label); **1.3** (173 GB — **the 38 Apache Java projects; use this if you want only manually validated data**). Manual validations present: **issue types and commit→issue links for 38 projects; bug-fix *line* validations for 23**. DOIs: 2.2 full 10.25625/6WAFNG; 1.3 10.25625/MUZPSF. ⚠️ The releases page lists **10 known data issues they will not fix** (unrelated commit-issue links e.g. VALIDATOR-276, LANG-100; fix in a different commit e.g. NET-270).

**Herbold et al., EMSE 27:42, 2022** validation procedure — the most rigorous in the field, and worth copying: **5,311 commit–issue links manually validated by the first author; 13,410 more accepted by a heuristic (single issue reference at message start); 1,000 heuristic links sampled — correct in all 1,000; 1,000 no-link commits also sampled.** All 11,295 linked BUG issues labelled by two authors (**κ = 0.62, 77% raw agreement**), 23% disagreements resolved by all three. Only 20 inducing commits spot-checked — they state full validation at that scale was infeasible. Data: Zenodo 10.5281/zenodo.5675024.

**Herbold, Trautsch, Ledel et al. (48 authors). "A fine-grained data set and analysis of tangling in bug fixing commits." EMSE 27(6), 2022 (Registered Report). DOI 10.1007/s10664-021-10083-5. arXiv:2011.06244.** **3,498 bug-fixing commits / 2,328 bugs / 28 Apache Java projects; 289,904 changed lines labelled by 64 labellers (45 became co-authors); four labellers per commit, consensus = ≥3 agree; Fleiss' κ = 0.67.** No consensus on 8.9% of lines. **Finding: only 17–32% of changes in bug-fixing commits actually modify source code to fix the problem** (66–87% restricted to production files). Noise without untangling, defect prediction total: **8–47% (bug level) / 5–39% (file-change level)**. Replication: github.com/sherbold/replication-kit-2020-line-validation.

Also: **Yatish, Jiarpakdee, Thongtanunam, Tantithamthavorn. "Mining Software Defects: Should We Consider Affected Releases?" ICSE 2019. DOI 10.1109/ICSE.2019.00075** — heuristic 6-month-window labelling vs team-recorded *affected release* over 32 releases: large impact. Follow-up (Vandehei, Costa, Falessi, arXiv:2011.05531): across 212 Apache projects the realistic method is **unusable for 51% of defects** because the field is missing.

### 5.5 Apache JIRA-linked corpora

- **Jureczko & Madeyski. PROMISE 2010, 9:1–10. DOI 10.1145/1868328.1868342.** The "Apache dataset," 33 projects / 65 releases, CK metrics; bug counts from **BugInfo regexes over commit messages, no issue-tracker linking at all**. ⚠️⚠️ **Demonstrably dirty**: Sun, Li & Sun (arXiv:1805.10787, ESEM 2018) found **52 of the datasets contain identical cases (1.76%–75.44%) and 28 contain inconsistent cases — identical features, conflicting labels (0.22%–56.3%).** The implausible published rates (xalan2.7 99% defective, log4j1.2 92%) are labelling artefacts.
- **Montgomery, Lüders, Maalej. "An Alternative Issue Tracking Dataset of Public Jira Repositories." MSR 2022, 73–77. DOI 10.1145/3524842.3528486. arXiv:2201.08368. Zenodo 10.5281/zenodo.5882881, CC BY 4.0.** 16 Jira instances, **1,822 projects, 2.7M issues, 32M changes, 1M issue links**, ~15 GB MongoDB. Real manual work: thematic analysis over 352 unique issue types, 50 examples per type, two peer-review sessions. ⚠️ **No κ** (peer discussion, not independent double-coding). ⚠️ **No commit links, no code metrics** — linking to git is left to you.
- **Ortu et al. "The JIRA Repository Dataset." PROMISE 2015. DOI 10.1145/2810146.2810147.** >1K projects, >700K issues, >2M comments.
- **ApacheJIT** — Keshavarz & Nagappan, MSR 2022, arXiv:2203.00101, Zenodo 10.5281/zenodo.5907001. 106,674 commits (28,239 bug-inducing), 14 projects. ⚠️ **T1, SZZ-derived, no manual validation.**

### 5.6 Technical Debt Dataset and Unified Bug Dataset — both explicitly unvalidated

- **Lenarduzzi, Saarimäki, Taibi. "The Technical Debt Dataset." PROMISE 2019. DOI 10.1145/3345629.3345630. arXiv:1908.00827. CC BY-NC-SA 4.0, research only.** 33 Java Apache projects, ~78K commits, ~28K faults, ~57K refactorings. ⚠️ **Fault-inducing commits come from OpenSZZ applied "as is"; the authors validate nothing** — and Rosa et al. score that implementation at **P 0.32 / R 0.19.** Corpus ends 2015.
- **Ferenc, Tóth, Ladányi, Siket, Gyimóthy. "A public unified bug dataset for Java." PROMISE 2018, 12–21. DOI 10.1145/3273934.3273936;** SQJ 28:1447–1506, 2020, DOI 10.1007/s11219-020-09515-0. Zenodo 10.5281/zenodo.3693686, CC BY 4.0. Unifies 5 datasets → 47,618 class-level / 43,744 file-level elements. ⚠️⚠️ **Verbatim from §6: *"We accepted the collected datasets 'as is', which means that we did not validate the data."*** All constituent labels are heuristic.

### 5.7 Infrastructure

- **GHTorrent — DEAD and actively hazardous.** Gousios & Spinellis, MSR 2012, DOI 10.1109/MSR.2012.6224294. ⚠️⚠️ **`ghtorrent.org` has lapsed and now serves an Indonesian online-gambling site** (last legitimate Wayback snapshot 2022-12-22; casino content by 2023-10-05; live today). The TU Delft mirror is NXDOMAIN. Shell access withdrawn Jul 2019; last usable dump ~Mar 2021. **Scrub any reference to it from the codebase and any bibliography.** The perils paper is still essential reading: **Kalliamvakou, Gousios, Blincoe, Singer, German, Damian. "The promises and perils of mining GitHub." MSR 2014, 92–101. DOI 10.1145/2597073.2597074** (extended EMSE 21(5):2035–2071, 2016, 13 perils): only 44% of repos are base repos; median 6 commits; **only 63.4% are software development**; 71.6% personal; only 10% ever used a PR; **GitHub reports 44% of PRs merged — manual check of 350 "non-merged" PRs found 65 actually merged**; 23% of committers aren't GitHub users.
- **GH Archive — alive.** Hourly gzipped JSON from 2011-02-12 at data.gharchive.org; BigQuery `githubarchive`. ⚠️ Code MIT, site CC-BY-4.0, **but the event data carries no stated licence** — the repo disclaims hosting it. One-maintainer pipeline, quiet since 2025-05.
- **Software Heritage — alive, most solid.** Di Cosmo & Zacchiroli, iPRES 2017; Pietri, Spinellis, Zacchiroli, MSR 2019, 138–142, DOI 10.1109/MSR.2019.00030. Live counters today: **31.2B contents, 6.39B revisions, 460M origins.** Parquet/ORC exports + public Athena, current to 2026-06-04. CC BY 4.0 + Ethical Charter. ⚠️ Authors state it is not fully reproducible and cannot claim full coverage. ⚠️ **No bugs, issues, PRs or reviews at all** — source and VCS history only.
- **World of Code — alive, access-gated.** **Ma, Bogart, Amreen, Zaretzki, Mockus. MSR 2019, 143–154. DOI 10.1109/MSR.2019.00031.** *(Your brief said "Mockus et al." — fine, but note Nolte and Herbsleb are not authors.)* EMSE version arXiv:2010.16196. Watermark V2605: **~7.3B commits, ~27.0B blobs, ~284M de-forked projects, ~63M people.** ⚠️ **Not an open download** — SSH key + GitHub/Bitbucket accounts + registration form, then shell on UTK servers. ⚠️ De-forking and author aliasing are heuristics with no published manual accuracy audit.

### 5.8 CVE → fix-commit (your CVE tier)

**The number that governs your CVE tier: of 235,341 NVD records, only ~6.7% carry a git reference tagged `Patch`.** Zhang et al., "Mapping NVD Records to Their VFCs: How Hard is it?" arXiv:2506.09702 (2025), two annotators, 95% CL / ±5% ME: **`Patch`-tagged git links are correct ~98.4%**; untagged git 86.7–89.1% (κ=0.84); **`Patch`-tagged non-git references only 13.3%** (κ=0.77); neither 8.6% (κ=0.79). After pulling six external DBs, mappable coverage reaches **11.3% — 88.7% of NVD records remain unmapped.** Corroboration: **Xu et al., ESEC/FSE 2022, arXiv:2112.02240** — only **45.7% of 10,070 CVEs had a patch in either Veracode or Snyk**, the two disagreed for ~20%, and on multi-commit fixes (41% of CVEs) recall is ~50%.

**Practical implication for you: a CVE id in a commit body is excellent evidence (the ~98% figure is for the reverse direction, but the asymmetry favours you — a developer writing "CVE-XXXX-YYYY" in a fix commit is near-conclusive). Treat it as your second-highest tier after reverts, and expect very low volume.**

**The label-noise result to cite: Croft, Babar, Kholoosi. "Data Quality for Software Vulnerability Datasets." ICSE 2023. arXiv:2301.05456.** 70 random samples per dataset (90% CL / ±10%), two security-experienced raters independently then consensus, **κ = 0.627**; ambiguous cases counted as correct, so these are **upper bounds**. **Label accuracy: Big-Vul 0.543, Devign 0.800, D2A 0.286, Juliet 1.000.** Error taxonomy (irrelevant changes / cleanup / **inaccurate fix identification**): Big-Vul 25%/28.1%/**46.9%**; D2A 0/0/**100%**. Retraining LineVul on corrected labels dropped precision **29% (Devign), 50% (Big-Vul), 80% (D2A)**. Independently reproduced by **Risse & Böhme, USENIX Security 2024** (100 random Devign "vulnerable" functions → 68 genuine, 23 not, 9 undecidable).

Per dataset:
- **Project KB / SAP — the manual gold standard.** Ponta, Plate, Sabetta, Bezzi, Dangremont. MSR 2019 Data Showcase. DOI 10.1109/MSR.2019.0006. arXiv:1902.02595. Apache-2.0, github.com/SAP/project-kb. **624 vulnerabilities, 205 Java projects, 1,282 fixing commits** — and **29 have no CVE ID at all, 46 have a CNA CVE not yet in NVD**, proving an NVD-only pipeline structurally misses fixes. Curation was a byproduct of running Eclipse Steady industrially, so there's no sampled audit or κ — the set *is* the artefact. Ground truth for Prospector/FixFinder (arXiv:2103.13375; 2,391 fix commits / 1,248 advisories; top-10 84.03%, rank-1 65.06%).
- **CVEfixes** — Bhandari, Naseer, Moonen. PROMISE 2021. DOI 10.1145/3475960.3475985. arXiv:2107.08760. Data CC-BY-4.0 (Zenodo 10.5281/zenodo.4476563), tool MIT. v1.0.8: **11,873 CVEs, 12,107 commits, 4,249 projects, 272 CWEs.** ⚠️ **Fully automatic, zero manual validation** — takes NVD `reference_json` fix links, drops ~20% non-git references, guesses language with `guesslang`. Their own limitations concede the fix commit "can still leave (part of) the vulnerability."
- **Big-Vul** (Fan et al., MSR 2020, DOI 10.1145/3379597.3387501) — 3,754 CVEs, C/C++. ⚠️ **accuracy 0.543**; 36% is Chromium, improperly traced.
- **CrossVul** (ESEC/FSE 2021, DOI 10.1145/3468264.3473122), **DiverseVul** (RAID 2023, arXiv:2304.00409) — no author-side manual validation.
- **SVEN** (He & Vechev, CCS 2023, arXiv:2302.05319) — **803 pairs, every commit manually inspected**, and the paper is a damning audit of its sources (documents a *directory rename* labelled CWE-022 by keyword flagging). Their curated 1.6k beat a baseline using ~19× more samples from the same sources.
- **SecBench** (Reis & Abreu, SecSE 2017, CEUR Vol-1977, 69–85; MIT) — **not CVE-driven**: 16 regexes over 1,978,482 commits in 248 projects, then **every candidate manually diagnosed**. Yield: 155/248 repos had hits but **only 84 (54.19%) survived manual evaluation** → 682 vulnerabilities. ⚠️ Single researcher, no κ; counts drift across versions. The 2021 successor (arXiv:2110.09635) merges other datasets, so the manual rigour does **not** extend to it.
- **OSV.dev** — schema carries fix commits properly (`affected[].ranges[]` GIT, introduced/fixed events). ⚠️ CVE-derived git ranges are **machine-inferred** ("algorithmically matching repository tags against NVD patch information" for 30,000+ advisories), no published hand-validation; ~50% of in-scope CVEs converted. ⚠️ **No single licence** — per source, including **Chainguard CC-BY-NC-ND**.
- **GitHub Security Advisories** — github/advisory-database, **CC-BY-4.0**, OSV format. ~92% unreviewed. ⚠️ **VFCFinder (Dunlap, Lin, Enck, Reaves, ASIA CCS 2024, arXiv:2311.01532) measured 63.1% of GHSA advisories missing their patch link** and backfilled 300+ VFCs that were merged — so some current GHSA fix links are model output under curator review.
- **VulnCode-DB (Google)** — ⚠️ **archived 2023-03-08, site discontinued**; self-described "experimental alpha." Historical reference only.

### 5.9 Reproducibility decay — cite in any methods section

**Zhu, Rubio-González. "On the Reproducibility of Software Defect Datasets." ICSE 2023, 2324–2335.**

| Dataset | reproducible | age at test |
|---|---|---|
| Defects4J | **96.9%** | — |
| BugSwarm | 1,239/1,795 = 69% | 32 mo |
| BEARS | 137/251 = 54.6% | 46 mo |
| GrowingBugs | 170/570 = 29.8% | 15 mo |
| Bugs.jar | 308/1,158 = 26.6% | ~5 yr |

62.6% of artifacts break at least once; artifact isolation raises reproducibility to ≥95%. **"N bugs" on a README is an upper bound on what you can run today.** Broader map: 2025 survey of 151 defect datasets, arXiv:2504.17977, catalog at defect-datasets.github.io.

---

## 6. Specific to your gap: techniques that improve RECALL, and who measures it honestly

### 6.1 The paper that is your situation, with your numbers

**König, Goldenits, König, Raubitzek, Obermann, Toth, Schmidt, Weippl, Mallinger. "Labelling Bug-Fixing Commits with Local Open-Weight Language Models." arXiv:2609.21616 (18 Sep 2026). CC BY 4.0. Code + corpus: https://github.com/Raubkatz/BugFixCommitLabelling**

Approach: prompt a local open-weight LLM with **commit message + truncated diff** (~50 lines/file, truncation marker appended), **temperature 0 / top-p 0 / top-k 1** so labels are deterministic and re-runnable. Seven models from Ollama (downloaded 2026-06-21), two fixed prompts held constant across models: P1 zero-shot, P2 few-shot with six pre-labelled examples. P2's instruction block explicitly lists non-fixes *"even when the message contains the word 'fix'"*: features, refactoring, perf work, docs, formatting, renames, config, build/CI, dependency bumps, version bumps, test-only changes, reverts, merges — and instructs the model to **judge from the diff, not the wording, and trust the diff when they disagree.**

Evaluation: four human-verified corpora — BugsInPy, BugsJS, PyBugHive (**positives only**) and **SmartSHARK** (has validated negatives). Primary results on the **34 SmartSHARK projects with manually validated issue types** (five dropped because their reference labels were themselves model-predicted), macro-averaged per repository.

**Per-repository F1 / precision / recall, 34 validated projects (mean ± SD):**

| Model | F1 P1 | Prec P1 | Rec P1 | F1 P2 | Prec P2 | Rec P2 |
|---|---|---|---|---|---|---|
| mistral-small3.2:24b | **0.645** | 0.572 | 0.751 | 0.644 | 0.588 | 0.724 |
| qwen3.6:35b | 0.633 | 0.545 | 0.773 | 0.633 | **0.634** | 0.644 |
| qwen3.5:122b | 0.620 | 0.517 | 0.799 | 0.641 | 0.602 | 0.703 |
| qwen3-coder:30b | 0.609 | 0.493 | 0.818 | 0.629 | 0.618 | 0.650 |
| gemma4:12b | 0.600 | 0.488 | 0.808 | 0.636 | 0.606 | 0.685 |
| codestral:22b | 0.519 | 0.374 | 0.904 | 0.546 | 0.405 | 0.879 |
| codegemma:7b | 0.410 | 0.268 | 0.983 | 0.429 | 0.286 | 0.953 |
| **stemming keyword baseline** | **0.399** | **0.436** | **0.394** | 0.399 | 0.436 | 0.394 |

**The keyword baseline gets recall 0.394 at precision 0.436.** Your measured 0.41 (curl) / 0.26 (commons-lang) sits squarely in that distribution — and note that **commons-lang is one of the projects in this very table.** Your audit is reproducing a published result.

Statistics: Friedman over 38 repos, χ²(7) = 222.7, p < 2.2e-16; Nemenyi CD = 1.703. **Repository-centred F1 maps are almost entirely row-coherent** — each predictor sits a roughly constant amount above or below the repository mean across the whole corpus. **So the ranking is not an averaging artefact; it holds repository by repository.** Absolute performance is governed chiefly by the repository (directory-fortress-core and opennlp hard; commons-net and ant-ivy easy) — i.e. your 0.27–0.86 precision spread is expected and is a property of the repos, not of your rule.

**The methodological finding you should internalise**: on positives-only corpora **a false positive is not representable, precision is pinned near 1 by construction, and F1 reduces to a monotone function of recall** — a classifier labelling everything a fix scores as well as a discriminating one. The ranking on the three positives-only corpora is **nearly reversed** on SmartSHARK; codegemma:7b tops all three positives-only corpora and falls to last on SmartSHARK. **This invalidates most "we achieve high recall on a curated fix dataset" claims in the field — and it means your own recall measurement is only meaningful because you also measured precision on the same repos.**

Operating-point guidance from the paper: P2 shifts every model toward precision (recall drops up to ~0.17). **For seeding SZZ use the precision-leaning point** (qwen3.6:35b under P2, precision 0.634). For corpus-building use the recall-leaning point. Caveats they state: per-repository precision for even the leading models ranges from ~0.34 to ~0.83; larger models do not consistently win; precision is a Java-only statement; SmartSHARK's negative class is "not linked to a validated bug issue," so **a real fix without a bug link counts as a negative — measured precision is a conservative lower bound.** Their released corpus (389,567 commits, 33 projects) is explicitly a **silver standard**, model-labelled.

### 6.2 Other recall-raising techniques, ranked by applicability to you

1. **Revert links** (you have them). Rosa et al. JSS 2023's HR heuristic is exactly your detector: body contains `This reverts commit`, or subject starts `Revert`. In SZZ it buys ~1 point of F1, but as a *fix-identification* tier it is near-perfect precision. ⚠️ Note that König et al.'s prompt classifies **reverts as NOT bug fixes** — a definitional conflict you must resolve explicitly. A revert is evidence that *something was wrong*, which makes it a strong tier for your purposes, but it is a different object from a forward repair. Decide and document which.
2. **Trailers** (you have them). The Linux `Fixes:` tag produced **76,046 developer-authored pairs** (Lyu et al.) and is described as created "entirely independently of the biases of software engineering researchers." Where your repos use kernel-style trailers, this is the best non-revert signal available anywhere.
3. **Issue references** (you have them). Ceiling set by Herzig's **33.8% issue-type misclassification** — expect ~2/3 precision from `issuetype == Bug` alone unless you also read the issue text.
4. **Code-aware classification of the diff.** This is the only thing that recovers fixes whose *message* carries no signal — your NULL-deref example. Evidence: VulFixMiner deliberately uses code changes only, because only 38% of security-fix messages contain a security word. König et al. show message+diff LLM prompting reaching recall 0.72–0.82 at precision 0.49–0.59 where keywords get 0.394/0.436.
5. **Supervised AST-change features** (Levin & Yehudai) — corrective P 0.75 / R 0.84 on their test set, +20 pp over keywords, dataset public. ⚠️ ChangeDistiller is Java-only, so it covers commons-lang but not curl.
6. **Issue-link recovery** to fill the unlinked ~50% (§2) — EasyLink's retrieval-only variant is the cheap entry point. But remember Nguyen/Adams/Hassan: recovering links will not de-bias the result.

### 6.3 Who measures recall honestly

**Properly**: König et al. 2026 (validated negatives, per-repo means and SDs, rank-based significance, and an explicit demonstration that the field's other corpora cannot measure precision). VulFixMiner (held-out projects, realistic 0.1–0.3% base rate; reports AUC + CostEffort because precision is meaningless at that base rate — CostEffort@5% = 0.49 is the closest readable recall). Favia 2026 (the only work quantifying how much candidate-pool construction inflates everyone). Sabetta & Bezzi (recall-at-fixed-precision table, the right presentation — though on randomly sampled, hence easy, negatives). Herbold et al. EMSE 2022 (median TPR 86.9% / FPR 81.1% for SZZ, on exhaustively hand-labelled data).

**Partially**: Levin & Yehudai (per-class recall on 172 pooled commits).

**Not at all**: essentially every tool in §2 before 2023; everything evaluated on a positives-only corpus; everything evaluated on a balanced-by-construction test set.

---

## Ranked: the 5 things most worth adopting, given your cascade inputs are already harvested

**1. Reproduce König et al.'s setup as your measurement harness, and use SmartSHARK as your external ground truth.** (arXiv:2609.21616; code github.com/Raubkatz/BugFixCommitLabelling; SmartSHARK 1.3, 38 manually validated projects, DOI 10.25625/MUZPSF.) This is the single highest-value item. It gives you (a) a published keyword baseline of **recall 0.394 / precision 0.436** that your 0.41/0.26 can be cited against, (b) **the only corpus with manually validated negatives**, so you can measure recall *and* precision on the same data, (c) **commons-lang is already in it**, so you get a direct external check on one of your eleven repos, and (d) a demonstrated rank-based protocol (Friedman + Nemenyi over repositories as blocks) for claiming one labeller beats another. Cost: a MongoDB restore and a few GPU-hours. Everything else on this list is easier to justify once this exists.

**2. Add a diff-reading LLM tier to the cascade, below the structural tiers and above/replacing keywords — at two operating points.** Same paper: message+diff, deterministic decoding (temp 0 / top-p 0 / top-k 1), their P1 prompt for the recall point (~0.75–0.82 recall at ~0.49–0.57 precision) and P2 for the precision point (~0.63 precision at ~0.64 recall). The P2 prompt text is published in full and already encodes your cleaning rule — it explicitly lists lint/docs/format/build/dependency/version-bump/test-only/revert/merge as non-fixes "even when the message contains the word 'fix'", and instructs the model to trust the diff over the message. **This is the only technique in the literature that addresses your actual failure mode** (a NULL-deref repair whose subject never says "fix"), because it is the only one that reads the repair. Note the definitional conflict on reverts and resolve it explicitly.

**3. Record a bias profile per cascade tier, not just precision.** Bird et al. (ESEC/FSE 2009, DOI 10.1145/1595696.1595716) measured that linked bugs skew **toward less severe bugs** (Apache: 63% of minor fixed bugs linked vs 15% of blockers) and **toward more experienced developers**, and their Observation 3.3 proves **commit feature bias is unobservable from inside a linked-only sample**. Nguyen/Adams/Hassan (WCRE 2010) then showed the bias survives even near-perfect linking, because it is a property of the *process*. The AspectJ anomaly is your lever: bias vanished there because three developers did 81% of the fixing and linked uniformly — **bias comes from heterogeneous linking behaviour, not from a low link rate**. So: for each tier, report the distribution of author, year, and (where available) issue severity/type against the full commit population. Nobody in §2 has done this, and it converts the field's known-unmeasurable problem into a partly measurable one.

**4. Harvest GitHub's own curated links, and widen the candidate window to one year.** Your regex over commit bodies and GitHub's `closedByPullRequestsReferences` / timeline / `closed_by` capture **different, partly disjoint** sets: a `Fixes #N` in a squashed-away feature-branch commit is invisible to the API, while PR-mediated closures are invisible to your regex. Both are cheap to add. And if you do any link recovery, EasyLink's measurement is decisive: a **7-day window captures 59% of true links; one year captures 97%** (ICSE 2026, arXiv:2507.09199). Every pre-2023 tool used 7 days, which alone caps their recall at ~0.59. Start with EasyLink's **retrieval-only variant** (FAISS + all-MiniLM-L6-v2, P@1 0.616, 0.87 s/issue, zero API cost) — it needs only issue summary/description and commit id/time/message, which is exactly what you have, and it needs no tracker labels.

**5. Treat the issue-reference tier's precision ceiling as externally bounded, and the revert/CVE tiers as near-certain but tiny.** Herzig, Just & Zeller (ICSE 2013, 392–401) hand-examined >7,000 issue reports and found **33.8% misclassified** — so a correctly linked `issuetype == Bug` commit is only about two-thirds likely to be a bug fix, independent of your linking quality. Meanwhile Herbold et al. (EMSE 27:42, 2022) found **only ~half of SZZ-identified bug-fixing commits are actually bug fixes, and ~a fifth of real ones are missed**, and the tangling study (EMSE 27(6), 2022, Fleiss κ=0.67 over 289,904 hand-labelled lines) found **only 17–32% of changes within a bug-fixing commit actually fix the bug**. For the CVE tier, Zhang et al. (arXiv:2506.09702) measured **`Patch`-tagged git references at ~98.4% correct but present for only ~6.7% of NVD records** — so expect excellent precision and very low volume. Publish these as the tier ceilings alongside your own measured numbers; it is what makes the cascade's per-tier precision claims credible rather than merely self-reported.

---

### Two corrections to the brief as given
- **Defexts** is **Benton, Ghanbari & Zhang (UT Dallas)**, ICSE '19 Companion — not "Kim & Kim".
- **"Issues with SZZ"** and **"Problems with SZZ and features"** are **the same paper** (arXiv:1911.08938, renamed before EMSE publication). Do not cite as two.

### One operational warning
**`ghtorrent.org` has lapsed and now serves an online-gambling site.** Any script, tooling reference or bibliography entry in the codebase still pointing there should be scrubbed.

### Gaps I could not close
- **Bissyandé et al., CSMR 2013** per-project table — the most load-bearing independent critique of ReLink; IEEE/CORE/HAL/SMU all 403'd. Only the qualitative conclusion ("misses many links") is sourced. Worth a manual retrieval.
- **FRLink and RCLinker** absolute per-project P/R/F from their own papers (ScienceDirect/IEEE blocked); both lead with relative improvements, which is itself a flag.
- **Hindle et al. ICPC 2009** per-class precision/recall (paywalled) — only the abstract-level ">50% accuracy" and the author-identity finding are verified.
- **BTLink's** project list and negative-sampling procedure are in neither the README nor any reachable copy.
- **No study isolates GitHub closing-keyword (`Fixes #N`) adoption** as distinct from bare `#N` references. Nearest data points: Ruan's 42.2% of issues linked, Rath's ~48% of commits unlinked.