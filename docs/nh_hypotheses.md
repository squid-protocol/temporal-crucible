# NH — the natural history of code structure: function lifecycles and include-graph hubs — registered 2026-11-06, before any lifecycle or hub statistic

**Why.** Every study so far asked whether structure *predicts* fixes or work. This one asks how structure **lives**:
- how long functions survive;
- whether their shape freezes with age;
- whether the hubs of the include graph are stable;
- whether the include graph grows "rich get richer";
- whether hubs are a frozen core.

These are descriptive questions. Each claim below still has its pass rule fixed now, so it can fail.

**Data.**
- Quarterly engine scans:
  - curl, 105 walk snapshots (`forward-asof` DB, `e246915aa`; the release-tag rows in that DB are ignored);
  - nDPI, 43 (`forward-asof`, `e246915aa`);
  - openssl, 110 (`frec`, `da852aa54`);
  - harfbuzz, 62, and libarchive, 70 distinct commits (`sc-class`, `da852aa54`).
- Validation: function extraction and spans 97–100% against tree-sitter and ctags on curl, nDPI and openssl
  (`engine_validation.md`), and on harfbuzz' and libarchive's sister repos; include graph 99–100% from 2013 on.
- C/C++ source files only (`language IN ('c','cpp')`).

**Nothing below has been computed.** Only row counts were checked, to confirm the tables are populated.

## Part 1 — function lifecycles (LIFE)

**Identity.**
- A function is (file_path, func_name) within a snapshot. Duplicate names in one file (static helpers, `#ifdef`
  variants) keep the first row by start line.
- **Move rule:** a function whose key vanishes, with exactly one new key of the same name in another file in the
  same snapshot, is the same function moved.
- A function is alive from its first to its last snapshot. One still present in the final snapshot is censored.

**Shape.** (loc, complexity, func_archetype). A **shape change** is any difference between consecutive appearances.

| id | claim | measure | supported iff |
|---|---|---|---|
| **LIFE-H1** | **infant mortality**: functions die young more than old | quarterly death hazard at age < 1 y vs at age 3–5 y (life-table hazards) | hazard(< 1 y) > hazard(3–5 y) on **≥ 4 of 5** repos, and the pooled ratio's snapshot-bootstrap lower bound > 1 |
| **LIFE-H2** | **structural freeze**: shape changes less as functions age | quarterly shape-change rate of living functions at age < 1 y vs ≥ 3 y | rate(≥ 3 y) / rate(< 1 y) < 1 on **≥ 4 of 5** repos, and the pooled ratio's upper bound < 1 |
| **LIFE-H3** | **archetypes persist** | share of consecutive appearances with an unchanged `func_archetype`, among functions whose (loc, complexity) changed | > 0.80 pooled (lower bound); a label that survives edits is a real type |

**Descriptive.**
- Kaplan-Meier survival: median lifespan, and share alive at 5 and 10 years.
- The archetype transition matrix, the most common transitions in particular.
- Shape-change rate by age band.

## Part 2 — include-graph hubs (HUB)

**Graph.** Each snapshot's `edge_data` import edges between source files. In-degree = files that include this file.
Hubs = the top 10% of files by in-degree in that snapshot (ties included).

| id | claim | measure | supported iff |
|---|---|---|---|
| **HUB-H1** | **hubs are stable** | of the hubs at t, the share still hubs at the first snapshot ≥ t + 1 y | median over t > 0.70 on ≥ 4 of 5 repos (chance ≈ 0.10) |
| **HUB-H2** | **rich get richer** (preferential attachment) | for files present at t and t + 1 y: new in-edges gained ~ in-degree at t. Fit log(gain + 1) on log(k + 1), pooled over t; the slope estimates the attachment exponent | slope > 0 with snapshot-bootstrap lower bound > 0 on ≥ 4 of 5 repos |
| **HUB-H3** | **frozen core**: hubs change less than non-hubs of the same size and type | per file and year, changed = the git blob differs between t and t + 1 y. Mantel-Haenszel risk ratio, hub vs non-hub, strata = snapshot × extension (`.h` / other) × LOC decile | pooled RR < 1 with upper bound < 1 |

**Tests.**
- Bootstrap over snapshots within each repo, 5,000 rounds, seed 2982; repos are pooled with equal weight where
  pooling is stated.
- α = 0.01 per claim, two-sided where a direction is not given above, one-sided otherwise.
- There is no family correction across these six descriptive claims; each is reported on its own.

## Priors

- **LIFE-H1 leaning supported.** Classic software-evolution results: most code that dies, dies young.
- **LIFE-H2 leaning supported.**
- **LIFE-H3 leaning supported.** The ARCH-S result: about 98% of *file* labels survive small edits.
- **HUB-H1 leaning supported.**
- **HUB-H2 uncertain.** Linear preferential attachment is a famous claim for networks, but tested on code
  dependency graphs it is often sub-linear.
- **HUB-H3 leaning supported.** Widely-included headers are risky to edit, so they should change less.

---

## Results — 2026-11-06 (scorer `ed84afe` committed before running; report `nh.md`)

### Function lifecycles

| repo | functions tracked | median lifespan* | alive at 5 y | alive at 10 y |
|---|---:|---:|---:|---:|
| curl | 8,477 | 8.0 y | 65% | 44% |
| nDPI | 2,827 | > span | 84% | 57% |
| openssl | 29,291 | 15.8 y | 80% | 71% |
| harfbuzz | 8,668 | 12.2 y | 71% | 62% |
| libarchive | 5,388 | > span | 85% | 77% |

\*Functions born after the first snapshot (Kaplan-Meier).

| claim | curl / nDPI / openssl / harfbuzz / libarchive | pooled | bound | verdict |
|---|---|---:|---:|---|
| **LIFE-H1** infant mortality: death hazard(< 1 y) / (3–5 y) | 1.91 / 2.91 / 3.51 / 1.97 / 7.82 | **2.93** | lo 1.80 | **SUPPORTED** |
| **LIFE-H2** structural freeze: shape-change rate(≥ 3 y) / (< 1 y) | 0.70 / 0.69 / 0.48 / 0.46 / 0.15 | **0.46** | hi 0.59 | **SUPPORTED** |
| **LIFE-H3** archetype kept when size or complexity changed | 0.90 / 0.89 / 0.88 / 0.80 / 0.84 | **0.876** | lo 0.862 | **SUPPORTED** |

- **Shape freezes but does not stop.** An old function still changes shape in 1–9% of quarters, against 7–13% for
  young ones.
- **The most common archetype transitions** are Parameter Forwarders ⇄ Compute Cores and Compute Cores → Many-Argument
  Workhorses. Functions that grow tend to accumulate logic and then arguments.

### Include-graph hubs

| repo | hubs still hubs after 1 y (median) | attachment slope | lo | hub vs non-hub, changed in 1 y (MH RR) |
|---|---:|---:|---:|---:|
| curl | 0.96 | 0.330 | 0.310 | 1.04 |
| nDPI | 0.92 | 0.484 | 0.445 | 1.11 |
| openssl | 0.98 | 0.273 | 0.242 | 1.23 |
| harfbuzz | 0.97 | 0.237 | 0.199 | 1.02 |
| libarchive | 1.00 | 0.195 | 0.151 | 1.62 |

- **HUB-H1, stable hubs: SUPPORTED (5/5).** The hub set barely changes from year to year.
- **HUB-H2, rich get richer: SUPPORTED (5/5), and sub-linear.** Gain in includers ∝ (in-degree)^0.2–0.5: popular files
  do attract more new includers, but far less than proportionally.
- **HUB-H3, frozen core: NOT supported. It is reversed.** Hubs are *more* likely than same-size, same-type files to
  change within a year: pooled RR 1.12 (bound 1.15), every repo ≥ 1.02, libarchive 1.62. Widely-included headers are
  where new declarations and API surface get added, so they are a stable *position* with active *content*.

### Caveats

- **Function identity is (file, name)**, plus the cross-file move rule. A rename within a file counts as a death and a
  birth, which can inflate infant mortality slightly.
- Quarterly resolution.
- Functions that existed before the first snapshot are excluded from the age-based measures (left truncation).
- "Changed" for hubs means the git blob differs a year later: any edit counts.
