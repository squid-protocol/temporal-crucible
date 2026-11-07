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

---

## DC-2 — registered 2026-11-06 (owner approved), after CMT-G failed and before any DC outcome was computed

- **Gate scope:** **C and C++ only.** These are the only languages DC's four repos use. CMT-G's measured C (P 99.9%,
  R 98.0%) and C++ (P 100%, R 99.4%) pass the 90% bar. CMT-G's pooled failure (COBOL) is recorded above and stands.
- **Everything else is DC's registration verbatim:** lexicon, exposure, strata, claims DC-H1 / DC-H2, α, bootstrap.
- This is a new registration, made because the original gate covered languages DC does not use. No DC statistic
  had been computed.

### Correction: both COBOL "engine findings" are reference-grammar artefacts (2026-11-06; `tools/exploratory/cmt_cobol_*.py`)

1. **The 14 timeouts are tree-sitter-cobol, not GitGalaxy.** On `cobrix/test1_copybook.cob` (36 lines), the engine's
   `split_positional_comment_stream` and `split_streams` finish instantly. tree-sitter-cobol's parse is still running
   after 30 seconds.
2. **The COBOL "recall" gap is the reference over-counting.**
   - Across 40 COBOL files, the engine's comment lines are a subset of tree-sitter's (precision 99.6%).
   - Of the 22,915 lines tree-sitter marks as comment that the engine does not, **22,835 (≈100%) are ordinary
     code/data lines**, all with a blank column-7 indicator.
   - 47 are `PROCESS`/`CBL` compiler directives, 19 are identification-division comment-entry headers, and 14 have
     text in columns 73–80.
   - The engine follows the COBOL rule (comments are `*` or `/` in column 7). tree-sitter-cobol misparses.

**So CMT-G's COBOL row measures the reference, not the engine.**
- With COBOL excluded as an invalid reference, pooled precision and recall over the remaining languages are well
  above 90%.
- The registered verdict (FAIL) stands as recorded.
- **No GitGalaxy issue is warranted.** The only possible engine nuance: COBOL comment-entries (`AUTHOR`,
  `DATE-WRITTEN` … text), which standard COBOL ignores, are counted as code. That is too small (19 headers) to file
  without a dedicated check.
- The other non-COBOL gaps (Perl POD, Haskell/SQL precision, Ada/PowerShell recall) are unverified in the same way.

## DC-2 results — 2026-11-06 (scorer `1fcbed0`; report `dc.md`)

**Data.** 43,233 births with comment information. 18,816 had ≥ 1 comment line at birth; 2,182 of those (12%) had
danger language.

| claim | result | verdict |
|---|---|---|
| **DC-H1** danger-commented vs plain-commented → whole-life first-CVE rate | **1.45** [1.08, 1.89]; first-CVE events 144 / 523. curl 1.29, OpenSSL 1.59, nDPI 1.59, harfbuzz 1.81 | **SUPPORTED**: the authors' words were right |
| **DC-H2** CVE-specific (÷ other-fix) | 1.30 (lo 0.95); other-fix 1.12 | **not supported** (narrowly) |

**Descriptive.**
- Regression 1.01; extrinsic 1.20.
- Commented vs uncommented functions: 1.08.
- Most frequent danger words in CVE-hit functions: *must be* 39, *do not* 28, *security* 17, *assume* 16,
  *trusted* 13, *must not* 12, *warning* 12, *overflow* 10, *validation* 10, *XXX* 6.

**Reading.**
- **When authors *write down* that a function is dangerous, they are right.** Functions whose comments at birth use
  danger language reach their first CVE fix about 1.45× as fast as size- and history-matched functions with ordinary
  comments, in every repo.
- **The contrast with INT-S is the finding.** Defensive *code* at birth (guard keywords) did not predict CVEs (0.96).
  Defensive *words* do. Authors' sense of danger shows in what they say, not in how many checks they write.
- **Not proven CVE-specific.** Danger-commented functions also get somewhat more ordinary fixes (1.12). The CVE
  excess (1.30×) has a lower bound just under 1.
  - Read: these are trickier functions overall, with security risk the strongest part.
  - Regressions show nothing (1.01).
- **Product angle:** "danger comments" are a cheap, cross-language, history-free risk marker, available at the
  moment code is written. That is useful where no fix history exists, such as new code and legacy estates without
  version control.
- **Caveats:** C/C++ repos only; a fixed English lexicon; association, not cause.

---

## CFIX and DC-R — registered 2026-11-06, before either ran

### CFIX: do CVE fixes add danger-language *comments*, and does that find silent patches?

**Units.** SILENT's fix commits: curl, OpenSSL, nDPI, harfbuzz; latent and other-fix; kept C/C++ files.

**Comment change of a commit.**
- For each kept file, take the engine comment lines (CMT-G's `split_positional_comment_stream`, C/C++ validated) of
  the parent and post-fix versions, whitespace-normalised, ≥ 3 characters.
- **Added comment lines** = post-fix lines not in the parent's set. **Removed** = the reverse.
- DC's danger lexicon is applied to the added lines.

**Features.**
- adds-comment (≥ 1 added line);
- adds-danger (≥ 1 lexicon match in added lines);
- log1p(added comment lines);
- log1p(danger matches added).

| id | claim | supported iff (α = 0.01/2) |
|---|---|---|
| **CF-H1** | CVE fixes add danger-language comments more than ordinary fixes | MH RR of adds-danger, latent vs other-fix, strata repo × patch-size bin (log₁₀ changed lines, 0.25): lo > 1 (2,000-round commit bootstrap) |
| **CF-H2** | comment changes improve silent-patch detection beyond location | WH's design: LORO, silent positives vs ordinary negatives. AUC(WHERE + comment features) − AUC(WHERE) > 0, paired commit bootstrap lo > 0 |

**Descriptive.** The same for comments that add without danger words; the top-10% enrichment of WHERE + comments.

### DC-R: danger comments replicated on unseen repos (git + tree-sitter only)

**Repos.** libxml2, libexif, `file`, libtiff, libpng: pool clones at their KF-R pool heads. Their CVE (security-fix)
labels come from `events/<repo>.json`.

**Reconstruction, no engine DBs.**
- **Quarterly snapshots:** the last first-parent commit before each quarter boundary, first to last.
- **Functions:** tree-sitter C `function_definition` (file, name, span) in `.c` files outside `test`/`fuzz`
  directories, with CHG's identity and move rule.
- **Loc:** span lines.
- **Comments at birth:** as DC, from the engine's C comment stream on the birth-snapshot file.
- **Lexicon, exposure, strata, whole-life MH rate ratio, file-cluster bootstrap:** as DC.
- **CVE hits:** CHG's tree-sitter fix mapping of each security-fix commit, resolved to identities.

| id | claim | supported iff |
|---|---|---|
| **DCR-H1** | danger-commented functions reach a CVE fix at a higher rate (replication of DC-H1) | rate ratio > 1, lo > 1 at α = 0.01; **not evaluable** if either side has < 15 first-CVE events |

**Descriptive.** Per-repo estimates, and DC + DC-R pooled (inverse-variance on log RR).

**Power caveat (fixed now).** These repos carry 84 security-fix commits in total, so DCR-H1 may be not evaluable.
That outcome will be reported as such, not as a failure to replicate.
