"""EXPLORATORY (not registered): is func_fan_out's NM-G signal leftover function size?

    python tools/exploratory/nm_func_vs_size.py   (run from the repo root)
"""
import sys, numpy as np
sys.path.insert(0, "tools")
import nm_screen as N
import json, sqlite3, statistics, subprocess
for repo_name, (db, evf) in N.FUNC_DBS.items():
    repo = N.POOL_DIR / repo_name
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    raw = {}
    for f in evf:
        for e in json.loads((N.REPO_ROOT / f).read_text())["events"]:
            if e["class"] in N.FIX_CLASSES and e["sha"] not in raw: raw[e["sha"]] = e
    events = []
    for sha, e in raw.items():
        ct = N._git(repo, "show", "-s", "--format=%ct", sha).strip()
        if ct: events.append({**e, "ct": int(ct)})
    med = statistics.median(e["ct"] for e in events)
    res = {k: [] for k in ("fo_t3", "loc_t3", "fo_minus_loc_t3", "fo_density_t3", "fo_exact_loc", "fo_per_complexity_t3", "cx_t3")}
    for e in events:
        if e["ct"] <= med: continue
        parent, child = N.parent_child(repo, e["sha"])
        if parent is None or not con.execute("SELECT 1 FROM repo_data WHERE commit_hash=?", (parent,)).fetchone(): continue
        try: st_ = N.diff_statuses(repo, parent, child)
        except subprocess.CalledProcessError: continue
        c = []
        for path, st in st_.items():
            if st["status"] != "touched" or not st["old_path"]: continue
            rows = con.execute("SELECT f.func_name,f.start_line,f.loc,f.func_fan_out,f.complexity FROM function_data f JOIN file_data fd ON f.file_id=fd.id WHERE fd.commit_hash=? AND fd.file_path=? AND fd.language='c'", (parent, st["old_path"])).fetchall()
            rows = [r for r in rows if r[1] is not None and r[2] is not None and r[0]]
            if len(rows) < 2: continue
            ch = N.hunk_lines_parent_side(repo, parent, child, st["old_path"])
            for r in rows: c.append((r[2], any(l in ch for l in range(r[1], r[1] + max(r[2], 1))), float(r[3] or 0), float(r[4] or 0)))
        if not c: continue
        a = np.array(c, dtype=float); loc, y, fo, cx = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
        if not 0 < y.sum() < len(y): continue
        s3 = N.equal_strata(loc, 3)
        v, d = N.strat_auc(fo, y, s3)
        if not d: continue
        l, _ = N.strat_auc(loc, y, s3)
        res["fo_t3"].append(v - .5); res["loc_t3"].append(l - .5); res["fo_minus_loc_t3"].append(v - l)
        res["fo_density_t3"].append(N.strat_auc(fo / np.maximum(loc, 1), y, s3)[0] - .5)
        cxv = N.strat_auc(cx, y, s3)[0]; res["cx_t3"].append(cxv - .5)
        res["fo_per_complexity_t3"].append(v - cxv)
        ve, de = N.strat_auc(fo, y, loc)  # exact-loc strata
        if de: res["fo_exact_loc"].append(ve - .5)
    print(repo_name, {k: (round(float(np.nanmean(v)), 3), len(v)) for k, v in res.items()})
