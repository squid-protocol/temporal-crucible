# ARG — are declared-AI commits named as the cause of later fixes more often than the same developers' other commits? — registered 2026-11-11 (owner OK), a living study with three scheduled looks

**Why.**
- The program's AI studies so far are descriptive and outcome-blind. AI-assisted commits comment differently by tool
  (#153). They keep code structure but add dependencies (#154).
- The question people care about is whether AI-assisted code **breaks more often**. Many projects record which
  commit caused a bug: a revert, or a `Fixes: <sha>` trailer. That gives a per-commit outcome.
- Declared AI use is new; most of it dates from 2026. A fair outcome needs a follow-up window, so this is registered
  as a **living study**: the rules are frozen now, scheduled looks spend the error budget, and every run updates a
  descriptive tracker.

## Prior work

- **This program:** #153 and #154 (exploratory, outcome-blind); REG (regression links, `tools/reg_links.py`), whose
  revert and sha-reference rules this study re-implements directly on git.
- **Śliwerski, Zimmermann and Zeller, "When do changes induce fixes?", MSR 2005** (the SZZ approach). Links fixes to
  the changes that induced them. This study uses only the explicit links developers write (reverts, `Fixes:`), not
  blame-based inference. Recalled from memory: checked against the paper before the result doc cites it.
- **AI-assisted code quality.** Studies of AI-written code mostly measure it in controlled tasks or by detector-based
  proxies (e.g. Ji et al., arXiv 2607.01867, on comments). We know of no study of **declared** AI commits in mature
  open-source projects against the developers' own commits, with the projects' own fix links as the outcome. A
  literature search is repeated before each result doc ships.
- **This study's difference:** trailer-declared AI use, within-developer and size-matched, the projects' own
  cause links, prospective looks.

## Repos (frozen by a rule fixed before any outcome was joined)

Survey 2026-11-11 (`git log` since 2024-01-01, counts only, no AI × cause join):

| repo | declared-AI commits | commits naming a cause | group |
|---|---:|---:|---|
| linux | 4,068 | 54,887 | primary |
| llvm-project | 4,662 | 2,957 | primary |
| mesa | 727 | 5,168 | primary |
| vscode | 9,921 | 562 | primary |
| ffmpeg | 276 | 650 | primary |
| openssl | 550 | 329 | primary |
| home-assistant | 4,609 | 175 | secondary |
| ruby | 1,799 | 227 | secondary |
| harfbuzz | 1,429 | 75 | secondary |
| bun | 789 | 83 | secondary |
| node | 471 | 81 | secondary |
| deno | 429 | 41 | secondary |
| cpython | 420 | 102 | secondary |
| llama.cpp | 256 | 125 | secondary |

- **Rule:**
  - **primary:** ≥ 250 declared-AI commits *and* ≥ 250 cause-naming commits since 2024;
  - **secondary:** ≥ 250 declared-AI commits and fewer than 250 cause-naming commits.
- **Surveyed and excluded:** systemd (23 AI), git (71), ghostty (97), php-src (12), rust (21), curl (2), redis (58),
  nDPI (29), prometheus (72).
- **New repos** that meet the rule later enter only a separate replication claim, registered when they are added.
  They never enter ARG-1 or ARG-2.
- Checkouts and paths are frozen in `events/arg_repos.json`. Each run fetches the repos first and records the heads.

## Definitions

- **Commits:** non-merge, since 2024-01-01, from each repo's first declared-AI commit on (its AI era). Both AI and
  other commits count.
- **Declared AI:** an AI tool named in a Co-authored-by / Assisted-by / Generated-by / "Generated with" line
  (`tools/ai_comments.tool_of`). A bare `Assisted-by: <person>` is not AI.
- **Named as a cause:** a later commit reverts it ("This reverts commit <sha>"), names it in a `Fixes: <sha>`
  trailer, or says it regressed, was introduced, broken or caused in / by / since / from `<sha>`.
  - The reference must resolve to a commit in the repo and not be the commit itself.
  - **Outcome Y** = named within **180 days** of the commit.
- **Eligible:** commits whose 180-day window has closed by the latest commit in the repo at that run.
- **Size:** lines added + deleted (`--numstat`, all files), binned 1–10, 11–50, 51–200, 201–1,000, > 1,000.
- **Author:** git author email, lowercased.

## Claims

| id | repos | test | supported iff |
|---|---|---|---|
| **ARG-1** | primary, pooled | Mantel-Haenszel risk ratio of Y, AI vs other, strata repo × author × size bin (so only authors with both AI and other commits of similar size inform it); author-cluster bootstrap 2,000, seed 2982; two-sided | the look's CI excludes 1 (direction named) |
| **ARG-2** | secondary, pooled | the same | the same |

- **Looks** (two-sided α per look; total 0.01 per claim):
  1. **2026-11-11** (α 0.002);
  2. **2027-05-11** (α 0.003);
  3. **2027-11-11** (α 0.005).
- A claim is decided at the first look whose CI excludes 1. If none does, the call at look 3 is:
  - **no meaningful difference** if the CI lies inside [0.8, 1.25];
  - **inconclusive** otherwise.
- **Power at each look:** ≥ 20 AI commits named as a cause in strata that also contain other commits. Below that the
  look is **underpowered** and spends nothing.
- Runs between looks are tracker runs: descriptive, never a verdict.

## Descriptive (every run)

- Per-repo counts, rates and within-author risk ratios (95% CI, not for verdicts).
- Rates by tool.

## Priors

- **No strong prior.** AI may raise the rate (unfamiliar code, plausible-looking bugs) or lower it (smaller, more
  routine tasks; more tests).
- The within-author, size-matched design removes who uses AI and how big the change is, but not **which tasks**
  people hand to AI.
- Look 1 will likely be underpowered: most AI commits are from 2026 and their windows have not closed.

## Known limits

- **Only explicit links count.** Bugs nobody traced back are invisible. Projects differ a lot in how often they trace
  (the survey's second column), which is why repo is a stratum.
- **Undeclared AI use sits in the "other" group** and biases toward 1.
- **Task selection is not controlled.**
- **A revert is not always a bug** (e.g. a premature merge). It is kept, because the REG rules count it too.
