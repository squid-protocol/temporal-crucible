# Cause-labeller pilot: can models find the PR that caused a bug, from the issue text alone? (plan fixed 2026-11-20, before any label exists)

EXPLORATORY. Goal: independent (cause PR, fix PR) pairs for the repair-radius experiment, because causes derived by blame are circular (docs/self_lattice_and_radius_plan.md section B). Context: docs/self_evolution/pr_issue_labeling_exploration.md; suggestion filed as promoter-bot#124.

## Sample (seed 2982)
100 bug-labelled issues of squid-protocol/gitgalaxy that were closed by a merged PR through a closing keyword. All issues whose body already names an earlier merged PR with causal wording (the regex-found pairs) are included as a GOLD group; the rest of the 100 are a seeded random draw from the remaining closed-by-PR bug issues. Reported separately.

## What a labeller sees (independence rule)
The issue title, body (trimmed to 3,000 characters), creation date, and a candidate list of merged PRs (number, title, merge date, up to 6 touched files, first 200 characters of body), merged in the 45 days before the issue, never the closing PR, never any fix diff, never blame. Candidates are ranked by overlap with files named in the issue (else by title/body word overlap with the issue) and cut to 25; bot-generated docs/data and dependency PRs are excluded. The closing PR and the regex-found cause live in a key file the labellers are not given.
Output per issue: `cause_pr` (a number from the list or null), `cause_type` (regression | pre-existing | external | unknown), `confidence` (high | medium | low), `evidence` (one quoted line of at most 25 words). null is a valid answer and must not be guessed.

## Labellers
Two models, labelling independently: Claude (4 subagents of 25 issues, no shared context) and Gemini 4 Neon (via agy, read-only plan mode). Same rubric text.

## Decision rules (fixed now)
- GOLD recall: on the gold issues (the cause is named in the text) the labeller should return that PR: at least 85% each. Below 70% means the labeller cannot even read explicit causes; stop.
- Agreement between the two labellers on the non-gold random group: on null versus non-null at least 70% raw agreement; exact agreement on the cause PR when both give one at least 60%. Below 50% exact agreement: the labels are not usable; fall back to the prospective template rule (promoter-bot#124).
- Plausibility check afterwards (not an input): for the non-gold labels where both models agree on a cause, the share where the cause PR touched a file the fix PR also touched, compared with the same share for the other candidates of those issues. Reported, not gated.
- Hand check: the owner's own labels of about 50 of these issues would be the real gold; this pilot cannot replace that.
- If the first three rules pass, scale to all closed-by-PR bug issues (556) and feed the repair-radius design B; otherwise report and stop.
