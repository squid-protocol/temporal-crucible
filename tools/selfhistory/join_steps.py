#!/usr/bin/env python3
"""EXPLORATORY join: for each interval between adjacent speed slots, line up
  (1) the measured speed step (CPU seconds per mapped file, per target; stage costs where timed),
  (2) the commits in the interval (first-parent): messages, files touched by kind, lines changed,
  (3) function-structure change of the scan-path engine code between the two anchor DBs,
  (4) commit messages that name a performance change.
Writes join/steps.json and join/steps.md. Nothing here is a confirmatory result."""
import gzip, json, re, sqlite3, statistics as st, subprocess
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIRROR = HERE / "mirror.git"
OUT = HERE / "join"; OUT.mkdir(exist_ok=True)
TARGETS = ["keyword-rosetta", "cics-crucible", "language-crucible"]
PERF = re.compile(r"\b(perf|performance|speed|fast(er)?|optimi[sz]\w*|O\(N|O\(n|quadratic|linear|cache[sd]?|caching|precompute\w*|memoi[sz]\w*|"
                  r"backtrack\w*|redos|slow\w*|timeout|hot ?path|bottleneck|throughput|latency|vectori[sz]\w*|batch\w*|prefetch\w*|"
                  r"hash ?map|lookup|index(ed)? )", re.I)


def git(*a):
    return subprocess.run(["git", "--git-dir", str(MIRROR), *a], check=True, capture_output=True, text=True, errors="replace").stdout


def kind(p):
    if p.startswith(("tests/", "test/")): return "tests"
    if p.startswith(("docs/", "site/", "templates/", ".github/", ".claude/")) or p.endswith((".md", ".txt")): return "docs"
    if "/standards/" in p or "gitgalaxy_standards" in p: return "standards"      # pattern tables / rule data
    if p.startswith("gitgalaxy/tools/"): return "translator_tools"
    if p.startswith(("gitgalaxy/", "backend/")): return "core"                    # the scan path
    return "other"


# ---- slots and speed ------------------------------------------------------------------------------
picks = [l.split("\t") for l in (HERE / "picks.tsv").read_text().split("\n") if l]
n = 12
idx = sorted({round(k * (len(picks) - 1) / (n - 1)) for k in range(n)})
slots = [{"slot": f"s{k:02d}", "date": picks[i][0], "sha": picks[i][1]} for k, i in enumerate(idx)]
runs = [json.loads(l) for l in (HERE / "speed" / "runs.jsonl").open()]
files_re = re.compile(r"(?:PIPELINE_SUCCESS|MISSION_SUCCESS): (\d+) (?:files|stars) mapped")
speed = defaultdict(dict)
for s in slots:
    for t in TARGETS:
        rs = [r for r in runs if r["slot"] == s["slot"] and r["target"] == t and not r.get("exit")]
        cpu = [r["cpu_s"] for r in rs if r.get("cpu_s")]
        fm = []
        for r in rs:
            m = files_re.search(gzip.open(HERE / "speed" / "raw" / f"{s['slot']}_{t}_r{r['rep']}.out.gz", "rt", errors="replace").read())
            if m: fm.append(int(m.group(1)))
        ph = defaultdict(list)
        for r in rs:
            for k, v in r.get("phases", {}).items(): ph[k].append(v["total_s"])
        if cpu and fm:
            speed[s["slot"]][t] = {"cpu_s": st.median(cpu), "files": st.median(fm), "cpu_per_file": st.median(cpu) / st.median(fm),
                                   "stages": {k: st.median(v) for k, v in ph.items()}, "n_cpu": len(cpu)}


# ---- function structure from anchor DBs ----------------------------------------------------------------
def funcs(sha):
    db = next((HERE / "dbs").glob(f"*_{sha[:10]}.db"))
    c = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
    d = {}
    for fp, name, loc, cx in c.execute("select f.file_path, fn.func_name, fn.loc, fn.complexity from function_data fn join file_data f on fn.file_id=f.id"):
        if kind(fp) == "core": d[(fp.replace("backend/", "gitgalaxy/"), name)] = (loc, cx)
    c.close()
    return d


F = {s["slot"]: funcs(s["sha"]) for s in slots}

# ---- intervals ---------------------------------------------------------------------------------------
rows = []
for a, b in zip(slots, slots[1:]):
    commits = []
    out = git("log", "--first-parent", "--no-renames", "--numstat", "--format=@@%H%x09%cd%x09%s", "--date=short", f"{a['sha']}..{b['sha']}")
    cur = None
    for line in out.splitlines():
        if line.startswith("@@"):
            sha, date, subj = line[2:].split("\t", 2)
            cur = {"sha": sha[:10], "date": date, "subject": subj, "by": defaultdict(lambda: [0, 0, 0]), "perf": bool(PERF.search(subj))}
            commits.append(cur)
        elif line.strip() and cur is not None:
            p = line.split("\t")
            if len(p) < 3: continue
            ad = int(p[0]) if p[0].isdigit() else 0; de = int(p[1]) if p[1].isdigit() else 0
            k = kind(p[2]); cur["by"][k][0] += ad; cur["by"][k][1] += de; cur["by"][k][2] += 1
    for c in commits:
        c["by_kind"] = {k: v for k, v in c.pop("by").items()}
    agg = defaultdict(lambda: [0, 0, 0])
    for c in commits:
        for k, v in c["by_kind"].items():
            for i in range(3): agg[k][i] += v[i]
    fa, fb = F[a["slot"]], F[b["slot"]]
    born = len(set(fb) - set(fa)); died = len(set(fa) - set(fb))
    changed = sum(1 for k in set(fa) & set(fb) if fa[k] != fb[k])
    stp = {}
    for t in TARGETS:
        x, y = speed[a["slot"]].get(t), speed[b["slot"]].get(t)
        if x and y:
            stp[t] = {"cpu_ratio": y["cpu_s"] / x["cpu_s"], "per_file_ratio": y["cpu_per_file"] / x["cpu_per_file"], "files": [x["files"], y["files"]],
                      "stage_ratio": {k: (y["stages"][k] / x["stages"][k]) for k in y["stages"] if k in x["stages"] and x["stages"][k] > 0}}
    rows.append({"from": a, "to": b, "n_commits": len(commits), "kind_lines_files": {k: {"added": v[0], "deleted": v[1], "files": v[2]} for k, v in agg.items()},
                 "core_funcs": {"before": len(fa), "after": len(fb), "born": born, "died": died, "changed": changed}, "speed": stp,
                 "perf_commits": [c for c in commits if c["perf"]], "commits": commits})
(OUT / "steps.json").write_text(json.dumps({"slots": slots, "speed": speed, "intervals": rows}, indent=1, default=float))

# ---- report ------------------------------------------------------------------------------------------
L = ["# Exploratory join: speed steps x commits (GitGalaxy on itself)", "",
     "Speed = CPU seconds per mapped file, median over repeats; ratio = later / earlier engine. Kinds: core = scan-path engine code; standards = pattern tables/rule data; translator_tools = gitgalaxy/tools/*.",
     "", "| interval | commits | core +/- lines | standards +/- lines | translator +/- | core funcs born/died/changed | kw-rosetta per-file x | cics per-file x | lang-crucible per-file x (cpu x) |", "|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    k = r["kind_lines_files"]; g = lambda n: f"{k.get(n,{}).get('added',0)}/{k.get(n,{}).get('deleted',0)}"
    sp = r["speed"]; f = lambda t, key="per_file_ratio": f"{sp[t][key]:.2f}" if t in sp else "-"
    cf = r["core_funcs"]
    L.append(f"| {r['from']['date']} -> {r['to']['date']} | {r['n_commits']} | {g('core')} | {g('standards')} | {g('translator_tools')} | {cf['born']}/{cf['died']}/{cf['changed']} | {f('keyword-rosetta')} | {f('cics-crucible')} | {f('language-crucible')} ({f('language-crucible','cpu_ratio')}) |")
L += ["", "## Performance-worded commits per interval (subjects matching a keyword list; not a measure of what changed)", ""]
for r in rows:
    L.append(f"### {r['from']['date']} -> {r['to']['date']} ({len(r['perf_commits'])} of {r['n_commits']} commits)")
    for c in r["perf_commits"][:14]:
        bk = c["by_kind"]; ks = ", ".join(f"{k}:{v[2]}f" for k, v in bk.items() if k in ("core", "standards"))
        L.append(f"- {c['date']} `{c['sha']}` {c['subject'][:130]}  [{ks}]")
    L.append("")
(OUT / "steps.md").write_text("\n".join(L))
print("\n".join(L[:20]))
