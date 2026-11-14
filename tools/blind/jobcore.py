"""What the two owner-run jobs (score.py, gates.py) share: seal check, in-memory decryption, the guard that
stops a scorer from writing or returning more than declared, the run-once ledger, dry runs on scrambled
labels. See blinding_spec.md ("Unblinding", "Checks that need real labels") and DECISIONS.md 11-17.

Messages printed or raised here never carry label content: when a scorer fails or misbehaves only the kind of
failure is reported (an exception's type name, a blocked audit event's name, a count of undeclared names) --
never an exception message, an argument, an undeclared output's name or anything the scorer printed.
"""
from __future__ import annotations

import datetime
import getpass
import hashlib
import json
import math
import os
import socket
import statistics
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import registry  # noqa: E402
import seal as sealmod  # noqa: E402
from build_labels import load_crypt  # noqa: E402

crypt = load_crypt()

STAMP = "NOT A RESULT"
MAX_STR = 64


class JobError(Exception):
    """A refusal; the message is safe to print."""
    exit_code = 2


class UndeclaredOutput(PermissionError):
    """The scorer tried to write, or returned, more than its declared outputs. A PermissionError so library
    code that tolerates a failed write still fails here (the violation is recorded either way)."""


class ScrambledInput(JobError):
    pass


# ------------------------------------------------------------------------------------------------- guard
_GUARD = {"active": False, "violations": []}
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
_BLOCKED_EVENTS = {
    "os.rename", "os.remove", "os.rmdir", "os.mkdir", "os.symlink", "os.link", "os.truncate", "os.chmod",
    "os.chown", "os.utime", "os.system", "os.exec", "os.spawn", "os.posix_spawn", "os.fork", "os.forkpty",
    "os.putenv", "os.unsetenv", "os.kill", "os.killpg", "os.mkfifo", "os.mknod", "os.setxattr",
    "os.removexattr", "os.startfile", "sys.addaudithook",
}
_BLOCKED_PREFIXES = ("subprocess.", "socket.", "ctypes.", "shutil.", "tempfile.", "pty.", "sqlite3.", "syslog.",
                     "mmap.", "http.", "urllib.", "ftplib.", "smtplib.", "poplib.", "imaplib.", "nntplib.",
                     "telnetlib.", "webbrowser.", "fcntl.", "_winapi.", "msvcrt.")


def _violate(what):
    _GUARD["violations"].append(what)
    raise UndeclaredOutput(f"blocked while the scorer runs: {what}")


def _audit(event, args):
    if not _GUARD["active"]:
        return
    if event == "open":
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else None
        if (isinstance(mode, str) and any(c in mode for c in "wax+")) or \
                (isinstance(flags, int) and flags & _WRITE_FLAGS):
            _violate("open for writing")
    elif event in _BLOCKED_EVENTS or event.startswith(_BLOCKED_PREFIXES):
        _violate(event)


_HOOK_INSTALLED = False


def _install_hook():
    global _HOOK_INSTALLED
    if not _HOOK_INSTALLED:
        sys.addaudithook(_audit)
        _HOOK_INSTALLED = True


class _RefuseWrites:
    def write(self, _s):
        _violate("write to sys.stdout/sys.stderr")

    def flush(self):
        pass

    def isatty(self):
        return False


def guarded_call(fn, *args):
    """Run fn(*args) in this process with: an audit hook that blocks opening files for writing, file
    management, processes, sockets, ctypes and the like; sys.stdout/sys.stderr replaced by objects that refuse
    writes; file descriptors 1 and 2 pointed at a pipe whose bytes are counted and discarded (never shown: they
    could be labels); logging.Logger.handle refusing every record; bytecode writing off. Returns (result, violations). Not a sandbox against a hostile
    scorer -- a deterrent against an honest mistake (DECISIONS.md 14)."""
    _install_hook()
    for s in (sys.stdout, sys.stderr):
        try:
            s.flush()
        except Exception:
            pass
    saved = (os.dup(1), os.dup(2))
    r, w = os.pipe()
    counted = [0]

    def drain():
        while True:
            chunk = os.read(r, 65536)
            if not chunk:
                break
            counted[0] += len(chunk)

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    os.dup2(w, 1)
    os.dup2(w, 2)
    os.close(w)
    old_streams = (sys.stdout, sys.stderr)
    old_bytecode = sys.dont_write_bytecode
    sys.stdout = sys.stderr = _RefuseWrites()
    sys.dont_write_bytecode = True
    logging_mod = sys.modules.get("logging")
    old_handle = None
    if logging_mod is not None:          # a log record could reach an in-memory or file handler: refuse it
        old_handle = logging_mod.Logger.handle
        logging_mod.Logger.handle = lambda self, record: _violate("logging call")
    _GUARD["violations"] = []
    _GUARD["active"] = True
    result, raised = None, None
    try:
        result = fn(*args)
    except BaseException as exc:          # noqa: BLE001 -- anything the scorer raises stops the job
        raised = type(exc).__name__
    finally:
        _GUARD["active"] = False
        sys.stdout, sys.stderr = old_streams
        sys.dont_write_bytecode = old_bytecode
        if old_handle is not None:
            logging_mod.Logger.handle = old_handle
        os.dup2(saved[0], 1)
        os.dup2(saved[1], 2)
        os.close(saved[0])
        os.close(saved[1])
        reader.join(timeout=10)
        os.close(r)
    violations = list(_GUARD["violations"])
    if counted[0]:
        violations.append(f"{counted[0]} byte(s) written to file descriptor 1 or 2 (discarded unseen)")
    if raised and not violations:
        violations.append(f"the scorer raised {raised} (message not shown: it could hold labels)")
    elif raised:
        violations.append(f"the scorer raised {raised}")
    return result, violations


def check_outputs(result, declared):
    """The scorer must return exactly the declared output names, each a scalar. Raises UndeclaredOutput with
    a message that names only declared outputs and counts anything else."""
    if not isinstance(result, dict):
        raise UndeclaredOutput(f"the scorer returned a {type(result).__name__}, not a mapping of declared outputs")
    declared = list(declared)
    extra = [k for k in result if k not in declared]
    if extra:
        raise UndeclaredOutput(f"the scorer returned {len(extra)} undeclared output(s); names not shown")
    missing = [k for k in declared if k not in result]
    if missing:
        raise UndeclaredOutput(f"the scorer did not return declared output(s): {', '.join(missing)}")
    for k in declared:
        v = result[k]
        ok = v is None or isinstance(v, bool) or (isinstance(v, int)) or \
            (isinstance(v, float) and math.isfinite(v)) or (isinstance(v, str) and len(v) <= MAX_STR)
        if not ok:
            raise UndeclaredOutput(f"declared output {k} is not a scalar (number, bool, null or a string of at "
                                   f"most {MAX_STR} characters)")
    return {k: result[k] for k in declared}


def call_scorer(fn, data, params, declared, dry_run):
    """The one gate every scorer and gate call goes through: refuses scrambled input outside a dry run,
    runs the function under the guard, accepts only declared outputs."""
    scrambled = [repo for repo, d in data.items() if d["labels"].get("scrambled")]
    if scrambled and not dry_run:
        raise ScrambledInput(f"scrambled labels for {', '.join(sorted(scrambled))}: a result is never written from "
                             f"scrambled input; use --dry-run")
    result, violations = guarded_call(fn, data, params)
    if violations:
        raise UndeclaredOutput("; ".join(violations))
    return check_outputs(result, declared)


# ------------------------------------------------------------------------------------------------- inputs
def _read_sealed(study_dir, rel, seal):
    """Read a sealed study file once and check the bytes read against the seal (no gap between check and
    use)."""
    with open(os.path.join(study_dir, rel), "rb") as fh:
        data = fh.read()
    if hashlib.sha256(data).hexdigest() != seal["study"].get(rel):
        raise sealmod.SealError(f"seal mismatch: {rel} changed while the job ran")
    return data


def _load_seal(study_dir):
    with open(os.path.join(study_dir, "seal.json"), "rb") as fh:
        return json.loads(fh.read())


def _scans(study_dir, study, seal):
    out = {}
    for repo in study["repos"]:
        scan = json.loads(_read_sealed(study_dir, f"scans/{repo}.json", seal))
        out[repo] = scan["files"]
    return out


def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _who():
    try:
        user = getpass.getuser()
    except Exception:                    # noqa: BLE001
        user = "unknown"
    return f"{user}@{socket.gethostname()}"


def _dump(obj) -> bytes:
    return (json.dumps(obj, indent=1, sort_keys=True) + "\n").encode("ascii")


def _write(path, obj) -> bytes:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = _dump(obj)
    sealmod.write_atomic(path, data)
    return data


# ------------------------------------------------------------------------------------------------- jobs
JOBS = {
    "score": {"result": "result/result.json", "ledger": "result/unblinding.json"},
    "gates": {"result": "result/gates.json", "ledger": "result/gates_unblinding.json"},
}


def _tasks(kind, study):
    """[(task name, function, params, declared outputs)] from the specification; unknown names refuse."""
    if kind == "score":
        s = study["scorer"]
        fn = registry.SCORERS.get(s["name"])
        if fn is None:
            raise JobError(f"scorer {s['name']!r} is not in the registry")
        return [("scorer", fn, s.get("params", {}), s["outputs"])]
    tasks = []
    for g in study.get("gates", []):
        fn = registry.GATES.get(g["gate"])
        if fn is None:
            raise JobError(f"gate {g['gate']!r} is not in the registry")
        tasks.append((g["name"], fn, g.get("params", {}), g["outputs"]))
    if not tasks:
        raise JobError("the specification declares no gates")
    return tasks


def run(kind, study_dir, private_key=None, key_path=None, rerun=None, dry_run=False):
    """The job. Returns 0 on success; raises JobError (refusals, nothing written) or returns 3 when the
    scorer was stopped (the attempt is recorded in the ledger, nothing else is written).

    private_key: a key OBJECT, for tests (a throwaway key generated in the test). The command line never
    passes one; it gives key_path, and crypt.owner_private_key asks for the passphrase on the terminal."""
    study_dir = os.path.abspath(study_dir)
    study = sealmod.load_study(study_dir)
    tasks = _tasks(kind, study)
    if dry_run:
        return _dry_run(kind, study_dir, study, tasks)
    if rerun is not None and not str(rerun).strip():
        raise JobError("--rerun needs a reason")

    # 1. the seal
    try:
        seal_hash = sealmod.verify_seal(study_dir)
    except sealmod.SealError as exc:
        raise JobError(f"stop: {exc}") from None
    seal = _load_seal(study_dir)

    # 5. once per seal
    paths = {k: os.path.join(study_dir, v) for k, v in JOBS[kind].items()}
    ledger = []
    if os.path.exists(paths["ledger"]):
        with open(paths["ledger"]) as fh:
            ledger = json.load(fh)
    earlier = [e for e in ledger if e.get("seal_hash") == seal_hash]
    if (earlier or os.path.exists(paths["result"])) and rerun is None:
        raise JobError(f"this job already ran for this seal ({len(earlier)} recorded run(s)"
                       f"{', and ' + JOBS[kind]['result'] + ' exists' if os.path.exists(paths['result']) else ''});"
                       f" a second run needs --rerun REASON, which is recorded")

    # key fingerprint before any passphrase is asked for
    blobs = {}
    for repo in study["repos"]:
        blobs[repo] = _read_sealed(study_dir, f"labels/{repo}.enc", seal)
        try:
            hdr = crypt.read_header(blobs[repo])
        except crypt.BlindCryptoError as exc:
            raise JobError(f"labels/{repo}.enc: {exc}") from None
        if hdr["key_fingerprint"] != study["key_fingerprint"] or hdr["repo"] != repo:
            raise JobError(f"labels/{repo}.enc was not made for this study's key and repo; refusing")
    scans = _scans(study_dir, study, seal)

    # 2. decrypt into memory
    if private_key is None:
        if not key_path:
            raise JobError("--key PATH is required (the passphrase is asked for on the terminal)")
        try:
            private_key = crypt.owner_private_key(key_path)
        except crypt.BlindCryptoError as exc:
            raise JobError(str(exc)) from None
    if crypt.fingerprint(private_key.public_key()) != study["key_fingerprint"]:
        raise JobError("this private key is not the study's key (fingerprint mismatch); refusing")
    data = {}
    for repo in study["repos"]:
        try:
            labels = crypt.decrypt_table(blobs[repo], private_key)
        except crypt.BlindCryptoError as exc:
            raise JobError(f"labels/{repo}.enc: {exc}") from None
        data[repo] = {"files": scans[repo], "labels": labels}
    scrambled = sorted(r for r, d in data.items() if d["labels"].get("scrambled"))
    if scrambled:
        raise ScrambledInput(f"the encrypted labels for {', '.join(scrambled)} are marked scrambled; no result is "
                             f"written from scrambled input")

    # 3. run once, recorded before it starts
    entry = {"job": kind, "time": _now(), "seal_hash": seal_hash, "who": _who(), "rerun_reason": rerun,
             "status": "started", "wrote": []}
    ledger.append(entry)
    _write(paths["ledger"], ledger)
    outputs = {}
    try:
        for name, fn, params, declared in tasks:
            outputs[name] = call_scorer(fn, data, params, declared, dry_run=False)
    except (UndeclaredOutput, ScrambledInput) as exc:
        entry["status"] = f"stopped: {exc}"
        entry["finished"] = _now()
        _write(paths["ledger"], ledger)
        del data
        print(f"{kind}: stopped -- {exc}; nothing but the ledger entry was written", file=sys.stderr)
        return 3
    del data

    # 4. only the declared outputs
    if os.path.exists(paths["result"]):
        stem, ext = os.path.splitext(paths["result"])
        i = 0
        while os.path.exists(f"{stem}.superseded-{i}{ext}"):
            i += 1
        os.replace(paths["result"], f"{stem}.superseded-{i}{ext}")
    body = {"study_id": study.get("study_id"), "job": kind, "seal_hash": seal_hash, "time": entry["time"]}
    if kind == "score":
        body["scorer"] = study["scorer"]["name"]
        body["outputs"] = outputs["scorer"]
    else:
        body["gates"] = {name: {"gate": g["gate"], "outputs": outputs[name]}
                         for g in study["gates"] for name in [g["name"]]}
    written = _write(paths["result"], body)
    receipt = (f"{kind} seal {seal_hash} time {entry['time']} "
               f"{JOBS[kind]['result']} sha256 {hashlib.sha256(written).hexdigest()}")
    entry["status"] = "completed"
    entry["finished"] = _now()
    entry["wrote"] = [JOBS[kind]["result"]]
    entry["receipt"] = receipt
    _write(paths["ledger"], ledger)
    print(f"keep this line somewhere other than this machine: {receipt}")
    return 0


def _dry_run(kind, study_dir, study, tasks):
    """Every copy of the scrambled labels through the scorer; every output stamped NOT A RESULT; nothing in
    result/, nothing in the ledger, no key."""
    try:
        seal_status = "sealed " + sealmod.verify_seal(study_dir)
    except sealmod.SealError as exc:
        seal_status = f"seal not verified: {exc}"
    scans = {}
    copies = {}
    for repo in study["repos"]:
        with open(os.path.join(study_dir, "scans", f"{repo}.json")) as fh:
            scans[repo] = json.load(fh)["files"]
        p = os.path.join(study_dir, "labels", f"{repo}.scrambled.json")
        if not os.path.exists(p):
            raise JobError(f"no scrambled labels for {repo} (not released, or not built); no dry run")
        with open(p) as fh:
            s = json.load(fh)
        if not s.get("scrambled") or not all(c.get("scrambled") for c in s["copies"]):
            raise JobError(f"labels/{repo}.scrambled.json is not marked scrambled; refusing")
        copies[repo] = s["copies"]
    k = min(len(c) for c in copies.values())
    runs = []
    for i in range(k):
        data = {repo: {"files": scans[repo], "labels": copies[repo][i]} for repo in study["repos"]}
        out = {}
        for name, fn, params, declared in tasks:
            try:
                out[name] = call_scorer(fn, data, params, declared, dry_run=True)
            except UndeclaredOutput as exc:
                raise JobError(f"dry run stopped on copy {i}, {name}: {exc}") from None
        runs.append({"stamp": STAMP, "copy": i, "outputs": out})
    summary = {}
    for name, _fn, _p, declared in tasks:
        for o in declared:
            vals = [r["outputs"][name][o] for r in runs]
            nums = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
            if len(nums) == len(vals) and len(nums) >= 2:
                summary[f"{name}/{o}"] = {"stamp": STAMP, "mean": statistics.fmean(nums),
                                          "sd": statistics.stdev(nums), "min": min(nums), "max": max(nums)}
    body = {"stamp": STAMP, "job": kind, "dry_run": True, "study_id": study.get("study_id"),
            "why": "computed on scrambled labels: any structural effect here is false by construction",
            "seal": seal_status, "k": k, "copies": runs, "spread": summary}
    out_path = os.path.join(study_dir, "dry_run", f"{kind}.NOT_A_RESULT.json")
    _write(out_path, body)
    print(f"{kind} dry run on {k} scrambled copies written to {out_path} -- {STAMP}")
    return 0


def cli(kind, argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=f"The {kind} job (owner-run; see tools/blind/README.md).")
    ap.add_argument("--study", required=True, help="the study directory")
    ap.add_argument("--key", help="the owner's passphrase-protected private key (asked for on the terminal)")
    ap.add_argument("--rerun", metavar="REASON", help="run again for the same seal; the reason is recorded")
    ap.add_argument("--dry-run", action="store_true",
                    help="run on the scrambled labels instead; no key; every output stamped NOT A RESULT")
    a = ap.parse_args(argv)
    if a.dry_run and (a.key or a.rerun):
        ap.error("--dry-run takes neither --key nor --rerun")
    try:
        rc = run(kind, a.study, key_path=a.key, rerun=a.rerun, dry_run=a.dry_run)
    except JobError as exc:
        print(f"{kind}: refused -- {exc}", file=sys.stderr)
        return exc.exit_code
    if rc == 0 and not a.dry_run:
        print(f"{kind}: done; wrote {JOBS[kind]['result']} and recorded the run in {JOBS[kind]['ledger']}")
    return rc
