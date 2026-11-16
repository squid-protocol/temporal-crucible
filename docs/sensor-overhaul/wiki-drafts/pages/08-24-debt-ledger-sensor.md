---
description: "> **Status:** design and prototype (not yet in the engine). Replaces the density score in 08-08 with a located, aged, ranked list of debt markers."
---
# Debt Ledger (Located, Aged, Ranked Technical Debt)

> **Status:** Design note and working prototype (temporal-crucible, branch `sensor-overhaul`, `tools/sensor/debt_worklist.py`). **Not shipped:** the engine's current gauge is documented in [Tech Debt Exposure](08-08-technical-debt.md) and is unchanged by this page.
>
> **Metric:** Open self-admitted debt markers (`TODO`, `FIXME`, `XXX`, `HACK` and the engine's other planned/fragile tags), each with its original age, author, file activity and a flag read against the repository's own repayment history.
>
> **Summary:** Replaces a 0-100 density with a ranked worklist. It answers: what self-admitted work is open here, how old is it compared with how this project normally behaves, is its author still around, and does it sit in a file someone is working on now? It never claims to predict defects.

## Engineering Summary
A debt marker is an admission by the author: discrete, locatable and ageable, which a line-density score throws away. The ledger tracks every marker through the repository history (moves, rewordings and renames continue the same item), measures how this repository actually repays debt, flags debt older than anything the project has ever repaid ("fossils"), and ranks what is left by how likely it is to stay stuck and how cheap it is to decide now. Every list opens with the repository's own track record, so a flag is accountable to what has happened in this repository.

## Purpose
To turn the engine's marker counts into an actionable, honest list: located, aged, ranked, triage-able, with the evidence for each flag stated.

## Problem Being Solved
The current score mixes five things in one sigmoid (planned markers, fragile markers, a language term, unreferenced names and duplicate logic), loses the marker's age, author and location, and moves with net line count even when no marker changes. Measured against what it claims, it correlates only +0.32 with the marker counts it is named for, while the underlying counts are sound (+0.84 to +0.97 against a text search in eight repositories). Debt density also adds nothing to fix prediction (+0.003 AUC beyond size, churn and history), so the value of this sensor is the worklist, not a risk number.

## Design
1. **Marker records.** For each open marker: a stable ID, file, line, marker word and class, a hash of its normalised text, the author and date of its first appearance (its **original age**, followed through moves, rewordings and renames; a `git blame` of the line gives only the date of its last edit, which understates the age: curl's `lib/urldata.h` XXX note is 0.2 years by blame and 22.1 years by tracking).
2. **The repository's yardstick**, computed only from debt already repaid before the date in question: the share repaid within one and five years, and the age by which 90% of the repaid debt was repaid (p90). An open marker older than p90 is a **fossil**: this project has almost never repaid debt that old.
3. **Stuck probability.** A logistic model of "will not be repaid within two years" on original age, the file's commits in the last year, and whether the author has committed in the last two years (fitted on nine C projects, 72,163 observations). Per standard deviation, the odds of repayment move by 0.56 for age, 1.36 for file activity and 1.42 for an active author; marker class, bare markers and text length do nothing.
4. **Ranking.** Stuck probability times file activity: stuck markers sitting where someone is already working. This is a heuristic combining two validated tendencies; whether surfacing it changes what gets repaid has not been tested.
5. **Track record.** Each list opens with what this repository's history says about the flag; for libgit2: fossils repaid 6.2% of the time within two years against 23.9% for other debt; fossils in hot files (10+ commits a year) 12.6% against 2.1% in quiet files; markers with an active owner 9.6% against 4.1% with the owner gone.
6. **Usual size.** Not an estimate: nothing observable before repayment predicts the size of the repaying change (all rank correlations at most 0.13). The list shows the file-size band and what repayment looked like in files of that size (under 500 lines: median change 24 lines; 500-2,000: 34; over 2,000: 56), plus how many other markers are open in the same file, because debt is cleared in clusters (+0.22 correlation with markers repaid in the same commit).
7. **Stable IDs and triage, in SARIF terms.** The ID derives from the marker's birth state, so it survives edits above it, moves and renames, and is exported as the SARIF `partialFingerprints` entry. States: `watching` (SARIF `underReview`; ranked last), `keep` (`accepted`; kept on purpose, with a reason), `not_debt` (`rejected`; hidden), `done` (hidden; reopened if the marker is found again).
8. **While-you-are-here use.** When a change is large enough, surface the open markers in the files it touches. Back-tested over six C projects (259,242 observations): only 1.3% of open markers in a touched file are repaid in that commit; a trigger of 50+ changed lines in the file gives 3.4% (2.7x) and keeps 48% of all repayments; the editor's own markers on such a change 4.8% (3.7x). Cap the list (three) and put the editor's own markers first.

## Pipeline Integration
- **Inputs:** the comment stream's positional marker hits (already computed per function and per file, not persisted with line numbers), git history (lineage or blame for the original age; as-of mode for historical scans), the repository's closed-marker history for the yardstick.
- **Outputs:** per-marker ledger records, a per-repository yardstick and track record, a worklist, and SARIF 2.1.0 results with the sensor's fields as properties.
- **Dependencies:** [Chronometer](02-15-chronometer.md) history; the comment extraction phase ([The Prism](02-07-the-prism.md)).

## Tradeoffs
- A list instead of a number gives up cross-repository comparability; the yardstick is the repository's own history on purpose (projects repay debt very differently: 38% to 98% eventually removed).
- The repo-relative fossil flag is an explanation, not a better predictor than raw age (AUC 0.614 against 0.636 for telling which debt will not be repaid); the list shows both.
- Original ages need a history walk, which costs more than a single-snapshot count.

## Limitations
- C family and nine projects so far; the heuristics for what counts as a comment line follow the lifecycle study.
- Located lines resolve for only 33-88% of markers when reconstructed from tracked text; the engine should persist positions.
- Overall predictive power for repayment is modest (AUC 0.613 forward in time); the list is a prioritisation aid, not a forecast.
- No effort estimate (see Design 6) and no pilot yet of whether the while-you-are-here prompt raises repayment.

## Performance Notes
The prototype tracks a repository's whole history in 10-60 seconds per repository (nine C projects, up to 65,000 commits) with one pass over the debt-touching diffs plus one rename pass.

## Future Work
Persist marker positions and IDs in the engine; compute the yardstick and original ages at scan time; replicate beyond C; a pilot of the prompt on a real repository.

## Related Components
- [Tech Debt Exposure](08-08-technical-debt.md) (the current gauge)
- [The Prism](02-07-the-prism.md) and [The Detector](02-08-the-detector.md) (comment stream and marker hits)
- [Chronometer](02-15-chronometer.md)
- [Activity sensor](08-25-activity-sensor.md)

## Evidence and Provenance
temporal-crucible, branch `sensor-overhaul`: `docs/sensor-overhaul/sensors/tech_debt.md` (design, trial, effort and triage sections), `docs/sensor-overhaul/sensors/change_aware.md` (prompt back-test), output logs in the same folder; earlier studies `docs/debt_lifecycle_exploratory.md`, `docs/drp.md`, `docs/cpf.md`. All results exploratory; no registered test.
