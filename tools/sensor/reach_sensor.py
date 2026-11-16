#!/usr/bin/env python3
"""Reach sensor: who depends on a file, from a GitGalaxy scan database plus the source tree.

    python tools/sensor/reach_sensor.py SCAN_DB SRC_ROOT [--top N] [--json OUT] [--all-roles]

Per source file: distinct caller files, caller functions, callers one hop out. Per header: files that #include it
(resolved by path, so same-named headers in different folders stay separate). Files the call graph cannot see are
reported as 'not measured' with a reason. Counts are lower bounds: calls to names the engine cannot resolve are not recorded.
No risk or defect claim."""
import argparse, os, collections, json, pathlib, re, sqlite3, sys

HDR = (".h", ".hpp", ".hh", ".hxx")
INC = re.compile(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', re.M)
TEXT = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx")

def role(p):
    if re.search(r"(^|/)(tests?|examples?|fuzz\w*|docs?|bench\w*)(/|$)", p): return "tests/docs"
    if p.startswith(".github/") or p.endswith((".yml", ".yaml")): return "ci/config"
    return "source"

def include_counts(src_root, paths):
    """Map header path -> set of including files. 'a/b.h' resolves to the unique-or-nearest header whose path ends with it."""
    by_tail = collections.defaultdict(list)
    for p in paths:
        if p.endswith(HDR): by_tail[pathlib.PurePosixPath(p).name].append(p)
    out = collections.defaultdict(set); root = pathlib.Path(src_root)
    for p in paths:
        if not p.endswith(TEXT): continue
        try: text = (root / p).read_text("utf8", "replace")
        except OSError: continue
        for h in INC.findall(text):
            cands = by_tail.get(pathlib.PurePosixPath(h).name, [])
            if not cands: continue
            tail = [c for c in cands if c.endswith("/" + h) or c == h] if "/" in h else []
            if tail: pick = tail
            else:  # same-directory or search-path include: prefer the includer's own folder, else the closest shared prefix
                here = str(pathlib.PurePosixPath(p).parent)
                pick = [c for c in cands if str(pathlib.PurePosixPath(c).parent) == here] or cands
                if len(pick) > 1:
                    best = max(len(os.path.commonpath([p, c])) for c in pick)
                    pick = [c for c in pick if len(os.path.commonpath([p, c])) == best][:1]
            for c in pick:
                if c != p: out[c].add(p)
    return out

def build(db, src_root):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    files = {r[0]: r[1:] for r in con.execute("select id,file_path,language,function_count from file_data")}
    funcs = {r[0]: r[1:] for r in con.execute("select id,file_id,func_name,is_public from function_data")}
    edges = con.execute("select src_func_id,src_file_id,dst_func_id,dst_file_id from fcall_data where dst_func_id is not null").fetchall()
    fcallers = collections.defaultdict(set); fcfiles = collections.defaultdict(set)
    callfiles = collections.defaultdict(set); callfuncs = collections.defaultdict(set)
    for sf, sfile, df, dfile in edges:
        fcallers[df].add(sf); fcfiles[df].add(sfile)
        if sfile != dfile: callfiles[dfile].add(sfile); callfuncs[dfile].add(sf)
    by_file = collections.defaultdict(list)
    for k, v in funcs.items(): by_file[v[0]].append(k)
    incl = include_counts(src_root, [v[0] for v in files.values()])
    rows, nm = [], []
    for fid, (p, lang, fc) in files.items():
        if p.endswith(HDR):
            rows.append(dict(path=p, kind="header", role=role(p), reach_files=len(incl.get(p, ())), measured_by="include count")); continue
        if fc and fc >= 1:
            two = set()
            for fn in by_file.get(fid, ()):
                for c in fcallers.get(fn, ()): two |= fcallers.get(c, set())
            rows.append(dict(path=p, kind="source", role=role(p), reach_files=len(callfiles.get(fid, ())), caller_functions=len(callfuncs.get(fid, ())), one_hop_out=len(two), measured_by="call graph"))
        else:
            nm.append(dict(path=p, reason="no functions found" if not fc else "unknown"))
    pub = []
    for k, (fid, name, is_pub) in funcs.items():
        n = len(fcfiles.get(k, set()) - {fid})
        if is_pub and n: pub.append(dict(function=name, path=files[fid][0], called_from_files=n))
    pub.sort(key=lambda r: -r["called_from_files"])
    return dict(files=len(files), rows=rows, not_measured=nm, public_functions=pub)

def report(R, top=8, all_roles=False):
    rows = [r for r in R["rows"] if all_roles or r["role"] == "source"]
    src = sorted((r for r in rows if r["kind"] == "source"), key=lambda r: -r["reach_files"])
    hd = sorted((r for r in rows if r["kind"] == "header"), key=lambda r: -r["reach_files"])
    c = collections.Counter(r["measured_by"] for r in R["rows"])
    L = [f"REACH  {R['files']} files; measured by call graph {c['call graph']}, by include count {c['include count']}, not measured {len(R['not_measured'])} (no functions, not a header).",
         "Counts are lower bounds: calls to standard-library names and macros are not recorded."]
    L.append("Files the most other files call into:")
    for r in src[:top]: L.append(f"  {r['path']:48s} {r['reach_files']:4d} caller files {r['caller_functions']:5d} caller functions {r['one_hop_out']:5d} one hop out")
    L.append("Most-used public functions:")
    for r in R["public_functions"][:top]: L.append(f"  {r['function']:34s} {r['path']:40s} {r['called_from_files']} files")
    L.append("Headers by number of files that include them:")
    for r in hd[:top]: L.append(f"  {r['path']:48s} {r['reach_files']:4d} files")
    return "\n".join(L)

def main(a=None):
    ap = argparse.ArgumentParser(); ap.add_argument("db"); ap.add_argument("src"); ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--json"); ap.add_argument("--all-roles", action="store_true"); n = ap.parse_args(a)
    R = build(n.db, n.src); print(report(R, n.top, n.all_roles))
    if n.json: pathlib.Path(n.json).write_text(json.dumps(R, indent=1))
if __name__ == "__main__": main()
