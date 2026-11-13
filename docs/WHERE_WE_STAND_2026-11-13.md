# Where we stand, in plain terms (2026-11-13)

> **Correction & follow-up note (later on 2026-11-13 — see [`docs/mod1_result.md`](mod1_result.md),
> [`docs/mod1_wide.md`](mod1_wide.md), and [`docs/hr_units.md`](hr_units.md)):**
> 1. **Unit-file denominator bug in the "4 up, 4 down" split:** The eight-repo `in_degree` split described below
>    (`struct_null.py`) ranked **every scanned file** (including tests, docs, and other languages that have
>    zero callers and can never receive a unit-file fix touch). Restricting the denominator to **unit files
>    only** ([`docs/mod1_result.md`](mod1_result.md)) collapses three of the four positive repos (commons-lang
>    `+0.130 → −0.036`, prometheus `+0.074 → −0.024`, sphinx `+0.068 → −0.008`), leaving **1 positive (ndpi)
>    and 7 negative** on the earlier eight.
> 2. **MOD-1 on the 25-repo drawn panel ([`docs/mod1_result.md`](mod1_result.md)):** Neither age (`r = −0.25`,
>    `p = 0.23`) nor language family (`−0.021`, CI `[−0.093, +0.050]`) moderates `AUC(in_degree) − AUC(LOC)`;
>    the pooled lift is **−0.069 `[−0.102, −0.036]`** (2 positive, 11 negative, 12 across zero), which says
>    `in_degree` does not *replace* `LOC`.
> 3. **Tree-wide commits ([`docs/mod1_wide.md`](mod1_wide.md)) and "adds to size" ([`docs/sa3_registration.md`](sa3_registration.md)):**
>    Single reformat/header commits wearing a fix keyword flip individual repo signs (e.g. openssl has a
>    992-file header commit), and `AUC(x) − AUC(LOC)` tests whether `x` *replaces* size rather than *adds to*
>    size. SA3 ([`docs/sa3_registration.md`](sa3_registration.md)) tests within-size lift (`bAUC(x) − 0.5`) with
>    tree-wide commits removed. The original text below is preserved as written.

## What "centrality beats size in half the repos" actually means

`in_degree` = how many calls come **into** a file's functions. A high-in-degree file is a **hub**: lots of
other code depends on it.

We asked, in each repo: *does knowing which files are hubs tell you where fixes land, better than just
knowing which files are big?*

- In **commons-lang, ndpi, prometheus, sphinx** — yes. Hubs get fixed more than their size predicts.
- In **curl, libxml2, postgres, redis** — no, and **backwards**. Hubs get fixed *less* than their size
  predicts. You would do better betting against centrality.

All eight results are statistically solid. The average across them is **+0.006 — almost exactly zero.**

**So the old finding "structure reduces to size" was an average of two opposite real effects.** It was never
a description of any actual repository. It is like saying the average person has one testicle and one ovary:
arithmetically true, descriptively useless.

### The likely story (a hypothesis, not a finding)

A hub is one of two things, and they pull opposite ways:

- **A battle-tested core.** Everything calls it, so every bug in it was found years ago. Mature, stable,
  fixed less than its size suggests.
- **A load-bearing junction.** Everything calls it, so every change has to touch it, and it keeps breaking.
  Fixed more than its size suggests.

The split lines up with that:

| | repos | mean age | language |
|---|---|---|---|
| hubs predict fixes | commons-lang, ndpi, prometheus, sphinx | **17 y** | Java, C, Go, Python |
| hubs predict *safety* | curl, libxml2, postgres, redis | **25 y** | **all C** |

The four anti-predictive repos are the four oldest, and all four are C. **Age and language are completely
confounded here**, so this is a hypothesis worth testing, not a result. But it is a concrete, falsifiable one.

## What this means for the actual goal

The goal is: **do the structural problems GitGalaxy finds correlate with real defects — CVEs, fixes, PRs of
particular kinds?**

The honest answer from everything measured: **a single global structural score cannot work.** Ship one
formula across all repos and it is right in half of them and backwards in the other half. That is not a
labelling problem and better labels do not fix it — the split survived our best label.

repowise hit the identical wall from a different direction: their score inverts (AUC 0.488, below random) in
one size band, and their own mixed-effects model says repo identity moves the odds as much as any feature.

**This reframes the product rather than killing it.** The question stops being "what is the universal risk
formula" and becomes **"for this repo, does structure carry signal, and in which direction?"** A tool that
answers *that* is more honest and more useful than one that assumes an answer — and nobody else is shipping
it, because everyone else pools.

## Your questions, answered directly

**Would specifically-labelled commits help?**
Yes, but less than hoped, and we now know exactly how much. Better labels **changed the direction** of curl's
answer (+0.048 → −0.036) and rescued sphinx from a false null, so labels matter for *sign*, not just
precision — that is a real gain. But the four-four split **persisted under our best label**. Labels sharpen
each repo's answer; they do not make the repos agree. **The disagreement is real, not an artefact.**

**Would CVEs help?**
For the security question specifically, **yes — they are the right label**: externally curated, no
announcement-habit problem, no "did they write the word fix". The catch is volume. Most repos have a handful,
which is below the floor where any of this is measurable. So CVEs are the right outcome for a focused
security claim on a few large projects, and useless as a general-purpose label.

**Would going to AI repos help?**
**Partly, and not as the main corpus.** They are useful as a *label-quality testbed* — agent-heavy histories
with linking conventions give unusually clean issue links. But our own result showed the linking comes from
the project's **workflow**, not from the agent (aider's agents link 0.4% of the time, *less* than its
humans). And AI repos are young, so they lack the decades of history these before/after designs need. Use
them to test labelling methods; do not rebuild the corpus around them.

**Did the correction help?**
**Yes, concretely — it changed conclusions, not just error bars.** It killed a false positive (curl's
apparent structural win was a label artefact), it exposed the sign split the pooled null had been hiding, and
it showed our "cleaner" v3c label was quietly destroying statistical power (ndpi 266 → 57 positives). Three
real changes from one re-run.

## What to do next, in priority order

1. **Find the moderator.** Four-and-four is a usable design. Test whether age, language, or
   core-periphery shape predicts the sign. If it does, that is a publishable finding *and* a product feature:
   the tool tells you upfront whether structural risk scoring will work on your codebase.
2. **Stop reporting pooled structural numbers.** Per-repo signs with CIs. A corpus mean over disagreeing
   signs is not a result, and every pooled estimate in this programme inherits the problem.
3. **Run the CVE arm separately** on the few projects with enough CVEs to clear a floor — that is the real
   security claim, and it needs its own design rather than a keyword label.
4. **Re-run the crucible's own structural claims per repo.** The ones that reported pooled nulls are exactly
   where this split is most likely hiding.
