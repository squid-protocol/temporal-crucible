# CMT-G and DC — is the engine's comment stream accurate, and do functions whose comments express danger at birth get more CVE fixes over their life? — registered 2026-11-06, before either ran

**Why.**
- GitGalaxy's `Prism.split_streams` separates every file into a code stream and a comment stream, AST-free, across
  50+ languages.
- INT-S found that *defensive code* at birth (guard keywords) neither predicts nor prevents later CVEs (rate ratio
  0.96).
- Its caveat: authors may express a sense of danger in **comments** instead ("caller must…", "assumes…", "not
  thread-safe").
- DC tests that, after a gate checks the comment stream itself.

## CMT-G — comment-stream gate (binding for DC)

- **Corpus:** the language-crucible export (`kw_scan`, `757545ba6fd6`), with the engine language per file from that
  scan.
- **Engine comment lines:** the lines that are non-blank in `Prism.split_positional_comment_stream(content, lang)`
  (engine `32619e4a5`, `LEXICAL_FAMILY_HEURISTICS` plus `LANGUAGE_DEFINITIONS`).
- **Reference:** lines spanned by any tree-sitter node whose type contains `comment`, using
  `tree_sitter_language_pack`, for languages whose grammar loads.
- **Metric:** line-level precision and recall per language, and pooled over languages with ≥ 200 reference comment
  lines.
- **Pass:** pooled precision and recall ≥ 0.90, **and** C and C++ each ≥ 0.90 (the DC repos). Otherwise DC stops.

## DC — danger comments at birth vs later CVE fixes

**Data.** INT-S's: curl, OpenSSL, nDPI and harfbuzz; functions born after the first snapshot with loc ≥ 3;
whole-life follow-up from birth to the first event, death or the end of labels; identity-resolved fix hits.

**A function's comments at birth.** At the birth snapshot's file version, the engine comment lines (CMT-G's) that
fall either:
- **inside** the function's tree-sitter span (matched by name); or
- in the **contiguous comment block directly above** its first line (at most one blank line between).

**Danger lexicon (fixed now; case-insensitive, word-bounded):** must not, must be, caller(s) must, caller is
responsible, assume / assumes / assumed / assuming / assumption(s), unsafe, not safe, not thread-safe,
thread-unsafe, careful(ly), beware, warning, danger(ous), untrusted, trust / trusted / trusts, validate / validated /
validates / validation, sanitiz…, overflow, underflow, bound(s), out of range, null-terminat…, do not,
never call / use / pass, undefined behaviour / behavior, race, reentran…, security, attacker, malicious, exploit…,
vulnerab…, XXX.

**Exposure.** Among functions with **≥ 1 comment line** at birth: **danger-commented** (≥ 1 lexicon match) vs
**commented without danger words**. Functions with no comments are excluded, so the contrast is about *what* the
comment says, not whether one exists.

**Strata.** INT-S's: repo × log₁₀ loc bin × file had a CVE fix before birth.

| id | claim | supported iff (α = 0.01/2; MH rate ratio of first-event rates; file-cluster bootstrap, 2,000) |
|---|---|---|
| **DC-H1** | danger-commented functions reach a CVE fix at a higher rate ("the authors' words were right") | rate ratio > 1, lo > 1. Reversed if < 1, hi < 1 |
| **DC-H2** | …specifically CVEs | RR_latent ÷ RR_other-fix > 1, lo > 1 |

**Descriptive.**
- Danger-word prevalence.
- Per-repo RRs.
- Regression and extrinsic RRs.
- The most frequent matched words among CVE-hit functions.
- Commented vs uncommented functions (a separate contrast).

## Priors

- **CMT-G likely to pass** for C and C++ (the engine's golden-tested languages).
- **DC-H1 uncertain:** a direct test of "did the authors sense danger".
- **DC-H2 uncertain.**

**CMT-G amendment (2026-11-06, before any gate number).** Run 1 was stopped after 17 minutes at 100% CPU: one or more
huge crucible files, such as an amalgamation, ran too long in the comment splitter. Files now run in parallel with a
**60-second per-file limit**. Timed-out files are excluded and **listed in the gate report**. Nothing else changes.
**CMT-G amendment 2 (before any gate number).** The 60-second limit only stopped *waiting*: workers kept grinding on
pathological files and jammed the pool. Timing showed typical and very large files take well under 1 second. Each
file now runs in its own child process, **killed** after 60 seconds. Timed-out files are listed in the report.

## CMT-G result — 2026-11-06 (scorer `0a6f72f`; report `cmt_gate.md`): **FAIL as registered → DC stops**

| | precision | recall |
|---|---:|---:|
| pooled, 35 languages | 97.5% | **80.3%** (bar 90%) |
| **C** | 99.9% | 98.0% |
| **C++** | 100.0% | 99.4% |

**What fails.**
- **COBOL recall 27.6%** (16,643 engine vs 60,009 reference lines). It is the largest language in the pool, so it
  sinks the pooled recall.
- **Perl** precision 65%: likely POD or heredoc handling differs from tree-sitter.
- **Haskell** precision 24% and **SQL** 25%: small samples.
- **Ada** recall 73% and **PowerShell** 72%.
- Most other languages are 97–100%.

**Two engine findings for the owner.**
1. **14 COBOL copybooks (cobrix test copybooks) time out (> 60 s) in `Prism.split_positional_comment_stream`.** This
   is a performance pathology in COBOL comment splitting, in GitGalaxy's core market.
2. **COBOL comment recall vs tree-sitter-cobol is 27.6%.** This needs a definitional check before it is called an
   engine bug: tree-sitter's COBOL comment nodes may include the sequence area (columns 1–6) or the identification
   area (73–80), which the engine rightly does not treat as comments.

**DC did not run** (registered rule). The C and C++ split that DC would use is accurate (98–100%). A DC run would
need a new registration whose gate is scoped to the languages it uses.
