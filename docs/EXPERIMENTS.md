# Experiment index — what we've tried to correlate

This is the **map** of the temporal crucible: every predictor we have tested against
real defect ground truth, what outcome we tested it against, on which repo, and how it
came out. It is a *view*, not a source of truth — the authoritative record is still
[`HYPOTHESES.md`](HYPOTHESES.md) (verdicts, direction, α) and the epic
([gitgalaxy#2982](https://github.com/squid-protocol/gitgalaxy/issues/2982)) +
`tc#` issues (registrations and open work). If this file and the register disagree,
the register wins; fix this file.

Read order for someone new: this file (what's been tried) → [`HYPOTHESES.md`](HYPOTHESES.md)
§ "plain-language summary" (what we learned) → the specific result doc (how).

------------------------------------------------------------------------

## 1. The correlation matrix — predictor × outcome

The question this leg exists to answer (gitgalaxy `README.md` § "Structural Surface
Profile"): **do GitGalaxy's measurements correspond to real software risk, beyond a
line count?** Every row is a *predictor* GitGalaxy can emit; every test asks whether it
beats `LOC` at ordering some *defect outcome*. The bar is always **defect-lift over
size**, never raw correlation.

Legend: ✓ survives · ✗ falsified/reduces-to-size · ⚠ contested/discounted · ○ open/registered.

| Predictor (what GitGalaxy measures) | vs which outcome | curl | nDPI | Durable finding | Hypotheses |
|---|---|---|---|---|---|
| **Recidivism** (prior CVE/bug-fix count) | next fix @review-budget, AUC | ✓✓ | ✓✓ | **SURVIVES** — beats every static ranking, both repos, p<1e-4. The rung-7 baseline. | RW-H2, N-RW2 |
| **Change entropy** (`HCM1_LD_30`, Hassan HCM) | fresh bug labels, out-of-selection | ✓ | ○ | **SURVIVES (1 repo)** — only *feature* to beat LOC out-of-selection (AUC .868 vs .830). Repo-#3 replication owed. | HV-H1, HV-H2, B-H3 |
| **Centrality / PageRank** | CVE + bug labels, by size band | ✗ / ⚠ | ⚠ | small-file: **dead** (inverted, AUC .26); mid-band (49–108 LOC): **open candidate**, registered for repo-#3 | C-H1, C-H2, B-H1, B-H2, N-FIRST |
| **Aggregate structural exposure** (Σ `risk_*`) | fix reduces / introduce raises; @budget | ✗ | ✗ | **= SIZE** — nulls equivalence-confirmed (TOST) on both repos | H1, H2, N-H1, N-H2, RW-H1, N-RW1, IV-H1 |
| **Per-vector exposure** (`safety_score`, `tech_debt`, danger density) | fix Δ; implicated functions | ⚠ | ✗ | curl-only (`safety_score` p=.007); fails to replicate on nDPI; density artifacts caught | H3, R2-H1, N-H3, D-H1, D-H2, D-H1′ |
| **Fix-shaped grammar** (branch/pointer adds, no new alloc) | security-fix vs control | ✓ | ✗ | **curl/human-report-specific** — not a size artifact (survives churn floor), does not travel to fuzzer-found fixes | G-H1, G-H2, N-GRAM, N-FIXSHAPE, W1-H3 |
| **Mechanism specificity** (right vector ↔ right CWE) | CWE-family labels | ✗ | n/a | vectors read as one code-mass blob, not mechanism-specific; cert/auth vocab dead on C | S-H0, S-H1, S-H2, S-H3, S-H4 |
| **Line count (`LOC`)** | — | — | — | **the baseline** every predictor above must clear | (control) |

**One-sentence standing (after 2 repos, 3 label families):** *history predicts
(recidivism replicated; change entropy out-of-selection), structure describes* —
everything structural reduces to size, the fix grammar is curl-specific, and centrality's
only live lead is the mid-size band. Repo #3 (openssl) carries every open question.

### Outcome (label) families in play
- **CVE-fix / CVE-introducing** — OSV GIT ranges (curl 186/137, nDPI 121/73)
- **Bug labels** — `Fixes #` / `Bug:` / `regression` (curl, 957 usable) — power the small bands CVEs can't
- **CWE families** — memory / cert-auth / info-leak / concurrency (specificity battery; needs repo #3)
- **Wave-1 classes** — reverts, follow-ups (instrument sanity)
- **First-CVE files** — pre-event standing vs age/size-matched clean files

------------------------------------------------------------------------

## 2. Register crosswalk — hypothesis → experiment → doc

Every registered hypothesis, the `tc#` experiment it belongs to, and the doc that
evaluates it. Verdicts are summarized here and authoritative in [`HYPOTHESES.md`](HYPOTHESES.md).

| id | correlate (short) | repo | tc# | verdict | doc |
|---|---|---|---|---|---|
| H1 | aggregate exposure ↓ on fix | curl | — (pilot) | ✗ | exposure_history_report.md |
| H2 | aggregate exposure ↑ on introduce | curl | — | ✗ | exposure_history_report.md |
| H3 | per-vector names carriers | curl | — | ✓ `safety_score` | exposure_history_report.md |
| D-H1 / D-H2 | function guard deficit | curl | — | ✗ degenerate | signal_anatomy.md |
| RW-H1 | exposure > LOC @20%-budget | curl | — | ✗ | rw_hypotheses.md |
| RW-H2 | **recidivism > static** | curl | tc#28 | **✓✓** | rw_hypotheses.md |
| W1-H1 | reverts are net-removal | curl | tc#1 | ✓ | wave1_hypotheses.md |
| W1-H2 | incomplete fixes thinner | curl | tc#1 | ✗ | wave1_hypotheses.md |
| W1-H3 | follow-ups carry grammar | curl | tc#1 | ✗ | wave1_hypotheses.md |
| IV-H1 | structure adds over size | curl | — | ✗ | incremental_value.md |
| HV-H1 | HCM variant clears size wall | curl | tc#24 | ✗ | hcm_variants.md |
| HV-H2 | best HCM beats LOC pooled | curl | tc#24 | ⚠ discounted | hcm_variants.md |
| C-H1 | small-file centrality > LOC | curl | tc#25 | ⚠ not evaluable | centrality_bands.md |
| C-H2 | centrality lift monotone w/ size | curl | tc#25 | suggestive | centrality_bands.md |
| B-H1 | small-file centrality (bug labels) | curl | tc#25 | ✗ | bh_eval.md |
| B-H2 | monotone lift shape (bug labels) | curl | tc#25 | ✗ (inverted-U) | bh_eval.md |
| B-H3 | **`HCM1_LD_30` selection-free** | curl | tc#24 | **✓** | bh_eval.md |
| G-H1 | grammar returns under floor | nDPI | — | ✗ | grammar_floor.md |
| G-H2 | grammar survives floor | curl | — | ✓ | grammar_floor.md |
| N-H1 | aggregate exposure (replicate) | nDPI | — | ✗ null-replicates | ndpi_exposure_report.md |
| N-H2 | introduce raises (replicate) | nDPI | — | ✗ null-replicates | ndpi_exposure_report.md |
| N-H3 | `safety_score` (replicate) | nDPI | — | ✗ fails | ndpi_exposure_report.md |
| N-GRAM | fix grammar (replicate) | nDPI | — | ✗ fails | ndpi_signal_anatomy.md |
| N-FIXSHAPE | fix-shaped signature (replicate) | nDPI | — | ✗ fails | ndpi_signal_anatomy.md |
| N-RW1 | exposure > LOC @budget (replicate) | nDPI | — | ✗ null-replicates | ndpi_rw.md |
| N-RW2 | **recidivism (replicate)** | nDPI | tc#28 | **✓✓** | ndpi_rw.md |
| N-FIRST | standing separates first-CVE | nDPI | tc#25 | ✓ (centrality) | ndpi_stage2.md |
| R2-H1 | danger density at equal length | nDPI | — | ✗ | ndpi_signal_anatomy.md |
| D-H1′ / D-H2′ | branch-per-danger guard | nDPI | — | ✗ | ndpi_stage2.md |
| S-H1 | memory ↔ danger cluster | curl held-out | tc#26 | ✗ | specificity_curl_heldout.md |
| S-H2 | cert/auth ↔ crypto/auth | curl held-out | tc#26 | ⚠ vocab dead | specificity_curl_heldout.md |
| S-H3 | info-leak ↔ io/api | curl held-out | tc#26 | ✗ | specificity_curl_heldout.md |
| S-H4 | concurrency ↔ sync/locks | repo #3 | tc#26 | ○ untestable on curl | — |
| S-H0 | the discriminant (diagonal?) | curl held-out | tc#26 | ✗ | specificity_curl_heldout.md |
| M-H1..M-H3 | multi-label signatures | curl | tc#1 | ○ pending | — |
| X-H1 | unpaired-allocation ↔ introduce | kernel harvest | tc#27 | ○ registered | keyword_pools_explore.md |
| X-H2 | fix-grammar gradient | openssl | tc#26 | ○ registered | keyword_pools_explore.md |

------------------------------------------------------------------------

## 3. Open experiments (`tc#` roster)

Live experiments and engine gaps, from the `temporal-crucible` issue tracker. Each should
carry a `Register:` line naming its hypothesis ids (see § naming below).

| tc# | title | hypotheses | state |
|---|---|---|---|
| tc#26 | Repo #3: openssl fixed-side harvest (CHANGES parser + NVD CWE join) | S-H1..H4, S-H0, X-H2 | open — primary repo-3 |
| tc#27 | Repo-3 sleeper: kernel subsystem-scoped harvest (net/, fs/) | X-H1 | open — only gold-standard introduced-side |
| tc#28 | Function-grain recidivism — sharpen the strongest predictor | RW-H2, N-RW2 (follow-up) | open |
| tc#24 | Change-entropy (`HCM1_LD_30`) engine adoption + repo-3 replication | HV-*, B-H3 | open |
| tc#25 | Mid-band (49–108 LOC) centrality — pre-register for repo #3 | C-*, B-H1/2, N-FIRST | open |
| tc#37 | SYS/INT wave: risk as a system property (module-level, dispersion, interactions) | (new — register) | open |
| tc#32 | Train the classifier the dataset was built for: multivariate keyword importance | (new — register) | open |
| tc#33 | Net-REMOVE pools + pairing-deviation features | X-H1 sibling | open |
| tc#29 | Engine gap: process features ablated to zero — add history-enabled forward-prediction mode | (engine) | open |
| tc#3 | Panel analyses over the 219-release walk (trajectories, dwell-vs-exposure) | (exploratory) | open |
| tc#1 | Phase M: multi-label harvesters + M-H1..M-H3 | M-H1..M-H3, W1-* | open |

------------------------------------------------------------------------

## 4. Result-doc index

Each analysis write-up, one line. Confirmatory docs evaluate registered hypotheses;
exploratory docs claim no p-values and feed future registrations.

**Confirmatory (evaluate registered hypotheses)**
- `exposure_history_report.md` — H1/H2/H3, curl aggregate + per-vector deltas
- `signal_anatomy.md` — D-H1/D-H2, curl function-grain guard deficit
- `rw_hypotheses.md` — RW-H1/RW-H2, review-budget ranking (recidivism)
- `wave1_hypotheses.md` — W1-H1..H3, reverts/follow-ups
- `incremental_value.md` — IV-H1, structure-over-size
- `grammar_floor.md` — G-H1/G-H2, churn-floor de-confound of the grammar
- `hcm_variants.md` — HV-H1/HV-H2, 36-variant HCM sweep
- `centrality_bands.md` — C-H1/C-H2, PageRank by size band (CVE)
- `bh_eval.md` — B-H1..H3, bug-label expansion (HCM validates, small-file centrality dies)
- `ndpi_exposure_report.md` — N-H1/N-H2/N-H3, nDPI replication
- `ndpi_signal_anatomy.md` — N-GRAM/N-FIXSHAPE/R2-H1, nDPI grammar + density
- `ndpi_rw.md` — N-RW1/N-RW2, nDPI ranking
- `ndpi_stage2.md` — D-H1′/N-FIRST + equivalence CIs
- `specificity_curl_heldout.md` — S-H0..H3, held-out curl specificity battery

**Exploratory / survey (no verdicts; seed future registrations)**
- `keyword_pools_explore.md` — pairing-deviation pools → X-H1/X-H2
- `specificity_density_explore.md` — family-signal beyond size (density/length-matched)
- `walk_trajectories.md` — 219-release panel trajectories (tc#3)
- `centrality_bands.md` (mid-band cells) — repo-#3 candidate
- `repo2_survey.md` / `repo3_survey.md` — candidate-repo selection
- `class_signals.md` — per-class prevalence profiles (Phase-M precursor)
- `hcm_variants.md` (family pattern) — HCM design space
- `instrument_controls_forensics.md` — instrument audit (caught gitgalaxy#2988)
- `bh_eval.md` (mid-band cells) — exploratory context outside the registered family

------------------------------------------------------------------------

## 5. Naming convention (use this for the repo-#3 wave)

The register grew batch-by-batch, so prefixes historically encoded *which batch*
(`N-` = nDPI, `B-` = bug-label, `W1-` = wave 1). Going forward, keep it consistent:

- **`<SCOPE>-H<n>`** for a confirmatory claim: `<SCOPE>` = the repo/wave it's registered
  *for* (`O-` = openssl/repo-3, `K-` = kernel harvest, `SYS-` = the tc#37 system wave).
- **`<SCOPE>-<NAME>`** (word, not `H<n>`) for a *named* test that isn't a numbered
  hypothesis in a family — as with `N-GRAM`, `N-FIXSHAPE`, `N-FIRST`.
- A replication of an existing claim on a new repo keeps the **base name prefixed by the
  new scope** (curl `RW-H2` → nDPI `N-RW2` → openssl `O-RW2`), so a predictor's whole
  cross-repo history reads down one grep.
- Every registration lands in **three places, same session**: the epic comment
  (timestamp = the pre-registration proof), a `Register:` line on its `tc#` issue, and a
  row in [`HYPOTHESES.md`](HYPOTHESES.md). Then this index gets a row. Registration and
  verdict never ship in the same PR (see [`CONTRIBUTING.md`](../CONTRIBUTING.md)).

New confirmatory experiments start from [`_experiment_template.md`](_experiment_template.md).
