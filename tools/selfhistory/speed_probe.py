#!/usr/bin/env python3
"""Speed + quality instrument: run GitGalaxy AS IT WAS at commit X on FIXED targets, with its own
stage timers on (--file-speed --splicing-speed), and record everything it reports.

    speed_probe.py slots [-n 12]        # print the sparse time slots (evenly spaced daily anchors)
    speed_probe.py run   [-n 12] [-r 3] # scan: for rep: for slot: for target (strictly one scan at a time)

Targets are pinned checkouts under targets/ (same input for every engine version).
Output: speed/runs.jsonl (one record per run), speed/raw/<slot>_<target>_r<rep>.out.gz (full stdout+stderr).
Each record holds wall time, box load before/after, exit code, the engine's own PIPELINE_SUCCESS seconds,
LOC and LOC/s, files mapped, the per-stage (phase) table, top slowest files, regex totals.
Interleaving the reps spreads machine drift across slots instead of biasing one slot.
"""
import argparse, gzip, json, os, re, resource, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIRROR, ENG, SPEED, RAW = HERE / "mirror.git", HERE / "eng", HERE / "speed", HERE / "speed" / "raw"
PY = "/srv/storage_16tb/projects/gitgalaxy/venvs/selfscan/bin/python"
TARGETS = ["keyword-rosetta", "cics-crucible", "language-crucible"]


def slots(n):
    picks = [l.split("\t") for l in (HERE / "picks.tsv").read_text().split("\n") if l]
    idx = sorted({round(k * (len(picks) - 1) / (n - 1)) for k in range(n)})
    return [{"slot": f"s{k:02d}", "pick": i, "date": picks[i][0], "sha": picks[i][1]} for k, i in enumerate(idx)]


def loadavg():
    return round(os.getloadavg()[0], 2)


def wait_quiet(limit=4.0, max_wait=0):
    t0 = time.time()
    while loadavg() > limit and time.time() - t0 < max_wait:
        time.sleep(10)
    return round(time.time() - t0)


def parse(out):
    r = {}
    m = re.search(r"PIPELINE_SUCCESS: (\d+) files mapped in ([\d.]+)s", out)
    if m: r["files_mapped"], r["pipeline_s"] = int(m.group(1)), float(m.group(2))
    m = re.search(r"MISSION_SUCCESS: (\d+) (?:stars|files) mapped in ([\d.]+)s", out)
    if m and "pipeline_s" not in r: r["files_mapped"], r["pipeline_s"] = int(m.group(1)), float(m.group(2))
    m = re.search(r"Processed ([\d,]+) lines of code at ([\d,]+) LOC/s", out)
    if m: r["loc"], r["loc_per_s"] = int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
    ph = {}
    for m in re.finditer(r"^\s*([\d.]+)s \|[^|]*\| (\S+) \(Avg: ([\d.]+)ms/file\)", out, re.M):
        ph[m.group(2)] = {"total_s": float(m.group(1)), "avg_ms": float(m.group(3))}
    if ph: r["phases"] = ph
    sl = [{"s": float(a), "path": b} for a, b in re.findall(r"^\s*([\d.]+)s \|[^|]*\| (\S+/\S+|\S+\.\w+)\s*$", out.split("TOP 10 SLOWEST")[-1].split("CUMULATIVE REGEX")[0], re.M)] if "TOP 10 SLOWEST" in out else []
    if sl: r["slowest"] = sl
    rx = {}
    if "CUMULATIVE REGEX" in out:
        for a, b in re.findall(r"^\s*([\d.]+)s \|[^|]*\| (\S+::\S+)\s*$", out.split("CUMULATIVE REGEX")[-1], re.M):
            rx[b] = float(a)
    if rx: r["regex"] = rx
    return r


def ensure_engine(s):
    wt = ENG / s["slot"]
    if not wt.exists():
        ENG.mkdir(exist_ok=True)
        subprocess.run(["git", "--git-dir", str(MIRROR), "worktree", "add", "-q", "--detach", str(wt), s["sha"]],
                       check=True, capture_output=True)
        # Early engines hard-code their output dir to the live data pool. Redirect that path (output location
        # only; no logic or timing code) so probing never writes into /srv/.../gitgalaxy/data.
        pool, patched = "/srv/storage_16tb/projects/gitgalaxy/data", []
        (SPEED / "out_pool").mkdir(parents=True, exist_ok=True)
        for f in wt.rglob("*.py"):
            try: t = f.read_text()
            except Exception: continue
            if pool in t:
                f.write_text(t.replace(pool, str(SPEED / "out_pool"))); patched.append(str(f.relative_to(wt)))
        (wt / ".instrument_patch.json").write_text(json.dumps(patched))
    return wt


V6 = "/srv/storage_16tb/projects/gitgalaxy/v6"


def engine_entry(wt):
    """(command prefix, extra PYTHONPATH) for THIS commit's own engine; layouts changed over history."""
    if (wt / "gitgalaxy" / "galaxyscope.py").exists():
        return [PY, "-m", "gitgalaxy.galaxyscope"], [str(wt)], "gitgalaxy.galaxyscope"
    if (wt / "backend" / "galaxyscope.py").exists():           # March 2026 layout: script in backend/
        return [PY, str(wt / "backend" / "galaxyscope.py")], [str(wt / "backend"), str(wt)], "galaxyscope"
    raise RuntimeError("no galaxyscope.py in this commit")


def provenance(wt, mod, paths):
    """Import the entry module and list any module that came from the v6 checkout (must be none)."""
    code = ("import sys,importlib\nm=importlib.import_module(%r)\nprint('ENTRY',m.__file__)\n"
            "for k,v in list(sys.modules.items()):\n f=getattr(v,'__file__',None)\n"
            " if f and %r in f: print('LEAK',k,f)\n") % (mod, V6)
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(paths))
    p = subprocess.run([PY, "-c", code], env=env, capture_output=True, text=True, cwd="/")
    leaks = [l for l in p.stdout.splitlines() if l.startswith("LEAK")]
    entry = next((l[6:] for l in p.stdout.splitlines() if l.startswith("ENTRY")), None)
    return (bool(entry) and str(wt) in entry and not leaks), entry, leaks[:3], p.stderr[-200:]


def one_run(s, target, rep, flags):
    wt = ensure_engine(s)
    cmdp, paths, mod = engine_entry(wt)
    work = SPEED / "scratch"; shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
    waited = wait_quiet()
    ok, entry, leaks, perr = provenance(wt, mod, paths)
    if not ok:
        return {"slot": s["slot"], "date": s["date"], "sha": s["sha"], "target": target, "rep": rep, "exit": 97,
                "tail": f"PROVENANCE FAILED entry={entry} leaks={leaks} {perr}"}
    env = dict(os.environ, GITGALAXY_DISABLE_GIT_HISTORY="1", PYTHONPATH=os.pathsep.join(paths))
    helptxt = subprocess.run(cmdp + ["--help"], cwd=work, env=env, capture_output=True, text=True, errors="replace").stdout
    used = [f for f in ("--db-only", "--file-speed", "--splicing-speed") if f in helptxt]   # only what THIS engine has
    cmd = cmdp + [str(HERE / "targets" / target), *used]
    l0, t0 = loadavg(), time.time()
    ru0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    p = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, errors="replace", timeout=1200)
    wall = time.time() - t0
    ru1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (ru1.ru_utime - ru0.ru_utime) + (ru1.ru_stime - ru0.ru_stime)   # all worker processes; load-robust
    out = p.stdout + p.stderr
    rec = {"slot": s["slot"], "date": s["date"], "sha": s["sha"], "target": target, "rep": rep, "flags": used,
           "engine_entry": entry, "provenance_ok": True, "exit": p.returncode, "wall_s": round(wall, 2), "cpu_s": round(cpu, 2), "load_before": l0, "load_after": loadavg(),
           "waited_s": waited, **parse(out)}
    RAW.mkdir(parents=True, exist_ok=True)
    with gzip.open(RAW / f"{s['slot']}_{target}_r{rep}.out.gz", "wt") as f:
        f.write(out)
    if p.returncode:
        rec["tail"] = out[-400:]
    try:                                   # output parity: a speed change that only skips output must be visible
        import sqlite3 as _sq
        dbp = next(iter(work.glob("*_master.db")), None)
        if dbp:
            _c = _sq.connect(f"file:{dbp}?mode=ro&immutable=1", uri=True)
            rec["out_funcs"] = _c.execute("select count(*) from function_data").fetchone()[0]
            try: rec["out_edges"] = _c.execute("select count(*) from edge_data").fetchone()[0]
            except Exception: pass
            _c.close()
    except Exception:
        pass
    shutil.rmtree(work, ignore_errors=True)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["slots", "run"])
    ap.add_argument("-n", type=int, default=12)
    ap.add_argument("-r", "--reps", type=int, default=3)
    ap.add_argument("--only-slot")
    a = ap.parse_args()
    S = slots(a.n)
    if a.cmd == "slots":
        for s in S: print(s)
        return
    if a.only_slot:
        S = [s for s in S if s["slot"] == a.only_slot]
    SPEED.mkdir(exist_ok=True)
    done = set()
    log = SPEED / "runs.jsonl"
    if log.exists():
        done = {(r["slot"], r["target"], r["rep"]) for r in map(json.loads, log.open()) if not r.get("exit")}
    for rep in range(1, a.reps + 1):
        for s in S:
            for t in TARGETS:
                if (s["slot"], t, rep) in done:
                    continue
                r = one_run(s, t, rep, True)
                with log.open("a") as f:
                    f.write(json.dumps(r) + "\n")
                print(f"{s['slot']} {s['date']} {t:<18} rep{rep} exit={r['exit']} wall={r['wall_s']}s pipe={r.get('pipeline_s')} "
                      f"loc/s={r.get('loc_per_s')} load={r['load_before']}->{r['load_after']}", flush=True)


if __name__ == "__main__":
    main()
