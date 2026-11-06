# BURST-H1..H3 — do extrinsic fixes surge after compiler releases? — registered 2026-11-06, before any shock × fix join

**Why.** The XC follow-up found extrinsic fixes bursty on every repo (dispersion 1.4–4.9). The burst months *read*
like outside events: new platforms, new compilers, new warnings (`xc_hypotheses.md`, exploratory follow-up 2). That
reading came after looking at the burst months. This entry tests it against an **independent, dated calendar of
outside shocks**, frozen before the join.

**Shocks (`events/shocks_compilers.json`, fetched 2026-11-06 from upstream git tags).**
- **GCC majors:** 3.0.0 … 3.4.0, 4.0.0 … 4.9.0, then N.1.0 for N = 5 … 16. That is 27 releases, 2001-06-17 →
  2026-04-30.
- **Clang majors:** LLVM release series from **2.6 (2009-10-24)**, the first in which Clang was a usable C compiler,
  through 23.1.0 (2026-08-25). That is 34 releases. Series 2.0–2.5 are listed in the file but **excluded by this rule**.
- The date is the annotated-tag date or the tagged-commit date.
- No fix data was looked at while choosing the shock set or the rules.

**Fix data.** `events/{curl,ndpi,openssl,harfbuzz,libarchive}_xc.json` (rules v2; audits in `xc_label_audit.md`,
`env_label_audit.md`).
- A repo's fix commits are all its labelled commits (every class).
- "Extrinsic share" in a window = extrinsic commits / all labelled fix commits in that window.

**Units.**
- (repo, shock) pairs where the repo's harvest covers [s − 90 d, s + 90 d]: harvest `since` ≤ s − 90 d and harvest
  head ≥ s + 90 d.
- Both windows must hold ≥ 1 labelled fix commit.
- Windows: before = (s − 90 d, s], after = (s, s + 90 d], by committer time.

**Claims (pooled over the five repos).**

| id | claim | per-unit quantity | supported iff |
|---|---|---|---|
| **BURST-H1** | extrinsic share rises after a GCC release | share_after − share_before, GCC shocks | mean > 0, one-sided lo > 0 |
| **BURST-H2** | …after a Clang release | same, Clang shocks | mean > 0, lo > 0 |
| **BURST-H3** | the surge is compiler-specific | for a shock of compiler C: [Δ count of extrinsic commits whose subject names C] − [Δ count naming the other compiler]; all shocks | mean > 0, lo > 0 |

Δ = after − before. Naming regexes (case-insensitive, on the subject):
- GCC: `\bg(cc|nu c)\b|\bgcc-?\d`
- Clang: `\bclang\b|\bllvm\b|\bclang-?\d`

**Tests.**
- Cluster bootstrap over **shocks**: resampling a shock takes all of its repo units. 5,000 rounds, seed 2982.
- α = 0.01 / 3 one-sided.
- Equivalence null: 90% CI inside [−0.01, +0.01] for H1/H2 (share units) and [−0.2, +0.2] for H3 (count units).
- Fewer than 20 shocks with ≥ 1 unit makes a claim *not evaluable*.

**Descriptive (no verdicts).**
- Per-repo means.
- A placebo: every shock shifted +182 d, which should show no effect.
- Windows of 30 and 180 d.

**Known bias, stated now.** GCC releases (April/May) fall about 1–2 months after Clang's spring releases. A GCC
shock's "before" window can therefore hold a Clang "after" window. This biases H1/H2 **toward zero**.

**Priors.**
- H1 **leaning supported**: new GCC warnings reach distros within weeks.
- H2 **uncertain**: Clang adoption is spread out (Apple's Xcode clang lags upstream).
- H3 **leaning supported**.

**Decision rule.**
- If H1 or H2 holds, the environment-coupling surface gets a time axis. GitGalaxy's coupling map could then flag "a
  toolchain release just landed: expect extrinsic work on these files".
- If neither holds, the bursts are project-internal (tooling adoption, platform campaigns), and only the *where* is
  predictable.

---

## Results — 2026-11-06 (scorer `860ff91` committed before the join; report `burst.md`)

| claim | shocks | units | mean | lo | 90% CI | verdict |
|---|---:|---:|---:|---:|---|---|
| **BURST-H1** extrinsic share after − before, GCC | 27 | 99 | +0.0020 | −0.0405 | [−0.0226, +0.0264] | **not supported (inconclusive)** |
| **BURST-H2** same, Clang | 33 | 153 | +0.0086 | −0.0173 | [−0.0069, +0.0244] | **not supported (inconclusive)** |
| **BURST-H3** own-compiler-named − other-named Δcount | 60 | 252 | +0.087 | −0.227 | [−0.112, +0.311] | **not supported (inconclusive)** |

**Placebo.** Shocks shifted +182 d give GCC +0.0073 and Clang +0.0154: as large as the real dates. H3's placebo is
−0.061 against +0.087 real, a hint with a CI too wide to read. The 30 d and 180 d windows do not change the picture.

**Headline → the bursts are not timed to compiler releases.**
- Extrinsic work is bursty (dispersion 1.4–4.9), but a GCC or Clang major release does not measurably raise the
  extrinsic share of fixes in the following 90 days, on any of the five repos or pooled.
- The equivalence bounds were not met either, so this is "no detectable effect at this resolution", not a proven zero.

**What the bursts probably are (a reading, not a result).** The burst months in the exploratory note look
**project-driven**:
- a platform campaign (openssl RISC-V 2022-09, harfbuzz Windows CE 2014-08);
- a newly enabled warning set or CI bot (libarchive's FreeBSD-current `-W` series 2012-02; curl's clang-tidy 2026-02);
- a contributor arriving with a new platform (Cygwin and MinGW fixes, 2009).

Compiler releases reach these projects diffusely, through distro and Xcode adoption months later. So a release date is
a weak shock marker.

**Decision rule → (b).** Only the *where* of the extrinsic surface is predictable for now (platform-conditional
density; own extrinsic history). The *when* is not tied to toolchain releases.

**If anyone pursues the *when*, the candidate shocks are project-internal and dated in the repo itself:**
- the first CI job for a new platform or compiler (`.github/workflows`, `.travis.yml`, `appveyor.yml` history);
- warning-flag changes in the build files.

That needs a fresh registration.
