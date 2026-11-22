#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The fixed shapes of the scoring job (docs/process/scoring_step_spec.md section 4: "through a validator of fixed
shapes, as for the owner job"), and the shape check of the reference's result file.

The checker is tools/owner/report.py's (`check`, `leaf`, `ReportError`; imported by file, not edited), extended
with this job's word lists and four kinds of its own:

  ("opt", S)     null, or a value of shape S
  "codepath"     a file path of a module a stage loaded: tools/<...>.py, and in the commit's `git ls-tree`
  "cellpos"      one element of a cell's position: a repo name of the marginals file, a word of the result's
                 fixed vocabulary, or a summary key built from fixed words
  "reason"       the owner's --rerun reason: letters, digits, spaces and . , ; : ( ) - / only, 1 to 200 characters

Every other leaf is report.py's (counts, times, yes/no, reals, 64-hex hashes, 40-hex only where the launcher
computed it from git or the commit itself, repo names from the marginals file). A value that does not fit raises
`ReportError("invalid report value: <field>")`: the field's schema path, never the value, never a key.
"""
from __future__ import annotations

import importlib.util
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent


def _owner(name: str):
    key = f"tools_owner_{name}"
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, TOOLS / "owner" / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return sys.modules[key]


RP = _owner("report")
ReportError = RP.ReportError
TX = None                                     # texts.py, set by _texts()


def _texts():
    global TX
    if TX is None:
        key = "tools_scoring_texts"
        if key not in sys.modules:
            spec = importlib.util.spec_from_file_location(key, HERE / "texts.py")
            mod = importlib.util.module_from_spec(spec)
            sys.modules[key] = mod
            spec.loader.exec_module(mod)
        TX = sys.modules[key]
    return TX


# ------------------------------------------------------------------------------------------- fixed vocabulary
OUTCOMES = ("HP", "HP_allreverts", "HP_revert", "HP_cve", "HP_fixref", "KW")
PREDICTORS = (
    "in_degree", "in_degree_per_loc", "out_degree", "pagerank_score", "betweenness_score", "struct_branch",
    "struct_branch_per_loc", "state_danger", "state_pointers_alloc", "def_safety", "state_flux", "nest_max",
    "nest_mean", "risk_safety_score", "risk_tech_debt", "risk_cognitive_load", "risk_state_flux", "risk_concurrency",
    "risk_safety_nonzero", "risk_safety_among_nonzero", "amplified_cascading_flux",
    "amplified_cascading_flux_per_loc", "state_heat_triggers")
PRIMARIES = ("in_degree", "struct_branch", "risk_safety_score", "amplified_cascading_flux")
CONFIRMATORY = ("struct_branch", "risk_safety_score", "amplified_cascading_flux")
STATS = ("bauc", "residual", "minus_surrogate", "S4_replaces", "S6_sauc_minus", "S7_tight", "S9_logistic_z",
         "minus_control", "minus_churn_any")
CUTS = ("all_drawn", "earlier_eight", "PU_django_circuitpython_removed", "PU_mediawiki_freebsd_removed",
        "S1_new_languages_removed", "S2_merge_workflow_removed", "S3_full_window", "go_django_removed", "C_family",
        "managed")
READING_WORDS = ("supported", "contradicted", "not detected", "not fitted", "not fitted (fewer than five repos)")
TEST_WORDS = ("supported, defect-specific", "supported, but tracks activity, not defects",
              "not robust to the statistic", "not detected (Holm: an earlier test in the family failed)",
              "contradicted", "not detected", "not fitted", "NO FINDING: the placebo gate failed")
EXPLORATORY_WORDS = ("positive", "negative", "not detected", "not fitted")
CELL_STATUS = ("ok", "instrument silent", "under pair floor")
ALLREVERTS_SENTENCE = "tracks reverted changes, not fixes"
UNAVAILABLE = {"dampened_flux": "named as a D secondary in the registration; the pinned engine emits no such value"}
NOT_RUN = {"S5": "tree-wide commits left in", "S8": "positives followed through renames",
           "nest_*": "Racket not measured; see docs for parse-error rates"}
SUMMARY_KEY = re.compile("(" + "|".join(OUTCOMES) + r")\|(" + "|".join(PREDICTORS) + r")\|(" + "|".join(STATS)
                         + r")\|(" + "|".join(CUTS) + ")")
ENGINE = re.compile(r"[0-9a-f]{7,40}")     # the scan sidecar's engine pin (sa3_scan.ENGINE_SHA: 40 hex)
DIRNAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
CODEPATH = re.compile(r"tools/[A-Za-z0-9_][A-Za-z0-9_/.-]{0,120}\.py")
REASON = re.compile(r"[A-Za-z0-9 .,;:()/-]{1,200}")
SAME_WORDS = ("same", "reading depends on a rule corrected after the estimates were partly seen")
VARIANT_WORDS = ("above zero", "below zero", "not detected", "not fitted (fewer than three repos)")
VARIANT_NAMES = ("PU_named_streams", "PU_tracker_keys_case_sensitive", "PU_late_revert_ticket_dropped")
VARIANT_REASONS = ("no row deleted: the frozen file stands",
                   "the builder does not reproduce the frozen file from the unmodified copy: the frozen file stands",
                   "rebuilt")
CELL_SECTIONS = ("study", "control", "valid", "unavailable", "repos", "tests", "sealed", "engine", "not_run",
                 "side_counts", "random_effects", "summaries", "n", "outcomes", "specificity") + OUTCOMES + PREDICTORS
STEP_NAMES = ("ledger", "pin", "run2_report", "seal_verify", "clone", "sealed_files", "seal_inputs", "copy",
              "tables", "rehearse", "lock", "after_lock", "score", "publish", "result_shape", "labels", "compare", "readings",
              "named", "hv_prepare", "hv_build", "variant", "report")
LEDGER_EVENTS = ("started", "completed", "stopped", "resume")
ATTEMPT_EVENTS = ("attempt_started", "attempt_ended")
MODES = ("score", "resume")


def words() -> dict:
    TX = _texts()
    return {
        "status": ("ok", "failed", "not_run"),
        "code": tuple(TX.STOP_CODES) + RP.STAGE_CODES + TX.PART_CODES + ("none",),
        "step_name": STEP_NAMES, "target": RP.TARGETS, "ledger_event": LEDGER_EVENTS,
        "attempt_event": ATTEMPT_EVENTS, "mode": MODES, "reading": READING_WORDS, "test_word": TEST_WORDS,
        "exploratory_word": EXPLORATORY_WORDS, "same": SAME_WORDS, "variant_word": VARIANT_WORDS,
        "variant_name": VARIANT_NAMES, "variant_reason": VARIANT_REASONS, "outcome": OUTCOMES,
        "primary": PRIMARIES, "confirmatory": CONFIRMATORY, "class": ("W", "D", "R"),
        "baseline": ("the frozen run", "PU_named_streams"), "scored": ("scored",),
        "build_status": RP.BUILD_STATUSES, "sentence": tuple(TX.SENTENCES), "placebo_verdict": RP.PLACEBO_VERDICTS,
        "test_word_or_level": ("above zero", "below zero", "not detected", "not fitted"),
        "part": ("labels", "compare", "readings", "named", "hv_prepare", "PU_tracker_keys_case_sensitive",
                 "PU_late_revert_ticket_dropped"),
        "tag": ("sa3-score-C",), "result_shape": ("expected", "unexpected"),
        "ledger_state": ("empty", "open", "completed"),
    }


@dataclass
class Vocab:
    repos: frozenset = frozenset()
    codepaths: frozenset = frozenset()
    commit: str = ""
    rp: object = field(default=None)

    def owner(self):
        return self.rp or RP.Vocab(repos=self.repos)


def leaf(kind: str, v, f: str, vocab: Vocab) -> None:
    nullable = kind.endswith("?")
    k = kind.rstrip("?")
    if v is None:
        if nullable:
            return
        raise ReportError(f)
    if k == "int":
        if not (isinstance(v, int) and not isinstance(v, bool) and abs(v) < 10 ** 9):
            raise ReportError(f)
        return
    if k.startswith("word:") and k[5:] in words():
        if not (isinstance(v, str) and v in words()[k[5:]]):
            raise ReportError(f)
        return
    if k == "codepath":
        if not (isinstance(v, str) and CODEPATH.fullmatch(v) and v in vocab.codepaths):
            raise ReportError(f)
        return
    if k == "commit":
        if not (isinstance(v, str) and RP.HEX40.fullmatch(v) and v == vocab.commit):
            raise ReportError(f)
        return
    if k == "anycommit":                       # a commit the launcher read from git itself
        if not (isinstance(v, str) and RP.HEX40.fullmatch(v)):
            raise ReportError(f)
        return
    if k == "cellpos":
        ok = isinstance(v, str) and (v in vocab.repos and RP.REPO_NAME.fullmatch(v) is not None
                                     or v in CELL_SECTIONS or SUMMARY_KEY.fullmatch(v) is not None)
        if not ok:
            raise ReportError(f)
        return
    if k == "shapepos":                         # a position in the result's schema: fixed words and <placeholders>
        ok = isinstance(v, str) and len(v) <= 300 and all(
            seg in SHAPE_WORDS or (seg.startswith("<") and seg.endswith(">") and seg[1:-1] in ("key", "repo"))
            for seg in v.replace("[]", "").split("."))
        if not ok:
            raise ReportError(f)
        return
    if k == "dirname":
        if not (isinstance(v, str) and DIRNAME.fullmatch(v)):
            raise ReportError(f)
        return
    if k == "reason":
        if not (isinstance(v, str) and REASON.fullmatch(v)):
            raise ReportError(f)
        return
    RP.leaf(kind, v, f, vocab.owner())


def check(schema, v, f: str, vocab: Vocab) -> None:
    """report.py's schema language plus ("opt", S)"""
    if isinstance(schema, str):
        leaf(schema, v, f, vocab)
    elif isinstance(schema, dict):
        if not isinstance(v, dict) or set(v) != set(schema):
            raise ReportError(f)
        for k, s in schema.items():
            check(s, v[k], f"{f}.{k}", vocab)
    elif schema[0] == "opt":
        if v is not None:
            check(schema[1], v, f, vocab)
    elif schema[0] == "map":
        _, kk, vs = schema
        if not isinstance(v, dict) or len(v) > 100000:
            raise ReportError(f)
        name = f"{f}.<{kk.split(':')[-1]}>"
        for k, x in v.items():
            leaf(kk, k, name, vocab)
            check(vs, x, name, vocab)
    elif schema[0] == "list":
        if not isinstance(v, list) or len(v) > 100000:
            raise ReportError(f)
        for x in v:
            check(schema[1], x, f"{f}[]", vocab)
    elif schema[0] == "pair":                   # a list of exactly two values of one shape
        if not isinstance(v, list) or len(v) != 2:
            raise ReportError(f)
        for x in v:
            check(schema[1], x, f"{f}[]", vocab)
    else:
        raise AssertionError(schema)


# ------------------------------------------------------------------------------------------- stage results
MODULES = ("map", "codepath", "hex64")
LABEL_REPO = {"code": "word:code", "comparable": "yesno?",
              "items": {i: "yesno?" for i in tuple(f"y:{o}" for o in OUTCOMES) + ("hp_commits", "pool")}}
LABEL_CHECK = {"repos": ("map", "repo", LABEL_REPO), "repos_checked": "count", "all_equal": "yesno"}
EQ = {"equal": "count", "not_equal": "count"}
CELLMAP = {"classes": {c: EQ for c in "WDR"}, "per_repo": ("map", "repo", {c: EQ for c in "WDR"}), "cells": "count",
           "all_equal": "yesno", "first_R": ("opt", ("list", "cellpos")), "R_after_first": EQ, "not_equal": "count",
           "not_equal_by_class": {c: "count" for c in "WDR"}}
BESIDE = ("map", "word:confirmatory", {"coded": "word:test_word", "corrected": "word:test_word", "status": "word:same"})
ALLREV = ("map", "word:confirmatory", {"repos_where_both_clear": "count", "n": "count", "mean": "real?",
                                       "ci": ("opt", ("pair", "real")), "word": "word:test_word_or_level",
                                       "tracks_reverts": "yesno"})
ROW = {"outcome": "word:outcome", "predictor": "word:primary", "n": "count", "mean": "real?",
       "ci": ("opt", ("pair", "real")), "word": "word:variant_word",
       "difference": {"n": "int", "mean": "real?", "lo": "real?", "hi": "real?"}}
BLOCK = {"name": "word:variant_name", "status": "word:scored", "baseline": "word:baseline", "rows": ("list", ROW)}
VINPUT = {"deleted_rows": "count", "applied": "yesno", "reason": "word:variant_reason"}

STAGE_RESULTS = {
    "lock": {"rc": "count"},
    "score": {"rc": "count"},
    "rehearse": {"loader": "word:code"},
    "labels": {"label_check": LABEL_CHECK},
    "compare": {"cellmap": CELLMAP},
    "readings": {"beside": BESIDE, "allreverts": ALLREV, "applies": {"change1": "yesno", "change2": "yesno"}},
    "named": {"block": BLOCK},
    "hv_prepare": {"deleted": {"case": "count", "late": "count"}, "meta_kept": {"case": "yesno", "late": "yesno"}},
    "hv_build": {"build_status": "word:build_status"},
    "variant": {"block": BLOCK, "inputs": ("map", "repo", VINPUT)},
}



def stage_schema(name: str) -> dict:
    return {"status": "word:status", "code": "word:code", "modules": MODULES, **STAGE_RESULTS[name]}


def validate_stage(name: str, res, vocab: Vocab) -> dict:
    f = f"{name}.result"
    if not isinstance(res, dict) or res.get("status") not in ("ok", "failed"):
        raise ReportError(f"{f}.status")
    if res["status"] == "failed":
        check({"status": "word:status", "code": "word:code", "modules": MODULES}, res, f, vocab)
        if res["code"] == "none":
            raise ReportError(f"{f}.code")
        return res
    check(stage_schema(name), res, f, vocab)
    if res["code"] != "none":
        raise ReportError(f"{f}.code")
    return res


# ------------------------------------------------------------------------------- the reference's result file
RESULT_KEYS = frozenset({
    "valid", "unavailable", "repos", "tests", "sealed", "engine", "not_run", "side_counts", "random_effects",
    "summaries", "result", "n", "outcomes", "specificity", "status", "bauc", "dropped_null", "null_sd", "nonzero_share",
    "residual", "perm_p", "S4_replaces", "S6_sauc_minus", "S9_logistic_z", "S7_tight", "ci95", "minus_surrogate",
    "holm_level", "minus_control", "reading", "allreverts", "allreverts_reading", "exploratory", "mean", "se", "level",
    "ci", "p", "positive", "negative", "above", "below", "across", "sign_test_p", "tau"})
SHAPE_WORDS = RESULT_KEYS | set(OUTCOMES) | set(PREDICTORS)


class ResultShapeError(ValueError):
    """the result does not have the reference's shape; the message is the field's path only"""


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_result(res, repos: frozenset, sealed_keys: frozenset) -> None:
    """the reference's sa3_result.json by shape: its top-level keys; every key a repo of the marginals file, an
    outcome, a predictor, a statistic or summary key, or a word of the fixed list; every string leaf a fixed word,
    except `engine` (an engine pin: 7 to 40 hexadecimal characters, or a version string) and the nine sealed
    hashes (40 hexadecimal characters each). Numbers may be NaN (the reference
    writes NaN as the bare token). Nothing else may appear: no path, no commit list, no free text."""
    top = ("valid", "unavailable", "repos", "tests", "sealed", "engine", "not_run", "side_counts", "random_effects",
           "summaries")

    def bad(f):
        raise ResultShapeError(f)

    if not isinstance(res, dict) or set(res) != set(top):
        bad("result")
    if not isinstance(res["valid"], bool):
        bad("valid")
    if res["unavailable"] != UNAVAILABLE:
        bad("unavailable")
    if res["not_run"] != NOT_RUN:
        bad("not_run")
    if not (isinstance(res["engine"], str) and (ENGINE.fullmatch(res["engine"]) or
                                                RP.VERSION.fullmatch(res["engine"]))):
        bad("engine")
    s = res["sealed"]
    if not isinstance(s, dict) or set(s) != set(sealed_keys) or \
            not all(isinstance(x, str) and RP.HEX40.fullmatch(x) for x in s.values()):
        bad("sealed")
    words_ok = set(READING_WORDS) | set(TEST_WORDS) | set(EXPLORATORY_WORDS) | set(CELL_STATUS) | \
        {ALLREVERTS_SENTENCE}
    keys_ok = SHAPE_WORDS

    def walk(x, f):
        if isinstance(x, dict):
            for k, v in x.items():
                if not isinstance(k, str) or k not in keys_ok:
                    bad(f + ".<key>")
                walk(v, f"{f}.{k}")
        elif isinstance(x, list):
            if len(x) > 2:
                bad(f)
            for v in x:
                walk(v, f + "[]")
        elif isinstance(x, str):
            if x not in words_ok:
                bad(f)
        elif x is None or isinstance(x, bool) or _num(x):
            pass
        else:
            bad(f)

    if not isinstance(res["repos"], dict):
        bad("repos")
    for r, rec in res["repos"].items():
        if r not in repos or not RP.REPO_NAME.fullmatch(r):
            bad("repos.<repo>")
        walk(rec, "repos.<repo>")
    for sect in ("tests", "side_counts", "random_effects"):
        if not isinstance(res[sect], dict):
            bad(sect)
        walk(res[sect], sect)
    if not isinstance(res["summaries"], dict):
        bad("summaries")
    for k, v in res["summaries"].items():
        if not SUMMARY_KEY.fullmatch(k):
            bad("summaries.<key>")
        walk(v, "summaries.<key>")


def check_lock(lock, sealed_keys: frozenset) -> None:
    if not isinstance(lock, dict) or set(lock) != {"sealed_at_commit", "files"}:
        raise ResultShapeError("lock")
    if not (isinstance(lock["sealed_at_commit"], str) and RP.HEX40.fullmatch(lock["sealed_at_commit"])):
        raise ResultShapeError("lock.sealed_at_commit")
    f = lock["files"]
    if not isinstance(f, dict) or set(f) != set(sealed_keys) or \
            not all(isinstance(x, str) and RP.HEX40.fullmatch(x) for x in f.values()):
        raise ResultShapeError("lock.files")


def finite_or_none(v):
    """a number for the public report: finite, else None (NaN and the infinities are not published as numbers)"""
    if v is None or not _num(v) or not math.isfinite(v):
        return None
    return float(v)


# ------------------------------------------------------------------------------------------- public files
STEP = {"step": "count", "name": "word:step_name", "repo": "repo_or_all", "status": "word:status",
        "code": "word:code", "seconds": "time"}
RUN_LOG = {"target": "word:target", "mode": "word:mode", "started": "time", "finished": "time?",
           "complete": "yesno", "steps": ("list", STEP)}
LEDGER_ENTRY = {"event": "word:ledger_event", "time": "time", "commit": "anycommit", "seal_sha256": "hex64",
                "rerun_reason": "reason?", "result_sha256": "hex64?", "code": "word:code", "protected": "dirname?"}
ATTEMPT = {"event": "word:attempt_event", "time": "time", "mode": "word:mode", "commit": "anycommit",
           "step": "count", "code": "word:code"}


