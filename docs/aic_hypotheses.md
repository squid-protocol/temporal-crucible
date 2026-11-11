# AIC — do AI-assisted changes add more new dependencies than the same author's own changes? — registered 2026-11-11 (owner OK), PROSPECTIVE: scored only on commits made after 2026-11-11

**Why.**
- The exploratory structural-footprint study (`docs/ai_structure_exploratory.md`, PR #154) found one pattern that
  was consistent across people. When an author's commit declares AI assistance, the functions it modifies gain more
  new callees than that author's other changes of the same size: median +0.28 per modified function, 11 of 13
  authors.
- Nothing else separated AI from human changes consistently: shape moves, guards, branching, and what AI writes from
  scratch.
- That pattern was found on the data it describes. This registration tests it **only on commits made after the
  registration date**, so no commit that suggested it can confirm it.

## Prior work

- **This program:** the AI-commenting study (`docs/ai_comments_exploratory.md`, #153) and the structural-footprint
  study (#154), both exploratory. CGT and CGK found call-network position matters for fix classes at file grain.
- **No published study known to us** compares the call dependencies added by explicitly AI-co-authored commits with
  the same developers' own commits. The closest work uses AI-text detectors on comments (Ji et al., arXiv 2607.01867)
  and does not look at structure. A literature check is repeated before the result ships.
- **This study's difference:** declared (trailer-marked) AI use, a within-author contrast at matched edit size, and a
  prospective holdout in time.

## Data

- **Repos:** every C/C++ repo in the pool with declared-AI commits after the cutoff. Today: curl, OpenSSL, nDPI,
  harfbuzz, libarchive, libgit2, libxml2, postgres, redis, plus any C/C++ repo added to the pool before scoring.
  Each repo is fetched to its latest upstream head at scoring time, and the heads are recorded.
- **Commits:** non-merge commits with commit time **after 2026-11-11T00:00:00Z** that touch in-scope C/C++ functions.
  "In scope" uses the rules of `tools/ai_structure.py` (#154).
- **Declared AI:** an AI tool named in a Co-authored-by / Assisted-by / Generated-by / "Generated with" line
  (`tools/ai_comments.tool_of`, #153). A bare `Assisted-by: <person>` is not AI.
- **Measure, per modified function:** the number of callee names present after the commit and absent before
  (tree-sitter call expressions, `tools/ai_structure.py`), and the lines changed inside the function.
- **Per author** (git author email, lowercased): mean new callees per modified function in their declared-AI commits,
  minus the same mean over their other commits re-weighted to the AI side's mix of lines changed per function (bins
  1–2, 3–8, 9–32, 33–128, > 128). This is #154's `std_mean`.
- **Qualifying authors:** ≥ 10 modified functions in declared-AI commits and ≥ 10 in other commits, within one repo
  (an author active in two repos counts once per repo).

## Claims (one-sided, α = 0.01/2)

| id | authors | test | supported iff |
|---|---|---|---|
| **AIC-1** | all qualifying authors | sign test on the per-author differences (H1: more authors positive than negative; zeros dropped) | p < 0.005 and the median difference > 0 |
| **AIC-2** | qualifying authors **not** among the 13 in #154 (author-repo pairs listed in the result doc) | the same | the same |

- **Power:** each claim needs ≥ 15 qualifying authors. Below that it is **underpowered**, and the scorer reports the
  count so far.
- **When it is scored:** at the first run after AIC-1 reaches 15 qualifying authors, or on 2027-05-11, whichever
  comes first. If it is underpowered then, it is re-run once on 2027-11-11 and called final.

## Descriptive (no verdicts)

- Per-repo and per-tool (Claude, Codex / OpenAI, Copilot, other) medians.
- The same difference for shape moves (the #154 null) as a negative control. We expect no consistent direction.
- The share of added callees defined in the same file.

## Priors

- **AIC-1, likely supported if powered.** 11 of 13 authors in #154.
- **AIC-2, less certain.** New adopters may use AI for different tasks, and the tool mix is shifting.

## Known limits

- Only declared AI use is seen. Undeclared use biases toward the null.
- Tool choice and task choice are not random. Within-author matching on edit size controls the person and the
  change size, not the kind of task.
- Callee names are compared by name. A renamed callee counts as removed plus added.
