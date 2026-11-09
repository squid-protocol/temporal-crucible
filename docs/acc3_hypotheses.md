# ACC-3 — Go: the resolved call graph vs `go/callgraph`, with a working output template — registered 2026-11-08, before any Go comparison

ACC and ACC-2 could not evaluate Go: ACC's flag clashed with prometheus's `go.work`; ACC-2's output template
printed token offsets (`{{.Caller.Pos}}`) instead of positions. A format check (no comparison) confirmed that
`{{posn .Caller}}` / `{{posn .Callee}}` print file:line:column. No Go agreement statistic has been computed.

**Design:** exactly ACC-2 (`docs/acc2_hypotheses.md`): prometheus @ c45b13bbdd96, the engine's resolved graph,
`callgraph -algo=static` as direct and `-algo=cha` minus static as dynamic, matching by (file, start line ± 3), and
the same bars. Only the template changes. **Claims:** ACC3-H1 (precision and recall ≥ 0.80) and ACC3-H3 (in-degree
ρ ≥ 0.80, hub Jaccard ≥ 0.50, coupling κ ≥ 0.60) for Go; **ACC3-G:** Go passes the LAWS gate iff ACC3-H3 holds.
One run; if the oracle fails again, Go is descriptive in LAWS.

## ACC-3b (2026-11-09 00:02, before any Go statistic)

The ACC-3 run was killed by the kernel's out-of-memory handler (the scorer held the full `-algo=cha` output, which
includes every dependency edge; 25 GB). No Go statistic was computed. ACC-3b changes only the plumbing: `callgraph`
output is streamed and lines whose caller and callee are both outside the repo are dropped as they arrive, under a
12 GB memory cap. Design, bars and gate are unchanged. If this run fails, Go is descriptive in LAWS; no further retry.

## Result (ACC-3b run, 2026-11-09 00:03)

| repo | precision | recall (direct) | in-degree ρ | hub Jaccard | coupling κ |
|---|---:|---:|---:|---:|---:|
| prometheus (Go) | 0.61 | 0.81 | 0.71 | 0.27 | 0.82 |

- 3,984 functions matched; agreeing edges are resolved mostly by file (3,002), import (1,282), unique name (857)
  and receiver (506).
- **ACC3-H1 ✗, ACC3-H3 ✗, gate ✗.**
- **Caveat:** `-algo=cha` added no edges beyond `-algo=static` after the in-repo filter. That is implausible for Go
  interfaces, so engine edges to interface implementations may be scored as false positives; precision is likely
  understated. The hub disagreement (Jaccard 0.27) fails the gate regardless.

**Gate after ACC, ACC-2 and ACC-3:** C passes; Java (1 of 2 repos), Go and Python do not. The engine's resolution of
same-arity Java overloads and Go receivers and interfaces is where the hub sets diverge.
