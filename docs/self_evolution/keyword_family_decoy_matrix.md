# Keyword-family decoy matrix (2026-11-21, exploratory first version)

A parserless precision test. For each keyword-rosetta language (47 with a manifest, menu and a real line-comment `decoy:` line; 45 scored) and each
token family in that language's generated menu (`docs/menus/<language>.json`), three variants of the language's own folder, each with ONE inserted line in
the language's own syntax, one scan of all 1,581 folders, counts compared with an unmodified baseline folder:

| variant | line | expected |
|---|---|---|
| code | the menu keyword as a bare line | the family count rises (the positive control; without it a pass says nothing) |
| comment | the same keyword after the language's comment marker (cloned from its own `decoy:` line, closer kept for block markers) | no change: comments are stripped |
| string | the same keyword as the content of the language's own string decoy literal (cloned from rosetta's string decoy) | policy: #2535 (closed, not-a-bug) says strings are not shielded, so it counts; the contracts say "at its invocation" / "in operator position" |

## Results
- **Comment layer: 756 of 756 controlled cells pass; no leaks** (45 languages; 11 further cells had no positive control and are not counted). Comment stripping is sound
  for every token family tested. (A first run showed 134 "leaks"; all were my insertion bug: the picker took the "Graph Decoy" block-comment prose as a marker. Fixed.)
- **String layer: a keyword inside a string literal counts in 665 of 715 controlled cells (93%).** 100% for concurrency, dependency_injection, immutability_locks, memory_alloc,
  scientific, ssr_boundaries, sync_locks, test, test_skip, ui_framework, listeners, pointers, explicit_casts, lazy_evaluation; 90-97% for panics_and_aborts, io,
  regex_execution, time_date_logic, serialization_parsing, thread_sleeps, telemetry, high_risk_execution, safety, debug_prints. `branch` counts in 48% (its rule needs
  more context than a bare keyword). This is the documented #2535 behaviour, measured: it is systemic, not a few families.

## What it means
- The comment surface is solid; the string surface is where precision goes. Part of the low precision in the oracle grid (io, regex, time, bitwise, ...) is this, by design.
- Whether to shield string literals for family rules is a decision for the maintainer (#2535's position versus the contracts), not a bug. The grid can show it as a layer.
- Not covered yet: identifier look-alikes (`print_total`, `sleeping`), operator look-alikes (generics `>>`, `|x|`, `&mut`), block comments in languages with only a block form,
  the 5 languages without a usable `decoy:` line, and families without menu keywords (structural families). Scripts: `tools/selfhistory/ast/decoys/`.
