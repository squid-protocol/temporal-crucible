---
date: 2026-11-06
title: Do extrinsic fixes surge after compiler releases? (BURST)
type: confirmatory
status: scored
verdict: not-supported
theme: coupling
ids: BURST-H1..H3
docs: docs/burst_hypotheses.md; docs/burst.md
links: temporal-crucible#60
takehome: Extrinsic (platform, compiler, dependency) work is bursty, but the bursts are not timed to GCC or Clang major releases (share change +0.002 and +0.009, with a placebo just as large); only where extrinsic work lands is predictable, not when.
---

# Do extrinsic fixes surge after compiler releases? (BURST)

## Question

Does the extrinsic share of fixes rise in the 90 days after a GCC (H1) or Clang (H2) major release? Do compiler-named extrinsic fixes respond to their own compiler (H3)?

## Why we asked

XC's exploratory follow-up found extrinsic fixes bursty on every repo (dispersion 1.4–4.9), and the burst months read like outside events. That reading came after looking at the bursts, so it needed an independent calendar of shocks. Priors: H1 leaning supported, H2 uncertain, H3 leaning supported.

## What we did

- Shocks were frozen from upstream git tags before any join: 27 GCC majors (2001–2026) and 34 Clang/LLVM series from 2.6.
- Fixes: XC labels on curl, nDPI, openssl, harfbuzz and libarchive.
- Units: (repo, shock) pairs with 90-day before and after windows.
- Cluster bootstrap over shocks, α = 0.01 / 3.
- Descriptive placebo: every shock shifted by +182 days.
- A known bias towards zero was stated in advance: Clang's spring releases fall inside GCC's "before" windows.

## What we found

- **BURST-H1:** +0.0020 (CI [−0.0226, +0.0264]). Not supported (inconclusive).
- **BURST-H2:** +0.0086 (CI [−0.0069, +0.0244]). Not supported (inconclusive).
- **BURST-H3:** +0.087 (CI [−0.112, +0.311]). Not supported (inconclusive).
- The placebo dates give effects as large as the real ones (+0.0073 and +0.0154). The 30-day and 180-day windows do not change the picture.
- None is an equivalence null, so this means no detectable effect at this resolution, not a proven zero.

## Take-home

Compiler releases reach projects diffusely, through distros and Xcode months later. The burst months look project-driven instead: porting campaigns, newly enabled warnings or CI bots, and new contributors bringing a platform.

## What it changed

The registered decision rule's second branch applies: only the *where* of the extrinsic surface is predictable (platform-conditional density and own extrinsic history). The owner's interpretation (the environment is chosen, as in niche construction) is written up as a reading, not a result. It proposes NICHE-H1..H3: bursts follow the project's own dated niche-entry events (CI jobs, build-system platform branches), and niche breadth predicts extrinsic share. These are to be registered before any join.
