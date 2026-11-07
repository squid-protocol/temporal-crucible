---
date: 2026-11-06
title: Does input-facing code mark where CVEs land? (INP)
type: confirmatory
status: scored
verdict: not-supported
theme: defect-prediction
ids: INP-H1..H6
docs: docs/inp_hypotheses.md; docs/inp.md
links: temporal-crucible#67
takehome: Files that call input APIs or handle raw byte buffers with a length lose to size at finding CVE fixes on curl, openssl and harfbuzz (pooled −0.092 and −0.054); only nDPI, with its fuzzer-found parser CVEs, is positive.
---

# Does input-facing code mark where CVEs land? (INP)

## Question

Latent defects should be found where untrusted bytes are handled. Do files that pull data in from outside, or handle raw bytes with a length, carry CVE fixes beyond size? Are those files CVE-specific, and do they show CVEs where a file has no CVE history?

## Why we asked

ENV and LIB showed that an explicit, declared dependency on the outside world marks where outside-driven work lands. Input is the outside world for latent defects. Prior on record: uncertain, leaning not shown. BUF was rated more likely than IN, and H5/H6 the most informative.

## What we did

- Two per-line measures. **IN** counts input-call lines (`recv`, `read`, `SSL_read`, `pcap_next`, ...). **BUF** counts byte-pointer + length parameter pairs or length-driven copies.
- Claims: each measure beats size for CVE fixes (H1/H2), is specific to CVEs against extrinsic and other fixes (H3/H4), and finds CVEs in files with no prior CVE fix (H5/H6).
- Pooled over curl, nDPI, openssl and harfbuzz with equal weight. Recall@20 lift over the stronger size order, α = 0.01 / 6.

## What we found

- All four repos were evaluable. **Every claim is not supported.**
- IN beats size: −0.092 pooled. BUF beats size: −0.054. Both are worse than size on curl, openssl and harfbuzz, and positive on nDPI (+0.096 / +0.163).
- BUF leans CVE-specific (H4 +0.032, CI [−0.018, +0.080]), but not significantly. Neither measure finds CVEs where history is blind (H5 −0.104, H6 −0.044).

## Take-home

"Handles outside bytes" is not concentrated in a few files the way platform or library coupling is. Input flows through most of the codebase. The input surface shows up only where fuzzers do the finding.

## What it changed

The declared-dependency pattern is now known to work for libraries and platforms, not for input. A call-graph reachability version of INP is the remaining untested form. The snapshot property that does track security fixes beyond size is per-file dynamism (DYN-H2).
