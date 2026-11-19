#!/usr/bin/env python3
"""Stage indicators across the reference repositories (growth, churn, fix share, untouched share, age), to set and check the stage cut points.
    python tools/report/stage_calibration.py DIR [DIR ...]      (each DIR holds <name>/<name>_evolution.json)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evolution_report as ER  # noqa: E402


def main():
    rows = []
    for d in sys.argv[1:]:
        for f in sorted(Path(d).glob("*/*_evolution.json")):
            o = json.load(open(f))
            ind = ER.stage_indicators(o)
            if ind:
                rows.append((o["name"], o["lang"], o["span"], o["commits"], ind))
    rows.sort(key=lambda r: -r[4]["growth_per_year"])
    print(f"{'repository':16s} {'lang':7s} {'funcs':>8s} {'growth/yr':>10s} {'edits/fn/yr':>12s} {'fix share':>10s} {'sweep share':>12s} {'untouched':>10s} {'commits':>8s}")
    for n, lang, span, c, i in rows:
        print(f"{n:16s} {lang:7s} {i['functions']:8,d} {100 * i['growth_per_year']:9.1f}% {i['edits_per_function_per_year']:12.2f} {100 * i['fix_share_last_year']:9.0f}% {100 * i['sweep_share_last_year']:11.0f}% {100 * (i['untouched_share'] or 0):9.0f}% {c:8,d}")
    g = [r[4]["growth_per_year"] for r in rows]
    print(f"\n{len(rows)} repositories; growth per year: min {100 * min(g):.1f}%, median {100 * sorted(g)[len(g) // 2]:.1f}%, max {100 * max(g):.1f}%")
    print("cut points in use:", ER.STAGE_CUTS)


if __name__ == "__main__":
    main()
