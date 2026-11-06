"""EXPLORATORY (not registered): do the NM-F leads beat total_loc inside the same strata?

    python tools/exploratory/nm_file_vs_size.py <touch-cache-dir>   (run from the repo root)
"""
import sys, pathlib, json, sqlite3, numpy as np
sys.path.insert(0, "tools")
import nm_screen as N
from walk_trajectories import harvest_touched_files
cache = pathlib.Path(sys.argv[1])
cols = ["fam_mutation", "fam_dead_code", "fam_connectivity", "fam_memory", "fam_guards"]
print("| metric | repo | strat AUC metric − strat AUC total_loc (10 bins) | metric, 50 bins | density metric/LOC, 10 bins | total_loc, 50 bins |")
print("|---|---|---:|---:|---:|---:|")
out = {}
for repo_name, db in N.FILE_DBS.items():
    repo = N.POOL_DIR / repo_name
    snaps = [s for s in json.loads((N.REPO_ROOT / "walks" / f"{repo_name}_quarterly.json").read_text())["revisions"] if s.get("status", "ok") == "ok"]
    for s in snaps: s["ct"] = int(N._git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())
    ev = {}
    for e in json.loads((N.REPO_ROOT / "events" / f"{repo_name}.json").read_text())["events"]:
        if e["class"] == "security-fix" and e.get("on_master", True):
            ct = N._git(repo, "show", "-s", "--format=%ct", e["sha"]).strip()
            if ct: ev[e["sha"]] = {**e, "ct": int(ct)}
    ev = list(ev.values())
    t = harvest_touched_files(repo, ev, 8, cache / f"arch_touch_{repo_name}.json")
    ef = {e["sha"]: set(t[e["sha"]]["old"]) | set(t[e["sha"]]["new"]) for e in ev if t.get(e["sha"])}
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    acc = {c: [[], [], []] for c in cols + ["amplified_cascading_flux"]}; size50 = []
    for s in snaps:
        rows = con.execute(f"SELECT file_path,total_loc,mitigation_telemetry,{','.join(cols)} FROM file_data WHERE commit_hash=? AND language='c'", (s["sha"],)).fetchall()
        if not rows: continue
        pf = set()
        for e in ev:
            if s["ct"] < e["ct"] <= s["ct"] + 180 * 86400 and e["sha"] in ef: pf |= ef[e["sha"]]
        pos = np.array([1.0 if r[0] in pf else 0.0 for r in rows])
        if pos.sum() == 0: continue
        loc = np.array([float(r[1] or 0) for r in rows]); s10, s50 = N.equal_strata(loc, 10), N.equal_strata(loc, 50)
        base10 = N.strat_auc(loc, pos, s10)[0]; size50.append(N.strat_auc(loc, pos, s50)[0] - .5)
        vals = {c: np.array([float(r[3 + i] or 0) for r in rows]) for i, c in enumerate(cols)}
        vals["amplified_cascading_flux"] = np.array([float((json.loads(r[2]) if r[2] else {}).get("amplified_cascading_flux", 0) or 0) for r in rows])
        for c, v in vals.items():
            acc[c][0].append(N.strat_auc(v, pos, s10)[0] - base10)
            acc[c][1].append(N.strat_auc(v, pos, s50)[0] - .5)
            acc[c][2].append(N.strat_auc(v / np.maximum(loc, 1), pos, s10)[0] - .5)
    for c, (a, b, d) in acc.items():
        print(f"| `{c}` | {repo_name} | {np.nanmean(a):+.3f} | {np.nanmean(b):+.3f} | {np.nanmean(d):+.3f} | {np.nanmean(size50):+.3f} |")
