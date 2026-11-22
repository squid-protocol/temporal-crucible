#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The before / after stat manifest of tables_phase_b_spec.md ("Before and after"; review M4, m9).

From outside the job, in a read-only sandbox of its own (tools/harness/sandbox_ro.py), one entry per declared
input of every repo -- including the side-file names a database could grow (-wal, -shm, -journal), so a side
file created during the run is reported -- and per file and directory of each clone's .git: path, type, size,
modification time, change time, inode, mode. No content is read. Taken before the run and after it (the after
also when a stage crashed) and compared: added, removed, changed.

    python3 tools/tables/manifest_stat.py compare A.json B.json
    python3 tools/tables/manifest_stat.py inside --repos a,b --out FILE      # inside the sandbox only

Seen from inside, only the declared files exist in the study path, so a file created beside them on the host is
visible only if it has a declared name; a clone is bound whole, so anything added to its .git is visible.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "harness"))
import sandbox_ro as SR  # noqa: E402


def entry(p: Path) -> list:
    s = os.lstat(p)
    kind = "dir" if stat.S_ISDIR(s.st_mode) else "link" if stat.S_ISLNK(s.st_mode) else "file"
    return [kind, s.st_size if kind != "dir" else 0, s.st_mtime_ns, s.st_ctime_ns, s.st_ino, s.st_mode]


def inside(repos: list[str], out: Path) -> int:
    SR.assert_inside_ro()
    import phase_b as P
    man: dict[str, list] = {}
    for r in repos:
        for _src, dst in P.declared(Path("/unused"), r):
            if os.path.lexists(dst):
                man["study/" + str(dst.relative_to(SR.STUDY))] = entry(dst)
        c = SR.POOL / r
        if not c.exists():
            man[f"pool/{r}"] = ["absent"]
            continue
        g = c / ".git" if (c / ".git").is_dir() else c
        man[f"pool/{r}"] = entry(c)
        for d, dirs, files in os.walk(g, followlinks=False):
            for n in dirs + files:
                p = Path(d) / n
                man["pool/" + str(p.relative_to(SR.POOL))] = entry(p)
            man["pool/" + str(Path(d).relative_to(SR.POOL))] = entry(Path(d))
    out.write_text(json.dumps({"entries": man}, sort_keys=True) + "\n")
    return 0


def take(study: Path, pool: Path, repos: list[str], out_file: Path, rundir: Path, code: Path) -> dict:
    """one manifest, in its own sandbox: every repo's declared inputs (originals) and clones, read-only"""
    import phase_b as P
    rundir.mkdir(parents=True, exist_ok=True)
    inputs = [x for r in repos for x in P.declared(study, r)]
    inputs += [(str(pool / r), SR.POOL / r) for r in repos]
    spec = SR.Spec(rw=[rundir], code=[code], inputs=inputs, cwd=rundir)
    (rundir / "home").mkdir(exist_ok=True)
    (rundir / "tmp").mkdir(exist_ok=True)
    res_file = rundir / "manifest.json"
    argv = ["/usr/bin/python3", "-I", "-B", str(code / "tools" / "tables" / "manifest_stat.py"), "inside",
            "--repos", ",".join(repos), "--out", str(res_file)]
    try:
        p = SR.run(argv, spec, rundir / "home", rundir / "tmp", timeout=7200)
        rc, err = p.returncode, (p.stdout + p.stderr)[-2000:]
    except subprocess.TimeoutExpired:
        rc, err = "timeout", ""
    (rundir / "stage.log").write_text(str(err))
    if rc != 0 or not res_file.exists():
        return {"ok": False, "status": f"failed (rc {rc})"}
    data = json.loads(res_file.read_text())
    out_file.write_text(json.dumps(data, sort_keys=True) + "\n")
    return {"ok": True, "status": f"{len(data['entries'])} entries", "entries": data["entries"]}


def compare(a: dict, b: dict) -> dict:
    ea, eb = a["entries"], b["entries"]
    return {"added": sorted(set(eb) - set(ea)), "removed": sorted(set(ea) - set(eb)),
            "changed": sorted(k for k in set(ea) & set(eb) if ea[k] != eb[k])}


def main() -> int:
    argv = sys.argv[1:]
    if argv[:1] == ["inside"]:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("--repos", required=True)
        ap.add_argument("--out", type=Path, required=True)
        a = ap.parse_args(argv[1:])
        return inside([r for r in a.repos.split(",") if r], a.out)
    if argv[:1] == ["compare"] and len(argv) == 3:
        d = compare(json.loads(Path(argv[1]).read_text()), json.loads(Path(argv[2]).read_text()))
        print(json.dumps({k: len(v) for k, v in d.items()}))
        return 0 if not any(d.values()) else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    raise SystemExit(main())
