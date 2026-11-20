#!/usr/bin/env python3
"""PNG figures into out/figures/."""
import math
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from common import *

FIG = OUT / "figures"; FIG.mkdir(exist_ok=True)
plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white", "axes.edgecolor": "#555", "text.color": "#222", "axes.labelcolor": "#222",
                     "xtick.color": "#333", "ytick.color": "#333", "axes.grid": True, "grid.color": "#ddd", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
UPC, DNC, SER = "#c0392b", "#2471a3", "#444"
ref = load_refined(); pm = pos(); dates = commit_dates(); series = load_series(dates); det = load_detected(); T = det["T"]
events = make_events(ref, pm)
D = lambda s: datetime.fromisoformat(s[:10])
ED = lambda sha: datetime(dates[sha].year, dates[sha].month, dates[sha].day)   # Eastern commit date at midnight, same base as the series
MIX = "#7d3c98"
clr = lambda down: DNC if down else UPC

# 1 series per corpus
fig, axs = plt.subplots(4, 1, figsize=(11, 11), sharex=True)
for ax, t in zip(axs, CORPORA):
    tm = timed(series, t)
    ax.plot([D(s["date"]) for _, s in tm], [s["cpu"] for _, s in tm], "-o", ms=2, lw=0.8, color=SER)
    ax.set_yscale("log"); ax.set_ylabel(f"{t}\nCPU seconds per scan (log)")
    for e in events:
        c = e["corpora"].get(t)
        if c is None or c["metric"] != "cpu_s": continue
        ax.axvline(ED(e["sha"]), color=clr(c["down"]), lw=0.9, alpha=0.8)
        if abs(c["boundary_rel"]) > 0.25:
            ax.annotate(dates[e["sha"]].strftime("%m-%d"), (ED(e["sha"]), 1), xycoords=("data", "axes fraction"), xytext=(2, -10), textcoords="offset points", fontsize=7, rotation=90, color=clr(c["down"]), va="top")
axs[0].set_title("Scan CPU time of the engine over its history (red line = localised step up, blue = step down; dates shown for steps over 25%)")
axs[-1].set_xlabel("Commit date (US Eastern)"); axs[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
fig.tight_layout(); fig.text(0.995, 0.003, 'input snapshot ' + snapshot_hash(), ha='right', fontsize=6, color='#888'); fig.savefig(FIG / "cpu_series.png", dpi=130); plt.close(fig)

# 2 histogram of step sizes (log2 ratio of the boundary pair)
vals = [(math.log2(c["boundary"][1] / c["boundary"][0]), c["down"]) for e in events for c in e["corpora"].values() if c["metric"] == "cpu_s" and c["boundary"][0] and c["boundary"][1]]
if not vals: print("figures: no CPU-metric steps for the histogram")
fig, ax = plt.subplots(figsize=(7, 4))
if vals:
    lim = max(1.0, max(abs(v) for v, _ in vals)) + 0.25
    bins = [-lim + k * 2 * lim / 24 for k in range(25)]
    ax.hist([v for v, d in vals if not d], bins=bins, color=UPC, alpha=0.85, label="step up")
    ax.hist([v for v, d in vals if d], bins=bins, color=DNC, alpha=0.85, label="step down")
    ax.legend(frameon=False)
ax.set_xlabel("Size of step: log2(CPU after / CPU before)  (+1 = doubled, -1 = halved)"); ax.set_ylabel("Number of (corpus, step) pairs"); ax.set_title("How big are the localised CPU steps?")
fig.tight_layout(); fig.text(0.995, 0.003, 'input snapshot ' + snapshot_hash(), ha='right', fontsize=6, color='#888'); fig.savefig(FIG / "step_size_hist.png", dpi=130); plt.close(fig)

# 3 events per month
by = defaultdict(lambda: [0, 0, 0])
for e in events: by[dates[e["sha"]].strftime("%Y-%m")][{"up": 0, "down": 1, "mixed": 2}[e["direction"]]] += 1
months = sorted(by); fig, ax = plt.subplots(figsize=(8, 3.8))
ax.bar(months, [by[m][0] for m in months], color=UPC, label="step up"); ax.bar(months, [by[m][1] for m in months], bottom=[by[m][0] for m in months], color=DNC, label="step down")
ax.bar(months, [by[m][2] for m in months], bottom=[by[m][0] + by[m][1] for m in months], color=MIX, label="mixed (corpora disagree)")
ax.set_xlabel("Month of the step commit"); ax.set_ylabel("Number of events"); ax.set_title("Localised step events per month"); ax.legend(frameon=False); plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
fig.tight_layout(); fig.text(0.995, 0.003, 'input snapshot ' + snapshot_hash(), ha='right', fontsize=6, color='#888'); fig.savefig(FIG / "events_per_month.png", dpi=130); plt.close(fig)

# 4 known events
KN = [("E1 #3929", "6b604f91a731a1c7a257db8ffb29f350f370fefb", ["keyword-rosetta", "cics-crucible", "onepl", "language-crucible"]),
      ("E2 #5512", "14fc9c7a55cd5d980e3008e586195046057b97c2", ["language-crucible", "onepl", "keyword-rosetta", "cics-crucible"]),
      ("E3 #1234", "89d86da58ad7e69bdc6827c6f8999985e8903185", ["language-crucible", "onepl", "keyword-rosetta", "cics-crucible"])]
cols = dict(zip(CORPORA, ["#1b9e77", "#d95f02", "#7570b3", "#e7298a"]))
fig, axs = plt.subplots(1, 3, figsize=(14, 4))
for ax, (name, sha, _) in zip(axs, KN):
    k = pm[sha]
    for t in CORPORA:
        tm = [(i, s) for i, s in timed(series, t) if abs(i - k) <= 200]
        pre = [s["cpu"] for i, s in tm if i < k][-3:]
        if not tm or not pre: continue
        base = st.median(pre)
        ax.plot([i - k for i, _ in tm], [s["cpu"] / base for _, s in tm], "-o", ms=3, lw=1, color=cols[t], label=t)
    ax.axvline(0, color="#222", lw=1, ls="--"); ax.set_yscale("log"); ax.set_title(f"{name}  ({dates[sha].strftime('%Y-%m-%d')})")
    ax.set_xlabel("First-parent commits after the event commit"); ax.set_ylabel("CPU time relative to the 3 commits before (log)")
axs[0].legend(frameon=False, fontsize=7)
fig.suptitle("The three previously known steps as seen by each corpus (only commits that were timed)"); fig.tight_layout(); fig.text(0.995, 0.003, 'input snapshot ' + snapshot_hash(), ha='right', fontsize=6, color='#888'); fig.savefig(FIG / "known_events.png", dpi=130); plt.close(fig)
print("figures: 4 PNGs")
