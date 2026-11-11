# Self-admitted debt comments in C: how long they live and what removes them (EXPLORATORY)

**Status: exploratory.** Every TODO / FIXME / XXX / HACK comment line in C/C++ files (tests, docs, fuzz, scripts and examples excluded) is followed through each repo's non-merge history. Script: `tools/debt_lifecycle.py`. Part A reads no fix label. Part B reads fix labels for the core repos only (curl, openssl, ndpi, harfbuzz, libarchive); the unseen repos (libgit2, libxml2, postgres, redis) are not read there.

- **removed** = the debt line left the file. **Moves** (same text removed and re-added in one commit) and **rewordings** (same marker, same file, same commit) are not removals. **repaid** = removed while the file still exists.
- Comment detection on diff lines is heuristic (see the script docstring).

## A. Survival (Kaplan-Meier; still present at HEAD = censored)

| repo | commits | debt items | moves / rewordings | removed (any) | of removed: file deleted | of removed: same author | median life, years | still present after 1 y | after 5 y |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| curl | 40,187 | 325 | 47 / 44 | 98% | 3% | 50% | 1.1 | 51% | 16% |
| openssl | 41,545 | 1,461 | 232 / 310 | 91% | 8% | 46% | 0.7 | 43% | 13% |
| ndpi | 5,428 | 251 | 95 / 25 | 38% | 17% | 46% | 7.5 | 78% | 66% |
| harfbuzz | 21,592 | 1,293 | 214 / 261 | 88% | 3% | 89% | 0.1 | 34% | 14% |
| libarchive | 7,486 | 433 | 42 / 42 | 47% | 9% | 52% | > observed | 73% | 58% |
| libgit2 | 12,535 | 360 | 70 / 72 | 76% | 6% | 60% | 0.3 | 39% | 28% |
| libxml2 | 7,831 | 1,065 | 169 / 361 | 53% | 19% | 59% | 20.7 | 72% | 59% |
| postgres | 65,885 | 3,141 | 903 / 1,086 | 72% | 8% | 53% | 3.4 | 68% | 41% |
| redis | 11,974 | 240 | 6 / 20 | 65% | 7% | 75% | 0.5 | 40% | 20% |

Same author = the removing commit's author email equals the adding commit's.

### By marker (all repos pooled)

| marker | items | removed | median life, years | after 5 y | bare (≤ 6 chars, e.g. `TODO`) |
|---|---:|---:|---:|---:|---:|
| TODO | 4,559 | 73% | 1.1 | 30% | 8% |
| FIXME | 436 | 86% | 1.1 | 32% | 3% |
| XXX | 3,529 | 73% | 3.0 | 39% | 3% |
| HACK | 45 | 67% | 2.7 | 43% | 0% |

### Debt still open at HEAD, by age

| repo | open items | median age, years | open > 10 years |
|---|---:|---:|---:|
| curl | 6 | 18.6 | 100% |
| openssl | 135 | 4.1 | 32% |
| ndpi | 156 | 3.2 | 7% |
| harfbuzz | 156 | 5.2 | 13% |
| libarchive | 229 | 16.9 | 87% |
| libgit2 | 85 | 12.8 | 67% |
| libxml2 | 505 | 21.5 | 82% |
| postgres | 891 | 12.6 | 59% |
| redis | 83 | 0.5 | 1% |

## B. What kind of commit repays debt? (core repos only; fix labels read here)

Compared with all non-merge commits touching C/C++ files. Repaid = removed while the file still exists.

| repo | repaid items | by a fix commit (any class) | all C commits that are fixes | by a CVE fix | all C commits that are CVE fixes |
|---|---:|---:|---:|---:|---:|
| curl | 311 | 34.1% | 38.9% | 0.32% | 0.86% |
| openssl | 1,225 | 16.7% | 32.7% | 0.08% | 0.85% |
| ndpi | 79 | 22.8% | 36.4% | 3.80% | 2.52% |
| harfbuzz | 1,108 | 12.6% | 24.6% | 0.18% | 0.48% |
| libarchive | 186 | 18.3% | 33.3% | 0.00% | 0.00% |

Item-level shares, not commit-level: one commit that removes many debt lines counts many times.

Runtime 94s.

## Reading (hand-written; exploratory)

- **Cross-check.** The open debt at HEAD found here matches what the independent profile study's debt density
  implies (`docs/comment_profiles_exploratory.md`): postgres 891 vs ~834, libxml2 505 vs ~500, OpenSSL 135 vs ~120,
  harfbuzz 156 vs ~152. redis is the exception (83 vs ~49). The tracker and the profile agree.
- **Repayment is a project habit, not a law.**
  - curl removed 98% of its debt comments, and the 6 left are all over 10 years old. That looks like deliberate
    clean-ups.
  - libxml2 removed 53%; its median debt comment lives 20.7 years, and 82% of its open debt is over 10 years old.
  - libarchive's median outlives the observation window.
  - Pooled, about 74% of debt comments are eventually removed. That happens to match the 74.4% reported for
    Maldonado et al.'s five Java projects (ICSME 2017, as cited by later work). The per-project spread (38–98%) is
    the bigger story.
- **About half of repayments are by the person who wrote the debt.** It is 46–60% in most repos. Projects dominated
  by one maintainer are higher (harfbuzz 89%, redis 75%).
- **Kinds of debt.** `XXX` lives longest (median 3.0 years vs 1.1 for TODO and FIXME). It reads as a standing warning
  more than a to-do. `FIXME` is the most often removed (86%).
- **Debt is not repaid by fix commits (Part B, core repos only).** In every core repo, fix commits repay debt less
  often than their share of commits: curl 34% vs 39%, OpenSSL 17% vs 33%, harfbuzz 13% vs 25%, libarchive 18% vs 33%,
  nDPI 23% vs 36%. CVE fixes almost never repay debt; nDPI is the exception, on 3 items.
  - Debt is paid down in clean-ups, refactors and feature work, not while fixing bugs.
  - **Caution:** these are item-level shares (one commit removing many lines counts many times), and there is no
    uncertainty interval. The unseen repos (libgit2, libxml2, postgres, redis) were not read for this, so it can be
    registered and tested there.
- **What this is not:** debt comments are not tied here to whether the code they mark breaks. CPF already found that
  debt density adds nothing to fix prediction at file grain.
