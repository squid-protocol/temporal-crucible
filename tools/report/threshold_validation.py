#!/usr/bin/env python3
"""Validate the self-check cut points (pass at 85% recall, 90% for functions and imports; warning from 65%, 75%) two ways:
  1. what each cut point means: a repository with recall r0 that loses a fraction f of its edges reads as which status;
  2. across the reference repositories: where the live checks sit, and whether the cheap name-matcher check predicts the compiler-grade one.
    python tools/report/threshold_validation.py DIR [DIR ...]      (each DIR holds <name>/<name>_evolution.json made with --reference libclang)"""
import json
import sys
from pathlib import Path

import numpy as np

PASS, WARN = 0.85, 0.65


def status(r, p=PASS, w=WARN):
    return "pass" if r >= p else ("warn" if r >= w else "fail")


def main():
    print("1. What the cut points mean (call edges, pass at 85%, warning from 65%)")
    print(f"   {'recall now':>10s} " + " ".join(f"{int(f * 100):>3d}% lost" for f in (0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4)))
    for r0 in (1.0, 0.95, 0.9, 0.88):
        print(f"   {r0 * 100:9.0f}% " + " ".join(f"{status(r0 * (1 - f)):>9s}" for f in (0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4)))
    rows = []
    for d in sys.argv[1:]:
        for f in sorted(Path(d).glob("*/*_evolution.json")):
            o = json.load(open(f))
            sc = o.get("self_check")
            if not sc:
                continue
            by = {r["id"]: r for r in sc["rows"]}
            rows.append((o["name"], o["lang"], by))
    print("\n2. Reference repositories")
    print(f"   {'repository':14s} {'lang':7s} {'files read':>10s} {'functions':>10s} {'calls vs name matcher':>22s} {'calls vs libclang':>18s} {'libclang parsed':>16s} {'imports':>9s}")
    cmp = []
    for n, lang, by in sorted(rows, key=lambda r: r[0]):
        def g(i, k="recall", sub=None):
            r = by.get(i)
            if not r or "data" not in r:
                return None
            d = r["data"]
            if sub:
                d = d.get(sub)
            return d.get(k) if d else None
        cov = by.get("coverage", {}).get("data")
        covs = f"{cov['scanned']}/{cov['code_files']}" if cov else "-"
        fr = g("functions")
        cr = g("calls", "recall", None)
        cl = (by.get("cg_calls", {}).get("data") or {}).get("edges", {}).get("recall")
        ps = (by.get("cg_calls", {}).get("data") or {}).get("parsed_share")
        im = g("imports")
        print(f"   {n:14s} {lang:7s} {covs:>10s} {('%.0f%%' % (fr * 100)) if fr is not None else '-':>10s} {('%.0f%%' % (cr * 100)) if cr is not None else '-':>22s} {('%.0f%%' % (cl * 100)) if cl is not None else '-':>18s} {('%.0f%%' % (ps * 100)) if ps is not None else '-':>16s} {('%.0f%%' % (im * 100)) if im is not None else '-':>9s}")
        if cr is not None and cl is not None:
            cmp.append((n, cr, cl))
    if cmp:
        a = np.array([[x[1], x[2]] for x in cmp])
        print(f"\n   Repositories with both: {len(cmp)}. Mean recall vs name matcher {a[:, 0].mean() * 100:.0f}%, vs libclang {a[:, 1].mean() * 100:.0f}% (gap {100 * (a[:, 0] - a[:, 1]).mean():+.0f} points).")
        agree = sum(status(x[1]) == status(x[2]) for x in cmp)
        print(f"   The cheap check gives the same status as the compiler-grade one in {agree} of {len(cmp)} repositories; where it differs it is the more lenient one in {sum(status(x[1]) == 'pass' and status(x[2]) != 'pass' for x in cmp)}.")
        if len(cmp) >= 4:
            print(f"   Correlation of the two recalls across repositories: {np.corrcoef(a[:, 0], a[:, 1])[0, 1]:+.2f}")


if __name__ == "__main__":
    main()
