# DRP — do fix commits repay self-admitted debt less often than other commits? — registered 2026-11-11 (owner OK), on repos whose debt and fix labels have not been joined

**Why.**
- The exploratory debt study (`docs/debt_lifecycle_exploratory.md`, PR #147) found the pattern in all five core repos:
  fix commits removed TODO/FIXME/XXX/HACK comments at about half their share of commits. CVE fixes almost never did.
- The count there was item-level, with no interval, and it did not account for commit size. Security patches, and
  probably fixes in general, are smaller than other commits (Li and Paxson, CCS 2017).
- This registration tests the pattern on four repos where debt removals and fix labels have never been joined:
  libgit2, libxml2, postgres and redis. It tests it raw and within commit-size strata.

## Prior work

- **This program.** The exploratory study above (core repos only). CPF: debt density adds nothing to file-level fix
  prediction.
- **Maldonado, Abdalkareem, Shihab and Serebrenik, "An empirical study on the removal of self-admitted technical
  debt", ICSME 2017.** Reported (as cited by later work) that 74.4% of SATD was removed in five Java projects.
  "Removal" meant removing the comment.
- **Sierra, Shihab and Kamei, "A survey of self-admitted technical debt", JSS 2019.** Organises the field into
  detection, comprehension and repayment. A later paper summarises it as finding repayment the least studied.
- **Li and Paxson, "A Large-Scale Empirical Study of Security Patches", CCS 2017.** Security patches are smaller and
  more localized than other bug fixes. That is the size confound tested by DRP-S.
- **This study's difference:** which *kind* of commit repays debt, in C, at commit grain, raw and size-matched, on
  held-out repos. It **extends** the SATD-repayment work from "how much" to "by what kind of work".

The Maldonado and Sierra findings are second-hand (from later papers' summaries). The result doc either checks them
against the papers or keeps them labelled second-hand.

## Data

- **Repos:** libgit2, libxml2, postgres, redis. Their fix labels (`events/<repo>_xc.json` via `chg_eval.fix_events`)
  have never been joined to debt removals.
- **Commits (units):** every non-merge commit that changes ≥ 1 line in an in-scope C/C++ file. In scope means paths
  not under tests/, docs/, fuzz/, scripts/ or examples/, at any depth: `tools/debt_lifecycle.py`'s rule.
- **Exposure:** the commit is a fix (any class `fix_events` returns).
- **Outcome:** the commit **repays** debt. It removes ≥ 1 debt comment line, by `tools/debt_lifecycle.py`'s tracker
  (moves, rewordings and renames are not removals), from a file that still exists after the commit.
- **Commit size:** lines added + deleted in in-scope C/C++ files (`git log --numstat`).

## Claims (α = 0.01/2, one-sided; commit bootstrap 2,000 rounds within repo, seed 2982)

| id | claim | test | supported iff |
|---|---|---|---|
| **DRP-R** | fix commits repay debt less often than other commits | Mantel-Haenszel risk ratio, strata = repo | RR < 1 and the bootstrap upper bound (α = 0.005) < 1 |
| **DRP-S** | the same, beyond commit size | MH risk ratio, strata = repo × size bin (1–2, 3–8, 9–32, 33–128, 129–512, > 512 lines) | RR < 1 and upper bound < 1 |

- **Power:** ≥ 30 repaying fix commits pooled. Otherwise both claims are **underpowered**.
- **Reading:**
  - R supported, S not: fixes repay less debt only because they are small.
  - Both supported: fix work avoids debt beyond size.

## Descriptive (no verdicts)

- Per-repo RRs, raw and size-stratified.
- Repay rate by fix class (other-fix, regression, extrinsic, latent); libxml2 is the only repo with CVE labels.
- The share of repaying commits that repay ≥ 5 debt lines (bulk clean-ups).

## Priors

- **DRP-R, likely supported:** the pattern held in all five core repos.
- **DRP-S, uncertain.** Size could explain most of it. Clean-up commits that sweep many TODOs are large and are
  rarely fixes.

## Known limits

- Debt detection on diff lines is heuristic: block-comment lines without a leading `*` are missed.
- Fix labels come from commit-message rules. They mean different things in different repos, so the per-repo rows
  matter.
- Commits are not independent (authors, release cycles). The commit bootstrap within repo may understate
  uncertainty.
