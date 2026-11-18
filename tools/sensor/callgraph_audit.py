#!/usr/bin/env python3
"""What does the engine's call graph record and miss? Audit A (recorded edges by resolution) and B (independent recall against the source). Hypotheses CG1-CG3:
docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

    python tools/sensor/callgraph_audit.py [REPO ...]      (latest quarterly scan of each repository)"""
import collections
import json
import sqlite3
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import lang_validation as LV  # noqa: E402
import verify_functions as VF  # noqa: E402

REPOS = ["dpdk", "curl", "sphinx", "scapy", "sqlmap", "prometheus", "commons-lang", "commons-io", "ripgrep"]
CALLS = {"python": {"call"}, "go": {"call_expression"}, "java": {"method_invocation"}, "rust": {"call_expression"}, "c": {"call_expression"}}


def call_sites(lang, src):
    """[(callee simple name, form)] for every call in the file; form plain, member or path."""
    parser = LV._PARSERS.get(lang) or LV._PARSERS.setdefault(lang, LV.get_parser(lang))
    tree = parser.parse(src)
    out, stack = [], [tree.root_node]
    txt = lambda n: src[n.start_byte:n.end_byte].decode("utf8", "replace")  # noqa: E731
    while stack:
        n = stack.pop()
        if n.type in CALLS[lang]:
            if lang == "java":
                x = n.child_by_field_name("name")
                if x is not None:
                    out.append((txt(x), "member" if n.child_by_field_name("object") is not None else "plain"))
            else:
                f = n.child_by_field_name("function")
                if f is not None:
                    if f.type == "identifier":
                        out.append((txt(f), "plain"))
                    elif f.type == "attribute":
                        x = f.child_by_field_name("attribute")
                        out.append((txt(x), "member")) if x is not None else None
                    elif f.type in ("selector_expression", "field_expression"):
                        x = f.child_by_field_name("field")
                        out.append((txt(x), "member")) if x is not None else None
                    elif f.type in ("scoped_identifier", "qualified_identifier"):
                        out.append((txt(f).replace("::", ".").split(".")[-1], "path"))
        stack.extend(n.children)
    return out


def file_worker(job):
    repo, lang, commit, items = job
    out = []
    for fid, path in items:
        src = VF.get(repo, f"{commit}:{path}")
        if src is None:
            continue
        try:
            defs = set(LV.func_texts(lang, src))
            calls = set(call_sites(lang, src))
        except Exception:  # noqa: BLE001
            continue
        out.append((path, defs, calls))
    return out


def audit(repo):
    lang = LV.CFG[repo]
    snap = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))[-1]
    con = sqlite3.connect(f"file:{snap['db']}?mode=ro", uri=True)
    nf = con.execute("select count(*) from function_data").fetchone()[0]
    rows = con.execute("select count(*), sum(dst_func_id is null), sum(dst_func_id is not null and coalesce(candidates,1)<=1), sum(dst_func_id is not null and candidates>1) from fcall_data where kind='call'").fetchone()
    steps = con.execute("select step, count(*), sum(dst_func_id is null), sum(dst_func_id is not null and candidates>1) from fcall_data where kind='call' group by step order by 2 desc").fetchall()
    eng = collections.defaultdict(dict)
    for path, callee, anyres, uniq in con.execute("select f.file_path, c.callee, max(c.dst_func_id is not null), max(c.dst_func_id is not null and coalesce(c.candidates,1)<=1) from fcall_data c join file_data f on f.id=c.src_file_id where c.kind='call' group by f.file_path, c.callee"):
        eng[path][callee] = (anyres, uniq)
    files = [(i, p) for i, p in con.execute("select id, file_path from file_data") if p.endswith(LV.EXT[lang])]
    path = f"{BR.POOL}/{repo}"
    per = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for res in ex.map(file_worker, [(path, lang, snap["commit"], files[i : i + 60]) for i in range(0, len(files), 60)]):
            per += res
    defined = set().union(*[d for _, d, _ in per]) if per else set()
    stats = collections.defaultdict(lambda: [0, 0, 0, 0])  # form -> [pairs, any edge, resolved, unique]
    for p, _, calls in per:
        for name, form in calls:
            if name not in defined:
                continue
            e = eng.get(p, {}).get(name)
            for key in (form, "all"):
                s = stats[key]
                s[0] += 1
                if e is not None:
                    s[1] += 1
                    s[2] += int(e[0])
                    s[3] += int(e[1])
    return {"repo": repo, "lang": lang, "functions": nf, "rows": rows, "steps": steps, "stats": dict(stats), "files": len(per)}


def main():
    repos = sys.argv[1:] or REPOS
    res = {}
    for r in repos:
        a = audit(r)
        res[r] = a
        n, unres, uniq, amb = a["rows"]
        print(f"\n########## {r} ({a['lang']}): {a['functions']} functions, {a['files']} files parsed ##########")
        print(f"  A. recorded call edges {n}: unique target {100 * uniq / n:.0f}%, ambiguous target {100 * amb / n:.0f}%, unresolved {100 * unres / n:.0f}%")
        print("     by step (edges; share unresolved; share ambiguous): " + ", ".join(f"{s} {c} ({100 * (u or 0) / c:.0f}%; {100 * (m or 0) / c:.0f}%)" for s, c, u, m in a["steps"] if c >= 20))
        st = a["stats"]
        al = st["all"]
        print(f"  B. name-resolvable call pairs (file, callee name) found in the source: {al[0]}; the engine has a call edge for {100 * al[1] / al[0]:.0f}%, a resolved target for {100 * al[2] / al[0]:.0f}%, a unique target for {100 * al[3] / al[0]:.0f}%")
        print("     by call form (pairs; any edge; resolved; unique): " + "; ".join(f"{k} {v[0]} ({100 * v[1] / v[0]:.0f}%; {100 * v[2] / v[0]:.0f}%; {100 * v[3] / v[0]:.0f}%)" for k, v in st.items() if k != "all" and v[0] >= 20))
    print("\n=== VERDICTS ===")
    shares = {r: res[r]["rows"][3] / max(res[r]["rows"][2] + res[r]["rows"][3], 1) for r in res}
    nonc = [r for r in res if res[r]["lang"] in ("python", "java", "go")]
    cs = [r for r in res if res[r]["lang"] == "c"]
    if nonc and cs:
        print("  CG1 ambiguous share of resolved call edges: " + ", ".join(f"{r} {100 * v:.0f}%" for r, v in shares.items()) + f" (needs at least 25% in Python, Java and Go repositories, at most 20% in C): {'supported' if all(shares[r] >= 0.25 for r in nonc) and all(shares[r] <= 0.2 for r in cs) else 'not supported'}")

        def pooled(group, k, form="all"):
            t = [res[r]["stats"].get(form, [0, 0, 0, 0]) for r in group]
            a = sum(x[0] for x in t)
            return sum(x[k] for x in t) / a if a else float("nan")

        print(f"  CG2 independent recall (any edge): non-C (python, java, go, rust) pooled {100 * pooled([r for r in res if res[r]['lang'] != 'c'], 1):.0f}% (needs 85% or less); C pooled {100 * pooled(cs, 1):.0f}% (needs 90% or more): " + ("supported" if pooled([r for r in res if res[r]['lang'] != 'c'], 1) <= 0.85 and pooled(cs, 1) >= 0.9 else "not supported"))
        allnc = [r for r in res if res[r]["lang"] != "c"]
        pl, me = pooled(allnc, 1, "plain"), pooled(allnc, 1, "member")
        print(f"  CG3 non-C recall by form: plain {100 * pl:.0f}%, member {100 * me:.0f}% (needs plain at least 10 points above member): {'supported' if pl - me >= 0.10 else 'not supported'}")
        low = pooled(allnc, 1)
        print(f"  surprise bar (non-C recall below 50%): {'MET' if low < 0.5 else 'not met'} ({100 * low:.0f}%)")


if __name__ == "__main__":
    main()
