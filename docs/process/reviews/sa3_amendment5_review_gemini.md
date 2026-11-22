# SA3 Amendment 5 (Revision 2) — independent methodology review

**Reviewer:** Gemini (independent review on PR #185 / `sa3/build`, commit `9a28de3`), 2026-11-14.
**Scope & independence:** Reviewed `docs/sa3_amendment5_draft.md` (Revision 2) against `docs/sa3_registration.md`, `docs/sa3_registration_consolidated.md`, `docs/process/research_codebase_spec.md` (Rev. 3), `docs/process/tables_spec.md`, `docs/STUDY_DEFECT_LOG.md`, and code diffs/sources (`git diff edc5c53..8fb7fe0`, `tools/sa3_score.py`, `tools/sa3_outcomes.py`, `tools/hist_meta.py`, `tools/laws_units.py`). Did not open `docs/process/reviews/sa3_amendment5_review_claude.md` or `docs/process/reviews/research_codebase_review_claude.md`. Computed no predictor-outcome association on study data.

**Verdict: sound core strategy; hold adoption until the sealing/integrity gap for running `8fb7fe0` "unchanged", the §5 regex/revert specification discrepancies, the `PU_generic_dirs_restored` / `PU_unreachable_made_reachable` operational gaps, and §1/§7/§9 completeness gaps are fixed.**

---

## 1. Blockers

1. **Running `8fb7fe0` "unchanged" (§2–§3) leaves the seal and non-number-moving protections (defects 44, 57, 60) unprovided.**
   - §2 (line 40) commits to *"the reference code, run once, unchanged"*, and §3 (line 49) pins `Code` to the reference contents of §1 (`8fb7fe0` for `tools/sa3_score.py` and `tools/sa3_outcomes.py`, `edc5c53` for `tools/sa3_stats.py` and `tools/mod1_lift.py`).
   - However, Revision 2 **dropped Revision 1's table of non-number-moving fixes** (defects 44, 57, 60) without specifying an external harness/wrapper for the confirmatory run:
     - `8fb7fe0`'s `stage_lock()` (`tools/sa3_score.py:36-38, 511-522`) seals only **9 files**—omitting `history/*.db`, `meta_sa3/*.db`, `sa3_scans/*`, `sa3_nesting/*`, `laws_units.py`, `hist_meta.py`, `hist_fixlabel.py`, `laws_history.py`, `_engine.py`, and the cached Linguist lists (defect 44)—and fails open outside a git checkout (`defect 57`).
     - `8fb7fe0`'s `stage_score()` (`lines 344-352`) verifies `docs/sa3_lock.json` against `SEALED`, which includes `docs/sa3_registration_consolidated.md` and `docs/sa3_placebo.json`. Revision 2 does not state (a) what tamper-evident seal covers Amendment 5, the missing data/code inputs (defect 44), and the parallel verification artifacts, nor (b) whether `docs/sa3_registration_consolidated.md` is updated *before* or *after* `stage_lock()` runs on `8fb7fe0`.
   - **Action needed:** Specify an external seal (`research_codebase_spec.md` §5 / `tools/harness/sandbox.py` `bwrap` pattern or a sealed wrapper runner) that hashes all inputs, all rule-defining code files, `8fb7fe0` reference scripts, and Amendment 5 **without** altering `8fb7fe0` scoring logic.

2. **§1 & §7 miss the cross-repo RNG coupling of `silent()` changes in `8fb7fe0`.**
   - §1 (lines 26–32) discloses that narrowing `silent()` in `8fb7fe0` un-silenced three count measures in 14 repo cells (defect 46) and notes this shifts the shared random stream relative to `edc5c53`. §7 item 1 (line 122) then asks only: *"Of defect 46's 14 cells, how many are confirmatory, and which repos."*
   - In `tools/sa3_score.py` (`lines 361, 375, 385, 406`), `stage_score()` creates **one** `rng = np.random.default_rng(SEED)` before looping over repos, outcomes, predictors (`N_PERMS = 200` `block_permute` calls per non-silent cell at `line 385`), and `control_effects(d, ..., rng)` (`line 406`). Because `control_effects` feeds `minus_control`, which gates the confirmatory reading (`"supported, defect-specific"` vs. `"supported, but tracks activity, not defects"` at `lines 440-441`), **any** of the 14 un-silenced HP or KW cells (including **secondary** or **KW** cells!) shifts `rng` for all subsequent repos' `control_effects` and permutations.
   - §1 should also state explicitly that `tools/sa3_outcomes.py`'s `8fb7fe0` change (`lo = max(f["cut"], snap_ct)` at `lines 164-166`) does **not** move any of the 15 drawn confirmatory repos (verified pre-scoring from `sa3_scans` / `mod1_lift`, not only assumed from Amendment 4's note on the earlier eight).
   - **Action needed:** Expand §7 item 1 to publish **all 14** un-silenced `(repo, outcome, measure)` cells (confirmatory and non-confirmatory) plus the pre-scoring verification that `lo == f["cut"]` on all 15 drawn repos.

---

## 2. Specification Accuracy Gaps in §5 ("What the code counts as a fix reference, stated exactly")

§5 (lines 76–96) aims to make the consolidated text exact *"so that a second builder would write the same code"* (`research_codebase_spec.md` §11 #3). Compared directly against `tools/hist_meta.py` (`lines 37–83`) and `tools/sa3_outcomes.py` (`lines 178–272`), §5 has four concrete discrepancies that would cause an independent second builder to diverge:

3. **Regex syntax for `issue_fix_sa3` (`tools/hist_meta.py:45-51` vs. §5 lines 81–84).**
   - `hist_meta.py:46` allows an optional `#` after `bug` and `PR` (`\bbug\s*#?|\bPR\s*#?`), not only `bug N` and `PR N`.
   - `hist_meta.py:47` permits an optional colon (`:?`) after the fix verb **only** for the tracker-key branch (`resolve[sd]?\s*:?\s+...`), whereas line 46 (`#N`, `GH-N`, `bug #?N`, `bpo-N`, `PR #?N`) does **not** allow a colon. §5 line 81 groups all forms after a single colon prose separator and omits this asymmetry.
   - `hist_meta.py:47` bounds tracker keys to **1 initial letter + 1–15 `[A-Z0-9_]` characters (2–16 chars total)** before `-` and **1–7 digits** (`\d{1,7}`) after `-` (with `re.I | re.M` also making `GnuPG-bug-id:` and `Fixes: <sha>` case-insensitive); §5 line 84 omits the `1–7` digit bound.

4. **Trailer scope and non-empty value rule (`tools/hist_meta.py:54-55, 81-82` vs. §5 line 87).**
   - §5 line 87 says *"Any `Fixes:`, `Bug:` or `Reported-by:` trailer, whatever follows the colon."*
   - In `hist_meta.py:81`, `RX["trailer"].finditer(body)` scans **only the commit body (`body`), never `subject`**, matches case-insensitively (`re.I | re.M`), and requires at least one character after `:\s*` (`(.+)`). (Note also `^Fixes:\s*([0-9a-f]{7,40})\b` in `issue_fix_sa3` runs on `subject + "\n" + body`.)

5. **Revert resolution, merge-owner timestamp, and intra-merge exclusion (`tools/hist_meta.py:38, 66-67` & `tools/sa3_outcomes.py:193-217` vs. §5 lines 89–90).**
   - A `Revert "..."` commit with no `This reverts commit <sha>`, a prefix `<7` hex chars, an ambiguous prefix, or an unreachable target (`resolve` returns `None`) does **not** qualify for `HP`, though it **does** qualify for `HP_allreverts` (`sa3_outcomes.py:213-216`) and qualifies `HP` if its own text carries a fix reference or CVE.
   - For an off-chain commit owned by a merge, `at_or_before_cut` (`sa3_outcomes.py:201-204`) checks the **owning merge's `ct`** (`owner.get(target, target)`), not the target commit's own `ct`; and a merge never inherits a revert targeting a commit brought in by the **same** merge (`tgt not in exclude` at `line 215`).

6. **Bot-authored commits in tainted merges (`tools/sa3_outcomes.py:234-243` vs. §5 lines 91–92).**
   - §5 should state explicitly that: (a) merges bringing in `> 50` commits (`MAX_BROUGHT = 50`) are **tainted** and cannot inherit; and (b) while bot-authored brought-in commits cannot *supply* an inherited link (`not topo[k][2]` at `line 241`), a bot-authored brought-in commit carrying a link or fix wording still **taints** the merge (`line 242` / `265-270`).

---

## 3. Sensitivities (§6), Verification (§9), and Reporting (§4, §8) Gaps

7. **`PU_generic_dirs_restored` (§6 line 108) must account for missing engine scan data.**
   - `PU_generic_dirs_restored` states: *"files excluded only by one of these GitHub patterns are ranked again: `(^|/)cache/`, `(^|/)dist/`, `(^|/)[Ee]xtern(als?)?/`, `(^|/)env/`."*
   - Wait: `tools/sa3_outcomes.py:74-79` populates `files` from `{repo}_master.db`'s `file_data` table. If the frozen engine skipped any directory matching `cache/`, `dist/`, `extern*/`, or `env/` at scan time (similar to the engine directory skips noted in PR #185), restored files will have **no `total_loc` or structural predictor rows** in `{repo}_master.db` (and `sa3_score.py:107` asserts `(loc > 0).all()` and `not np.isnan(loc).any()`!).
   - **Action needed:** State explicitly whether `PU_generic_dirs_restored` restores only already-scanned files present in `{repo}_master.db` (and drops unscanned ones) or requires scanning the restored paths under `engine-f71181aae7`, and report in §7 item 4 how many restored files per repo already have scan rows.

8. **`PU_unreachable_made_reachable` (§6 line 107) cannot be built from `history/*.db` alone.**
   - `sa3_outcomes.py:168-171` reads touches from prebuilt `history/{repo}.db`, which was harvested with `laws_history`'s own exclusions (without snapshot `.gitattributes` overrides). Building `PU_unreachable_made_reachable` therefore requires re-extracting git touches for those `.gitattributes`-re-included paths from the clone, not just filtering `history/*.db`. §6 should state this dependency explicitly.

9. **Closed sensitivity list (§6 line 98) omits Amendment 4's existing sensitivities.**
   - §6 states *"the list is closed by this amendment"*, yet omits `PU_django_circuitpython_removed`, `PU_mediawiki_freebsd_removed`, `go_django_removed`, and `S1`–`S9` already in Amendment 4 (`tools/sa3_score.py:483-490`). Clarify that §6 **adds** the 10 listed cuts to Amendment 4's existing list, and together they are closed.

10. **§9 Layer 2 & Layer 3 verification holes.**
    - **Layer 2 (`lines 151-152`):** Running `8fb7fe0`'s `stage_placebo()` directly overwrites `docs/sa3_placebo.json` in-place (`tools/sa3_score.py:285`), and byte-for-byte JSON equality across BLAS/NumPy updates is fragile for `fit_size_model` floating-point outputs (`lines 204, 211`). Specify running Layer 2 inside a sandbox (`tools/harness/sandbox.py`) against the pinned environment and normalizing/tolerance-checking float diffs if BLAS differs.
    - **Layer 3 (`lines 153-158`):** *"equal / not equal"* per cell requires an explicit numerical tolerance rule for derived/floating-point outputs; and the *"five one-line faults"* meta-test lacks **clean unmodified control copies judged blind** alongside single-fault copies (`STUDY_SCAFFOLD.md:28`), without which false-alarm rates are unmeasured. Also note `docs/process/tables_spec.md` (lines 52, 67–68) currently omits derived `measure` rows and `linking commit` in Phase A, so Layer 3 depends on Phase B defining exact null-propagation for `sa3_score.py:103, 132-143`.

11. **Minor reporting & self-verification fixes (§4, §8).**
    - **§4 line 67:** Still leaves *"On the reviewer's truth table of 729 input combinations (not re-run by the author)"* unverified; verify the `3^6 = 729` Holm truth table directly in Python (`sa3_score.py:424-438`) before adopting Amendment 5.
    - **§8 line 133:** Pin `N` explicitly (e.g., 4 reading/comparison corrections in §4, distinct from `PU_` sensitivities) in `"scoring code corrected afterwards in N listed places"`.
