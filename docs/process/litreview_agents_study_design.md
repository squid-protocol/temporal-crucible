# Using AI agents to design, review and run empirical studies: a literature review

Scope: how to use LLM agents to design, review and run observational studies so that the result convincingly shows (or fails to show) a claim. Covers how many independent reviews are enough, which reviewer roles to use, and how to build positive and negative controls into a study pipeline.

Written 2026-11-14. Every source in Section 5a was opened during this review. Where only an abstract, a repository record or a secondary page was available, the entry says so. Works I recall but could not open are listed separately in Section 5b and are not used as evidence in the body.

Labels used throughout:
- **[M]** what a study measured.
- **[C]** what its authors concluded.
- **[I]** my inference for this team.

---

## 1. One-page summary: the ten most useful findings

| # | Finding | Strongest source | Confidence |
|---|---|---|---|
| 1 | **LLM reviewers find a small, unstable fraction of real errors, and each run finds a different fraction.** On 91 real errata or retraction-grade errors, the best model reached 21.1% recall and 6.1% precision, and "across eight independent runs, models rarely rediscover the same errors". FLAWS: 39.1% identification at k=10 on 713 inserted errors. **[I]** The team's experiment matches this: each review finds new blockers and the rate does not fall. That pattern means a large pool of faults sampled with low probability per review. It does not mean the reviews are failing. | Son et al. 2025 (SPOT); Xi et al. 2025 (FLAWS) | High that recall is low. Medium on the exact numbers, which depend on the benchmark. |
| 2 | **Planted errors are much easier to catch than real ones, so a positive control can flatter the pipeline.** A multi-layer LLM reviewer caught over 70% of planted contradictions but only 16.1% (exact match) of real mistakes in withdrawn papers; "all review systems… perform worse on real mistakes than on our benchmark". OHDSI says the same for injected effects: synthetic positive controls carry measured confounding but not unmeasured confounding, so calibration from them may underestimate error. | Teo et al. 2026; Schuemie et al. 2018 (PNAS) | High (two independent fields agree). |
| 3 | **Same-model and even cross-vendor reviewers share blind spots, and debate does not fix it.** Over 350 LLMs: when two models both err, they pick the same wrong answer 60% of the time. Errors are more correlated in more accurate models, even across providers. Multi-agent debate is a martingale: majority voting explains most of the gain, and "debate alone does not improve expected correctness". Intrinsic self-correction does not improve reasoning and sometimes hurts it. | Kim et al. 2025 (ICML); Choi, Zhu & Li 2025 (NeurIPS) | High for the direction. Evidence comes from QA benchmarks, not study design. |
| 4 | **In human inspection, two independent reviewers caught as many defects as four. What drives yield is reading technique and expertise, not head count.** In a randomized 18-month industrial experiment (Lucent, 88+ inspections), 1-reviewer teams were worse than 2, and 2 equalled 4. Two 2-person teams were no better than one. **[I]** This does not carry over to LLM reviewers, whose per-run recall is much lower (finding 1). | Porter, Siy, Toman & Votta 1997 (IEEE TSE) | High for human code inspection. Low for transfer to LLMs. |
| 5 | **You can estimate the faults still unfound from reviewer overlap, but with fewer than four reviewers the estimate runs low.** Capture–recapture models "tend to underestimate", and fewer than four inspectors gives "rather inaccurate estimates". The recommended model is Mh with the Jackknife estimator (detection probability varies by defect). **[I]** Two reviewers with 5 blockers each and 2 shared gives a Lincoln–Petersen estimate of about 12.5 blockers (Chapman: 11), so at least 3–5 remain beyond the 8 found. Because LLM reviewers are correlated (finding 3), treat this as a floor. | Briand, El Emam, Freimut & Laitenberger 2000 (IEEE TSE) | High that the estimate is biased low. Medium on applying it to LLM reviewers. |
| 6 | **Role-based reading ("perspectives") is not reliably better than a good checklist; checklists built from the defect log are the oldest well-attested idea.** A quantitative aggregation of PBR experiments found "no clear positive effect": PBR beat ad hoc reading but lost to checklists, with "strong indicators of researcher bias". A rigorous replication found no difference between perspectives. Fagan's original process has inspectors study "ranked distributions of error types found by recent inspections" and matching checklists. | Ciolkowski 2009 (ESEM); Regnell et al. 2000; Fagan 1976 | Medium-high. The roles evidence is mixed. Defect-log-driven checklists are long-standing practice with weak controlled evidence. |
| 7 | **Run the null and positive controls through the whole pipeline before trusting it. Standard pipelines often fail their own nulls.** Uncalibrated observational designs returned p<0.05 on 50–72% of negative-control drugs (expected 5%). Standard fMRI cluster inference produced up to 70% familywise false positives on real null data. A null check is only as good as its own validation: calibration helps when controls share the bias structure, and a negative control's zero estimate is "necessary but not sufficient". | Schuemie et al. 2014; Eklund et al. 2016 (PNAS); Hwang et al. 2022 | High. |
| 8 | **Analytic flexibility is larger than reviewers expect, and AI analysts reproduce it.** 29 teams, one dataset: odds ratios from 0.89 to 2.93, with 69% significant. 73 teams: more than 95% of outcome variance was unexplained by coded decisions. LLM "AI analysts" given a fixed hypothesis and dataset also disagree on effect sizes and verdicts, and model or persona choice shifts the distribution. **[I]** A multiverse or specification curve should be a required slot. | Silberzahn et al. 2018; Breznau et al. 2022 (PNAS); Bertran, Fogliato & Wu 2026 | High for humans. Medium for AI analysts (one preprint). |
| 9 | **Blinding works when the people who decide to unblind are not the analysts, and when every look at the answer is labelled as such.** Physics practice: hidden signal box, hidden offset, hidden data fraction. The decision to unblind should sit with the wider review "and not by the data analysts alone". Post-unblinding changes are reported as such. In psychology, a separate data manager hides outcomes from the analyst. **[I]** A reviewer-proposed check that runs on the real outcome is an unblinding event. | Klein & Roodman 2005 (Annu. Rev. Nucl. Part. Sci.); Dutilh et al. 2021 | High as practice. Direct evidence that blinding reduces bias is circumstantial. |
| 10 | **Pre-registration and checklists help only when enforced; deviations go undisclosed by default.** Registration coincided with a fall in positive large NHLBI trials (57% to 8%, associational). Registered Reports carry 44% positive results against 96% in the standard literature. But 24 of 27 preregistered studies had at least one undisclosed deviation. Asking authors to complete the ARRIVE checklist produced no full-compliance gain in a 1,689-manuscript RCT. **[I]** Make the scaffold machine-checked and the deviations a computed diff. | Kaplan & Irvin 2015; Scheel et al. 2021; Claesen et al. 2021; Hair et al. 2019 | Medium-high. Registration effects are observational. The checklist RCT is strong. |

The least covered area: **I found no study that evaluates multi-agent review of study designs specifically** (as opposed to papers, QA tasks or code). Everything about LLM reviewers of designs is extrapolated from paper review, error-detection benchmarks and debate studies.

---

## 2. Findings by topic

### 2.1 LLM agents doing science end to end, and how they fail

**Systems (claims by their builders).**
- **The AI Scientist.** Lu et al. 2024 covers idea → code → experiments → paper → automated review, at under $15 per paper. **[C]** Its automated reviewer reaches "near-human performance in evaluating paper scores". Its claim that papers clear a top-conference acceptance threshold is *as judged by its own reviewer*.
- **AI Scientist-v2.** Yamada et al. 2025 submitted three fully generated manuscripts to an ICLR 2025 workshop. One scored above the average human acceptance threshold.
- **Agent Laboratory.** Schmidgall et al. 2025: **[C]** human feedback at each stage "meaningfully improved" quality, and o1-preview was the best backend.
- **AI co-scientist.** Gottweis et al. 2025, Gemini-based. Generate–critique–refine agents run a tournament. **[C]** More test-time compute improved hypothesis quality on automated evaluation, and some AML drug-repurposing candidates were validated in vitro.

**Independent evaluations and critiques (the part that matters).**
- **Beel, Kan & Baumgart 2025** (SIGIR Forum; arXiv). **[M]** 42% of experiments failed on coding errors. Code changes averaged about 8% more characters per iteration. Generated papers had a median of 5 citations, only 5 of 34 from 2020 or later. Each paper needed about 3.5 h of human involvement. The authors report that well-known ideas were labelled novel. Small sample (twelve experiments), single group.
- **Luo, Kasirzadeh & Shah 2025** (NeurIPS 2025 AI4Science spotlight). They name four failure modes in Agent Laboratory and AI Scientist v2: inappropriate benchmark selection, data leakage, metric misuse, and post-hoc selection bias. They tested these with controlled planted conditions. **[C]** The failures are "easy to miss". Auditing trace logs and code detects them "much more effectively than reviewing the final paper alone". I saw only the abstract. The roughly 82% / F1 0.81 auditor figure appeared in a secondary summary and is not verified.
- **PaperBench** (Starace et al. 2025). On 20 ICML 2024 papers (8,316 gradable tasks), the best agent averaged a 21.0% replication score. Models did not beat an ML-PhD baseline.
- **CausalPitfalls** (Du et al. 2025). **[C]** LLMs show "significant limitations" at avoiding Simpson's paradox and selection-bias traps, even when writing analysis code. The abstract gives no headline number.
- **Many AI analysts** (Bertran, Fogliato & Wu 2026). LLM analysts given a fixed dataset and hypothesis, with an AI auditor screening for methodological validity, varied substantially in effect sizes, p-values and conclusions across three datasets. Persona and model choice steered outcomes even among valid runs.

**LLMs as peer reviewers.**
- **Agreement looks like human-to-human agreement, which is itself low.** Liang et al. 2023: GPT-4 overlapped with human reviewers on 30.85% of points (Nature journals; 3,096 papers) and 39.23% (ICLR; 1,709 papers). Human–human overlap was 28.58% and 35.25%. Overlap was higher for weaker papers. For context, human journal peer review has a mean Cohen's kappa of about 0.17 and a mean ICC/r² of about 0.34 (Bornmann, Mutz & Daniel 2010; 48 studies, 19,443 manuscripts). "As good as a human reviewer" is a low bar.
- **Focus bias.** Shin et al. 2025 (EMNLP; 676 papers, 3,657 strengths and weaknesses): LLMs over-weight technical validity and "significantly overlook novelty assessment".
- **Error detection.** SPOT (Son et al. 2025): best recall 21.1%, precision 6.1%, poor run-to-run reproducibility. FLAWS (Xi et al. 2025): GPT-5 at 39.1% with k=10 candidates. Teo et al. 2026: over 70% on planted contradictions versus 16.1% (exact) / 26.1% (similar) on real withdrawn-paper errors.
- **Susceptibility to confident claims.**
  - Wang et al. 2026: an evidence-free, confident author rebuttal raised LLM-referee scores for 81% of papers in the main text (89% in a figure caption; the paper does not reconcile the two), and lowered none. Models were Gemini 2.5 and GPT 5.1, on 100 ICLR 2025 papers.
  - BadScientist (Jiang et al. 2025, ACL 2026): papers fabricated by an agent, with no experiments, reached up to 82% acceptance with o3, o4-mini and GPT-4.1 reviewers. Reviewers often flagged integrity concerns yet still gave acceptance-level scores (o4-mini 100% for several strategies). Detection-focused mitigations were about at chance.
  - Zhu et al. 2025: GPT-5-mini inflated ratings for weaker papers, and field-specific hidden prompts could steer reviews.
- **Self-preference.** Panickssery, Bowman & Feng 2024: GPT-4 and Llama 2 recognise their own outputs and rate them higher. Self-preference strength correlates linearly with self-recognition ability.

**Multi-agent review and debate.**
- **Choi, Zhu & Li 2025** (NeurIPS spotlight). Across seven benchmarks, majority voting accounts for most of the gain credited to multi-agent debate. Debate forms a martingale over beliefs.
- **Liu et al. 2026.** Argue standard debate cannot beat majority voting when errors are correlated. Propose a peer-prediction fix (preprint).
- **Kim et al. 2025** (ICML). 60% same-wrong-answer agreement when two models both err. Correlation is driven by shared provider and architecture, and rises with accuracy.
- **Huang et al. 2024** (ICLR). Intrinsic self-correction does not help reasoning without external feedback.
- **MARG** (D'Arcy et al. 2024). Splitting a paper across specialised agents (experiments, clarity, impact) cut generic comments from 60% to 29% and raised good comments per paper from 1.7 to 3.7. **[I]** Specialisation improves specificity, which is not the same as recall of blockers.

**What is contested or missing.**
- No study measures how many LLM reviews of a *study design* are enough, or whether yield plateaus.
- Evidence that model diversity helps is indirect. Kim et al. show cross-provider correlation is lower than same-provider, but still substantial for strong models.
- Beel et al. and Luo et al. are small or partly abstract-level.
- **[I]** The team's observations fit this literature closely: every design wrong, every reviewer finding new faults, a cross-vendor reviewer also finding faults, and a reviewer introducing a fault. The finding most relevant to the team is Luo et al.'s: reviewers need the code and logs, not the write-up.

### 2.2 How many reviewers, and what structure: software inspection

**Process and defect logs.** Fagan 1976 (IBM Systems Journal) defines moderator-led inspections with defined roles and exit criteria. Before inspecting, the team "should first study the ranked distributions of error types found by recent inspections" plus checklists of clues. He reports an 82% inspection error-detection efficiency on one Aetna COBOL application (4,439 statements; single uncontrolled case). Orthogonal Defect Classification (Chillarege et al. 1992, IEEE TSE) classifies each defect by *type* (the semantics of the fix) and *trigger* (what surfaced it). The distribution then diagnoses which verification step is leaking. **[I]** This is the model for a running defect log that feeds checklists.

**Number of reviewers.**
- **Porter, Siy, Toman & Votta 1997** (IEEE TSE). Randomized team size (1/2/4), number of sessions (1/2) and repair-between-sessions, over 18 months at Lucent, with reviewers drawn from 11 developers. **[M]** 1sX1p < 1sX2p and 1sX2p = 1sX4p. Two-session inspections were no better than one. **[C]** Cutting the default from four reviewers to two "may significantly reduce effort without… reducing effectiveness".
- **Rigby & Bird 2013** (FSE). Across Google, Microsoft and AMD, the median modern code review uses two reviewers. They cite the inspection consensus that "two inspectors find an optimal number of defects" (descriptive, not causal).

**Capture–recapture.**
- **Briand et al. 2000.** Real inspection data with virtual teams of 2–6 inspectors. **[M]** Models "tend to underestimate the number of defects". Fewer than four inspectors gives "rather inaccurate estimates". Calibration from past inspections "does not work for two inspectors". **[C]** Use Mh with the Jackknife estimator.
- **Petersson et al. 2004** (JSS) review a decade of work since Eick et al. 1992. Most software-engineering studies are evaluations, a majority recommend Mh-JK, and "there is a need for application experiences".
- Main known biases: unequal detection probability across defects, unequal capability across inspectors, and dependence between inspectors. Dependence means overlap is inflated, so the remaining count is underestimated. **[I]** Correlated LLM reviewers violate independence in exactly the direction that hides remaining faults.

**Role- or scenario-based reading.**
- **Basili et al. 1996** (PBR). From the replication report's summary: PBR teams found significantly more defects than teams using their usual technique. For individuals the gain was significant on generic documents but not on NASA documents.
- **Replications were weaker.** Shull, Carver, Maldonado et al. (Readers project): PBR versus checklist was not significant in either replication (for example p = 0.143 and 0.911 in R1; p = 0.063 and 0.659 pooled). Perspective had no significant effect on effectiveness (p = 0.654). Regnell, Runeson & Thelin 2000 (30 students): no significant difference among perspectives in detection rate or coverage.
- **Aggregation.** Ciolkowski 2009: "no clear positive effect of PBR". It beats ad hoc reading, loses to checklists, and shows strong indicators of researcher bias.

**Fault seeding and stopping rules.**
- I found no controlled study that opened and that measures inspector detection rates via seeded faults. Mills-style seeding (recalled, Section 5b) assumes seeded faults are as hard to find as real ones.
- The closest modern evidence comes from adjacent fields. Teo et al. 2026 (planted 70%+ versus real 16%) and Just et al. 2014 (Section 2.5) both say planted faults are only partly representative.
- Stopping rules in this literature are capture–recapture thresholds (Petersson et al. propose decision points). I found no validated universal stopping rule.

**Contested or missing.** Effect sizes for PBR shrink on replication. "Two reviewers is optimal" rests on one strong RCT plus practice. All of this is human data.

### 2.3 Controls and calibration in observational research

**Negative controls.** Lipsitch, Tchetgen Tchetgen & Cohen 2010 (Epidemiology):
- A negative-control outcome (or exposure) must be **U-comparable**: it shares the unmeasured common causes of the real pair but has no causal link.
- Under those conditions, an association in the control signals bias. Their examples cover confounding, recall bias and immortal-time bias.
- They call it a "sensitive, but blunt, tool". It cannot say which bias exists or how large it is. Control selection depends on subject-matter judgment, and wrong causal assumptions make a control misleading.

**Empirical calibration (OHDSI).**
- **Schuemie et al. 2014** (Stat Med). Uncalibrated cohort, case-control and SCCS replications gave p<0.05 for 17/34 (50%), 33/46 (72%) and 33/46 (72%) negative controls. After calibration: 6%, 11% and 5%. Their literature extrapolation ("at least 54%" of significant findings not significant) depends on assumed bias distributions.
- **Schuemie et al. 2018** (PNAS). **Synthetic positive controls**: start from negative controls and inject outcomes during exposure until a target incidence-rate ratio (1.5, 2, 4) is reached. Injected outcomes are sampled from per-subject predicted risk, to preserve *measured* confounding. **[C]** Calibrated 95% CIs cover the truth about 95% of the time in leave-one-out validation. Stated limitation: injection does not reproduce *unmeasured* confounding, so positive controls may have less bias than real effects and calibration may underestimate systematic error. Negative and positive controls are assumed exchangeable with the outcomes of interest.
- **Hwang, Quiroz & Gallego 2022** (BMC Med Res Methodol; simulation, 50,000 subjects, 500 iterations). With suitable controls, calibration raised coverage in 8 of 10 cases (+1 to +60 points), most for unmeasured confounding. With unsuitable controls the gain was only +1 to +8. It could trade bias for coverage and widen CIs a lot (0.10 to 0.44). A zero estimate on a negative control is necessary but not sufficient for suitability.
- **Gruber & Tchetgen Tchetgen 2016** (Stat Med; abstract). Calibration is conservative under mild violations and anti-conservative under severe ones, and raises type II error substantially. Routine use is "premature". (Schuemie et al. rebutted this; I recall but did not open the rebuttal.)
- **OHDSI Methods Benchmark** (Schuemie et al. 2020, HDSR). Opened only the OHDSI news page: common observational designs fall "short of expected confidence levels", and self-controlled designs did best. The specific coverage figures are listed as unverified.

**Plasmode and simulation.**
- **Franklin et al. 2014** (CSDA). Resample real covariates and exposure unchanged, simulate outcomes from models fitted to the real data with an investigator-set effect (HR 1.0, 1.5), giving 500 datasets × 100k patients. The simulated data closely matched observed structure. A known effect let them rank propensity-score strategies: hdPS cut crude bias by 88% and 70%, and an "unbiased" model was biased at HR 1.5 (1.40). Limitation: outcomes come from a limited covariate set, so realism is bounded.
- **Morris, White & Crowther 2019** (Stat Med). The ADEMP planning structure (Aims, Data-generating mechanisms, Estimands, Methods, Performance measures). In 100 simulation papers, 93 did not report Monte Carlo SEs, and only 4 of 87 justified the number of repetitions.
- **Talts et al. 2018.** Simulation-based calibration checks Bayesian inference by repeatedly simulating from the prior and checking rank uniformity (abstract only). Gelman et al. 2020's Bayesian workflow places fake-data checking inside the workflow; I saw only the abstract, which does not say this explicitly.

**Falsification on real null data.** Eklund, Nichols & Knutsson 2016 (PNAS) ran resting-state data from 499 people (about 3 million group analyses) as if task data. Parametric cluster inference reached up to 70% familywise false positives against 5% nominal. Permutation tests were nominal. **[I]** This is the clearest demonstration that a standard pipeline must be shown to pass a known null before use, and that the null must be *real data with no effect*, not idealised noise.

**What a positive control is good for, and its pitfalls (synthesis).**
- Good for: showing the pipeline *can* recover an effect of a given size (power and sensitivity), catching sign or join errors, and calibrating CIs.
- Pitfalls:
  - Injected effects lack the unmeasured confounding of real ones (Schuemie 2018).
  - Planted signals are easier than real ones (Teo 2026, in error detection).
  - Calibration quality depends on control suitability (Hwang 2022).
  - Calibration costs power (Gruber 2016).

### 2.4 Pre-registration, multi-analyst and adversarial designs, blinding, checklists

**Pre-registration and Registered Reports.**
- Kaplan & Irvin 2015 (PLOS ONE): 17/30 (57%) large NHLBI trials published before 2000 reported a significant benefit, against 2/25 (8%) after. Prospective registration was the factor most strongly associated, but this is not shown causal.
- Scheel, Schijen & Lakens 2021: 96% positive first hypotheses in 152 standard papers versus 44% in 71 Registered Reports (50% excluding replications). The authors note this is not a causal test.
- Claesen et al. 2021 (R Soc Open Sci): of 27 preregistered *Psychological Science* studies, 2 had no deviations, 1 disclosed all, and 24 (89%) had at least one undisclosed deviation. Deviations clustered in sample size, exclusions and analysis.

**Many analysts and multiverse.**
- Silberzahn et al. 2018: 29 teams and 61 analysts, odds ratios 0.89–2.93 (median 1.31), 20/29 significant.
- Breznau et al. 2022 (PNAS): 161 researchers in 73 teams, more than 95% of variance unexplained by coded decisions.
- Steegen et al. 2016: in one example only 7 of 120 reasonable processing paths gave p<.05.
- Simonsohn, Simmons & Nelson 2020: specification curve analysis in three steps (define the valid specification set, plot, joint inference). Of three published findings, one was robust, one weak and one not robust.

**Adversarial collaboration and red teams.**
- Lakens 2020 (Nature column) argues for paid red teams. He notes that the PSA red team's criticisms were later repeated by a journal reviewer because the authors had ignored them. So "assembling a red team isn't enough".
- The red-team feasibility test (Lakens & Tiokhin blog, 2020): 5 paid critics, three weeks, 107 reports, 18 unique critical issues per the arbiter (one passage says 19), 5 major. Feasibility only.
- I found no outcome-based evaluation of adversarial collaboration. The 2025 Isch, Tetlock & Clark survey surfaced only as a search snippet (Section 5b).

**Blind analysis.**
- Klein & Roodman 2005 describe four things that can be hidden: signal events (hidden box), the numerical result (hidden offset or sign from a pseudo-random seed), event counts, and a data fraction. Their guidance:
  - Design the blind "as simply and narrowly as possible".
  - Make unblinding a review decision.
  - Report post-unblinding changes.
  - Blinding solves only experimenter's bias.
  - Independent analyses complement blinding but prevent bias less directly.
  - No technique works if humans inspect events one by one.
- Roodman 2003 describes BABAR's experience (abstract only).
- Dutilh, Sarafoglou & Wagenmakers 2021: a data manager blinds the analyst. This keeps flexibility for unexpected data features while preserving confirmatory status.
- Golub 2023 (surfaced only by search) disputes that blinding is necessary. Evidence that blinding reduces bias is "at least circumstantial" (Klein & Roodman's own words).

**Checklists and reporting guidelines.**
- Hair, Macleod & Sena 2019 (IICARus RCT, 1,689 PLOS ONE manuscripts): requesting a completed ARRIVE checklist gave no full compliance in either arm. Median compliance was 36.8% versus 39.5%, and one sub-item improved. The authors suggest editorial checks are needed.
- The Cochrane CONSORT review is recalled only (Section 5b).
- **[I]** Self-attested checklists do little. Verified checklists might.

### 2.5 The software analogy: mutation, metamorphic testing, standards

**Mutation testing.**
- Just et al. 2014 (FSE; 357 real faults, 5 programs, 321 kLOC; abstract opened): mutant detection correlates significantly with real-fault detection independent of coverage. Per the search summary of the paper, 73% of real faults are coupled to mutants, 10% need new operators and 17% are not coupled.
- Papadakis et al. 2018 (recalled, Section 5b): the correlation weakens once test-suite size is controlled. That is a direct analogue of the size confound in defect prediction.
- **[I]** A pipeline that "kills" planted effects is evidence of sensitivity to *that kind* of effect only.

**Metamorphic testing and scientific software.**
- Segura et al. 2016 (IEEE TSE survey): metamorphic relations address the oracle problem by checking how outputs change under input transformations.
- Kanewala & Bieman 2014 (62 studies): oracle problems and the scientist–SE culture gap are the main obstacles to testing scientific software.
- **[I]** Metamorphic relations for a study pipeline include:
  - Permuting file IDs leaves the estimate unchanged.
  - Duplicating a repository halves the SE but leaves the point estimate unchanged.
  - Rescaling the metric rescales the coefficient.
  - Shuffling the outcome within strata drives the effect to zero.

**Known-answer datasets.** NIST StRD supplies certified values for univariate, regression, nonlinear and ANOVA computations. NIST warns that passing them "does not guarantee correct results on your own data".

**MSR standards.**
- ACM SIGSOFT Empirical Standards (Ralph et al. 2020) include a Repository Mining standard (Chatterjee, Sharma & Ralph 2022 tutorial; abstract opened). The standards are living community checklists.
- I could not open the standard's text, so I do not quote its items.

**Missing.** I found no published work that treats a research-design document as a tested artefact with planted-truth control repositories and CI. The pieces exist (plasmode, synthetic positive controls, mutation analysis, StRD, ADEMP), but no source I opened combines them for MSR studies.

### 2.6 Defect-prediction methodology (short)

- **Size confound.** El Emam, Benlarbi, Goel & Rai 2001 (IEEE TSE; via a summary of the abstract): object-oriented metrics associated with fault-proneness lost all association after controlling for class size. The authors call it "a strong size confounding effect".
- **Mislabelled bug fixes.** Herzig, Just & Zeller 2013 (ICSE): of more than 7,000 manually checked issue reports, 33.8% labelled bugs were not bugs. On average 39% of files marked defective never had a bug.
- **Bias in linked fixes.** Bird et al. 2009 (FSE): the fixes that get linked to commits are a systematically biased sample of all fixes.
- **Cross-project heterogeneity.** Zimmermann et al. 2009 (622 cross-project predictions; reportedly about 3.4% successful) is recalled only.

### 2.7 Practitioner tooling on GitHub (agent skills for research review)

**How these were checked.** I opened each repository's README or the named skill file on 2026-11-14. I read their contents as claims to assess, not instructions to follow. Star counts are ignored. None of these repositories is peer-reviewed.

The most useful finding in this subsection is that **one repository already does what this team needs and reports its own multi-agent review as unmeasured.** `pedrohcgs/claude-code-my-workflow` keeps a qualification ledger in which every check must catch planted defects. Its own ledger lists `/review-paper --peer` and "the 18-agent review fleet" as never measured.

| Repo (as opened) | Review structure and roles | Positive control / planted-effect / mutation test | Check simulated before trusted | Blinding | Stopping rule | Defect log | Evidence that it finds more errors than one review |
|---|---|---|---|---|---|---|---|
| **scunning1975/MixtapeTools**: README and `personas/referee2.md` | "Referee 2" runs in a fresh terminal, by a Claude session that "has never seen the work". Five audits: code, cross-language replication, directory, output automation, econometrics. Never modifies author code. Replication goes into the other two of R, Stata and Python; point estimates must match "to 6+ decimal places", and N and constructed variables must match exactly. | Cross-language re-implementation acts as a replication check, not a planted-effect test. Simulated data is allowed only when raw data are restricted. | No | Context separation only (fresh session). No outcome blinding. | Revise-and-resubmit rounds until Accept or Minor Revisions, or a Reject recommendation. | No (the report is filed under `correspondence/referee2/`) | **None.** The claim that "hallucination errors are likely orthogonal across LLM-produced code in different languages" is asserted without data. It sits awkwardly with Kim et al. 2025 (correlated errors, Section 2.1). A "Fletcher" interpretation audit is named only on third-party aggregator pages; I did not find it in the current README, and the README's referenced `skills/referee2/` folder was absent from its file tree. |
| **Orchestra-Research/AI-Research-SKILLs** `22-agent-native-research-artifact/`: folder listing and `rigor-reviewer/SKILL.md` | Level 1 checks structure (references, required fields, links). Level 2 has a single "rigor-reviewer" score six dimensions from 1 to 5: evidence relevance, falsifiability quality, scope calibration, argument coherence, exploration integrity (dead ends recorded, no claim resting on a dead end), and methodological rigour. Read, Write, Glob and Grep only; no code execution. | No | No | No | No (grade from mean score with floors) | The exploration tree records dead ends, which is a kind of decision log. | **None found.** The design idea worth borrowing: claims carry falsification criteria, and experiments are mapped to claims. |
| **James-Traina/compound-science**: README and `.evals/` listing | `/workflows:review` runs econometric-reviewer, numerical-auditor, identification-critic and journal-referee in parallel. A mathematical-prover is also listed. Findings under 0.60 confidence are suppressed. Each major finding carries a "what would change my mind" statement. `/replicate` routes to a reproducibility auditor (seeds, paths, pinned versions, AEA checklist). | No (the numerical auditor *reviews* a simulation design; it does not run one on the pipeline) | No | No | No (the confidence cutoff is not a stopping rule) | No (a CHANGELOG only) | **None reported.** 237 structural tests are cited. `.evals/` holds a single `grade.py`, with no results published. |
| **pedrohcgs/claude-code-my-workflow**: README, `.claude/skills/vaccinate/SKILL.md`, `quality_reports/qualification/LEDGER.md` | `deep-audit`: decompose, then independent skeptics, then a separate judge per finding, then fix and re-verify, "loop-until-dry". The README does **not** say "four parallel auditors". `review-paper --peer` simulates an editor and referees; `--variance N` gives a decision distribution. A `review-fencing` rule gives reviewers neutral copies with prior verdicts excluded. | **Yes.** `/vaccinate` builds seeded-defect variants plus a mandatory clean control, runs the checker fresh and blind to the test, and scores recall, false positives, localization and the delta against a simple baseline such as grep or diff. Its rule: "an unqualified check is not weak evidence — it is none." | **Yes.** Checks must be qualified before use, re-qualified after material change, with tolerances fixed in advance. | Reviewer fencing (neutral copy, prior verdicts withheld). No outcome blinding. | "Loop-until-dry". Two clean rounds is the convergence rule for a different QA skill. | **Yes**, the qualification ledger. Example rows: `validate-findings.py` 8/8 recall with 0/1 false positives; `backtest.sh` 3/4 at first (FAIL, then fixed) and 10/10 later. | **Only for scripted checkers, not for the LLM review fleet**, which the ledger itself lists as unqualified. The ledger also contradicts itself on skill evals: it says "No skill in this template has been eval'd", yet tabulates 3/3 versus 0/3. Results are self-reported throughout. |
| **K-Dense-AI/scientific-agent-skills**: README | The README lists experimental-design (randomization, blocking, factorial designs), statistical-power, scientific-critical-thinking and peer-review skills. I did not open the skill files. | Not described | Not described | Not described | Not described | No | **None for these skills.** The benchmarks cited in the README concern other skills. |
| **Imbad0202/academic-research-skills**: README | A 10-stage research → write → review → revise pipeline with integrity gates. The gates use a 7-mode blocking checklist of AI research failure modes, and an R&R traceability matrix maps each concern to a revision and a verified re-review. The paper reviewer is described as "7-agent" (journal-fit reviewer, three dynamic reviewers, devil's advocate, two unnamed). The devil's advocate concedes only at a 4/5 rebuttal score. Optional cross-model critique. | An opt-in calibration measures false-negative and false-positive rates against a user-supplied gold set. Not a planted effect in study data. | No | No | No explicit rule for review rounds | The failure-mode checklist plays a similar role. | **None.** The README says live reviews are `NOT_CALIBRATED`. The calibration runner uses a 25-item synthetic gold set with a stub judge. A showcase run's integrity gate flagged 15 bad references, yet a later audit found 21 of 68 final references still problematic, which is evidence of what the gate *missed*. |
| **kthorn/research-superpower**: README | `subagent-driven-review` is **parallel literature screening** (batches of papers scored against a rubric), not review of a study. | n/a | n/a | n/a | n/a | n/a | None. Not relevant to design review. |
| **brycewang-stanford/Auto-Empirical-Research-Skills**: README | A mirror of upstream snapshots (including MixtapeTools, compound-science and pedrohcgs) plus first-party skills, CC BY-SA 4.0 with a license audit file. | It reports 19 numeric benchmark tasks with gold values "recomputed from real data each run", plus 9 pass/fail fixtures, but these test analysis skills, not review. | n/a | n/a | n/a | n/a | Self-reported tests only. Its own counts disagree: 23,000+ versus 1,151 skills, and 17/37 versus 19/42 evaluations. |
| **SakanaAI/AI-Scientist**: README | `perform_review` has 5 self-reflection rounds and a 5-review ensemble at temperature 0.1, outputting a 1–10 score, Accept/Reject and weaknesses. The README notes other models show "positivity bias". | No | No | No | Fixed counts (reflections, ensemble) | No | None in the README. Independent evaluation is negative: Beel et al. 2025, Section 2.1. |
| **SakanaAI/AI-Scientist-v2**: README | A review model flag (`--model_review`). Tree search is bounded by `steps`, `max_debug_depth` and `num_drafts`. | No | No | No | Tree-search budget only | No | None in the README. One of three papers passed a workshop review, per the paper. |
| **SamuelSchmidgall/AgentLaboratory**: README | Three phases with specialised agents. A co-pilot mode flag adds the human. The README describes no reviewer roles. | No | No | No | Not described | No | None in the README. The paper reports that human feedback improved quality (Section 2.1). |

**Bottom line for this team.**
- **No repository offers evidence that multi-agent or multi-role review finds more errors than a single review.** The one that measures anything (pedrohcgs) measures scripted checks and openly marks its LLM review fleet as unqualified.
- **Three ideas are worth borrowing:**
  1. pedrohcgs's *qualify-before-trust* ledger: seeded defects, a clean control, a simple baseline, and tolerances fixed in advance. This is exactly the step that would have caught the 71% placebo.
  2. MixtapeTools's fresh-session auditor plus independent re-implementation. Treat it as an untested hypothesis: same-family models may share errors across languages.
  3. Orchestra's claims with falsification criteria, mapped to experiments, plus a dead-end log.
- **None of the repositories has outcome blinding or a positive control planted in study data.**

---

## 3. Implications for a study-design scaffold (testable proposals)

Each proposal names its evidence and a way to test whether it works for this team.

### 3.1 Required slots (commit as a file; CI refuses to advance a design with an empty or "n/a" slot unless a justification is given)

1. **Estimand and claim.** One sentence: the metric predicts bug-fix location *beyond size*, on which population, with which effect measure. *(Morris 2019 ADEMP: estimand first.)*
2. **Prior-work check.** Cite at least 3 closest prior studies and say how this one differs. Flag known confounds from the domain list in Section 2.6. *(Beel 2025 and Shin 2025: LLMs misjudge novelty. The team skipped this.)*
3. **Data-generating assumptions and threats.** Size, label noise (Herzig), linkage bias (Bird), cross-project heterogeneity. Each threat is mapped to the control or analysis that addresses it.
4. **Negative controls**, each with a written U-comparability argument: why the control shares the confounding structure (for example with size) and why it cannot cause the outcome. *(Lipsitch 2010.)* Each must also carry a **pre-validated false-positive rate**: run the check on simulated or permuted null outcomes before real data, report the rate with its Monte Carlo SE, and reject any check whose rate on a correct pipeline exceeds its nominal level. *(Eklund 2016; Morris 2019; this would have caught the 71% placebo.)*
5. **Positive controls**, at a graded range of effect sizes (OHDSI used IRR 1.5/2/4). Each states how confounding with size is preserved during injection, and acknowledges what is *not* preserved. *(Schuemie 2018.)*
6. **Power and detection curve.** The probability that the pipeline detects the positive control at each size, from simulation. *(Morris 2019.)*
7. **Multiverse or specification set.** The defensible analytic choices and a joint-inference plan. *(Steegen 2016; Simonsohn 2020; Breznau 2022.)* Optionally, several independent agent-analysts as a multiverse. *(Bertran 2026.)*
8. **Blinding plan.** What is hidden, who holds the key, what triggers unblinding, and how post-unblinding analyses are labelled. *(Klein & Roodman 2005.)*
9. **Defect-log checklist.** The current top-N defect classes from the running log, each answered "addressed by …". *(Fagan 1976; Chillarege 1992.)*
10. **Deviation log.** A computed diff between the committed design and what ran. *(Claesen 2021: deviations are almost always undisclosed otherwise.)*

*Test:* over the next N designs, count blockers found after the slot-filled design is committed versus the historical baseline (every design materially wrong). The scaffold earns its keep if late-found blockers per design fall.

### 3.2 Reviewer roles and what each reads for

The evidence does not support roles over checklists (Ciolkowski 2009; Regnell 2000). Two designs reasonably fit what is known:
- give each reviewer a **role and the defect-log checklist**, not a role alone; and
- give every reviewer **the code, logs and simulated outputs, not just the prose**. *(Luo 2025: auditing traces beats reading the paper.)*

Suggested roles:
- **Estimand and statistics.** Identification, the size adjustment, inference, multiverse.
- **Measurement and data provenance.** Bug-fix labelling, SZZ/linkage, sampling. Reads for Herzig- and Bird-type failures.
- **Controls auditor.** Checks each control's U-comparability argument and *reruns its null-validation simulation*. Never sees real outcomes.
- **Pipeline-code auditor.** Diffs code against design, runs the metamorphic relations (Section 2.5), checks known-answer cases.
- **Prior-work and novelty.** Run by a human or a retrieval-grounded agent; LLMs are weak here (Shin 2025).
- **Falsifier / red team.** Must state each objection as a testable prediction ("if X, the placebo will show Y"), which is then simulated before it is accepted.

Rules for all reviewers:
- **Proposed checks are code, not prose, and are validated on synthetic data before adoption.** A reviewer introducing an unvalidated check is a defect class in the log.
- **Blockers must be stated as falsifiable claims.** Reviewer scores and severity labels are not trusted, given sycophancy (81–89% inflation from an evidence-free rebuttal; Wang 2026) and the concern-acceptance conflict (BadScientist).
- **Authors may not argue a blocker away. They must fix it or show a test.** This removes the rebuttal channel that Wang 2026 shows is easily exploited.

*Test:* seed known flaws into a design (Section 3.4) and compare detection by role+checklist reviewers against generic reviewers.

### 3.3 How many independent reviews, and a stopping rule

- Human inspection says 2 ≈ 4 (Porter 1997). LLM per-run recall is about 20–40% with poor run-to-run overlap (SPOT, FLAWS). So **do not stop at two LLM reviews**.
- **Proposed rule:**
  1. Run reviews in rounds of k ≥ 4 independent reviewers. Use separate sessions; mix vendors and prompts or roles; no reviewer sees another's output. *(Briand 2000: fewer than 4 reviewers gives inaccurate estimates. Kim 2025: diversity reduces, but does not remove, correlation.)*
  2. After each round, deduplicate blockers into a canonical list, an adjudication step for a human or a fixed rubric.
  3. Estimate remaining blockers with Mh-Jackknife.
  4. Stop when the estimated remaining blockers fall below 1 **and** a round of k fresh reviewers finds no new blocker *class*.
  5. Cap total rounds. If the cap is hit, the design goes to a human expert, not to more agents.
- Aggregate by union of verified blockers, not by debate or vote. *(Choi 2025: debate adds little beyond voting. For defect finding the union matters, not the majority.)*
- **Caveat.** Correlated reviewers make the estimate a floor. Calibrate it with seeded flaws (Section 3.4) to learn the reviewers' actual detection probability.

### 3.4 Estimating remaining faults (worked example and calibration)

- Two reviewers, 5 and 5 blockers, 2 shared:
  - Lincoln–Petersen N̂ = 5×5/2 = 12.5.
  - Chapman N̂ = (6×6)/3 − 1 = 11.
  - So about 3–5 blockers remain beyond the 8 distinct ones found.
  - With 2 reviewers and positive dependence, Briand's results say this underestimates.
- **Calibrate with seeded flaws.** Each cycle, plant m known flaws drawn from the defect log into a copy of the design: an unvalidated placebo, a leakage path, a size-adjustment error, mislabelled outcomes. Measure the fraction found. *(Mills-style seeding; Teo 2026 and Just 2014 both warn planted flaws are easier than real ones.)* So seed flaws **copied from real past defects**, not invented ones, and treat the measured detection rate as an upper bound.

### 3.5 Building and validating positive and negative controls

**Positive control by injection into real repository data** (Schuemie 2018; Franklin 2014):
- Keep the real files, metrics and size. Simulate additional bug-fix events whose probability depends on the metric with a known effect, *on top of* a fitted baseline model that includes size and other covariates.
- This preserves measured confounding with size. It does not preserve unmeasured structure such as developer behaviour or labelling bias.
- Run a range of effect sizes. Report the recovery curve and CI coverage.
- **Pitfall test:** also inject effects whose signal is partly carried by size (metric correlated with size), and check the pipeline does not over- or under-attribute.

**Plasmode control repository with planted truth:**
- Valuable as a CI fixture that catches regressions and sign errors (an analogue of NIST StRD).
- Risks: the pipeline gets tuned to it (Goodhart), and it is easier than real data (Teo 2026).
- Mitigations: keep several control repositories; hold some out and use them only at release; refresh planted effects with random seeds unknown to the analyst agent (the hidden-offset idea from Klein & Roodman).

**Mutating small repositories:**
- Useful for sensitivity: does the pipeline notice when you plant a bug-fix pattern?
- Mutation analysis is confounded by size and test volume (Papadakis 2018, recalled). Mutants cover most but not all real fault types (Just 2014: about 17% uncoupled, per summary).
- So report detection by mutant *class*, never as a single score, and never as evidence of validity on real effects.

**Negative controls** (Lipsitch 2010; Hwang 2022; Eklund 2016):
- Prefer controls that share the confounding with size: a placebo metric that tracks size but has no plausible causal path, or an outcome the metric cannot affect.
- Validate the false-positive rate of each placebo on simulated nulls *and* on permuted real outcomes **before** looking at the real result.
- Use several negative controls and fit an empirical null (Schuemie 2014). Remember calibration costs power (Gruber 2016).

**What makes controls trustworthy:**
- exchangeability with the real question, argued in writing;
- validated operating characteristics, with Monte Carlo SE;
- graded strengths;
- held-out instances;
- seeds the analyst cannot see.

**What makes them misleading:**
- injected effects that are cleaner than real ones;
- placebos that do not share the confounding structure;
- a single control repository reused until the pipeline fits it;
- controls run on real outcomes, which leaks the answer.

### 3.6 Protecting blinding with agents

*(Klein & Roodman 2005; Dutilh 2021; MacCoun & Perlmutter 2015, recalled.)*

- **Separate the data manager from the analysts.**
  - One process holds the real outcome and an analyst-invisible key.
  - Analyst and reviewer agents receive blinded outcomes: hidden offset, permuted labels within project, or a hidden-box exclusion of the test projects.
  - Enforce this with file permissions or credentials, not with instructions.
- **Unblinding is a recorded, reviewed event.**
  - It needs the stopping rule met and human sign-off.
  - Any check proposed after unblinding is labelled post-blind in the report.
- **Any reviewer-proposed check that touches real outcomes is an unblinding event** and requires that sign-off. The placebo incident is exactly this failure.
- **Agents may leak via logs.** Keep the real-result artefacts out of any directory or context an analyst or reviewer agent can read. Test the protection by planting a canary value in the blinded store and checking that it never appears in agent outputs.

### 3.7 Where a human expert is not replaceable (on current evidence)

- **Choosing controls and arguing U-comparability.** This needs subject-matter judgment (Lipsitch 2010).
- **Novelty and prior-work judgment.** LLMs mislabel known ideas as new and overlook novelty (Beel 2025; Shin 2025).
- **Adjudicating severity and deduplicating blockers.** LLM reviewers inflate scores, cave to confident rebuttals and flag concerns without acting on them (Wang 2026; BadScientist; Zhu 2025). Lakens' red team used a neutral human arbiter.
- **Authorising unblinding**, and deciding when a design that hits the review cap is fundamentally unsound.
- **Judging whether a positive control is realistic enough** to stand in for the real effect.

---

## 4. What I could not find or verify, and questions for a second search

**Not found:**
1. Any evaluation of LLM (multi-)agent review of **study designs or pre-registrations**: yield per reviewer, plateau, or the benefit of vendor diversity.
2. Controlled evidence that **seeded-fault calibration** predicts inspectors' detection of real defects.
3. Application of **capture–recapture to LLM reviewers**, including how strongly reviewer dependence biases the estimate.
4. Published **MSR or defect-prediction pipelines validated with injected positive controls** or plasmode repositories.
5. Outcome-based evaluation of **adversarial collaboration** and **red teams** beyond feasibility.
6. Any practitioner repository (Section 2.7) with evidence that its multi-agent review beats a single review. The ledger in the one repository that measures checks marks its own review fleet as unqualified.

**Not verified** (search snippets only; see Section 5b):
- Papadakis 2018
- Porter, Votta & Basili 1995, and the Fusaro 1997 replication
- Votta 1993
- Zimmermann 2009
- the Turner 2012 CONSORT review
- Prasad & Jena 2013
- the OHDSI 2020 coverage numbers
- the Luo 2025 auditor F1
- Sauer 2000 (expertise drives review yield)

**Questions for an independent search:**
- Is there any 2025–26 study of "AI reviewer panels" for protocols or registered reports (for example at journals piloting AI review), with yield-versus-panel-size curves?
- Do correlated-error results (Kim 2025) hold for *critique* tasks, as opposed to multiple-choice QA?
- What does the OHDSI benchmark report for coverage of synthetic versus real positive controls?
- Has anyone measured whether LLM reviewers catch *planted design flaws* (as opposed to paper errors) at rates that predict real-flaw detection?
- Domain review: the Tantithamthavorn and Shepperd line on mislabelling and researcher bias in defect prediction; SZZ validity studies; size-adjusted metric validity since El Emam.

---

## 5. Sources

### 5a. Verified (opened during this review)

Format: Authors (year). Title. Venue. URL opened. What was seen.

**Topic 1: AI science systems, LLM reviewers, debate**
1. Lu, C., Lu, C., Lange, R.T., Foerster, J., Clune, J., Ha, D. (2024). The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery. arXiv:2408.06292. https://arxiv.org/abs/2408.06292. Abstract.
2. Yamada, Y., Lange, R.T., Lu, C., Hu, S., Lu, C., Foerster, J., Clune, J., Ha, D. (2025). The AI Scientist-v2: Workshop-Level Automated Scientific Discovery via Agentic Tree Search. arXiv:2504.08066. https://arxiv.org/abs/2504.08066. Abstract.
3. Schmidgall, S., et al. (2025). Agent Laboratory: Using LLM Agents as Research Assistants. arXiv:2501.04227. https://arxiv.org/abs/2501.04227. Abstract.
4. Gottweis, J., Weng, W.-H., et al. (2025). Towards an AI co-scientist. arXiv:2502.18864. https://arxiv.org/abs/2502.18864. Abstract.
5. Beel, J., Kan, M.-Y., Baumgart, M. (2025). Evaluating Sakana's AI Scientist: Bold Claims, Mixed Results, and a Promising Future? SIGIR Forum / arXiv:2502.14297. https://arxiv.org/abs/2502.14297. Abstract.
6. Luo, Z., Kasirzadeh, A., Shah, N.B. (2025). The More You Automate, the Less You See: Hidden Pitfalls of AI Scientist Systems. arXiv:2509.08713 (NeurIPS 2025 AI4Science). https://arxiv.org/abs/2509.08713. Abstract.
7. Starace, G., et al. (2025). PaperBench: Evaluating AI's Ability to Replicate AI Research. arXiv:2504.01848. https://arxiv.org/abs/2504.01848. Abstract.
8. Son, G., et al., Biderman, S. (2025). When AI Co-Scientists Fail: SPOT, a Benchmark for Automated Verification of Scientific Research. arXiv:2505.11855. https://arxiv.org/abs/2505.11855. Abstract.
9. Xi, S., Rao, V., Payan, J., Shah, N.B. (2025). FLAWS: A Benchmark for Error Identification and Localization in Scientific Papers. arXiv:2511.21843. https://arxiv.org/abs/2511.21843. Abstract.
10. Teo, R.S.Y., Yamada, Y., Kotyan, S., Imajuku, Y., Clanuwat, T. (2026). Beyond Imitation: A Framework and Benchmark for LLM-Assisted Peer Review. arXiv:2610.11087. https://arxiv.org/html/2610.11087. Full text, partial (planted versus real-error results, Table 3).
11. Jiang, F., Feng, Y., Li, Y., Niu, L., Alomair, B., Poovendran, R. (2025). BadScientist: Can a Research Agent Write Convincing but Unsound Papers that Fool LLM Reviewers? arXiv:2510.18003 (ACL 2026). https://arxiv.org/html/2510.18003v1. Full text, tables.
12. Liang, W., et al., Zou, J. (2023). Can large language models provide useful feedback on research papers? A large-scale empirical analysis. arXiv:2310.01783. https://arxiv.org/abs/2310.01783. Abstract.
13. Shin, H., et al., Kim, J. (2025). Mind the Blind Spots: A Focus-Level Evaluation Framework for LLM Reviews. EMNLP 2025. https://arxiv.org/abs/2502.17086. Abstract.
14. Zhu, C., Xiong, J., Ma, R., Lu, Z., Liu, Y., Li, L. (2025). When Your Reviewer is an LLM: Biases, Divergence, and Prompt Injection Risks in Peer Review. arXiv:2509.09912. https://arxiv.org/abs/2509.09912. Abstract.
15. Wang, J., et al., Chen, L. (2026). When AI reviews science: Can we trust the referee? arXiv:2604.23593 (The Innovation Informatics). https://arxiv.org/html/2604.23593. Full text, partial (rebuttal-sycophancy probe).
16. Huang, J., Chen, X., Mishra, S., Zheng, H.S., Yu, A.W., Song, X., Zhou, D. (2024). Large Language Models Cannot Self-Correct Reasoning Yet. ICLR 2024. https://arxiv.org/abs/2310.01798. Abstract.
17. Choi, H.K., Zhu, X., Li, S. (2025). Debate or Vote: Which Yields Better Decisions in Multi-Agent Large Language Models? NeurIPS 2025. https://arxiv.org/abs/2508.17536. Abstract.
18. Liu, Y., et al., Lukas, N. (2026). Breaking the Martingale Curse: Multi-Agent Debate via Asymmetric Cognitive Potential Energy. arXiv:2603.06801. https://arxiv.org/abs/2603.06801. Abstract.
19. Kim, E., Garg, A., Peng, K., Garg, N. (2025). Correlated Errors in Large Language Models. ICML 2025. https://arxiv.org/abs/2506.07962. Abstract.
20. Panickssery, A., Bowman, S.R., Feng, S. (2024). LLM Evaluators Recognize and Favor Their Own Generations. arXiv:2404.13076 (NeurIPS 2024). https://arxiv.org/abs/2404.13076. Abstract.
21. D'Arcy, M., Hope, T., Birnbaum, L., Downey, D. (2024). MARG: Multi-Agent Review Generation for Scientific Papers. arXiv:2401.04259. https://arxiv.org/abs/2401.04259. Abstract.
22. Du, J., et al., Ding, J. (2025). Ice Cream Doesn't Cause Drowning: Benchmarking LLMs Against Statistical Pitfalls in Causal Inference. arXiv:2505.13770. https://arxiv.org/abs/2505.13770. Abstract.
23. Bertran, M., Fogliato, R., Wu, Z.S. (2026). Many AI Analysts, One Dataset: Navigating the Agentic Data Science Multiverse. arXiv:2602.18710. https://arxiv.org/abs/2602.18710. Abstract.
24. Bornmann, L., Mutz, R., Daniel, H.-D. (2010). A Reliability-Generalization Study of Journal Peer Reviews. PLoS ONE 5(12):e14331. https://pmc.ncbi.nlm.nih.gov/articles/PMC3001856. Abstract.

**Topic 2: inspection**
25. Fagan, M.E. (1976). Design and code inspections to reduce errors in program development. IBM Systems Journal 15(3). https://www.ida.liu.se/~TDDC90/labs/lab-papers/fagan76.pdf. Full text (extracted).
26. Porter, A.A., Siy, H.P., Toman, C.A., Votta, L.G. (1997). An Experiment to Assess the Cost-Benefits of Code Inspections in Large Scale Software Development. IEEE TSE 23(6). https://userweb.cs.txstate.edu/~rp31/papersSQ/PorterEtAl_TSE.pdf. Full text (extracted).
27. Briand, L.C., El Emam, K., Freimut, B.G., Laitenberger, O. (2000; NRC report 2001). A Comprehensive Evaluation of Capture-Recapture Models for Estimating Software Defect Content. IEEE TSE 26(6). https://www.ehealthinformation.ca/web/default/files/wp-files/2001-A-Comprehensive-Evaluation.pdf. Full text (extracted).
28. Petersson, H., Thelin, T., Runeson, P., Wohlin, C. (2004). Capture-recapture in software inspections after 10 years research. JSS 72(2). https://ebse.webspace.durham.ac.uk/?p=220. Abstract page.
29. Ciolkowski, M. (2009). What do we know about perspective-based reading? An approach for quantitative aggregation in software engineering. ESEM 2009. https://ebse.webspace.durham.ac.uk/?p=130. Abstract page.
30. Regnell, B., Runeson, P., Thelin, T. (2000). Are the perspectives really different? Further experimentation on scenario-based reading of requirements. Empirical Software Engineering 5(4). https://lup.lub.lu.se/record/777841. Repository abstract.
31. Shull, F., Carver, J., Basili, V., Mendonça, M., Maldonado, J.C., Höhn, E.N., Fabbri, S., Oliveira, M.C.F., Martimiano, L., et al. (undated technical report, c. early 2000s). Data Analysis of the First Two PBR Replications in Readers Project. ICMC/USP report hosted at https://www.cs.umd.edu/users/basili/publications/technical/T136.pdf. Full text (extracted). Note: the URL suggested Basili et al. 1996, but the file is this replication report.
32. Rigby, P.C., Bird, C. (2013). Convergent contemporary software peer review practices. ESEC/FSE 2013. https://users.ece.utexas.edu/~miryung/teaching/EE379K-Spring2014/Papers/Paper%204.pdf. Full text (extracted).
33. Chillarege, R., et al. (1992). Orthogonal Defect Classification: A Concept for In-Process Measurements. IEEE TSE 18(11). https://chillarege.com/docs/Papers/concept. Full text (partial).

**Topic 3: controls and calibration**
34. Lipsitch, M., Tchetgen Tchetgen, E., Cohen, T. (2010). Negative Controls: A Tool for Detecting Confounding and Bias in Observational Studies. Epidemiology 21(3). https://pmc.ncbi.nlm.nih.gov/articles/PMC3053408. Full text.
35. Schuemie, M.J., Ryan, P.B., DuMouchel, W., Suchard, M.A., Madigan, D. (2014). Interpreting observational studies: why empirical calibration is needed to correct p-values. Stat Med 33(2). https://pmc.ncbi.nlm.nih.gov/articles/PMC4285234. Full text.
36. Schuemie, M.J., Hripcsak, G., Ryan, P.B., Madigan, D., Suchard, M.A. (2018). Empirical confidence interval calibration for population-level effect estimation studies in observational healthcare data. PNAS 115(11). https://pmc.ncbi.nlm.nih.gov/articles/PMC5856503. Full text.
37. Hwang, H., Quiroz, J.C., Gallego, B. (2022). Assessing the effectiveness of empirical calibration under different bias scenarios. BMC Med Res Methodol 22:208. https://pmc.ncbi.nlm.nih.gov/articles/PMC9327283/. Full text.
38. Gruber, S., Tchetgen Tchetgen, E. (2016). Limitations of empirical calibration of p-values using observational data. Stat Med 35(22). https://read.qxmd.com/read/26970249/limitations-of-empirical-calibration-of-p-values-using-observational-data. Abstract.
39. OHDSI (n.d.). News item on Schuemie et al., "How Confident Are We About Observational Findings in Healthcare: A Benchmark Study" (HDSR 2020). https://www.ohdsi.org/ohdsi-news-updates/benchmark-study/. Secondary news page only.
40. Franklin, J.M., Schneeweiss, S., Polinski, J.M., Rassen, J.A. (2014). Plasmode simulation for the evaluation of pharmacoepidemiologic methods in complex healthcare databases. CSDA 72. https://pmc.ncbi.nlm.nih.gov/articles/PMC3935334. Full text.
41. Morris, T.P., White, I.R., Crowther, M.J. (2019). Using simulation studies to evaluate statistical methods. Stat Med 38(11). https://pmc.ncbi.nlm.nih.gov/articles/PMC6492164. Full text.
42. Talts, S., Betancourt, M., Simpson, D., Vehtari, A., Gelman, A. (2018). Validating Bayesian Inference Algorithms with Simulation-Based Calibration. arXiv:1804.06788. https://arxiv.org/abs/1804.06788. Abstract.
43. Gelman, A., Vehtari, A., Simpson, D., Margossian, C.C., et al. (2020). Bayesian Workflow. arXiv:2011.01808. https://arxiv.org/abs/2011.01808. Abstract (does not itself mention fake-data simulation).
44. Eklund, A., Nichols, T.E., Knutsson, H. (2016). Cluster failure: Why fMRI inferences for spatial extent have inflated false-positive rates. PNAS 113(28). https://pmc.ncbi.nlm.nih.gov/articles/PMC4948312. Full text.

**Topic 4: pre-registration, multi-analyst, blinding, checklists**
45. Kaplan, R.M., Irvin, V.L. (2015). Likelihood of Null Effects of Large NHLBI Clinical Trials Has Increased over Time. PLoS ONE 10(8). https://pmc.ncbi.nlm.nih.gov/articles/PMC4526697. Abstract and full text.
46. Scheel, A.M., Schijen, M.R.M.J., Lakens, D. (2021). An excess of positive results: Comparing the standard psychology literature with Registered Reports. AMPPS (PsyArXiv record). https://research.tue.nl/en/publications/an-excess-of-positive-results-comparing-the-standard-psychology-l/. Abstract.
47. Claesen, A., Gomes, S., Tuerlinckx, F., Vanpaemel, W. (2021). Comparing dream to reality: an assessment of adherence of the first generation of preregistered studies. R Soc Open Sci 8:211037. https://pmc.ncbi.nlm.nih.gov/articles/PMC8548785. Full text.
48. Silberzahn, R., Uhlmann, E.L., et al. (2018). Many analysts, one data set. AMPPS 1(3). https://dare.uva.nl/id/0785a9cc-2470-4a3a-bea8-0f34828953c2. Abstract.
49. Breznau, N., Rinke, E.M., Wuttke, A., et al. (2022). Observing many researchers using the same data and hypothesis reveals a hidden universe of uncertainty. PNAS 119(44). https://eprints.whiterose.ac.uk/192743. Abstract.
50. Steegen, S., Tuerlinckx, F., Gelman, A., Vanpaemel, W. (2016). Increasing Transparency Through a Multiverse Analysis. Perspect Psychol Sci 11(5). https://errorstatistics.com/wp-content/uploads/2016/10/steegen-et-al-2016-increasing-transparency.pdf. Full text (extracted).
51. Simonsohn, U., Simmons, J.P., Nelson, L.D. (2020). Specification curve analysis. Nature Human Behaviour 4. https://www.Gwern.net/doc/statistics/meta-analysis/2020-simonsohn.pdf. Full text (extracted).
52. Klein, J.R., Roodman, A. (2005). Blind Analysis in Nuclear and Particle Physics. Annu Rev Nucl Part Sci 55. https://www.Gwern.net/doc/statistics/bias/2005-klein.pdf. Full text (extracted).
53. Roodman, A. (2003). Blind Analysis in Particle Physics. PhyStat2003, arXiv:physics/0312102. https://arxiv.org/abs/physics/0312102. Abstract.
54. Dutilh, G., Sarafoglou, A., Wagenmakers, E.-J. (2021). Flexible yet fair: blinding analyses in experimental psychology. Synthese 198. https://dare.uva.nl/id/b37d9c71-6623-4de9-a022-50915754009e. Abstract.
55. Lakens, D. (2020). Pandemic researchers — recruit your own best critics. Nature 581:121. https://media.nature.com/original/magazine-assets/d41586-020-01392-8/d41586-020-01392-8.pdf. Full text (extracted).
56. Lakens, D., Tiokhin, L. (2020). The Red Team Challenge (Part 3): Is it Feasible in Practice? Blog, The 20% Statistician. https://daniellakens.blogspot.com/2020/07/the-red-team-challenge-part-3-is-it.html. Blog post (primary account by the organisers).
57. Hair, K., Macleod, M.R., Sena, E.S., IICARus Collaboration (2019). A randomised controlled trial of an Intervention to Improve Compliance with the ARRIVE guidelines (IICARus). Research Integrity and Peer Review 4:12. https://pmc.ncbi.nlm.nih.gov/articles/PMC6560728/. Full text.

**Topic 5: software analogy**
58. Just, R., Jalali, D., Inozemtseva, L., Ernst, M.D., Holmes, R., Fraser, G. (2014). Are mutants a valid substitute for real faults in software testing? FSE 2014. https://homes.cs.washington.edu/~mernst/pubs/mutation-effectiveness-fse2014-abstract.html. Abstract (the 73% / 10% / 17% coupling figures come from a search summary of the paper and are not seen on this page).
59. Kanewala, U., Bieman, J.M. (2014). Testing Scientific Software: A Systematic Literature Review. IST 56 (arXiv:1804.01954). https://arxiv.org/abs/1804.01954. Abstract.
60. Segura, S., Fraser, G., Sanchez, A.B., Ruiz-Cortés, A. (2016). A Survey on Metamorphic Testing. IEEE TSE 42(9). https://eprints.whiterose.ac.uk/110335/. Abstract.
61. NIST (n.d.; data last modified 2003). Statistical Reference Datasets: background. https://itl.nist.gov/div898/strd/general/bkground.html. Primary web page.
62. Ralph, P., et al. (2020). Empirical Standards for Software Engineering Research. arXiv:2010.03525. https://arxiv.org/abs/2010.03525. Abstract.
63. Chatterjee, P., Sharma, T., Ralph, P. (2022). Empirical Standards for Repository Mining. arXiv:2203.15950 (MSR tutorial). https://arxiv.org/abs/2203.15950. Abstract.

**Topic 6: defect prediction**
64. El Emam, K., Benlarbi, S., Goel, N., Rai, S.N. (2001). The confounding effect of class size on the validity of object-oriented metrics. IEEE TSE 27(7). https://neverworkintheory.org/2011/07/07/the-confounding-effect-of-class-size-on-the-validity-of-object-oriented-metrics.html. Secondary page quoting the abstract.
65. Herzig, K., Just, S., Zeller, A. (2013). It's Not a Bug, It's a Feature: How Misclassification Impacts Bug Prediction. ICSE 2013. https://2013.icse-conferences.org/content/its-not-bug-its-feature-how-misclassification-impacts-bug-prediction.html. Abstract.
66. Bird, C., Bachmann, A., Aune, E., Duffy, J., Bernstein, A., Filkov, V., Devanbu, P. (2009). Fair and Balanced? Bias in Bug-Fix Datasets. ESEC/FSE 2009. https://www.cs.ucdavis.edu/~filkov/papers/biasbusters.pdf. Abstract (extracted).

**Practitioner repositories** (Section 2.7; opened 2026-11-14; self-descriptions, not evidence)
67. scunning1975/MixtapeTools. https://github.com/scunning1975/MixtapeTools and https://raw.githubusercontent.com/scunning1975/MixtapeTools/main/personas/referee2.md.
68. Orchestra-Research/AI-Research-SKILLs, 22-agent-native-research-artifact. https://github.com/Orchestra-Research/AI-Research-SKILLs/tree/main/22-agent-native-research-artifact and https://raw.githubusercontent.com/Orchestra-Research/AI-Research-SKILLs/main/22-agent-native-research-artifact/rigor-reviewer/SKILL.md.
69. James-Traina/compound-science. https://github.com/James-Traina/compound-science (and the `.evals/` listing).
70. pedrohcgs/claude-code-my-workflow. https://github.com/pedrohcgs/claude-code-my-workflow, https://raw.githubusercontent.com/pedrohcgs/claude-code-my-workflow/main/.claude/skills/vaccinate/SKILL.md and https://raw.githubusercontent.com/pedrohcgs/claude-code-my-workflow/main/quality_reports/qualification/LEDGER.md (first 100k characters read).
71. K-Dense-AI/scientific-agent-skills. https://github.com/K-Dense-AI/scientific-agent-skills (README only).
72. Imbad0202/academic-research-skills. https://github.com/Imbad0202/academic-research-skills.
73. kthorn/research-superpower. https://github.com/kthorn/research-superpower.
74. brycewang-stanford/Auto-Empirical-Research-Skills. https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills.
75. SakanaAI/AI-Scientist. https://github.com/SakanaAI/AI-Scientist.
76. SakanaAI/AI-Scientist-v2. https://github.com/SakanaAI/AI-Scientist-v2.
77. SamuelSchmidgall/AgentLaboratory. https://github.com/SamuelSchmidgall/AgentLaboratory.

**Count: 77 verified sources** (66 literature sources plus 11 repositories). Of the 66 literature sources, about 30 rest on the abstract only, and 3 on a secondary or news page (items 39, 56, 64).

### 5b. Recalled, not verified (search snippets only, or from memory; not used as primary evidence)

1. Votta, L.G. (1993). Does Every Inspection Need a Meeting? FSE '93. Believed to show most defects are found in individual preparation, with an average meeting gain of about 5%.
2. Porter, A., Votta, L., Basili, V. (1995). Comparing detection methods for software requirements inspections: a replicated experiment. IEEE TSE 21(6). Believed: scenario reviewers beat ad hoc and checklist reviewers (48 students, 16 teams).
3. Fusaro, P., Lanubile, F., Visaggio, G. (1997). A replicated experiment to assess requirements inspection techniques. Empirical Software Engineering. Believed: failed to replicate the scenario advantage.
4. Miller, J., Wood, M., Roper, M. (1998). Further experiences with scenarios and checklists. Empirical Software Engineering 3(1). Content not confirmed.
5. Basili, V.R., et al. (1996). The empirical investigation of perspective-based reading. Empirical Software Engineering 1(2). Original PBR study; results seen only as summarised in item 31 above.
6. Eick, S.G., et al. (1992). Estimating software fault content before coding. ICSE. First application of capture–recapture to inspections.
7. Mills, H.D. (1972). On the statistical validation of computer programs. IBM report. Fault seeding; estimator N = S·n/s, assuming seeded faults are as detectable as real ones.
8. Sauer, C., Jeffery, D.R., Land, L., Yetton, P. (2000). The effectiveness of software development technical reviews. IEEE TSE 26(1). The bibliographic record was opened but had no abstract. A snippet says task expertise is the primary driver of review performance.
9. Papadakis, M., Shin, D., Yoo, S., Bae, D.-H. (2018). Are mutation scores correlated with real fault detection? ICSE 2018. Believed: the correlation weakens once test-suite size is controlled, but mutation-score-guided selection still beats random selection at equal size.
10. Chen, Y.T., et al. (2020). Revisiting the relationship between fault detection, test adequacy criteria, and test set size. ASE 2020.
11. Zimmermann, T., Nagappan, N., Gall, H., Giger, E., Murphy, B. (2009). Cross-project defect prediction. ESEC/FSE. 622 predictions; reportedly about 3.4% (21/622) successful.
12. Turner, L., et al. (2012). CONSORT and completeness of reporting of RCTs. Cochrane MR000030. Reported: 25/27 outcomes favour endorsing journals, 5 significant (for example allocation concealment 45% vs 22%).
13. Prasad, V., Jena, A.B. (2013). Prespecified falsification end points: can they validate true observational associations? JAMA 309(3). (The PDF I fetched under this name was a different Prasad et al. paper.)
14. Nosek, B.A., et al. (2018). The preregistration revolution. PNAS.
15. Schuemie, M.J., et al. (2020). How Confident Are We About Observational Findings in Health Care: A Benchmark Study. HDSR 2(1). Snippet: only about half of 95% CIs contained the true effect in most settings.
16. Schuemie, M.J., et al. (2016). Robust empirical calibration of p-values using observational data. Stat Med. Rebuttal to Gruber & Tchetgen Tchetgen.
17. MacCoun, R., Perlmutter, S. (2015). Blind analysis: Hide results to seek the truth. Nature 526:187–189. Paywalled.
18. Golub, R. (2023). Blind analysis in physics experiments: Is this trip necessary? arXiv:2311.13542.
19. Isch, C., Tetlock, P.E., Clark, C.J. (2025). Survey of adversarial-collaboration participants (Theory and Society). Mellers, B., Hertwig, R., Kahneman, D. (2001). Do frequency representations eliminate conjunction effects? An exercise in adversarial collaboration. Psychological Science.
20. Simmons, J.P., Nelson, L.D., Simonsohn, U. (2011). False-positive psychology. Psychological Science. Flexible analysis inflates false positives far above 5%.
21. Shepperd, M., Bowes, D., Hall, T. (2014). Researcher bias: the use of machine learning in software defect prediction. IEEE TSE. Recalled: research group explains more variance in reported results than the technique does.
22. Tantithamthavorn, C., et al. (2015). The impact of mislabelling on the performance and interpretation of defect prediction models. ICSE.
23. Zhou, Y., et al. (2014). An in-depth study of the potentially confounding effect of class size in fault prediction. ACM TOSEM.
24. Fanous, A., et al. (2025). SycEval: Evaluating LLM Sycophancy. arXiv:2502.08177. Snippet: regressive sycophancy in 14.66% of cases.
25. Luo et al. 2025 auditor accuracy of about 82% / F1 0.81 with code access. From a secondary summary only.
26. MixtapeTools "Fletcher" audit (a six-step interrogation of empirical output). Seen only on third-party aggregator pages; not found in the current repository README.

**Count: 26 recalled-only items.**
