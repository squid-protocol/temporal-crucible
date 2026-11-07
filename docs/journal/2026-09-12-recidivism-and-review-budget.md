---
date: 2026-09-12
title: Does exposure beat a line count at a review budget, and does recidivism? (RW, N-RW)
type: confirmatory
status: scored
verdict: replicated
theme: defect-prediction
ids: RW-H1; RW-H2; N-RW1; N-RW2
docs: docs/rw_hypotheses.md; docs/ndpi_rw.md; docs/ndpi_stage2.md
links: gitgalaxy#2982; temporal-crucible#28
takehome: The file that had the last security fix is where the next one lands: prior-fix count beats both structural exposure and a line count at a 20%-of-lines review budget on curl and nDPI (p<1e-4), while structural exposure ties a line count.
---

# Does exposure beat a line count at a review budget, and does recidivism? (RW, N-RW)

## Question

A reviewer's cost is lines read. If a reviewer reads 20% of the code, does ranking files by structural exposure find more of the next CVE fix than ranking by size (RW-H1)? Does a file's count of prior CVE fixes beat every static ranking (RW-H2)?

## Why we asked

repowise-bench reported an effort-aware (Popt) result, and the AUC nulls might have been asking the wrong question. Recidivism was registered as the history baseline any structural signal would have to beat.

## What we did

- Registered on gitgalaxy#2982 before the tool ran, using existing snapshots only.
- Per fix event, recall at 20% of the snapshot's lines, paired per event against LOC ordering, with a one-sided sign test at α = 0.01.
- Prior counts follow paths, so renames break lineage and handicap the predictor.
- curl had 182 fix events, with 179 events having enough history for RW-H2.
- nDPI ran the same pre-registered pair as N-RW1 / N-RW2 (112 events), with a TOST equivalence check for the null.

## What we found

- **RW-H1 not supported:** curl exposure vs LOC 52 wins, 48 losses, 82 ties (p=0.38).
- **N-RW1, the null, replicates on nDPI:** 8 wins, 8 losses, 96 ties (p=0.60). It is equivalence-confirmed, with CI [0, 0] inside ±0.05.
- **RW-H2 supported decisively on curl:** median recall 0.444 vs 0.000. Prior fixes beat exposure 77–27 and LOC 71–10, both p<1e-4.
- **N-RW2 replicates on nDPI:** median recall 0.500. Prior fixes beat exposure 42–8 and LOC 40–2, both p<1e-4.
- Pooled AUC still favours LOC (curl 0.862 vs 0.762). AUC rewards finding big files, and recall per line rewards finding fixed files cheaply.

## Take-home

Recidivism is the program's strongest and most replicated predictor. Structural exposure is a line count, even at ordering a review budget.

## What it changed

Recidivism became the rung-7 baseline every later study had to beat. Later arcs:
- Function-grain memory (FREC) failed against function size.
- The effort-aware openssl battery (EA) confirmed prior fixes on a third repo.
- XC showed that recidivism is specifically a property of latent defects.
- WH used it to find silent security patches.

See the history forward-tests entry.
