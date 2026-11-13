# What the LAWS data says, exploratory — 8 development repos, 5 languages

**Status: descriptive, development set, not a result.** LAWS is closed as a failure (`laws_postmortem.md`); no
panel repository was ever scanned or labelled. What follows is the full law run over the eight **development**
repositories whose quarterly walks were already built, kept because the owner asked what the data we did get
can still say. Every number here would have to be re-earned on a real panel before it could be claimed.

Run: `laws_run.py --matched-coverage` over 8 repos, **0 law failures**, 13,096 s. Tables:
`laws_exploratory_tables.md`. Figures: `laws_figs/`. Reproduce with `tools/laws_explore.py`.

| repo | language | quarters |
|---|---|---|
| commons-lang | java | 97 |
| prometheus | go | 55 |
| sphinx | python | 75 |
| libgit2 | c | 72 |
| libxml2 | c | 108 |
| postgres | c | 121 |
| redis | c | 65 |
| ripgrep | rust | 33 |

## The headline: one law survives everything, and one is contradicted

**LAW-2, preferential attachment, is the only law here that holds up under every check.**

- **8 of 8 repos** clear the registered margin with the whole 95% interval. Effects 1.16 to 1.79, every language.
- It is **robust to the instrument**: deleting 44% of resolved call edges moves it a median of 5%, worst case 10%.
- It needs the **smallest panel** of any law: ~2 repos per language.

New calls really do attach to already-popular functions, beyond what a fitness-only null explains, in Java, Go,
Python, C and Rust. If any claim from this family deserves a proper confirmatory study, it is this one.

**LAW-5, decay, is the one the data argues against.** The registered direction — modularity falling over time —
**fails in 7 of 8 repos**. Only ripgrep, by far the youngest at 33 quarters, decays. In the older C projects
modularity is flat or *rising* across two decades. Whatever software rot is, this measurement does not find it.

## Law by law

| law | repos clearing margin | coverage sensitivity | reading |
|---|---|---|---|
| **LAW-2** attachment | **8 / 8** | 10% worst | **supported, and robust** |
| **LAW-1** heavy tails | 6 / 8 | 26% worst | supported in direction, fragile in definition |
| **LAW-4** centralisation | 5 / 8 | **1093% worst** | statistically present, substantively nil, instrument-dominated |
| **LAW-3** hub persistence | 1 / 6 | **157% worst** | not evidence either way |
| **LAW-5** decay | — (descriptive) | — | **contradicted: 7 of 8 go the other way** |
| **LAW-8** network metrics predict defects | — | — | **no: AUC moves −0.028 to +0.015** |

**LAW-1 heavy tails.** Six of eight clear the margin, effects +0.05 to +0.26. But "the tail" is not one object:
the KS-chosen x_min runs 1 to 10 and the tail covers **8% to 100%** of nodes depending on the repo, and the
power law is rejected outright (GOF p<0.05) in sphinx, whose registered effect is nonetheless positive. The
direction looks real; the quantity is not comparable across repos as currently defined.

**LAW-4 centralisation.** Five of eight are statistically non-zero, yet the largest Gini gap is 0.029 on a 0–1
scale — detectable, not meaningful. With 8 repos the coverage ladder also shows the worst case at **1093%**,
up from 30% on five repos: the number tracks the extractor more than the code. Both facts point the same way.

**LAW-3 hub persistence.** Hubs persist (0.88–0.99) but so does the random-target null, leaving gaps of −0.006
to +0.12, one of six clearing the margin, and a 157% swing under edge loss. It is a ceiling test: when almost
everything persists, so does the null.

**LAW-8.** Adding the network metrics to the defect predictor moves AUC by between −0.028 and +0.015. In the
one repo where it helps most it is +0.015; in libgit2 it actively hurts.

**LAW-7, as a side note, is largely size.** Adjusting for size removes 60–90% of the structural signal
(in-cycle AME 0.239 → 0.051 in commons-lang).

## What this costs to do properly

Panel size per law, from the between-repo variance of these eight runs (`tools/laws2_size.py`):

| law | repos per language |
|---|---|
| LAW-2 | **2** |
| LAW-1 | **5** |
| LAW-4 | 22 |
| LAW-3 | 32 |
| LAW-8 | 61 |
| LAW-6 | **>400** |

Only LAW-1 and LAW-2 are affordable. LAWS 1 registered a uniform 16 per confirmatory language, which was
generous for the two feasible laws and far short for the rest — and it is the kind of thing that should be
known before a frame is built, not after a study is abandoned.

## Caveats that matter

- **Eight repos, five languages, mostly one or two per language.** Between-repo and between-language variation
  are tangled; the sizing numbers are order-of-magnitude planning figures, not estimates.
- **Development repos, chosen long ago for convenience, not drawn.** No claim about any language follows.
- **One instrument.** Every number comes from the same compile-free extractor. The coverage ladder bounds how
  much that matters per law, which is exactly why LAW-3 and LAW-4 are reported as instrument-dominated.
- **LAW-9 is effectively absent**: 7 of 8 repos have no sized OSV fix table, so it was evaluable once.
