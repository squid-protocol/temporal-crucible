---
date: 2026-11-08
title: Do the call-network findings replicate on unseen repos and other languages?
type: confirmatory
status: scored
verdict: mixed
theme: natural-history
ids: CGR-*
docs: docs/cgr_hypotheses.md; docs/cgr.md
links: temporal-crucible#92; temporal-crucible#94; temporal-crucible#96
takehome: Across eight new repos in five languages, hubs persist and attract new calls, and rewiring, coupling and cycles each mark files needing later fixes (jointly, beyond size, churn and prior fixes); but the jumps picture, centralisation and several C findings do not carry, concurrency code is central outside C, and pointer-rich hubs are a C property.
---

<!--
Header fields (one per line, `key: value`; lists use `;`):
  date      the day the entry was opened (registration day for confirmatory work)
  type      confirmatory | exploratory | engine-finding | program
  status    draft | registered | scored | superseded
  verdict   supported | replicated | mixed | not-supported | inconclusive | pending | n/a   (a draft is always pending)
  theme     provenance | coupling | natural-history | defect-prediction | keyword-grammar | fingerprints | comments | engine | program
  ids       register ids exactly as in docs/HYPOTHESES.md's first column, e.g. KWP-H1..H3
  docs      repo paths of the registration and result docs, e.g. docs/kwp_hypotheses.md; docs/kwp.md
  links     issues / PRs, e.g. gitgalaxy#8024; temporal-crucible#85
Then: python tools/journal.py build   (CI runs `check`)
-->

## Question

Do the CGT, CGN and CGK call-network findings hold on repositories never used for them, and in languages other than
C? Which of the three bug-related network signals (rewiring, coupling, cycles) carries the effect when they compete?

## Why we asked

All three studies ran on five heavily studied C libraries. Their leads need unseen data, and the owner asked whether
findings like pointer-rich hubs are language artefacts.

## What we did

Registered in `docs/cgr_hypotheses.md` before any scan: eight new repos (four C; Go, Java, Python, Rust), one engine,
the original scorers unchanged with the repo list and pass rules swapped, each claim in its observed direction, plus
language and joint-model claims.

## What we found

- **Replicated** (8 repos, C, Go, Java, Python, Rust, one engine, 626 snapshots, 0 scan failures): call networks are
  static most quarters; hubs persist (8/8), are made early and attract new calls (8/8); hubs are public,
  decision-dense and rich-shaped; rewiring (OR 2.86), cycles (1.67) and coupling (1.89) go with later fixes;
  extrinsic fixes land in peripheral hub-hosting files.
- **Jointly (M1):** rewired 1.42, coupled 1.60, in a cycle 1.38, beyond size, churn and prior fixes.
- **Not replicated:** change in jumps (5/8), centralisation (5/8), duplicated wiring as a safe sign, orphans dying
  sooner, CVE fixes rewiring more (libxml2 only, opposite).
- **Reversed:** concurrency code is more central, not peripheral, once Go, Java and Python concurrency is included.
- **Language:** pointer-rich hubs are C-specific (L2 ✓); only public surface is a language-neutral hub trait (L1 ✗);
  59% of keyword-screen signs carry to non-C code (L3 ✗, bar 60%).

## Take-home

The hub laws and the network-defect links replicate across languages; several finer C results do not, and keyword
profiles of network roles are language-specific.

## What it changed

- Concurrency-at-the-periphery and duplicated-wiring-is-safe are withdrawn as C artefacts.
- Keyword x network results are reported per language from now on.
- LAWS (registered, amended) adds the missing controls (authors, change coupling, clustering) and the null models.
