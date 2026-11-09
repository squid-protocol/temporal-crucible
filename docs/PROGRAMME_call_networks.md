# Call-network research programme (owner decision, 2026-11-08)

## Why this programme exists

On 2026-11-08 four registered studies looked at call networks:
- **WIRE:** COBOL → Java call networks along the translator's map;
- **CGT:** how call networks change over time;
- **CGN:** hubs, efficiency, bad shapes;
- **CGK:** what kind of code sits where.

A literature review the same day (`gitgalaxy/cgt-study/lit_review.md`, outside the repo) found most of their results
already known from 2004–2012 work: preferential attachment and hub persistence, Lehman-style decay, network metrics
and cycles predicting defects. What was new was mostly *how* we tested them (code-volume and size controls), plus a
few results:
- the fix-class ranking by rewiring;
- extrinsic fixes in peripheral hub-hosting files;
- call networks as a translation-fidelity measure.

So the programme stops rediscovering laws on five heavily studied C libraries and plays to what GitGalaxy has that
compiler-bound tooling does not:
- **many languages without compilation**, so decades-old snapshots scan as easily as today's;
- **history at scale**: a 10-second scan per snapshot, and a 6.9-million-function population database;
- **two measurement layers in one system**: keyword families (habit) and the call network (design);
- **corpora few others have**: mainframe estates, translations (COBOL → Java, the DOOM ports), polyglot repos.

## The five steps, in order

| step | what | why first / what it unlocks |
|---|---|---|
| **1. Accuracy (ACC)** | per-language precision and recall of GitGalaxy's call graph against compiler-grade oracles (libclang for C, a bytecode call graph for Java, `go/callgraph` for Go, PyCG for Python), and whether the network statistics the studies use survive the difference | every cross-language claim needs it: "your extractor differs by language" is the first objection |
| **2. Evolution panel (PANEL)** | a frozen, stratified multi-language sample (about 8–10 languages × 8–10 repos, quarterly history), one pinned engine, released as measurements only | ends the five-heavily-studied-repos problem: every later study draws from it. The CGR replication set is the first slice |
| **3. Many-labs replications (LAWS)** | the classic claims, each registered with null models (degree-preserving and size-matched growth), size-adjusted, per language and pooled: preferential attachment, hub persistence, Lehman decay, network metrics vs defects (forward-validated, after Zimmermann & Nagappan 2008 and Premraj & Herzig 2011), security-patch locality (Li & Paxson 2017), the size confound (El Emam et al. 2001) | headline output: a table of laws × languages: universal, language-specific, or artefact |
| **4. Joint-layer science (JOINT)** | keyword × network: CGK across languages; habit vs architecture over a codebase's life (gitgalaxy#7533 item 3); model handwriting in call networks (agent-habits) | questions only a system holding both layers can ask |
| **5. Translation fidelity (FID)** | WIRE follow-ups once gitgalaxy#8151 resolves the dispatcher; model-written ports; DOOM; mainframe estates | the applied track that matches the product |

## Rules for this programme

- **Prior work first.** Every registration has a *Prior work* section filled before any hypothesis is frozen: the
  closest published results, whether our claim replicates, extends or contradicts them, and the controls they used
  (`docs/_experiment_template.md`).
- **Data from the panel**, not from curl, OpenSSL, libarchive, harfbuzz and nDPI (they stay available as a
  development set).
- **Null models** with every network claim; **size-adjusted** estimates as headlines.
- **Bug-prediction claims only as forward-validated replications** of published ones. Programme standing: history
  predicts, structure describes.
- Measurements only; third-party code is never committed (`docs/journal` and register as usual).

## Status (2026-11-08)

- WIRE, CGT, CGN, CGK: scored and merged.
- CGR (replication on eight repos in five languages; registration #97): running, the pilot for steps 2–4.
- ACC: to be registered next. PANEL: registered after CGR reports.
