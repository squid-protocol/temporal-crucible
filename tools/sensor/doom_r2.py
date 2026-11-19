#!/usr/bin/env python3
"""DOOM-R2: is the cross-lineage neighbour overlap one inherited defect or coupling? Hypotheses RD1-RD3: docs/sensor-overhaul/sensors/doom_ports_plan.md section 9, fixed before running.
    python tools/sensor/doom_r2.py"""
import collections
import pickle
import re
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import doom_r1 as D  # noqa: E402
import lang_validation as LV  # noqa: E402
import repair_structure as RS  # noqa: E402
import verify_functions as VF  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
rng = np.random.default_rng(2982)
COMMENT = re.compile(r"^\s*(/\*|\*|//)")


def func_lines(src):
    parser = LV._PARSERS.get("c") or LV._PARSERS.setdefault("c", LV.get_parser("c"))
    tree = parser.parse(src)
    out, stack = {}, [tree.root_node]
    while stack:
        n = stack.pop()
        if n.type == "function_definition":
            nm = RS.func_name(n, src)
            if nm and nm not in out:
                ls = [re.sub(r"\s+", " ", l.strip()) for l in src[n.start_byte:n.end_byte].decode("utf8", "replace").splitlines()]
                out[nm] = [l for l in ls if len(l) > 3 and not COMMENT.match(l)]
            continue
        stack.extend(n.children)
    return out


def lines_worker(job):
    repo, shas, refnames = job
    res = {}
    for sha in shas:
        d = {}
        for status, old, new in LV.name_status(repo, sha, "c"):
            if status not in "MR":
                continue
            a, b = VF.get(repo, f"{sha}:{new}"), VF.get(repo, f"{sha}^:{old}")
            if a is None or b is None:
                continue
            try:
                fa, fb = func_lines(a), func_lines(b)
            except Exception:  # noqa: BLE001
                continue
            for n in fa:
                if n in fb and fa[n] != fb[n] and D.norm(n) in refnames:
                    d.setdefault(D.norm(n), (frozenset(set(fb[n]) - set(fa[n])), frozenset(set(fa[n]) - set(fb[n]))))
        res[sha] = d
    return res


def jac(a, b):
    return len(a & b) / len(a | b) if (a or b) else 0.0


def sim(x, y):
    """similarity of two repairs of one function: removed lines, or added lines when neither removes anything."""
    (ra, aa), (rb, ab) = x, y
    if ra and rb:
        return jac(ra, rb)
    if not ra and not rb:
        return jac(aa, ab)
    return 0.0


def main():
    g = BR.Graph(D.REFDB)
    keys = sorted(g.index, key=g.index.get)
    name_nodes = collections.defaultdict(list)
    for i, (p, n) in enumerate(keys):
        if g.loc[i] >= 3:
            name_nodes[D.norm(n)].append(i)
    refnames = set(name_nodes)
    cache = {}

    def n2(name):
        if name not in cache:
            near = g.near(np.array(name_nodes[name], dtype=np.int64))["either2"]
            cache[name] = sorted({D.norm(keys[i][1]) for i in np.nonzero(near)[0] if D.norm(keys[i][1]) in refnames} - {name})
        return cache[name]

    lineages = D.LIN + [D.CTRL]
    obs, fixes_of, lines = {}, {}, {}
    for repo in lineages:
        pairs, info = LV.build(repo, 3000)
        path = f"{BR.POOL}/{repo}"
        fshas = list(dict.fromkeys(p["fix"] for p in pairs))
        cf = f"{B}/blast/doom_r2_lines_{repo}.pkl"
        try:
            lines[repo] = pickle.load(open(cf, "rb"))
        except Exception:  # noqa: BLE001
            lines[repo] = {}
            with ProcessPoolExecutor(max_workers=6) as ex:
                for r in ex.map(lines_worker, [(path, fshas[i : i + 25], refnames) for i in range(0, len(fshas), 25)]):
                    lines[repo].update(r)
            pickle.dump(lines[repo], open(cf, "wb"))
        o = collections.defaultdict(set)
        fo = collections.defaultdict(set)
        for p in pairs:
            Fn = {D.norm(x[1]) for x in info[p["fix"]][0]} & refnames
            In = {D.norm(x[1]) for x in info[p["ind"]][0]} & refnames
            for gname in Fn:
                fo[gname].add(p["fix"])
            for f in In:
                nb = set(n2(f))
                for gname in Fn:
                    if gname != f and gname in nb:
                        o[(f, gname)].add(p["fix"])
        obs[repo], fixes_of[repo] = o, fo
        print(f"{repo}: {len(pairs)} pairs, {len(o)} inherited (F, G) observations, {sum(len(v) for v in lines[repo].values())} repaired-function texts", flush=True)

    def s_between(A, B, f, gname, G=None):
        G = G or gname
        best = 0.0
        fa = obs[A].get((f, gname)) if (f, gname) in obs[A] else fixes_of[A].get(G, set())
        fb = obs[B].get((f, gname)) if (f, gname) in obs[B] else fixes_of[B].get(G, set())
        for x in fa:
            lx = lines[A].get(x, {}).get(G)
            if lx is None:
                continue
            for y in fb:
                ly = lines[B].get(y, {}).get(G)
                if ly is not None:
                    best = max(best, sim(lx, ly))
        return best

    def overlaps(A, B):
        return [(f, gname) for (f, gname) in obs[A] if (f, gname) in obs[B]]

    ok = [r for r in D.LIN if len(obs[r]) >= 30]
    pairs_ab = [(a, b) for i, a in enumerate(ok) for b in ok[i + 1 :]]
    ov = [(a, b, f, g_, s_between(a, b, f, g_)) for a, b in pairs_ab for f, g_ in overlaps(a, b)]
    same = sum(1 for *_, s in ov if s >= 0.5)
    print(f"\ncross-lineage overlaps among the {len(ok)} independent lineages: {len(ov)}; the same defect (similarity at least 0.5): {same} ({100 * same / len(ov):.0f}%); not the same defect: {len(ov) - same}")
    # popularity-matched null with the same similarity computed on the drawn function
    def draw(f, A):
        nb = n2(f)
        if not nb:
            return None
        w = np.array([len(fixes_of[A].get(x, ())) + 0.5 for x in nb])
        return nb[int(rng.choice(len(nb), p=w / w.sum()))]

    null_tot, null_non = [], []
    for _ in range(100):
        draws = {r: {(f, draw(f, r)) for f, _ in obs[r] if n2(f)} for r in ok}
        tot = non = 0
        for a, b in pairs_ab:
            for (f, gname) in draws[a] & draws[b]:
                tot += 1
                # similarity of the drawn function's repairs in the two lineages
                best = 0.0
                for x in fixes_of[a].get(gname, ()):
                    for y in fixes_of[b].get(gname, ()):
                        lx, ly = lines[a].get(x, {}).get(gname), lines[b].get(y, {}).get(gname)
                        if lx is not None and ly is not None:
                            best = max(best, sim(lx, ly))
                non += best < 0.5
        null_tot.append(tot)
        null_non.append(non)
    print(f"popularity-matched null (100 permutations): overlaps {np.mean(null_tot):.1f}, of which not the same defect {np.mean(null_non):.1f}")
    ctrl = [(f, g_, s_between(D.CTRL, "crispy-doom", f, g_)) for f, g_ in overlaps(D.CTRL, "crispy-doom")]
    cs = sum(1 for *_, s in ctrl if s >= 0.5)
    print(f"positive control chocolate-doom with crispy-doom (shared commits): {len(ctrl)} overlaps, the same defect {cs} ({100 * cs / max(len(ctrl), 1):.0f}%)")
    sh = [s for *_, s in ov]
    print(f"similarity of the cross-lineage overlaps: median {np.median(sh):.2f}; share exactly 0: {100 * np.mean([x == 0 for x in sh]):.0f}%; share at least 0.8: {100 * np.mean([x >= 0.8 for x in sh]):.0f}%")
    print("\n=== VERDICTS ===")
    non_obs = len(ov) - same
    ratio = non_obs / max(np.mean(null_non), 1e-9)
    print(f"  RD1 same-defect share of the overlaps {100 * same / len(ov):.0f}% (needs under 50%): {'supported' if same / len(ov) < 0.5 else 'not supported'}")
    print(f"  RD2 not-the-same-defect overlaps {non_obs} against null {np.mean(null_non):.1f} = {ratio:.2f} (needs 1.5): {'supported' if ratio >= 1.5 else 'not supported'}")
    print(f"  RD3 positive control same-defect share {100 * cs / max(len(ctrl), 1):.0f}% (needs 80%): {'supported' if cs / max(len(ctrl), 1) >= 0.8 else 'not supported'}")
    print(f"  surprise bar (more than 80% same defect and RD2 at or below 1.2): {'MET' if same / len(ov) > 0.8 and ratio <= 1.2 else 'not met'}")


if __name__ == "__main__":
    main()
