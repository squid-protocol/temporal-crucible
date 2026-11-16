#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The validator of the owner-run job, and the only writer of its public directory (docs/process/owner_job_spec.md,
"Where things are written").

Every value that reaches `owner_report.json`, `owner_report.md`, `seal.json` or `run_log.json` is checked here
against a fixed shape: repo names only from the committed marginals file; counts non-negative integers; verdicts,
reason codes, stage names and roles members of the fixed lists below; hashes 64 hexadecimal characters (40 only
under the seal's named git-blob keys, whose values the launcher computes itself from code and documents); versions
by the pattern of a version string; times integers; one real number. Anything else raises `ReportError` carrying
the FIELD NAME as the schema spells it (`repos.<repo>.count`), never the value and never a key that failed: a key
is data too. Nothing is free text. The Markdown report is rendered from validated values only, with fixed words.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path

# ------------------------------------------------------------------------------------------------ fixed lists
STAGES = ("setup", "manifest_before", "seal_inputs", "copy", "build_A", "build_Aprime", "count", "placebo",
          "runtime", "manifest_after", "seal", "report")
STATUSES = ("ok", "failed")
# why a stage failed: the stage maps its exception's TYPE to one of these (never its message); the launcher adds
# the last four when a stage left no usable result
STAGE_CODES = ("input_missing", "key_error", "assertion", "database_error", "write_refused", "os_error",
               "value_error", "type_error", "git_error", "memory", "import_error", "unclassified",
               "timeout", "no_result", "sandbox_refused", "code_copy_differs")
# why a repo's count is not determined (besides a failed stage's code)
BUILD_STATUSES = ("ok", "unprepared", "scan_incomplete", "no_meta", "build_status_other")
REPO_REASONS = ("none", "unprepared", "scan_incomplete", "no_meta", "build_status_other", "aprime_status_differs",
                "stored_not_ok", "not_run") + STAGE_CODES
PLACEBO_VERDICTS = ("bytes_equal", "numbers_equal", "differs", "failed", "not_run")
FAIL_CODES = ("count_not_determined", "a_differs_from_stored", "pattern_disagreements", "placebo_differs",
              "placebo_failed", "placebo_not_run", "seal_not_written", "manifest_changed", "manifest_failed",
              "inputs_changed_during_run", "reference_code_changed", "reference_code_unchecked",
              "setup_failed", "no_repos", "invalid_report_value", "launcher_error")
TARGETS = ("decoy", "real")
VERDICTS = ("PASS", "FAIL")
ROLES = ("history", "history-wal", "scan_db", "scan_db-wal", "scan_sidecar", "harvest", "harvest-wal", "outcome",
         "nesting")
LISTS = ("vendor.yml", "documentation.yml")
DOCUMENTS = ("sa3_registration.md", "sa3_registration_consolidated.md", "sa3_placebo.json",
             "sa3_outcome_marginals.json", "sa3_power.md", "sa3_code_review.md")
JOB_CODE = ("tools/owner/prepare.py", "tools/owner/tracker_keys.py", "tools/owner/placebo_check.py",
            "tools/owner/seal.py", "tools/owner/report.py", "tools/harness/sandbox_ro.py", "tools/harness/sandbox.py")
ENV_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS", "PYTHONHASHSEED", "LD_LIBRARY_PATH", "LD_PRELOAD", "EXPOSURE_POOL",
            "LAWS_LINGUIST_DIR", "GITGALAXY_PATH", "LANG", "LC_ALL", "TZ")
VERSION_KEYS = ("python", "numpy", "scipy", "git", "tar")
REPO_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,99}")       # phase B's pattern, with a length bound
HEX64 = re.compile(r"[0-9a-f]{64}")
HEX40 = re.compile(r"[0-9a-f]{40}")
VERSION = re.compile(r"[0-9][0-9A-Za-z.+~-]{0,39}")
LIB = re.compile(r"lib[A-Za-z0-9_+.-]{1,60}")
MODULE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,60}")
PACKAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,60}")
SEALED_KEY = re.compile(r"(tools|docs)/[A-Za-z0-9_.-]{1,80}")


class ReportError(Exception):
    """the value at `field` does not fit its shape; str() is 'invalid report value: <field>' and nothing else"""

    def __init__(self, fieldname: str):
        super().__init__(f"invalid report value: {fieldname}")
        self.field = fieldname


@dataclass
class Vocab:
    """the sets a value must come from that are not fixed in this file; each is built by the launcher from
    public, code-side or host sources (the marginals file, the code tree's tools/*.py, the host's installed
    distributions, the reference scorer's SEALED list read from its source as text)"""
    repos: frozenset = frozenset()
    modules: frozenset = frozenset()
    packages: frozenset = frozenset()
    sealed: frozenset = frozenset()


# ---------------------------------------------------------------------------------------------- the checker
def _int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def leaf(kind: str, v, f: str, vocab: Vocab) -> None:
    nullable = kind.endswith("?")
    k = kind.rstrip("?")
    if v is None:
        if nullable:
            return
        raise ReportError(f)
    ok = False
    if k in ("count", "time"):
        ok = _int(v) and v >= 0
    elif k == "yesno":
        ok = isinstance(v, bool)
    elif k == "real":
        ok = (isinstance(v, float) or _int(v)) and math.isfinite(v) and abs(v) < 1e300
    elif k == "hex64":
        ok = isinstance(v, str) and HEX64.fullmatch(v) is not None
    elif k == "hex40":
        ok = isinstance(v, str) and HEX40.fullmatch(v) is not None
    elif k == "version":
        ok = isinstance(v, str) and VERSION.fullmatch(v) is not None
    elif k == "lib":
        ok = isinstance(v, str) and LIB.fullmatch(v) is not None
    elif k == "repo":
        ok = isinstance(v, str) and v in vocab.repos and REPO_NAME.fullmatch(v) is not None
    elif k == "repo_or_all":
        ok = isinstance(v, str) and (v == "*" or (v in vocab.repos and REPO_NAME.fullmatch(v) is not None))
    elif k == "module":
        ok = isinstance(v, str) and v in vocab.modules and MODULE.fullmatch(v) is not None
    elif k == "package":
        ok = isinstance(v, str) and v in vocab.packages and PACKAGE.fullmatch(v) is not None
    elif k == "sealed":
        ok = isinstance(v, str) and v in vocab.sealed and SEALED_KEY.fullmatch(v) is not None
    elif k == "envval":                       # unset, a small integer, or the SHA-256 of the value
        ok = (_int(v) and 0 <= v < 10 ** 6) or (isinstance(v, str) and HEX64.fullmatch(v) is not None)
    elif k.startswith("word:"):
        ok = isinstance(v, str) and v in WORDS[k[5:]]
    else:
        raise AssertionError(f"unknown kind {k}")
    if not ok:
        raise ReportError(f)


WORDS = {"stage": STAGES, "status": STATUSES, "stage_code": STAGE_CODES + ("none",), "build_status": BUILD_STATUSES,
         "repo_reason": REPO_REASONS, "placebo_verdict": PLACEBO_VERDICTS, "fail_code": FAIL_CODES,
         "target": TARGETS, "verdict": VERDICTS, "role": ROLES, "list": LISTS, "document": DOCUMENTS,
         "job_code": JOB_CODE, "env": ENV_VARS}


def check(schema, v, f: str, vocab: Vocab) -> None:
    """schema: a kind string; a dict (exactly these keys); ("map", keykind, value schema); ("list", item schema)"""
    if isinstance(schema, str):
        leaf(schema, v, f, vocab)
    elif isinstance(schema, dict):
        if not isinstance(v, dict) or set(v) != set(schema):
            raise ReportError(f)
        for k, s in schema.items():
            check(s, v[k], f"{f}.{k}", vocab)
    elif schema[0] == "map":
        _, kk, vs = schema
        if not isinstance(v, dict) or len(v) > 100000:
            raise ReportError(f)
        name = f"{f}.<{kk.split(':')[-1]}>"
        for k, x in v.items():
            leaf(kk, k, name, vocab)               # the field name never carries the key itself
            check(vs, x, name, vocab)
    elif schema[0] == "list":
        if not isinstance(v, list) or len(v) > 100000:
            raise ReportError(f)
        for x in v:
            check(schema[1], x, f"{f}[]", vocab)
    else:
        raise AssertionError(schema)


# -------------------------------------------------------------------------------------------- the schemas
REPO_ROW = {"determined": "yesno", "reason": "word:repo_reason", "count": "count?", "a_equals_stored": "yesno?",
            "disagreements": "count?"}
REPORT = {
    "verdict": "word:verdict", "codes": ("list", "word:fail_code"), "target": "word:target",
    "started": "time", "finished": "time", "seconds": "time",
    "repos": ("map", "repo", REPO_ROW),
    "placebo": {"verdict": "word:placebo_verdict", "code": "word:stage_code", "largest_difference": "real?",
                "numbers_differing": "count?", "integer_fields_equal": "yesno?", "repos_in_stage": "count"},
    "versions": {k: "version?" for k in VERSION_KEYS} | {"linear_algebra": ("list", "lib")},
    "seal": {"written": "yesno", "entries": "count", "code_modules_found": ("list", "module"),
             "modules_unchanged_since_8fb7fe0": "yesno?", "lock_expected_entries": "count"},
    "manifest": {"unchanged": "yesno?", "entries": "count?"},
    "stages_failed": "count",
}
RUN_LOG = {
    "target": "word:target", "started": "time", "finished": "time?", "complete": "yesno",
    "last_stage": "word:stage", "invalid_in_stage": ("list", "word:stage"),
    "stages": ("list", {"stage": "word:stage", "repo": "repo_or_all", "status": "word:status",
                        "code": "word:stage_code", "seconds": "time"}),
}
RUNTIME = {"python": "version", "python_sha256": "hex64", "packages": ("map", "package", "version"),
           "git": "version?", "git_sha256": "hex64?", "tar": "version?", "tar_sha256": "hex64?",
           "libraries": ("map", "lib", "hex64"), "environment": ("map", "word:env", "envval?")}
SEAL = {
    "taken": "time", "target": "word:target",
    "inputs": ("map", "repo", {r: "hex64?" for r in ROLES}),
    "lists": {n: "hex64?" for n in LISTS},
    "clones": ("map", "repo", {"head_sha256": "hex64?"}),
    "code": ("map", "module", {"sha256": "hex64", "blob": "hex40", "unchanged_since_8fb7fe0": "yesno?"}),
    "job_code": ("map", "word:job_code", "hex64"),
    "documents": ("map", "word:document", {"sha256": "hex64?", "blob": "hex40?"}),
    "lock_expected": ("map", "sealed", "hex40?"),
    "runtime": RUNTIME,
    "placebo_libraries": ("map", "lib", "hex64"),
}


def entries(seal: dict) -> int:
    """the number of hashed entries of a seal (leaf values that are hashes or versions)"""
    n = 0

    def walk(x):
        nonlocal n
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, str):
            n += 1
    walk({k: v for k, v in seal.items() if k not in ("taken", "target")})
    return n


# ---------------------------------------------------------------------------------------------- the writer
def _atomic(path: Path, text: str) -> None:
    tmp = path.with_name("." + path.name + ".part")
    tmp.write_text(text)
    os.replace(tmp, path)


def _yn(v) -> str:
    return "n/a" if v is None else ("yes" if v else "no")


PLACEBO_WORDS = {
    "bytes_equal": "the code and inputs reproduce the published gate result exactly: proceed",
    "numbers_equal": ("every number within 1e-9, bytes differ: proceed. A library change and a formatting change "
                      "cannot be told apart"),
    "differs": ("some number is beyond 1e-9: STOP. Nothing after this job proceeds. It is reproduced on a decoy; "
                "the real cells are not examined"),
    "failed": "the stage did not complete: STOP",
    "not_run": "not run: STOP",
}


def markdown(rep: dict) -> str:
    """the owner's page, from validated values only; the first line is PASS or FAIL"""
    L = [rep["verdict"], ""]
    if rep["codes"]:
        L += ["Reason codes: " + ", ".join(rep["codes"]), ""]
    started = dt.datetime.fromtimestamp(rep["started"], dt.timezone.utc)
    L += ["# The owner-run preparation job", "",
          f"Target: {rep['target']}. Started {started:%Y-%m-%d %H:%M} UTC (epoch {rep['started']}); "
          f"took {rep['seconds']} s. It does not score SA3. Failed stages: {rep['stages_failed']}.", "",
          "PASS means: every repo on the frozen list has a determined count, A equals the stored file, and zero "
          "pattern disagreements; the placebo verdict is bytes_equal or numbers_equal; the seal was written; every "
          "module the reference scorer loaded, and hist_meta, is unchanged since 8fb7fe0 (checked with git); the "
          "manifests are unchanged. Anything else is FAIL.", "",
          "## 1. Tracker-key count (Amendment 5 section 7, item 5)", "",
          "| repo | determined | reason | count | A equals the stored file | pattern disagreements |",
          "|---|---|---|---:|---|---:|"]
    for r, x in rep["repos"].items():
        L.append(f"| {r} | {_yn(x['determined'])} | {x['reason']} | "
                 f"{'not reported' if x['count'] is None else x['count']} | {_yn(x['a_equals_stored'])} | "
                 f"{'n/a' if x['disagreements'] is None else x['disagreements']} |")
    L += ["", "The count is the number of commits under the primary outcome when the reference outcome builder runs "
          "on the inputs as they are, and not when it runs on a copy of the link harvest without its lower-case "
          "tracker keys (a fix-reference value with a hyphen and a lower-case letter, such as \"fix x86-64 build\"). "
          "A key written in capitals (\"Fix UTF-8 decoding\") matches the registered pattern with or without case "
          "and is not in this count (docs/sa3_amendment5_erratum_draft.md).", "",
          "## 2. The placebo output reproduced (Amendment 5 section 9, layer 2)", ""]
    p = rep["placebo"]
    L += [f"Verdict: **{p['verdict']}** ({PLACEBO_WORDS[p['verdict']]}). Stage code: {p['code']}. "
          f"Repos in the stage: {p['repos_in_stage']}.", "",
          f"Largest absolute difference among numbers: "
          f"{'n/a' if p['largest_difference'] is None else repr(float(p['largest_difference']))}; numbers beyond "
          f"1e-9: {'n/a' if p['numbers_differing'] is None else p['numbers_differing']}; integer fields equal: "
          f"{_yn(p['integer_fields_equal'])}.", "",
          "A pass speaks for the universe, LOC, the primary outcome's file lists and the four primary predictors of "
          "the repos that clear the primary floor; not for the other outcomes, the commit lists, the pool or the "
          "secondary predictors.", "",
          "Versions now: " + ", ".join(f"{k} {rep['versions'][k] or 'unknown'}" for k in VERSION_KEYS)
          + "; linear algebra: " + (", ".join(rep["versions"]["linear_algebra"]) or "unknown")
          + ". The committed placebo file was produced at 8fb7fe0 with versions that were not recorded.", "",
          "## 3. The seal", "",
          f"seal.json written: {_yn(rep['seal']['written'])}; entries: {rep['seal']['entries']}; expected `lock` "
          f"hashes: {rep['seal']['lock_expected_entries']}.", "",
          "Modules the reference scorer loaded (import recorder around the placebo stage): "
          + (", ".join(rep["seal"]["code_modules_found"]) or "none recorded")
          + f". Unchanged since 8fb7fe0: {_yn(rep['seal']['modules_unchanged_since_8fb7fe0'])}.", "",
          f"Label-side manifest, before and after: unchanged {_yn(rep['manifest']['unchanged'])}; entries "
          f"{'n/a' if rep['manifest']['entries'] is None else rep['manifest']['entries']}. The manifest itself stays "
          "in the protected directory.", "",
          "Do not paste anything from the protected directory into a session. Do not re-run to see if it passes.", ""]
    return "\n".join(L)


def write_public(out: Path, vocab: Vocab, report: dict | None = None, seal: dict | None = None,
                 run_log: dict | None = None) -> None:
    """validate every given object first, then write; a value that does not fit raises ReportError and nothing
    of that call is written"""
    if report is not None:
        check(REPORT, report, "report", vocab)
    if seal is not None:
        check(SEAL, seal, "seal", vocab)
    if run_log is not None:
        check(RUN_LOG, run_log, "run_log", vocab)
    if seal is not None:
        _atomic(out / "seal.json", json.dumps(seal, indent=1, sort_keys=True) + "\n")
    if report is not None:
        md = markdown(report)
        _atomic(out / "owner_report.json", json.dumps({"first_line": report["verdict"], **report}, indent=1) + "\n")
        _atomic(out / "owner_report.md", md)
    if run_log is not None:
        _atomic(out / "run_log.json", json.dumps(run_log, indent=1) + "\n")
