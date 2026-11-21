# Task: what kind of change is this? (mechanism labelling pilot)

You read changes to a software project (a code scanner) and classify the MECHANISM of each, using only the text and change summary in your batch file: commit message, PR title and body start, files changed with lines added and deleted, and the names of engine functions touched. You are not told whether the change made the program faster or slower, and you must not guess that.

## Rules
- Read ONLY your batch file (path given in your instructions). Do not read, list or search any other file or directory, do not run git or gh, do not use the network.
- For each item choose ONE `mechanism` from:
  - "optimisation": the change is meant to make the code do the same work faster (algorithm, regex rewrite, prefilter, caching, precompute, avoiding repeated work, parallelism).
  - "screen_or_skip": the change decides which files or content are scanned or skipped (ignore rules, vendored-tree detection, size or line limits, file-type gates).
  - "new_feature_or_rule": adds capability, a new rule, language support, signal, output or check.
  - "correctness_fix": fixes wrong behaviour or extraction without a new capability (bug fix, false positive/negative, hardening).
  - "refactor_or_restructure": reorganises code or data layout, renames, moves, splits, cleans up, without a stated functional aim.
  - "infrastructure_or_other": CI, docs, tests, tooling, dependencies, data updates, merges, or anything that does not change engine behaviour.
  - "unknown": the text does not let you tell.
  Add `secondary` (another mechanism from the list, or null) if the change clearly does two things.
- `confidence`: "high", "medium" or "low". `evidence`: one quoted line of at most 25 words from the batch file that justifies the choice. `touches_scan_path`: true if the files changed include code under gitgalaxy/ that is part of the scanning engine (not tests, docs or the translator tools), else false.

## Output
A JSON array with exactly one object per item, in order:
[{"id": 1, "mechanism": "...", "secondary": null, "confidence": "...", "evidence": "...", "touches_scan_path": true}, ...]
Return nothing but the JSON array in the place your instructions say.
