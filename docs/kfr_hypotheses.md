# KF-R and KF-L — replicate `goto` ↔ lifetime faults on unseen repos, and localize it to functions — registered 2026-11-06, before any new repo is cloned

**Origin.** KF-H3 (`kf_hypotheses.md`, PR #68), on nDPI + openssl:
- files containing `goto` are ~13× more likely, at equal size and evidence, to be where a **lifetime** fault is fixed;
- for **bounds** faults the figure is ~1.9×;
- the ratio is 7.1 (lo 2.77).

It rests on 26 lifetime events, and curl (context) does not show it. This entry replicates it on repos never touched
by this program, and tests where *inside* a file the effect lives.

## Repos (unseen; none cloned, scanned or harvested before this entry)

| repo | clone | OSS-Fuzz project (OSV) |
|---|---|---|
| libxml2 | `https://gitlab.gnome.org/GNOME/libxml2.git` | libxml2 |
| libtiff | `https://gitlab.com/libtiff/libtiff.git` | libtiff |
| libpng | `https://github.com/pnggroup/libpng.git` | libpng |
| libexif | `https://github.com/libexif/libexif.git` | libexif |
| file (libmagic) | `https://github.com/file/file.git` | file |

**Why these.** They are long-lived C libraries that parse untrusted input and have OSS-Fuzz histories with sanitizer
crash types, chosen for those properties before any of their data was seen. A repo's events come from
`tools/event_harvest.py --source oss-fuzz`, with the repo-filter set to the repo name.

## Gates (binding, checked before any KF-R/KF-L statistic)

- **G1 — engine extraction (localization needs function spans).**
  - Run `tools/engine_validate.py` (gitgalaxy's own audit tools: tree-sitter, Universal Ctags, libclang) on the head
    snapshot of each new repo, engine `32619e4a5`.
  - A repo enters **KF-L** only if functions vs tree-sitter have recall and precision ≥ 95% **and** span start and end
    are exact for ≥ 95% of functions.
  - nDPI and openssl already pass (`engine_validation.md`).
- **G2 — construct counts.**
  - On the head snapshot of all seven repos, compare per C file the regex counts (KF's `GOTO`, `MACRO`) with
    tree-sitter-c node counts (`goto_statement`, `preproc_function_def`).
  - Gate: **exposure agreement (count > 0) ≥ 98% of files** for each construct, pooled.
  - If it fails, both KF-R and KF-L use tree-sitter counts instead (the registered fallback), and the regex result is
    reported.
- **G3 — power.** KF-R needs ≥ 20 lifetime **and** ≥ 20 bounds events pooled over the five new repos. Otherwise it is
  not evaluable.

## KF-R — file-level replication (new repos only)

The statistic is KF's, verbatim:
- T0 = the event's first parent, scanned with engine `32619e4a5`, ablated history.
- Candidates are `.c` / `.h` files; the rename-tracked join gives the positives.
- Mantel-Haenszel strata: event × LOC decile × evidence quartile.
- Fault types use KF's map: OSS-Fuzz crash type, or CWE when present.

| id | claim | supported iff |
|---|---|---|
| **KFR-H1** | `goto` raises the security-fix rate on unseen repos | RR(GOTO, all) one-sided lo > 1 |
| **KFR-H3** | `goto` ↔ lifetime faults replicates | RR(GOTO \| lifetime) / RR(GOTO \| bounds) one-sided lo > 1 |

## KF-L — localization to functions (all G1-passing repos: nDPI, openssl and the new ones)

- **Unit:** FREC's construction (`tools/frec_eval.py`). Candidates are the functions of touched C files at T0 (files
  with ≥ 2 functions). A function is positive if its span overlaps the fix's parent-side changed lines.
- **Exposure:** the function's span contains a `goto` line (or a `goto_statement` node, if G2 falls back).
- **Strata:** event × function-LOC quintile within the event.
- **Mantel-Haenszel rate ratio,** with the event bootstrap resampling within each fault type.

| id | claim | supported iff |
|---|---|---|
| **KFL-H1** | inside fixed files, **lifetime** fixes land in `goto`-containing functions | RR(goto-function \| lifetime) one-sided lo > 1 |
| **KFL-H2** | …and more so than bounds fixes | RR(goto-function \| lifetime) / RR(goto-function \| bounds) one-sided lo > 1 |

## Tests and headline

- 5,000 rounds, seed 2982. α = 0.01 / 4 one-sided across the four claims.
- Equivalence for ratios: the 90% CI inside [0.8, 1.25].
- **The goto ↔ lifetime link is replicated iff KFR-H3 is SUPPORTED.**
- **It is localized iff KFL-H1 is SUPPORTED** (KFL-H2 adds specificity at function grain).

## Priors

- KFR-H3 **uncertain**: curl did not show it.
- KFL-H1 **leaning supported**: if `goto fail` cleanup chains are the mechanism, the fix should land in the function
  that owns them.

---

## Results — 2026-11-06 (gates `kfr_gates.md`; scorer `86d58bd` committed before running; report `kfr.md`)

**Gates.**
- G1: libxml2, libexif, libtiff and libpng pass. **file fails** (tree-sitter recall 94.0%) and is excluded from KF-L.
- G2: PASS (99.8% / 99.9%).
- G3: PASS (lifetime 29, bounds 42).
- All 84 parent snapshots scanned, 0 failed.

### KF-R — file level, five unseen repos (78 events)

| claim | estimate | one-sided lo (α = 0.0025) | 90% CI | verdict |
|---|---:|---:|---|---|
| **KFR-H1** RR(`goto`), all security fixes | **2.80** | 1.12 | [1.58, 6.91] | **SUPPORTED** |
| **KFR-H3** RR(`goto` \| lifetime) / RR(`goto` \| bounds) | 0.54 | 0.02 | [0.10, 2.12] | **not supported (inconclusive)** |

Descriptive:
- RR(`goto` | lifetime) 2.06 vs RR(`goto` | bounds) 3.83. With 50 LOC bins: 1.82 / 2.07.
- Per repo, RR(`goto`): libxml2 3.34 (41 events), file 4.50 (24), libexif 0.00 (11), libtiff 0.56 (2).

### KF-L — function level (nDPI, openssl, libxml2, libtiff, libpng, libexif; 387 events: 50 lifetime, 140 bounds)

| claim | estimate | one-sided lo (α = 0.0025) | 90% CI | verdict |
|---|---:|---:|---|---|
| **KFL-H1** RR(goto-function \| lifetime) | 2.07 | 0.77 | [1.20, 3.36] | **not supported** |
| **KFL-H2** lifetime ratio / bounds ratio | 1.02 | 0.33 | [0.54, 1.81] | **not supported (inconclusive)** |

Per repo, lifetime vs bounds RR at function level: nDPI 1.51 / 2.89; openssl 4.32 / 0.90; libxml2 2.01 / 2.19.

### Headline

- **The `goto` ↔ lifetime-fault link does NOT replicate.** On unseen repos `goto` goes with bounds faults at least as
  much as with lifetime faults. KF-H3's 7× on nDPI + openssl rested on 26 lifetime events and does not travel. It
  looks like a small-sample, two-repo result (openssl's function-level 4.3 vs 0.9 is the only cell that carries it).
- **What does replicate is the general `goto` effect.** Files containing `goto` are where security fixes land more
  often, at equal size and evidence:

  | data | RR(`goto`) |
  |---|---:|
  | nDPI + openssl | 1.59 |
  | five unseen repos | **2.80** (lo 1.12) |

- **Localization is not shown at the registered α.** Within fixed files, lifetime fixes land in `goto`-containing
  functions about 2× as often as in same-size siblings (90% CI 1.2–3.4), but the one-sided bound at α = 0.0025 is 0.77.
  It is not specific to lifetime faults either (bounds is similar).

**Program standing on "keywords ↔ specific faults".**
- **Keyword → *security faults in general*: replicated.** `goto` (and function-like macros, KF-H2) mark security-prone
  C code beyond size, on seven repos.
- **Keyword → *a specific fault type*: not replicated.** The one candidate (`goto` → lifetime) failed on unseen data.
- The engine's dynamism signal is a **general security-risk marker**, not a fault-type fingerprint.
