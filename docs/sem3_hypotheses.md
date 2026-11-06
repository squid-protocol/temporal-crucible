# SEM-3 — does requiring a fix's lines to be *new to the whole file* repair the code-reading check on refactoring fixes (expat) without losing zlib? — registered 2026-11-06, before SEM-3 ran on any unit

**Why.** In CMB, the code-reading checks wrongly called about 25% of old, verbatim expat copies "patched": 683 of
687 SEM-2 errors were false "patched". Blind-audited modified copies split by library: zlib 30/30 for SEM-2 against
0/30 for closest-version (CV); expat 1/26 against 25/26.

The diagnosed mechanism: expat's fixes are refactoring pull requests whose "added" lines already exist elsewhere in
older files, and whose "removed" lines reappear elsewhere after the fix (moved code).

## Instrument SEM-3 (fixed now). For each (fix, file)

- **A\*** = the fix's added code lines (VZ-T rules: normalised, ≥ 10 characters, a letter, not a comment) that do
  **not** occur anywhere in the whole **pre-fix file**.
- **R\*** = its removed code lines that do **not** occur anywhere in the whole **post-fix file**.
- **F\*** = guard fragments (SEM rules) from the added lines that do **not** occur in the whole pre-fix file's token
  stream.

**Verdict.** The first rule that fires:
1. **patched** if F\* is non-empty and ≥ 50% of F\* is present in the host file;
2. **patched** if A\* is non-empty and ≥ 50% of A\* is present;
3. **unpatched** if R\* is non-empty and ≥ 50% of R\* is present;
4. otherwise **undetermined**.

For multi-PR expat items, the per-PR sets are unioned; "pre-fix" and "post-fix" are per PR.

## Claims (CMB's units, truth and comparators; α = 0.01/2)

| id | claim | supported iff |
|---|---|---|
| **S3-H1** | no new errors on verbatim truth, **in each library** | zlib and expat each: SEM-3 wrong calls ≤ 1% of decided verbatim units, Wilson 99% upper ≤ 2% |
| **S3-H2** | SEM-3 beats closest-version on modified copies (blind) | fresh sample (seed 2986) of non-verbatim units where SEM-3 and CV both decide and disagree. Up to 30 per library; **excludes every unit in earlier audit samples**. Labelled by fresh agents (same packet format and blindness as CMB, fixed excerpts), hash-locked before comparison. Pooled: SEM-3 right > CV right, exact sign test p < α (≥ 10 labelled) |

**Descriptive.**
- Per library: coverage, verbatim wrong calls, and the blind split.
- SEM-3 vs SEM-2 on CMB's audited units (in-sample).
- The follow-up-fix definitional sensitivity, as in CMB.

## Priors

- **S3-H1 zlib likely.** zlib's fixes are surgical, so A\* ≈ A.
- **S3-H1 expat uncertain.** Some refactors also add genuinely new boilerplate lines.
- **S3-H2 uncertain.** It depends on whether expat units still decide after filtering, and decide correctly.
