# Signal-name audit: what each function signal actually counts (2026-11-07)

**Method.**
- Each `function_data` signal column is traced to its engine rule (`gitgalaxy/recorders/record_keeper.py`; engine
  `b64f42bf`).
- **Prevalence** = the share of the population's 8.17M functions with count > 0
  (`master_db_v2.12.0-b64f42bf.db`).
- **Real matches** = the strings each language's rule most often matches on the engine's **comment-free code
  stream** (Prism `split_streams`) of language-crucible files.
- Script: `tools/exploratory/signal_audit.py`.
- The engine's per-rule definitions live in `docs/<rule>_rule_contract.md`.

## Names that mislead (the signal is fine; the column name says something else)

| column | engine rule | prevalence | what it really matches | clearer name |
|---|---|---:|---|---|
| `struct_linear` | structural_boundaries | 85% | `return`, `void`, `def`, `import`, `export`, `struct`, `=>` | **structural keywords** |
| `state_safety_neg` | safety_bypasses | 8.4% | C `sprintf`, `strcpy`, `(T *)` casts; C++ `void *`, `catch (...)`; TS `any`, `!` | **unsafe constructs** |
| `state_heat_triggers` | reflection_metaprogramming | 3.5% | C `goto`, `#define`; Python `getattr`, `@classmethod` | **metaprogramming / dynamic** |
| `struct_args` | args | 89% | call and definition sites with arguments (`pyerr_format(…)`, `bind_method(…)`) | **calls / signatures with arguments** |
| `state_flux` | state_mutation | 39% | `i++`, `x =`, `.push(`, `.append(` | **state mutation** |
| `state_bailout_hits` | panics_and_aborts | 5.7% | `raise`, `throw`, `abort`, `exit`; C `return -1` | **error exits** |
| `state_halt_hits` | thread_sleeps | 0.3% | `sleep`, `usleep`, `setTimeout`, `time.sleep` | **sleeps / waits** |
| `def_freeze_hits` | immutability_locks | 12% | `const`, `readonly`, `final`, `frozenset` | **immutability** |
| `def_safety` | safety | 15% | `assert`, `try`/`catch`, `isinstance`, `?.`, `noexcept`; **also C `size_t`, `nullptr`** | **defensive checks** (noisy in C) |
| `arch_api` | api | 37% | public / exported surface (`export`, `public`, non-`_` Python `def`); in C `typedef`, `extern` | **public surface** |
| `def_encapsulation` | encapsulation | 20% | `private`, `protected`, C `static`, Python `_name` | **private scope** |

## Rules with false positives worth an engine look

- **`arch_scientific`:** in C it matches a bare `i` and `log` (any variable or function so named).
- **`arch_ui_framework`:** in TypeScript it matches generic type arguments (`<e1`, `<namedtypenode`) as if they were
  JSX.
- **`def_safety` / `state_pointers` overlap in C:** `size_t` counts as both safety and pointers, so their
  co-occurrence is partly definitional.
- **`struct_comprehensions`:** true comprehensions in Python, but `.map(` / `.filter(` / `.forEach(` in TS and JS.
  That is defensible as "collection pipelines", but the name differs by language.
- **`def_doc`** on the code stream matches only string literals such as `'/**'`. Documentation lives in the comment
  stream, so at function level this column is effectively noise.

## Columns empty at function level (≈ 0% of 8.17M functions)

`llm_*` (4), `ml_traditional`, `dl_frameworks`, `lit_*` (4), `threat_*` (13), `sec_*` (3), `prompt_injection`,
`agentic_rce`, `struct_var_decl`, `state_slop_duplicates`, `state_unreferenced`, `def_ownership`,
`def_spec_exposure`, `state_graveyard`, `arch_hardware`, `arch_crypto`, `def_auth`, `arch_sys_config`.

- That is about **38 of 89 columns**. They are file-level or unpopulated per function.
- The keyword studies already excluded them (2–98% prevalence filter).
- They inflate the schema, and the zero `threat_*` result in OUT came from this.

## Effect on this program's findings

- **Statistics are unchanged:** columns were analysed as data. Plain-language readings change:
  - "linear code" → structural keywords;
  - "negative safety" → unsafe constructs;
  - "heat triggers" → metaprogramming.
- **The defensive-control core still reads as defensive.** `def_safety` (assert / try / isinstance),
  `state_bailout_hits` (raise / throw / abort) and `def_cleanup` (close / free / dispose) are what their names
  suggest, apart from `size_t` in C.
- **One pair is partly definitional in C:** `def_safety` × `state_pointers` (shared `size_t`). Treat C results
  involving it with care.

## Recommendation (owner decision; no engine change made)

1. **Display-name layer now,** as the 2026 Structural Surface Profile rename did (#2991): readable names in reports,
   charts and docs; stored columns unchanged; no retrain.
2. **Engine issues** for the noisy rules (`arch_scientific`, `arch_ui_framework`, `size_t` in `def_safety`) and the
   empty function-level columns.
3. **Column renames or removals only at the next archetype retrain:** they change the archetype models' feature
   dimension (the `feature_flags` precedent, #4114).
