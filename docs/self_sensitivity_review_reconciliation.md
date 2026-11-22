# Reconciliation of two independent reviews of the final-analysis scripts (2026-11-20; dated amendment record per STUDY_CHECKLIST item 15)

Reviewers: Claude (Fable) and Gemini 4 Neon, same brief (`reviews/brief_final_analysis.md`), read-only, each ran synthetic tests (Claude 7 scenarios; Gemini 17 tests, 15 reproducing bugs). Full amendments adopted: `docs/self_sensitivity_plan.md` Amendment 2 (and the fix list sent to the script builder).

## Where they agree (acted on)
- Rounding of `dcpu` routes the bisection to the wrong metric (2 of 75 candidates, including the E1 bracket on cics-crucible). Bisect also never probes the first commit after the lower bracket (8 of 22 non-localised refinements end at the second commit). Fixed in `bisect_cost_v2.py` / `refine_candidates_v2.py`; second pass queued.
- The persistence rule is flawed: "reversed" counts steps that were never visible, overshoots read as persistent, "elevated at tip" is almost automatic under 3x-100x cumulative growth, windows overlap neighbouring steps, run dates are UTC while commit dates are Eastern. Rule rewritten (Amendment 2).
- The quiet-step test mixes populations (the all-events share is paired with an engine-path-only p-value), is era-confounded, and the diff cache omits 27 core merge commits and the root. Stratified and reported at several cutoffs; cache gaps reported separately.
- Known-event recall can not fail (always-true date test, no UNCONFIRMED status). Duplicate (corpus, commit) rows and mixed CPU/files sizes corrupt sizes and persistence. `run_all.sh` continues after a failure and can read stale JSON. T measured on the tip's long scans is applied to 0.3-3 second early scans (post-hoc absolute-floor sensitivity added).
## Found by one reviewer only (also adopted)
- Gemini: the performance-word regex inherited from `join_steps.py` has no closing word boundary and a trailing-space bug (matches PERFORM, FastAPI, PERF401); recomputed: 209 subjects (3.1%) against 277 (4.1%), scan-path share unchanged at 26%, culprit still unflagged (correction added to `docs/self_speed/step_join_findings.md`). Also: PR numbers are missed when `#N` is not at the end of the subject (77 commits); Fisher 0/0 odds ratio and a Clopper-Pearson overflow at n >= 1030; a corpus with one timed point crashes the report; reversal scan skips the first commits after the post window; DOWN steps with fewer than 3 later commits are dropped and their size can turn positive.
- Claude: bisect off-by-one (above); the files-metric refinement uses 3% not T; right-censoring; the all-events quiet test pairs inconsistently; "mixed" direction plotted as up.
## Disagreements
None of substance. Gemini ranks the Fisher-complement bug higher and Claude ranks persistence higher; both are fixed.
## Not changed
`detect_steps.py` is left alone (it runs again at the end of the pipeline); the report lists every consecutive pair that spans a failed run as UNRESOLVED instead. Reviewers' point that multiplicity is uncontrolled and p-values are descriptive stands: the report labels them so.
