# CGT — how do call networks change over a codebase's life, and what changes them? — registered 2026-11-08, before any call-network statistic, commit scan or scorer

**Why.**
- WIRE (2026-11-08, supported H3): a COBOL program's paragraph call network survives translation and identifies the
  port's source where whole-program fingerprints cannot. DOOM (exploratory): wiring separates designs that were kept
  from redesigns. Both suggest the call network is the *design* layer of a codebase.
- Owner's hypothesis (2026-11-08): call networks stay static over time and change in big jumps as features come
  online. What else do the jumps coincide with, and do fixes (CVEs, regressions) change the call graph?
- Earlier programme results that set the priors: keyword-mix drift comes in spurts at architecture events (SIG-H2:
  top 10% of quarters carry 45–89%); 71% of functions never change shape (LAT); CVE fixes add guards (branch,
  pointer, `#define`) while regression fixes add functions, globals and state (FORT); structural predictors of fixes
  reduce to size and churn (the size wall); identity: keyword mix 95.9% (SIG-H1), sfs 99.0% (SFS-H1).
- Nothing below has been computed on call networks. CGT-6 (GitGalaxy's own PRs) is deferred to a later registration.

## Data (fixed before any measurement)

- **Snapshots:** the canonical quarterly history databases (`tools/sfs_eval.py` `DBS`) and their walks
  (`tools/nh_eval.py` `snapshots`): curl 105, OpenSSL 110, libarchive 70, harfbuzz 62, nDPI 43 (390 in all). Each
  database was scanned by one engine; comparisons stay within a repository (CGT-5 is the exception, see its caveat).
- **Fix labels:** `events/<repo>_xc.json` (classes `latent` = CVE fix, `regression`, `extrinsic`, `other-fix`) and the
  `control` commits of `events/<repo>.json`.
- **Release tags:** the pool clones' git tags.

## The call network of a snapshot

- **Nodes:** functions with `loc ≥ 3` in C/C++ files (`.c .h .cc .cpp .cxx .hh .hpp`), identified by (path, name).
- **Edges:** caller → callee for each name in the caller's `calls_out_to` that resolves to a node: a definition in the
  caller's own file first, else the only definition of that name in the snapshot; ambiguous and external names
  (libc, other libraries) are dropped. Self-loops dropped.
- **Rename tracking:** between consecutive snapshots, paths are carried across `git diff -M --name-status` renames,
  so a moved file is not death plus birth.
- **Between consecutive snapshots t → t+1:**
  - *persisting* nodes P = nodes present at both;
  - **rewiring** R = |E_t[P] Δ E_{t+1}[P]| (edges among persisting functions added or removed);
  - **growth** G = edges at t+1 touching new nodes + edges at t touching removed nodes;
  - **churn** C = lines added + removed in C/C++ files (`git diff --numstat`, renames followed);
  - **rewiring fraction** r = R / |E_t[P] ∪ E_{t+1}[P]|.

## Claims

All one-sided; α = 0.01 per claim family (CGT-1 … CGT-5), split evenly across a family's claims; bootstrap and
permutation seeds 2982.

| id | claim | supported iff |
|---|---|---|
| **CGT-1a** | **Static most of the time:** a typical quarter barely rewires | median quarterly r < 0.02 in ≥ 4 of 5 repos |
| **CGT-1b** | **Change comes in jumps:** the busiest 10% of quarters carry a large share of all rewiring | top-decile share of Σ R ≥ 0.40 in ≥ 4 of 5 repos |
| **CGT-1c** | **Jumps beyond code volume:** rewiring is burstier than churn | Gini(R) − Gini(C) > 0 with block-bootstrap (blocks of 4 quarters, 5,000) lower bound > 0 in ≥ 4 of 5 repos |
| **CGT-2a** | **Releases:** quarters containing a major/minor release (x.y.0, or nDPI x.y) rewire more than others, beyond churn | rewiring residual (log(1+R) on log(1+C), per repo) higher in release quarters; within-repo label permutation (10,000), pooled statistic = mean residual difference, p < 0.005 |
| **CGT-2b** | **Features arriving:** quarters that add new C files also rewire existing code more, beyond churn | Spearman(new C files, rewiring residual) > 0 pooled over repos (within-repo permutation, 10,000), p < 0.005 |
| **CGT-3a** | **Regressions rewire more than CVE fixes** at equal diff size | commit changes ≥ 1 internal call edge: regression vs latent, Cochran–Mantel–Haenszel across (repo × diff-size quintile) strata, odds ratio > 1, p < 0.005 |
| **CGT-3b** | **CVE fixes are surgical:** they rewire less than other fixes at equal size | latent vs other-fix, same CMH test, odds ratio < 1, p < 0.005 |
| **CGT-4** | **Rewired files attract later fixes beyond churn** (prior: null, the size wall) | file-quarters with rewiring vs churn-matched file-quarters without: fix (any xc class) touching the file in the next 365 days; CMH over (repo × churn quintile), OR > 1, p < 0.01 |
| **CGT-5** | **The call network identifies a project across eras** | name-free Weisfeiler–Lehman (3 iterations, initial label (in, out) degree) histogram cosine; each snapshot's nearest neighbour among all other repos' snapshots plus its own repo's snapshots ≥ 5 years away is its own repo in ≥ 90% of snapshots that have such a same-repo candidate (SIG's bar) |

**CGT-3 sampling and measurement.** Per repo and class (latent, regression, other-fix, extrinsic, control), up to 120
commits with ≥ 1 C/C++ file changed, drawn at random (seed 2982) from the labelled set. For each commit, the changed
C/C++ files are scanned at the commit and at its first parent (one engine scan per repo, gitgalaxy `8f96d76ba`,
history off); a call edge is internal if its callee is defined in the nearest earlier quarterly snapshot or in the
changed files. Diff size = C/C++ lines added + removed. Extrinsic and control are descriptive.

**CGT-4 grain.** File-quarter: a file rewires in quarter t if it holds a caller of an added or removed persisting edge.
Churn = the file's lines added + removed in that quarter. Fixes from `<repo>_xc.json` by `c_files`.

## Not evaluable

- CGT-1/2: a repo with < 20 consecutive-snapshot pairs is dropped (none expected).
- CGT-3: < 30 commits in either compared class pooled over repos. CGT-4: < 20 positive file-quarters per repo.

## Priors (stated so they can be wrong)

- **CGT-1a/1b:** expected to pass (owner's hypothesis; SIG's keyword spurts). **CGT-1c:** uncertain; rewiring may just
  be a fraction of churn.
- **CGT-2a:** uncertain (releases may follow, not hold, the work). **CGT-2b:** expected weakly positive.
- **CGT-3a/3b:** expected to pass (FORT: CVE fixes guard, regressions add functions and state).
- **CGT-4:** expected null.
- **CGT-5:** uncertain; large networks may all look alike to a degree-seeded WL histogram.
  **Caveat:** each repo was scanned by a different engine, so an engine difference could separate repos.
  Descriptive control: the same identification on keyword-mix vectors from the same databases.

## Guards

- Registration before scorer and run; one run; verdicts published either way.
- Size: churn controls in CGT-1c, 2a, 2b, 3 (diff-size strata), 4 (churn-matched).
- Rename tracking between snapshots; temporal ablation is inherited from how the history databases were scanned.
- Multiple comparisons: α split within each family as stated; families reported separately.
