# How do declared-AI commits comment? (EXPLORATORY, outcome-blind)

**Status: exploratory.** No fix or defect data is read. Script: `tools/ai_comments.py`. A commit is *declared AI* when its message names an AI tool in a Co-authored-by / Assisted-by / Generated-by / "Generated with" line. A bare `Assisted-by: <person>` is human help (curl's usage) and does not count. **Undeclared AI use is in the 'other' group**, which dilutes every contrast toward zero.

- commits since 2024-01-01 that add in-scope source lines (C/C++, Python, Go; tests, docs, vendor, examples excluded): 25,689; declared AI: 3,142
- **comment share** = added comment lines ÷ added non-blank lines; **prose** = comment lines with ≥ 4 words; Python counts `#` comments only (docstrings are strings).

## 1. Declared-AI vs other commits, same repo, since the repo's first declared-AI commit

| repo | AI commits (main tool) | other commits | median added lines AI / other | comment share AI | other | other, at AI's size mix | chars per comment AI / other | prose AI / other | danger AI / other | comments deleted per removed line AI / other |
|---|---|---:|---|---:|---:|---:|---|---|---|---|
| harfbuzz | 1,167 (claude) | 661 | 20 / 17 | **13.8%** | 11.9% | 12.4% | 38 / 34 | 64% / 54% | 1.5% / 1.0% | 11.2% / 11.0% |
| openssl | 215 (claude) | 1,179 | 17 / 9 | **20.6%** | 20.2% | 18.1% | 43 / 39 | 69% / 65% | 4.2% / 2.6% | 12.7% / 11.8% |
| redis | 39 (claude) | 543 | 51 / 15 | **23.8%** | 26.3% | 28.4% | 55 / 43 | 86% / 70% | 3.9% / 3.2% | 24.2% / 19.4% |
| ndpi | 5 | 566 | too few | | | | | | | |
| prometheus | 57 (claude) | 1,001 | 29 / 33 | **14.2%** | 12.1% | 17.8% | 59 / 58 | 85% / 88% | 3.6% / 3.9% | 19.5% / 10.8% |

## 2. The same people with and without declared AI

Authors with ≥ 5 declared-AI and ≥ 5 other commits after their repo's first AI commit. Per author: comment share of their AI commits minus that of their other commits, the other side re-weighted to the AI side's size mix.

- authors: **14** (openssl 7, harfbuzz 4, prometheus 2, redis 1)
- comment share, AI minus own other commits: median **+0.9%** (bootstrap 95% [-11.2%, +12.2%]); authors who comment more with AI: 7 of 14
- prose share of their comments, AI minus other: median +7% (10 of 13 higher with AI)

## 3. By tool (adopters pooled, declared-AI commits; gitgalaxy excluded)

| tool | commits | comment share | chars per comment | prose |
|---|---:|---:|---:|---:|
| claude | 917 | 18.0% | 43 | 70% |
| codex/openai | 526 | 7.4% | 43 | 70% |
| copilot | 21 | 19.6% | 51 | 87% |
| cursor | 11 | 23.0% | 62 | 88% |
| other-ai | 8 | 2.7% | 47 | 100% |

Within one repo, so the tool is not confounded with the project (tools with ≥ 30 commits there):

| repo | tool | commits | comment share | at the repo's other-commit size mix | chars per comment | prose |
|---|---|---:|---:|---:|---:|---:|
| harfbuzz | claude | 696 | 16.2% | 22.9% | 37 | 64% |
| harfbuzz | codex/openai | 466 | 7.1% | 9.1% | 42 | 69% |
| openssl | claude | 152 | 24.3% | 29.8% | 42 | 68% |
| openssl | codex/openai | 60 | 10.3% | 15.7% | 49 | 76% |
| prometheus | claude | 37 | 13.0% | 16.2% | 58 | 85% |

## 4. Commenting culture over time (all commits; comment share of added lines; AI share of commits in brackets)

| repo | 2024Q1 | 2024Q2 | 2024Q3 | 2024Q4 | 2025Q1 | 2025Q2 | 2025Q3 | 2025Q4 | 2026Q1 | 2026Q2 | 2026Q3 | 2026Q4 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| harfbuzz | 12% | 7% | 4% | 14% | 12% | 16% | 6% | 8% | 12% [37%] | 16% [84%] | 9% [62%] | 12% [85%] |
| openssl | 18% | 17% | 26% | 16% | 22% | 17% | 20% | 6% | 16% | 13% | 26% [25%] | 20% [46%] |
| redis | 31% | 26% | 19% | 26% | 23% | 31% | 26% [10%] | 33% | 28% | 23% [5%] | 29% | 24% [30%] |
| ndpi | 23% | 20% | 23% | 18% | 15% | 16% | 17% | 21% | 19% | 16% | 16% | 16% |
| prometheus | 10% | 10% | 10% | 9% | 8% | 9% | 6% | 11% | 12% | 15% | 12% [9%] | 11% [5%] |
| postgres (control) | 29% | 36% | 31% | 31% | 41% | 41% | 33% | 32% | 20% | 35% | 33% | 39% |
| libxml2 (control) | 25% | 19% | 16% | 13% | 14% | 63% | 40% | · | 12% | 18% | · | · |
| curl (control) | 20% | 13% | 23% | 19% | 13% | 16% | 14% | 13% | 23% | 13% | 17% | 13% |
| libgit2 (control) | 19% | 8% | 25% | 39% | 23% | · | 24% | 9% | · | 28% | 18% [6%] | · |
| gitgalaxy | · | · | · | · | · | · | · | · | · | 21% [5%] | 32% [78%] | 11% [99%] |

## 5. All-AI reference: gitgalaxy (every commit written with Gemini or Claude, per the owner)

Undeclared commits here are not human; the owner reports them as Gemini. Python, so not directly comparable with the C repos.

| group | commits | median added lines | comment share | at Claude's size mix | chars per comment | prose | danger | debt |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| declared Claude | 1,642 | 33 | 23.1% | 23.1% | 62 | 88% | 1.7% | 0.1% |
| undeclared (Gemini, per owner) | 361 | 16 | 23.1% | 23.2% | 54 | 81% | 3.7% | 0.1% |
| *human-written controls, pooled (C)* | 11,693 | 12 | 27.6% | | 35 | 59% | 2.6% | 0.2% |

· = fewer than 20 commits in the quarter. Comment share is computed over all commits in the quarter, AI and other.

Runtime 208s.

## Reading (hand-written; exploratory, outcome-blind)

- **"AI" is not one thing for comments. The tool matters more than whether AI was used.**
  - Within harfbuzz, Claude-assisted commits add comments at 16.2% of their lines and Codex-assisted ones at 7.1%;
    the repo's other commits sit at 11.9%.
  - OpenSSL shows the same split: Claude 24.3%, Codex 10.3%, other 20.2%.
  - Pooled as "AI vs not", the two cancel. That is why the declared-AI vs other comparison (§1) and the same-author
    comparison (§2) show no consistent change in *how much* is commented. Same authors: median +0.9%, 95% interval
    −11% to +12%, 7 of 14 authors higher.
- **What AI does change consistently is comment *style*.** AI comments are longer and read more like sentences:
  - prose share AI vs other: harfbuzz 64% vs 54%, OpenSSL 69% vs 65%, redis 86% vs 70%; prometheus is the exception
    (85% vs 88%);
  - within the same authors, 10 of 13 write more prose-like comments with AI (median +7 points).
- **Danger wording is a little higher in declared-AI commits** in the C repos: harfbuzz 1.5% vs 1.0%, OpenSSL 4.2% vs
  2.6%, redis 3.9% vs 3.2%. That matters for any danger-comment signal (DC-2) in the AI era: the lexicon may start
  measuring the tool's habits, not the author's worry.
- **No visible shift in project-level commenting yet (§4).** harfbuzz went from about 0% to 85% declared-AI commits
  in 2026, and its comment share stayed in its usual 6–16% band. Opposite-direction tools are one reason; the
  quarterly series are also noisy.
- **All-AI reference (gitgalaxy, §5).** Claude and Gemini (per the owner) comment at the same rate (23.1%). Claude's
  comments are longer (62 vs 54 characters) and more prose-like (88% vs 81%). Gemini's carry more danger words
  (3.7% vs 1.7%).
  - Both are far more prose-like than human-written C (59%), but Python vs C is a confound.
- **Limits.**
  - Only *declared* AI use is seen; undeclared use dilutes contrasts toward zero.
  - Tool choice is not random. In harfbuzz, Codex and Claude may be used by different people for different kinds of
    change; the size re-weighting does not remove that.
  - "Prose" is a crude ≥ 4-word rule.
  - 14 authors is a small within-person sample.
- **Possible registrations:**
  - "Claude-assisted commits add more comments than Codex-assisted ones in the same repo", on the repos that adopt
    both next. The data is growing every month.
  - "AI-assisted comments are more prose-like than the same author's own", on new authors.
