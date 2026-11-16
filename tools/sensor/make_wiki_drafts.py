#!/usr/bin/env python3
"""Generate the wiki drafts: revised copies of four existing GitGalaxy wiki pages (anchored edits against origin/main) and unified diffs.
    python tools/sensor/make_wiki_drafts.py"""
import subprocess, pathlib, difflib
V6="/srv/storage_16tb/projects/gitgalaxy/v6"; OUT=pathlib.Path(__file__).resolve().parents[2]/"docs/sensor-overhaul/wiki-drafts"
def orig(name): return subprocess.run(["git","-C",V6,"show",f"origin/main:docs/wiki/{name}"],capture_output=True,text=True).stdout
def edit(text,anchor,new,mode="replace"):
    assert anchor in text, f"anchor not found: {anchor[:70]}"
    return text.replace(anchor,new,1) if mode=="replace" else (text.replace(anchor,anchor+new,1) if mode=="after" else text.replace(anchor,new+anchor,1))
RES="> **Research notes:** temporal-crucible, branch `sensor-overhaul`, `docs/sensor-overhaul/` (guide, `sensors/activity.md`, `sensors/tech_debt.md`) and `docs/turn_surface_area.md`. Measurements are exploratory (13 repositories; a 580-repository population sample confirms the descriptive results)."
pages={}
# ---------------- 08-06 Deep Churn ----------------
t=orig("08-06-deep-churn.md")
t=edit(t,"1. **Raw Commit Frequency:** Commit volume is normalized against the square root of the file's age in weeks to dampen the penalty on long-standing legacy files.","1. **Raw Commit Frequency:** Commit volume is normalized against the square root of the file's age in weeks to dampen the penalty on long-standing legacy files. **What \"age\" means in the code:** the time since the file's **last modification** (the repository's newest time minus the file's modification time, never less than one week), not the time since the file was created. A file edited this week counts as one week old whatever its history. `commit_count` is the number of commits that touched the file inside the Chronometer's 12-month sweep.")
t=edit(t,"- **Inputs received:** `commit_count` (total commits modifying the file), `age_in_weeks` (file age relative to newest commit), and `max_freq` (highest raw change frequency in repo).","- **Inputs received:** `commit_count` (commits that modified the file within the Chronometer's 12-month sweep), `age_in_weeks` (weeks since the file's last modification, minimum 1), and `max_freq` (highest raw change frequency in repo).")
t=edit(t,"- Highly dependent on team commit hygiene (e.g., squashed merges vs. raw commit logs).","- Highly dependent on team commit hygiene (e.g., squashed merges vs. raw commit logs).\n- Counts mass migrations like any other commit. In 13 repositories, 4-44% of in-place edits to surviving functions (median about 22%) were mechanical sweeps (the same call or macro swapped across many functions in one quarter); they raise churn without being new work.\n- Follows paths, not file identity: a renamed or moved file starts a new history, and the 12-month sweep is the only window (no lifetime counts or true file age).\n- When no usable history exists (not a git checkout, an exported tree with no `.git`, a shallow clone) the value is a neutral `0.0`, which is indistinguishable from a file with no commits.","after")
t=edit(t,"## Performance Notes","""## Measured Behavior (exploratory, 2026-11)
"""+RES+"""

- **Rank-equivalent to a 365-day commit count.** Across 35,287 file-intervals in 7 repositories (history-aware scans), the persisted churn value correlates 0.96 (within-repository ranks) with the number of commits to the file in the last 365 days, and 1.00 with the raw frequency.
- **Shares its recency term with [File Stability](08-10-file-stability.md).** The two history values correlate -0.86 within repositories (one principal component carries 93% of their joint variance), and -0.88 across 27,957 files with history in 494 repositories of the v2.12.0 population database. In practice they behave as one axis, "how recently did this file change".
- **Independent of the keyword gauges.** Absolute rank correlation with every keyword-based risk value is at most 0.11; it correlates +0.55 with ownership entropy and +0.67 with silo risk.
- **Relation to outcomes (descriptive, no risk claim).** Added to code size, churn and stability raise AUC for later fixes by +0.015 to +0.019 under three fix-label definitions; within size quartiles churn ranks later fixes at AUC 0.65 and correlates +0.26 with how much a file changes in the next interval. A single 365-day commit count carries the same information; 30-day, 90-day and lifetime windows add nothing.

""","before")
t=edit(t,"## Related Components","""**Design direction.** The proposed [Activity sensor](08-25-activity-sensor.md) keeps the volatility reading as plain recent activity (365-day commits, with a 90-day hot-now read), shows dormancy as the other end of the same axis, follows renames, and reports the **mechanical share** of recent edits so a migration wave is not read as activity.

""","before")
pages["08-06-deep-churn.md"]=t
# ---------------- 08-10 File Stability ----------------
t=orig("08-10-file-stability.md")
t=edit(t,"*(When Newest file, Score = 0.0; When Oldest file, Score = 100.0)*","*(When Newest file, Score = 0.0; When Oldest file, Score = 100.0)*\n\n**What this measures.** `FileMTime` is the file's last modification time, so the score is the time since the file's **last change** as a share of the repository's whole timeline, not its age since creation: a ten-year-old file edited yesterday scores about 0 (RECENT). With no usable history (not a git checkout, an exported tree with no `.git`, a shallow clone) the engine returns a neutral `50.0`.")
t=edit(t,"- Relies on Git commit timestamps which can be manually spoofed or accidentally rewritten during interactive rebases.","- Relies on Git commit timestamps which can be manually spoofed or accidentally rewritten during interactive rebases.\n- The same effect as the rogue formatting commit happens at smaller scale all the time: in 13 repositories 4-44% of in-place edits (median about 22%) were mechanical sweeps that reset a file's last-modified time without new work.\n- Follows paths, not file identity: renaming or moving a file resets its history (libgit2's 2022 source reorganisation made 15-year-old files look 3.5 years old to a path-following history).\n- Neither this value nor [Deep Churn](08-06-deep-churn.md) gives true file age (time since creation) or lifetime commit counts.","after")
t=edit(t,"## Related Components","""## Measured Behavior (exploratory, 2026-11)
"""+RES+"""

- **It is days since the last change.** Across 35,287 file-intervals in 7 repositories the persisted stability correlates 0.97 (within-repository ranks) with the number of days since the file's last commit.
- **One axis with churn, not two.** Churn and stability correlate -0.86 within repositories and -0.88 across 494 repositories of the population database; the intended short-term versus long-term pair is not realised because both are driven by the same recency input.
- **Relation to outcomes (descriptive).** Within size quartiles, stability ranks later fixes at AUC 0.41 (0.59 inverted: recently changed files get more fixes) and correlates -0.17 with later change.
- **True file age is a different, independent quantity.** Years since the first commit (following renames) correlates at most 0.15 in absolute value with recent activity and is not predictive (AUC 0.47); it is useful as context ("old and settled" versus "new").

**Design direction.** The proposed [Activity sensor](08-25-activity-sensor.md) reports file age and lifetime commits separately, from a rename-aware history, and shows dormancy ("no commit for N years") as part of recent activity instead of a project-relative ratio. This also addresses the planned work above: automated formatting commits are separated as mechanical edits.

""","before")
pages["08-10-file-stability.md"]=t
# ---------------- 08-08 Technical Debt ----------------
t=orig("08-08-technical-debt.md")
t=edit(t,"**Mathematical Formulation**\n1. **Stress Sum Calculation:**\n$$\\text{StressSum} = (\\text{PlannedDebt} \\times 1.0) + (\\text{FragileDebt} \\times 3.0) + (Irc \\times 0.5)$$","**What the code does beyond the annotation markers.** The score also counts two implicit terms that are not comments: functions flagged as unreferenced by name (`unreferenced_by_name`, weight 2.0) and duplicate logic (`duplicate_logic`, weight 5.0); when any implicit term and any acknowledged marker are both present, the stress is multiplied by 1.5. A file with no markers and no implicit terms returns 0.0 immediately.\n\n**Mathematical Formulation**\n1. **Stress Sum Calculation:**\n$$\\text{Slop} = (\\text{Unreferenced} \\times 2.0) + (\\text{DuplicateLogic} \\times 5.0)$$\n$$\\text{StressSum} = (\\text{PlannedDebt} \\times 1.0) + (\\text{FragileDebt} \\times 3.0) + (Irc \\times 0.5) + \\text{Slop}$$\n$$\\text{if } \\text{Slop} > 0 \\text{ and } (\\text{PlannedDebt} > 0 \\text{ or } \\text{FragileDebt} > 0): \; \\text{StressSum} \\mathrel{\\times}= 1.5$$")
t=edit(t,"- Custom debt tags (e.g., `OPTIMIZE`, `TECHDEBT`) are not recognized unless explicitly added to the static scanner regex.","- Custom debt tags (e.g., `OPTIMIZE`, `TECHDEBT`) are not recognized unless explicitly added to the static scanner regex.\n- The score is a density squashed by a sigmoid and mixes three different things (annotation markers, unreferenced names, duplicate logic); see Measured Behavior. It moves with net line count even when no debt marker is added or removed (the density-denominator artifact tracked in `docs/vectors.md`, `debt_markers`).\n- No age, owner or history: a three-year-old `FIXME` and a three-day-old `TODO` look alike, and nothing says whether the marker's author is still around.","after")
t=edit(t,"## Related Components","""## Measured Behavior (exploratory, 2026-11)
"""+RES+"""

- **Counting the markers is sound.** The engine's planned-plus-fragile counts match a plain text search of the same commit: per-file Spearman +0.84 to +0.97 across eight repositories (libgit2 +0.92, libxml2 +0.95, redis +0.84, curl +0.94, sqlmap +0.90, scapy +0.95, sphinx +0.97, prometheus +0.94); the engine counts slightly more (more marker words, several human languages).
- **The composite loses it.** The persisted tech-debt value correlates only +0.32 (median over repositories) with the marker counts, because the sigmoid mixes in unreferenced names and duplicate logic; 59% of files score 0 and the value is sparse.
- **Debt density does not predict fixes.** A file's comment profile, including debt density, adds +0.003 AUC beyond size, churn and history (temporal-crucible comment-profile study).
- **How debt behaves over time** (nine C projects, every marker followed through its life): about three quarters of debt comments are eventually removed, but projects range from 38% to 98% and from months to decades; `XXX` lives longest (median 3.0 years against 1.1 for `TODO` and `FIXME`); about half is repaid by its own author; debt is repaid in large commits, not bug fixes.
- **Old debt is stuck, not riskier.** Debt older than the 90th percentile of what that repository has repaid ("fossils") is repaid within two years 6.9% of the time against 22.0% for other debt; fossils in files with 10 or more commits that year are repaid 12.6% of the time against 2.6% in quiet files; markers whose author is still active are repaid more often. Marker class (`TODO` vs `FIXME` vs `XXX`) and bare markers do not change the odds.

**Design direction.** The proposed [Debt ledger](08-24-debt-ledger-sensor.md) replaces the density score with a located, aged, ranked list of markers whose flags carry the repository's own track record. Its "Debt Age" is the planned work above, with one change from the plan: older debt should be surfaced for a decision, not penalised in a score, because the evidence says old debt is stuck, not riskier.

""","before")
pages["08-08-technical-debt.md"]=t
# ---------------- 02-15 Chronometer ----------------
t=orig("02-15-chronometer.md")
t=edit(t,"* **Stability (Age):** The exact modification time (`mtime`) of each file, along with the repository's minimum and maximum timestamps.","* **Stability (Age):** The exact modification time (`mtime`) of each file, along with the repository's minimum and maximum timestamps. This is the time of the file's **last** modification, not its creation (see [File Stability](08-10-file-stability.md)).")
t=edit(t,"* **Raw Churn Frequency:** The total commit count for each file within the historical sweep window.","* **Raw Churn Frequency:** The total commit count for each file within the historical sweep window (12 months).")
t+="""
## Scans of Historical Commits (As-Of Mode)

Two things decide whether a scan of an old commit carries history values at all:

* **The directory must be a git work tree.** An exported tree (for example a tarball of a commit) has no `.git`, so the Chronometer falls back to neutral values (stability `50.0`, churn `0.0`). Scan a detached `git worktree` of the commit instead.
* **The window must be anchored to the commit, not to today.** The default sweep is "one year before now", which is empty for any commit older than a year. `GITGALAXY_HISTORY_ASOF=1` anchors the window to the checked-out commit's date, streams the whole window and dates out-of-window files by their last ancestor commit, so every history field becomes a deterministic function of the checked-out commit.

## Measured Behavior (exploratory, 2026-11)
"""+RES+"""

On the history-aware scans of 7 repositories (143 scans, each from a detached worktree with `GITGALAXY_HISTORY_ASOF=1`) the two persisted values reduce to two plain quantities: churn is rank-equivalent to the file's commits in the last 365 days (Spearman 0.96) and stability to the days since the file's last commit (0.97), and the two correlate -0.86 with each other. Details, limits (renames, mechanical sweeps, the 12-month window and the early-halt rules above) and a proposed redesign: [Deep Churn](08-06-deep-churn.md), [File Stability](08-10-file-stability.md) and the [Activity sensor](08-25-activity-sensor.md) design note.
"""
pages["02-15-chronometer.md"]=t
for n,t in pages.items():
    (OUT/"pages"/n).write_text(t)
    o=orig(n); d="".join(difflib.unified_diff(o.splitlines(True),t.splitlines(True),fromfile=f"a/docs/wiki/{n}",tofile=f"b/docs/wiki/{n}"))
    (OUT/"patches"/(n[:-3]+".patch")).write_text(d); print(n,"changed lines:",sum(1 for l in d.splitlines() if l.startswith(("+","-")) and not l.startswith(("+++","---"))))
