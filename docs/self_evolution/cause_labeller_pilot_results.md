# Cause-labeller pilot: results (EXPLORATORY; plan `docs/self_cause_labeller_pilot_plan.md` incl. Amendment 1; 2026-11-20)

100 bug issues of gitgalaxy closed by a merged PR (seed 2982; 15 regex-gold candidates + 85 random). Two labellers, independent, same rubric: Claude (four Sonnet subagents, 25 issues each) and Gemini 4 Neon (via agy, plan mode, four runs). Each saw only the issue text, its date and up to 25 candidate PRs merged in the 45 days before the issue; never the closing PR, fix diff or blame. Labels: `cause_pr` or null, type, confidence, evidence line. Data: `cause_labeller_pilot/`.

## Outputs
| | Claude | Gemini 4 Neon |
|---|---|---|
| issues with a named cause | 15 | 15 |
| "pre-existing" / "unknown" / "regression" | 81 / 4 / 15 | 69 / 15 / 16 |
| confidence of the named causes | 3 high, 3 medium, 9 low | 8 high, 6 medium, 1 low |
Both models say most bugs (80%) have no findable recent cause from the issue text alone. Claude hedges its causes more (9 of 15 low); Gemini states them with more confidence.

## Against the rules fixed before the labels
- Gold recall (rule 1; amended to the 5 author-verified cause statements; at least 85% each, below 70% stop): Claude 3/5 (60%), Gemini 2/5 (40%). **Gate failed as written; the plan says stop and report.** All three clear cases (5525, 4859, 3867) were found by Claude; Gemini found two of three (it answered null on 3867). The two misses common to both are the cases I marked least certain when judging the gold (4300, 4528). With 5 issues, one reader, and a gold I judged after seeing four labels, this gate is weak evidence either way.
- Agreement on null versus non-null (rule 2; at least 70%): **93%** on the random group (79 of 85), 90% on all 100. Passed.
- Exact agreement on the cause PR when both name one (at least 60%, stop below 50%): **10 of 10** overall (6 of 6 in the random group). Passed, on a small count.
- Ten issues have the same cause named by both models: 1193 -> #698, 2204 -> #1975, 2827 -> #2734, 3909 -> #3866, 3929 -> #3923, 3946 -> #3887, 4758 -> #4740, 4859 -> #4843, 5208 -> #4705, 5525 -> #5512 (`agreed_pairs.json`, with the closing PR for each). Five more are named by Claude only and five by Gemini only.
- Plausibility (not gated): 8 of the 10 agreed causes touched a file the fix PR also touched, against 162 of 242 (67%) for the other candidates of those issues: no clear enrichment, because the candidates were already ranked by file overlap with the issue text.

## What this means
1. The labellers agree very strongly with each other, and mostly decline to name a cause (80% null, both). So the labels that exist are probably reliable, and scarce. Scaled to the 555 closed-by-PR bug issues the yield would be roughly 55 independent pairs (10 per 100): too few for the repair-radius test on its own (the curl run used 212 pairs).
2. The gold gate failed as written, so by the plan the pilot does not authorise scaling up. The result favours the prospective route: a required `Introduced by:` / `Regression of:` line written by the worker that knows the cause (promoter-bot#124), rather than guessing it afterwards from text.
3. Not done and needed before trusting even the 10: the owner's own labels of about 50 of these issues (the real gold); a check of the 10 agreed pairs by reading the PRs; a rerun with a wider candidate window for the issues whose cause may be older than 45 days.
Caveats: 100 issues; gold of 5 judged by the author; both models read the same candidate list built by me; the rubric allowed text-named PR numbers outside the list (3929 and 2204 used this); issues are agent-written and may omit causes the agent did not know.
