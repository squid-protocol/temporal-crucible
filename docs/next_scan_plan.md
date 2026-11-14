# Is the keyword/function work suspect too, and what should we scan? (2026-11-13)

## 1. The keyword/function-lattice work is NOT suspect — it never used a label

Checked against `docs/EXPERIMENTS.md`. The two keyword-lattice rows both read *"what changes after birth,
**irrespective of defects**"*:

- **Keyword family COUNTS over a function's life** (vs the presence set the lattice uses)
- **Keyword ORDER and NESTING depth over a life** (tree-sitter + scan DB for identity)

They have **no fix label anywhere in the outcome**, so nothing measured today touches them. Same for LAW-1 to
LAW-5. Their real limitation is different and already recorded: exploratory, curl-only.

**But ~16 of the 18 structural rows do use a fix/bug/CVE outcome** — recidivism, change entropy, centrality,
aggregate and per-vector exposure, fix-shaped grammar, mechanism specificity, language strictness,
archetypes, the new engine metrics, fix-class split, platform-conditional density, compiler shocks,
co-change omission. **All of those inherit everything measured today.**

## 2. The bigger problem: the matrix was tested on one repo from each side of the split

Nearly every row in `EXPERIMENTS.md` was evaluated on **curl and nDPI**. We now know those two sit on
**opposite sides of the structural sign split** (curl −0.036, nDPI +0.118).

Look at the recurring verdict with that in mind:

| row | verdict as written |
|---|---|
| Per-vector exposure | "curl-only (`safety_score` p=.007); **fails to replicate on nDPI**" |
| Fix-shaped grammar | "**curl/human-report-specific**" |
| Change entropy | ✓ curl, ○ nDPI |
| New engine metrics | ✗ curl, ⚠ nDPI |
| Centrality / PageRank | ✗/⚠ curl, ⚠ nDPI |

Every one of these was read as *"the effect is not real, it is a curl artefact."* **It is equally consistent
with the effect being real and opposite-signed in the two repo families, with one repo drawn from each.**

That ambiguity sits on more rows than the label problem does, and no amount of label work resolves it. **Only
more repositories do.**

## 3. We have no unassessed time courses — but we do not need them

The LAWS study walked 10 repos; all 10 are assessed, 8 clear the positives floor. Nothing is waiting.

**What we do have: 80 repositories with deep git history already on disk** in `/nvme-data/gitgalaxy-data`
(123 with any history; 80 with ≥2,000 commits). And `struct_null.py` needs **one snapshot**, not a time
course — structure at the cut, labels from `git log`. `laws_build --limit` caps the walk.

**So n can go from 8 to ~40 without cloning anything.**

## 4. The pool breaks the confound that blocks us

Our 4-and-4 split is useless for finding the moderator because **age and language are perfectly confounded**
— all four anti-predictive repos are old C. The pool fixes exactly that:

| stratum | n | examples |
|---|---|---|
| **old C** | 12 | curl, freebsd-src, gnupg, racket, root |
| **young C** | 15 | ghostty, godot, PowerToys, circuitpython |
| **old managed** | 13 | cpython, django, jenkins, mediawiki |
| **young managed** | 40 | ansible, angr, bun, discourse, AppFlowy |

**All four cells are populated.** A balanced draw of ~10 per cell separates age from language for the first
time.

## 5. Recommendation: scan breadth first, then redo the keyword studies

**Scan first.** The keyword/function studies are curl-only, so re-running them on curl returns curl. Breadth
is what we lack, and the moderator pays off twice: it is a finding in itself, *and* it tells us how to read
every "fails to replicate on nDPI" verdict in the matrix — leverage on ~16 rows rather than 2.

Order:

1. **Draw 40 repos, 10 per stratum**, from the pool.
2. **Harvest history + one structural snapshot each**; run `struct_null.py` per repo under the cascade label.
3. **Test the moderator**: does age, language, or core-periphery shape predict the sign? Pre-register the
   test before looking — the registered-default rule applies.
4. **Then re-run the keyword/function studies** on a moderator-stratified sample rather than on curl alone.
5. **Re-read EXPERIMENTS.md** with the moderator in hand and re-mark every curl-vs-nDPI verdict.

## What this does not fix

The label problem is still there underneath — precision 0.27–0.86, recall 0.26–0.57, and the cascade's recall
still unmeasured. Breadth makes the *sign* question answerable; it does not make any single repo's estimate
more accurate. Both lines of work are needed, and breadth is the one that unblocks the most claims.
