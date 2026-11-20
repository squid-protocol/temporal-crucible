#!/usr/bin/env python3
"""How does new code arrive? From the quarterly scans: function births per interval, split into
  new file    the function's file did not exist (with functions) in the previous scan,
  moved       the same name existed elsewhere in the previous scan (a move or rename, not new code),
  added       a new function in a file that already existed.
Plus how bursty arrival is: the share of all births in the busiest 10% of intervals, the busiest single interval, and the share arriving as new files in the busiest intervals.
    python tools/report/arrival.py NAME=SNAPSHOTS.json [NAME=...]"""
import collections
import json
import sqlite3
import sys

import numpy as np


def load(s):
    con = sqlite3.connect(f"file:{s['db']}?mode=ro", uri=True)
    files = {i: p for i, p in con.execute("SELECT id, file_path FROM file_data")}
    keys = set()
    for f, n in con.execute("SELECT file_id, func_name FROM function_data WHERE func_name IS NOT NULL AND func_name != ''"):
        if f in files:
            keys.add((files[f], n))
    con.close()
    return keys


def main():
    print(f"{'repo':10s} {'scans':>5s} {'births':>8s} {'new file':>9s} {'added':>7s} {'moved':>7s} | {'births/yr/size':>14s} | {'top10% intervals':>17s} {'busiest':>8s} {'new-file share, top10%':>23s} {'median new-file size':>21s}")
    for arg in sys.argv[1:]:
        name, path = arg.split("=")
        sn = json.load(open(path))
        per = [load(s) for s in sn]
        rows = []
        sizes = []
        for i in range(1, len(per)):
            prev, cur = per[i - 1], per[i]
            if len(prev) < 20:
                continue
            pfiles = {p for p, _ in prev}
            pnames = collections.Counter(n for _, n in prev)
            nf = ad = mv = 0
            newfile = collections.Counter()
            for p, n in cur - prev:
                if pnames.get(n):
                    mv += 1
                elif p not in pfiles:
                    nf += 1
                    newfile[p] += 1
                else:
                    ad += 1
            sizes += list(newfile.values())
            rows.append((nf, ad, mv, len(prev)))
        if not rows:
            continue
        nf = sum(r[0] for r in rows); ad = sum(r[1] for r in rows); mv = sum(r[2] for r in rows)
        births = np.array([r[0] + r[1] for r in rows], float)  # genuine new code: new-file + added
        tot = births.sum()
        k = max(1, int(round(0.1 * len(births))))
        order = np.argsort(-births)
        top = births[order[:k]].sum() / max(tot, 1)
        newfile_share_top = sum(rows[j][0] for j in order[:k]) / max(sum(rows[j][0] + rows[j][1] for j in order[:k]), 1)
        years = len(rows) * 0.25
        rate = float(np.mean([(r[0] + r[1]) / r[3] for r in rows])) * 4
        print(f"{name:10s} {len(rows) + 1:5d} {int(tot):8,} {nf / max(tot, 1) * 100:8.0f}% {ad / max(tot, 1) * 100:6.0f}% {mv / max(tot + mv, 1) * 100:6.0f}% | {rate:14.2f} | {top * 100:16.0f}% {births.max() / max(tot, 1) * 100:7.0f}% {newfile_share_top * 100:22.0f}% {int(np.median(sizes)) if sizes else 0:21d}")


if __name__ == "__main__":
    main()
