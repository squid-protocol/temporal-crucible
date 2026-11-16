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
              the --rerun reason (null on a first start)
  completed   the result's SHA-256, after the result was checked and published
  stopped     a start that ended without a usable result (a crash, a time-out, LOCKED, an invalid result): its code
  resume      a --resume of steps 11 to 14: the commit it ran from

`decide()` is the whole rule: any entry refuses a start, whatever directory is named, except --resume (which needs a
`completed`) and --rerun REASON after a start with no completion. After a `completed`, no start, ever.

The attempts file (beside the ledger, `<ledger stem>_attempts.jsonl`) records every attempt and resume, including
those that stopped in steps 1 to 8 and so wrote no ledger entry (section 5: "every attempt is listed in the
report"). It never decides anything.
"""
from __future__ import annotations

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
            "open_start": bool(starts) and not done}


def decide(entries: list[dict], resume: bool, rerun: str | None) -> str:
    """'first' (no entry: a first start), 'rerun' (a start with no completion, and a reason given), 'resume'
    (a completed score, and --resume); anything else raises LedgerError with its stop code"""
    st = state(entries)
    if resume:
        if st["completed"] is None:
            raise LedgerError("nothing_to_resume")
        return "resume"
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
          code: str = "none") -> dict:
    return {"event": event, "time": int(time.time()), "commit": commit, "seal_sha256": seal_sha256,
            "rerun_reason": rerun, "result_sha256": result_sha256, "code": code}


def attempt(event: str, mode: str, commit: str, step: int = 0, code: str = "none") -> dict:
    return {"event": event, "time": int(time.time()), "mode": mode, "commit": commit, "step": step, "code": code}
