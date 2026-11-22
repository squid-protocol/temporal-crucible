# Research codebase specification — independent methodology review

**Reviewer:** Gemini (independent review on PR #185 / `sa3/build`, commit `8127814`), 2026-11-14.
**Scope & independence:** Reviewed `docs/process/research_codebase_spec.md` alongside sibling PR #185 specs (`docs/sa3_amendment5_draft.md` Rev. 2, `docs/process/tables_spec.md`, `docs/process/control_repo_spec.md`, `docs/process/harness_spec.md`, `docs/process/harness_report.md`, `docs/process/blinding_spec.md`, `docs/process/STUDY_SCAFFOLD.md`, `docs/STUDY_DEFECT_LOG.md`) and SA3/harness tools (`tools/sa3_score.py`, `tools/sa3_outcomes.py`, `tools/harness/sandbox.py`). Did not open `docs/process/reviews/research_codebase_review_claude.md` or `docs/process/reviews/sa3_amendment5_review_claude.md`. Computed no predictor-outcome association on study data.

**Verdict: sound architecture; hold Step 3 (Phase B) / Step 4 / Step 7 until the cross-document contradictions with Amendment 5 Rev. 2, the §4/§11 reachability leftovers, and the §5/§7/§11 verification gaps are resolved.**

---

## 1. Blockers: Cross-Document and Internal Contradictions

1. **Confirmatory architecture diverges between `research_codebase_spec.md` and `docs/sa3_amendment5_draft.md` (Revision 2).**
   While commit `3f0b7f6` aligned §3 Step 4, §5, and §6 items `c` and `e` on keeping the frozen universe and frozen random streams in the confirmatory run, commit `e929a84` (`sa3_amendment5_draft.md` Rev. 2) introduced a sharper conflict that `research_codebase_spec.md` has not yet absorbed:
   - `research_codebase_spec.md` §3 Step 2 (line 64) still states: *"SA3 Amendment 5: scoring moves from 'exactly as frozen at `edc5c53`' to the stored tables."*
   - `research_codebase_spec.md` §6 item `k` (line 150) keeps Holm and "not robust" governed by `text` with *"the code is fixed (defect log 42, 43, 47)"* inside the main confirmatory build.
   - `docs/sa3_amendment5_draft.md` Rev. 2 instead names `8fb7fe0` (not `edc5c53`) as the reference for `tools/sa3_score.py` and `tools/sa3_outcomes.py` (§1 lines 33–34), decrees *"The confirmatory run is the reference code, run once, unchanged. Not a rewrite, not the stored tables"* (§2 line 40), and keeps defects 42 and 43 **as coded** in the confirmatory run with corrected readings printed beside them (§3 line 61, §4 lines 67–68).
   - **Action needed:** Update `research_codebase_spec.md` §3 (Steps 2–7) and §6 item `k` to state clearly whether stored tables are the parallel verification/sensitivity path (`sa3_amendment5_draft.md` §9 layer 3) or the confirmatory engine, and update the baseline commit from `edc5c53` to `8fb7fe0` for `sa3_score.py` and `sa3_outcomes.py`.

2. **Internal contradiction on reachability (`item e`) between §4, §6, and §11.**
   - §4 (lines 94–100) still lists *"every universe file is one the history could record a touch for"* under **"Invariants, failing the build"**, while noting in the same bullet that `.gitattributes` switching vendoring off triggers it and *"the count of such files per repo is reported for a ruling (section 6, item e)."*
   - §11 (lines 198–200, 208) still reads *"Item e is applied in step 3, after the count"* and *"Nothing here is open"* (line 196).
   - Both conflict with §6 item `e` (line 144), `tables_spec.md` lines 64–65 & 82 (which already moved `history_can_touch = 0` to a data-card report, not a failing invariant), and `sa3_amendment5_draft.md` §6 (which runs `PU_reachable_universe` beside the frozen run and keeps two owner questions open).
   - **Action needed:** Separate §4 into (a) non-failing reachability accounting (`history_can_touch`) on the frozen universe and (b) a build-failing invariant enforced only on the `PU_reachable_universe` view, and update §11 and status line 3 (*"Nothing is built"* is stale with Steps 0–1 and `tables_spec.md` in PR #185).

3. **Step 3 `event` schema in §4 conflicts with "move, not rewrite" (`tables_spec.md` realization).**
   - `research_codebase_spec.md` §4 (line 90) keys `event` on `(unit commit, linking commit, path)`.
   - `docs/process/tables_spec.md` (lines 55, 67–68) documents that existing `sa3_outcomes` JSON files do not record which brought-in commit supplied a merge's inherited positive, forcing Phase A to drop `linking commit` from `event`'s key (`repo, sha, path`).
   - **Action needed:** Either restrict §4's `event` key to `(repo, unit commit, path)` for the moved-code tables and defer `(unit commit, linking commit, path)` strictly to the second independent derivation (`sa3_amendment5_draft.md` §9 / `research_codebase_spec.md` §11 #3), or clarify how Step 3 populates `linking commit` without violating Principle 8 (*"move before rewriting"*).

---

## 2. Methodological & Statistical Critique

4. **Control suite (§7) negative-control criterion has low power for small confound leakage and skips gate-level qualification.**
   - §7 (line 162) accepts the negative control if each property's effect on 20 seeds (800 files) falls *"within three standard errors of the same statistic computed from the manifest's expected labels."* Unlike `control_repo_spec.md` lines 205–206 (which enforces `3 SE` **and** `±0.03` on true-fix rank correlation), §7 sets no absolute bound on the expected-label check. At 20 seeds, `3 SE` corresponds to a ~99.7% null pass interval and has low statistical power to detect small-to-moderate confound leakage—the exact failure mode in defect log entry 28 (`+0.002` to `+0.006` `bauc` size leakage).
   - Furthermore, §7 tests primary `bauc` recovery on planted properties, **not** the qualification gates actually used in `tools/sa3_score.py`: `path_hash`, `dir_hash`, and `size_surrogate` (`fit_size_model` / `draw_surrogate`, lines 193–229, checked against `SURR_TOL = 0.005` at line 48). Without including the placebo/surrogate stage in §7 (including on directory-clustered control repos), regressions in parametric size-matching or directory clustering (cf. `blinding_spec.md` lines 51–55) go untested by the suite.
   - §7 lines 157–158 state *"each pass rule is simulated for its false-failure rate before it is used"*, which is missing from the pass criteria table.
   - **Recommendation:** Pair the `3 SE` gate with an explicit absolute tolerance on both expected labels and placebos (`SURR_TOL = 0.005`), add `placebo` gate checks to §7, and record the simulated false-failure and minimum-detectable-bias rates of each §7 threshold.

5. **Single-generator circularity on label-rule attenuation.**
   - As `sa3_amendment5_draft.md` (§8 lines 137–142) and `harness_report.md` (lines 80–83) note, the synthetic generator's assumed commit-convention mix already drops ~40–45% of a planted effect (`+0.138` on true fixes vs. `+0.077` on written-rule expected labels; `+0.075` Python / `+0.062` C pipeline).
   - Testing §7 against *expected labels* alone validates code faithfulness to the generator's label assumptions, not robustness across realistic label-convention regimes. Adding a sensitivity run in §7 varying silent-fix / `feature_with_ticket` / `jira_bare` proportions (or verifying `control_repo_spec` `tickets_for_everything` and `no_references` in the suite, not just as binary usability mutations) prevents overfitting validation to one unmeasured convention mix.

6. **Static-rule discipline for `item e` / `PU_reachable_universe` must generalize beyond `.gitattributes`.**
   - `sa3_amendment5_draft.md` §6 (line 106) improves over `research_codebase_spec.md` §4 line 99 by defining `PU_reachable_universe` strictly by rule (*"never by 'has no touch'"*), preventing catastrophic post-outcome selection bias from conditioning on zero post-cut activity.
   - Still, `tools/sa3_outcomes.py` (`universe` lines 63–89 vs. `touch` join lines 168–171) can produce ranked-but-unreachable files through mechanisms beyond `.gitattributes`: `git archive` vs. `history/*.db` path-normalization mismatches, symlinks/submodules, or non-first-parent commits when `merge_units = 0`. `file.history_can_touch` (`tables_spec.md` line 64) should explicitly audit *every* static path-filtering divergence between `laws_history` and `laws_units` / `git archive`, not only `.gitattributes` re-inclusion.

7. **Dual-build experiment (§11 #3) lacks blind fault-seeding controls and clean-run tie-breaking.**
   - §11 #3 (lines 202–206) builds Step 3 (`event`) and Step 5 (reading rule) independently with a second model, compares outputs on control repositories, and seeds known faults into one copy.
   - To make this informative as methodology (`STUDY_SCAFFOLD.md` line 28):
     1. Seed **one fault per copy alongside unmodified clean copies**, scored **blind** so both detection rate (hits) and false-alarm rate are measured rather than hit count alone;
     2. Run the equivalence comparison across **all mutations** in `control_repo_spec.md` (especially `merge_workflow`, `huge_import_merge`, `renames_after_snapshot`, `bot_merges`), not a single base repo;
     3. Define the **adjudication rule** beforehand when clean builds disagree on an underspecified boundary (e.g., Holm p-value ties, empty commit pools, case-insensitive link patterns as in defect 61).

---

## 3. Engineering, Reproducibility & Provenance Blind Spots

8. **Python I/O wrappers (§5) do not seal native libraries or subprocess internals.**
   - Wrapping `open`, `sqlite3.connect`, and `subprocess` in Python (§5 lines 110–114) will miss C-level SQLite sidecar/journal reads (`-wal`, `-shm`), `os.open` / `mmap` / `scandir`, C-extension library/cache reads (`numpy`, `scipy`, `tree_sitter_language_pack` grammar cache under `$HOME/.cache` noted in `tools/harness/sandbox.py:42-46`), and git's internal config/attribute reads (`.git/config`, `.git/info/attributes`, global/system gitconfig).
   - **Recommendation:** Enforce §5 isolation structurally at the OS boundary using the `bwrap` pattern already built in `tools/harness/sandbox.py` (binding **only** declared inputs read-only into `WORK`), or verify Python hooks with `sys.addaudithook` / `strace -e trace=file`.

9. **Canonical table hashing (§4) and derived `measure` missingness need exact specification.**
   - **Float canonicalization (§4 lines 77–80):** Python's `float.hex()` emits `'-0x0.0p+0'` for `-0.0` vs. `'0x0.0p+0'` for `+0.0`, and `NaN` values can carry distinct payloads/signs. Canonicalization (`tables_spec.md` line 35) should explicitly normalize `-0.0 -> 0.0` and forbid non-null `NaN` (mapping to `null`), with column schemas driving int-vs-real normalization.
   - **Derived predictor missingness (`tools/sa3_score.py:103, 132-143`):** §4 line 87 defines `absent_means` per measure and states derived predictors are rows built by named functions. In `sa3_score.py`, missingness semantics vary by formula: `amplified_cascading_flux` coerces missing/unparseable JSON to `0` (`line 103`), `state_pointers_alloc` propagates `NaN` via addition (`line 135`), `risk_safety_nonzero` maps `NaN -> NaN` (`line 140`), and `risk_safety_among_nonzero` converts `<= 0` to `NaN` (`line 141`), which subsequently causes `design_for` (`lines 177-180, 374`) to drop rows and **recompute size bands** (`S.bands`). Before Phase B (`measure` with derived rows), each derived function must specify exact null propagation so band membership does not drift silently.

10. **Provenance gaps on prebuilt inputs (`history/*.db`, `meta_sa3/*.db`, `sa3_nesting/*.json`, `linguist` lists).**
    - §4 (`repo`, line 84) checks the clone's tip hash, while `tools/sa3_outcomes.py` and `tools/sa3_score.py` consume prebuilt `history/{repo}.db`, `meta_sa3/{repo}.db`, `sa3_scans/{repo}.json`, `sa3_nesting/{repo}.json`, and cached GitHub Linguist lists (`vendor.yml`, `documentation.yml` in `tools/harness/sandbox.py:42, 80`).
    - Two `history/*.db` or `meta_sa3/*.db` builds over the same clone tip can differ silently in build flags or cached `linguist` versions unless `repo`/`index.json` records the SHA-256 of the Linguist YAML files, `history` walk parameters (`merge_units`), and `meta` harvest flags (`with_merges`, `sa3_links`) rather than only opaque DB file hashes.

---

## Summary Checklist Before Step 3 (Phase B) / Step 4

1. Reconcile `research_codebase_spec.md` (§3 Steps 2–7, §6 item `k`, §11, and status line 3) with `docs/sa3_amendment5_draft.md` Revision 2 (`8fb7fe0` reference, confirmatory unchanged vs. parallel verification).
2. Move `history_can_touch` out of §4's build-failing invariant list onto the `PU_reachable_universe` view, covering all static path/archive/history mismatches.
3. Align §4's `event` primary key with `tables_spec.md` Phase A vs. the Step 3/§11 #3 independent `event` derivation.
4. Add placebo/size-surrogate qualification (`SURR_TOL = 0.005`) and an explicit absolute bias ceiling to §7's negative control, plus convention-mix sensitivity.
5. Enforce §5 input declaration via `bwrap` (not Python `open` hooks alone), normalize `-0.0`/`NaN` in canonical hashing, pin Linguist/prebuilt-DB build metadata, and formalize blind single-fault seeding + tie-breaking in §11 #3.
