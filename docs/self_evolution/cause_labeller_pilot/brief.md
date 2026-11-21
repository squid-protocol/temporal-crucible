# Task: find the pull request that caused each bug (labelling pilot)

You label bug issues of a software project. For each issue in your batch file, decide which EARLIER pull request (PR) most likely introduced the bug, using ONLY what is in that file: the issue title and body, its creation date, and a list of candidate PRs that were merged in the 45 days before the issue was created.

## Rules
- Read ONLY your batch file (path given in your instructions). Do not read, list or search any other file or directory, do not run git or gh, do not use the network. Judge from the text in the batch file only.
- `cause_pr` must be: a PR number from that issue's `candidates` list, OR a PR number the issue text itself explicitly names as the cause, OR null.
- null is a valid and common answer. Return null when no candidate is a plausible cause: the bug may be old, caused by something outside the list, a gap in a new feature, a test or tooling problem, an external change, or the issue gives too little to tell. Do not guess to fill the list. A wrong cause is worse than null.
- Prefer a candidate only if you can quote a line from the issue or from the candidate (its title, files or body start) that ties them: the same function, file, feature, symptom or an explicit statement of cause.
- `cause_type`: "regression" (a listed or named PR introduced it), "pre-existing" (latent, found now but not introduced by a recent PR), "external" (dependency, platform, upstream data), or "unknown".
- `confidence`: "high" (explicit statement or unmistakable tie), "medium" (strong textual tie), "low" (plausible only).
- `evidence`: one quoted line, at most 25 words, that justifies your choice (or, for null, the line that shows why none fits; empty string if there is nothing to quote).

## Output
A JSON array with exactly one object per issue in the batch, in order:
[{"issue": 1234, "cause_pr": 5678 or null, "cause_type": "regression", "confidence": "medium", "evidence": "..."}, ...]
Return nothing but the JSON array (no commentary) in the place your instructions say.
