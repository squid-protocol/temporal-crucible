# Blinding tools, build phase A — review

**Reviewer:** Claude Fable 5.2, 2026-11-14. **Built by:** Claude Opus from `docs/process/blinding_spec.md`
(Revision 2). **Reviewed:** `tools/blind/` and `tests/test_blind.py`, uncommitted.

**Verdict: accept with changes — and the main change is to the specification, not the build.** The encryption
and the jobs do what was asked. The scramble does what Revision 2 asked, and the review shows Revision 2 asked
for the wrong thing: any scramble that keeps directory hands over each directory's fix rate.

## What was checked, and the result

| check | how | result |
|---|---|---|
| The builder's tests | re-run | 59 passed, 3 expected failures (finding 1), 21 s |
| Encryption round trip | my own throwaway 2048-bit keys, the builder's `crypt.py` | decrypts to the same table; two encryptions of one table differ; a 1-row and a 40-row table give files of equal length |
| Tampering | one bit flipped in the ciphertext, the nonce, the wrapped key; the repo name changed; the fingerprint swapped | every one refused, each with a fixed message carrying no content |
| Wrong key | a second throwaway key | refused before any key operation |
| Fingerprint | of the committed public key, by the builder's code | begins `8b222bdc37b28697`, as recorded in `keys/README.md` |
| Label builder outputs | run with the committed public key on a control repository (308 files, 86 positives) | four files; the marginals and the cell report contain no path; the encrypted file contains no path in clear |
| Scrambled copies | the same run | 20 copies, each with 86 positives, no two alike, none equal to the truth, 0 true positives positive in all 20; overlap with the truth 36% (chance is 28%) |
| No plaintext path | read `crypt.py`, `build_labels.py`, `jobcore.py` in full | no code path writes a decrypted table; no decrypt command exists; errors print type names only |
| Private key untouched | searched the build for the key's path | only `~/…/blind_key.pem` in usage text. The file's access time is unchanged since the owner made it, which under this filesystem's settings is weak evidence, not proof |

## Findings

### 1. A scramble that keeps directory reveals each cell's fix rate — major, a fault in the specification

Permuting labels inside a cell keeps the cell's count of positives. Anyone holding one copy can read each
cell's fix rate. A cell with no positives is a list of files known to be negative. And the part of a
structural effect that lies between cells survives.

Measured on 16 control repositories with a strong planted effect (true effect +0.21 to +0.24), 20 copies each:

| cells | effect on scrambled labels, as a share of the true one | files in cells with no positives | true positives positive in all 20 copies |
|---|---|---|---|
| first version: band × full directory | 38–45% | 30–42% | 30–34% |
| Revision 2: cells of at least 8 files | 2–4% on average; the builder measured up to 16% in one repository | 2–5% | 0% |
| band only | about 0% | 0–1% | 0% |

The control repository plants its effect file by file, with nothing at directory level. Real repositories
differ strongly by directory in both structure and fix rate, so there the between-cell part would be larger.
The builder's three expected failures are this: Revision 2's "under 10%" rule cannot be met at cells of 8,
because about (cells − bands) / (files − bands) of an effect survives, up to one eighth.

**Change (Revision 3 of the specification).** Scrambles released to sessions are permuted within the **size
band only**. Then the statement "any structural effect on scrambled labels is false by construction" is true.
A directory-preserving scramble is still useful to measure how much a null result varies when files cluster,
but it is computed and used only inside the owner-run gates job, in memory, and only its declared summary is
written.

### 2. The seal covers `tools/blind/` but not what a scorer imports — minor, for the next phase

Fine for the reference scorer. When SA3's scorer is registered, every module it loads must be in the seal
(`research_codebase_spec.md`, section 5).

### 3. Run-once is enforced by files a session can delete — minor, known

The ledger and the result sit in the study directory. The specification's "Open" section already says this is
a deterrent. Cheap improvement: the job prints one line (seal hash, time, result hash) for the owner to keep
somewhere else.

### 4. Output files are written in place — minor

A crash mid-write leaves a partial file. Write to a temporary name in the same directory and rename.

### The builder's objections to the specification

| objection | reviewer |
|---|---|
| The `openssl` command line cannot do AES-GCM | Agree; using the installed `cryptography` package is the right call and adds no dependency |
| The 10% rule and cells of 8 are inconsistent | Agree; finding 1 goes further |
| Rules 2 and 4 are ambiguous; rule 4's merges can be detected across copies; rule 5's exact number would identify files | Agree; with band-only release they no longer apply to anything released |
| "Largest commit's share" undefined | The builder's definition is adopted: that commit's positive files over all positive files |

## What this review did not do

It did not run the two jobs end to end with its own harness; it read the job code and relied on the builder's
tests for the seal, the one-run rule, the guard and the dry run. It did not test the owner's terminal prompt
with a real key, by design.

## Re-review after the builder's changes (same day)

The builder made all seven changes and disputed none. Re-checked with the reviewer's own scripts.

| check | result |
|---|---|
| Tests | 62 passed, no expected failures (run together with the control repository's 40: 102 passed, 151 s) |
| Released copies are band-only | on a 945-file control repository with a planted effect: the count of positives in each size band is identical in all 20 copies and in the truth; the per-directory counts differ in every copy |
| Leak | 0 of 259 true positives positive in all copies; overlap with the truth 28.9% against a prevalence of 27.4% |
| Effect on scrambled labels | −0.0004 (sd 0.025 over copies) against a true +0.213: −0.2% |
| Outputs | four files, written under temporary names and renamed; marginals and report contain no path; the report no longer carries any label-derived count |
| Label builder | no option and no import of the directory-preserving cells |
| Encryption | unchanged: round trip and tamper refusal re-run with a fresh throwaway key |

**Accepted.** Noted by the builder and agreed: at about 300 files a minimum cell of 20 leaves no directory in
the directory-preserving scramble either, so the gates job's "spread with clustering" differs from the
band-only spread only in repositories of roughly 600 files or more.
