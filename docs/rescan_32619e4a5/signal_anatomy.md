# Signal anatomy — curl

Raw-signal layer vs CVE ground truth. Events analyzed: control 172, introduced 132, security-fix 185. Median event net-LOC: control +2, introduced +9, security-fix +3.

## 1 · The grammar of a security fix (signal deltas, fixes vs controls)

Per-signal mean delta over touched files, per event (median across events). One-sided MW in the direction the medians differ; sorted by p.

| signal | fixes Δ | controls Δ | introduced Δ | p (fix vs ctrl) |
|---|---|---|---|---|
| state_pointers | +0.33 | +0.00 | +2.20 | 0.0001 |
| struct_branch | +0.50 | +0.00 | +1.24 | 0.0002 |
| state_flux | +0.00 | +0.00 | +0.56 | 0.0118 |
| struct_args | +0.00 | +0.00 | +0.16 | 0.0201 |
| struct_func_start | +0.00 | +0.00 | +0.00 | 0.0325 |
| arch_events | +0.00 | +0.00 | +0.00 | 0.0361 |
| def_safety | +0.00 | +0.00 | +0.00 | 0.0383 |
| state_bailout_hits | +0.00 | +0.00 | +0.00 | 0.0409 |
| arch_regex | +0.00 | +0.00 | +0.00 | 0.0483 |
| def_doc | +0.00 | +0.00 | +0.00 | 0.0794 |
| state_fragile_debt | +0.00 | +0.00 | +0.00 | 0.0794 |
| arch_crypto | +0.00 | +0.00 | +0.00 | 0.0867 |
| state_unreferenced | +0.00 | +0.00 | +0.00 | 0.0882 |
| def_listeners | +0.00 | +0.00 | +0.00 | 0.1019 |
| struct_generics | +0.00 | +0.00 | +0.00 | 0.1046 |
| arch_dependency_injection | +0.00 | +0.00 | +0.00 | 0.1512 |
| def_test_skip | +0.00 | +0.00 | +0.00 | 0.1512 |
| state_danger | +0.00 | +0.00 | +0.00 | 0.1512 |
| struct_class_start | +0.00 | +0.00 | +0.00 | 0.1684 |
| arch_concurrency | +0.00 | +0.00 | +0.00 | 0.1689 |

## 1b · Signature prevalence (EXPLORATORY — descriptive shares, no p-values claimed; class-discrimination confirmatory tests belong to Phase M / repo #2)

Share of events whose touched files NET-added (or removed) each construct.

| construct | security-fix | control | introduced |
|---|---|---|---|
| +struct_branch | 58% | 34% | 67% |
| +state_pointers | 54% | 27% | 73% |
| +def_safety | 13% | 9% | 28% |
| +state_cast_hits | 3% | 6% | 27% |
| +state_memory_alloc | 3% | 2% | 26% |
| -state_pointers | 12% | 9% | 14% |
| -struct_branch | 11% | 11% | 17% |
| loose signature (branch+ or ptr+) | 70% | 41% | 77% |
| strict signature (branch+ and ptr+) | 42% | 20% | 63% |
| fix-shaped (branch/ptr+ WITHOUT new allocs/casts) | 64% | 34% | 40% |

Reading: no single feature is a fingerprint (71% of fixes add branch-or-ptr, but so do 45% of controls). The DIFFERENTIAL is the lead: introductions match fixes on branches/pointers but differ sharply on allocations and casts — 'pointer/branch-heavy WITHOUT new allocs/casts' is fix-shaped; the same WITH them is feature-shaped, which is where vulnerabilities are born. Multi-feature classification is the ML dataset's job, not a threshold's.

## 2 · Assumed vs observed — where CVE files stand per signal, before the event

Median pre-event percentile of implicated files per signal (ranked among all files in the parent snapshot), fix-class vs the control-file baseline. A large gap in either direction is a keyword whose risk association differs from the 'change happens in hot files' baseline; sorted by |gap|.

| signal | CVE-fix files | control files | gap |
|---|---|---|---|
| state_safety_neg | 80 | 0 | +80 |
| state_unreferenced | 68 | 47 | +21 |
| def_encapsulation | 92 | 83 | +9 |
| state_cast_hits | 87 | 78 | +9 |
| state_heat_triggers | 84 | 78 | +6 |
| struct_class_start | 94 | 89 | +6 |
| struct_func_start | 92 | 87 | +5 |
| arch_import | 94 | 89 | +5 |
| state_flux | 92 | 87 | +5 |
| struct_macros | 90 | 84 | +5 |
| struct_args | 92 | 87 | +5 |
| bitwise_ops | 84 | 80 | +5 |
| state_pointers | 95 | 90 | +5 |
| struct_branch | 92 | 88 | +4 |
| struct_var_decl | 93 | 88 | +4 |

## 3 · The vulnerable function — implicated vs same-file siblings (parent snapshot)

Functions overlapping a fix's changed lines (n=603) vs untouched siblings in the same files (n=11316):

| metric | implicated median | sibling median | p (sib < imp) |
|---|---|---|---|
| complexity | 13.00 | 4.00 | 0.0000 |
| z-score | 0.58 | -0.29 | 0.0000 |
| loc | 65.00 | 23.00 | 0.0000 |

If implicated functions stand out from their own file's siblings, the instrument localizes below file granularity — the sharpest claim rung 7 could make.

**Length-bias gate (loc-matched pairs, n=451, sibling within 0.66–1.5× loc in the same file):**

| metric | implicated median | matched sibling median | p (sib < imp) |
|---|---|---|---|
| complexity | 10.00 | 10.00 | 0.7633 |
| z-score | 0.14 | 0.24 | 0.8231 |
| loc (match check) | 51.00 | 50.00 | 0.4005 |

Pairwise: implicated more complex than its length-matched sibling in 191/451 pairs (55 ties). If the gate holds, complexity separates future-patched functions at equal length — a real below-file signal, not hunk-area bias.

### Phase D — the guard deficit (pre-registered)

guard rate = (def_safety + bailouts) / (pointers + danger + memory_alloc + casts + 1), function grain, parent snapshot, loc-matched pairs.

| metric | implicated | matched sibling | p (one-sided, registered direction) |
|---|---|---|---|
| guard rate (D-H1) | 0.000 | 0.000 | 0.2467 |
| danger load (control) | 20.0 | 17.0 | 0.0344 |
| guard-rate change after fix (D-H2) | +0.0000 (n=431) | +0.0000 (n=451) | 0.8685 |

**D-H1 (vulnerable = under-guarded relative to danger): not supported** · **D-H2 (the fix closes the deficit): not supported** (α=0.01, directions registered on gitgalaxy#2982 before this table was generated).

---
*Counts are the engine's own extraction (persisted per commit in file_data/function_data); no diff-text keyword matching involved. Regenerate: `python tools/signal_anatomy.py --events events/curl.json`.*
