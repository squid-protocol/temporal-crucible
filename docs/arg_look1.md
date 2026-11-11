# ARG — are declared-AI commits named as the cause of later fixes more often? (living study)

Registration `docs/arg_hypotheses.md`. Run 2026-11-11; **scheduled look 1** (two-sided α = 0.002). Window 180 days; author-cluster bootstrap 2000, seed 2982. Aggregates only.

- repo heads: linux `067c5c24cef2` (data to 2026-11-10), llvm-project `fe5542793246` (data to 2026-11-11), mesa `47d4c9ac15af` (data to 2026-11-11), vscode `cb9ed5a1db50` (data to 2026-11-11), ffmpeg `7b00cbd7edf6` (data to 2026-11-11), openssl `df281a12096f` (data to 2026-11-11), home-assistant `4116717bae28` (data to 2026-11-11), ruby `0738c9dfaa45` (data to 2026-11-11), harfbuzz `8d01a1b14895` (data to 2026-11-11), bun `447ff870b609` (data to 2026-11-11), node `50ce73fe07b9` (data to 2026-11-11), deno `e7b39ebd55c8` (data to 2026-10-26), cpython `a8720240f12e` (data to 2026-11-11), llama.cpp `2cbe0ec429b8` (data to 2026-11-11)

## Registered claims (pooled MH risk ratio, strata repo × author × commit size)

| id | repos | AI commits (named) | other commits (named) | rate AI / other | RR (within author, size-matched) | 99.8% CI | AI events in informative strata | call |
|---|---|---|---|---|---:|---|---:|---|
| **ARG-1** | primary | 3,162 (51) | 117,676 (4390) | 1.61% / 3.73% | **0.96** | [0.51, 1.49] | 43 | **no verdict yet: continue to the next look** |
| **ARG-2** | secondary | 3,352 (29) | 34,870 (166) | 0.87% / 0.48% | **1.25** | [0.19, 12.32] | 29 | **no verdict yet: continue to the next look** |

## Tracker (descriptive, every run)

| repo | AI-era commits eligible | AI | named as cause: AI / other | rate AI / other | RR (within author, size-matched) |
|---|---:|---:|---|---|---:|
| linux (primary) | 53,526 | 235 | 14 / 3229 | 5.96% / 6.06% | 0.90 [0.27, 1.63] |
| llvm-project (primary) | 44,756 | 657 | 4 / 868 | 0.61% / 1.97% | 0.40 [0.09, 1.08] |
| mesa (primary) | 1,444 | 30 | 4 / 62 | 13.33% / 4.38% | nan [nan, nan] |
| vscode (primary) | 20,038 | 2,202 | 29 / 196 | 1.32% / 1.10% | 1.12 [0.70, 1.68] |
| ffmpeg (primary) | 107 | 1 | 0 / 1 | 0.00% / 0.94% | nan [nan, nan] |
| openssl (primary) | 967 | 37 | 0 / 34 | 0.00% / 3.66% | nan [nan, nan] |
| home-assistant (secondary) | 15,225 | 1,291 | 0 / 3 | 0.00% / 0.02% | 0.00 [nan, nan] |
| ruby (secondary) | 2,870 | 178 | 2 / 30 | 1.12% / 1.11% | 0.41 [0.41, 0.41] |
| harfbuzz (secondary) | 1,302 | 715 | 10 / 4 | 1.40% / 0.68% | 1.78 [1.78, 1.78] |
| bun (secondary) | 2,854 | 718 | 14 / 20 | 1.95% / 0.94% | 5.14 [0.79, 23.31] |
| node (secondary) | 551 | 14 | 0 / 2 | 0.00% / 0.37% | nan [nan, nan] |
| deno (secondary) | 2,089 | 402 | 3 / 16 | 0.75% / 0.95% | 0.23 [0.20, 0.26] |
| cpython (secondary) | 11,110 | 19 | 0 / 84 | 0.00% / 0.76% | nan [nan, nan] |
| llama.cpp (secondary) | 2,221 | 15 | 0 / 7 | 0.00% / 0.32% | 0.00 [nan, nan] |

- by tool (all repos, raw rate named as cause): claude 1.39% of 3,242, copilot 1.01% of 2,984, codex/openai 2.82% of 177, other-ai 0.00% of 79, cursor 0.00% of 32
- rates are per commit within the window; CIs in the tracker are 95% and not for verdicts

Runtime 969s.

## Reading (hand-written)

- **Look 1 of 3: no verdict, as designed.**
  - **ARG-1** had enough events to look (43 AI commits named as a cause in strata with both kinds of commits;
    ≥ 20 required). It spent α = 0.002 and did not cross: RR 0.96, 99.8% CI [0.51, 1.49].
  - **ARG-2:** 1.25 [0.19, 12.3].
  - Both continue to look 2 (2027-05-11).
- **The raw gap is misleading.** In the primary repos, AI commits are named as a cause *less* often than other
  commits (1.6% vs 3.7%). Once the same author's commits of the same size are compared, the ratio is about 1 (0.96).
  The raw difference is who uses AI and how big their commits are, not what AI does. That is why the registration
  compares within author.
- **Per-repo rows (tracker, 95%, not verdicts):** Linux 0.90, LLVM 0.40 [0.09, 1.08], VS Code 1.12; the rest are too
  thin. They point in different directions, consistent with no common effect so far.
- **Power so far is thin.** Most declared-AI commits are from 2026; only 3,162 primary AI commits have a closed
  180-day window. Mesa and OpenSSL alone add about 1,200 more by look 2.
- **Instrument checks (outcome-blind, before the look).** In a random sample of 30 Mesa and OpenSSL cause links,
  about 27 were genuine bug-to-culprit links (`Fixes: <sha>`); the rest were softer (a refactor, a test list, a
  typo).
- **Next:** `python tools/ai_regress.py --fetch --look 2` on or after 2027-05-11.
