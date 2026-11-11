# CPF — does a file's comment profile predict its next year of fixes? (SCORED)

Registration `docs/cpf_hypotheses.md` (owner OK 2026-11-11). Profiles: `tools/comment_profiles.py` (engine c7cdf7832). Aggregates only. File-cluster bootstrap 2,000, seed 2982; α = 0.01/4.

- file-years: curl 3,048, openssl 18,694, ndpi 1,307, harfbuzz 2,147, libarchive 2,093, libgit2 2,777, libxml2 1,834, postgres 22,864, redis 2,630
- training era = anchor years ≤ each repo's median anchor year; claims scored on the later test era

## Registered claims

| id | outcome, repos | test file-years (positives) | AUC B | AUC B + P | lift | one-sided lower bound | 99% CI | call |
|---|---|---:|---:|---:|---:|---:|---|---|
| **CPF-F** | any fix; core 5 | 16,027 (6,522) | 0.773 | 0.772 | **-0.0003** | -0.0017 | [-0.0016, +0.0009] | **not supported — replicated null** |
| **CPF-V** | CVE fix; curl, OpenSSL, nDPI, harfbuzz | 14,876 (433) | 0.772 | 0.772 | **+0.0000** | -0.0066 | [-0.0061, +0.0064] | **not supported — replicated null** |
| **CPF-R** | any fix; unseen libgit2, libxml2, postgres, redis | 19,262 (7,691) | 0.806 | 0.808 | **+0.0027** | +0.0011 | [+0.0012, +0.0042] | **SUPPORTED** |

| id | claim | result | call |
|---|---|---|---|
| **CPF-N** | comment neglect (code +20%, body comments flat) → next-year fix, among 2,948 growing file-years, all 9 repos | MH RR **0.88** [0.74, 1.07] (99.75%); neglected 411 file-years, 164 with a fix (40% vs 67%) | **not supported** |

Lift claims: supported iff lift > 0 and lower bound > 0; a failed claim is a replicated null iff its 99% CI lies inside ±0.02. CPF-V needs ≥ 20 test-era positives; CPF-N ≥ 20 neglected file-years with a fix.

## Descriptive (no verdicts)

- **CPF-F**: single measures, lift over B: density -0.0003, header coverage -0.0001; recall at 20% of code lines: B 43.3%, B + P 43.4%; C chosen B 10, B + P 0.1
  - P coefficients (standardized): density +0.131, header_cov -0.029, danger_share -0.024, debt_kloc +0.017, dead_kloc +0.072
  - per repo, AUC B → B + P (positives / file-years): curl 0.797 → 0.796 (1,443 / 2,100); openssl 0.771 → 0.770 (3,775 / 10,428); ndpi 0.740 → 0.746 (251 / 768); harfbuzz 0.715 → 0.713 (744 / 1,580); libarchive 0.776 → 0.777 (309 / 1,151)
- **CPF-V**: single measures, lift over B: density -0.0003, header coverage -0.0008; recall at 20% of code lines: B 36.7%, B + P 35.1%; C chosen B 0.0316228, B + P 0.0316228
  - P coefficients (standardized): density +0.045, header_cov +0.108, danger_share +0.094, debt_kloc +0.081, dead_kloc +0.053
  - per repo, AUC B → B + P (positives / file-years): curl 0.776 → 0.769 (170 / 2,100); openssl 0.754 → 0.761 (155 / 10,428); ndpi 0.941 → 0.934 (40 / 768); harfbuzz 0.660 → 0.657 (68 / 1,580)
- **CPF-R**: single measures, lift over B: density +0.0019, header coverage +0.0024; recall at 20% of code lines: B 48.8%, B + P 49.0%; C chosen B 3.16228, B + P 10
  - P coefficients (standardized): density -0.008, header_cov +0.160, danger_share +0.001, debt_kloc +0.081, dead_kloc +0.038
  - per repo, AUC B → B + P (positives / file-years): libgit2 0.754 → 0.751 (385 / 1,843); libxml2 0.800 → 0.808 (422 / 1,066); postgres 0.791 → 0.794 (6,449 / 14,756); redis 0.892 → 0.897 (435 / 1,597)
- libxml2 CVE (descriptive): 17 test positives; AUC B 0.273 → B + P 0.409 (lift +0.1358)

Runtime 54s · seed 2982.

## Reading (hand-written, not generated)

- **A file's comment profile does not help predict its fixes or its CVE fixes in the core repos.** These are
  replicated nulls with tight intervals:
  - any fix: lift −0.0003, 99% CI within ±0.002;
  - CVE fix: +0.0000, within ±0.007.
  - Size, churn, fix history, age and prior CVE already give AUC 0.77, and nothing in the comments adds to it.
  - This is "everything reduces to size and history", now confirmed for comments at file grain.
- **In the unseen repos the profile adds a statistically real but negligible lift (CPF-R).** +0.0027 AUC;
  effort-aware recall 48.8% → 49.0%.
  - It meets the registered bar, which had no minimum effect size, so it is reported as supported. It is too small
    to matter in practice.
  - It comes mainly from header coverage, in a pool dominated by postgres: the same project where Ibrahim et al.
    found comment practice linked to bugs.
  - The core/unseen difference fits the owner's observation that fixes mean different things in different repos.
    It is not evidence that comments matter more in those projects.
- **Comment neglect does not precede more fixes (CPF-N, 0.88 [0.74, 1.07]).** The raw gap (40% vs 67% next-year fix
  rate) almost vanishes once size and prior fixes are matched. Files that grow without new comments are mostly
  quieter files to begin with.
- **The libxml2 CVE row is uninterpretable.** It has 17 positives, and its baseline AUC of 0.27 is below chance.
  Ignore it.
- **Process notes.**
  - The scorer was committed before running (`94c8b19`).
  - The first run crashed at import before reading anything; the fix is `755e2c2`.
  - No other change was made after the registration.
