# Keyword-family validity across languages (2026-11-21, exploratory, discovery not confirmation)

Follows `keyword_family_validity_pilot.md` (Python). The family-validity tool (gitgalaxy PR #8864, `tests/tools/family_oracle.py` and
`family_oracle_ts.py`) scored six more languages against a tree-sitter reading of the same functions, one real repository each, scanned with the pinned
scanner: Go (prometheus), Rust (tokio), JavaScript (express), TypeScript (vue), Java (retrofit), C (redis). Raw tool output and JSON: `rewrites/cross_language/`.
Epic: gitgalaxy#8863, milestone Eagle Eye.

Recall / precision per family; `-` means the oracle never sees the construct in that repository.

| family | Go | Rust | JavaScript | TypeScript | Java | C |
|---|---|---|---|---|---|---|
| complexity | 1.00/1.00 | 1.00/0.70 | 0.96/0.96 | 0.98/0.93 | 0.62/0.99 | 1.00/1.00 |
| args (parameters) | 1.00/1.00 | 1.00/1.00 | 1.00/1.00 | 1.00/0.90 | 0.97/1.00 | 1.00/1.00 |
| struct_closures | 1.00/0.36 | 0.52/0.98 | 0.90/0.32 | 0.79/0.53 | 1.00/0.92 | n/a |
| struct_decorators | --/0.00 | 1.00/0.93 | - | --/0.00 | 0.99/0.99 | - |
| state_bailout_hits | 1.00/0.98 | 0.78/0.76 | 1.00/1.00 | 0.98/0.98 | 1.00/1.00 | 0.38/0.49 |
| bitwise_ops | 1.00/0.64 | 1.00/0.05 | 1.00/0.67 | 1.00/0.03 | 1.00/0.01 | 1.00/0.54 |
| state_print_hits | 0.34/1.00 | 1.00/0.98 | 1.00/1.00 | 1.00/0.86 | 1.00/0.65 | 1.00/0.99 |
| state_halt_hits | 0.89/0.99 | 0.36/0.84 | 0.00/-- | 0.98/0.94 | 1.00/0.71 | 1.00/1.00 |
| arch_regex | 0.89/0.56 | - | 1.00/0.25 | 0.63/0.87 | --/0.00 | 1.00/1.00 |
| arch_time | 0.83/0.48 | 0.11/0.78 | 1.00/1.00 | 1.00/0.02 | 0.00/0.00 | 0.52/0.64 |
| arch_io | 0.33/0.62 | 0.49/0.25 | 1.00/0.80 | 1.00/0.21 | 0.00/0.00 | 0.77/0.85 |
| is_documented | 0.76/0.88 | 0.92/0.89 | 0.20/0.02 | 0.46/0.26 | 0.98/0.72 | 0.01/0.93 |

Matched functions (left out: functions the parser cannot place): Go 7,935 (0), Rust 6,826 (671; functions inside macro bodies are not parsed as
functions), JavaScript 332 (3), TypeScript 2,142 (175), Java 2,616 (6), C 6,073 (3).

## What it shows
- **The oracles read functions correctly.** `args` equals the parser's parameter count at 1.00 / 1.00 in Rust, C and Go, 0.97 / 1.00 in Java. `complexity` agrees at
  0.96-1.00 in Go, C, JavaScript, TypeScript; Java misses `catch` (reproduced: a method whose only branch is a catch has complexity 0) and Rust counts more branches than the oracle.
- **`bitwise_ops` is systemically wrong, not a Python quirk.** Recall 1.00 and precision 0.01-0.67 in all six (0.03 in Python). Reproduced on tiny files:
  closing generics (`Map<String, List<String>>`) count as a right shift in Java, Rust and TypeScript, and text inside strings counts in C and Go
  (`"a >> b ^ c ~ d << e"` scores 4 and 3). This is gitgalaxy#8866 and generalises #8861.
- **Everything else depends on a definition.** `is_documented` ranges 0.01-0.98 because the oracle reads "a doc comment directly above" and the families
  read something else per language; `arch_time` and `arch_io` swing between precision 0.00 and 1.00. These are listed in gitgalaxy#8868 for the
  definition decisions in #8862, not called bugs.

## Oracle limits (read before using these numbers)
One repository per language; a naive oracle whose callee lists are in `family_oracle_ts.py` (they are the oracle's own reading of each family's name,
written independently of `standards/`); `&` and `|` are left out of the bitwise reading (they are also address-of, pipes, bounds and closures);
functions inside macro bodies and anonymous callbacks that a scan names differently are unmatched; no second oracle (a compiler or a different parser)
has been run. The Rust `complexity` over-count, Go and TypeScript `struct_closures`, and `struct_decorators` firing in Go and TypeScript where the
oracle sees none are measured differences whose cause has not been traced.
