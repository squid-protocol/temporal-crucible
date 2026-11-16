#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The committed record of the predictor-side check (docs/process/scoring_step_spec.md section 2, step 2), in
the one shape the scoring job's step 5 reads (`docs/sa3_predictor_check.json` at the pinned commit):

    {"verdict": "all_equal" | "not_equal",
     "phase_b": {"dir": <phase B's output directory>, "files": {repo: {file: sha256}}},
     "compare": {"dir": <tools/compare/tables.py predictor output>, "files": {repo: {file: sha256}}}}

for every repo of the marginals file with status ok, every file under <dir>/<repo>/ (index.json and the tables),
and the verdict of tools/compare/input_check.py's public output (`all_equal`). Hashes and names only.

    python3 tools/scoring/score_sa3.py predictor-check --phase-b PB --compare CT --input-check IC.json \
        --marginals docs/sa3_outcome_marginals.json --out docs/sa3_predictor_check.json

Run by a session (step 2), never by the scoring job, which only reads the file. It reads the table directories'
bytes on the host to hash them; the predictor tables hold no label.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def files(d: Path) -> dict[str, str]:
    return {str(p.relative_to(d)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(d).rglob("*"))
            if p.is_file()}


def record(pb: Path, ct: Path, input_check: dict, repos: list[str]) -> dict:
    return {"verdict": "all_equal" if input_check.get("all_equal") is True and
            input_check.get("repos_checked") == len(repos) else "not_equal",
            "phase_b": {"dir": str(Path(pb).resolve()), "files": {r: files(Path(pb) / r) for r in repos}},
            "compare": {"dir": str(Path(ct).resolve()), "files": {r: files(Path(ct) / r) for r in repos}}}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="score_sa3.py predictor-check")
    ap.add_argument("--phase-b", required=True)
    ap.add_argument("--compare", required=True)
    ap.add_argument("--input-check", required=True)
    ap.add_argument("--marginals", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    marg = json.loads(Path(a.marginals).read_text())
    repos = [r["repo"] for r in marg if r["status"] == "ok"]
    rec = record(Path(a.phase_b), Path(a.compare), json.loads(Path(a.input_check).read_text()), repos)
    Path(a.out).write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print(rec["verdict"])
    return 0 if rec["verdict"] == "all_equal" else 1
