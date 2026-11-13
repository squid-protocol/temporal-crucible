#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""EXPLORATORY read of a finished laws_run output. Descriptive only.

    python tools/laws_explore.py --run DIR/laws_run_<tag>.json --figs docs/laws_figs --md docs/laws_exploratory_tables.md

LAWS is closed as a failure (docs/laws_postmortem.md). This tool does not compute any law: it reads what
`laws_run.py` already produced on the DEVELOPMENT repositories and lays it out so the numbers can be argued
with -- per-repo effects against each law's registered margin, and the diagnostics that say whether a number
means what its name suggests. Nothing here is a panel result; the development set is 8 repos and 5 languages,
one or two per language, which is below the pooling floor the registration itself sets.
"""
from __future__ import annotations

import argparse, json, math
from pathlib import Path

# dataviz: categorical slots 1-5, fixed order, validated light-surface (contrast WARN -> direct labels + tables)
HUES = {"c": "#2a78d6", "go": "#eb6834", "java": "#1baf7a", "python": "#eda100", "rust": "#e87ba4"}
INK, MUTED, GRID, SURFACE = "#1a1a19", "#5c5c58", "#e6e6e2", "#fcfcfb"
NET = ("LAW-1", "LAW-2", "LAW-3", "LAW-4")
TITLES = {"LAW-1": "LAW-1 heavy tails", "LAW-2": "LAW-2 preferential attachment",
          "LAW-3": "LAW-3 hub persistence", "LAW-4": "LAW-4 centralisation",
          "LAW-5": "LAW-5 decay (descriptive)", "LAW-6": "LAW-6 in-cycle defects",
          "LAW-8": "LAW-8 network metrics add to prediction"}
MARGIN = {"LAW-1": 0.0, "LAW-2": 0.0, "LAW-3": 0.0, "LAW-4": 0.0, "LAW-6": 0.0, "LAW-7": 0.5, "LAW-8": 0.02}


def load(p: Path):
    d = json.loads(p.read_text())
    mc = d.get("matched_coverage") or {}
    return d["repos"], d.get("synthesis") or {}, (mc.get("repos") or []), mc.get("share")


def ci(e, s):
    return (e - 1.96 * s, e + 1.96 * s) if s else (e, e)


def verdict(e, s, margin, direction=1):
    """Plain words. 'clears' only when the whole 95% interval is past the margin in the registered direction."""
    if s in (None, 0) or e is None:
        return "no interval"
    lo, hi = ci(e, s)
    if direction > 0:
        return "clears" if lo > margin else ("opposite" if hi < margin else "straddles")
    return "clears" if hi < margin else ("opposite" if lo > margin else "straddles")


def tables(repos, out: Path) -> dict:
    L = []
    A = L.append
    A("# LAWS exploratory tables (development repos only; descriptive)\n")
    A(f"{len(repos)} repos, {len({r['language'] for r in repos})} languages. "
      "`clears` = the whole 95% interval is past the registered margin in the registered direction.\n")
    rows = {}
    for law in NET + ("LAW-6", "LAW-8"):
        A(f"\n## {TITLES.get(law, law)} (margin {MARGIN.get(law, 0)})\n")
        A("| repo | language | effect | SE | 95% interval | verdict | note |")
        A("|---|---|---|---|---|---|---|")
        rows[law] = []
        for r in sorted(repos, key=lambda x: (x["language"], x["repo"])):
            d = r.get(law) or {}
            if not d.get("evaluable"):
                A(f"| {r['repo']} | {r['language']} | — | — | — | **not evaluable** | {d.get('why','')} |")
                continue
            e, s = d.get("effect"), d.get("se")
            if e is None:
                A(f"| {r['repo']} | {r['language']} | — | — | — | (no single effect) | see metrics |"); continue
            lo, hi = ci(e, s or 0)
            v = verdict(e, s, MARGIN.get(law, 0))
            note = ""
            if law == "LAW-1":
                note = (f"x_min {d.get('xmin')}, tail {d.get('tail_fraction',0):.0%} of nodes, "
                        f"GOF p {d.get('gof_p')}, strength {d.get('strength')}")
            if law == "LAW-3":
                note = f"observed {d.get('observed_mean'):.3f} vs null {d.get('null_mean'):.3f}"
            if law == "LAW-4":
                note = f"Gini {d.get('gini_observed'):.3f} vs replay {d.get('gini_replayed_mean'):.3f}"
            if law == "LAW-8":
                note = f"AUC {d.get('auc_a'):.3f} -> {d.get('auc_b'):.3f}"
            A(f"| {r['repo']} | {r['language']} | {e:+.4f} | {s:.4f} | {lo:+.3f}, {hi:+.3f} | **{v}** | {note} |")
            rows[law].append((r["repo"], r["language"], e, s, v))
    A("\n## LAW-5 decay (descriptive; registered direction is modularity DOWN)\n")
    A("| repo | language | modularity slope/yr | SE | propagation-cost slope | predicted direction? |")
    A("|---|---|---|---|---|---|")
    for r in sorted(repos, key=lambda x: (x["language"], x["repo"])):
        d = r.get("LAW-5") or {}
        if not d.get("evaluable"):
            A(f"| {r['repo']} | {r['language']} | — | — | — | not evaluable |"); continue
        A(f"| {r['repo']} | {r['language']} | {d.get('q_slope'):+.4f} | {d.get('q_se'):.4f} | "
          f"{d.get('pc_slope'):+.5f} | {'YES' if d.get('predicted_direction') else '**NO**'} |")
    A("\n## LAW-7 size confound (AME before and after adjustment)\n")
    A("| repo | metric | unadjusted AME | adjusted AME | shrinkage | effect vs margin 0.5 | SE |")
    A("|---|---|---|---|---|---|---|")
    for r in sorted(repos, key=lambda x: (x["language"], x["repo"])):
        for m, d in ((r.get("LAW-7") or {}).get("metrics") or {}).items():
            if not d.get("evaluable"):
                continue
            u, a = d.get("ame_unadjusted"), d.get("ame_adjusted")
            sh = (1 - a / u) if (u not in (None, 0) and a is not None) else None
            A(f"| {r['repo']} | {m} | {u:.4f} | {a:.4f} | {('%.0f%%' % (sh*100)) if sh is not None else '—'} | "
              f"{d.get('effect'):.3f} | {d.get('se'):.3f} |")
    out.write_text("\n".join(L) + "\n")
    return rows


def figures(repos, figdir: Path) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figdir.mkdir(parents=True, exist_ok=True)
    made = []

    def style(ax):
        ax.set_facecolor(SURFACE)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(GRID)
        ax.tick_params(colors=MUTED, labelsize=8, length=0)
        ax.grid(axis="x", color=GRID, lw=0.8)
        ax.set_axisbelow(True)

    def dots(ax, data, margin, xlabel):
        """one row per repo: effect with a 95% interval, margin as a reference line"""
        ys = range(len(data))
        for y, (repo, lang, e, s) in zip(ys, data):
            lo, hi = ci(e, s or 0)
            ax.plot([lo, hi], [y, y], color=HUES.get(lang, INK), lw=2, solid_capstyle="round", zorder=2)
            ax.plot([e], [y], "o", ms=8, color=HUES.get(lang, INK), mec=SURFACE, mew=2, zorder=3)
        ax.axvline(margin, color=MUTED, lw=1.2, ls=(0, (4, 3)), zorder=1)
        ax.set_yticks(list(ys)); ax.set_yticklabels([f"{r}  ({l})" for r, l, _, _ in data], fontsize=8, color=INK)
        ax.set_xlabel(xlabel, fontsize=8, color=MUTED)
        ax.invert_yaxis(); style(ax)

    # F1: the four network laws, effect vs margin 0
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.2), facecolor=SURFACE)
    for ax, law in zip(axes.ravel(), NET):
        data = [(r["repo"], r["language"], (r.get(law) or {}).get("effect"), (r.get(law) or {}).get("se"))
                for r in sorted(repos, key=lambda x: (x["language"], x["repo"]))
                if (r.get(law) or {}).get("evaluable") and (r.get(law) or {}).get("effect") is not None]
        dots(ax, data, 0.0, "effect (95% interval); dashed line = registered margin 0")
        ax.set_title(TITLES[law], fontsize=10, color=INK, loc="left", pad=8)
    fig.suptitle("The four network laws on the development repos — effect against the registered margin",
                 fontsize=12, color=INK, x=0.012, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95)); p = figdir / "f1_network_laws.png"
    fig.savefig(p, dpi=150, facecolor=SURFACE); plt.close(fig); made.append(p.name)

    # F2: LAW-1's tail is not a comparable object across repos
    d1 = [(r["repo"], r["language"], (r.get("LAW-1") or {}))
          for r in sorted(repos, key=lambda x: (x["language"], x["repo"])) if (r.get("LAW-1") or {}).get("evaluable")]
    fig, ax = plt.subplots(figsize=(8.6, 3.6), facecolor=SURFACE)
    for i, (repo, lang, d) in enumerate(d1):
        frac = d.get("tail_fraction") or 0
        ax.barh(i, frac, height=0.5, color=HUES.get(lang, INK), edgecolor=SURFACE, lw=2)
        ax.text(frac + 0.015, i, f"x_min={d.get('xmin')}  GOF p={d.get('gof_p')}  {d.get('strength')}",
                va="center", fontsize=8, color=MUTED)
    ax.set_yticks(range(len(d1))); ax.set_yticklabels([f"{r}  ({l})" for r, l, _ in d1], fontsize=8, color=INK)
    ax.set_xlim(0, 1.45); ax.set_xlabel("share of nodes the fit calls 'the tail'", fontsize=8, color=MUTED)
    ax.invert_yaxis(); style(ax)
    ax.set_title("LAW-1: what counts as 'the tail' moves from 8% to 100% of nodes between repos",
                 fontsize=11, color=INK, loc="left", pad=8)
    fig.tight_layout(); p = figdir / "f2_law1_tail_instability.png"
    fig.savefig(p, dpi=150, facecolor=SURFACE); plt.close(fig); made.append(p.name)

    # F3: LAW-3's null sits on top of the observed value
    d3 = [(r["repo"], r["language"], r["LAW-3"]) for r in sorted(repos, key=lambda x: (x["language"], x["repo"]))
          if (r.get("LAW-3") or {}).get("evaluable")]
    fig, ax = plt.subplots(figsize=(8.6, 3.6), facecolor=SURFACE)
    for i, (repo, lang, d) in enumerate(d3):
        o, n = d["observed_mean"], d["null_mean"]
        ax.plot([n, o], [i, i], color=GRID, lw=3, solid_capstyle="round", zorder=1)
        ax.plot([n], [i], "o", ms=8, color=MUTED, mec=SURFACE, mew=2, zorder=2)
        ax.plot([o], [i], "o", ms=8, color=HUES.get(lang, INK), mec=SURFACE, mew=2, zorder=3)
        ax.text(max(o, n) + 0.004, i, f"gap {o-n:+.4f}", va="center", fontsize=8, color=MUTED)
    ax.set_yticks(range(len(d3))); ax.set_yticklabels([f"{r}  ({l})" for r, l, _ in d3], fontsize=8, color=INK)
    lo3 = min(min(d["observed_mean"], d["null_mean"]) for _, _, d in d3)
    ax.set_xlim(lo3 - 0.01, 1.11)   # room for the gap labels
    ax.set_xlabel("share of hubs still hubs 5 years later — grey = the random-target null, coloured = observed",
                  fontsize=8, color=MUTED)
    ax.invert_yaxis(); style(ax)
    ax.set_title("LAW-3: hubs persist — but so does the null, so the test is near-empty",
                 fontsize=11, color=INK, loc="left", pad=8)
    fig.tight_layout(); p = figdir / "f3_law3_ceiling.png"
    fig.savefig(p, dpi=150, facecolor=SURFACE); plt.close(fig); made.append(p.name)

    # F4: LAW-5, decay's registered direction is down
    d5 = [(r["repo"], r["language"], r["LAW-5"]) for r in sorted(repos, key=lambda x: (x["language"], x["repo"]))
          if (r.get("LAW-5") or {}).get("evaluable")]
    fig, ax = plt.subplots(figsize=(8.6, 3.6), facecolor=SURFACE)
    dots(ax, [(r, l, d["q_slope"], d["q_se"]) for r, l, d in d5], 0.0,
         "directory-modularity slope per year (95% interval); decay predicts NEGATIVE")
    ax.set_title("LAW-5: modularity is flat or rising, not decaying, in every development repo",
                 fontsize=11, color=INK, loc="left", pad=8)
    fig.tight_layout(); p = figdir / "f4_law5_decay.png"
    fig.savefig(p, dpi=150, facecolor=SURFACE); plt.close(fig); made.append(p.name)

    # F5: LAW-7's effects mostly survive as size
    pairs = [(r["repo"], m, d["ame_unadjusted"], d["ame_adjusted"])
             for r in sorted(repos, key=lambda x: (x["language"], x["repo"]))
             for m, d in ((r.get("LAW-7") or {}).get("metrics") or {}).items() if d.get("evaluable")]
    if pairs:
        fig, ax = plt.subplots(figsize=(9.2, max(3.2, 0.32 * len(pairs))), facecolor=SURFACE)
        for i, (repo, m, u, a) in enumerate(pairs):
            ax.plot([a, u], [i, i], color=GRID, lw=3, solid_capstyle="round", zorder=1)
            ax.plot([u], [i], "o", ms=7, color="#e34948", mec=SURFACE, mew=2, zorder=3)
            ax.plot([a], [i], "o", ms=7, color="#2a78d6", mec=SURFACE, mew=2, zorder=3)
        ax.set_yticks(range(len(pairs))); ax.set_yticklabels([f"{r} · {m}" for r, m, _, _ in pairs],
                                                            fontsize=7.5, color=INK)
        ax.set_xlabel("average marginal effect on P(defect) — red = raw, blue = after adjustment",
                      fontsize=8, color=MUTED)
        ax.invert_yaxis(); style(ax)
        ax.set_title("LAW-7: most of the structural signal is size — adjustment removes 60–90% of it",
                     fontsize=11, color=INK, loc="left", pad=8)
        fig.tight_layout(); p = figdir / "f5_law7_size_confound.png"
        fig.savefig(p, dpi=150, facecolor=SURFACE); plt.close(fig); made.append(p.name)

    # F6: LAW-8, does adding network metrics move the ranking at all
    d8 = [(r["repo"], r["language"], r["LAW-8"]) for r in sorted(repos, key=lambda x: (x["language"], x["repo"]))
          if (r.get("LAW-8") or {}).get("evaluable")]
    fig, ax = plt.subplots(figsize=(8.6, 3.6), facecolor=SURFACE)
    for i, (repo, lang, d) in enumerate(d8):
        a, b = d["auc_a"], d["auc_b"]
        ax.plot([min(a, b), max(a, b)], [i, i], color=GRID, lw=3, solid_capstyle="round", zorder=1)
        ax.plot([a], [i], "o", ms=8, color=MUTED, mec=SURFACE, mew=2, zorder=2)
        ax.plot([b], [i], "o", ms=8, color=HUES.get(lang, INK), mec=SURFACE, mew=2, zorder=3)
        ax.text(max(a, b) + 0.004, i, f"{b-a:+.4f} AUC", va="center", fontsize=8, color=MUTED)
    ax.set_yticks(range(len(d8))); ax.set_yticklabels([f"{r}  ({l})" for r, l, _ in d8], fontsize=8, color=INK)
    lo8 = min(min(d["auc_a"], d["auc_b"]) for _, _, d in d8)
    hi8 = max(max(d["auc_a"], d["auc_b"]) for _, _, d in d8)
    ax.set_xlim(lo8 - 0.02, hi8 + 0.09)   # room for the delta labels
    ax.set_xlabel("AUC — grey = without network metrics, coloured = with them", fontsize=8, color=MUTED)
    ax.invert_yaxis(); style(ax)
    ax.set_title("LAW-8: adding the network metrics moves AUC by less than 0.03 everywhere",
                 fontsize=11, color=INK, loc="left", pad=8)
    fig.tight_layout(); p = figdir / "f6_law8_auc.png"
    fig.savefig(p, dpi=150, facecolor=SURFACE); plt.close(fig); made.append(p.name)
    return made


def sensitivity(repos, thinned, share, figdir: Path, md: Path):
    """The question ACC-P existed to answer, asked of the data directly: when the instrument resolves FEWER
    calls, which law numbers move? A law that moves with coverage is reporting the extractor as much as the
    code."""
    if not thinned:
        return [], None
    full = {(v["repo"], l): (v.get(l) or {}) for v in repos for l in NET}
    thin = {(v["repo"], l): (v.get(l) or {}) for v in thinned for l in NET}
    rows = []
    for (repo, law), a in sorted(full.items()):
        b = thin.get((repo, law)) or {}
        if not (a.get("evaluable") and b.get("evaluable")):
            continue
        ea, eb = a.get("effect"), b.get("effect")
        if ea in (None, 0) or eb is None:
            continue
        rows.append((repo, law, ea, eb, (eb - ea) / abs(ea)))
    if not rows:
        return [], None
    L = ["\n## Coverage sensitivity — the same laws with "
         f"{(1-(share or 0))*100:.0f}% of resolved call edges removed\n",
         f"Edges kept: {share:.1%}. A law whose number barely moves is reporting the CODE; one that swings is "
         "reporting the EXTRACTOR.\n",
         "| law | repos | median |change| | worst |change| | reading |", "|---|---|---|---|---|"]
    import statistics
    by_law = {}
    for repo, law, ea, eb, ch in rows:
        by_law.setdefault(law, []).append(abs(ch))
    for law in NET:
        v = by_law.get(law)
        if not v:
            continue
        med, worst = statistics.median(v), max(v)
        reading = ("robust to coverage" if worst < 0.15 else
                   "sensitive — treat with care" if worst < 0.6 else "coverage-dominated — not usable compile-free")
        L.append(f"| {TITLES[law]} | {len(v)} | {med*100:.0f}% | {worst*100:.0f}% | **{reading}** |")
    md.write_text(md.read_text() + "\n".join(L) + "\n")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9.0, max(3.4, 0.30 * len(rows))), facecolor=SURFACE)
    for i, (repo, law, ea, eb, ch) in enumerate(rows):
        ax.plot([0, ch * 100], [i, i], color=GRID, lw=3, solid_capstyle="round", zorder=1)
        ax.plot([ch * 100], [i], "o", ms=7, color=HUES.get(
            next((r["language"] for r in repos if r["repo"] == repo), ""), INK), mec=SURFACE, mew=2, zorder=3)
    ax.axvline(0, color=MUTED, lw=1.2, zorder=2)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f"{r} · {l}" for r, l, _, _, _ in rows], fontsize=7.5, color=INK)
    # symlog: one repo's LAW-4 moves by ~1000% while most cells sit under 30%. On a linear axis that single
    # outlier flattens every other mark into the spine, which hides the comparison the figure exists to make.
    ax.set_xscale("symlog", linthresh=20)
    ax.set_xticks([-1000, -100, -20, 0, 20, 100, 1000])
    ax.set_xticklabels(["-1000%", "-100%", "-20%", "0", "+20%", "+100%", "+1000%"])
    ax.axvspan(-20, 20, color=GRID, alpha=0.45, zorder=0)  # the linear band, so the scale change is visible
    ax.set_xlabel(f"% change in the law's effect when {(1-(share or 0))*100:.0f}% of resolved edges are removed"
                  f"  —  shaded band is +/-20%, axis is symlog beyond it", fontsize=8, color=MUTED)
    ax.set_facecolor(SURFACE)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True); ax.invert_yaxis()
    worst = max(rows, key=lambda r: abs(r[4]))
    ax.set_title(f"Which laws survive a worse call graph? LAW-2 barely moves; "
                 f"{worst[0]} {worst[1]} moves {worst[4]*100:+.0f}%",
                 fontsize=11, color=INK, loc="left", pad=8)
    fig.tight_layout(); q = figdir / "f7_coverage_sensitivity.png"
    fig.savefig(q, dpi=150, facecolor=SURFACE); plt.close(fig)
    return rows, q.name


def traps(repos, synth) -> list[str]:
    """Computed, not asserted: each line is derived from the run."""
    out = []
    t = [(r["repo"], r["LAW-1"]) for r in repos if (r.get("LAW-1") or {}).get("evaluable")]
    if t:
        fr = [d.get("tail_fraction") or 0 for _, d in t]
        xm = [d.get("xmin") for _, d in t]
        bad = [r for r, d in t if (d.get("gof_p") or 1) < 0.05]
        out.append(f"LAW-1's tail is not one object: x_min {min(xm)}–{max(xm)}, tail {min(fr):.0%}–{max(fr):.0%} "
                   f"of nodes; the power law is REJECTED (GOF p<0.05) in {len(bad)} of {len(t)} repos "
                   f"({', '.join(bad) or 'none'}) yet the registered effect is still positive there.")
    t3 = [(r["repo"], r["LAW-3"]) for r in repos if (r.get("LAW-3") or {}).get("evaluable")]
    if t3:
        gaps = [d["observed_mean"] - d["null_mean"] for _, d in t3]
        out.append(f"LAW-3 is a ceiling test: observed persistence is {min(d['observed_mean'] for _,d in t3):.2f}–"
                   f"{max(d['observed_mean'] for _,d in t3):.2f} and the null is almost the same, so the gap is "
                   f"{min(gaps):+.4f} to {max(gaps):+.4f}. A law whose null nearly equals the observation cannot "
                   f"be evidence either way.")
    t4 = [(r["repo"], r["LAW-4"]) for r in repos if (r.get("LAW-4") or {}).get("evaluable")]
    sig = [(r, d) for r, d in t4 if d.get("se") and abs(d["effect"]) > 1.96 * d["se"]]
    if t4:
        out.append(f"LAW-4 is the significance/size trap: {len(sig)} of {len(t4)} repos are statistically "
                   f"non-zero, but the largest Gini gap is {max(abs(d['effect']) for _,d in t4):.3f} on a 0–1 "
                   f"scale. With margin 0 and 50–100 snapshots, 'detectable' and 'meaningful' come apart.")
    t5 = [r for r in repos if (r.get("LAW-5") or {}).get("evaluable")]
    nd = [r["repo"] for r in t5 if not r["LAW-5"].get("predicted_direction")]
    if t5:
        out.append(f"LAW-5's predicted direction fails in {len(nd)} of {len(t5)} repos ({', '.join(nd)}). "
                   f"Decay is the one law here the data actively argues against.")
    ne = [(r["repo"], (r.get(l) or {}).get("why")) for r in repos for l in ("LAW-6", "LAW-9")
          if (r.get(l) or {}) and not (r.get(l) or {}).get("evaluable")]
    if ne:
        out.append("Evaluability gates and data availability silently removed repos: "
                   + "; ".join(f"{r} ({w})" for r, w in ne if w))
    for law, rec in (synth.get("per_law") or {}).items():
        for lang, L in (rec.get("languages") or {}).items():
            pooled = L.get("pooled") or {}
            c = pooled.get("ci99")
            if c and all(isinstance(x, (int, float)) and not math.isnan(x) for x in c) and (c[1] - c[0]) > 2:
                out.append(f"The synthesis is unusable at this panel size: {law} {lang} pools k={pooled.get('k')} "
                           f"repos and returns a 99% interval {c[0]:.2f} to {c[1]:.2f} (width {c[1]-c[0]:.1f}) "
                           f"with a NaN prediction interval. Random effects need more repos per language than the "
                           f"development set has.")
                break
        else:
            continue
        break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--figs", type=Path, default=Path("docs/laws_figs"))
    ap.add_argument("--md", type=Path, default=Path("docs/laws_exploratory_tables.md"))
    a = ap.parse_args()
    repos, synth, thinned, share = load(a.run)
    print(f"{len(repos)} repos: " + ", ".join(f"{r['repo']}({r['language']})" for r in repos))
    tables(repos, a.md); print(f"tables -> {a.md}")
    for n in figures(repos, a.figs):
        print(f"figure -> {a.figs / n}")
    rows, fname = sensitivity(repos, thinned, share, a.figs, a.md)
    if fname:
        print(f"figure -> {a.figs / fname}  (coverage sensitivity, {len(rows)} law x repo cells)")
    print("\nTRAPS (computed from the run):")
    for i, t in enumerate(traps(repos, synth), 1):
        print(f"  {i}. {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
