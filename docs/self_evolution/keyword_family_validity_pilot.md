# Do GitGalaxy's keyword families measure what their names say? Python pilot (2026-11-21, exploratory, discovery not confirmation)

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
struct_decorators fires in 0 functions although 4,156 have decorators (the `decorated_by` column holds them: the family regex exists, the function column is never fed:
a data-flow gap, not a keyword gap). state_halt_hits 0 (185 functions call sys.exit; no Python rule). arch_serialization 0 and threat_eval_exec 0 are by design
(unsafe-deserialization and eval/exec only); json (978 dumps, 416 loads) and subprocess (648 check_output, 373 call) sit in no family, which is a family-design question.

## Caveats
One language, one repo (the engine's own code, regex-heavy and tool-like), a naive oracle, and no independent second oracle yet. Not yet run on other languages
(tree-sitter would supply the oracle) or the keyword-rosetta corpus. Adding keywords adds regex cost, which the speed work showed is where time goes.
