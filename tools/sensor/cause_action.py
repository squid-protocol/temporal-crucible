#!/usr/bin/env python3
"""What the cause did to the identifiers its repairs share. Hypotheses CA1-CA5: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

    python tools/sensor/cause_action.py linux dpdk mesa openssl"""
import collections
import re
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import repair_structure as RS  # noqa: E402
import what_changes as W  # noqa: E402

rng = np.random.default_rng(2982)
RELS = RS.RELS
ACTIONS = ["defined", "redefined or signature changed", "definition removed", "check added, changed or removed", "new use", "use removed", "use changed"]
GENERIC_DEF = [re.compile(r"\s*#\s*define\s+\w+"), re.compile(r"^[A-Za-z_][\w\s\*]*\b\w+\s*\([^;{]*\)?\s*[;{]?\s*$"), re.compile(r"^\s+(?:(?:struct|enum|union|const|volatile|unsigned|signed)\s+)*[A-Za-z_][\w\s\*]*[\s\*]\w+\s*(\[[^\]]*\])?\s*(:\s*\d+)?\s*;\s*$"), re.compile(r"^\s*\w+\s*(=[^,]*)?,\s*$")]
COND = re.compile(r"\b(if|while|for)\s*\(|\?")


def diff_lines(repo, shas):
    out = subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "log", "--no-walk=unsorted", "--stdin", "-p", "-U0", "--no-color", "--format=@@COMMIT %H", "--", "*.c", "*.h"], input="\n".join(shas) + "\n", capture_output=True, text=True, errors="replace").stdout
    res, cur, path = collections.defaultdict(list), None, None
    for l in out.splitlines():
        if l.startswith("@@COMMIT "):
            cur = l[9:].strip()
        elif l.startswith("+++ b/"):
            path = l[6:]
        elif cur and path and l[:1] in "+-" and not l.startswith(("+++", "---")):
            t = RS.STRING.sub(" ", l[1:])
            if t.strip() and not t.strip().startswith(("*", "/*", "//")):
                res[cur].append((path, l[0], t.rstrip()))
    return res


def action(name, lines):
    pat = re.compile(rf"\b{re.escape(name)}\b")
    defs = [re.compile(rf"\s*#\s*define\s+{re.escape(name)}\b"), re.compile(rf"^[A-Za-z_][\w\s\*]*\b{re.escape(name)}\s*\("), re.compile(rf"^\s+(?:(?:struct|enum|union|const|volatile|unsigned|signed)\s+)*[A-Za-z_][\w\s\*]*[\s\*]{re.escape(name)}\s*(\[[^\]]*\])?\s*(:\s*\d+)?\s*;\s*$"), re.compile(rf"^\s*{re.escape(name)}\s*(=[^,]*)?,\s*$")]
    occ = [(p, s, t) for p, s, t in lines if pat.search(t)]
    if not occ:
        return None, False
    dl = [(p, s) for p, s, t in occ if any(d.match(t) for d in defs)]
    if dl:
        sg = {s for _, s in dl}
        hdr = any(p.endswith(".h") for p, _ in dl)
        return ("redefined or signature changed" if len(sg) == 2 else "defined" if sg == {"+"} else "definition removed"), hdr
    sg = {s for _, s, _ in occ}
    cond = any(COND.search(t) for _, _, t in occ)
    if cond:
        return "check added, changed or removed", False
    return ("use changed" if len(sg) == 2 else "new use" if sg == {"+"} else "use removed"), False


def cause_interface(lines):
    return any(p.endswith(".h") and any(g.match(t) for g in GENERIC_DEF) for p, s, t in lines)


def main():
    repos = sys.argv[1:]
    toks, pairs = [], []
    for repo in repos:
        d = W.load(repo)
        dl = diff_lines(repo, list(d.ind.unique()))
        for r in d.itertuples():
            for n, cls in r.shared:
                a, hdr = action(n, dl[r.ind])
                if a:
                    toks.append({"repo": repo, "pid": r.pid, "rel": r.rel, "label": r.label, "name": n, "cls": cls, "action": a, "hdr_def": hdr and a in ("defined", "redefined or signature changed", "definition removed")})
        g = d.groupby("pid").agg(ind=("ind", "first"), far=("rel", lambda x: float(x.isin(["same file, farther", "elsewhere"]).mean())), els=("rel", lambda x: float((x == "elsewhere").mean())))
        g["repo"] = repo
        g["iface"] = [cause_interface(dl[i]) for i in g.ind]
        pairs.append(g)
        print(f"{repo}: {len(d)} records; {sum(1 for t in toks if t['repo'] == repo)} classified shared identifiers", flush=True)
    t = pd.DataFrame(toks)
    pr = pd.concat(pairs)
    print(f"\n{len(t)} (pair, fixed function, shared identifier) tokens; {len(pr)} pairs")
    print("\n=== cause action on the shared identifier, by relation of the repair (row shares) ===")
    tab = pd.crosstab(t.rel, t.action).reindex(columns=ACTIONS, fill_value=0)
    sh = tab.div(tab.sum(axis=1), axis=0)
    print(f"  {'':20s}" + "".join(f"{a[:16]:>17s}" for a in ACTIONS) + "   header def   n")
    for rel in RELS:
        if rel in sh.index:
            x = t[t.rel == rel]
            print(f"  {rel:20s}" + "".join(f"{100 * sh.loc[rel, a]:16.1f}%" for a in ACTIONS) + f"   {100 * x.hdr_def.mean():8.1f}%  {len(x)}")
    print(f"  {'ALL':20s}" + "".join(f"{100 * (t.action == a).mean():16.1f}%" for a in ACTIONS) + f"   {100 * t.hdr_def.mean():8.1f}%  {len(t)}")
    print("\n=== by identifier class (what kind of name), cause action row shares ===")
    tab2 = pd.crosstab(t.cls, t.action).reindex(columns=ACTIONS, fill_value=0)
    for c in tab2.index:
        print(f"  {c:10s}" + "".join(f"{100 * tab2.loc[c, a] / tab2.loc[c].sum():16.1f}%" for a in ACTIONS) + f"   n {int(tab2.loc[c].sum())}")
    far = t[t.rel.isin(["callee", "two calls away", "same file, farther", "elsewhere"])]
    same = t[t.rel == "same"]
    uses = t.action.isin(["new use", "use removed", "use changed", "check added, changed or removed"]).mean()
    print(f"\n  CA1 uses and checks {100 * uses:.0f}% of the shared identifiers (needs 60%): {'supported' if uses >= 0.6 else 'not supported'}")
    print(f"  CA2 header definitions among shared identifiers: repairs not in the same function {100 * far.hdr_def.mean():.1f}% against same function {100 * same.hdr_def.mean():.1f}% = {far.hdr_def.mean() / max(same.hdr_def.mean(), 1e-9):.2f} (needs 1.5): {'supported' if far.hdr_def.mean() >= 1.5 * same.hdr_def.mean() else 'not supported'}")
    a, b = pr[pr.iface].far.to_numpy(), pr[~pr.iface].far.to_numpy()
    bs = [rng.choice(a, len(a)).mean() / max(rng.choice(b, len(b)).mean(), 1e-9) for _ in range(500)]
    print(f"  CA3 share of repairs in 'same file, farther' or 'elsewhere': causes with an interface change {100 * a.mean():.1f}% (n {len(a)}) against without {100 * b.mean():.1f}% (n {len(b)}) = {a.mean() / b.mean():.2f} [{np.percentile(bs, 2.5):.2f},{np.percentile(bs, 97.5):.2f}] (needs 1.3): {'supported' if a.mean() >= 1.3 * b.mean() else 'not supported'}")
    a2, b2 = pr[pr.iface].els.to_numpy(), pr[~pr.iface].els.to_numpy()
    print(f"      'elsewhere' alone: {100 * a2.mean():.1f}% against {100 * b2.mean():.1f}% = {a2.mean() / b2.mean():.2f}; pairs with an interface change: {100 * pr.iface.mean():.0f}%")
    g = lambda x: x.label.isin(["adds a guard", "changes a condition"]).mean()  # noqa: E731
    ck, ot = t[t.action == "check added, changed or removed"], t[t.action != "check added, changed or removed"]
    print(f"  CA4 repair adds a guard or changes a condition: after 'check' actions {100 * g(ck):.1f}% against {100 * g(ot):.1f}% for the others = {g(ck) / g(ot):.2f} (needs 1.3): {'supported' if g(ck) >= 1.3 * g(ot) else 'not supported'}")
    ca = lambda x: x.label.isin(["changes a call's arguments", "replaces a callee"]).mean()  # noqa: E731
    rs = t[t.action == "redefined or signature changed"]
    print(f"  CA5 repair changes call arguments or replaces a callee: after 'redefined or signature changed' {100 * ca(rs):.1f}% against {100 * ca(t):.1f}% for all = {ca(rs) / ca(t):.2f} (needs 1.5): {'supported' if ca(rs) >= 1.5 * ca(t) else 'not supported'}")
    print("\n=== cause action x repair edit type: row shares (top edit types) ===")
    top = list(t.label.value_counts().index[:7])
    for a_ in ACTIONS:
        x = t[t.action == a_]
        print(f"  {a_[:30]:30s} n {len(x):6d} " + "  ".join(f"{l[:13]} {100 * (x.label == l).mean():4.1f}%" for l in top))
    print(f"  {'ALL':30s} n {len(t):6d} " + "  ".join(f"{l[:13]} {100 * (t.label == l).mean():4.1f}%" for l in top))
    print("\n=== per repository: shares of cause actions, and CA3 ===")
    for r in repos:
        x = t[t.repo == r]
        p = pr[pr.repo == r]
        print(f"  {r:8s} n {len(x):6d}  " + ", ".join(f"{a_.split(' ')[0]} {100 * (x.action == a_).mean():.0f}%" for a_ in ACTIONS) + f";  CA3 far share with interface change {100 * p[p.iface].far.mean():.1f}% vs without {100 * p[~p.iface].far.mean():.1f}%  (pairs with an interface change {100 * p.iface.mean():.0f}%)")
    t.to_pickle("/tmp/gitgalaxy-scratch/claude/blast/cause_action.pkl")


if __name__ == "__main__":
    main()
