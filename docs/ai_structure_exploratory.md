# Structural footprint of declared-AI vs other commits (EXPLORATORY, outcome-blind)

**Status: exploratory.** No fix or defect data is read. Script: `tools/ai_structure.py`. Functions touched by each commit are read before and after with tree-sitter and the engine's C/C++ rules, as in LAT-F; shapes are placed on LAT's frozen lattice (`a27d2c93f817`). Declared AI = an AI tool named in a commit trailer (as in `docs/ai_comments_exploratory.md`). Undeclared AI use is in the 'other' group.

- commits since 2024-01-01 with touched C/C++ functions: 18,932 (declared AI 1,284); function changes 117,731 (modified 94,215, born 23,516)
- Comparisons are within repo, after the repo's first declared-AI commit. The 'other' side is re-weighted to the AI side's mix of lines changed per function (1–2, 3–8, 9–32, 33–128, > 128).

## 1. Modified functions: does the shape move?

| repo | modified fns AI / other | median lines changed AI / other | shape moved AI | other (size-matched) | family changed AI / other | signals gained per fn AI / other | defensive signals added per 100 changed lines AI / other | branches added per 100 changed lines AI / other |
|---|---|---|---:|---:|---|---|---|---|
| harfbuzz | 3,164 / 1,764 | 5 / 5 | **20%** | 18% | 3% / 3% | 0.16 / 0.16 | -0.06 / +0.23 | +3.77 / +2.69 |
| openssl | 584 / 4,275 | 7 / 4 | **21%** | 24% | 1% / 1% | 0.14 / 0.23 | +0.16 / +0.63 | +1.84 / +4.08 |
| redis | 363 / 3,252 | 6 / 6 | **19%** | 14% | 1% / 2% | 0.18 / 0.12 | +0.83 / +0.63 | +10.63 / +6.15 |
| ndpi | 9 / 3622 | too few | | | | | | |

## 2. Calls: do AI commits add new dependencies?

| repo | modified fns adding ≥ 1 new callee AI | other (size-matched) | new callees per modified fn AI / other (size-matched) | share of added callees defined in the same file AI / other |
|---|---:|---:|---|---|
| harfbuzz | 47% | 47% | 0.89 / 0.87 | 19% / 19% |
| openssl | 45% | 49% | 0.79 / 0.76 | 26% / 14% |
| redis | 67% | 59% | 1.36 / 1.09 | 28% / 28% |

## 3. Footprint per commit

| repo | commits AI / other | files touched per commit AI / other | functions touched | share of touched functions that are new | functions deleted per commit |
|---|---|---|---|---|---|
| harfbuzz | 1,027 / 556 | 2.6 / 2.3 | 4.9 / 5.0 | 37% / 37% | 0.87 / 0.86 |
| openssl | 208 / 1,100 | 2.2 / 3.0 | 3.8 / 4.9 | 25% / 20% | 0.12 / 0.34 |
| redis | 39 / 524 | 4.5 / 3.2 | 22.4 / 9.6 | 59% / 36% | 1.74 / 0.34 |

Footprint rows are not size-matched: a bigger change touches more, by construction.

## 4. Functions born in AI vs other commits

| repo | born AI / other | median loc AI / other | median rung k AI / other | defensive signals per 100 loc AI / other | callees per fn AI / other | top lattice family AI / other |
|---|---|---|---|---|---|---|
| harfbuzz | 1,846 / 1,038 | 9 / 11 | 6 / 6 | 5.40 / 2.07 | 3.3 / 3.2 | F8 (72%) / F8 (71%) |
| openssl | 199 / 1,092 | 12 / 13 | 7 / 7 | 0.89 / 1.66 | 3.7 / 3.2 | F8 (60%) / F8 (53%) |
| redis | 512 / 1,802 | 9 / 12 | 7 / 7 | 1.75 / 1.58 | 4.0 / 4.4 | F8 (72%) / F7 (55%) |
| ndpi | 6 / 410 | too few | | | | |

## 5. The same people, and the tools

- authors with ≥ 10 AI and ≥ 10 other modified functions: **13**
- shape moved, AI minus own other (size-matched): median **-0%**; higher with AI for 6 of 13
- new callees per modified function, AI minus own other: median +0.28; higher with AI for 11 of 13

| repo | tool | modified fns | shape moved | other commits, size-matched | new callees per fn |
|---|---|---:|---:|---:|---:|
| harfbuzz | claude | 1,898 | 17% | 19% | 0.95 |
| harfbuzz | codex/openai | 1,259 | 24% | 18% | 0.81 |
| openssl | claude | 377 | 17% | 23% | 0.72 |
| openssl | codex/openai | 198 | 27% | 25% | 0.92 |
| redis | claude | 287 | 20% | 14% | 1.52 |
| redis | copilot | 70 | 17% | 12% | 0.73 |

## 6. Era check: control repos (no declared AI), 2026 vs 2024–25, same measures

| repo | modified fns 2024–25 / 2026 | shape moved 2024–25 | 2026 (size-matched to 2024–25) | new callees per fn 2024–25 / 2026 |
|---|---|---:|---:|---|
| postgres | 16,786 / 9,799 | 16% | 19% | 0.56 / 0.57 |
| libxml2 | 4,985 / 155 | 20% | 6% | 0.63 / 0.46 |
| curl | 14,171 / 7,233 | 17% | 16% | 0.54 / 0.43 |
| libgit2 | 999 / 398 | 18% | 28% | 0.66 / 0.50 |

Runtime 281s.

## Reading (hand-written; exploratory, outcome-blind, no intervals)

- **AI-assisted changes do not change function shape more or less often.** At matched edit size, the share of
  modified functions whose fingerprint moved is:
  - harfbuzz 20% vs 18%, OpenSSL 21% vs 24%, redis 19% vs 14%;
  - within the same 13 authors, median 0 (6 of 13 higher with AI);
  - lattice family changes are rare (1–3%) either way.
  - The control repos drift as much from one year to the next with no AI at all: libgit2 18% → 28%, libxml2
    20% → 6% on small 2026 samples. So differences of a few points are within ordinary variation.
  - **Structure stays put.** The program's "structure describes" picture holds for AI-assisted work.
- **The one consistent difference: AI-assisted changes add new callees (new dependencies).**
  - Within the same authors, AI commits add more new callees per modified function: median +0.28, for 11 of 13
    authors.
  - Repo-level gaps are small but in the same direction: harfbuzz 0.89 vs 0.87, OpenSSL 0.79 vs 0.76, redis 1.36 vs
    1.09.
  - In OpenSSL the extra calls are more often to functions in the same file (26% vs 14%), and AI commits create
    slightly more new functions (25% vs 20% of touched functions). That fits factoring logic out into new local
    helpers.
- **Tools differ again.** Codex-assisted commits move function shapes more than the repo's other commits (harfbuzz 24%
  vs 18%, OpenSSL 27% vs 25%). Claude-assisted ones move them less (harfbuzz 17% vs 19%, OpenSSL 17% vs 23%). The
  comment study found the two tools pulling apart too.
- **No consistent "AI adds guards".**
  - Defensive signals added per 100 changed lines: AI lower in harfbuzz and OpenSSL, higher in redis.
  - Functions *born* in AI commits are 2.6× more guard-dense in harfbuzz (5.4 vs 2.1 per 100 loc), but half as
    guard-dense in OpenSSL (0.9 vs 1.7).
  - Branching follows the same split.
  - These look like project-by-tool habits, not a property of AI.
- **What AI writes from scratch looks like what humans write there.** AI-born functions are a little smaller (median
  9–12 lines vs 11–13), at the same lattice rung, mostly in the same family (F8).
- **Footprint depends on how a project uses AI.** redis's 39 declared-AI commits are big feature drops (22 functions
  touched, 59% new). OpenSSL's AI commits are smaller than its others. harfbuzz's are the same size.
- **Limits.**
  - Declared AI only.
  - No intervals; this is exploratory.
  - harfbuzz carries most of the AI sample.
  - Who uses which tool for what is not random.
  - Duplication (`state_slop_duplicates`) and rework were not measured here.
- **Possible registration:** "AI-assisted changes add more new callees than the same author's other changes", on
  authors and repos that adopt AI after today. It is the one pattern consistent across people.
