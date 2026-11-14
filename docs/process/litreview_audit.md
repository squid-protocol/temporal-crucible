# Audit of `litreview_agents_study_design.md`

Audited version: **502 lines** (the version that includes Section 2.7 on GitHub tooling, 77 "verified" sources, 26 recalled-only items). Audit date 2026-11-14.

## How each source was opened

- **arXiv papers (items 1–23, 42, 43, 53, 59, 62, 63):** abstracts and metadata pulled from the arXiv API. Full-text PDFs downloaded and searched for items 3, 5, 6, 8, 9, 10, 11, 15, 17, 19, 23.
- **PDFs at the review's URLs (items 25, 26, 27, 31, 32, 50, 51, 52, 55, 58, 66):** downloaded, converted to text, searched.
- **PMC and repository/abstract pages (items 24, 28–30, 33–41, 44–49, 54, 56, 57, 60, 61, 64, 65):** fetched through a page-reading tool that returns short verbatim quotes (125 characters maximum) plus a summary. Where I quote these, the quote is verbatim but the surrounding description is the tool's reading, one step removed from the page.
- **GitHub repositories (items 67–77):** the README or named skill file fetched raw and keyword-searched. Spot-check only.
- **Not opened:** three sites refused automated access (HDSR, core.ac.uk, PubMed) and I did not work around the refusals. Affected items are marked.

Statuses: CONFIRMED / CONFIRMED WITH CORRECTION / NOT SUPPORTED BY THE SOURCE / SOURCE NOT FOUND / COULD NOT OPEN.

---

## 1. The ten headline findings

| # | Claim in the review | Source | Status | Evidence |
|---|---|---|---|---|
| 1a | Best model 21.1% recall, 6.1% precision on 91 real errata/retraction-grade errors; "across eight independent runs, models rarely rediscover the same errors" | Son et al. 2025 (SPOT), arXiv:2505.11855, marked "work in progress" | **CONFIRMED** | Abstract: "a dataset of 83 published papers paired with 91 errors significant enough to prompt errata or retraction … none surpasses 21.1% recall or 6.1% precision (o3 achieves the best scores, with all others near zero) … across eight independent runs, models rarely rediscover the same errors". Table 2: o3 precision 6.1 ± 1.3, recall 21.1 ± 4.4, pass@1 18.4, pass@4 37.8. |
| 1b | FLAWS: 39.1% identification at k=10 on 713 inserted errors | Xi et al. 2025, arXiv:2511.21843 (v2 Oct 2026) | **CONFIRMED** | Abstract: "713 paper-error pairs … GPT 5 is the top-performing model, achieving 39.1% identification accuracy when k=10, where k is the number of top-ranked error text candidates". The errors are inserted by LLMs. k=10 means the error is somewhere in the model's ten best guesses. |
| 2a | A multi-layer LLM reviewer caught "over 70% of planted contradictions" but only 16.1% (exact) of real mistakes in withdrawn papers; "all review systems… perform worse on real mistakes than on our benchmark" | Teo et al. 2026, arXiv:2610.11087 (header: published in TMLR 07/2026) | **CONFIRMED WITH CORRECTION** | The 70% applies only to the easiest stratum, with a four-review ensemble. Text: "MLR detects more than 70% of distance 0 contradictions" (distance 0 = contradictions of a main claim). Table 14, same system: distance 0 = 73.43% (4 reviews) or 60.79% (1 review); **whole planted benchmark = 40.95% (4 reviews) or 28.32% (1 review)**. Real errors (Table 3, 211 withdrawn arXiv papers): 26.07% "similar", 16.11% "exact". Correct statement: about 28–41% on planted contradictions overall versus 16–26% on real withdrawn-paper errors. The "all systems perform worse" sentence is in the paper, but its own tables do not bear it out for two of three baselines: AI Reviewer 6.50% planted overall vs 9.00% exact / 13.74% similar on real; AgentReview 5.95% vs 5.69% / 18.48%. The authors also give a second explanation the review omits: the systems are "optimized for machine learning conferences, whereas the papers in WithdrarXiv-Check predominantly come from theoretical mathematics and physics journals". |
| 2b | OHDSI: synthetic positive controls preserve measured but not unmeasured confounding, so calibration may underestimate error | Schuemie et al. 2018, PNAS 115(11) | **CONFIRMED** | "our injection of outcomes to synthesize positive controls can only maintain measured confounding"; "positive controls may have less unmeasured confounding than what exists in reality"; "which could thereby lead to the calibration procedure underestimating the magnitude of systematic error." |
| 3a | "Over 350 LLMs: when two models both err, they pick the same wrong answer 60% of the time"; errors more correlated in more accurate models, even across providers | Kim, Garg, Peng & Garg 2025, ICML, arXiv:2506.07962 | **CONFIRMED WITH CORRECTION** | The 60% is from one of the two leaderboards, with 71 models. Abstract: "on one leaderboard dataset, models agree 60% of the time when both models err". Body: "The mean agreement rate across pairs is 0.423 on HuggingFace and 0.6 on Helm" — HuggingFace is the 349-model set, Helm has 71 models. Chance levels are 0.127 and 1/3. Correct statement: 60% (chance 33%) across 71 models on Helm; 42% (chance 13%) across 349 models on the HuggingFace leaderboard. Multiple-choice questions only. The accuracy/provider sentence is confirmed: "larger and more accurate models have highly correlated errors, even with distinct architectures and providers". |
| 3b | Debate is a martingale; majority voting explains most of the gain; "debate alone does not improve expected correctness" | Choi, Zhu & Li 2025, NeurIPS spotlight, arXiv:2508.17536 | **CONFIRMED** (with an omission) | Abstract: "Majority Voting alone accounts for most of the performance gains typically attributed to MAD … it induces a martingale over agents' belief trajectories, implying that debate alone does not improve expected correctness." Omitted: the next sentence, "targeted interventions, by biasing the belief update toward correction, can meaningfully enhance debate effectiveness"; and that the experiments use Qwen2.5-7B and Llama3.1-8B (a 32B model as a check), on QA benchmarks. |
| 3c | Intrinsic self-correction does not improve reasoning and sometimes hurts | Huang et al. 2024, ICLR, arXiv:2310.01798 | **CONFIRMED** | "LLMs struggle to self-correct their responses without external feedback, and at times, their performance even degrades after self-correction." |
| 4 | Randomized 18-month experiment at Lucent, 88 inspections: 1 reviewer worse than 2, 2 equal to 4; two 2-person teams no better than one. "What drives yield is reading technique and expertise, not head count." | Porter, Siy, Toman & Votta 1997, IEEE TSE 23(6) | **CONFIRMED WITH CORRECTION** | Confirmed: "88 code inspections", "18 months", "pool of 11 experienced software developers", "(1sX1p < 1sX2p, but 1sX2p = 1sX4p)", "two two-person teams weren't more effective than one, two-person team", "reducing the default number of reviewers from four to two may significantly reduce effort without increasing interval or reducing effectiveness". Corrections: (i) "2 = 4" is a failure to detect a difference in observed defect density, on 26 two-person and only 13 four-person single-session inspections (Table 2); the one-person arm was discontinued early. (ii) The "technique and expertise" sentence is not a finding of this paper. The paper says only that "developing better defect detection techniques may be much more important" and offers three untested explanations for 2 = 4 ("maybe better inspection techniques would have found more defects, maybe the code was relatively defect-free, or maybe problems with group interaction…"). Expertise was not tested. It is "88", not "88+". |
| 5 | Capture–recapture models "tend to underestimate"; fewer than four inspectors gives "rather inaccurate estimates"; recommended model Mh with Jackknife | Briand, El Emam, Freimut & Laitenberger 2000, IEEE TSE 26(6) (NRC report copy) | **CONFIRMED** | "the capture-recapture models and their evaluated estimators tend to underestimate the number of defects. In particular, using a small number of inspectors (defined as less than four) will lead to rather inaccurate estimates." "we recommend using a model taking into account that defects have different probabilities of being detected and the corresponding Jackknife estimator." "calibration does not work for two inspectors". The paper is stronger than the review: "for less than four inspectors the capture-recapture models become unusable in practice". It also reports that some estimators "exhibit occasional large overestimation" at two or three inspectors. See over-reach B. |
| 6a | PBR aggregation: "no clear positive effect"; beats ad hoc, loses to checklists; "strong indicators of researcher bias" | Ciolkowski 2009, ESEM (abstract page) | **CONFIRMED** | "there is no clear positive effect of PBR"; "Inspection teams using PBR on requirements documents are more effective when compared to ad-hoc approaches, but are less effective when compared to checklists"; "we found strong indicators of researcher bias". |
| 6b | A replication found no difference between perspectives | Regnell, Runeson & Thelin 2000, ESE 5(4) (repository abstract) | **CONFIRMED** | 30 subjects, 10 per perspective. "there is no significant difference among the three perspectives in terms of defect detection rate"; "no significant difference in the defect coverage". "Rigorous" is the review's word, not the source's. |
| 6c | Fagan: inspectors study "ranked distributions of error types found by recent inspections" plus checklists | Fagan 1976, IBM Systems Journal 15(3) | **CONFIRMED** | "the inspection team should first study the ranked distributions of error types found by recent inspections … Checklists of clues on finding these errors should also be studied." 82% and 4,439 statements (Aetna COBOL) also confirmed. |
| 7a | Uncalibrated designs returned p<0.05 on 50–72% of negative controls | Schuemie et al. 2014, Stat Med 33(2) | **CONFIRMED** (narrower than the wording) | 17/34 (50%), 33/46 (72%), 33/46 (72%); after calibration "2 of 34 (6%), 5 of 46 (11%), and 3 of 46 (5%)". These are replications of two specific published studies (isoniazid/liver injury cohort in MarketScan; sertraline/GI bleeding case-control and SCCS in GE Centricity), not a survey of "standard pipelines". The generalisation is the authors' own claim: "this problem is intrinsic to observational studies in general." They add that calibration comes "most likely at the cost of vastly increasing the number of type II errors." |
| 7b | Standard fMRI cluster inference: up to 70% familywise false positives on real null data; (Section 2.3) "Permutation tests were nominal" | Eklund, Nichols & Knutsson 2016, PNAS 113(28) | **CONFIRMED WITH CORRECTION** | 499 subjects, about 3 million analyses (2,880,000), "false-positive rates of up to 70%" for parametric cluster-wise inference: confirmed. Permutation was nominal for two-sample tests only. For one-sample tests the paper says "they can exhibit conservative or invalid behavior" and "the FWE can be as low as 0.8% or as high as 40%", attributed to asymmetric errors. The article carries a published correction. |
| 7c | Calibration helps when controls share the bias structure; a negative control's zero estimate is "necessary but not sufficient" | Hwang, Quiroz & Gallego 2022, BMC Med Res Methodol 22:208 | **CONFIRMED** | 50,000 subjects, 500 iterations; coverage up in 8 of 10 cases (+1 to +60 points) with suitable controls, +1 to +8 with unsuitable. Source wording: "A null (zero) treatment effect estimate is necessary but insufficient for the negative control to be suitable." The "0.10 to 0.44" CI width is one scenario; the largest calibrated width in Table 4 is 0.62. |
| 8a | 29 teams: odds ratios 0.89–2.93, 69% significant | Silberzahn et al. 2018, AMPPS 1(3) (abstract) | **CONFIRMED** | "Twenty-nine teams involving 61 analysts"; "ranged from 0.89 to 2.93 (Mdn = 1.31) in odds-ratio units"; "Twenty teams (69%) found a statistically significant positive effect." |
| 8b | 73 teams: more than 95% of outcome variance unexplained by coded decisions | Breznau et al. 2022, PNAS 119(44) (abstract) | **CONFIRMED** | "We coordinated 161 researchers in 73 research teams"; "More than 95% of the total variance in numerical results remains unexplained". |
| 8c | LLM analysts on a fixed dataset and hypothesis disagree; model or persona shifts the distribution | Bertran, Fogliato & Wu 2026, arXiv:2602.18710 (preprint) | **CONFIRMED** | "substantial dispersion in effect sizes, p-values, and conclusions"; "reassigning the analyst persona or LLM shifts the distribution of results even among methodologically sound runs." "Larger than reviewers expect" in the headline is not in any of the three sources. |
| 9a | Physics blinding: hidden box, hidden offset, hidden fraction; unblinding decided by wider review "and not by the data analysts alone"; post-unblinding changes reported; evidence that blinding reduces bias is "at least circumstantial (Klein & Roodman's own words)" | Klein & Roodman 2005, Annu. Rev. Nucl. Part. Sci. 55 | **CONFIRMED WITH CORRECTION** | Methods, "as simply and narrowly as possible", event-by-event caveat, "solve only one problem": confirmed. Two corrections. (i) The "circumstantial" quote is about something else: "There is at least circumstantial evidence that such a bias has affected past measurements". It is evidence that experimenter's bias exists, not that blinding reduces it. The paper offers no evidence on whether blinding reduces bias. (ii) The source is permissive, not prescriptive: "Collaborations can require that the decision to unblind a result be made as a part of the internal review process … and not by the data analysts alone"; "One useful principle that may be adopted is that the publication simply describe the full analysis procedure". |
| 9b | In psychology a separate data manager hides outcomes from the analyst | Dutilh, Sarafoglou & Wagenmakers 2021, Synthese 198 | **CONFIRMED WITH CORRECTION** | The review cites the abstract, and the abstract does not mention a data manager. It says only "blinded analyses break the feedback loop between the analysis plan and analysis outcome" and "retain the flexibility to account for unexpected peculiarities in the data". The claim is true of the paper: the authors' own summary page describes "a data manager who blinds the data and an analyst who designs the analyses". Springer full text was not reachable; confirmation is from that page. |
| 10a | Large NHLBI trials: 57% positive before 2000, 8% after; associational | Kaplan & Irvin 2015, PLoS ONE 10(8) | **CONFIRMED** | 17 of 30 (57%) vs 2 of 25 (8%). "We cannot say that trend toward null trials to preregistration in ClinicalTrials.gov is causal." |
| 10b | Registered Reports 44% positive vs 96% standard | Scheel, Schijen & Lakens 2021 (record page) | **CONFIRMED** | "96% positive results in standard reports, but only 44% positive results in Registered Reports"; 152 and 71; first hypothesis only. |
| 10c | 24 of 27 preregistered studies had at least one undisclosed deviation | Claesen et al. 2021, R Soc Open Sci 8:211037 | **CONFIRMED** | 27 studies from 16 *Psychological Science* articles: 2 none, 1 all disclosed, 24 (89%) at least one undisclosed. Omitted context: ambiguous cases were coded as no deviation; 9 of 25 disclosed none of their deviations (so most disclosed some); "Deviations from a preregistered plan do not constitute evidence of exploited researcher degrees of freedom." |
| 10d | ARRIVE checklist request produced no full-compliance gain "in a 1,689-manuscript RCT" | Hair, Macleod, Sena & IICARus 2019, Res Integr Peer Rev 4:12 | **CONFIRMED WITH CORRECTION** | 1,689 were randomised, but the outcome was measured on 672 accepted manuscripts: "Of the remaining 1269 manuscripts, 672 were accepted for publication (340 control, 332 intervention)". The abstract's "762" contradicts its own arm counts. Full compliance was zero in both arms ("No manuscript achieved full compliance"), so the primary outcome could not move. Median 36.8% (control) vs 39.5% (intervention); one sub-item (9b) improved. The trial tested a request, as the review says: "PLOS ONE did not fully mandate checklist completion". It contains no arm in which enforcement was tried. |

**Headline conclusions versus sources.** Findings 1, 5, 7, 8 and 10 are supported as measurements. For findings 2, 3, 4, 6 and 9 the numbers are in the sources, but the conclusion drawn for the team is wider than what was measured: see Section 4.

---

## 2. All other "verified" literature sources (in order of the review's list)

| # | Source | Status | Note |
|---|---|---|---|
| 1 | Lu et al. 2024, AI Scientist | CONFIRMED | "less than $15 per paper"; "near-human performance in evaluating paper scores"; "as judged by our automated reviewer". |
| 2 | Yamada et al. 2025, AI Scientist-v2 | CONFIRMED | Three manuscripts to an ICLR workshop; one exceeded "the average human acceptance threshold". |
| 3 | Schmidgall et al. 2025, Agent Laboratory | CONFIRMED WITH CORRECTION | The quoted words "meaningfully improved" do not occur anywhere in the paper (v2 full text searched). The abstract says human feedback "significantly improves the overall quality of research". o1-preview claim confirmed. |
| 4 | Gottweis et al. 2025, AI co-scientist | CONFIRMED | Current arXiv v2 is retitled "Accelerating scientific discovery with Co-Scientist" and marked Nature (2026). Claims match the abstract. |
| 5 | Beel, Kan & Baumgart 2025 | CONFIRMED | "five out of twelve proposed experiments (42%) failed"; 8% more characters; median five citations, five of 34 from 2020 or later; 3.5 hours. |
| 6 | Luo, Kasirzadeh & Shah 2025 | CONFIRMED WITH CORRECTION | The two phrases in quotation marks are paraphrases. Abstract: "which can be easily overlooked in practice" and "enables far more effective detection of such failures than examining the final paper alone". Four failure modes confirmed. The "unverified" 82% / F1 0.81 is in the paper: paper only "accuracy 55%, F1 score 0.51"; with logs and code "accuracy 82%, F1 score 0.81". The detector is an LLM-based classifier. |
| 7 | Starace et al. 2025, PaperBench | CONFIRMED | 20 ICML 2024 Spotlight/Oral papers, 8,316 tasks, 21.0%; human baseline was on a subset. |
| 11 | Jiang et al. 2025, BadScientist | CONFIRMED | "acceptance rates up to 82.0%" (one strategy at one threshold; 67.0% at the other); o4-mini concern-acceptance conflict 100% for s1, s3 and All; detection "near the 50% random baseline". ACL 2026 per arXiv comment. |
| 12 | Liang et al. 2023 | CONFIRMED | 30.85% / 39.23% vs 28.58% / 35.25%; 3,096 and 1,709 papers; larger overlap for weaker papers. |
| 13 | Shin et al. 2025 | CONFIRMED | 676 reviews, 3,657 strengths and weaknesses; "significantly overlooking novelty assessment when criticizing papers". |
| 14 | Zhu et al. 2025 | CONFIRMED | GPT-5-mini; inflated ratings for weaker papers; field-specific instructions manipulate reviews. |
| 15 | Wang et al. 2026 | CONFIRMED | "81% of papers received a higher score … while not a single score was revised downwards"; figure caption says 89%. 100 papers (25 per decision category), Gemini 2.5 and GPT 5.1. The review reports the 81/89 discrepancy honestly. |
| 18 | Liu et al. 2026 | CONFIRMED | "standard MAD cannot improve belief correctness beyond majority voting"; peer-prediction mechanism; preprint. |
| 20 | Panickssery, Bowman & Feng 2024 | CONFIRMED | The linear correlation was found after fine-tuning. The NeurIPS 2024 venue is not on the arXiv record; recollection agrees. |
| 21 | D'Arcy et al. 2024, MARG | CONFIRMED | 60% to 29%; 1.7 to 3.7 good comments; user study. |
| 22 | Du et al. 2025, CausalPitfalls | CONFIRMED | "significant limitations"; no headline number in the abstract, as the review says. |
| 24 | Bornmann, Mutz & Daniel 2010 | CONFIRMED | 48 studies, 19,443 manuscripts, "mean ICC/r2 = .34", "mean Cohen's Kappa = .17". |
| 28 | Petersson et al. 2004 | CONFIRMED | "most software engineering research is performed on evaluation"; "a majority ending up in recommendation of the Mh-JK model"; "there is a need for application experiences"; decision points mentioned. |
| 31 | Fabbri, Shull, Carver et al., Readers Project report | CONFIRMED | p = 0.143 and 0.911 (R1); 0.063 and 0.659 (R1+R2); perspective p = 0.654. Not mentioned: the pooled efficiency comparison on one document has p = 0.026, which the report itself calls not significant. |
| 32 | Rigby & Bird 2013 | CONFIRMED | "The consensus seems to be that two inspectors find an optimal number of defects"; "Two reviewers involved in review in the median case". The file at the URL is a truncated course copy but contains these passages. |
| 33 | Chillarege et al. 1992, ODC | CONFIRMED | Type: "representing the semantics of the fix". Trigger: "a condition that allows a defect to surface". |
| 34 | Lipsitch et al. 2010 | CONFIRMED | "U-comparable"; "a sensitive, but blunt, tool to probe the credibility of a study"; "Subject matter knowledge is required for the choice of negative controls." |
| 38 | Gruber & Tchetgen Tchetgen 2016 | CONFIRMED | "can be conservative"; "under more extreme departures, it can be anti-conservative"; "its adoption for routine use in studies of real-world health care datasets is premature." |
| 39 | OHDSI news page | CONFIRMED | "are falling short of expected confidence levels"; self-controlled designs "performed best in many scenarios". No numbers on the page, as stated. |
| 40 | Franklin et al. 2014 | CONFIRMED | HR 1.0 and 1.5; 500 × 100,000; 88% and 70%; 1.40 (1.33–1.48) at true 1.5. |
| 41 | Morris, White & Crowther 2019 | CONFIRMED | "93 did not mention Monte Carlo SEs"; "Of the 87 studies reporting n_sim, four provided any justification". |
| 42 | Talts et al. 2018, SBC | CONFIRMED WITH CORRECTION | Marked "abstract only", but the abstract does not say what the review attributes to it. It contains nothing about simulating from the prior or rank uniformity; it says only that SBC is "a general procedure for validating inferences from Bayesian algorithms capable of generating posterior samples". The description is from memory of the paper (recollection agrees), not from the abstract. |
| 43 | Gelman et al. 2020 | CONFIRMED | The review correctly says the abstract does not mention fake-data checking. |
| 50 | Steegen et al. 2016 | CONFIRMED | "7 out of the 120 choice combinations" in one example. |
| 51 | Simonsohn, Simmons & Nelson 2020 | CONFIRMED | Three steps; "one finding is robust, one is weak and one is not robust at all." |
| 53 | Roodman 2003 | CONFIRMED | Abstract only; nothing specific is claimed. |
| 55 | Lakens 2020, Nature | CONFIRMED | "This shows that assembling a red team isn't enough". The review's wording slightly distorts the anecdote: Lakens was the journal reviewer and repeated criticisms the red team had already made and the authors had "opted to ignore". |
| 56 | Lakens & Tiokhin 2020 blog | CONFIRMED | Five members, three weeks, "107 error reports", "18 unique critical issues" (19 elsewhere), "5 major errors". |
| 58 | Just et al. 2014 | CONFIRMED | 357 faults, 5 applications, 321,000 lines; correlation "independently of code coverage". The 73% / 10% / 17% figures, which the review took from a search summary, are in the paper's contribution list ("for 73% of real faults", "10%", "17% of real faults are not coupled to mutants"). |
| 59 | Kanewala & Bieman 2014 | CONFIRMED | 62 studies; oracle problems and cultural differences. |
| 60 | Segura et al. 2016 | CONFIRMED | Abstract describes transforming an input and observing the output; "oracle problem" is in the keywords. |
| 61 | NIST StRD background page | CONFIRMED WITH CORRECTION | The words in quotation marks are not on the page. Actual: "producing correct results for all datasets in this collection does not imply that your software will do the same for your particular dataset." Same meaning. |
| 62 | Ralph et al. 2020 | CONFIRMED | "living documents". |
| 63 | Chatterjee, Sharma & Ralph 2022 | CONFIRMED | Tutorial presenting the repository-mining standard. |
| 64 | El Emam et al. 2001 (secondary page) | CONFIRMED | "After controlling for size, none of the metrics we studied were associated with fault-proneness any more"; "a strong size confounding effect". One C++ telecom system; "all association" means "all metrics studied". |
| 65 | Herzig, Just & Zeller 2013 | CONFIRMED | More than 7,000 reports, 33.8%, 39%; five projects. |
| 66 | Bird et al. 2009 | CONFIRMED | "find strong evidence of systematic bias". |

Items 8–10, 16, 17, 19, 23, 25–27, 29, 30, 35–37, 44–49, 52, 54, 57 are in the headline table.

### Abstract-only claims where the abstract does not contain the claim

- Item 3 (Agent Laboratory): the quoted phrase.
- Item 6 (Luo): both quoted phrases are paraphrases.
- Item 42 (Talts): the mechanism described.
- Item 54 (Dutilh): the data manager.
- Item 19 (Kim): the abstract restricts the 60% to "one leaderboard dataset"; the review dropped the restriction.
- Item 5 (Beel): "twelve experiments" is not in the arXiv abstract but is in the paper. Fine.

### GitHub repositories (items 67–77), spot-checked

Each README or skill file was fetched and searched for the specific claims.

- **pedrohcgs/claude-code-my-workflow: confirmed.** `/vaccinate`: "an unqualified check is not weak evidence — it is none"; "At least one clean control". Ledger: a "Not yet qualified" section says these "are relied upon and have **never been measured**" and lists `/review-paper --pe…` and "the 18-agent review fleet"; "No skill in this template has been eval'd"; rows with 8/8, 3/4 FAIL then fixed, 10/10. README: "decompose, independent skeptics, a separate judge per finding, fix, re-verify"; "loop-until-dry"; `review-fencing`; `--variance N`.
- **scunning1975/MixtapeTools: confirmed.** "by a Claude instance that has never seen the work"; "You NEVER Modify Author Code"; "Point estimates must match to 6+ decimal places"; "Hallucination errors are likely orthogonal across LLM-produced code in different languages" (asserted, no data). README does reference `skills/referee2/`; I did not check the file tree.
- **Imbad0202/academic-research-skills: confirmed.** "Current live reviews remain `NOT_CALIBRATED`"; stub judge; "flagged 15 problem references"; "21 of the 68 final references still had problems after 3 rounds of integrity checks"; "7-agent".
- **Orchestra-Research rigor-reviewer: confirmed** (six dimensions, falsifiability).
- **James-Traina/compound-science: confirmed** for the four parallel review agents, the 0.60 cutoff and "what would change my mind". "237 structural tests" was not found in the current README.
- **SakanaAI/AI-Scientist, AI-Scientist-v2, AgentLaboratory, kthorn: confirmed** (`num_reflections=5`, `num_reviews_ensemble=5`, `temperature=0.1`; `--model_review`, `max_debug_depth`; co-pilot mode; "Parallel screening for large searches").
- **brycewang-stanford: partly confirmed.** Found 1,151 skills, 19 benchmark tasks with "gold values recomputed from real data each run", 42 evaluation scenarios, and "17 … 37" in the Chinese text (so the 17/37 vs 19/42 inconsistency is real). "23,000+" was not found in the current README.
- **K-Dense-AI: not confirmed as worded.** The current README describes these areas in prose ("power analysis, and experimental design", "critical thinking", "peer review") but the four skill names the review lists do not appear as such.

Repositories change daily; "not found" here means not in the README as fetched today.

---

## 3. Recalled-only items checked

| Item | Opened? | What it actually says |
|---|---|---|
| **Papadakis, Shin, Yoo & Bae 2018 (ICSE)** | **COULD NOT OPEN** the paper or publisher abstract (core.ac.uk and IEEE refused or returned empty; the Luxembourg repository had a certificate error). Bibliographic record confirmed (ICSE 2018, pp. 537–548). | From search-result excerpts of the abstract only: earlier correlations "are the results of the confounding effects of the test suite size"; "all correlations between mutation scores and real fault detection are weak when controlling for test suite size"; but against random suites of the same size, "achieving higher mutation scores improves significantly the fault detection". The review's recollection matches these excerpts. Still unverified at source. One search hit (an arXiv 2026 replication on LLM-generated suites) reports correlations that stay moderate to strong after controlling for size, so the point is disputed. |
| **Zimmermann et al. 2009 (ESEC/FSE)** | **Opened** (author's PDF). | **Confirmed.** "For 12 real-world applications, we ran 622 cross-project predictions." "Out of the 622 non-trivial cross-project combinations, only 21 had precision, recall, and accuracy values which satisfied our criteria; an alarmingly low success rate of 3.4%." Success means all three above 0.75. Full title: "Cross-project defect prediction: a large scale experiment on data vs. domain vs. process". |
| **Votta 1993** | **COULD NOT OPEN** the paper. | Confirmed through two papers by the same group that I did open. Porter et al. 1997: "These meeting gain rates are higher than those reported by Votta [23] (5 percent)". That same paper found **30%** meeting gains in code inspections and says Votta's study "focused on design inspections". So "about 5%" is right for Votta 1993, but it is contradicted by the review's own item 26, which the review does not mention. |
| **Porter, Votta & Basili 1995** | **COULD NOT OPEN** the paper (the UMD record has no abstract; the PDF copy returned nothing readable). | Search excerpt of the IEEE abstract: 48 graduate students, sixteen three-person teams; Scenario had a higher detection rate than Ad Hoc or Checklist; Checklist no better than Ad Hoc; collection meetings gave no net improvement. The authors' own later summary (Porter & Votta, IEEE Software Nov/Dec 1997, opened) describes the experiment plus its replication as "48 graduate students in computer science and 21 professional software developers" in 23 three-member teams. Recollection in the review agrees. Note that the Readers Project report (item 31) labels the PBR original as "[Porter1995]", which invites confusing the two studies. |
| **Turner et al. 2012 (Cochrane MR000030)** | **Opened** the Cochrane summary page (PubMed refused). | **Confirmed.** 50 evaluations, 16,604 RCTs. "Twenty-five of 27 outcomes assessing completeness of reporting in RCTs appeared to favour CONSORT-endorsing journals", five significant. "Allocation concealment was reported adequately in 45% (393/876) of RCTs in CONSORT-endorsing journals" vs 22% (329/1520). "None of the evaluations included in this review used experimental designs." |
| **Prasad & Jena 2013 (JAMA 309(3):241–2)** | **COULD NOT OPEN** (no abstract on PubMed; the PDF at the URL the review tried is a different Prasad paper, as the review says). | From quotations on a secondary page: "A falsification hypothesis is a claim, distinct from the one being tested, that researchers believe is highly unlikely" to be causally related; "falsification analysis is not a perfect tool for validating the associations in observational studies". A Viewpoint, not a study. |
| **Schuemie et al. 2020 (HDSR benchmark)** | Abstract opened via a bibliographic API (the HDSR site refused). | **Confirmed for the abstract.** "in most contexts, only half of the 95% confidence intervals we calculated contain the corresponding true effect size." Four databases; five designs; "self-controlled methods such as the empirically calibrated self-controlled case series perform well across a wide range of scenarios." Per-design coverage tables, and coverage on synthetic versus real positive controls, were not opened. |
| Luo 2025 auditor 82% / F1 0.81 | Opened (full text). | Confirmed; see item 6. It can move to the verified list. |
| Fanous et al. 2025, SycEval | Opened (abstract). | Confirmed: regressive sycophancy "was observed in 14.66%". |
| Golub 2023 | Opened (abstract). | The abstract says only "we present an alternate conclusion as to the charm of blind analysis". It does not state that blinding is unnecessary; the review's "disputes that blinding is necessary" is an inference from the title. |
| Sauer et al. 2000 | Record only, no abstract. | Not verified. |
| Others (Fusaro, Miller, Basili 1996, Eick, Mills, Chen 2020, Nosek, Schuemie 2016, MacCoun & Perlmutter, Isch, Simmons, Shepperd, Tantithamthavorn, Zhou, "Fletcher") | Not checked. | — |

---

## 4. Over-reaches

**A. Results on LLMs reviewing papers carried over to LLMs reviewing study designs.**
The review says plainly (line 29, Section 4) that no study covers design review. But Section 3.3 then uses "LLM per-run recall is about 20–40%" as a design parameter. That range mixes three different things: 21% recall on real errors in published papers (SPOT), 39% for a top-10 candidate list on LLM-inserted errors (FLAWS), and 28% for one review on planted contradictions (Teo). None concerns a design document, where there is no fixed list of true errors and "blocker" is a judgement.

**A2. Finding 1's inference ignores the precision figure in its own source.**
The review reads "each review finds new blockers and the rate does not fall" as "a large pool of faults sampled with low probability" and adds "it does not mean the reviews are failing". SPOT's best precision is 6.1%: roughly 94 of every 100 things the best model flagged were not the real error. A reviewer with that precision will produce new, non-overlapping "blockers" indefinitely whether or not real faults remain. The team's pattern fits that explanation equally well, and the sources cannot separate the two. This is the most consequential over-reach, because the stopping rule, the capture–recapture estimate and the "do not stop" advice all depend on it.

**B. The capture–recapture estimate applied to the team's numbers.**
Arithmetic is right (Lincoln–Petersen 12.5, Chapman 11, 8 distinct found). Problems:
1. The cited source says the method is "unusable in practice" below four inspectors, and that calibration "does not work for two inspectors". The headline table presents a two-reviewer estimate anyway.
2. "Treat this as a floor" is not what Briand shows. Underestimation is the tendency, but the paper reports "occasional large overestimation" for some estimators at two or three inspectors.
3. The "floor" argument assumes positive dependence between reviewers. Two things in the review's own plan push the other way. Role-specialised reviewers (Section 3.2) are designed to find different things, which lowers overlap and inflates the estimate. False positives are rarely shared between reviewers, so any unverified "blocker" in the lists also inflates it.
4. Briand's data are human inspectors on requirements documents with a known defect count. Nothing in any source tests the estimator on LLM reviewers. The review admits this in Section 4 item 3, but the headline row gives "at least 3–5 remain" without that caveat.

**C. "Rounds of k ≥ 4 independent, mixed-vendor reviewers".**
- The "4" comes from Briand, where it is the point at which a statistical estimator becomes usable for humans. It is not a finding about how many reviews are needed to find faults.
- The direction (more than two runs) does have support the review did not use: SPOT's pass@1 of 18.4% rises to 37.8% at pass@4, and Teo's Figure 28 shows gains from 1 to 6 reviews.
- "Mixed-vendor" has no direct support. Kim et al. say strong models' errors are highly correlated "even with distinct architectures and providers". The review's gloss "diversity reduces, but does not remove, correlation" is a fair reading of the regression, but no source measures whether mixing vendors raises the number of real faults found in a critique task.
- Finding 4 (two humans equal four) is set aside for LLMs on the strength of finding 1. That is reasonable, but it means the "how many" recommendation rests on no direct evidence at all.

**D. Presented as settled; the source is one study or contested.**
- **"Planted errors are much easier to catch than real ones" (finding 2, "High, two independent fields agree").** With the correct numbers the gap is about 28–41% versus 16–26% for one system, in one paper, with a domain shift between the two test sets, and with two of three baselines doing as well or better on the real errors. The OHDSI point is an authors' caveat about unmeasured confounding, not a measurement that injected effects are easier to detect. "High" confidence is not warranted; "plausible, one study plus a stated limitation" is.
- **"Debate does not fix it" (finding 3).** One paper, small open models, QA benchmarks. The same paper reports that a modified debate does help.
- **"Two reviewers caught as many defects as four" (finding 4).** One experiment, one project, 13 four-person inspections. The review says "one strong RCT plus practice" in the body; the headline says "High".
- **"Checklists help only when enforced" (finding 10).** Hair shows a request did nothing measurable. No cited source shows that enforcement works; Hair's authors say checks "may be required". The recalled Cochrane review points mildly the other way (journal endorsement associated with better reporting, observationally).
- **"Blinding works when…" (finding 9).** The source gives practice and argument. The one phrase offered as evidence of effect is misattributed (see 9a).
- **"Standard pipelines often fail their own nulls" (finding 7).** Rests on three analyses replicating two drug studies and on one fMRI method family. The HDSR benchmark abstract (recalled item, now confirmed) is better support and should be the citation.
- **Section 3.7, "LLMs … flag concerns without acting on them".** From one paper (BadScientist) on fabricated ML papers with three OpenAI models.

**E. Smaller inferential steps.**
- Section 3.2: "Luo 2025: auditing traces beats reading the paper" is used to require code and logs for *design* review. Luo tested detection of four specific planted pitfalls in AI-scientist runs by an LLM classifier (55% to 82% accuracy).
- Section 2.3: "the null must be real data with no effect, not idealised noise" is the review's own gloss on Eklund, reasonable but not a quoted conclusion.
- Section 2.5 metamorphic relations: "duplicating a repository halves the SE" is wrong as arithmetic (duplicating independent data shrinks the SE by about 1/√2, about 29%) and is not from any source.

---

## 5. Omissions and softenings

1. **Teo et al. report a yield-versus-panel-size curve.** Appendix B.1, Figure 28: ensembles of 1 to 6 reviews; "the largest increase in accuracy across most node distances occurs when ensembling 2 reviews instead of 1 … increasing the number of ensembles continues to improve the system's performance in detecting contradictions, without plateauing." The review says no study measures "whether yield plateaus" (true for designs) and asks in Section 4 for exactly this kind of curve, while its own source contains one for planted paper errors.
2. **SPOT's pass@K figures** (18.4% at one run, 37.8% within four) are the most direct evidence for running several reviews. Not mentioned.
3. **Teo's alternative explanation** for the planted/real gap (domain mismatch) and the baselines that did not do worse on real errors. Omitted; the gap is presented as clean.
4. **Choi et al.: targeted debate interventions help.** Omitted. Cuts against "aggregate by union … not by debate" as a settled rule.
5. **Eklund: the one-sample permutation test was itself invalid on some real null data (up to 40%).** Softened to "permutation tests were nominal". The accurate version makes the review's own point (validate every check on real nulls) more strongly, but it also shows that a permuted-outcome null check, which Section 3.5 recommends, can be wrong.
6. **Porter 1997: 30% of defects were meeting gains**, against Votta's 5%. The review cites only the 5% (recalled) and recommends that no reviewer sees another's output. Also from the same group (Porter & Votta 1997, not in the review): only 3% of the variation in effectiveness was explained by process structure, 50% by the code and the reviewers.
7. **Schuemie 2014: calibration "most likely at the cost of vastly increasing the number of type II errors"**, in the authors' own words. The review attributes the power cost only to the critics (Gruber).
8. **Hwang 2022: calibration reduced bias in only 8 of 10 suitable-control cases, and null-only calibration lowered coverage in 9 of 10.** The second matters because Section 3.5 recommends fitting an empirical null from negative controls alone.
9. **Claesen: deviations are not evidence of misconduct, and ambiguous cases were scored in the authors' favour.** Section 3.1 item 10 says deviations are "almost always undisclosed"; the source says at least one was undisclosed in 89% of studies, while most studies disclosed some.
10. **Liang 2023: 57.4% of users found GPT-4 feedback helpful and 82.4% found it more beneficial than at least some human reviewers.** Omitted; the review uses the paper only for the low-bar point.
11. **Klein & Roodman: "in our opinion blind analyses prevent experimenter's bias much more directly than redundant analyses"** is reported as guidance without "in our opinion".

---

## 6. Totals

| | Checked | Confirmed | Confirmed with correction | Not supported | Not found | Could not open |
|---|---|---|---|---|---|---|
| Headline sources (24 distinct) | 24 | 17 | 7 (Teo, Kim, Porter, Eklund, Klein & Roodman, Dutilh, Hair) | 0 | 0 | 0 |
| Other verified literature (42) | 42 | 38 | 4 (Schmidgall, Luo, Talts, NIST) | 0 | 0 | 0 |
| **All 66 literature sources** | **66** | **55** | **11** | **0** | **0** | **0** |
| GitHub repositories (spot check) | 11 | 9 | 2 partly (K-Dense skill names; brycewang "23,000+"; also compound-science "237") | 0 | 0 | 0 |
| Recalled-only items | 10 checked of 26 | 5 at source (Zimmermann, Turner, HDSR abstract, Luo figure, SycEval) | 1 (Golub: abstract does not say what is attributed) | 0 | 0 | 4 at source (Papadakis, Votta, Porter–Votta–Basili, Prasad & Jena); secondary evidence agrees with the review for all four |

No source is invented; every one exists with the stated authors and year. No number is fabricated. Within sources marked "confirmed with correction", individual claims that the source does not support are:

- "over 70% of planted contradictions" as a benchmark-wide figure (Teo);
- "over 350 LLMs … 60%" (Kim);
- "what drives yield is reading technique and expertise" as a finding (Porter);
- "permutation tests were nominal" without qualification (Eklund);
- "at least circumstantial" as evidence that blinding reduces bias (Klein & Roodman);
- "1,689-manuscript" as the analysed sample (Hair);
- four phrases in quotation marks that are not verbatim (Schmidgall; Luo twice; NIST).

Limits of this audit: PMC and abstract pages were read through a tool that returns short quotes, so table cells built from those are verbatim only inside the quotation marks. Rigby & Bird was checked on a truncated copy. Dutilh's full text and the full Ciolkowski, Petersson, Regnell, Gruber, Silberzahn, Breznau and Scheel papers were not opened beyond the abstract, the same level as the review.

---

## 7. Judgement

**Can be relied on as they stand.**
- Validate every null check and positive control on simulated and real nulls before trusting it (Section 3.1 slots 4–6, Section 3.5), with one amendment: permutation nulls need validating too.
- Synthetic positive controls preserve only measured confounding.
- Negative controls need a written comparability argument and subject-matter judgement.
- A multiverse or specification slot.
- A computed deviation log.
- A blinding plan with a separate key-holder, as practice.
- Do not trust reviewer scores, and do not let authors argue a blocker away.
- Give reviewers code and logs.
- The domain threats in Section 2.6.
- The observation that nobody, in the literature or in the repositories, has measured multi-agent review of study designs.

**Need rewording.**
- Finding 2: about 28–41% planted versus 16–26% real, one study, confounded by domain; drop "High".
- Finding 3: 60% on one 71-model leaderboard, 42% on the 349-model one; debate result is for small models on QA and has a stated exception.
- Finding 4: "no difference detected", one project, and the technique/expertise sentence attributed elsewhere or removed.
- Finding 7: permutation was not always nominal.
- Finding 9: remove the "circumstantial" attribution and say there is no cited evidence that blinding reduces bias.
- Finding 10: "a request did nothing measurable among 672 assessed manuscripts"; "only when enforced" is a hypothesis.
- Section 3.3: the 20–40% recall figure should be labelled as coming from paper-error benchmarks; cite the SPOT and Teo multi-run data, not Briand, for "more than two".
- Fix the four non-verbatim quotations and the Talts and Dutilh "abstract" attributions.

**Should be dropped or demoted to an explicit untested proposal.**
- The capture–recapture estimate of "at least 3–5 remaining blockers" from two reviewers, and its description as a floor.
- The Mh-Jackknife stopping rule ("stop when estimated remaining falls below 1") as anything more than an experiment to run. Its source calls the method unusable below four human inspectors. It has never been applied to LLM reviewers. It assumes every listed blocker is real, when the review's best source puts LLM precision at 6%.
- The sentence in finding 1 that the team's pattern "does not mean the reviews are failing". The evidence cannot distinguish a deep pool of real faults from a steady stream of false positives. The only way to tell them apart is the seeded-flaw calibration the review proposes in Section 3.4, which should therefore come before any stopping rule.
