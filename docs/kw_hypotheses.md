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
