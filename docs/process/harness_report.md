# The first three-way table — SA3's existing pipeline against control repositories

**2026-11-14.** Produced by the harness (`tools/harness/`, built by Opus to `harness_spec.md`), checked and
written up by the reviewer (Fable). This is step 1 of `research_codebase_spec.md`. Every SA3 tool ran
unmodified, inside a sandbox in which the real study directory, the corpus and the network do not exist.

**What it is.** For each rule: what SA3's code did on a generated repository, what the repository's manifest
says the answer is, and whether they agree. Ten repositories, seed 11, default size (306 unit files, 3,000
commits), ten-year span: negative and positive controls in Python and C, and six mutations.

**What it is not.** No real repository was scanned and no SA3 outcome was read. Nothing here is a result
about SA3's hypotheses.

## Headline

| | |
|---|---|
| Rules compared per repository | 22 |
| Agree | 4 to 7 |
| Differ | 13 to 16 |
| One engine scan | 2.4 seconds; a whole repository, both routes, 16 seconds |
| Stages that would not run | `lock` and `score`, as designed: no committed code review |

Most "differ" rows are two sound things measuring differently. Six are faults in SA3's code, listed first.

## Faults in SA3's code that this found

Each was confirmed in the source by the reviewer. They are in the defect log as entries 55–60.

1. **Any directory named `cache/` is treated as vendored.** GitHub's vendored list has the pattern
   `(^|/)cache/`. The generated repository has first-party code under `src/…/cache/`; the pipeline dropped all
   54 such files from the ranked set (252 of 306 ranked), and with them 22 positive files. In a real repo this
   removes first-party code such as a framework's cache module. How many SA3 files it removes is unknown; it is
   a count to make when the stored `file` table is built.
2. **The completeness check cannot see this.** It divides the scanned unit files by the unit files in the
   archive, both under the pipeline's own unit rule. It read 100% with 54 unit files missing.
3. **The seal fails open outside a git checkout.** `sa3_score.py lock` reads an empty answer from `git status`
   as "nothing uncommitted" without checking that git succeeded. Outside a checkout it seals "at commit ''".
4. **The nesting scan can measure nothing and report success.** Every error per file is swallowed. Without its
   grammar cache it measured 0 of 252 files and exited 0.
5. **A repository whose merges are all bot-authored is scored as an empty, valid repository** when the
   snapshot is supplied: the cut falls on the first commit, the window ends two years before it starts, and
   the outcome file says status "ok" with no positives. (Left to choose its own snapshot, the pipeline stops
   correctly: "only 1 usable commits".) This is how mediawiki went wrong (defect log 29).
6. **The placebo stage crashes** when no repository clears the floor.

## What the pipeline does that the text does not say

| | |
|---|---|
| A Jira key counts only after a fix word | "PROJ-12: handle empty input" is not a fix reference; "Fixes PROJ-12" is. 15–17 of 103 expected commits were lost this way. The registration says "fix reference (issue, Jira, …)" |
| A revert of new code that quotes a ticket | is counted, through the quoted ticket. This is the case the control repository lists as ambiguous |
| The window never moves | It starts at the later of the code's own cut and the scanned snapshot, and ends at the cut plus 730 days. Supplying a snapshot changes the scan, not the window |
| A file renamed after the snapshot | stops being a positive (matching is by equal path), as the registration's unrun sensitivity S8 implies |

## Where the instrument and the manifest count differently (not faults)

| measure | relation, on every file checked |
|---|---|
| Lines | engine = file's line count + 1 |
| Branch keywords | engine's `struct_branch` = `if`/loop/switch keywords **plus** `else`, `case`, `default`, `&&`, `||`, `and`, `or` |
| Calls in | `in_degree` includes calls within the same file (2,159 of 2,811 in one repository); its cross-file part equals the manifest on 251 of 252 files |
| Pointers (C) | `state_pointers` = pointer writes + pointer declarations, exactly; allocations equal exactly |
| Nesting | equal on every file |
| Snapshot | the pipeline's is 6 commits (2.9 days) later: it takes position `int(0.8 n)` of non-bot commits, the generator `ceil(0.8 n) − 1` of all commits |

## How much of a planted effect comes through

The builder's single-repository reading ("most of the planted effect is lost at the label step", +0.028 against
+0.094) did not hold up. The reviewer ran ten positive controls (`branches=0.5`, seeds 21–30):

| the statistic computed on | mean effect | standard error |
|---|---|---|
| true fixes, all unit files | +0.133 | 0.010 |
| the labels SA3's written rule should give | +0.081 | 0.013 |
| … on the files the pipeline also ranks | +0.079 | 0.014 |
| … measured with the engine's instrument | +0.078 | 0.016 |
| the pipeline's own labels (what SA3 would report) | **+0.066** | 0.014 |

- **The label rule costs about 40% of a true effect**, before any code runs: ticketed features count as fixes,
  and fixes with only a keyword or no signal do not. How large this is depends on the mix of conventions the
  generator was given, which is an assumption, not a measurement of real repositories.
- **The pipeline's own losses cost about another 20%** of what is left (the `cache/` files, the Jira keys).
- **The instrument costs nothing measurable**: counting `else` and `&&` as branches did not blur the effect.
- A single repository of this size is noise: the ten pipeline values run from −0.002 to +0.135. No effect row
  of a single run should be read.

## Mutations: what the pipeline did with each planted fault

| mutation | outcome |
|---|---|
| `merge_workflow` | Inheritance works: the same 70 positive files as without merges. The keyword outcome is empty, because a merge subject never carries a keyword |
| `bot_merges` | Fault 5 above |
| `sweep_labelled_fix` | Handled: the ticketed licence sweep is removed as tree-wide |
| `renames_after_snapshot` | 9 fixes lost to renames, 8 to a cut moved 56 days by the extra commits. A delete touching 38 unit files counts as 25 for the pipeline, so it is not tree-wide and enters the control pool |
| `vendored_half` | Not detected, as expected: all 295 unmarked imported files are ranked and can never be positive; call-graph effects inflate to +0.17 |
| `mixed_language` | Handled: the other language's files are excluded |

## What follows

- The six faults go into SA3's fix list beside entries 42–48. Numbers 1 and 2 need a count on the real repos
  before a ruling; that count is a product of the stored `file` table (step 3).
- The four unstated behaviours go into Amendment 5 with "code governs" as the default.
- The control repository should stop placing base files under names GitHub's lists match, and plant them as a
  mutation instead; and split its Jira convention into "with a fix word" and "bare". Until then the universe
  and label rows differ for a known reason.
- Effect rows need many seeds. The suite of `research_codebase_spec.md` section 7 is affordable: 20 seeds of
  one configuration take about five minutes.
