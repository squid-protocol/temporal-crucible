# SCAR — what the danger comments that fixes leave behind mean (SCORED)

Registration `docs/scar_hypotheses.md` (owner OK 2026-11-11). Aggregates only. File-cluster bootstrap 2000, seed 2982; α = 0.01/4.

## Part R — do scars mark lasting fragility?

- units (each function's first CVE fix; curl, openssl, harfbuzz, ndpi, libarchive): **1,098**, scarred **35** (3.2%); excluded: no function identity 86, not found after the fix 132
- follow-up: from the fix to function death, label end or 5 years; MH rate ratio, strata repo × loc (0.25 decade) × in-function edit size (1–2, 3–8, 9–32, > 32 lines).

| id | outcome | scarred: events / rate per fn-year | unscarred: events / rate | RR [99.75% CI] | call |
|---|---|---|---|---|---|
| **SCAR-R1** | later CVE fix | 4 / 0.033 | 137 / 0.047 | **0.88** [0.00, 8.39] | **underpowered** |
| **SCAR-R2** | later fix, any class | 15 / 0.169 | 526 / 0.288 | **0.35** [0.10, 1.58] | **not supported** |

Power rule: ≥ 15 events among scarred and among unscarred units.

## Part I — is DC-2's birth signal inherited scar tissue?

- DC-2's commented births (curl, OpenSSL, nDPI, harfbuzz): **18,816**; danger-commented 2,182; in prior-CVE files 2,661 (14.1%)
- reproduces DC-2: whole-cohort danger → first-CVE rate ratio 1.45 (DC-2 reported 1.45)

| id | claim | result | call |
|---|---|---|---|
| **SCAR-I1** | danger-commented births over-represented in prior-CVE files (two-sided) | MH OR **1.38** [0.94, 2.00] (99.75%); danger share 13.4% in prior-CVE files vs 11.3% elsewhere | **not supported** |
| **SCAR-I2** | DC-2's link holds in files with no prior CVE fix (one-sided) | rate ratio **1.55** (lower bound 1.04, α = 0.0025); first-CVE events danger / plain 111 / 409 | **SUPPORTED** |

Power rule (I2): ≥ 15 first-CVE events among danger-commented births in no-prior-CVE files.

## Descriptive (no verdicts)

- DC-2's rate ratio inside prior-CVE files: 1.17; outside (I2): 1.55; ratio 0.75
- Copied scars: of 2,182 danger-commented births, 9 (0.4%) carry a danger line whose text an earlier CVE fix had added somewhere in the repo; 235 (10.8%) one an earlier ordinary fix had added
- Scars still fully present at the function's last snapshot: 17 of 29 (59%)
- Scars left by **ordinary (other-fix)** repairs, same design (19,133 units, 245 scarred): R1 2.38 [0.68, 5.50] (13 / 441 events); R2 1.69 [1.13, 2.39] (151 / 8168)
- Top scar words (CVE fixes): must be 9, overflow 8, must not 4, do not 3, validate 2, bound 2, sanitize 2, sanitizer 2, assumed 1, careful 1
- Per repo, CVE-fix units scarred / R1 events (scarred, unscarred): curl 12/365 (1, 42); openssl 19/385 (3, 47); harfbuzz 2/206 (0, 18); ndpi 2/142 (0, 30); libarchive 0/0 (0, 0)

## Per repo (descriptive, no verdicts; fix labels differ by repo, so read the pooled claims with these)

| repo | CVE-fix units (scarred) | R1 RR (events scarred / unscarred) | R2 RR (events) | I2-style RR, no-prior files (danger / plain first-CVE events) | same, prior-CVE files |
|---|---|---|---|---|---|
| curl | 365 (12) | 0.42 (1 / 42) | 0.32 (5 / 191) | 1.30 (52 / 178) | 1.25 (21 / 69) |
| openssl | 385 (19) | 1.54 (3 / 47) | 0.27 (8 / 166) | 1.67 (42 / 148) | 1.25 (10 / 25) |
| harfbuzz | 206 (2) | inf (0 / 18) | inf (0 / 77) | 2.13 (9 / 40) | 0.00 (0 / 5) |
| ndpi | 142 (2) | 0.00 (0 / 30) | 42.77 (2 / 92) | 2.22 (8 / 43) | 0.91 (2 / 15) |
| libarchive | 0 (0) | — | — | — (not in DC-2) | — |

inf / nan = no events on one side within the repo's strata.

Runtime 321s · seed 2982.

## Reading (hand-written, not generated)

- **Danger comments at birth are foresight, not inherited scars (SCAR-I2 supported).**
  - In files with no prior CVE fix, danger-commented births reach a first CVE fix 1.55× as often as plain-commented
    ones (lower bound 1.04). That is stronger than inside prior-CVE files (1.17).
  - Danger wording barely clusters in files with a CVE past (I1: 1.38, CI spans 1).
  - Only 0.4% of danger-commented births carry text that an earlier CVE fix had written.
  - The ratio is above 1 in each repo (1.30–2.22), so it does not depend on how each repo labels fixes.
- **Whether scars mark lasting fragility stays open.**
  - At function grain, only 35 of 1,098 first CVE fixes (3.2%) left a danger line in the fixed function or its
    header. CF-H1's 8.8% counted any comment line anywhere in the touched files.
  - R1 is underpowered: 4 later CVE fixes among scarred functions.
  - R2 meets the power rule exactly (15 events) and is not supported. Its point estimate is 0.35, toward "lesson
    learned", but the CI is wide.
  - Descriptively, scars from *ordinary* fixes point the other way: R2 1.69 [1.13, 2.39]. CVE scars and ordinary
    scars may mean different things, but nothing here is a verdict on that.
- **Deviation from the registration: libarchive contributes nothing to Part R's claims.** Its fix labels
  (`events/libarchive_xc.json`) have no CVE class. The registration listed it for Part R without checking. It
  enters only the ordinary-fix descriptive row.
- **Per-repo rows were added before any output was read** (owner note 2026-11-11: fix labels mean different things
  in different repos). They are descriptive only. "inf" or 0.00 cells mean no events on one side.
