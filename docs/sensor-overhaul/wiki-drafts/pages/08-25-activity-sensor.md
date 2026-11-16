---
description: "> **Status:** design and back-tested mock-up (not yet in the engine). Replaces the Deep Churn and File Stability pair with independent recent-activity, age and ownership readings."
---
# Activity Sensor (Recent Activity, Age and Ownership)

> **Status:** Design note and mock-up (temporal-crucible, branch `sensor-overhaul`, `tools/sensor/activity_mockup.py`). **Not shipped:** the engine's current pair is documented in [Deep Churn](08-06-deep-churn.md) and [File Stability](08-10-file-stability.md) and is unchanged by this page.
>
> **Metric:** Where change is happening, how long a file has been settled, and who looks after it, in plain units (commits, days, years, shares) with repository percentiles.
>
> **Summary:** Keeps the intent of the existing pair, a short-term volatility reading and a long-term position on the timeline, and makes the two actually independent. It is context for where change lands, not a risk score.

## Engineering Summary
The existing Deep Churn and File Stability values were meant as a short-term and a long-term reading. In the code both are driven by the same input: how recently the file last changed (churn divides the 12-month commit count by the square root of the weeks since the last change; stability is that time as a share of the repository timeline). They therefore behave as one axis (rank correlation -0.86 within repositories). The sensor separates the pieces: recent activity (commits in the last 365 days), age and lifetime from a rename-aware history, and ownership concentration gated on activity, and it reports the share of recent edits that were mechanical migrations so a rename wave is not read as activity.

## Purpose
To show, per file, where change is concentrated now, how old and settled the file is, and who owns it, from a history that follows renames, in units a reader can act on.

## Problem Being Solved
- The two current values are one axis, so the intended short-term versus long-term split is lost.
- "Age" in the code is time since the last modification, not since creation, so a decade-old file edited yesterday reads as brand new.
- Commit counts include mass migrations (4-44% of in-place edits in 13 repositories, median about 22%), which inflate churn without being new work.
- History follows paths: libgit2's 2022 source reorganisation made 15-year-old files look 3.5 years old.
- With no history the engine returns neutral values that look like measurements.

## Design
1. **Recent activity.** Commits to the file in the last 365 days (the best-supported window: within size quartiles it ranks later fixes at AUC 0.661, against 0.604 for 90 days, 0.562 for 30 days and 0.605 for lifetime commits), with the last-90-day count as the "hot now" read and a repository percentile. **Dormancy** (days since the last change, shown as "dormant for N years" when there are no commits in 365 days) is the other end of the same axis (rank correlation -0.73), not a second gauge.
2. **Age and lifetime.** Years since the file's first commit and commits ever, from a history that follows renames (`git log -M`). Independent of activity (absolute correlation at most 0.15); descriptive, not predictive (AUC 0.47): it answers "old and settled" versus "new".
3. **Ownership concentration.** The top author's share of the last year's commits, with whether that author has committed in the last two years. **Activity-gated:** reported only for files active in the last year, so dormant stable files are not flagged. The number of authors adds nothing beyond commit count (0.91 correlation).
4. **Mechanical share.** The share of the last year's in-place edits that belong to a detected sweep (the same call or macro swapped across many functions in one quarter).
5. **Role tag and "not measured".** Tests, CI configuration, build scripts and source are tagged and lists default to source; anything with no usable history (not a work tree, an exported tree, a shallow clone) is "not measured" with the reason, not a neutral number.
6. **Companion reach reading.** Activity combined with reach (how much code depends on the file; see Evidence) is the strongest simple worklist.

## Pipeline Integration
- **Inputs:** a whole-history walk (one `git log --name-status -M` per scan, seconds per repository) instead of the 12-month sweep with early halting; [Chronometer](02-15-chronometer.md) as-of mode for historical scans; the sweep detector for the mechanical share; the call graph for reach.
- **Outputs:** per-file commits (365 and 90 days), days since last change, first-commit age, lifetime commits, top-author share, owner-active flag, mechanical share, role, repository percentiles; worklists.
- **Dependencies:** git history; [Signal Processing](02-09-signal-processing.md) for the existing columns, which stay as deprecated aliases.

## Tradeoffs
- Plain counts and days give up the 0-100 spectrum mapping; repository percentiles restore comparability within a repository.
- A whole-history walk costs more than a 12-month sweep, but it is a single pass and removes the 50%-of-files, 5,000-file and 15-second early halts that truncate coverage on large repositories.
- Dormancy is folded into activity rather than kept as its own gauge, trading a second number for independence.

## Limitations
- Back-tested on three repositories (curl, libxml2, libgit2); libgit2 is a repository where recent activity does not help forward in time (the engine pair even hurts there).
- Predictive claims are small by design: the panel adds +0.030, +0.023 and +0.008 AUC to code size for later fixes (curl, libxml2, libgit2), and age, ownership and mechanical share add about nothing; the value is descriptive and as a worklist.
- Commit counts still count every commit; the mechanical share addresses sweeps, not formatting commits that the detector cannot see.
- Change entropy and co-change scatter (established in the literature) are not tested here.

## Performance Notes
The prototype builds the panel for 16-28 snapshots per repository in a few minutes including the sweep detector; the history walk itself is seconds per repository.

## Future Work
Persist the horizons per file; as-of mode by default for historical scans; test change entropy and co-change; replicate beyond three repositories; the change-aware views (a diff-aware change report, and a "while you are here" prompt).

## Related Components
- [Deep Churn](08-06-deep-churn.md) and [File Stability](08-10-file-stability.md) (the current pair)
- [Chronometer](02-15-chronometer.md)
- [Ownership Entropy](08-04-ownership-entropy.md)
- [Debt ledger](08-24-debt-ledger-sensor.md)

## Evidence and Provenance
- **Redundancy:** the persisted churn is rank-equivalent to the 365-day commit count (0.96) and stability to days since the last change (0.97); the pair correlates -0.86 (one component carries 93% of the variance); -0.88 across 27,957 files in 494 repositories of the v2.12.0 population database.
- **Independence of the proposed axes** (curl): activity against age +0.09, against ownership share -0.06, against mechanical share +0.27, against reach +0.25.
- **Forward-in-time AUC for later fixes** (v3c label; size / engine churn and stability / panel): curl 0.813 / 0.828 / 0.843; libxml2 0.860 / 0.874 / 0.883; libgit2 0.790 / 0.767 / 0.798. Added one at a time to size, the axes that carry it are reach (+0.018, +0.016, +0.012) and recent activity (+0.015, +0.013, -0.009).
- **Worklists** (later-fix rate against all active source files, curl / libxml2 / libgit2): hot only x1.97 / 1.85 / 2.06; hot and high reach x2.08 / 1.97 / 2.56; reach alone x1.15 / 1.43 / 1.47; high reach but quiet x0.62 / 0.95 / 0.76 (quiet foundations are not where fixes land).
- Source documents: temporal-crucible, branch `sensor-overhaul`, `docs/sensor-overhaul/sensors/activity.md` and the output logs beside it; `docs/turn_surface_area.md`. All results exploratory; no registered test.
