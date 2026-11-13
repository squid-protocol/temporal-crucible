# Critique: is the anchored author model worth pursuing? (2026-11-13)

Three questions, answered by measurement rather than argument.

## 1. Is the per-author model too thin to answer anything? — **Yes, as built**

The numbers are against it:

- curl has **228 mechanism anchors** spread over **1,629 authors**. Only **8 authors** clear even 3 anchors.
- After the shrinkage the author-effects review (correctly) insisted on, curl's per-author recall compresses
  from an unshrunk **0.14–1.00** to **0.39–0.73**. That is the estimator telling us the extremes were
  small-sample noise — and it leaves a band too narrow to separate authors usefully.
- sphinx has **48** mechanism anchors in total.

**Verdict: it works as a per-REPO instrument and fails as a per-AUTHOR model.** The repo-level recall
estimates (curl 0.57, redis 0.50, postgres 0.44, sphinx 0.10) rest on 48–542 anchors and are worth having as
a third independent instrument. The per-author layer needs an order of magnitude more anchors than mechanism
labelling can supply, and manufacturing them by hand is exactly the manual grind the critique names.

## 2. Same author across multiple repos — **right design, not available in this bank**

This is the correct identification strategy: if one person's announcement rate differs between two projects,
that is *project convention*; if it travels with them, that is *personal habit*. It separates the author
effect from the project effect, which is the confound we could not otherwise break — and the author-effects
review found nobody has measured it (Zeng et al. observed the convention "travels with developers" but never
quantified it per person).

Measured on our nine repos:

- distinct authors: **5,834**
- authors appearing in **≥2 repos: 97**
- authors with **≥10 commits in ≥2 repos: 0**

**Zero.** These communities are disjoint — curl, postgres and commons-lang share essentially no contributors
at working volume. The design needs a corpus *chosen* for author overlap: one ecosystem (Apache projects
share committers heavily), Linux subsystems, or a GitHub-wide pull. It is a reason to pick different repos,
not a reason to abandon the idea.

## 3. Agents label more consistently — **right idea, and we already own the corpus**

Not in this bank. Bot-flagged commits run 0–827 per repo and are overwhelmingly dependency bumps, not fixes;
AI-trailer matches are 0–262 and mostly regex false positives on words like "generated with".

But **gitgalaxy itself has roughly 8,500 commits carrying a `Co-Authored-By: Claude` trailer**, against 6,631
non-merge commits on main — the overwhelming majority of its history is agent-authored, under a *documented*
message convention, with most commits naming the issue they serve (`Part of #7965`).

That is a natural experiment nobody else can run, and it answers a sharper question than "are agents
consistent" — they are consistent by construction, which is close to tautological. The useful questions:

1. **Does an agent-written message agree with ground truth better than a human-written one?** We can check a
   commit's claim against the issue it cites — is that issue a bug? — and compute precision and recall for
   agent-authored commits the same way we did for curl's humans.
2. **Is announcement *variance* lower?** Our τ is a variance component. If agent commits have τ ≈ 0 while
   human commits in the same repo have τ ≈ 0.8, that is a direct, quantified demonstration that the labelling
   problem is a human-convention problem — measured, not asserted.
3. **The forward-looking one: does this problem solve itself?** If agent-authored commits are legible to
   keyword labelling at 0.9 recall where human commits sit at 0.4, then as agents write more code the label
   quality of repository data improves on its own, and the correction machinery we built today has a shelf
   life. That is worth knowing before investing further in it.

## What I would actually do

1. **Keep the repo-level anchor estimate.** Cheap, independent, already corroborating the other two
   instruments. Drop the per-author layer until there are more anchors.
2. **Run the agent-vs-human comparison on gitgalaxy.** It is the highest-information experiment available,
   it uses data we already own, and nobody else has this corpus.
3. **Treat multi-repo author overlap as a corpus-selection requirement** for any future bank, alongside the
   oracle-feasibility screen. It is the only clean way to separate person from project.
4. **Do not hand-label at scale.** The critique is right: that road is long and the per-author payoff is
   small. The leverage is in (2) and in a diff-reading model, not in more human judgement.
