# LAWS Amendment 6 — PROPOSAL (not filed): adopt FIXLIKE v3c as the fix-class rule

**Drafted 2026-11-11. NOT YET IN THE REGISTER.** Amendments in `docs/laws_hypotheses.md` carry owner OK
by convention (Amendments 1, 2 and 3 each say so), so this is a draft for the owner to file, not a
change made on its own authority. To take effect without a rescan it must be filed **before the panel
draw** — Amendment 1 item 2 requires a full rescan for any change landing after it.

## Why this is needed, specifically for LAWS

LAWS takes its fix classes from **`tools/xc_harvest.py`** (registration line 49) — the exact gate
`docs/otherfix_audit.md` has now measured — and sets a **class gate: a class whose label precision is
< 70% in a language is descriptive-only there** (line 53).

Measured precision of the residual `other-fix` class under the registered v1 gate, 440 hand judgments
over three rounds:

| | v1 gate | FIXLIKE v3c |
|---|---|---|
| pooled | 0.558 | **0.761** |
| C | 0.733 | **0.750** |
| non-C (Go, Java, Python, Rust) | **0.383** | **0.773** |
| repos over the 0.70 gate | 3 of 8 | **7 of 8** |

`other-fix` carries **85–97% of fix-event mass in every repo**. So under the registered gate and the
registered class rule, `other-fix` would fall below 0.70 in Go, Java, Python and Rust, and **LAW-6,
LAW-7 and LAW-8 would be descriptive-only across most of the panel** — the three laws Amendment 0 item
2 explicitly kept confirmatory. The cause is community vocabulary, not a coding error: outside C,
"fix" largely introduces lint, mypy, javadoc, formatting and typo changes.

## What is proposed

1. **Adopt FIXLIKE v3c** (`tools/fixlike_v2.py --rules v3c`) as the class rule, applied **to
   `other-fix` only** — the class it was developed and audited on. `latent` (OSV-derived),
   `regression` and `extrinsic` keep their own measured precision from `docs/xc_label_audit.md`
   (0.73–0.87 and 0.90–1.00). Two of them must not be touched by these rules in any case:
   `regression` via revert reaches its class *before* the fix-like gate, so rule C would discard
   `Revert "..."` commits; `extrinsic` is already gated on a subject-matched environment *and* action,
   so rule C would drop legitimate entries like "port to AIX" that carry no fix word.
2. **The decisive rule is rule C: require the fix word in the commit SUBJECT.** v1 matched subject *or
   body*, so plain feature commits whose body said "fixes #123" were admitted. Path and prose
   exclusions alone reached only 0.660 pooled and still failed 5 of 8 repos. Rule C was designed on a
   240-commit development set and tested on a later 200-commit sample, so 0.761 is out-of-sample.
3. **Cost:** 43.0% of `other-fix` events dropped, which is roughly **22% of real fixes to remove
   roughly 69% of the noise**. Non-destructive: v3c sets are written to `events/<repo>_xc2.json` and
   v1 sets are untouched, so every published v1 result stays reproducible.
4. **v3c is the starting rule, not a substitute for the M6 audit.** The audit covers C, Go, Java,
   Python and Rust — **5 of the 10 candidate languages**. PHP, C#, Kotlin, C++ and JS/TS are
   unaudited. M6's per-language audit and the class gate still decide; this amendment only changes
   which rule that audit is run against.

## Explicitly NOT proposed

- **No change to the frozen scorer** (Amendment 5 item 8, 2026-11-11). In particular the oracle-ladder
  ceiling estimator from `docs/ceil.md` is **not** added to LAWS: **LAW-8 already measures the right
  thing** (forward, effort-aware gain in recall@20% LOC), and a new estimator after the freeze would
  cost a full rescan for marginal gain. CEIL stands as a companion result, cited rather than merged.
- **No change to the controls.** LAWS already registers distinct authors and change coupling
  (registration lines 68–69). CEIL independently confirms that was the right call — author count came
  out the **strongest single term** in the re-fit model (OR 2.06 [1.92, 2.22]), ahead of prior fixes,
  and adding it moved prior fix 2.10 → 1.65 and churn 1.22 → 1.10.
- **No change to panel size or the draw.**

## Caveats the owner should weigh

- **libgit2 fails all three audit rounds** (0.63 / 0.60 / 0.60) on build-and-warning churn that reads
  exactly like a bug fix. LAWS's class gate is **per language**, not per repo, so one bad C repo may
  not trip it while still adding noise. Worth deciding whether the gate should also apply per repo.
- Several libgit2 misses are cheap regex gaps (bare `Fix warnings`, plural `broken tests`,
  `misspelling`, `linting`, `Javadocs`, `PEP8`), deliberately left unfixed so as not to overfit the
  round-3 test set. They are candidate amendment 3 to `xc_harvest`, pending a fresh round-4 sample.
- The development set predicted 0.932 and the confirmatory sample gave 0.761, so the tuned figure was
  optimistic by ~0.17. **Quote 0.761.**

## Evidence

`docs/otherfix_audit.md` (both rounds, all 440 verdicts listed), `docs/fixlike_v2_impact.md`,
`tools/fixlike_v2.py`, `tools/otherfix_sample.py`, journal
`docs/journal/2026-11-11-otherfix-precision.md`. Companion ceiling work: `docs/ceil.md`,
`docs/journal/2026-11-11-error-prediction-ceiling.md`.
