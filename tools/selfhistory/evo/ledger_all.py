import sys, time, glob, os, pickle, json
from pathlib import Path
sys.path.insert(0, "/srv/storage_16tb/projects/structural-fingerprint-scanner/src")
from structural_fingerprint.ledger import Snapshot, build_ledger
H = Path("/srv/storage_16tb/projects/gitgalaxy-history")
picks = dict((l.split("\t")[0], l.split("\t")[1]) for l in (H / "picks.tsv").read_text().split("\n") if l)
dbs = sorted(glob.glob(str(H / "dbs" / "*.db")))
snaps = [Snapshot(Path(p), picks[os.path.basename(p)[:10]], os.path.basename(p)[:10]) for p in dbs]
t = time.time(); led = build_ledger(H / "mirror.git", snaps)
print("built %d snapshots in %.0fs" % (len(snaps), time.time() - t), flush=True)
span = led.span()
json.dump({"labels": [s.label for s in snaps], "n_functions": [len(led.ids[i]) for i in range(len(snaps))], "n_lineages": len(span)}, open(H / "evo" / "ledger_summary.json", "w"))
try:
    pickle.dump(led, open(H / "evo" / "ledger_all.pkl", "wb")); print("pickled", flush=True)
except Exception as e:
    print("pickle failed:", e, flush=True)
print("DONE", flush=True)
