import sys, subprocess, shutil, json
from concurrent.futures import ThreadPoolExecutor
sys.argv=['x','none']
exec(open('events_probe.py').read().split('if sys.argv[1]')[0])
import history_scan as hs
out = HERE / "dbs_events"; out.mkdir(exist_ok=True)
def one(p):
    final = out / f"{p['event'][:2]}_{p['offset']:+d}_{p['sha'][:10]}.db"
    if final.exists(): return p["slot"], "kept"
    job = HERE / "work" / f"ev_{p['sha'][:10]}"; shutil.rmtree(job, ignore_errors=True); job.mkdir(parents=True)
    db = hs.checkout_scan(p["sha"], job)
    if db: shutil.move(str(db), final)
    shutil.rmtree(job, ignore_errors=True); return p["slot"], "ok" if db else "FAILED"
with ThreadPoolExecutor(3) as ex:
    for r in ex.map(one, pts): print(*r, flush=True)
print("DONE")
