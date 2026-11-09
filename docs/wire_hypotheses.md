# WIRE — does a COBOL program's call network survive into its deterministic Java port, and can the network find the port's source when whole-program fingerprints cannot? — registered 2026-11-08, before any scorer, scan of a port, or wiring statistic

**Why.**
- DOOM study (gitgalaxy `doom-study`, exploratory, 2026-11-08): wiring between linuxdoom's 16 game areas, read against
  a shuffled-placement null, separates ports and translations from redesigns (forks +0.33, redesigns +0.00, Quake /
  Lua +0.00) and separates translations that kept the design (Go +0.55) from ones that rewired (C# −0.17). That
  corpus suggested the idea; this one has not been looked at for it.
- gitgalaxy#7532: whole-program `sfs` fingerprints pick a det-port's own COBOL source 1–3 times in 124 (chance 0.8%),
  because det Java is mechanical (runtime calls, dispatch methods) and every port has the same style. #7532 proposes
  measuring fidelity along the translator's own map instead. This study tests the call-network part of that.
- **Scope.** LAY's owner note (2026-11-06) put cross-language port traceability out of LAY. The owner asked for this
  test directly (2026-11-08). It uses the translator's own map, as that note said it should.

## Data (fixed before any measurement)

- **Ports.** gitgalaxy `origin/main` **8f96d76ba**, `tests/tools/det_port.py run --all-cases --translate-only`, in both
  styles: `--style dispatch` (default) and `--style structured` (B1). Work dirs `wire-study/ports-{dispatch,structured}`
  (outside every repo; third-party source is never committed). `--typed` is on by default for both (det_port.py).
- **COBOL sources.** Each case's own COBOL program(s), as the case names them.
- **Instrument.** GitGalaxy at the same commit, scanning the COBOL program and the port's Java separately.
  - COBOL: each paragraph (and the main line, named after PROGRAM-ID, #7170) is a `function_data` unit. Edges: p → q
    when q is in p's `calls_out_to` or `transfers_to` (PERFORM, PERFORM THRU, GO TO as the engine records them).
  - Java: each method is a unit; edges m → n when n is in m's `calls_out_to`.
- **The map (truth).** The translator writes each paragraph method under a `/** <PARAGRAPH>. */` header; the main
  line is the method `main()` (structured) or the `MAINLINE`-headed method (dispatch). A Java method so headed maps
  to the COBOL unit of that name; all other Java methods (runAll, perform, run, helpers, runtime) are unmapped and
  their edges are dropped. Names are used **only** to read the translator's map, never to score.
- **Program (unit of analysis).** One COBOL program with its port, de-duplicated by source file content (a program in
  several cases counts once, its first case by name). **Evaluable** iff ≥ 3 mapped units and ≥ 2 COBOL edges among them.
- Instrument check done before registration (no Java scanned, no comparison): CBACT02C's COBOL scan lists its 6 units
  with their PERFORM targets in `calls_out_to`.

## Measures

- **Mapped wiring J.** Jaccard of the two directed edge sets on the mapped units (Java edges carried back through
  the map; self-loops dropped).
- **Null.** The same program with the map permuted among its mapped units (1,000 draws, seed 2982): same two graphs,
  correspondence at random. **Gap** = J − mean(null J); a program **beats its null** iff J > the null's 95th percentile.
- **Name-free identification (H3).** For each structured port: the unlabeled directed graph of its mapped methods
  (headers tell which methods are paragraphs; their names are discarded). For every evaluable COBOL program: its
  unlabeled unit graph. Similarity = cosine of Weisfeiler–Lehman subtree histograms (3 iterations, initial label =
  (in-degree, out-degree)). Rank all evaluable COBOL programs; hit = the port's own source ranks first, ties
  pessimistic (the source is placed last among equal scores). Chance = 1 / number of candidates.

## Claims (α = 0.01/3 one-sided each; bootstrap over programs, 5,000 rounds, seed 2982)

| id | claim | supported iff |
|---|---|---|
| **WIRE-H1** | **structured** ports keep the COBOL call network, as GitGalaxy reads both languages | mean gap > 0 with bootstrap lo > 0, **and** ≥ 50% of evaluable programs beat their null |
| **WIRE-H2** | **dispatch** ports keep it too | same test on the dispatch ports |
| **WIRE-H3** | the call network alone (no names, no map at scoring time) finds a structured port's own COBOL source | top-1 rate > chance (label-permutation p, 10,000 draws) **and** top-1 rate > 3/124 (sfs's best in #7532) |

- **Not evaluable:** < 30 evaluable programs for a claim.
- **Priors (stated so they can be wrong).** H1: expected to pass strongly; the structured translator calls paragraph
  methods directly, so H1 is chiefly a test that GitGalaxy *sees* preserved wiring on both sides. H2: expected to
  **fail**; dispatch routes PERFORM through `perform(int, int)` and a `switch`, so the engine sees calls to the
  dispatcher, not between paragraphs. A failure there is an instrument limit to report, not a translator defect. H3:
  uncertain; many small programs have the same unlabeled shape (a main line calling a few leaves), so ties may sink it.
- **Descriptive (no verdicts):** per estate; programs dropped and why; J on the model-refined B2 ports committed in
  gitgalaxy `docs/benchmarks/det-refine-*` (3 programs); H3's top-5 rate; dispatch J with `perform(a, b)` literals
  resolved to paragraphs a..b by the scorer (a parser, not the engine: labelled as such).

## Guards

- Registration before scorer and run; verdicts published either way.
- The null holds both graphs fixed and breaks only the correspondence (the DOOM lesson: raw wiring flatters everything).
- Size: H3's chance is computed over the actual candidate set; ties are pessimistic.
- Temporal ablation, rename tracking, length-matched pairs: not applicable (no history, single snapshot, graph grain).
