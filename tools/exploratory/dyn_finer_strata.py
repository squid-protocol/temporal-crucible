"""EXPLORATORY (not registered): is DYN-H2's rate ratio leftover size? Re-run the Mantel-Haenszel ratio with finer LOC
strata (equal-count bins per T0 snapshot) and with size-matched evidence. DYN-H2 itself used LOC deciles.

    python tools/exploratory/dyn_finer_strata.py <repo> <db>     (run from the repo root)
"""
import json, sqlite3, sys
import numpy as np
sys.path.insert(0, "tools")
from dyncen_eval import EVIDENCE_COLUMNS, POOL_DIR, REPO_ROOT, diff_statuses, parent_child
repo_name, db = sys.argv[1], sys.argv[2]
repo = POOL_DIR / repo_name
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
evs = [e for e in json.load(open(REPO_ROOT / "events" / f"{repo_name}.json"))["events"] if e["class"] == "security-fix" and e.get("on_master", True)]
cols = ", ".join(EVIDENCE_COLUMNS)
snaps = []
for e in evs:
    parent, child = parent_child(repo, e["sha"])
    if not parent: continue
    rows = con.execute(f"SELECT file_path, total_loc, state_heat_triggers, {cols} FROM file_data WHERE commit_hash=?", (parent,)).fetchall()
    if not rows: continue
    snap = {r[0] for r in rows}
    pos = {s["old_path"] for _, s in diff_statuses(repo, parent, child).items() if s["status"] == "touched" and s["old_path"] in snap}
    if not pos: continue
    loc = np.array([float(r[1] or 0) for r in rows]); heat = np.array([float(r[2] or 0) for r in rows]) > 0
    ev = np.array([sum(float(x or 0) for x in r[3:]) for r in rows]); y = np.array([r[0] in pos for r in rows])
    snaps.append((loc, heat, ev, y))
def mh(nloc, nev):
    num = den = 0.0
    for loc, ex, ev, y in snaps:
        lb = np.minimum((np.argsort(np.argsort(loc, kind="stable")) * nloc) // len(loc), nloc - 1)
        eb = np.searchsorted(np.quantile(ev, np.linspace(0, 1, nev + 1)[1:-1]), ev, side="right") if nev > 1 else np.zeros(len(ev), int)
        s = lb * 100 + eb
        for k in np.unique(s):
            m = s == k; n1, n0 = ex[m].sum(), (~ex[m]).sum(); N = n1 + n0
            if n1 and n0:
                num += (y[m] & ex[m]).sum() * n0 / N; den += (y[m] & ~ex[m]).sum() * n1 / N
    return num / den if den else float("nan")
print(f"{repo_name}: {len(snaps)} events")
for nloc, nev in ((10, 4), (10, 1), (25, 1), (50, 1), (100, 1), (50, 4)):
    print(f"  LOC bins {nloc:3d} x evidence bins {nev}: rate ratio {mh(nloc, nev):.3f}")
