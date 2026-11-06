# SEM — a semantic "fixed differently" patch check: does looking for the fix's *guard condition* rather than its exact lines repair the line check's blind spot without new errors? — registered 2026-11-06, before the instrument was run on any host state

**Why.** VZ-T's line-based check never erred when it decided on verbatim copies (1,229 / 1,229). But on its audited
disagreements it was wrong 7 / 20 times. Every error was an **independent fix**: zlib-ng guarded CVE-2022-37434 with
its own `if (len < state->head->extra_max)`, kept zlib's removed line, and so was called "unpatched".

**Design-bias note.** The instrument below was conceived **after seeing that example**. That example and VZ-T's first
audit sample (seed 2982) are therefore excluded from the claims. Scoring uses VZ-T's verbatim truth, plus a **fresh**
audit sample (seed 2983, disjoint from the first).

## Instrument (fixed now)

**Guard fragments.** For each (fix, file), from the fix's added code lines (VZ-T's A set):
1. **Tokenise:** identifiers, numbers and multi-character operators as single tokens.
2. **Drop** all `(` `)` tokens and the keywords `if`, `while`, `for`, `return`; map `Z_NULL` → `NULL`.
3. **Split** the token list at `&&`, `||`, `{`, `}`, `;`, `?`, `:`, `,`.
4. **Keep** each piece that contains a comparison operator (`<` `>` `<=` `>=` `==` `!=`) and has ≥ 3 tokens.

**Presence.** A fragment is present if its token sequence occurs contiguously in the host file's token stream after
the same normalisation (steps 1–2).

**SEM verdict.** The first rule that fires:
1. **patched** if ≥ 50% of the (fix, file)'s guard fragments are present (and there is ≥ 1 fragment);
2. otherwise VZ-T's **line verdict**: patched / unpatched / undetermined.

So SEM can only *add* "patched" calls where the line rule said unpatched or undetermined. It can never add an
"unpatched" call.

## Claims (VZ-T's units, hosts and truth; α = 0.01/3)

| id | claim | supported iff |
|---|---|---|
| **SEM-H1** | **no new errors on known truth** | on VZ-T's verbatim units (1,552), SEM's wrong calls ≤ 1%, Wilson 99% upper bound ≤ 2% |
| **SEM-H2** | it meets the bars VZ-T missed | sensitivity on verbatim-unpatched ≥ 90% **and** specificity on verbatim-patched ≥ 90%, each Wilson lo ≥ 75% |
| **SEM-H3** | it repairs "fixed differently" **out of sample** | on a fresh seeded sample of 20 non-verbatim code-vs-version disagreements (seed 2983, excluding VZ-T's 20), hand-audited before SEM's verdicts are looked at: SEM correct > line check correct |

**Audit protocol (H3).**
- The 20 fresh units are drawn and audited by reading code and commits.
- Each unit's truth (patched / unpatched / unclear) is recorded **before** the SEM column is computed for them.
- Unclear units are excluded.

**Descriptive.**
- SEM vs line on VZ-T's first audit sample (in-sample, for transparency).
- Which CVEs yield guard fragments.
- SEM's change to the abstention rate.

## Priors

- **H1 likely.** Guard fragments come from fixed code, and pre-fix copies lack them.
- **H2 unlikely.** SEM cannot fix abstentions on unpatched copies, and sensitivity was 81.5%.
- **H3 uncertain.** It works only where the independent fix reuses the guard expression.

**H3 audit recorded (2026-11-06, before SEM ran on any unit).**
- 20 fresh units (seed 2983), audited on the vulnerability's semantics. Aggregate: **20 patched, 0 unpatched,
  0 unclear.**
- The labels sit in the private file `vz_private/sem_audit.json`, sha256 `fbecbeb5dcc3c3c1c0e01cecb6e69953715f19661872ccad860321594b9173f8`.

---

## SEM-1 results — 2026-11-06 (scorer `934a639`; report `sem.md`)

| claim | result | verdict |
|---|---|---|
| **SEM-H1** no new errors on verbatim truth | **227 wrong calls** / 1,552 (line check: 0) | **not supported** |
| **SEM-H2** meets VZ-T bars | sensitivity 64.4%, specificity 91.1% | **not supported** |
| **SEM-H3** beats the line check on the fresh audit | 17 / 20 vs 12 / 20 | **SUPPORTED** |

**Why H1 failed** (exploratory breakdown, `tools/exploratory/sem_error_breakdown.py`, after scoring):
- **All 227 errors** call a *verbatim-unpatched* copy "patched". 114 are CVE-2022-37434 and 113 are CVE-2016-9842.
- **The cause:** guard fragments that are **not new**. The CVE-2022 follow-up fix re-adds `state->head->extra != NULL`,
  and the CVE-2016-9842 fix keeps the context `strm == NULL` / `strm->state == NULL`. Both already exist in
  pre-fix code.
- This is the most dangerous error type: vulnerable code reported as fixed.
- **SEM-1 must not be used.**

## SEM-2 — registered 2026-11-06, before SEM-2 ran on any unit

**One change to the instrument:** a guard fragment is kept only if its token sequence does **not** occur in the
fix's *pre-fix function body* (the query side, normalised the same way). Everything else is as SEM-1.

**Claims SEM2-H1..H3:** as SEM-H1..H3. H3 uses a **third** fresh sample:
- seed 2984;
- disjoint from the seed 2982 and 2983 samples;
- audited and hash-locked before SEM-2 runs.

**Prior:** H1 likely now. H3 uncertain: removing fragments may also remove zlib-ng's `len < extra_max`. It should
not, because that fragment is new in the fix.
