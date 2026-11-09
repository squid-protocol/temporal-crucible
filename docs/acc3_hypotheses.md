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
