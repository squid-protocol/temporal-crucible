# UT — unpatched twins: does structural twin search find forks' copies of OpenSSL's CVE-fixed functions, and are they still unpatched? — registered 2026-11-06, before any fork scan or twin search

**Why.** CVE fixes recur in place (KF-R, SRCH), and copied code carries its flaws with it. If the engine's structural
twin search (`sfs`, SFS-H1 99%) can find a CVE-fixed function's **copies in other code bases**, and tell whether each
copy still has the pre-fix code, that is a supply-chain capability: "this vendored or forked function is a twin of one
that was patched, and the patch is absent".

**Test bed.** OpenSSL and its two 2014 forks, which copied OpenSSL and have patched independently since:
- **BoringSSL**: `google/boringssl` @ `e375adcf13f8`, 2026-11-06; first commit 2014-06-20.
- **LibreSSL**: `libressl/openbsd` @ `a22aeee114ad`, 2026-11-04; `src/lib/libcrypto` and `src/lib/libssl`; forked
  2014-04.

## ⚠ Disclosure rule (binding, because this repository is public)

A confirmed unpatched copy in a fork's current head could be a **live vulnerability**.
- **Public files** (this doc, the report, the PR) give **aggregate counts only**: no function names, files or CVE
  identifiers for audited-unpatched cases.
- The specifics go to a **private local file** outside the repo, and to the owner.
- The owner decides any disclosure; no outreach (standing rule).

## Data

- **CVE fixes:** OpenSSL's `latent` class (`events/openssl_xc.json`, rules v2), dated on or after **2014-06-20**:
  192 fix commits.
- Each fix maps to the functions it changes as in CHG: tree-sitter at the parent, `-U0` hunks.
- For each changed function, from the hunks anchored inside it:
  - **R** = its removed lines;
  - **A** = its added lines.
  - Both are whitespace-normalised. Only non-trivial lines count: ≥ 10 characters and containing a letter.
- **Query (pre-fix OpenSSL):** the latest OpenSSL quarterly snapshot before each fix (CHG's DB, engine `da852aa54`),
  restricted to `crypto/`, `ssl/` and `include/`.
  - That snapshot holds the pre-fix version unless the function also changed in between; such cases fall to the
    "diverged" status below.
- **Targets:**
  - each fork's head, scanned with the **same engine binary and arguments** (`galaxyscope-tc` `da852aa54`,
    `--spec-alignment`, git history off);
  - BoringSSL `crypto/`, `ssl/`, `decrepit/`, `include/`; LibreSSL `src/lib/libcrypto`, `src/lib/libssl`.
  - The 32 `sfs` signals are static text counts, so history mode does not enter them.
- **Twin search:** `sfs` `search` + `accept` with its default parameters (min loc 6, ratio 0.8, FDR 0.01,
  target-decoy calibrated), one search per (pre-fix snapshot, fork). Structure only: **no names, no text**.
- **Name baseline:** fork functions with the same name.

## Instruments

- **Textual copy:** token Jaccard (identifiers, numbers, operators) between the pre-fix OpenSSL function and the fork
  function ≥ 0.5.
- **Patch status of a fork counterpart.** Shares of R and A lines present in its body:

| status | rule |
|---|---|
| **patched** | ≥ 50% of A present |
| **unpatched-looking** | ≥ 50% of R present, < 50% of A present, R non-empty |
| **fix absent (addition-only)** | R empty, < 50% of A present (weak: the fork may guard elsewhere) |
| **diverged** | otherwise |

## Claims

| id | claim | supported iff |
|---|---|---|
| **UT-H1** | structural twins of CVE-fixed functions are **real copies** | among CVE-fixed functions with an accepted twin in a fork (both forks pooled), the share whose twin is a textual copy is ≥ 80%, with Wilson 99% lower bound ≥ 60%. Not evaluable if < 30 such twins |
| **UT-H2** | twin search finds copies **name matching misses** | ≥ 1 accepted twin that is a textual copy under a different name (reported as a count) |
| **UT-H3** | it finds **unpatched copies** | ≥ 1 *unpatched-looking* twin confirmed by manual audit: the fork's current code contains the flawed logic the OpenSSL fix removed, and no equivalent guard elsewhere in the function |

**H3 audit.**
- All unpatched-looking twins, capped at 25 by a seeded sample.
- Each is read against the OpenSSL fix diff and labelled one of:
  - **confirmed-unpatched**;
  - **fixed differently**;
  - **not applicable** (code path absent or unreachable in the fork);
  - **unclear**.

**Descriptive.**
- Twin recall on name-identified copies (same name, Jaccard ≥ 0.5).
- Patch-status mix for twins and for name matches, per fork.

## Priors

- **H1 likely supported:** SFS-H1 twins are highly precise.
- **H2 uncertain:** forks mostly keep OpenSSL names; BoringSSL renamed some.
- **H3 expected null or near-null:** both forks track OpenSSL advisories closely, and LibreSSL and BoringSSL removed
  a lot of code. An "unpatched-looking" twin will mostly turn out "fixed differently" or "not applicable". A
  confirmed case would be significant and is handled under the disclosure rule.

---

## Results — 2026-11-06 (scorer `26bd206` committed before running; report `ut.md`; aggregates only, per the disclosure rule)

**Data.** 192 post-fork OpenSSL CVE fixes → 780 (fix, function, fork) rows. 567 rows have no counterpart in the fork
by either name or twin: the code was removed, or never present.

| claim | result | verdict |
|---|---|---|
| **UT-H1** twins are real copies | only **21** accepted twins; 13 are textual copies (61.9%, Wilson lo 35%) | **not evaluable** (< 30) |
| **UT-H2** renamed copies found | **0** | **not supported** |
| **UT-H3** audited-unpatched copies | 4 unpatched-looking twins, all audited: **0 confirmed-unpatched**; 1 fixed (same core change); 1 fixed differently; 1 not applicable (API refactor); 1 unclear (referred to the owner privately) | **not supported** |

**The headline is recall: the coarse L1 fingerprint finds few copies.**
- Of the 104 copies that name matching finds (same name, Jaccard ≥ 0.5), twin search retrieves the same function
  only **12.5%** of the time.
- In **BoringSSL** it finds **none**: its C++ rewrite changes the signal profile.
- Every twin that is a real copy keeps its OpenSSL name. Here name matching is strictly better.
- This settles the question the layered-fingerprint discussion left open: **L1 is too coarse for copy-finding.**
  Behaviour and shape layers (calls, constants, control flow) are needed. The next step is a registered benchmark
  on these same pairs.

**Instrument lessons, for the follow-up.**
- The line-presence status rule was fooled by comment and assert lines in fixes. The follow-up needs code-only lines.
- The `latent` label covers whole commits, including refactor hunks unrelated to the flaw: one audited case.
- Name-matched LibreSSL copies show 17 "unpatched-looking". Given the 0-of-4 audit, that count is mostly instrument
  noise and **not a finding**.
