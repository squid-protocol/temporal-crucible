#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Nesting depth of every unit file at a repo's SA3 snapshot (SA3 Amendments 2 and 3). No outcome is read.

    <engine venv>/python tools/sa3_nest_scan.py --repo NAME     # -> <pilot>/sa3_nesting/NAME.json

Needs tree_sitter_language_pack 1.20.0, which an engine venv has and the scorer venv does not.
"""
from __future__ import annotations

import argparse, importlib.metadata as md, json, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sa3_nesting as N  # noqa: E402
import laws_units as U  # noqa: E402
from _engine import POOL_DIR  # noqa: E402
from mod1_lift import frame, STUDY  # noqa: E402
from sa3_outcomes import universe, SCANS  # noqa: E402

OUT = STUDY / "sa3_nesting"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    a = ap.parse_args()
    got = md.version("tree_sitter_language_pack")
    assert got == N.PACK_VERSION, f"grammar pack {got}, the registration pins {N.PACK_VERSION}"
    f = frame(a.repo)
    files, _ = universe(a.repo, f["langs"])
    sha = json.loads((SCANS / f"{a.repo}.json").read_text())["snapshot"]
    out, skipped, errors = {}, 0, 0
    with tempfile.TemporaryDirectory(dir=STUDY) as tmp:
        arch = subprocess.Popen(["git", "-C", str(POOL_DIR / a.repo), "archive", sha], stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", tmp], stdin=arch.stdout, capture_output=True)
        arch.wait()
        for p in sorted(files):
            g = N.grammar_for(U.language_of(p), p)
            if g is None or g not in N.CONTROL:
                skipped += 1
                continue
            try:
                r = N.nesting((Path(tmp) / p).read_bytes(), g)
            except Exception:
                skipped += 1
                continue
            errors += r["parse_error"]
            out[p] = [r["nest_max"], r["nest_mean"]]
    OUT.mkdir(exist_ok=True)
    (OUT / f"{a.repo}.json").write_text(json.dumps({"repo": a.repo, "snapshot": sha, "pack": got, "measured": len(out),
                                                    "not_measured": skipped, "parse_errors": errors, "files": out}) + "\n")
    print(f"{a.repo}: {len(out)} files measured, {skipped} not measured, {errors} with a parse error", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
