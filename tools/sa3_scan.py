#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""SA3 rescan: one snapshot per repo, scanned at ONE pinned engine, with the engine's FULL output kept.

    python tools/sa3_scan.py --repo NAME          # -> <pilot>/sa3_scans/NAME_master.db + NAME.json

MOD-1's scans (tools/laws_build.py) kept only files, functions and edges and threw the engine's master DB away;
SA3's keyword-family, risk-vector and branch-state predictors live in that DB (`file_data`, and the
`mitigation_telemetry` JSON). This rescans the SAME commit MOD-1 measured (docs/mod1/lift_<repo>.json
`snapshot`) and keeps everything. It reads no outcome and scores nothing.

The engine is a frozen export of gitgalaxy f71181aae7 (docs/sa3_registration.md Amendment 1, rule 10: one engine
SHA for all 46 repos), not the live v6 checkout, whose HEAD moves.
"""
from __future__ import annotations

import argparse, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import POOL_DIR  # noqa: E402
from laws_build import is_generated  # noqa: E402

STUDY = Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot")
ENGINE = Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/engine-f71181aae7")
ENGINE_SHA = "f71181aae765eeeb250109d32464d3063332870e"
OUT = STUDY / "sa3_scans"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    a = ap.parse_args()
    r = a.repo
    OUT.mkdir(parents=True, exist_ok=True)
    side, keep = OUT / f"{r}.json", OUT / f"{r}_master.db"
    if side.exists() and keep.exists():
        print(f"{r}: already scanned"); return 0
    lift = json.loads(Path(f"docs/mod1/lift_{r}.json").read_text())
    sha = lift.get("snapshot")
    if not sha:
        print(f"{r}: no MOD-1 snapshot ({lift.get('status')})"); return 1
    t0 = time.time()
    env = {**os.environ, "PYTHONPATH": str(ENGINE), "GITGALAXY_LICENSE_KEY": "COMMUNITY_FREE_TIER",
           "GITGALAXY_DISABLE_GIT_HISTORY": "1"}
    with tempfile.TemporaryDirectory(dir=OUT) as tmp:
        src, res = Path(tmp) / "src", Path(tmp) / "out"
        src.mkdir(); res.mkdir()
        arch = subprocess.run(["git", "-C", str(POOL_DIR / r), "archive", sha], capture_output=True)
        subprocess.run(["tar", "-x", "-C", str(src)], input=arch.stdout, capture_output=True)
        p = subprocess.run([sys.executable, "-m", "gitgalaxy.galaxyscope", str(src), "--output", str(res) + "/"],
                           env=env, capture_output=True, text=True, errors="replace")
        dbs = sorted(res.glob("*_galaxy_master.db"))
        if p.returncode or not dbs:
            (OUT / f"{r}.err").write_text((p.stdout + p.stderr)[-6000:])
            print(f"{r}: scan FAILED rc={p.returncode}"); return 1
        # what laws_build recorded beside the scan, so the unit rule can be applied identically later
        files = [str(f.relative_to(src)) for f in src.rglob("*") if f.is_file()]
        gen = [f for f in files if is_generated(src / f)]
        attrs = {str(g.relative_to(src)): g.read_text(encoding="utf-8", errors="replace")[:200000]
                 for g in src.rglob(".gitattributes") if g.is_file()}
        shutil.move(str(dbs[0]), keep)
        side.write_text(json.dumps({"repo": r, "snapshot": sha, "engine": ENGINE_SHA, "src_root": str(src),
                                    "archive_files": len(files), "generated": gen, "attrs": attrs,
                                    "seconds": round(time.time() - t0, 1)}, indent=1) + "\n")
    print(f"{r}: ok, {len(files)} files in the archive, {time.time()-t0:.0f}s -> {keep.name}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
