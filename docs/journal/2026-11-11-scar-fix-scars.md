---
date: 2026-11-11
title: Scars: what do the danger comments that fixes leave behind mean? (SCAR)
type: confirmatory
status: scored
verdict: mixed
theme: comments
ids: SCAR-R1, SCAR-R2, SCAR-I1, SCAR-I2
docs: docs/scar_hypotheses.md
links:
takehome: Danger comments at birth predict CVE fixes even in files with no CVE history (1.55×), so they are foresight rather than inherited scars; whether the warnings that CVE fixes leave behind mark lasting fragility is still underpowered.
---

## Question

CVE fixes leave danger-worded comments behind (CF-H1). Do those scars mark code that stays fragile, or code whose
lesson stuck? And is DC-2's "danger comments at birth predict CVEs" partly inherited from the file's past CVE fixes?

## Why we asked

- **CF-H1** (CVE fixes add danger comments 1.61×) and **DC-2** (danger comments at birth → 1.45× first CVE) are both
  population tendencies.
- **DCS** found no code signature that separates risky from safe danger-commented functions.
- The owner asked (2026-11-11) for both follow-ups: scars → later fixes, and the birth signal in files without
  history.

## What we did

Registered (owner OK 2026-11-11): [`../scar_hypotheses.md`](../scar_hypotheses.md).

## What we found

Scored in [`../scar.md`](../scar.md).
- **SCAR-I2, supported.** In files with no prior CVE fix, danger-commented births reach a first CVE fix 1.55× as
  often as plain-commented ones (lower bound 1.04). That holds in each of the four repos (1.30–2.22).
- **SCAR-I1, not supported.** Danger wording does not clearly cluster in files with a CVE past (OR 1.38 [0.94, 2.00]).
- **Copied scars are rare.** Only 0.4% of danger-commented births carry text that an earlier CVE fix had written.
- **Scars are rare at function grain.** Only 35 of 1,098 first CVE fixes left a danger line in the fixed function.
  - SCAR-R1 (later CVE fix) is underpowered: 4 events among scarred functions.
  - SCAR-R2 (any later fix) is not supported: 0.35 [0.10, 1.58].
  - Descriptively, scars from ordinary fixes point the other way (any later fix, 1.69 [1.13, 2.39]).
- **libarchive's fix labels have no CVE class,** so Part R ran on four repos.

## Take-home

When authors warn about danger at birth, they are anticipating risk, not echoing the file's history. Whether the
warnings that CVE fixes leave behind mark lasting fragility is still underpowered.

## What it changed

- **DC-2's signal is strengthened:** it does not reduce to prior-CVE history.
- **Part R would need far more CVE fixes.** Function-grain scars are only 3% of first CVE fixes.
- **The ordinary-fix contrast is a lead for a new registration on unseen repos.** CVE scars lean toward "lesson
  learned", ordinary scars toward "more fixes follow".
