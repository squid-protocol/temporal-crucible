# LAWS label audit: the raters, the prompts and the model (methods review M6)

Registered in `docs/laws_hypotheses.md` Amendment 0 item 3: the fix label is audited by two Claude raters, and
**the prompts, the model id and the sampling settings are committed before any audit label is produced**. This
file is that commitment. `tools/laws_audit.py` reads the prompts from here by heading, so an edit to a prompt
after labels exist shows up as a diff against the labels' recorded prompt hash.

## What is audited

`tools/laws_history.py`'s fix label: the commit's message matches `FIXLIKE` once `Fixes #N`-style phrases are
removed, the author and committer are not bots, and the commit touches at least one unit source file. The audit
measures that rule's **precision** (of the commits it calls fixes, how many are fixes) and its **recall** (of the
commits that are fixes, how many it calls fixes). Both are needed: LAW-6 to LAW-9 all read the fix label, and a
keyword rule's error is not symmetric.

## The sample

Per language of the pilot (c, java, go, python, rust), with seed 2982, from the development repos only:

| stratum | drawn from | n per language |
|---|---|---|
| `fix` | commits the rule labels `fix = 1` | 50 |
| `not-fix` | commits the rule labels `fix = 0` that touch a unit source file | 50 |
| `recall` | a fresh draw from `fix = 0`, disjoint from the `not-fix` stratum | 50 |

`fix` and `not-fix` give precision and specificity; `recall` is the separate pool the review asks for, so a recall
estimate is not read off the same commits that produced the precision estimate. 150 commits per language, 750 in
all, each rated twice: 1,500 ratings.

## The raters

Both raters are `claude-opus-5-5`. Rater A is given the commit message, the diff and the class definitions, plus
the list of files touched. Rater B is given the commit message, the diff and the class definitions **only** -- no
file list, no rater A label, no network measure, no repo name, in its own request with no shared conversation.
Disagreements are reported, not resolved: the audit reports Cohen's kappa and both raters' marginals, and the
label's precision and recall are reported as the interval spanned by the two raters.

**Sampling settings.** None are sent. `temperature`, `top_p` and `top_k` return HTTP 400 on `claude-opus-5-5`, so
the registered "temperature" cannot be set; thinking is always on for this model and `output_config.effort` is the
only depth control. The audit sends `effort: "low"` -- the task is a two-way classification of a short diff -- and
records the effort, the model id and this file's hash with every label. **This is a deviation from Amendment 0
item 3 as written** ("prompts, model id and temperature"): it is logged here and belongs in the scorer-freeze
amendment.

Requests go through the Batch API (half price, and the audit is not latency-sensitive). A diff is truncated to
`MAX_DIFF_LINES` lines; a truncated diff is marked as such in the prompt and in the record, and the share of
truncated diffs is reported per stratum.

## Prompt: system

```
You are labelling commits from an open-source repository for a software-engineering study. You will be shown one
commit: its message, and its diff. Decide whether the commit is a BUG FIX.

A commit is a BUG FIX when its purpose is to correct behaviour that was wrong: a crash, a wrong result, a memory
error, a race, a regression, a security flaw, a build that was broken for users, or a mistake in behaviour that
had shipped. The repair itself is what matters, not the words used for it.

A commit is NOT a bug fix when its purpose is anything else: a new feature or option, a refactor or rename that
keeps behaviour, formatting or style, a comment or documentation change, a dependency or version bump, a test
added or changed without a behaviour change beside it, a build or CI configuration change, a revert, a merge, or
a release or changelog commit.

Judge the commit in front of you. Do not guess at project conventions you cannot see, and do not treat the
presence or absence of a word like "fix" as decisive: a commit that says "fix" may be a refactor, and a commit
that never says it may repair a crash.

If the diff has been truncated you will be told so; label from what you can see and lower your confidence.

Answer with JSON only: {"label": "fix" | "not-fix", "confidence": "high" | "medium" | "low", "reason": "<one
short sentence>"}.
```

## Prompt: rater A user message

```
Commit message:
<<<
{message}
>>>

Files touched ({n_files}): {files}

Diff{truncated}:
<<<
{diff}
>>>
```

## Prompt: rater B user message

```
Commit message:
<<<
{message}
>>>

Diff{truncated}:
<<<
{diff}
>>>
```
