# ENV-H1..H3 — does platform-conditional density find extrinsic fixes on unseen repos? — registered 2026-11-06, before either repo is cloned

**Origin.** XC's exploratory follow-up (`docs/xc_hypotheses.md`, `tools/exploratory/xc_envcond.py`).
- **The measure:** `#if/#ifdef/#ifndef/#elif` lines testing platform, compiler or arch macros, per line ("P per line").
- **On curl, nDPI and openssl it** found extrinsic fixes better than both size orders (+0.119 / +0.048 / +0.133) and
  was worse than size on every other class.
- **That was exploratory.** The labels were seen and the measure was chosen after looking at the top files. This entry
  tests it on repos nobody has looked at.

**Repos (unseen).**
- `harfbuzz/harfbuzz` (C++, default branch `main`).
- `libarchive/libarchive` (C, `master`).
- Neither has been cloned, scanned or harvested in this program. They are picked for what they are: heavily portable
  code with platform backends, and therefore a fair test. They were not picked for any result.

## Data (git only, no engine scan)

- **Snapshots.** For each calendar quarter, the last first-parent commit on the default branch before the quarter
  boundary.
  - Start: the first quarter with ≥ 50 candidate files.
  - End: the last quarter whose boundary + 180 d precedes the clone's head commit time.
- **Candidates.**
  - harfbuzz: files ending `.c .h .cc .hh .cpp .hpp`.
  - libarchive: `.c .h`.
  - The same extensions define a "C file" in the harvester.
- **Size.** Line count of the file at the snapshot (`git grep -c ''`).
- **Predictor.** "P per line" = platform-conditional line count / max(lines, 1). The regex is `PATTERNS["P"]` of
  `tools/exploratory/xc_envcond.py` at commit `8a793c9`, verbatim.
- **Labels.** `tools/xc_harvest.py` rules v2 (amendment 1), unchanged except:
  - (a) the candidate extensions above;
  - (b) no security-fix events file exists for these repos, so **the latent class is not formed**. Latent commits fall
    into regression / other-fix by the same rules. This is a known contamination of those comparison classes.
- **Outcome.** A candidate file at t is positive for class K if touched by a class-K commit in (t, t + 180 d].

## Gates (binding, before scoring)

- **Precision audit:** 30 seeded (2982) extrinsic and 30 regression commits per repo, by XC's audit rules. Gate
  ≥ 0.70, or the class is withheld (no amendment allowed this time).
- **Power:** ≥ 20 snapshots with ≥ 1 positive of the class.

## Claims (per repo)

Lift(K) = recall@20(P per line, K) − max(recall@20(lines desc, K), recall@20(lines asc, K)). Recall@20 follows EA's
rule (ties by fewer lines, then path).

| id | claim | supported iff |
|---|---|---|
| **ENV-H1** | P per line finds extrinsic fixes beyond size | mean lift(extrinsic) > 0, one-sided snapshot-bootstrap lo > 0 |
| **ENV-H2** | …more than regressions | mean over snapshots scored for both of [lift(extrinsic) − lift(regression)] > 0, lo > 0 |
| **ENV-H3** | …more than other fixes | same vs other-fix |

- 5,000 rounds, seed 2982, α = 0.01 / 3 one-sided.
- Equivalence null: 90% CI inside [−0.02, +0.02].

**Headline.**
- **Replicated** iff ENV-H1, H2 and H3 are all SUPPORTED on both repos.
- **Partly replicated** if ENV-H1 is supported on both.
- **Not replicated** otherwise.

**Decision.** If replicated, open a gitgalaxy issue for a per-file platform-conditional density column (and a
"environment-coupling surface" view). Language scope C/C++ first.

**Priors.**
- ENV-H1 **leaning supported** (3/3 exploratory).
- ENV-H2 / H3 **leaning supported**.
- Main risk: libarchive isolates platforms in per-OS files (`archive_*_windows.c`). There the coupling surface may
  be expressed by file name, not conditionals.

---

## Results — 2026-11-06 (labels and walks `ENV labels` commit; scorer `708b36c` committed before labels)

- **Label audit** (`env_label_audit.md`):
  - harfbuzz: extrinsic 0.93, regression 0.77;
  - libarchive: extrinsic 0.83, **regression 0.43 → withheld**. Most of its regression-word hits add *regression test*
    fixtures and fix nothing.

| claim | harfbuzz (62 snapshots) | libarchive (72) |
|---|---|---|
| **ENV-H1** P per line beats both size orders on extrinsic fixes | **+0.173**, lo +0.028, 90% CI [+0.085, +0.261] → **SUPPORTED** | **+0.123**, lo +0.031, [+0.067, +0.181] → **SUPPORTED** |
| **ENV-H2** …by more than on regressions | **+0.269**, lo +0.092 → **SUPPORTED** | **withheld** (label gate). Computed +0.296, lo +0.045: non-binding |
| **ENV-H3** …by more than on other fixes | **+0.193**, lo +0.045 → **SUPPORTED** | **+0.157**, lo +0.061 → **SUPPORTED** |

- **Mean lift by class.**
  - harfbuzz: extrinsic +0.173, regression −0.093, other-fix −0.018.
  - libarchive: extrinsic +0.123, regression −0.098, other-fix −0.031.
- **Headline (registered rule) → PARTLY REPLICATED.** ENV-H1 and H3 hold on both unseen repos; H2 holds on harfbuzz and
  is withheld on libarchive by the label gate, not by the measure.
- **Across five repos** (three exploratory, two registered), platform/compiler/arch conditional density finds extrinsic
  fixes beyond size, and does worse than size on every other class. It is the first static GitGalaxy-style measure in
  this program to replicate beyond size on unseen data.
- **The decision rule** ("open a gitgalaxy issue if replicated") is not strictly met. Whether H1 + H3 on both repos is
  enough to open the engine-column issue is an owner call.
