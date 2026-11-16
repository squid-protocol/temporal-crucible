#!/usr/bin/env python3
"""LANG-H1..H3 (docs/sensor-overhaul/sensors/library_surface_languages_registration.md): import coupling to a library vs where its work lands,
in Go, Python, Java and Rust. The library table below is the registered one, verbatim. python tools/sensor/lib_surface_lang_eval.py [REPO ...]"""
import sys, re, json, sqlite3, pathlib, collections
import numpy as np
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import lib_eval as LE
from sc_discover import recall20
from _engine import REPO_ROOT, POOL_DIR
DB = pathlib.Path("/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2/libsurface")
EXT = {"prometheus": (".go",), "sphinx": (".py",), "commons-lang": (".java",), "ripgrep": (".rs",)}
DEPS = {
 "prometheus": [("k8s", r"^k8s\.io/", "kubernetes|k8s"), ("aws", r"^github\.com/aws/", "aws|ec2|lightsail"), ("azure", r"^github\.com/Azure/", "azure"),
   ("consul", r"^github\.com/hashicorp/consul", "consul"), ("grpc", r"^google\.golang\.org/grpc", "grpc"), ("kingpin", r"^github\.com/alecthomas/kingpin", "kingpin"),
   ("fsnotify", r"^github\.com/fsnotify/", "fsnotify"), ("opentelemetry", r"^go\.opentelemetry\.io/", "otel|opentelemetry"),
   ("docker", r"^github\.com/(?:docker|moby)/", "docker|swarm"), ("openstack", r"^github\.com/gophercloud/", "openstack")],
 "sphinx": [("docutils", r"^docutils(?:\.|$)", "docutils"), ("jinja2", r"^jinja2(?:\.|$)", "jinja"), ("pygments", r"^pygments(?:\.|$)", "pygments"),
   ("babel", r"^babel(?:\.|$)", "babel"), ("requests", r"^requests(?:\.|$)", "requests"), ("alabaster", r"^alabaster(?:\.|$)", "alabaster"),
   ("imagesize", r"^imagesize", "imagesize"), ("snowballstemmer", r"^snowballstemmer", "snowball"), ("sphinxcontrib", r"^sphinxcontrib", "sphinxcontrib"),
   ("pytest", r"^pytest(?:\.|$)", "pytest")],
 "commons-lang": [("junit", r"^org\.junit", "junit"), ("easymock", r"^org\.easymock", "easymock"), ("mockito", r"^org\.mockito", "mockito"),
   ("hamcrest", r"^org\.hamcrest", "hamcrest"), ("jmh", r"^org\.openjdk\.jmh", "jmh"), ("commons-text", r"^org\.apache\.commons\.text", r"commons.text|commons-text")],
 "ripgrep": [("serde", r"^serde(?:_\w+)?(?:::|$)", "serde"), ("termcolor", r"^termcolor(?:::|$)", "termcolor"), ("bstr", r"^bstr(?:::|$)", "bstr"),
   ("anyhow", r"^anyhow(?:::|$)", "anyhow"), ("memchr", r"^memchr(?:::|$)", "memchr"), ("pcre2", r"^pcre2(?:::|$)", "pcre2"), ("crossbeam", r"^crossbeam", "crossbeam"),
   ("walkdir", r"^walkdir(?:::|$)", "walkdir"), ("encoding_rs", r"^encoding_rs", "encoding"), ("regex", r"^regex(?:::|$)", "regex")],
}

def work_commits(repo):
    walk = json.loads((REPO_ROOT / "walks" / f"{repo}_quarterly.json").read_text()); ex = EXT[repo]
    subj = {d: re.compile(rf"\b(?:{s})\b", re.I) for d, _, s in DEPS[repo]}
    raw = LE._git(POOL_DIR / repo, "-c", "core.quotepath=off", "log", "--no-merges", "--name-only", "--format=%x00%H%x1f%ct%x1f%s", walk["events_head"])
    out = collections.defaultdict(list)
    for chunk in raw.split("\x00")[1:]:
        head, _, files = chunk.partition("\n"); h, ct, s = head.split("\x1f", 2)
        cf = [f for f in files.splitlines() if f.strip() and f.endswith(ex)]
        if not 1 <= len(cf) <= 50: continue
        for d, rx in subj.items():
            if rx.search(s): out[d].append({"sha": h, "ct": int(ct), "files": cf})
    return out

def snapshot(db, ex, deps):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try: rows = [(p, max(l or 0, 1), json.loads(i or "[]")) for p, l, i in con.execute("select file_path,total_loc,raw_imports from file_data")]
    finally: con.close()
    rows = [r for r in rows if r[0].endswith(ex)]; rxs = {d: re.compile(rx) for d, rx, _ in deps}
    return {p: l for p, l, _ in rows}, {d: {p: sum(1 for i in imps if rxs[d].search(i)) for p, _, imps in rows} for d in rxs}

def run(repo):
    walk = json.loads((REPO_ROOT / "walks" / f"{repo}_quarterly.json").read_text()); snaps = [s for s in walk["revisions"] if s.get("status", "ok") == "ok"]
    for s in snaps: s["ct"] = int(LE._git(POOL_DIR / repo, "show", "-s", "--format=%ct", s["sha"]).strip())
    work = work_commits(repo); deps = DEPS[repo]; names = [d for d, _, _ in deps]; tok = {d: [t.strip().lower() for t in re.split(r"\|", s) if t.strip()] for d, _, s in deps}
    per = collections.defaultdict(list)
    for i, s in enumerate(snaps):
        dbs = list((DB / repo).glob(f"{i:03d}_*.db"))
        if not dbs: continue
        lines, coup = snapshot(dbs[0], EXT[repo], deps)
        if not lines: continue
        paths = sorted(lines); loc = np.array([float(lines[p]) for p in paths]); pr = np.argsort(np.argsort(np.array(paths)))
        S = {d: np.array([coup[d][p] for p in paths], dtype=float) / loc for d in names}
        for d in names:
            touched = set()
            for c in work[d]:
                if s["ct"] < c["ct"] <= s["ct"] + LE.WINDOW * LE.DAY: touched.update(c["files"])
            y = np.array([1.0 if p in touched else 0.0 for p in paths])
            if y.sum() == 0: continue
            base = max(recall20(loc, loc, pr, y), recall20(-loc, loc, pr, y)); r = recall20(S[d], loc, pr, y)
            others = float(np.mean([recall20(S[o], loc, pr, y) for o in names if o != d]))
            nm = np.array([1.0 if any(t.replace(".", "") in p.lower().replace("-", "").replace("_", "").replace(".", "") or t in p.lower() for t in tok[d]) else 0.0 for p in paths])
            per[d].append({"r": r, "base": base, "h1": r - base, "h2": r - others, "h3": r - recall20(nm, loc, pr, y), "coupled": int((S[d] > 0).sum())})
    return per

def main():
    repos = sys.argv[1:] or list(DEPS); rng = np.random.default_rng(2982); units = {}
    print(f"{'repo':13s} {'library':16s} {'snaps':>5s} {'coupling':>8s} {'size':>6s} {'H1':>7s} {'H2':>7s} {'H3':>7s} {'coupled files (mean)':>20s}")
    for repo in repos:
        for d, v in run(repo).items():
            if len(v) < LE.MIN_SNAPS: print(f"{repo:13s} {d:16s} {len(v):5d}   not evaluable (< {LE.MIN_SNAPS} snapshots with library work)"); continue
            m = lambda k: float(np.mean([x[k] for x in v])); units[(repo, d)] = v
            print(f"{repo:13s} {d:16s} {len(v):5d} {m('r'):8.3f} {m('base'):6.3f} {m('h1'):+7.3f} {m('h2'):+7.3f} {m('h3'):+7.3f} {m('coupled'):20.1f}")
    for scope, keep in [("ALL", lambda k: True)] + [(r, (lambda rr: lambda k: k[0] == rr)(r)) for r in repos]:
        for name, key in (("LANG-H1 vs size", "h1"), ("LANG-H2 vs other libraries (placebo)", "h2"), ("LANG-H3 vs file-name lookup", "h3")):
            arrs = [np.array([x[key] for x in v]) for k, v in units.items() if keep(k)]
            if not arrs: continue
            mean = float(np.mean([a.mean() for a in arrs])); b = np.array([np.mean([a[rng.integers(0, len(a), len(a))].mean() for a in arrs]) for _ in range(5000)])
            lo = float(np.quantile(b, LE.ALPHA)); verdict = "SUPPORTED" if mean > 0 and lo > 0 else "not supported"
            print(f"[{scope:12s}] {name:38s} units {len(arrs):2d} mean {mean:+.3f} lower bound (alpha 0.0033) {lo:+.3f}  90% CI [{np.quantile(b,.05):+.3f}, {np.quantile(b,.95):+.3f}]  {verdict}")
if __name__ == "__main__": main()
