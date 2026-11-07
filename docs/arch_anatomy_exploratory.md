# EXPLORATORY — keyword anatomy of function archetypes, and fingerprint distribution (population DB v2.12.0-b64f42bf)

**Circularity:** archetypes are clustered on these signal densities, so presence rates partly follow by construction. Structural absences and within-archetype pair grammar are the informative parts.

- functions (loc ≥ 3): 6,936,799; signals 89; signals present in ≥ 5% overall: 20

## Structural absences and near-universals per archetype (signals with ≥ 5% overall prevalence)

| archetype | n | never (< 0.1%) | almost always (≥ 90%) |
|---|---:|---|---|
| Parameter Forwarders | 957,185 | def_safety, struct_generics, state_cast_hits | struct_linear, struct_args, struct_func_start |
| Compute Cores | 616,724 | — | struct_branch, struct_linear, struct_args, struct_func_start |
| Defensive Guards | 562,117 | — | struct_linear, struct_args, struct_func_start, def_safety |
| Interface Declarations | 560,964 | — | struct_linear, struct_func_start |
| Many-Argument Workhorses | 557,135 | — | struct_branch, struct_linear, struct_args, struct_func_start |
| Annotated & Test Methods | 528,475 | — | struct_args, struct_func_start, struct_decorators |
| I/O & Config Routines | 506,419 | — | struct_func_start |
| Stateful Encapsulated Methods | 484,664 | — | struct_linear, struct_args, struct_func_start, def_encapsulation |
| Encapsulated Accessors | 477,992 | — | struct_linear, struct_args, struct_func_start, def_encapsulation |
| Generic / Templated Code | 432,216 | — | struct_args, struct_func_start, struct_generics |
| State Mutators | 373,864 | struct_class_start | struct_args, struct_func_start |
| Callbacks & Closures | 351,722 | — | struct_linear, struct_args, struct_func_start, struct_closures |
| C Struct Operations | 302,737 | — | struct_linear, struct_args, struct_func_start, struct_class_start, state_pointers, def_encapsulation |
| Type Conversions | 224,585 | — | struct_linear, struct_args, struct_func_start, state_cast_hits |

## Does the confirmed pair grammar hold within each archetype? (sign agreement with crucible consensus)

| archetype | pairs testable | agreement |
|---|---:|---:|
| Parameter Forwarders | 9 | 89% |
| Compute Cores | 20 | 90% |
| Defensive Guards | 24 | 75% |
| Interface Declarations | 9 | 78% |
| Many-Argument Workhorses | 32 | 84% |
| Annotated & Test Methods | 29 | 76% |
| I/O & Config Routines | 32 | 78% |
| Stateful Encapsulated Methods | 31 | 84% |
| Encapsulated Accessors | 23 | 87% |
| Generic / Templated Code | 29 | 86% |
| State Mutators | 5 | 60% |
| Callbacks & Closures | 29 | 86% |
| C Struct Operations | 9 | 56% |
| Type Conversions | 24 | 79% |

## Fingerprint distribution: exact signal-presence signatures (which of the signals are present)

- distinct signatures: **314,979** across 6,936,799 functions; singletons 181,043 (57% of signatures, 2.6% of functions)
- the top 10 signatures cover 14% of functions; **205** signatures cover 50%, **19,238** cover 90%
- rank–frequency slope (ranks 10 to 100k, log–log): **-1.28** (Zipf ≈ −1)
- signature entropy 11.6 bits
- per-line density profile (20 common signals, 2,100,000-function archetype-balanced sample): first 3 components explain 30%; 90% needs 16 components; participation ratio (effective dimensions) **15.7**
