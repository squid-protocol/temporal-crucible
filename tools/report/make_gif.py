#!/usr/bin/env python3
"""A GIF of the call graph growing, drawn by historical-call-graph-gif from scan databases we already have (no rescan).
    python tools/report/make_gif.py --scans /path/scan_x/snapshots.json --name nDPI --out OUT [--width 720] [--max-files 1500]"""
import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

HCG = "/srv/storage_16tb/projects/historical-call-graph-gif"
sys.path.insert(0, HCG)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scans", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=720)
    ap.add_argument("--size", default="900x900")
    ap.add_argument("--max-files", type=int, default=1500)
    ap.add_argument("--duration", type=float, default=22.0)
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    import json
    from historical_call_graph_gif import cli, collect, snapshots
    sn = json.load(open(a.scans))
    picks = [snapshots.Pick(commit=s["commit"], date=s["date"], label=s["label"]) for s in sn]
    dbs = [Path(s["db"]) for s in sn]
    ds = collect.drop_leading_empty(collect.from_snapshot_dbs(a.name, picks, dbs))
    args = SimpleNamespace(preset="default", size=a.size, title=None, subtitle=None, credit=None, no_legend=False, no_captions=False, fit="contain", zoom=1.0, focus=None, quality="standard", fps=None, duration=a.duration, hold=2.0, frames_per_snapshot=2, safe_top=None, safe_bottom=None, no_smooth=False, gif_width=a.width, text_scale=None, formats="gif", jobs=a.jobs, max_files=a.max_files)
    st = cli._make_style(args)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cli._build_outputs(ds, args, out, a.name, st)


if __name__ == "__main__":
    main()
