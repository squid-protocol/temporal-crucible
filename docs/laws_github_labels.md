# PR titles, PR bodies and linked-issue labels in the fix label (methods review M6)

Development data (the eight CGR practice repos), never panel results. Tool: `tools/laws_github.py`. Records:
`/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot/github/<repo>.json`, PR cache under
`.../pilot/github/cache/<owner>__<name>/`.

M6's "Workflow handling" paragraph, implemented verbatim: where at least 30% of first-parent commits are merges
the unit is the first-parent commit, **labelled from the merge commit message plus the PR title and body**; where
available **the linked issue's labels** are used, a `bug` / `type: bug` / `kind/bug` / `defect` issue making the
fix label and a `feature` / `enhancement` issue suppressing a keyword-only one; and `Fixes|Closes|Resolves #N`
alone is not a keyword.

## What it changes

| repo | language | merge share | unit | units | with PR | with issue | fixes before | after | change |
|---|---|---|---|---|---|---|---|---|---|
| prometheus | go | 0.469 | first-parent | 4,861 | 4,398 | 658 | 1,300 | **2,362** | **+81.7%** |
| libgit2 | c | 0.671 | first-parent | 2,874 | 1,885 | 218 | 837 | **1,101** | **+31.5%** |
| sphinx | python | 0.284 | non-merge | 9,873 | 889 | 202 | 2,354 | 2,417 | +2.7% |
| redis | c | 0.104 | non-merge | 9,349 | 2,692 | 454 | 3,276 | 3,275 | −0.0% |
| commons-lang | java | 0.023 | non-merge | 5,333 | 420 | 0 | 849 | 849 | 0 |
| ripgrep | rust | 0.028 | non-merge | 1,060 | 15 | 1 | 254 | 254 | 0 |
| postgres | c | 0.000 | non-merge | 40,621 | 0 | 0 | 16,980 | 16,980 | 0 |
| libxml2 | c | 0.000 | non-merge | — | — | — | 2,927 | — | skipped (GitLab) |

By rule, where anything changed: prometheus +1,025 from PR text, +67 from a bug-labelled issue, −30 suppressed by
a feature-labelled one; libgit2 +257 from PR text, +7 from a bug label; sphinx +63 all from bug labels; redis +3
and −4.

## What that means

1. **M6 was right, and the size of it is the point.** The keyword rule on a merge-commit workflow finds barely
   half the fixes: prometheus goes up by 82% and libgit2 by 32% once the PR title and body are read. A merge
   commit's own message is "Merge pull request #7 from user/branch" and carries no evidence at all, so the rule
   was labelling the wrapper rather than the work. Without this correction the defect laws would compare a Go
   repo at roughly 55% fix recall against a C repo at nearly 100% — differential recall by workflow, and since
   workflow tracks language, by language. That is the confound LAW-7 exists to test, sitting in the labels.
2. **The issue-label half of the rule is not a general instrument.** Outside the two merge-unit repos it moves
   between 0.0% and 2.7%. It reaches nothing at all in commons-lang, which has 420 pull requests and **zero**
   linked issues, because Apache tracks issues in JIRA (`LANG-####` in the message) and GitHub's
   `closingIssuesReferences` cannot see them. Any Apache or JIRA-based panel repo gets the keyword rule and
   nothing more, and a registration that leans on issue labels should say so.
3. **A non-GitHub repo cannot have the rule applied.** libxml2 is on gitlab.gnome.org and is skipped. This is a
   second, unregistered source of differential recall: of the panel's ten languages, the C and C++ pools will
   hold self-hosted and GitLab repos that get no PR or issue evidence while their Go and Java counterparts do.
   The registration does not address it. Worth an amendment line before the draw, even if the answer is only to
   report the share of panel repos the rule could reach.
4. **postgres is a correct no-op.** 40,621 units, no pull requests: it is a mailing-list project whose github.com
   presence is a mirror. The rule neither helps nor harms there, which is the right behaviour.

## A bug this found, worth not repeating

The first run changed 250 postgres labels with no PR and no issue involved — impossible under the rules. The
cause: `laws_history.py` stores only the first 300 characters of a subject, and this tool was recomputing the
keyword decision from that truncated copy, so a keyword past character 300 was lost. The keyword decision is now
taken from the history database's own `keyword` column and the PR's text can only ever **add** to it. postgres is
now 16,980 → 16,980. Any future consumer of `commit_.subject` has the same trap waiting.

## API cost

The whole pilot cost **1,780 GraphQL points of the 5,000/hour budget** (core REST untouched), and every pull
request is cached on disk, so the re-run after the bug fix cost **0**. One batched query carries 50 pull requests
with their linked issues' labels; `--max-queries` and a 500-point floor stop a run rather than draining the
budget. PR numbers come from the commit messages (`Merge pull request #N`, or a squash subject's trailing
`(#N)`), never from an API call.

## Not done

`laws_panel.py` still builds its file-years from the history database's `fix` column, so **LAW-6, LAW-7 and LAW-8
are still computed from the keyword label.** `laws_github.fix_labels()` returns the revised mapping ready for it.
Wiring it in changes what those three laws are computed from, so it is its own step and has to happen before the
scorer freeze — on this evidence it should, because the two merge-unit repos move by 32% and 82%.
