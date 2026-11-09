# CGR — replicate the call-network studies (CGT, CGN, CGK) on eight unseen repositories in five languages, and test language bias — registered 2026-11-08, before any scan, label harvest or statistic on these repositories

**Why.** CGT, CGN and CGK (2026-11-08, merged) were scored on five C libraries this programme has studied heavily.
Their leads (rewiring, coupling and cycles predicting later fixes; extrinsic fixes in peripheral hub files; the hub
profile) need unseen data. The owner (2026-11-08) also asked whether findings such as pointer enrichment in hubs are
specific to memory-managed C rather than general: language bias.

## Replication set (fixed now; none used in any call-network study)

| repo | language | snapshots | CVE labels |
|---|---|---|---|
| libgit2 | C | existing walk, 72 quarters | — |
| PostgreSQL | C | existing walk, 121 quarters | — |
| libxml2 | C | new quarterly walk | `events/libxml2.json` |
| redis | C | new quarterly walk | — |
| prometheus | Go | new quarterly walk | — |
| commons-lang | Java | new quarterly walk | — |
| sphinx | Python | new quarterly walk | — |
| ripgrep | Rust | new quarterly walk | — |

- **New walks:** the newest first-parent commit before each calendar-quarter boundary, from the first quarter whose
  tree holds ≥ 50 source files of the repo's language, to the last boundary before 2026-11-08.
- **Scans:** one engine for all eight, gitgalaxy `8f96d76ba`, git history off, each snapshot scanned from a clean
  `git archive`.
- **Fix labels:** `tools/xc_harvest.py --exts` with the language's source extensions (C `.c,.h`; Go `.go`; Java
  `.java`; Python `.py`; Rust `.rs`).
- **Source files** for the network: the same extensions. The network, rewiring, roles and every measure are exactly
  as in `docs/cgt_hypotheses.md`, `cgn_hypotheses.md` and `cgk_hypotheses.md`, run by those scorers unchanged, with
  the repository list, the extension set and the pass rules below swapped in.

## Pass rules

- **Per-repo claims:** "≥ 4 of 5 repos" becomes **≥ 6 of the evaluable repos out of 8** (75%).
- **Pooled CMH claims:** pooled over all eight repos with the original α.
- **Direction:** each claim is replicated in the direction it was **observed** (registered direction where it held;
  the reverse where it came out reversed: CGT-3b, CGN-C2, CGK-K1, K2, H1). Claims that failed are retested as
  registered and expected to fail again.

## Claims replicated (R- prefix; definitions and α as originally registered)

| family | claims (expected outcome from the original run) |
|---|---|
| CGT | R-1a ✓, R-1b ✓, R-1c ✗, R-2a ✗, R-2b ✗, R-3a ✗; **R-3b** CVE fixes rewire *more* than other fixes (libxml2 only; likely not evaluable); **R-4** rewired files get later fixes beyond churn ✓; R-5 ✓ |
| CGN | R-A1 ✓, R-A2 ✓, R-A3 ✓, R-B1 ✗, R-B2 ✗, R-B3 ✓, **R-C1** cycles ✓, **R-C2** duplicated wiring → *fewer* fixes, **R-C3** coupling ✓, R-C4 ✗, R-D1 ✗, R-D2 ✓, R-E1 ✓ |
| CGK | R-K1 hubs *more* complex per line, R-K2 orchestrators *less*, R-K3 hubs public ✓, R-H1 hubs *not* low-rung; R-KS screen (Bonferroni); R-F grid (extrinsic: hub-hosting ↑, coupled ↓, cyclic ↓, peripheral ↑) |

## New claims

| id | claim | supported iff |
|---|---|---|
| **CGR-L1** | **language-neutral hub core:** hubs carry public surface, arguments and branches in every language | `arch_api`, `struct_args`, `struct_branch` each enriched in hubs (per-repo CMH over loc quintiles, OR > 1, p < 0.05) in ≥ 6 of 8 repos |
| **CGR-L2** | **pointer enrichment is a memory-management effect:** hubs are pointer-enriched in C and not in Java or Python | `state_pointers` in hubs OR > 1, p < 0.05 in ≥ 3 of the 4 C repos, **and** not significantly > 1 in commons-lang and sphinx (Go and Rust, which have pointers or references, are descriptive) |
| **CGR-L3** | **language bias is limited:** most screen cells keep their sign across languages | of the 78 screen cells with a significant call in the original C run, ≥ 60% have the same sign of log OR in the pooled non-C repos (prometheus, commons-lang, sphinx, ripgrep) |
| **CGR-M1** | **which network signal carries later fixes:** rewiring, coupling and cycles in one model | file-years (CGN-C design): logistic regression of fix-in-next-year on rewired-in-prior-year, top-quintile coupled, in-cycle, log functions, log churn, prior fix and repo fixed effects, over all eight repos; each of the three is reported with its OR and Wald p; a signal **carries** iff OR > 1, p < 0.01/3 |

## Not evaluable

As in the original registrations. A repo whose scans fail on more than 20% of its snapshots is dropped and named.

## Guards

Registration before any scan, harvest or statistic. One run. One engine for all eight repos. Verdicts either way,
per language as well as pooled. The original five repos are not used.
