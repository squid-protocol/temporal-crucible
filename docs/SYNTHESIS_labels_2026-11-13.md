# What we learned about our labels, 2026-11-13

One day, one question — *are our fix labels good enough?* — followed to the end. This is the arc, the
numbers, and the lessons, in order.

## The arc

**1. We had never measured recall.** Every audit in the programme measured precision: of the commits we call
fixes, how many are real. Nobody had asked the other half.

**2. Precision, per repo, is wildly uneven** — 0.27 to 0.86 on the raw keyword gate. Worst: commons-lang at
**0.27**, where nearly three in four "fix" commits are Javadoc, checkstyle, formatting. That repo carried the
largest effect in HR-1.

**3. Cleaning the label (FIXLIKE v3c) looked like a clear win** — precision 0.70–0.86 on 9 of 11 repos — and
it reversed the headline result. HR-1's pooled lift fell from **+0.082 [+0.039, +0.125]** to **+0.009
[−0.011, +0.029]**, and commons-lang flipped from +0.143 to −0.015.

**4. Then we measured recall, and it is bad.** curl **0.41**, commons-lang **0.26**. The keyword gate misses
most real fixes — and misses them by *writing style*. The missed ones are concrete: a Coverity NULL deref, an
ignored return value, a busy-loop, a library adaptation. None says "fix" in the subject.

**5. An external benchmark put us in our place.** Scored against 35,167 commits with manually validated
positives **and negatives** (König et al.), our keyword gate gets **F1 0.402** against their stemming
baseline's 0.396 — the same thing. Every LLM in their table beats every keyword method. And **v3c, our
"improvement", scores 0.354 — worse than the baseline we started from**, because it buys precision at a
brutal recall cost. We could not have learned that from inside our own data; we only ever measured the half
it improves.

**6. The literature says our numbers are the published numbers.** Keyword matching scores recall 0.394 /
precision 0.436 on 34 validated projects. We are not broken; the method is.

**7. A cascade label recovers some recall** — rank revert links, `Fixes #N`, CVE ids above the keyword gate.
curl gains 1,930 high-confidence fixes the keyword gate never saw (+54%), sphinx +69%. But auditing it
immediately caught an error: treating *any* issue reference as evidence labelled 14,376 curl commits, and
only ~2 of 9 sampled were real fixes, because curl writes `Closes #N` on every merged PR. Splitting
fix-semantic verbs from bare references collapsed that tier to 2,013.

**8. A quantitative bias analysis changed what "significant" means here.** Simulating a null where fixes land
by size alone, and the only mechanism is that some units announce more than others, the manufactured lift is
**frequently positive**. For libxml2 and sphinx the null *median* lift is +0.157 and +0.142. **A small
positive lift is the expected output of this measurement under no effect at all** — so reporting "+0.02,
interval excludes zero" against a **zero** null was the wrong comparison all along.

**9. Author variation dominates file variation.** Announcement spread between authors exceeds spread between
files in every repo, by 1.5× to 4×. Some curl contributors with 15–22 commits announce at **0.00**.

**10. Where it lands.** At each repo's honest (author + file) spread, **only curl's effect exceeds its own
null** (+0.071 against a null max of +0.061). On libxml2, postgres and sphinx the *original raw* lifts sit
**below their own null medians** — smaller than what noise alone manufactures. And curl's spread (0.91) is
mid-range, so curl does not win by labelling tidily; it wins by having a larger effect.

## Standing, as of today

| claim | status |
|---|---|
| LAW-2 preferential attachment (8/8, coverage-robust) | **solid** — no fix label involved |
| LAW-5 decay contradicted (7/8) | **solid** — no fix label involved |
| LAW-3 / LAW-4 instrument-dominated | **solid** (negatives) |
| Label precision 0.27–0.86; recall 0.41/0.26 | **solid**, externally confirmed |
| "recidivism beats size" on **curl** | **holds**, at a ~1.2× margin on announcement spread |
| the same on the CGR eight | **does not hold**; several raw lifts are below their own nulls |
| "replicated on curl + nDPI, p<1e-4" | curl half defended; **nDPI half still unrun** |
| any pooled cross-repo lift | **not supported** — per-repo nulls differ by an order of magnitude |

## Lessons

**Measure both halves or you will celebrate a net loss.** v3c improved precision, and we declared it better.
Scored on precision *and* recall against external truth it is the worst of our three labellers.

**Self-validation is not validation.** Every number we generated ourselves looked better than the external
score. The audit that would have flagged commons-lang existed **two days before** HR-1 ran, and nothing
required reading it. Hence the LABEL CARD, enforced in code: a tool now refuses a repo whose label precision
is unpublished or under 0.70.

**The right null is almost never zero.** When predictor and outcome come from the same noisy label, the
measurement manufactures positive effects by itself. Simulate the null you actually face.

**Correlated error is the dangerous kind.** Non-differential noise attenuates toward zero and is correctable.
Ours is correlated by construction — the predictor and the outcome are read off the same label — and no amount
of data fixes it.

**Breadth is leverage on bias, not a substitute for it.** More eras and languages pool more *labelling
conventions*. But variation across repos is variation in the labelling process, and that is what made the
bias estimable at all.

**Audit your own tool's output, not just its exit code.** Three errors today were caught only by looking:
the issue-reference tier that was mostly workflow noise, an audit queue that ranked by size and surfaced
feature commits, and a verdict line that called a negative lift "exceeds null" because it beat a
more-negative null.

**Registering before running is what caught the reversal.** It is the one practice that worked unchanged all
day; without it the +0.082 would have been published.

## Digest of lit review #1 — fix labelling (full text: `labelling_literature.md`)

- **Keyword matching is as bad as ours.** Recall 0.394 / precision 0.436 on 34 manually validated SmartSHARK
  projects (König et al., arXiv:2609.21616). Only **38%** of real vulnerability-fix messages contain any
  security word (VulFixMiner, 1,982 commits).
- **SZZ chain** — B-SZZ → AG-SZZ → DJ-SZZ → L/R-SZZ → RA-SZZ; each fixes a prior flaw. Herbold et al. (EMSE
  2022): only ~half of SZZ-identified bug-fixing commits are actually bug fixes, and ~a fifth of real ones are
  missed. Tangling study: only **17–32%** of lines inside a bug-fixing commit actually fix the bug.
- **Bird et al. (ESEC/FSE 2009)** — linked bugs skew toward **less severe** bugs (Apache: 63% of minor fixed
  bugs linked vs **15%** of blockers) and toward more experienced developers. **Observation 3.3: commit-feature
  bias is unobservable from inside a linked-only sample.** The AspectJ anomaly — bias vanished where three
  developers did 81% of fixing and linked uniformly — says bias comes from *heterogeneous* linking behaviour,
  not from a low link rate.
- **Nguyen, Adams & Hassan (WCRE 2010)** — bias survives even process-enforced linking: it is upstream of the
  linking. **Better link recovery will not remove it.**
- **Herzig, Just & Zeller (ICSE 2013)** — 33.8% of >7,000 issue reports misclassified; 39% of files marked
  defective never had a bug. Our issue tier's precision ceiling is set by tracker quality, not by our linking.
- **EasyLink (ICSE 2026)** — a 7-day candidate window captures **59%** of true links; one year captures
  **97%**. Every pre-2023 tool used 7 days.
- **CVE → fix commits** — NVD `Patch` references are ~98.4% correct but present for only ~6.7% of records:
  excellent precision, tiny volume.
- **Top adoptions named**: SmartSHARK as external ground truth; a diff-reading LLM tier at two operating
  points (~0.75–0.82 recall at ~0.49–0.57 precision); a recorded bias profile per tier; GitHub's own curated
  links plus a one-year window.
- **Operational**: `ghtorrent.org` has lapsed and now serves a gambling site. (Checked — not referenced here.)

## What to do next

1. **Measure recall of the cascade**, the way we measured the keyword gate's. We know it is broader; we do not
   know that it is better.
2. **Per-tier precision audits** — only the keyword tier has a number.
3. **A diff-reading tier.** It is the only technique in the literature that addresses our failure mode,
   because it is the only one that reads the repair rather than the prose.
4. **Condition any cross-repo statement on announcement spread**, or do not make it.
5. **nDPI**: label 0.68 and no structural walk. The founding claim's second half is still unrun.

## Digest of lit review #2 — author effects (full report: `author_effects_literature.md`)

**Our measurement appears to be novel.** Per-developer *linking* propensity has been measured exactly once:
Bachmann et al. (FSE 2010) had an Apache httpd core developer hand-annotate all 493 commits in a six-week
window. Result: developers differ significantly in linking behaviour (**p ≈ 0.002**), and **9 of 17 developers
linked zero times**. Per-developer *keyword/announcement* propensity — what we measured — the review could
not find measured anywhere. Our seven-repo figure is the scaled-up version of the one hypothesis they got
significance on.

**Three findings that change what we should do:**

1. **Announcement propensity may be an author × file INTERACTION, not two separable components.** Bachmann
   found (anecdotally, not significant) that **file owners are *less* likely to link their own fixes**. If
   that holds, our `τ_combined = √(τ_author² + τ_file²)` is wrong — the components are not independent, and
   the combined figure could be over- or under-stated. **This is a real objection to the number we just
   published**, and the test is cheap: does an author's announcement rate differ between files they own and
   files they do not?
2. **Our recall is inside the published band, not below it.** König's per-repository SD is ±0.11–0.14, so
   ±1 SD spans roughly **0.26–0.54** recall. Our 0.41 (curl) and 0.26 (commons-lang) sit inside it.
   Separately, Eyolfson et al. measured keyword recall at **71–73%** on Linux and PostgreSQL. That is not a
   better pipeline — it is a different **announcement regime**. Projects with strong "fix" conventions are
   simply more legible to this method, which is our variance component showing up across projects.
3. **The "never announces" authors need shrinkage before they are claims.** With 15–22 commits, a 0.00 rate
   is a binomial-tail statement before it is a behavioural one. We removed the sampling component from the
   *variance*, but the per-author extremes should be reported under partial pooling.

**Ethics, acted on immediately.** Gold & Krinke (EMSE 27:17, 2022) document that repository *metadata* about
named people is where MSR ethics bite hardest, and that the norm is to publish aggregates and never author
identifiers — noting that across 141 MSR Mining Challenge papers, exactly one discussed ethics. Earlier today
`author_model.py` printed contributor names and email addresses. **It no longer does**: it reports the
distribution of announcement rates and the variance components only. A pseudonymous per-repo index is not
sufficient either, because "the author with 17 commits who never says fix" is a very short list in a small
project.

**Where the literature is thin — worth knowing before we build more:**
- **No study controls for what work a developer was assigned.** Every "experienced developers introduce fewer
  defects" result is an uncontrolled or exposure-controlled marginal association. Dieste et al. (EMSE 2017)
  found industrial experience had *no* detectable effect on quality in 10 quasi-experiments.
- **Ownership → defects is contested, and fails in our regime.** Confirmed inside Microsoft (Bird FSE'11,
  Greiler MSR'15); **Foucault et al. (EASE'14) failed to replicate it on Java OSS at file granularity** —
  fewer than half the systems significant at best, none at worst, with size dominating. Files in C/Java OSS
  is exactly our setting.
- **No defect-label study uses a per-author random intercept with a reported variance component.** That is
  the gap our measurement sits in.
- **Bias directions oppose each other and nobody has netted them out**: linked data over-represents
  *experienced* developers (Bird 2009), while the experience literature claims experienced developers produce
  *fewer* defects. If announcement propensity correlates with experience, the two biases partly cancel —
  quantifying that would be a result in itself.
