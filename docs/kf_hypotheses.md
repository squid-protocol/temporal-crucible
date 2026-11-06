# KF-H1..H4 — which construct carries the dynamism effect, and does each go with its own kind of fault? — registered 2026-11-06, before any construct-split or fault-type statistic

**Origin.**
- DYN-H2 (`cen_hypotheses.md`, DYN section) found that files with *any* dynamism get about 2× the security-fix
  touches at equal size and evidence: nDPI 2.03, openssl 2.33, robust to 50–100 LOC strata.
- "Dynamism" in C lumps two constructs together: function-like `#define` and `goto`.
- The engine's founding idea is that **specific keywords associate with specific faults**. This entry tests that
  directly, for the first time.

**What has been looked at.**
- The combined DYN result.
- Fault-type *counts* in the event files: nDPI OSS-Fuzz crash types; openssl CWE fields on 241 events.
- **Never computed:** per-construct exposure, or any construct × fault-type statistic.

## Data

- **Events and T0 snapshots** exactly as DYN:
  - nDPI: 121 security-fix events, frec DB (`32619e4a5`, ablated).
  - openssl: 252 events, dyncen DB (`32619e4a5`, ablated).
  - T0 = the event's first parent. A positive is a T0 file the fix touches (rename-tracked join).
- **Candidates:** T0 files ending `.c` / `.h`, so that the two constructs are counted from the same source.
- **Construct counts**, from the T0 tree (git):
  - **GOTO** = lines matching `\bgoto\b`;
  - **MACRO** = lines matching `^\s*#\s*define\s+[A-Za-z_]\w*\(`.
  - Exposure = count > 0, each construct separately. A file can be exposed to both.
- **Fault type per event:**

| type | nDPI (OSS-Fuzz crash type, the summary's prefix before " in ") | openssl (CWE field) |
|---|---|---|
| **bounds** | Heap-/Stack-/Global-/Dynamic-stack-buffer-overflow, Index-out-of-bounds, Negative-size-param, Container-overflow | CWE 119, 120, 121, 122, 123, 124, 125, 126, 127, 129, 130, 131, 170, 193, 786, 787, 788, 805, 806, 823, 1284 |
| **lifetime** | Memory leak, Heap-use-after-free, Use-after-free, Double-free, Use-of-uninitialized-value, Use-after-poison, Stack-use-after-return / -scope, Bad-free, Invalid-free | CWE 401, 404, 415, 416, 457, 459, 672, 763, 772, 824, 825, 908, 909, 911 |
| **other** | everything else (Segv on unknown address, UNKNOWN READ/WRITE, …) | everything else, or no CWE |

An event whose CWEs fall in both bounds and lifetime is excluded from H3/H4.

## Statistic

- **Mantel-Haenszel rate ratio**, exposed vs unexposed, with DYN-H2's strata: event × LOC decile × evidence quartile,
  edges per T0 snapshot, evidence = the pilot's `EVIDENCE_COLUMNS`.
- Events are pooled over **both repos**; strata nest within events.
- **Bootstrap:** 5,000 rounds over events, seed 2982. For H3/H4, resample within each fault type.

| id | claim | supported iff |
|---|---|---|
| **KF-H1** | GOTO alone carries the effect | RR(GOTO, all security fixes) one-sided lo > 1 |
| **KF-H2** | MACRO alone carries the effect | RR(MACRO, all security fixes) one-sided lo > 1 |
| **KF-H3** | `goto` goes with **lifetime** faults (cleanup paths: leaks, double free, use-after-free) | RR(GOTO, lifetime) / RR(GOTO, bounds) one-sided lo > 1 |
| **KF-H4** | function-like macros go with **bounds** faults (byte-access arithmetic) | RR(MACRO, bounds) / RR(MACRO, lifetime) one-sided lo > 1 |

- α = 0.01 / 4 one-sided.
- A fault type with < 20 pooled events makes H3/H4 not evaluable.
- Equivalence null for the H3/H4 ratios: the 90% CI inside [0.8, 1.25].

**Headline.** **"Keyword → specific fault" is shown** iff H3 or H4 is SUPPORTED. H1/H2 say which construct carries the
general effect.

**Descriptive.**
- Per-repo RRs.
- The 50-LOC-bin variant.
- curl as labelled context only: it carried the dynamism pilot, so it is never scored. Its CWE field supplies types.

## Priors

- H1 / H2 **uncertain** (both constructs plausible).
- H3 **leaning supported**: `goto fail` cleanup chains are where lifetime bugs live.
- H4 **uncertain**: macros are also used for feature flags and logging, not only byte access.
- Main risk: the lifetime type is small (nDPI about 15 events).
