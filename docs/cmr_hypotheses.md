# CMR — do comments, and danger comments, sit differently by call-graph role, and does their link to each fix class change with role? — DRAFT registration 2026-11-10 (owner OK pending; no statistic computed)

**Why.**
- CGK found strong role structure. Hubs (most-called) are public, branchy, pointer-handling workhorses.
  Orchestrators (call many) are straight-line glue. The periphery (low k-core) is private, low-level code.
- Fix classes split by position. Extrinsic fixes are enriched in hub-hosting files (1.35) and peripheral files
  (1.49), and depleted in coupled and cyclic ones. CVE fixes lean toward coupled and cyclic files.
- DC-2 found that danger-language comments at birth predict CVE fixes (1.45×). Its descriptive rows: regression 1.01,
  extrinsic 1.20.
- The owner's question (2026-11-10): do comments in general, and danger comments in particular, cluster differently
  by role? Does what they predict depend on role and on fix class?
- No study has crossed comments with roles. CGK could not have: comment signals were 0 at function grain before
  gitgalaxy#8200, and CGK used none.

## Prior work

- **Program.** CGK (roles × signals × fix-class file positions); DC-2 (danger comments → CVE); CF-H1 (CVE fixes add
  danger comments); COM-H4 (header drift: not supported, wrong direction).
- **Arafat and Riehle, "The commenting practice of open source", OOPSLA Companion 2009.** Found a stable comment
  density across open-source projects, so comment presence varies more by kind of code than by project.
- **Zimmermann and Nagappan, "Predicting Defects Using Network Analysis on Dependency Graphs", ICSE 2008.**
  Network position predicts defects beyond complexity. This study asks whether comments interact with position.
- **Tan et al., iComment (SOSP 2007).** Comments state assumptions that the code violates. Danger comments are the
  authors' own record of such assumptions.
- **What is new here:** comments × call-graph role × fix class, at function grain, prospective from birth.

The citations are from memory and are checked against the published papers before the result doc ships.

## Data

- **Repos:** curl, OpenSSL, nDPI, harfbuzz (DC-2's) **plus libarchive** (CGK's fifth repo, never used by DC). nDPI
  is in both.
- **Networks and roles:** CGT's quarterly call networks (`tools/cgt_eval.py` `snapshot_networks`) and CGK's role
  rules, per snapshot:
  - **hub:** top 10% by in-degree (in-degree > 0);
  - **orchestrator:** top 10% by out-degree (out-degree > 0);
  - **periphery:** undirected k-core number below the snapshot median;
  - **other:** none of the three. Roles can overlap; each is tested as "role vs not".
- **Functions:** births after the first snapshot with loc ≥ 3 (`ints_eval.lives`); role read **at the birth
  snapshot**.
- **Comments at birth:** DC's definition. These are engine comment lines inside the function or in the block directly
  above, plus DC's fixed danger lexicon.
  - **commented** = ≥ 1 comment line;
  - **danger** = commented with ≥ 1 lexicon match.
- **Fix labels:** `chg_eval.fix_events` / `map_fix`. The classes are latent (CVE), regression and extrinsic, plus
  other-fix as the reference.

## Part P — placement (no outcome)

Within repo × log₁₀ loc (0.1 decade) strata, two-sided CMH odds ratio, role vs not:

| id | claim (two-sided) | bar |
|---|---|---|
| **CMR-P1** (×3 roles) | commented vs uncommented functions differ by role | p < 0.01/6 |
| **CMR-P2** (×3 roles) | among commented functions, danger vs plain differs by role | p < 0.01/6 |

Descriptive: comment lines per loc by role; the top 10 danger words by role.

Priors, stated without a direction:
- hubs (public API) more commented;
- the periphery (private, low-level) less commented but, when commented, more often danger-worded (bit-twiddling,
  allocation, "must", "overflow").

## Part F — does the comment → fix link change with role? (prospective from birth)

- **Measure.** For each fix class c ∈ {latent, regression, extrinsic} and each role R, the whole-life first-fix
  **rate ratio** (MH, DC-2's strata: repo × loc bin × file had a CVE fix before birth), computed inside R and outside
  R.
- **Interaction.** The ratio of those two rate ratios: RR_in-R ÷ RR_out-of-R.
- **Inference.** File-cluster bootstrap (2,000, seed 2982), two-sided.

| id | exposure | cells | supported iff (per cell) |
|---|---|---|---|
| **CMR-FD** | danger vs plain-commented | 3 roles × 3 classes = 9 | interaction CI excludes 1 at α = 0.01/9 |
| **CMR-FC** | commented vs uncommented | 9 | the same |

- **Power rule.** A cell is evaluable only with ≥ 20 first-fix events of that class in each of the four role ×
  exposure groups. Otherwise it is underpowered, not a verdict.
- **What DC-2 already showed, so it is not re-tested here:** the pooled rate ratios by class (latent 1.45,
  regression 1.01, extrinsic 1.20) on four of these five repos. Only the role interactions are new. libarchive's
  births are wholly unseen and get a per-repo descriptive row.

## Descriptive (no verdicts)

- The 9 within-role rate ratios themselves, per family.
- Role at the function's last live snapshot instead of at birth (hubs gain callers over time, CGN-A2).
- Per repo, with libarchive separately.

## Priors

- **P:** role differences in commenting are likely, given CGK's sharp role profiles. The direction is open.
- **F:** most cells will be underpowered. CVE fixes in DC-2 were 144 danger-commented first events over all roles,
  and hubs and orchestrators are 10% each. A **regression × hub** or **extrinsic × periphery** interaction is the
  most plausible.
- **Size:** roles correlate with size (hubs are bigger); the loc strata carry that.

## Known limits

- Roles at birth are noisy for young functions (few callers yet). The last-snapshot sensitivity row is there for
  that.
- The quarterly scan DBs predate gitgalaxy#8200. Comments come from the current engine's Prism split at the birth
  blob, as in DC, not from the DB columns.
