#!/usr/bin/env python3
"""Area-level evolution (core vs rest): see docs/sensor-overhaul/sensors/core_area.md for the pre-registered definitions.
    python tools/report/core_area.py --repo R --name N --lang python --scans snapshots.json --areas openfold|colabfold --out DIR"""
import argparse
import collections
import json
import re
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))
import evolution_report as ER  # noqa: E402

AREAS = {
    "openfold": [("tests", r"(^|/)tests?/|(^|/)test_[^/]*\.py$"), ("core", r"^openfold/model/|^openfold/utils/geometry/|^openfold/utils/rigid_utils\.py$|^openfold/utils/loss\.py$"),
                 ("data", r"^openfold/(data|np)/"), ("support", r"^openfold/"), ("entry", r".*")],
    "colabfold": [("tests", r"(^|/)tests?/|(^|/)test_[^/]*\.py$"), ("core", r"^colabfold/(batch|colabfold|pairmsa)\.py$|^colabfold/(mmseqs|alphafold)/"),
                  ("support", r"^colabfold/"), ("entry", r".*")],
}


def area_of(path, rules):
    for a, rx in rules:
        if re.search(rx, path):
            return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo"), ap.add_argument("--name"), ap.add_argument("--lang", default="python")
    ap.add_argument("--scans"), ap.add_argument("--areas"), ap.add_argument("--out"), ap.add_argument("--blame", type=int, default=1500)
    a = ap.parse_args()
    rules = AREAS[a.areas]
    out = ER.build(SimpleNamespace(repo=a.repo, lang=a.lang, out=a.out, cache=None, name=a.name, blame=a.blame, scans=None, radius=False, gif=None, link_base=None))
    it = out["_internal"]
    cat, diff = it["cat"], it["diff"]
    edits, fixes = collections.Counter(), collections.Counter()
    edit_fn = collections.defaultdict(collections.Counter)
    for s, c in cat.items():
        for p, f in diff[s]["funcs"]:
            ar = area_of(p, rules)
            edits[ar] += 1
            if cat[s].startswith("fix"):
                fixes[ar] += 1
            edit_fn[ar][(p, f)] += 1
    sn = json.load(open(a.scans))
    seen = {}  # (path,name) -> list of snapshot indices present
    area_now = collections.Counter()
    per = []
    for i, s in enumerate(sn):
        con = sqlite3.connect(f"file:{s['db']}?mode=ro", uri=True)
        files = {k: p for k, p in con.execute("SELECT id, file_path FROM file_data")}
        keys = {(files[f], n) for f, n in con.execute("SELECT file_id, func_name FROM function_data") if f in files}
        per.append(keys)
        if i == len(sn) - 1:
            ids = {k: (files[f], n) for k, f, n in con.execute("SELECT id, file_id, func_name FROM function_data") if f in files}
            incoming = collections.Counter()
            for sid, did in con.execute("SELECT src_func_id, dst_func_id FROM fcall_data WHERE dst_func_id IS NOT NULL"):
                if did in ids and sid in ids and ids[sid] != ids[did]:
                    incoming[ids[did]] += 1
            last_ids = ids
        con.close()
    n = len(sn)
    first = {}
    last = {}
    for i, keys in enumerate(per):
        for k in keys:
            first.setdefault(k, i)
            last[k] = i
    res = {}
    for ar in ("core", "support", "data", "entry", "tests"):
        ks = [k for k in first if area_of(k[0], rules) == ar]
        if not ks:
            continue
        now = [k for k in ks if last[k] == n - 1]
        died = [k for k in ks if last[k] < n - 1]
        old = [k for k in ks if first[k] <= n - 1 - 4]  # born at least 4 scans before the last (~a year)
        surv4 = [k for k in old if last[k] >= first[k] + 4 or last[k] == n - 1]
        years = (n - 1) * 0.25
        births = [k for k in ks if first[k] > 0]
        inc = [k for k in now if incoming.get(k)]
        fwd = [k for k in now if k[1] in ("forward", "__init__")]
        res[ar] = {"functions_now": len(now), "ever": len(ks), "died": len(died), "born_after_first_scan": len(births), "birth_death_per_year_over_size": (len(births) + len(died)) / years / max(len(now), 1),
                   "edits": edits[ar], "fix_edits": fixes[ar], "edits_per_function_now": edits[ar] / max(len(now), 1), "fix_edits_per_function_now": fixes[ar] / max(len(now), 1),
                   "alive_4q_share": len(surv4) / max(len(old), 1), "old_functions": len(old), "with_incoming_call": len(inc) / max(len(now), 1),
                   "functions_edited_2plus": sum(1 for v in edit_fn[ar].values() if v >= 2), "functions_edited_any": len(edit_fn[ar])}
    tot_now = sum(r["functions_now"] for r in res.values())
    tot_edits = sum(r["edits"] for r in res.values())
    for ar, r in res.items():
        r["share_of_functions"] = r["functions_now"] / max(tot_now, 1)
        r["share_of_edits"] = r["edits"] / max(tot_edits, 1)
    # timeline of core births/deaths per scan interval
    tl = []
    for i in range(1, n):
        b = [k for k in per[i] - per[i - 1] if area_of(k[0], rules) == "core"]
        d = [k for k in per[i - 1] - per[i] if area_of(k[0], rules) == "core"]
        tl.append({"label": sn[i]["label"], "core_functions": sum(1 for k in per[i] if area_of(k[0], rules) == "core"), "born": len(b), "died": len(d), "born_examples": sorted(f"{p.split('/')[-1]}:{f}" for p, f in b)[:4], "died_examples": sorted(f"{p.split('/')[-1]}:{f}" for p, f in d)[:4]})
    top_core = sorted(((v, k) for k, v in edit_fn["core"].items()), reverse=True)[:10]
    Path(a.out).mkdir(parents=True, exist_ok=True)
    json.dump({"name": a.name, "areas": res, "timeline": tl, "top_core_edited": [{"function": f"{k[0]}:{k[1]}", "edits": v} for v, k in top_core]}, open(Path(a.out) / f"{a.name}_core_area.json", "w"), indent=1)
    print(f"== {a.name}  ({n} scans)")
    print(f"{'area':8s} {'funcs now':>9s} {'% funcs':>8s} {'edits':>6s} {'% edits':>8s} {'edits/fn':>9s} {'fix/fn':>7s} {'born+died /yr / size':>21s} {'alive>4q':>9s} {'incoming call':>14s}")
    for ar, r in res.items():
        print(f"{ar:8s} {r['functions_now']:9d} {r['share_of_functions'] * 100:7.0f}% {r['edits']:6d} {r['share_of_edits'] * 100:7.0f}% {r['edits_per_function_now']:9.2f} {r['fix_edits_per_function_now']:7.2f} {r['birth_death_per_year_over_size']:21.2f} {r['alive_4q_share'] * 100:8.0f}% {r['with_incoming_call'] * 100:13.0f}%")
    print("core timeline (scan: functions, +born/-died):", "; ".join(f"{t['label']}: {t['core_functions']} +{t['born']}/-{t['died']}" for t in tl))
    print("most edited core functions:", "; ".join(f"{k['function']} ({k['edits']})" for k in [{'function': f'{k[0].split(chr(47))[-1]}:{k[1]}', 'edits': v} for v, k in top_core]))


if __name__ == "__main__":
    main()
