# Change-aware sensors: the "while you are here" prompt and the diff-aware change report

**Status: first idea back-tested, second prototyped; exploratory.** Both are our own designs, not borrowed from other tools (guide section 4.1). Tools: `tools/sensor/while_here_backtest.py`, `while_here_report.py` (output `while_here_output.txt`), `change_report.py` (demo `change_report_demo.txt`).

## 1. Idea one: a "while you are here" prompt
When a change is in front of a reader, surface the open debt in the files it touches, so a marker is decided at the cheapest moment (the debt trial found fossils in hot files are repaid about five times as often as in quiet files). The question the test answers is what a prompt has to beat: **how often is an open marker in a touched file actually repaid in that commit, under different trigger rules?**

### Back-test
Every non-merge commit of six C projects (libgit2, libxml2, redis, curl, harfbuzz, openssl) replayed over its whole history: for each commit and each touched file, the open markers at that moment (markers followed through moves, rewordings and renames); the outcome is whether the marker was repaid in that very commit. 259,242 (commit, file, open marker) observations; 3,355 repaid in the commit that touched their file (**1.29%**).
**Repayment by size of the change to the file** (per marker per commit): 0-5 lines 0.42%; 5-20 0.98%; 20-50 1.40%; 50-100 2.41%; 100-300 3.33%; 300+ **5.10%**.
**Trigger rules replayed** (precision = surfaced markers repaid in that commit; recall = share of all repaid markers the rule would have surfaced):
| rule | surfaced | per fired commit | precision | lift | recall |
|---|---:|---:|---:|---:|---:|
| every open marker in a touched file | 259,242 | 7.2 | 1.29% | 1.0x | 100% |
| change in the file of 20+ lines | 86,499 | 6.9 | 2.51% | 1.9x | 64.6% |
| change of 50+ lines | 46,941 | 7.5 | 3.44% | 2.7x | 48.1% |
| change of 100+ lines | 28,200 | 8.9 | 4.12% | 3.2x | 34.6% |
| change of 200+ lines | 16,590 | 11.8 | 4.88% | 3.8x | 24.1% |
| 50+ lines, fossil markers only | 19,087 | 6.6 | 2.18% | 1.7x | 12.4% |
| 100+ lines, fossil markers only | 11,647 | 7.9 | 2.91% | 2.2x | 10.1% |
| **50+ lines, the editor wrote the marker** | 20,410 | 5.4 | **4.81%** | **3.7x** | 29.3% |
| 50+ lines, file holds 3+ open markers | 45,254 | 8.4 | 3.09% | 2.4x | 41.7% |
Repo by repo, "50+ lines" beats "every marker" in all six (libgit2 6.0% vs 1.9%, libxml2 1.6% vs 0.4%, redis 6.6% vs 2.1%, curl 4.2% vs 1.6%, harfbuzz 6.5% vs 2.1%, openssl 6.5% vs 2.4%); libxml2 would surface 22.6 markers per fired commit (it holds 505 open markers), the others 2-5.

### Reading and design
* **Gate on the size of the change.** The 50-line rule triples the natural repayment rate and still reaches half of all repayments; below 20 lines a prompt is mostly noise.
* **Put the editor's own markers first** (precision 4.8%): people clear what they wrote, as the debt lifecycle found.
* **Fossils-only is not the way to raise the hit rate** (2.2%): fossils are the stuck ones. The prompt's job for them is to prompt a decision (delete, convert to an issue, keep), not to predict acceptance.
* **Cap the list** (three markers, ranked by the debt sensor's own order) so a repo like libxml2 does not flood the prompt.
* **What this test is and is not:** it measures how often debt is repaid *naturally* when a file is touched, under each rule; it is what a prompt has to beat. It does not measure whether showing the prompt raises repayment; that needs a pilot.

## 2. Idea two: a diff-aware change report
What did this change do to the picture of the files it touched? `change_report.py REPO COMMIT [--scan]` reports, for any commit: size and roles (source vs tests); the **mechanical share** (repeated old-to-new call swaps paired hunk by hunk, with the share of changed lines that belong to them); the **debt balance** (markers added and removed by the diff) and, if the change is large enough, the while-you-are-here markers; and, with `--scan` (engine scans of the commit and its parent, history-aware), the **reach of what actually changed**: the functions whose lines the diff touches, their callers, caller files, ripple one hop out, and their size and complexity change.
Demo on three real libgit2 commits (`change_report_demo.txt`):
| commit | what it did | what the report said |
|---|---|---|
| `2ba5a96be` delta: fail on truncated packfile | 1 file, 19 lines | organic; 1 function touched (+17 lines, complexity +2), 1 caller; too small to prompt about debt; no open markers in the file |
| `72e29b9b0` refdb: initialize on-disk data structures via the backend | 8 files, 276 lines | organic; 6 functions touched (3 new), 2 with 10+ callers (`git_repository_init_ext`: 20 callers in 6 files, 133 more one hop out, +62 lines, complexity +9); 35 distinct callers affected; prompts for two fossil TODOs in `repository.c` |
| `8bb32e578` object: move internal use to `git_object_id_from...` | 16 files, 517 lines | **mechanical swap found: `git_odb__hashfile` -> `git_object_id_from_file` x22 (about 9% of the lines)**; 24 functions touched, 62 distinct callers affected, most depended-on `git_odb_write` (27 callers in 20 files); prompts for six open markers, two written by this author |
First-run bugs found and fixed while building it: "affected callers" originally counted the callers of every function in a touched file, not only the touched ones; the swap detector originally paired lines per file and missed the third commit's swap.
Caveats: three commits is a demo, not a validation; the mechanical detector is conservative (single-call swaps in equal-size hunks); function matching uses the engine's line ranges; no outcome is claimed.

## 3. Open
* A pilot of the prompt (does showing the markers raise repayment, and at which cap and gate?).
* A validated mechanical detector (precision and recall against the sweep detector's quarterly ground truth).
* Extending the report to gauge deltas (complexity, mutation, concurrency) across more than the touched functions, and to a pull request as a set of commits.
