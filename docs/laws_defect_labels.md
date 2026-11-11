# The defect laws under the keyword label and under the M6 workflow label

Development data (the eight CGR practice repos), never panel results. Tool: `tools/laws_defect_run.py`; the label
comes from `tools/laws_github.py` (see `docs/laws_github_labels.md`). Numbers:
`/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot/defect_laws_both.json`.

`laws_panel.History` now takes an optional per-sha fix label and `file_years` threads it through, recording how
many labels it changed. A sha the mapping does not name keeps the history database's own label, which is the
fallback for a bot's commit, a commit touching no unit source file, and every commit of a repo that is not on
github.com.

## What changes

| repo | language | labels changed | positive file-years | LAW-6 | LAW-7 coupling | LAW-8 |
|---|---|---|---|---|---|---|
| prometheus | go | 1,122 | 800 → **1,356** (38.8% → **65.8%**) | −0.002 ± 0.171 → **+0.176 ± 0.282** | +0.75 → +0.80 | −0.0006 → −0.0010 |
| libgit2 | c | 264 | 575 → **974** (20.9% → **35.4%**) | −0.350 ± 0.219 → −0.454 ± 0.232 | +0.97 → +0.95 | +0.0026 → −0.0002 |
| sphinx | python | 63 | 1,152 → 1,174 (53.4% → 54.4%) | −0.393 ± 0.265 → −0.418 ± 0.266 | +0.51 → +0.52 | −0.0067 → −0.0079 |
| redis | c | 7 | 757 → 757 (56.8%) | not evaluable | +0.59 | +0.0053 |
| commons-lang | java | 0 | 608 → 608 (22.4%) | −0.019 ± 0.171 | +0.69 | +0.0011 |
| ripgrep | rust | 0 | 132 → 132 (34.0%) | +0.393 ± 0.303 | +0.85 | not evaluable |
| libxml2 | c | 0 (GitLab) | 807 → 807 (44.1%) | not evaluable | +0.58 | +0.0224 |
| postgres | c | 0 (no PRs) | 12,682 → 12,682 (47.9%) | +0.092 ± 0.088 | +0.74 | +0.0046 |

redis's 7 revised labels fall outside the file-year windows, so its panel does not move. Four repos cannot move
at all: commons-lang and ripgrep have no linked issues to read, postgres has no pull requests, libxml2 is not on
GitHub.

## Four readings

1. **LAW-7 is robust to the label, and that matters most.** Coupling's attenuation moves by at most 0.05 anywhere
   (0.97 → 0.95, 0.75 → 0.80, 0.51 → 0.52), and the other two metrics likewise. The size-confound result — the
   one confirmatory defect law the pilot found an effect for — does not depend on which fix label is used. That
   is the strongest thing in this table.
2. **LAW-6's prometheus reading was partly an artefact of the label.** It moves from −0.002 ± 0.171 to
   +0.176 ± 0.282: the point estimate crosses zero and the interval widens. Neither is significant, so nothing is
   claimed either way, but a law whose sign depends on how fixes are labelled cannot be read off the keyword
   label alone. LAW-6 was already expected to be inconclusive; this is a second reason.
3. **The new label's precision is untested, and prometheus's positive rate is the warning.** 65.8% of
   prometheus's file-years now carry a fix in the following year. M6's own problem statement predicted this:
   "Conventional commits put `fix:` on lint, docs and test fixes", and this implementation reads the PR title
   with the same keyword regex, so a Go repo using conventional commits will have `fix:` titles that are not
   defect repairs. The +82% is therefore an upper bound on the recall gain and carries unknown precision loss.
   **This is now the concrete question the label audit has to answer**, and it is why the audit should be drawn
   from this label rather than the keyword label.
4. **Only three of eight repos can move.** The correction reaches exactly the repos whose workflow puts the
   evidence in a PR, which is the differential-evidence problem from `docs/laws_github_labels.md` seen from the
   other side: adopting the workflow label does not remove the asymmetry between languages, it relocates it. A C
   pool of GitLab and mailing-list repos still gets the keyword label while the Go pool gets PR text.

## What this does not settle

Whether the panel's confirmatory LAW-6, LAW-7 and LAW-8 runs use the workflow label is a registration decision,
not a result. The evidence for taking it: a merge-unit repo's recall under the keyword label is roughly half, and
LAW-7 is unaffected either way, so adopting it costs the robust law nothing. The evidence against: precision is
unmeasured and prometheus's positive rate looks high. The audit decides it, and the scorer freeze records it.
Nothing here changes any registered default -- `file_years` still defaults to the database's keyword label, and
every number above is reported in pairs.
