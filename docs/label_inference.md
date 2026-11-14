# Inferring fix probability from author habits (2026-11-13)

The original question: *can we label changes using an evolving model of authorship, anchored on fixes we
already know about?* Yes — it is **positive-unlabelled learning with a non-constant label frequency**, and
the pieces are in hand. `tools/label_infer.py` is the first working version.

## The circularity, and the way out

We cannot estimate "how often does this author say *fix* when fixing" from the keyword label — that is the
label grading its own homework. But some fixes are identified by **mechanism rather than prose**:

| anchor | what it is | biased by writing style? |
|---|---|---|
| **revert** | `This reverts commit <sha>` | no |
| **cve** | a CVE id | no |
| ~~fixref~~ | `Fixes #N` | **yes — contains a fix word** |

Among an author's **mechanism** anchors, the share the keyword gate also catches is that author's keyword
recall, measured against a denominator that does not depend on whether they write "fix".

**The prose anchor had to be dropped, and measuring it showed why.** On postgres the keyword gate catches
**96%** of `Fixes #N` anchors against **44%** of mechanism anchors — it is catching its own word back. On
curl the gap runs the other way (26% vs 57%), because curl puts `Fixes #N` in the *body*, where a
subject-only gate never sees it. Either way the prose anchor measures the overlap of two text rules, not
recall. It is available behind `--prose-anchors` for comparison only.

## What it measures

Pooled keyword recall on mechanism anchors, per repo — an independent estimate, from a different method than
the hand audit:

| repo | mechanism anchors | keyword recall on them |
|---|---|---|
| curl | 228 | **0.57** |
| redis | 72 | 0.50 |
| postgres | 542 | 0.44 |
| sphinx | 48 | **0.10** |

sphinx at 0.10 is the striking one. The spread across repos is the same announcement-regime variation seen
everywhere today, now visible through a third instrument.

Per-author, with James–Stein shrinkage toward the pooled rate: curl's unshrunk spread is **0.14 to 1.00**,
and shrinks to **0.39 to 0.73**. The shrinkage is doing real work — the extremes were mostly small-sample
artefacts, exactly as the author-effects review warned.

## The inversion, and the sampling pools

For a commit the keyword gate did **not** label, by an author with recall r:

    P(fix | unlabelled, author) = p(1 − r) / (p(1 − r) + (1 − p))

A non-announcement from someone who always announces is strong evidence of "not a fix". The same
non-announcement from someone who never announces is nearly no evidence at all. That is where an LLM or a
human should read:

| author recall band | unlabelled commits | inferred P(fix) | priority |
|---|---|---|---|
| 0.20–0.40 | 3,101 | 0.120 | **high** |
| 0.40–0.60 | 22,034 | 0.088 | low — the label is already informative |
| ≥ 0.60 | 805 | 0.046 | low |
| **unknown (too few anchors)** | **7,358** | — | **measure first** |

The largest actionable pool is the one we cannot yet score: **7,358 curl commits by authors with too few
mechanism anchors to estimate**. That is the first target — not because those commits are most likely to be
fixes, but because they are the ones the model cannot speak about at all.

## Honest limits

- **Mechanism anchors are a subpopulation.** Reverts and CVE fixes are not typical fixes, so this estimates
  recall *on them*, not globally. The direction of that bias is unknown.
- **They are scarce**: 48–542 per repo, and only 8 curl authors clear 3 anchors. Per-author estimates are
  thin, which is why shrinkage is mandatory rather than optional.
- **The model is static.** Announcement habits drift — conventional-commit adoption has been rising steadily
  — so a time-varying propensity is the obvious next version.
- **It assumes author and file effects separate.** The author-effects review surfaced evidence that file
  *owners* announce differently on their own files, which would make this an interaction. Untested.

## What this unlocks

1. **A principled sampling plan** for expensive labelling, instead of random draws.
2. **A per-repo recall estimate from a third, independent instrument**, to triangulate against the hand audit
   and the external benchmark.
3. **A route to inferred labels with calibrated uncertainty** rather than a boolean — which is what a
   measurement-error correction needs as input.
