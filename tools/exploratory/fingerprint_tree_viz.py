#!/usr/bin/env python3
"""EXPLORATORY: draw Tree 1 (growth tree of the common fingerprints) from fingerprint_trees.py's outputs.

Solid line = the chosen parent (most common sub-shape); gray dotted lines = every OTHER common shape the node could
have grown from by one signal. Columns = number of signals present. Node area ~ share of functions. Colour = the
three largest similarity families (Tree 2), the rest folded into "Other" (all-pairs palette cap).

Writes docs/fingerprint_tree.html (interactive, D3) and docs/fingerprint_tree.png (static preview).

    python tools/exploratory/fingerprint_tree_viz.py [--engine <gitgalaxy checkout with #8009>]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import defaultdict

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from _engine import DOCS_DIR  # noqa: E402

FAM_NAMES = {}  # filled from the data: the 3 largest families get descriptive names below
LIGHT = ["#2a78d6", "#eb6834", "#1baf7a"]
DARK = ["#3987e5", "#d95926", "#199e70"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="/srv/storage_16tb/projects/gitgalaxy/gitgalaxy-worktrees/signal-names")
    ap.add_argument("--families", type=int, default=14)
    a = ap.parse_args()
    sys.path.insert(0, a.engine)
    from gitgalaxy.standards.analysis_lens import signal_display_name as dn  # noqa: E402

    def short(c):
        return re.sub(r"\s*\(.*\)$", "", dn(c))

    D = json.loads((DOCS_DIR / "fingerprint_trees_exploratory.json").read_text())
    md = (DOCS_DIR / "fingerprint_trees_exploratory.md").read_text()
    meta = {}
    for m in re.finditer(r" — #(\d+): ([\d.]+)% · (\d+) repos \(top (\d+)%\) · ([^·]+) · (\d+) lines · tests (\d+)%", md):
        meta[int(m.group(1))] = {"top": int(m.group(4)), "lines": int(m.group(6)), "tests": int(m.group(7))}
    shapes = D["shapes"]
    total = D["total"]
    sets = [frozenset(s["signals"]) for s in shapes]
    n = len(shapes)
    # Tree 2 families, recomputed exactly as fingerprint_trees.py does
    J = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            u = len(sets[i] | sets[j])
            J[i, j] = J[j, i] = 1 - (len(sets[i] & sets[j]) / u if u else 1)
    lab = fcluster(linkage(squareform(J, checks=False), method="average"), a.families, criterion="maxclust")
    share = defaultdict(float)
    for i, s in enumerate(shapes):
        share[int(lab[i])] += s["n"] / total
    big = [f for f, _ in sorted(share.items(), key=lambda t: -t[1])[:3]]
    names = {}
    for f in big:
        core = defaultdict(float)
        for i in np.flatnonzero(lab == f):
            for x in sets[i]:
                core[x] += shapes[i]["n"]
        w = sum(shapes[i]["n"] for i in np.flatnonzero(lab == f))
        langs = defaultdict(int)
        for i in np.flatnonzero(lab == f):
            for l, c in shapes[i]["langs"]:
                langs[l] += c
        often = [short(x) for x, v in sorted(core.items(), key=lambda t: -t[1]) if 0.4 <= v / w < 0.9][:2]
        top_l = ", ".join(l for l, _ in sorted(langs.items(), key=lambda t: -t[1])[:2])
        names[f] = f"F{f}: {' + '.join(often) if often else 'bare one-step functions'} ({top_l})"
    # alternative one-step parents
    alt = defaultdict(list)
    for i, S in enumerate(sets):
        p = shapes[i]["parent"]
        for j, T in enumerate(sets):
            if j != i and T < S and len(S - T) == 1 and (j + 1) != p:
                alt[i].append(j)
    # layout: x = number of signals, y = tidy DFS over the chosen-parent tree
    kids = defaultdict(list)
    roots = []
    for i, s in enumerate(shapes):
        (kids[s["parent"] - 1] if s["parent"] else roots).append(i)
    y = {}
    nxt = [0]

    def place(i):
        ch = sorted(kids[i], key=lambda j: -shapes[j]["n"])
        for c in ch:
            place(c)
        if ch:
            y[i] = float(np.mean([y[c] for c in ch]))
        else:
            y[i] = nxt[0]
            nxt[0] += 1
    for r in roots:
        place(r)
    nodes = []
    for i, s in enumerate(shapes):
        f = int(lab[i])
        p = s["parent"] - 1 if s["parent"] else None
        added = sorted(sets[i] - sets[p]) if p is not None else []
        mt = meta.get(i + 1, {})
        nodes.append({"id": i, "rank": i + 1, "k": len(sets[i]), "y": y[i], "share": s["n"] / total, "n": s["n"],
                      "repos": s["repos"], "top": mt.get("top"), "lines": mt.get("lines"), "tests": mt.get("tests"),
                      "langs": [[l, c / s["n"]] for l, c in s["langs"][:3]],
                      "signals": [short(x) for x in sorted(sets[i])], "added": [short(x) for x in added],
                      "family": big.index(f) if f in big else 3, "fam": names.get(f, f"F{f} (other)"),
                      "parent": p, "alt": alt[i]})
    n_alt = sum(len(v) for v in alt.values())
    multi = sum(1 for v in alt.values() if v)
    data = {"nodes": nodes, "legend": [names[f] for f in big] + ["Other families"], "total": total,
            "cover": D["cover"], "n_alt": n_alt, "multi": multi, "leaves": nxt[0]}
    html = TEMPLATE.replace("__DATA__", json.dumps(data))
    (DOCS_DIR / "fingerprint_tree.html").write_text(html)
    # static preview
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    H = max(8, nxt[0] * 0.13)
    fig, ax = plt.subplots(figsize=(15, H))
    col = LIGHT + ["#a3a29c"]
    for nd in nodes:
        for j in nd["alt"]:
            ax.plot([nodes[j]["k"], nd["k"]], [nodes[j]["y"], nd["y"]], ls=(0, (1, 2)), lw=0.6, color="#b9b8b2", zorder=1)
    for nd in nodes:
        if nd["parent"] is not None:
            p = nodes[nd["parent"]]
            ax.plot([p["k"], nd["k"]], [p["y"], nd["y"]], lw=1.4, color="#52514e", zorder=2)
    for nd in nodes:
        ax.scatter(nd["k"], nd["y"], s=20 + 9000 * nd["share"], color=col[nd["family"]], edgecolor="#fcfcfb", lw=1.5, zorder=3)
        if nd["rank"] <= 12:
            ax.annotate(f"#{nd['rank']}" + (f" +{', '.join(nd['added'])}" if nd["added"] else " (empty)"),
                        (nd["k"], nd["y"]), xytext=(8, 3), textcoords="offset points", fontsize=8, color="#0b0b0b", zorder=4)
    ax.invert_yaxis()
    ax.set_xlabel("number of signals present (keyword families)", color="#52514e")
    ax.set_yticks([])
    for s_ in ("top", "right", "left"):
        ax.spines[s_].set_visible(False)
    ax.set_title("Growth tree of the 200 most common function fingerprints (exploratory)\n"
                 "solid = chosen parent (most common sub-shape) · gray dotted = other one-signal parents · area = share of functions",
                 fontsize=11, loc="left", color="#0b0b0b")
    from matplotlib.lines import Line2D
    hs = [Line2D([], [], marker="o", ls="", color=c, label=l, markersize=8) for c, l in zip(col, data["legend"])]
    hs += [Line2D([], [], color="#52514e", lw=1.4, label="chosen parent"),
           Line2D([], [], color="#b9b8b2", lw=0.8, ls=(0, (1, 2)), label="other possible parent")]
    ax.legend(handles=hs, loc="lower right", frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(DOCS_DIR / "fingerprint_tree.png", dpi=110)
    print(f"nodes {n}; alt edges {n_alt}; nodes with >=1 alt parent {multi}; leaves {nxt[0]}; legend {data['legend']}")
    return 0


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fingerprint Growth Tree</title>
<style>
:root{--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#8a8984;--edge:#52514e;--alt:#b9b8b2;--ring:#fcfcfb;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#a3a29c;--card:#ffffff;--line:#e4e3de}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#8f8e86;
--edge:#c3c2b7;--alt:#5c5b56;--ring:#1a1a19;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#76756f;--card:#242422;--line:#33332f}}
:root[data-theme="dark"]{--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#8f8e86;--edge:#c3c2b7;--alt:#5c5b56;--ring:#1a1a19;
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#76756f;--card:#242422;--line:#33332f}
body{margin:0;background:var(--surface);color:var(--ink);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1400px;margin:0 auto;padding:20px 16px}
h1{font-size:20px;margin:0 0 4px} p{margin:4px 0;color:var(--ink2)}
.bar{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin:12px 0}
.key{display:flex;align-items:center;gap:6px;color:var(--ink2);font-size:13px}
.dot{width:11px;height:11px;border-radius:50%} .ln{width:22px;height:0;border-top:2px solid var(--edge)} .ln.alt{border-top:2px dotted var(--alt)}
label{color:var(--ink2);font-size:13px;cursor:pointer}
#wrap{overflow:auto;border:1px solid var(--line);border-radius:8px;background:var(--surface)}
#tip{position:fixed;pointer-events:none;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;
font-size:12.5px;max-width:340px;box-shadow:0 4px 18px rgba(0,0,0,.18);display:none;color:var(--ink)}
#tip b{font-size:13px} #tip .m{color:var(--ink2)}
text{fill:var(--ink);font-size:11px} .axis text{fill:var(--muted)} .axis line,.axis path{stroke:var(--line)}
</style></head><body><main>
<h1>Fingerprint growth tree</h1>
<p>The 200 most common function fingerprints (<span id="cov"></span> of <span id="tot"></span> functions), arranged by how many keyword families
each contains. A <b>solid line</b> joins a shape to its chosen parent, the most common shape it extends. <b>Gray dotted lines</b> join it to every
other common shape it could equally have grown from by adding one signal. Node area = share of all functions. Hover a node for details.</p>
<p class="m" style="color:var(--muted)">Exploratory · population DB v2.12.0 (745 targets) · engine b64f42bf rules, before the #8010/#8011/#8016 fixes ·
counts are per function, so a few OS-scale repos weigh heavily (repo counts in the tooltip).</p>
<div class="bar" id="legend"></div>
<div class="bar"><label><input type="checkbox" id="showalt" checked> show other possible parents</label>
<span class="key"><span class="ln"></span>chosen parent</span><span class="key"><span class="ln alt"></span>other possible parent</span></div>
<div id="wrap"><svg id="svg"></svg></div>
<div id="tip"></div>
</main>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
const D = __DATA__;
const N = D.nodes, fmt = d3.format(".2%");
document.getElementById("cov").textContent = d3.format(".1%")(D.cover);
document.getElementById("tot").textContent = d3.format(",")(D.total);
const fam = ["var(--s1)","var(--s2)","var(--s3)","var(--s4)"];
const lg = d3.select("#legend");
D.legend.forEach((t,i)=>{const k=lg.append("span").attr("class","key");k.append("span").attr("class","dot").style("background",fam[i]);k.append("span").text(t);});
const kmax = d3.max(N,d=>d.k), rowH = 13, colW = 120, m = {t:30,l:30,r:260,b:20};
const W = m.l + (kmax+1)*colW + m.r, H = m.t + D.leaves*rowH + m.b;
const x = k => m.l + k*colW, y = v => m.t + v*rowH;
const r = d3.scaleSqrt().domain([0, d3.max(N,d=>d.share)]).range([3, 22]);
const svg = d3.select("#svg").attr("width", W).attr("height", H);
const ax = svg.append("g").attr("class","axis");
for (let k=0;k<=kmax;k++){ax.append("line").attr("x1",x(k)).attr("x2",x(k)).attr("y1",m.t-8).attr("y2",H-m.b).attr("stroke-dasharray","2 4");
 ax.append("text").attr("x",x(k)).attr("y",m.t-14).attr("text-anchor","middle").text(k+" signal"+(k===1?"":"s"));}
const path = (a,b)=>{const mx=(x(a.k)+x(b.k))/2;return `M${x(a.k)},${y(a.y)} C${mx},${y(a.y)} ${mx},${y(b.y)} ${x(b.k)},${y(b.y)}`;};
const altG = svg.append("g"), treeG = svg.append("g"), nodeG = svg.append("g"), labG = svg.append("g");
const alts = []; N.forEach(d=>d.alt.forEach(j=>alts.push({s:N[j],t:d})));
const altP = altG.selectAll("path").data(alts).join("path").attr("d",e=>path(e.s,e.t)).attr("fill","none")
  .attr("stroke","var(--alt)").attr("stroke-width",1).attr("stroke-dasharray","1.5 3");
const tre = N.filter(d=>d.parent!==null).map(d=>({s:N[d.parent],t:d}));
const treP = treeG.selectAll("path").data(tre).join("path").attr("d",e=>path(e.s,e.t)).attr("fill","none")
  .attr("stroke","var(--edge)").attr("stroke-width",1.6).attr("stroke-opacity",.75);
const tip = document.getElementById("tip");
const circ = nodeG.selectAll("circle").data(N).join("circle").attr("cx",d=>x(d.k)).attr("cy",d=>y(d.y)).attr("r",d=>r(d.share))
  .attr("fill",d=>fam[d.family]).attr("stroke","var(--ring)").attr("stroke-width",2).style("cursor","pointer")
  .on("mousemove",(ev,d)=>{tip.style.display="block";tip.style.left=Math.min(ev.clientX+14, innerWidth-360)+"px";tip.style.top=(ev.clientY+14)+"px";
   const par = d.parent!==null?`#${N[d.parent].rank}`:"none (root)";
   const others = d.alt.length? d.alt.map(j=>"#"+N[j].rank+" (−"+N[d.id].signals.filter(s=>!N[j].signals.includes(s)).join(", ")+")").join("; ") : "none among the top 200";
   tip.innerHTML=`<b>#${d.rank}</b> · ${fmt(d.share)} of functions (${d3.format(",")(d.n)})<br>
   <span class="m">signals:</span> ${d.signals.length?d.signals.join(", "):"(none)"}<br>
   <span class="m">adds to parent ${par}:</span> ${d.added.length?d.added.join(", "):"—"}<br>
   <span class="m">other possible parents:</span> ${others}<br>
   <span class="m">spread:</span> ${d.repos} repos (largest ${d.top??"?"}%) · ${d.langs.map(l=>l[0]+" "+d3.format(".0%")(l[1])).join(", ")}<br>
   <span class="m">size:</span> ~${d.lines??"?"} lines · <span class="m">in tests:</span> ${d.tests??"?"}%<br><span class="m">family:</span> ${d.fam}`;
   const anc=new Set([d.id]); let p=d.parent; while(p!==null){anc.add(p);p=N[p].parent;}
   treP.attr("stroke-opacity",e=>anc.has(e.t.id)&&anc.has(e.s.id)?1:.15).attr("stroke-width",e=>anc.has(e.t.id)&&anc.has(e.s.id)?2.6:1.6);
   altP.attr("stroke",e=>e.t.id===d.id?"var(--ink2)":"var(--alt)").attr("stroke-opacity",e=>e.t.id===d.id?1:.25);
   circ.attr("opacity",c=>anc.has(c.id)||d.alt.includes(c.id)?1:.35);})
  .on("mouseleave",()=>{tip.style.display="none";treP.attr("stroke-opacity",.75).attr("stroke-width",1.6);altP.attr("stroke","var(--alt)").attr("stroke-opacity",1);circ.attr("opacity",1);});
labG.selectAll("text").data(N.filter(d=>d.rank<=12)).join("text").attr("x",d=>x(d.k)+r(d.share)+4).attr("y",d=>y(d.y)+4)
  .text(d=>"#"+d.rank+(d.added.length?"  + "+d.added.join(", "):"  (no signals)"));
document.getElementById("showalt").addEventListener("change",e=>altG.style("display",e.target.checked?null:"none"));
</script></body></html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
