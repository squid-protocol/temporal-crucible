# KW — the keyword grammar of code: is signal co-occurrence a shared, cross-language structure, and does it form stable architectural modules? — registered 2026-11-06, before any co-occurrence statistic

**Why.**
- GitGalaxy's core measurement is per-function counts of keyword and structure signals: branching, safety guards,
  memory allocation, I/O, concurrency, error handling and so on.
- Earlier studies found that projects have stable keyword fingerprints (SIG 95.9%), and that individual signals
  (platform conditionals, library calls, `goto`) mark where specific kinds of work land.
- **Not yet asked: how signals relate to each other.**
  - Which appear together in the same function, and which avoid each other?
  - Is that pattern a property of code in general, or does it differ by language?
  - Do signals group into recurring "modules", an architectural vocabulary?
- KW uses the **language-crucible**: real, unmodified code from notable projects in about 35 languages.

## Data (fixed now)

- **Corpus:** `squid-protocol/language-crucible` @ `757545ba6fd6`, its `data/` tree exported with `git archive`.
  This excludes uncommitted local edits.
- **Scan:** engine `32619e4a5` (`galaxyscope-tc`, the study pin), `--spec-alignment`, git history off.
- **Units:** functions with loc ≥ 3.
- **Signals:** every per-function signal count column in `function_data`, **except**:
  - non-signal fields (ids, names, loc, complexity, args, keyword_density, archetype, z-score, graph metrics,
    token_mass, flags, `impact`);
  - whitespace and naming-style counters (`struct_tabs`, `struct_spaces`, `struct_camel_case`, `struct_snake_case`,
    `struct_pascal_case`, `struct_upper_case`, `struct_short_vars`, `struct_long_vars`).
- **Presence** = count > 0.
- **Signal families,** by name prefix: `struct`, `def`, `state`, `arch`, `threat`, `sec`, `lit`, model-related
  (`llm`, `ml`, `dl`), other.
- **Languages:** those with ≥ 500 functions, analysed separately. Within a language, a signal is used if present in
  ≥ 2% and ≤ 98% of its functions. A signal pair is used if both of its signals are used.

## Association

- For each (language, signal pair): the **Mantel–Haenszel log odds ratio of co-presence**, stratified by that
  language's **loc deciles**, with a 0.5 continuity correction.
- So "bigger functions contain more of everything" is removed: the association is within size.

## Claims (α = 0.01/3)

| id | claim | statistic | supported iff |
|---|---|---|---|
| **KW-H1** | **co-occurrence is a shared grammar across languages** | the mean, over language pairs, of the Pearson correlation of their log-OR vectors (pairs defined in both). Null: within each language independently, permute signal labels (2,000 rounds), preserving each language's marginal structure | observed mean > 99.67th percentile of the null **and** observed mean ≥ 0.30 |
| **KW-H2** | …**not an artefact of related detectors** | KW-H1 restricted to pairs whose two signals belong to **different families** (most definitional overlap is within a family) | same criteria |
| **KW-H3** | signals form **stable modules** across languages | per language: average-linkage hierarchical clustering of the used signals on distance = 1 − tanh(log OR / 2), cut to **k = 6** clusters. Statistic: the mean adjusted Rand index between every pair of languages' clusterings, on their shared signals. Null: permute signal labels per language (2,000) | observed mean ARI > 99.67th percentile of the null |

**Descriptive.**
- The strongest universal positive pairs (median log OR across languages) and negative pairs (signals that avoid each
  other).
- The consensus modules, from clustering the median association.
- Language-specific deviations: pairs whose association differs most from the cross-language median.
- Which languages are most and least "typical".

## Caveats fixed in advance

- The crucible is curated to be hard to parse, and the detectors are golden-tuned on it, so it is not a random
  sample of code. A population replication (a fresh multi-repo scan with the current engine) is the planned
  follow-up.
- Language counts are uneven (python about 2,800 functions, others about 500).
- Co-occurrence is within a function, not causal.

## Priors

- **H1 likely**: shared programming idioms such as allocation with cleanup, and guards with error handling.
- **H2 likely, smaller.**
- **H3 uncertain**: clustering is sensitive to the signal set, and k = 6 is a convention.

**Pre-run clarification (2026-11-06; no statistic on the crucible computed yet).** A synthetic check found that
size-only signals keep a small residual association within loc deciles: about +0.03 on average, but noisy. A
residual shared by every language could mimic a "shared grammar".

**Added size-only placebo, binding for H1 and H2:**
- Per language, simulate 20 datasets in which each used signal is drawn independently, with probability equal to its
  prevalence in the function's fine loc bin (50 quantile bins).
- Compute the same mean cross-language r on each.
- H1 and H2 now **also** require: observed − mean placebo r ≥ 0.10.

---

## Results — 2026-11-06 (scorer `71277b0`; report `kw.md`, matrices `kw_matrices.json`)

**Data.** 43,473 functions (loc ≥ 3); 22 languages with ≥ 500 functions, from Ada and AGC assembly to COBOL, Zig and
TypeScript.

| claim | observed | label-shuffle null (99.67th pct) | size-only placebo | verdict |
|---|---:|---:|---:|---|
| **KW-H1** mean cross-language r of co-occurrence | 0.167 | 0.037 | **0.242** | **not supported** (below the placebo; below 0.30) |
| **KW-H2** …cross-family pairs only | 0.182 | 0.043 | **0.258** | **not supported** |
| **KW-H3** module agreement (mean ARI, k = 6) | 0.083 | 0.028 | (none registered) | **SUPPORTED, weak**; may carry the same size leak |

**Reading.**
- Co-occurrence is far from random across languages (r ≈ 0.17 against a shuffle null of about 0).
- **But size-only signals reproduce even more cross-language agreement (0.24).** At decile stratification, the
  apparent "universal grammar" is dominated by function size leaking through: long functions contain more of
  everything, consistently in every language.
- The size placebo, added before the run, is what caught this. Without it, H1 would have looked like a success.

**Beyond size (exploratory, after scoring; `tools/exploratory/kw_beyond_size.py`).**
- Method: subtract each pair's size-placebo association (20 simulations) from its real association.
- **The residual is still shared across languages: mean r = 0.12** (230 language pairs; shuffle null ≈ 0). There is
  a modest genuine grammar.
- **Universal beyond-size pairs**, median residual log OR (share of languages agreeing in sign):

| relationship | residual | agreement | reading |
|---|---:|---:|---|
| safety guard + branch | **+1.19** | 76% of 21 | defensive logic is branching logic |
| concurrency + linear code | +1.01 | 73% | |
| early exit (bailout) + branch | +0.76 | 76% | |
| concurrency + safety guard; concurrency + early exit | +0.73 / +0.66 | 64–83% | concurrent code is guarded code |
| cleanup + safety guard | +0.58 | **91%** | guard-and-release idiom |
| **API surface × branch** | **−0.49** | **93%** | API or declaration functions are branch-free wrappers |
| **early exit × state mutation** | **−0.50** | 82% | state-mutating code rarely bails out |

**What this suggests architecturally.** A recurring "defensive control" module (branch, guard, early exit, cleanup;
concurrency joins it), kept apart from two other roles: **interface code** (API surface, branch-free) and
**state-mutation code** (no early exits). This is the clearest form of the module result.

**Next (needs fresh data to be confirmatory).**
- Re-register the beyond-size claims (placebo-corrected association shared across languages; the specific pairs and
  modules above, as directional predictions) on the **population scan** the owner proposed: local repos rescanned with
  the current engine into `gitgalaxy_raw_output`.
- A finer size control, such as per-line densities or exact-loc matching, belongs in the design from the start.

---

## KW-R — method check: stoichiometric (compositional log-ratio) co-occurrence — registered 2026-11-06, before KW-R ran

**Why.** KW's decile stratification leaked size: a size-only placebo produced *more* cross-language agreement than
real code. Population-analyses' file-composition "stoichiometry" uses **shares**, which are size-free. KW-R applies
that idea to signals: compare signals by their **ratios** within each function, so a function that is twice as big
with twice of everything looks identical.

**This is a method check on the same crucible scan, not a confirmation.** The crucible's beyond-size pairs were seen
in KW's exploratory step. Confirmation belongs on a fresh population scan.

**Measure.**
- Per language (KW's languages and used signals), keep functions whose total count over the used signals is ≥ 3.
- **Per-function centred log-ratios:** clr_s = log(c_s + 0.5) − the mean over used signals of log(c + 0.5).
- **Pair association = proportionality** ρ_ij = 1 − var(clr_i − clr_j) / (var(clr_i) + var(clr_j)), across that
  language's functions.
- **Cross-language agreement:** the mean Pearson r over language pairs of their ρ vectors on shared pairs, as KW.

**Size-only placebo.**
- Per language, 20 simulated datasets with counts c_s ~ Poisson(λ_s · loc), where λ_s is the language's per-line
  rate of signal s.
- Signals are therefore independent and scale only with size.
- The same filter and statistic are applied.

| id | claim | supported iff |
|---|---|---|
| **KWR-H1** | **the ratio method removes size** | placebo mean cross-language r ≤ 0.05 |
| **KWR-H2** | grammar remains under ratios | real mean r > label-shuffle null 99.5th percentile (2,000) **and** real − placebo ≥ 0.10 |

**Sensitivity (descriptive):** pseudocounts 0.1 and 1.0; the top universal ρ pairs.

### KW-R results — 2026-11-06 (scorer `bf6023c`; report `kwr.md`)

| claim | result | verdict |
|---|---|---|
| **KWR-H1** ratios remove size | size-only placebo cross-language r = **0.221** (bar ≤ 0.05; the decile method gave 0.242) | **not supported** |
| **KWR-H2** grammar under ratios | real 0.247; shuffle null 0.032; real − placebo **+0.026** | **not supported** |

Pseudocount sensitivity: 0.1 gives 0.207 / 0.149 and 1.0 gives 0.270 / 0.248 (real / placebo). The conclusion holds
at every setting.

**Reading.**
- **Per-function log-ratios do not remove the artefact, because functions are sparse.** Most signals count 0 or 1
  per function, so log-ratios are dominated by zeros and the pseudocount.
- What is left mostly encodes **how common each signal is**, and that is similar in every language.
- The very common `struct_branch` comes out "anti-proportional" to nearly everything, often with 100% sign agreement.
  This is the closure artefact of compositional data, not grammar.
- **Both function-level methods (deciles and ratios) are dominated by size plus signal frequency.**
- Population-analyses' "stoichiometry" works because it applies **shares at the file level**, where counts are dense.
  Note that its *set-of-active-traits* signatures, in `mine_dna_stoichiometry.py`, do **not** remove size.

**Implication for the confirmatory design (population scan).**
1. Make **placebo correction the primary measure** (real minus size-and-frequency placebo association). It is the
   only one of the three that left a cross-language residual (decile residual r 0.12, exploratory).
2. Measure grammar at the **file level**, on composition shares of signals or of function archetypes, where
   compositional methods are well posed.
3. Keep both placebos binding.

### Exploratory: yes/no presence with a continuous size model (after KW and KW-R; `tools/exploratory/kw_presence_oe.py`)

**Method.**
- Presence per function (yes/no).
- Per language and signal, a logistic model of presence on log loc (plus its square).
- Pair association = log(observed co-presence ÷ the co-presence expected if the two signals were independent given
  each function's size).

**The method passes its size check:**

| | cross-language r |
|---|---:|
| real | **0.112** |
| size-only placebo | **0.003** (deciles 0.242, ratios 0.221) |
| shuffle null, 99.5th percentile | 0.029 |
| real, without `struct_branch` | 0.110 |

**A modest shared grammar, and it is not branch-driven.** Pairs that occur together more than size predicts (median
over languages; share of languages agreeing):

| together more | × size-expected | agreement |
|---|---:|---:|
| concurrency + early exit (bailout) | 1.73 | 83% |
| cleanup + safety guard | 1.22 | **91%** |
| safety guard + early exit | 1.18 | 88% |
| negative-safety state + cleanup / comprehensions / closures | 1.26–1.31 | 73–82% |
| API + concurrency | 1.33 | 75% |

| together less | × size-expected | agreement |
|---|---:|---:|
| concurrency × casts | 0.71 | 83% |
| early exit × state mutation | 0.90 | 88% |
| API × branch | 0.92 | 87% |
| API × casts | 0.91 | 83% |

**Reading.**
- The same structure appears under three differently built analyses (decile-placebo residual, this model; and partly
  under ratios). The cleanest version is a **"defensive control" cluster**: guards, early exits, cleanup and
  concurrency, kept apart from interface (API) code and from state-mutation code.
- **Effects are modest** (×0.7 to ×1.7). This is a grammar of tendencies, not rules.

**Confirmation plan.** Register this measure, with these pairs as signed directional predictions, on the population
scan, both at function level and at file level. Size placebo and shuffle null are binding.
