---
name: registered-study
description: Run a study in temporal-crucible end to end — check the label, register the design, run, and report both columns. Use when adding or extending any hypothesis test (HR-*, LAW-*, CG*, LIB, CPF, DRP) or when asked to "replicate", "extend", or "test whether X predicts Y" on this repo's cohorts.
---

# Running a registered study here

The repo's discipline is hypothesis-first (`CONTRIBUTING.md`). This is the order that discipline implies,
with the two steps that were learned the hard way on 2026-11-13 marked **NEW**.

## 1. Check what already exists — NEW

Re-measuring something the programme already measured is the expensive mistake; not knowing it was
measured is the dangerous one.

- labels and their precision → `docs/LABEL_CARD.md`
- what predictor × outcome has been tried → `docs/EXPERIMENTS.md`
- structure, history, line deltas → `laws-study/pilot/{dbs,history,deltas}`
- labelled fix events → `events/*_xc*.json`

## 2. Check the label is fit — NEW

```
python tools/label_card.py --assert <repo> <label>
```

Non-zero means the label's precision on that repo is unpublished or under the 0.70 gate. Measure it
(`tools/otherfix_sample.py` + the `otherfix_audit.md` pattern), clean it, or use the label descriptively.
**Never run the study and decide about the label afterwards** — that ordering is what produces a result
that reverses the next day.

## 3. Pick the tier

- **Development** repos (the CGR eight) are deliberately spent: breadth or falsification, never fresh
  confirmation. Say so in the write-up.
- **Confirmatory** repos are sealed and used once per registered hypothesis family. openssl is reserved.

## 4. Register before running

Direction, test, bar, cut, exclusions, floors, and what would falsify it — into `docs/HYPOTHESES.md` or a
study doc, **committed before the run**. State in advance what a null would mean: if a known weakness makes
a null uninformative, say so now, not after seeing one.

## 5. Run, and keep the floors

A floor moved after seeing which side a repo falls on is not a floor. If a repo is excluded, name it and
the reason in the output.

## 6. Report both columns

Raw and cleaned, original and strengthened — publish both, and never only the flattering one. The gap
between them is usually the finding.

## 7. Journal it

Every study gets an entry (`CONTRIBUTING.md`, "The experiment journal") and a row in `docs/EXPERIMENTS.md`.
