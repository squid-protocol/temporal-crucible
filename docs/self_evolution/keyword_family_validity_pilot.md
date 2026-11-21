# Do GitGalaxy's keyword families measure what their names say? Python pilot (2026-11-21, exploratory, discovery not confirmation)

> **Update 2026-11-21 (later): superseded in part.** The oracles were aligned to the families' written contracts (`gitgalaxy/standards/signal_contracts.py`,
> 71 families) after this note was written. What changed: closures are anonymous callables only (a nested `def` is not one); `bitwise_ops` includes `&` and `|`
> (and type annotations such as `str | None` are not counted); `time_date_logic` includes durations; `doc` is structured documentation (`/** */`, `///`, godoc);
> debug prints leave out writers and log calls; `serialization_parsing` covers JSON, YAML, XML, CSV and protobuf, so the "by design" reading of its
> pickle-only rule below is wrong (the contract says JSON counts: gitgalaxy#8882). Two rows were oracle errors and are withdrawn (Go print, C documented).
> Re-run numbers: `rewrites/cross_language_contract_aligned/`. The grid that now carries these results: gitgalaxy PR #8876; corrections to the public issues:
> #8861, #8862 (comment), #8866, #8868.


Test: for the 72,044 Python functions in the engine's own code (the isolated-file scans of the rewritten files, `ast/gscan/trees/new`), count what Python's `ast`
says each function really does (calls, comprehensions, closures, decorators, raises, ...), then compare each `function_data` family column on the same function:
recall (oracle > 0 and family > 0), precision (family > 0 and oracle > 0) and rank correlation. Matching is by file and start line (100% matched).
Script: `tools/selfhistory/ast/family_oracle.py`; numbers: `rewrites/family_oracle_results.json`. Oracle limits: it is a naive reading of the family NAME. Where a
family is deliberately narrow (e.g. serialization = unsafe deserialization) a low recall is a definition, not a bug; the table separates those. The oracle's first
version counted `ast.walk` as file I/O (corrected before these numbers).

Of 110 function columns, 54 ever fire on this code (many of the rest are other-language or security families expected to be zero here).

## Aligned (the family measures what it says)
branch/complexity (recall 0.99, precision 0.98, rho 0.98), print (1.00/0.97), raise = bailout (1.00/0.97), type casts (1.00/0.97), imports (1.00/1.00),
comprehensions (0.83/0.91), documented (0.89/0.99).

## Measurement gaps (the keyword list covers fewer constructs than the family name)
| family | recall | precision | what is missed or over-counted | candidate keywords (functions missed) |
|---|---|---|---|---|
| arch_regex (regex_execution) | 0.53 | 1.00 | list is the six `re.` module calls; methods on compiled patterns are invisible | finditer (5,153), fullmatch (3,390), match (3,186), search (2,777), findall (1,873) |
| arch_time (time_date_logic) | 0.54 | 1.00 | list is datetime.datetime/timedelta/sleep/time.time/calendar | perf_counter (1,183), now, strftime; monotonic, process_time |
| arch_io | 0.25 | 0.43 | `pathlib` counts only if the word appears; `os.` also fires on pure path-string work | read_text (1,746), rglob (713), glob (691), write_text, read |
| bitwise_ops | 0.15 | 0.32 | Python rule is text `<< >> ^ ~`: matches inside strings and regex patterns (this engine is full of both) and ignores `&`/`\|` by design | n/a: fix is operator position (ast), not more keywords. Not yet verified by sampling |
| struct_closures | 0.45 | 0.98 | undercounts nested functions or lambdas | check lambda |
| def_cleanup | 0.14 | 0.57 | `with` / finally forms only partly covered | to inspect |
| lazy_evaluation | 0.04 | 0.96 | counts `yield` and Generator names, not generator expressions (15,208 functions): a definition call for the owner |

## Dead on Python
struct_decorators fires in 0 functions although 4,156 have decorators (the `decorated_by` column holds them: the family regex exists, the function column is never
fed: a data-flow gap, not a keyword gap). json (978 dumps, 416 loads) sits in no family: the Python `serialization_parsing` rule matches only pickle/marshal/literal_eval, although the contract names JSON, YAML, XML, CSV and protobuf (gitgalaxy#8882).

## Corrections after reading the rules (2026-11-21)
The first version of this note listed `state_halt_hits` and `threat_eval_exec` as dead. That was a wrong mapping on my side: `state_halt_hits` is "Sleeps & Timed
Waits" (`thread_sleeps`, `time.sleep`), and eval / subprocess / sys.exit live in `high_risk_execution` -> `state_danger`. The controlled files below show both fire
correctly. Neither is a gap.

## Controlled reproductions (one function per case, `tools/selfhistory/ast/family_repro/`, pinned scanner)
| case | expected | got |
|---|---|---|
| decorated method (`@staticmethod`, `@property`) | struct_decorators > 0 | 0 (decorated_by is filled) |
| `time.perf_counter()` | arch_time > 0 | 0 |
| `Path(p).read_text()` | arch_io > 0 | 0 |
| `os.path.join(a, b)` | arch_io == 0 (path string work) | 1 |
| `sys.exit(2)` | arch_io == 0 | 1 (also state_bailout_hits 1, correct) |
| module-level `PAT = re.compile(..)`, then `PAT.finditer(s)` / `PAT.fullmatch(s)` | arch_regex > 0 | 0 |
| `re.compile(r"^a|~b<<")` (characters inside a string) | bitwise_ops == 0 | 3 |
| `time.sleep(1)` | state_halt_hits 1 | 1 (correct) |
| `subprocess.run`, `eval` | state_danger 1 | 1 (correct) |
| `json.loads` | no family by design | 0 |
| generator expression only | lazy_evaluation: definition call | 0 |

## Caveats
One language, one repo (the engine's own code, regex-heavy and tool-like), a naive oracle, and no independent second oracle yet. Not yet run on other languages
(tree-sitter would supply the oracle) or the keyword-rosetta corpus. Adding keywords adds regex cost, which the speed work showed is where time goes.
