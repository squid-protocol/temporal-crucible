#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The fixed texts of the scoring job (docs/process/scoring_step_spec.md, Revision 2): the sentences of
section 6 (owner ruling 1 of 2026-11-15), the label of Amendment 5 section 8, the paragraphs the report always
carries, the stopping codes with what each means, and the plan the owner reads before pressing Enter.

Nothing here is computed. Every word the job prints or writes that is not a validated value comes from this
file. These constants are reviewed before the pinned commit C (section 6, last line).
"""
from __future__ import annotations

# ======================================================================= section 6: if a check fails (ruling 1)
# One constant per row of the table, in the table's order. Each is printed (terminal and report) exactly when its
# case happens, and no other is.
SENTENCES = {
    "run2_placebo": ("run-2's placebo is not bytes_equal: the route stops here; nothing has been scored."),
    "before_score": "A check before the score failed: the job stopped; nothing has been scored.",
    "rehearsal": "The loader rehearsal failed: the job stopped; nothing has been scored.",
    "gate": ("The placebo gate is the `valid` field of the sealed placebo file, fixed since 2026-11-14; it cannot "
             "newly fail in this run."),
    "label_check": ("The result stands (Amendment 5 sections 2 and 9). The inputs the two routes read were not "
                    "shown equal. The cell map is still printed."),
    "r_only": ("The result stands (Amendment 5 sections 2 and 9). Cells of class R (the shared random stream: the "
               "permutation spreads and p-values, the matched control and what is read from it) differ; every W "
               "and D cell is equal. \"Defect-specific\" against \"tracks activity\" is unverified in this run."),
    "w_or_d": ("The result stands as the registered output. The check did not confirm this run: a cell of class W "
               "or D differs. No hypothesis is called confirmatory until a decoy investigation, written up and "
               "dated, places the cause."),
    # owner ruling of 2026-11-15 (after the build review): a check that cannot be computed is "not confirmed"
    "not_computed": ("The result stands as the registered output. The check could not be computed: {code}. The "
                     "check did not confirm this run: no hypothesis is called confirmatory until a decoy "
                     "investigation, written up and dated, places the cause."),
    "part_failed": ("A corrected reading or a variant failed to run; it is reported \"failed\" with its code. A "
                    "later run is dated and labelled later. It never blocks the report."),
}

# what the ledger holds when a run stops (build review M4): chosen from the ledger read at that moment, never from
# the step number. A section 6 row sentence ("nothing has been scored") is printed only with "empty".
LEDGER_STATE = {
    "empty": "The ledger has no entry: a new attempt is still the first scoring.",
    "open": ("The ledger holds a start with no completion, and no result was recorded. If that run's clone holds a "
             "result (<protected>/clone/docs/sa3_result.json), run --resume with that protected directory: it "
             "adopts the result. Otherwise a second start needs --rerun REASON."),
    "completed": ("The ledger records a completed score: the result is recorded and is never scored again. Nothing "
                  "here changed the published result or report; run --resume to finish the report."),
}
# step 10 when the result exists (build review B1): fixed lines
RESULT_LINES = {
    "where": "the result is recorded in the ledger; it is in the protected directory at {path}",
    "publish_failed": ("the result exists and is recorded; it could not be published; run --resume (it publishes "
                       "the result from the clone)"),
    "interrupted": ("interrupted after the result was recorded: the ledger holds started and completed; run --resume "
                    "with the receipt to publish what is missing and finish the report"),
    "stage_failed": ("the score stage ended failed ({code}) after the reference had written its result; the result "
                     "is recorded and published as written"),
    "stage_modules": ("the score stage reported modules_differ: the result's code is not shown to be the pinned "
                      "commit's (owner ruling open); the result is recorded and published as written"),
}


def sentence(key: str, code: str | None = None) -> str:
    """a sentence of section 6 as printed; only "not_computed" carries a value: a code of the fixed lists"""
    s = SENTENCES[key]
    return s.format(code=code) if key == "not_computed" else s


# the label's added clause when "w_or_d" or "not_computed" applies (section 6: 'the label gains "the check did not confirm this
# run"')
LABEL_ADDITION = "the check did not confirm this run"

# ======================================================================= Amendment 5 section 8: the label
LABEL = ("pre-registered design; point estimates partly seen before scoring; scoring code corrected afterwards in "
         "four listed places; readings given as coded and as corrected.")

TEST_NAMES = {"struct_branch": "SA3-B", "risk_safety_score": "SA3-C", "amplified_cascading_flux": "SA3-D",
              "in_degree": "SA3-A"}

GATE_WORDS = {True: "valid (the gate passed when the placebo file was made)",
              False: "not valid: NO FINDING may be reported (the gate failed when the placebo file was made)"}

# ======================================================================= paragraphs the report always carries
PARAGRAPHS = {
    "what_seen": ("What was seen and when: Amendment 4 of the registration (docs/sa3_registration.md, \"What "
                  "happened\"), unchanged. The point estimates were partly seen before scoring."),
    "recovery": ("How much of a planted effect the pipeline recovers on generated repositories "
                 "(docs/process/harness_report.md, 20 seeds per case; Amendment 5 section 8): with an effect of "
                 "+0.138 on true fixes, the labels the written rule gives carry +0.077 and the Python pipeline "
                 "reports +0.075; in generated C, +0.062 against +0.081. With no effect planted every predictor "
                 "reads zero. These are properties of generated repositories. The share lost in the label rule "
                 "depends on the mix of commit conventions the generator was given; it has not been measured on "
                 "real repositories and is not a correction factor."),
    "power": ("Power: docs/sa3_power.md (sealed). A null on the primary outcome is read against it."),
    "counts": ("The counts published before scoring: docs/sa3_prescoring_counts.md, and the tracker-key count of "
               "the owner-run preparation job (run-2's owner_report.md, section 1)."),
    "blind": ("The check itself was tested blind (docs/process/blind_test_run1/RESULT.md): eight faults of eight "
              "kinds and eight clean copies on a decoy study; every fault flagged, no clean copy flagged. Eight "
              "and eight give no detection or false-alarm rate, and a fault of a kind nobody thought of is the "
              "case it cannot speak to."),
    "match": ("A full match of the cell map is agreement between two routes and one description, not evidence "
              "that the code does what the registration says (docs/process/comparison_scorer_spec.md, \"What it "
              "is for\"): both routes share the statistics module, numpy and scipy, and the comparison loop was "
              "transcribed from the reference."),
    "raw_words": ("sa3_result.json is the reference's file byte for byte. It holds the words \"supported\" and "
                  "\"contradicted\" for every summary of every cut (defect log 47). Outside the three "
                  "confirmatory tests those words are not readings: read them as \"above zero\" and \"below "
                  "zero\" at an unadjusted 95%."),
    "variants_intro": ("None of these replaces the confirmatory reading. Every one is reported, in this order, "
                       "whatever it shows."),
    "later": "run later, on {date}",
}

# ======================================================================= stopping codes (terminal and report)
# step -> what it checks. A failure in steps 1 to 8 stops the job with nothing scored and no ledger entry.
STEPS = {
    1: "ledger, pin, run-2's report, seal verify",
    2: "fresh clone at the commit",
    3: "sealed files in the clone against the seal",
    4: "copies of the inputs, each original against the seal",
    5: "predictor-side tables against their committed hashes",
    6: "loader rehearsal on every ok repo",
    7: "the reference lock",
    8: "seal verify --after-lock; the clone's status",
    9: "the reference score, once",
    10: "result published, receipt, then its shape checked",
    11: "label tables and the label-side input check",
    12: "the comparison scorer and the cell map",
    13: "corrected readings, named streams, harvest variants",
    14: "the report",
}

STOP_CODES = {
    # before anything: the ledger and the command line
    "ledger_has_entry": "the ledger already has an entry: the job refuses whatever directory is named (only "
                        "--resume, or --rerun after a start with no completion)",
    "ledger_completed": "the ledger records a completed score: no second start, ever; only --resume",
    "rerun_needs_start": "--rerun is allowed only after a start with no completion",
    "ledger_unreadable": "the ledger cannot be read as the job writes it",
    "ledger_locked": "another scoring job holds the ledger's lock: one launcher at a time",
    "ledger_changed": "the ledger changed between the start of this run and the score: nothing was started",
    "result_exists_resume": ("the open start's clone holds a result: run --resume with that protected directory, "
                             "never --rerun"),
    "production_needs_production_ledger": ("a run on the production study and pool uses the production ledger and "
                                           "refuses OWNER_JOB_TEST_PROTECTED_ROOT; any other study needs that test "
                                           "root"),
    # step 1
    "head_differs": "HEAD of the checkout is not the commit given with --commit",
    "checkout_dirty": "the checkout has an untracked, modified or ignored file other than __pycache__",
    "tag_differs": "the tag sa3-score-C does not point at the commit",
    "run2_not_pass": "run-2's owner_report.json beside the seal is not PASS on the same target",
    "run2_placebo": "run-2's placebo verdict is not bytes_equal",
    "seal_not_verified": "seal.py verify against run-2's seal did not print VERIFIED",
    "git_error": "a git command on the host failed",
    # step 2
    "clone_failed": "the fresh clone or its checkout failed",
    "clone_not_clean": "the clone's .git is not a directory, its HEAD is not the commit, its status is not clean, "
                       "or an object file is hard-linked",
    # step 3
    "sealed_file_differs": "a sealed file in the clone does not have the seal's SHA-256",
    # step 4
    "copy_failed": "the owner job's copy stage failed for a repo",
    "input_differs": "an input does not match the seal (an original, a clone's HEAD or GitHub's lists)",
    "copy_unusable": "a database copy did not pass its quick check or kept a side file",
    # step 5
    "predictor_check_missing": "the committed predictor-side check or the deviation table is missing or malformed",
    "predictor_check_not_equal": "the committed predictor-side check is not all equal",
    "table_hash_differs": "a predictor-side table does not have its committed hash",
    # step 6
    "rehearsal_failed": "the reference loader failed on a repo",
    # step 7, 8
    "lock_refused": "the reference lock refused (exit 2)",
    "lock_failed": "the lock stage did not complete",
    "after_lock_differs": "seal.py verify --after-lock did not print VERIFIED",
    "lock_commit_differs": "the lock's sealed_at_commit is not the commit",
    "clone_status_after_lock": "the clone's status after lock is not exactly docs/sa3_lock.json",
    "modules_differ": "a stage loaded a module whose bytes are not git ls-tree's for the commit",
    # step 9, 10 (a start is recorded: a second start needs --rerun REASON)
    "locked": "the reference score refused (exit 2, LOCKED)",
    "score_crashed": "the reference score stopped with an error",
    "score_timeout": "the reference score did not finish within a day",
    "no_result": "the reference score wrote no result",
    "result_shape_unexpected": "the result was published, but it does not have the reference's expected shape "
                               "(its position is named in the report); the parts after it may fail on it",
    "result_exists": "a result file existed in the clone before the score",
    "result_truncated": "the result file exists but does not parse as a JSON object (a write cut short)",
    "interrupted": "the run was interrupted during the score, before any result file existed",
    "publish_failed": "the result is recorded but could not be copied to the public directory: run --resume",
    # anywhere
    "invalid_report_value": "a value did not fit its fixed shape (the field is named on the terminal)",
    "launcher_error": "the launcher itself failed (its traceback is in the protected directory)",
    # resume
    "nothing_to_resume": "--resume needs a completed score in the ledger",
    "receipt_differs": "the result's SHA-256 is not the receipt's (or the ledger's)",
}

# codes a part after the score ends with, besides a stage's own exception code
PART_CODES = ("not_run", "dependency_failed", "code_differs", "invalid_value", "timeout", "no_result",
              "sandbox_refused")


def plan(target: str, study: str, pool: str, protected: str, out: str, ledger: str, commit: str) -> str:
    return "\n".join([
        "The SA3 scoring job (docs/process/scoring_step_spec.md, Revision 2). It runs the reference `score` once.",
        f"Target: {target}. Commit: {commit} (the checkout must be at it, clean, and the tag sa3-score-C on it).",
        "Every stage runs from a fresh clone of the repository at that commit, made inside the protected directory,",
        "in the read-only sandbox. It binds, read-only:",
        f"  the study directory {study}: per repo the history, the scan database, its sidecar, the link harvest,",
        "  the outcome file and the nesting file (databases are copied into the protected directory first and",
        "  each original hashed against run-2's seal)",
        f"  the clones under {pool}, GitHub's two lists, the predictor-side tables named by the commit",
        f"It writes the protected directory {protected} (mode 700), the ledger {ledger}",
        f"(appended, on this machine), and the public directory {out}.",
        "Steps 1 to 8 stop on any failure with nothing scored. Step 9 records a start in the ledger, then runs the",
        "reference score once (up to a day). Step 10 publishes the result byte for byte and prints a receipt line:",
        "keep it somewhere other than this machine. Steps 11 to 14 never stop the report.",
        "Run this inside tmux: the sandbox dies with its terminal.",
        "Press Enter to start. Anything else, or end of input, stops it."])
