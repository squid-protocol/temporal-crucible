# KW-P — does the language-crucible's keyword grammar hold across a population of independent repos? — registered 2026-11-07, before any KW-P statistic

**Why.** On the language-crucible, yes/no signal presence with a continuous size model showed a modest shared
cross-language grammar (size-only placebo 0.003, real r 0.112; exploratory). It held in 69% of pair signs in five C
repos (GR-H1). The population scan makes a large, independent confirmation possible.

## Data

- **Population DB:** `gitgalaxy-population-analyses/data/master_db_v2.12.0-b64f42bf.db`.
  - Merged from batch `gitgalaxy-raw-output/v2.12.0-b64f42bfcfb7`: engine origin/main `b64f42bfcfb7`, full precision,
    745 targets.
  - Integrity report: perfect match; 8,173,786 functions.
- **Independence:** the 92 population repos whose name (case-insensitive) matches a crucible source folder are
  **excluded**. The list is in `events/sources/crucible_source_repos_757545ba6fd6.txt`, crucible @ `757545ba6fd6`.
- **Units:** functions with loc ≥ 3.
- **Languages:** those with ≥ 5,000 such functions in ≥ 5 non-excluded repos. Per language, a seeded sample of up to
  200,000 functions (seed 2982).
- **Signals and presence:** KW's definitions. A language uses the signals with 2–98% prevalence.
- **Engine caveat:** the crucible grammar came from engine `32619e4a5`; the population from `b64f42bf`. Signal
  definitions may have shifted in between.

## The grammar under test (fixed before any population number)

GR's crucible consensus: signal pairs defined in ≥ 11 crucible languages with ≥ 70% sign agreement of the median
log(O/E) (`kw_presence_oe` method). Each pair's **predicted sign** = that median's sign.

## Association (KW's exploratory method)

- Per language and signal: a logistic model of presence on log loc and its square.
- Pair association = log((observed co-presence + 0.5) ÷ (co-presence expected under size-conditional
  independence + 0.5)).

## Claims (α = 0.01/3)

| id | claim | supported iff |
|---|---|---|
| **KWP-H1** | the crucible grammar's signs hold in the population | pooled over (language × consensus pair) cells, the share whose sign matches the prediction > 50%, exact binomial p < α |
| **KWP-H2** | the shared grammar is real beyond size, at scale | mean cross-language r of population log(O/E) vectors > the 99.67th percentile of a signal-label shuffle (1,000), **and** > the size-only placebo mean (5 simulations) + 0.05 |
| **KWP-H3** | it holds within **individual repos**, not just pooled (functions cluster in repos) | for (repo × language) units with ≥ 2,000 functions, per-unit sign agreement on consensus pairs. The share of units with agreement > 50% is > 50%, binomial p < α |

**Descriptive.**
- Per-language agreement.
- The pairs that replicate most and least.
- Pairs whose population sign is opposite to the crucible's.
- The distribution of per-repo agreement.

## Priors

- **H1 likely:** GR found 69% in C.
- **H2 likely:** large n.
- **H3 uncertain:** repos may have their own "accents" (KW-follow-up 3).

---

## Results — 2026-11-07 (scorer `c11cfe7`; report `kwp.md`)

**Data.** 2,889,002 population functions (loc ≥ 3) after excluding the 92 crucible-source repos; 22 languages; 32
consensus pairs.

| claim | result | verdict |
|---|---|---|
| **KWP-H1** crucible signs hold pooled | **328 / 420 = 78%** of language × pair cells; p = 1.9 × 10⁻³² | **SUPPORTED** |
| **KWP-H2** shared grammar beyond size | cross-language r **0.235** (228 language pairs); shuffle 99.67th 0.031; **size placebo −0.006** | **SUPPORTED** |
| **KWP-H3** holds within repos | **169 / 174** repo × language units agree on > 50% of pairs (97%); median 76%; p = 5 × 10⁻⁴⁴ | **SUPPORTED** |

**Per language.**
- Agreement is highest in C++ 92%, MATLAB 91%, Python 90%, C# 88% and C 88%; Go, TypeScript, Perl and Ruby are
  82–85%.
- It is lowest in Zig 63%, COBOL 57% (7 pairs), CSS 56%, Fortran 50% and YAML 50%.

**Most replicated pairs** (crucible sign; share of languages agreeing):
- safety guard + cast **100%** (15 languages);
- cleanup + safety guard **100%**;
- encapsulation + branch **100%**;
- concurrency + linear code **100%**;
- concurrency × cast (negative) **100%**;
- safety guard + early exit **94%** (16);
- safety guard + branch **89%** (19);
- early exit + branch **89%** (18).

**Least replicated:** branch × closures (−) 40%; API × cast (−) 50%; I/O + state mutation (+) 50%; API + concurrency
(+) 56%.

**Reading.**
- **The keyword grammar is confirmed at population scale, on independent code.** Learned from 22 languages of
  crucible snippets, its pair signs hold in 78% of cells across about 2.9 million functions in about 550 unseen
  repos.
- Its cross-language agreement (0.235) is **twice** the crucible's (0.112), against a size-only placebo of ~0. More
  data sharpens it.
- **It is not an average over a few repos.** 97% of individual repo × language units follow it.
- **The defensive-control core is the most universal part.** Safety guards travel with casts, cleanup, early exits
  and branching in essentially every language. The interface and state-mutation contrasts are less universal.
- **Weak in declarative and data-oriented languages** (CSS, YAML), and in Fortran and COBOL. Their constructs map
  poorly onto these signals, or carry a different grammar: a candidate "dialect" result for the next study.
- **This upgrades KW's exploratory finding to a confirmed, replicated one,** the strongest result in the keyword
  line of work.

**Caveat.** The crucible grammar was built with engine `32619e4a5` and the population scanned with `b64f42bf`.
Agreement despite any definition drift strengthens rather than weakens the result.
