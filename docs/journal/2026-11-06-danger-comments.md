---
date: 2026-11-06
title: Do comments that warn of danger mark risky code? (CMT-G, DC-2, CFIX, DC-R)
type: confirmatory
status: scored
verdict: mixed
theme: comments
ids: CMT-G, DC-H1..H2; DC-2; CF-H1..H2, DCR-H1
docs: docs/dc_hypotheses.md; docs/cmt_gate.md; docs/dc.md; docs/cfix.md; docs/dcr.md
links: temporal-crucible#84
takehome: Functions born with danger-language comments get CVE fixes 1.45× as often [1.08, 1.89]; the replication on unseen repos was inconclusive (1.13), and CVE fixes themselves add such comments (1.61×).
---

# Do comments that warn of danger mark risky code? (CMT-G, DC-2, CFIX, DC-R)

## Question

Do developers' own warnings ("unsafe", "careful", "overflow") in comments mark code that later needs security fixes?

## Why we asked

Comments are a channel the structural signals ignore.

## What we did

A gate first checked the engine's comment stream against tree-sitter (CMT-G). It failed as registered because of COBOL: tree-sitter-cobol labels code as comments, so no engine issue was filed. The study was re-registered as DC-2 with a gate scoped to C/C++ (98–100%). CFIX looked at fix commits; DC-R replicated on unseen repos.

## What we found

- DC-2 ✓ H1: 1.45× [1.08, 1.89], in all 4 repos (1.29–1.81). H2 (CVE-specific) ✗.
- CFIX ✓: CVE fixes add danger comments 1.61×, which does not help detection.
- DC-R inconclusive: 1.13 [0.48, 3.08], 75 events, mostly libxml2 (0.88); it does not contradict DC-2 (pooled 1.42).

## Take-home

Developers' warnings carry some signal: the one birth-time code property with a supported association, not yet replicated.

## What it changed

A larger replication with more CVE labels is owed.
