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

---

## Exploratory (not registered): keyword anatomy of archetypes, and the fingerprint distribution (`tools/exploratory/arch_anatomy.py`; report `arch_anatomy_exploratory.md`)

**Circularity:** archetypes were clustered on these signal densities. Per-archetype presence follows partly by
construction; the within-archetype pair grammar is the informative part.

**Structural absences.** Among signals with ≥ 5% overall prevalence, true near-zeros (< 0.1%) are rare:
- **Parameter Forwarders never contain safety checks, generics or casts.** They are pure pass-through code.
- **State Mutators never start a class.**
- Every other archetype contains every common signal at least occasionally. Archetypes differ by *degree*, not by
  hard exclusion.

**The confirmed pair grammar holds inside 12 of 14 archetypes:**
- Compute Cores 90%; Parameter Forwarders 89%; Encapsulated Accessors 87%; Generic / Templated and Callbacks /
  Closures 86%.
- It is weak only in **C Struct Operations (56%)** and **State Mutators (60%)**, each with few testable pairs.
- So the grammar is **not an artefact of mixing archetypes**: it holds *within* kinds of function, which is the less
  circular test.

**Fingerprint distribution** (exact signal-presence signatures over 6.94M functions):
- **314,979 distinct signatures. Just 205 cover half of all functions; 19,238 cover 90%.**
- 57% of signatures are singletons, but they hold only 2.6% of functions.
- Rank–frequency slope **−1.28**: steeper than Zipf (−1), i.e. more concentrated than word frequencies in natural
  language.
- The per-line density profile is genuinely **high-dimensional**: 3 components explain only 30%, and the
  participation ratio is 15.7 effective dimensions out of 20.
- **Reading:** most code is built from a small vocabulary of a few hundred recurring keyword combinations, plus a
  long tail of rare ones. The space they live in is not reducible to a handful of axes. That supports a
  multi-signal fingerprint over a few summary scores.

### Exploratory: the five most common fingerprints (`tools/exploratory/top_signatures.py`; report `top_signatures_exploratory.md`)

The top 5 exact signal-presence signatures cover 8.9% of 6.94M functions. They fall into two families.

**Universal "bricks":** tiny, cross-language, and they differ from each other by one signal.

| # | signals | share | repos | median size | in tests | what it is |
|---|---|---:|---:|---:|---:|---|
| 1 | linear + args + function start | 2.6% | 386 | 3 lines | 35% | the one-step function: a wrapper, delegator, stub, or tiny pure computation (`easeInQuint`). JS / C++ / TS / Kotlin / Swift … |
| 2 | #1 + **API** (public / exported) | 2.5% | 318 | 4 | 23% | public one-liners: `toString`, `getName`, `equals`, `hashCode`, `__construct`, `getValue`. PHP / Python / Java / C / C# |
| 5 | #2 + **state mutation** | 1.2% | 294 | 5 | 35% | public setters and initialisers: `__construct`, `setUp`, `init`, `setX`. PHP / Python / C# / Java |

**Dialect shapes:** large, C-only, and concentrated in a few repos (examples are from Linux, FreeBSD, ReactOS).

| # | signals | share | repos (largest single repo) | median size | in tests | what it is |
|---|---|---:|---:|---:|---:|---|
| 3 | branch + linear + args + struct + mutation + pointers + `static` | 1.4% | 40 (77%) | 23 | 1% | kernel-driver C: `*_probe`, `vidioc_*`, lock-annotated (`__acquires` / `__releases`) functions |
| 4 | linear + args + pointers + `static` | 1.3% | 89 (57%) | 5 | 3% | static C pointer accessors: `impl_from_IUnknown`, `to_state`, `container_of`-style casts |

**Reading.**
- The commonest code is a **ladder of tiny bricks**: one-step function → public one-step function → public one-step
  mutator. Each rung adds one keyword family. They recur in hundreds of repos and every major language, and a third
  sit in tests.
- Next come **regional dialects**: kernel-style C shapes that are large, branchy and pointer-heavy, owned by a few
  repos.
- So the vocabulary has a **universal core** (bricks) plus **ecosystem idioms**.
- **Measurement note:** shape #1 also captures functions that only return a big string or template (`infoPlist` in
  Go) and COM `E_NOTIMPL` stubs. The signal set sees no branch or call structure there, so they look "linear".

### Correction: what two signal names actually mean (2026-11-07; from `record_keeper.py`'s rule → column map, engine `b64f42bf`)

| column | engine rule | what it actually counts | earlier (wrong) description in this program |
|---|---|---|---|
| `struct_linear` | `structural_boundaries` | structural **keywords**: `return`, `def`, `function`, `void`, `export`, `class`, `break`, `continue`… (per language) | "linear / straight-line code" |
| `state_safety_neg` | `safety_bypasses` | constructs that **bypass** safety (per-language rule) | "negative safety checks (e.g. `!ptr`)" |

- The **statistics are unaffected**: the signals are the same. Only the plain-language readings change.
- Read "concurrency + linear code" as "concurrency + structural keywords".
- Read pairs with "negative-safety" as "safety-bypass constructs".
- Also confirmed: `arch_api` = the **public / exported** surface. Python: a `def` / `class` whose name does not start
  with `_`. TypeScript: `export` / `public`. Java: `public` / `protected`. C: a non-static function definition.
- Fingerprint #1 is therefore "a function with arguments and a structural keyword (usually `return`), and nothing
  else". #2 adds "and it is public".

### Exploratory: fingerprint #6 (`top_signatures.py --top 6`)

- **Signals:** branch + structural keywords + args + function start + state mutation + pointers + `static`. That is #3 without
  `struct_class_start`.
- **Size and spread:** 73,614 functions (1.1%), 84 repos (largest 39%), 98% C, median 19 lines, 2% in tests.
- **What it is:** ReactOS / Wine COM methods (`*_AddRef`, `*_QueryInterface`), graphics primitives (`putimage`, `vertline`),
  and driver `init_hw`.
- **Reading:** the private-C family (#3, #4, #6) forms its own ladder.
  - #4 = static pointer one-liner;
  - #6 = #4 + branch + mutation;
  - #3 = #6 + struct declarations.

  It mirrors the public OO ladder (#1 → #2 → #5).
- **Corpus caveat:** these shapes are concentrated in a few OS-scale repos (Linux, FreeBSD, ReactOS, Haiku). The function-weighted
  ranking reflects corpus composition; the bricks (#1, #2, #5) are the shapes that hold across hundreds of repos.
- **Coverage gap seen here:** Windows `Interlocked*` is not counted as concurrency in C (gitgalaxy#8016 comment).

### Exploratory: draft family trees (`tools/exploratory/fingerprint_trees.py`, `fingerprint_tree_viz.py`)

The top 200 signatures (49.7% of functions) form two trees.

**Growth tree:**
- Each shape hangs under its most common sub-shape. 196 of 199 edges add exactly **one** signal.
- 148 shapes have at least one other one-signal parent among the 200 (219 alternative edges, the gray dotted lines in
  `docs/fingerprint_tree.html` / `.png`).

**Similarity families** (average-linkage Jaccard, 14 clusters):

| family | share | spread |
|---|---:|---|
| F7 public / general | 17.5% | 504 repos |
| F8 private C + pointers | 15.8% | 356 repos, Linux 34% |
| F6 bare one-step functions | 4.7% | |
| F3 annotated / test methods | 3.3% | Java / Rust / C#, 53% tests |

Smaller families: Rust pointer code, generics, and shell / config fragments.

Draft only: rules as of `b64f42bf` (before #8010 / #8011 / #8016), function-weighted.
