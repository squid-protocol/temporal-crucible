#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
""""Once" (docs/process/scoring_step_spec.md section 5, owner ruling 2 of 2026-11-15), and the list of attempts.

The ledger is one JSON object per line, appended and flushed (and fsynced, with its directory) by the launcher on
the host, at a fixed path outside any run directory. Events:

  started     written before the reference `score` process is started: time, the commit, run-2's seal SHA-256,
              the --rerun reason (null on a first start), the protected directory's name
  completed   the result's SHA-256, written as soon as the result file exists in the clone and parses, BEFORE it
              is published (build review B1)
  stopped     a start after which no result file exists (a crash, a time-out, LOCKED, an interruption, no file) or
              the file does not parse (cut short): its code
  resume      a --resume of steps 11 to 14: the commit it ran from

`decide()` is the whole rule: any entry refuses a start, whatever directory is named, except --resume (which needs a
`completed`, or adopts a result left in the clone of a start with no completion) and --rerun REASON after a start
with no completion. After a `completed`, no start, ever. `hold()` is the exclusive lock beside the ledger that one
launcher holds for its whole life, taken before the ledger is read (build review M1).

The attempts file (beside the ledger, `<ledger stem>_attempts.jsonl`) records every attempt and resume, including
those that stopped in steps 1 to 8 and so wrote no ledger entry (section 5: "every attempt is listed in the
report"). It never decides anything.
"""
from __future__ import annotations

import fcntl
import json
import os
import time
from pathlib import Path


class LedgerError(Exception):
    """carries a stop code of texts.STOP_CODES"""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def attempts_path(ledger: Path) -> Path:
    return ledger.with_name(ledger.stem + "_attempts.jsonl")


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    try:
        for line in path.read_text().splitlines():
            if line.strip():
                e = json.loads(line)
                if not isinstance(e, dict) or "event" not in e:
                    raise ValueError
                out.append(e)
    except (OSError, ValueError):
        raise LedgerError("ledger_unreadable") from None
    return out


def append(path: Path, entry: dict) -> None:
    """one line, flushed and fsynced; the directory fsynced when the file is new"""
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(path, "a") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    if new:
        fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def state(entries: list[dict]) -> dict:
    starts = [e for e in entries if e["event"] == "started"]
    done = [e for e in entries if e["event"] == "completed"]
    return {"entries": len(entries), "starts": len(starts), "completed": done[-1] if done else None,
            "open_start": bool(starts) and not done, "last_start": starts[-1] if starts else None,
            "word": "completed" if done else "open" if starts else "empty"}


def decide(entries: list[dict], resume: bool, rerun: str | None) -> str:
    """'first' (no entry: a first start), 'rerun' (a start with no completion, and a reason given), 'resume'
    (a completed score, and --resume), 'adopt' (--resume after a start with no completion: the caller adopts the
    result only if the start's clone holds one); anything else raises LedgerError with its stop code"""
    st = state(entries)
    if resume:
        if st["completed"] is not None:
            return "resume"
        if st["open_start"]:
            return "adopt"
        raise LedgerError("nothing_to_resume")
    if st["completed"] is not None:
        raise LedgerError("ledger_completed")
    if st["entries"] == 0:
        if rerun is not None:
            raise LedgerError("rerun_needs_start")
        return "first"
    if st["open_start"] and rerun is not None:
        return "rerun"
    raise LedgerError("ledger_has_entry")


def entry(event: str, commit: str, seal_sha256: str, rerun: str | None = None, result_sha256: str | None = None,
          code: str = "none", protected: str | None = None) -> dict:
    return {"event": event, "time": int(time.time()), "commit": commit, "seal_sha256": seal_sha256,
            "rerun_reason": rerun, "result_sha256": result_sha256, "code": code, "protected": protected}


def lock_path(ledger: Path) -> Path:
    return ledger.with_name(ledger.name + ".lock")


def hold(ledger: Path):
    """the exclusive lock beside the ledger, or LedgerError('ledger_locked') when another launcher holds it. The
    open file is returned: the lock lasts while it is open (the caller keeps it for its whole life)"""
    ledger.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fh = open(lock_path(ledger), "a")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        raise LedgerError("ledger_locked") from None
    return fh


def attempt(event: str, mode: str, commit: str, step: int = 0, code: str = "none") -> dict:
    return {"event": event, "time": int(time.time()), "mode": mode, "commit": commit, "step": step, "code": code}
