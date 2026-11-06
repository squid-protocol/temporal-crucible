# TGT-H1..H3 — does the *named* platform's conditional density find the files its fix touches? — registered 2026-11-06, before any per-platform statistic

**Why.** ENV and SC showed that platform/compiler conditional density, taken over *all* platforms, finds files that get
extrinsic fixes. A practical question ("we want to support version X of system Y: which files?") needs the
**targeted** form. This tests it.

**What has been seen.**
- These XC extrinsic labels (curl, nDPI, openssl, harfbuzz, libarchive), their audit samples, and the generic measure's
  results.
- **Never computed:** any per-platform-family density, or any within-commit file ranking.

## Unit

- **Commits.** Every labelled extrinsic commit (`events/{repo}_xc.json`, rules v2) whose **subject** names **exactly
  one** platform family below. Commits naming two or more families are excluded.
- **Candidates.** The C/C++ files (repo extensions as in ENV) present in the commit's **first parent** tree.
- **Positive.** A candidate the commit modifies (path present in the parent and in the commit's `c_files`). Files the
  commit creates are not candidates.
- A commit counts only with ≥ 1 positive and ≥ 1 negative candidate.

## Platform families

| family | subject names (case-insensitive) | macros (in `#if/#ifdef/#ifndef/#elif` lines) |
|---|---|---|
| **windows** | windows, win32, win64, wince, mingw, cygwin, msys, msvc, visual studio, uwp | `_WIN32 WIN32 _WIN64 _WIN32_WINNT _WIN32_WCE _MSC_VER __MINGW32__ __MINGW64__ __CYGWIN__ WINAPI_FAMILY` |
| **apple** | macos, mac os, osx, darwin, apple, ios, xcode | `__APPLE__ __MACH__ TARGET_OS_*` |
| **bsd** | freebsd, netbsd, openbsd, dragonfly | `__FreeBSD__ __NetBSD__ __OpenBSD__ __DragonFly__` |
| **solaris** | solaris, illumos, sunos | `__sun __sun__ __SVR4` |
| **aix** | aix | `_AIX` |
| **hpux** | hp-ux, hpux | `__hpux` |
| **vms** | vms, openvms | `__VMS` |
| **android** | android | `__ANDROID__` |
| **gcc** | gcc | `__GNUC__ __GNUC_MINOR__` |
| **clang** | clang | `__clang__ __clang_major__` |

Subject names match on word boundaries.

## Scores (per candidate file, from the parent tree)

- **S_F**: conditional lines naming any macro of the commit's family F, ÷ the file's line count.
- **S_P**: the generic measure. Conditional lines matching ENV's registered `PATTERNS["P"]`, ÷ lines.
- **S_G**: the same as S_F for each **other** family G with ≥ 1 commit in the pool.
- **size**: line count.

## Claims

Per commit, compute AUCs over its candidates (ties ½).

| id | claim | per-commit quantity | supported iff |
|---|---|---|---|
| **TGT-H1** | the named platform beats the generic measure | AUC(S_F) − AUC(S_P) | mean > 0, one-sided lo > 0 |
| **TGT-H2** | the named platform beats size | AUC(S_F) − AUC(size) | mean > 0, lo > 0 |
| **TGT-H3** | it is the *right* platform (placebo) | AUC(S_F) − mean over G ≠ F of AUC(S_G) | mean > 0, lo > 0 |

**Tests.**
- Pooled over the five repos; commit bootstrap stratified by repo. 5,000 rounds, seed 2982. α = 0.01 / 3 one-sided.
- < 30 qualifying commits = not evaluable. Equivalence null: 90% CI inside [−0.02, +0.02].

**Headline.** **"Targeted is shown"** iff H2 and H3 are SUPPORTED, i.e. the right platform's macros beat both size and
the wrong platform's. H1 says whether targeting adds over the generic measure.

**Descriptive.**
- Per-repo and per-family means and counts.
- A "where would a reviewer look" figure: the share of commits whose touched files all sit in the top 10% of files by
  S_F.

## Priors

- H2 **leaning supported**; H3 **leaning supported**.
- H1 **uncertain**: the generic measure already concentrates on adapter files, and most platform commits are Windows,
  whose macros dominate S_P.

---

## Results — 2026-11-06 (scorer `3128096` committed before running; report `tgt.md`)

1,405 extrinsic commits named exactly one platform family; **1,396 qualify** (curl 477, openssl 385, libarchive 382,
harfbuzz 121, nDPI 31).

| claim | mean ΔAUC | lo | 90% CI | verdict |
|---|---:|---:|---|---|
| **TGT-H1** named platform − generic measure | −0.041 | −0.053 | [−0.048, −0.035] | **not supported** (generic is better) |
| **TGT-H2** named platform − size | −0.145 | −0.165 | [−0.157, −0.133] | **not supported** (size is better) |
| **TGT-H3** named platform − wrong platforms | **+0.131** | +0.115 | [+0.121, +0.140] | **SUPPORTED** |

**Headline (registered rule) → "targeted" is NOT shown.**
- **Platform specificity is real.** A Windows fix's files carry Windows conditionals far more than macOS or BSD ones
  (Windows +0.195; Apple, BSD and GCC +0.08 to +0.09; rare platforms such as Solaris, AIX, HP-UX and Android ≈ 0).
- **The named platform's density does not beat size, or the generic measure, at *which files one commit touches*.**
  Within a commit, the big core files that most multi-file changes touch rank first by size (AUC ≈ 0.80). Many touched
  files carry no conditional for the named platform at all.
- **Statistic differs from ENV/SC.** This used per-commit AUC, which rewards size. ENV/SC used effort-aware recall over
  future windows. The two answer different questions: "which files will absorb environment work, per line read" versus
  "which files will *this* platform change touch".

### Exploratory follow-up (not registered): a practical ranking

Tool `tools/exploratory/tgt_combined.py`; same 1,396 commits.

| ranking | mean AUC |
|---|---:|
| size alone | 0.798 |
| named platform's conditional density | 0.652 |
| files with *any* platform conditional first, then by size | 0.823 |
| **files with the *named* platform's conditional first, then by size** | **0.827** (Windows: 0.831 vs size 0.793) |

So for "we want to support system Y", the useful list is **files that already branch on Y (or on any platform) first,
largest first**. It is a modest gain over size (+0.03 AUC), and naming Y adds little beyond "any platform" (+0.004).
This would need its own registration before it is called shown.
