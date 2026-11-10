# LAW-9 on the pilot: the OSV labels, and why the law stays descriptive

Development data (the eight CGR practice repos), never panel results. Registration: `docs/laws_hypotheses.md`
LAW-9 and Amendment 0 item 2; methods review item 6. Tools: `tools/laws_osv.py` (labels and fix sizes),
`tools/laws_security.py` (the estimator). Numbers:
`/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot/law9_pilot.json`, records under `.../pilot/osv/<repo>.json`.

OSV dumps pinned at stamp `20261110` (the `GIT` ecosystem-less bucket plus Maven, Go, PyPI and crates.io),
cached with sha256 under `~/.cache/temporal-crucible/osv-20261110/`, deliberately not committed.

## The evaluability count, which the registration requires before any statistic

LAW-9 is confirmatory only where at least 5 repos per language are evaluable, at 20 or more advisory-labelled
fix commits each. Advisory-labelled fix commits on the pinned default branch, per pilot repo:

| repo | language | claimed by OSV | resolve on the branch | on the walk | evaluable |
|---|---|---|---|---|---|
| libxml2 | c | 109 | 73 | **64** | yes |
| redis | c | 121 | 18 | 18 | no |
| libgit2 | c | 58 | 27 | 13 | no |
| prometheus | go | 10 | 7 | 3 | no |
| commons-lang | java | 3 | 2 | 2 | no |
| postgres | c | 7 | 2 | 2 | no |
| ripgrep | rust | 1 | 1 | 1 | no |
| sphinx | python | 0 | 0 | 0 | no |

**1 of 8 evaluable.** The methods review expected 0 to 3 and it was right to; the real number is at the bottom of
that range. Nothing about the sample size fixes this, so **LAW-9 stays descriptive**, which is what Amendment 0
item 2 already registered. No decision is owed.

### Why the claimed count collapses, which is the finding worth carrying

Three quarters of what OSV claims never reaches the walk, and the reasons are not noise:

- **Release-branch fixes.** redis loses 103 of 121. OSV cites the commit on a `6.x` or `7.x` release branch;
  the default branch carries an equivalent commit with another sha. `laws_osv.py` recovers such a fix through a
  `cherry picked from commit <sha>` trailer, and redis recovers none that way -- its maintainers do not leave the
  trailer. Any repo that maintains release branches loses most of its CVE fixes to this, invisibly, and a repo's
  LAW-9 count is therefore partly a fact about its branching habits.
- **Fixes inside merged branches.** libgit2 resolves 27 commits but only 13 are walk units: the rest sit inside
  merged pull requests, and where the walk is the first-parent chain the merge is the unit. Attributing a fix to
  the merge that brought it in raised libgit2 from 8 to 13. Without that attribution the count is simply wrong.
- **Forks and siblings.** Advisories name `libxml2` under three URL spellings and `redis` under a historical
  `antirez` path, while `libxml2-fork` and a dozen `redis*` projects are different software. The alias set per
  repo is registered in `laws_osv.ALIASES`, and the ancestor check is what makes aliasing safe.

libxml2's own attribution: 73 direct, 36 unattributed, 0 through a merge or a cherry-pick.

## The reading on libxml2

64 CVE fixes against 2,879 other fix commits. Effect = the Hodges-Lehmann median difference (CVE - other);
`P(cve smaller)` is the rank test's own effect size, ties counted half, where 0.5 is no difference.

| metric | shift | 95% CI | p (one-sided) | P(cve smaller) | median CVE vs other |
|---|---|---|---|---|---|
| files touched | +0.00 | [0, 0] | **0.003** | 0.584 | 1 vs 1 |
| functions changed | +0.00 | [0, 0] | 0.100 | 0.545 | 2 vs 2 |
| non-test source lines | −1.00 | [−3, +2] | 0.329 | 0.516 | 14 vs 13 |

**LAW-9 does not hold here.** The law is a conjunction of all three, an intersection-union test, so its p is the
weakest leg's: 0.329. Only the files leg is significant, and at `P(cve smaller) = 0.584` it is small -- a CVE fix
in libxml2 is a little more likely to touch fewer files than another fix, and is otherwise the same size. Both
registered sensitivities agree (the prior work's 50-file cap: 64/2,877, p = 0.333; GIT-range labels alone:
63/2,879, p = 0.288). Li & Paxson's result is not reproduced on this one repo, which is all this says: one
descriptive repo is not evidence about the law.

## Two things the pilot forced, for the scorer-freeze amendment

1. **The registered effect is degenerate on these counts.** "Median difference ... each < 0" is read here as the
   Hodges-Lehmann shift. For files and functions that shift is exactly 0.00 with SE 0.00, because the counts are
   tiny and heavily tied (median 1 file, 2 functions) and most pairwise differences are 0 -- while the rank test
   on the same data is significant for files. A conjunction over an effect pinned at 0 can never fire, whatever
   the data. Nothing was changed: the shift stays the registered effect and the reading above stands. The
   amendment should decide, with these numbers in front of it, whether LAW-9's effect is the shift or
   `P(cve smaller)`. I would take `P(cve smaller)` with a 0.5 null, because it is the effect size of the test
   that supplies the p-value and it is defined on tied counts; that is a recommendation, not a change.
2. **The registered rater temperature cannot be sent.** Amendment 0 item 3 commits "prompts, model id and
   temperature". `temperature`, `top_p` and `top_k` return HTTP 400 on `claude-opus-5-5`; thinking is always on
   and `output_config.effort` is the only depth control. `docs/laws_audit.md` commits the prompts, the model id
   and `effort: "low"` in place of a temperature, and records the deviation.

## Not done

- The CGT-3b extension (call-edge rewiring, CVE against other fix, at matched size) is implemented
  (`laws_security.rewiring`) but has no input: it needs a call graph either side of each fix commit, and no pilot
  artefact holds one. It reports that rather than guessing.
- `functions changed` is git's funcname heuristic over `-U0` hunk headings, not a parse. It is the same measure
  for both classes, so it cannot favour one, but it is not the engine's unit extraction.
- redis sits at 18, two short of the bar. Recovering its release-branch fixes by patch-id rather than by trailer
  would likely clear it and would make a second descriptive repo available. Not attempted.
