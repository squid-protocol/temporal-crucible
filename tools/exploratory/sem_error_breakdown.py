"""Exploratory (after SEM scoring): which CVEs/fragments cause SEM's wrong 'patched' calls on verbatim-unpatched units."""
import sys, pathlib, multiprocessing
from collections import Counter, defaultdict
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import sem_eval as S, vzt_eval as T, vz_eval as Z
up, _ = T.upstream()
fixes = {}
for f in Z.FIXES:
    es = Z.engine_spans(Z.OUT / f"zlib@{f[:9]}^" / f"zlib@{f[:9]}^_galaxy_master.db")
    pf = defaultdict(lambda: {"R": set(), "A": set()})
    for (p, _n), d in Z.fix_functions(f, es).items():
        pf[p]["R"] |= d["R"]; pf[p]["A"] |= d["A"]
    fixes[f[:9]] = {k: {**v, "F": S.fragments(v["A"])} for k, v in pf.items()}
tasks = [(n, s, c) for n in T.HOSTS for s, c in T.host_states(n)]
with multiprocessing.get_context("fork").Pool(8) as p:
    states = list(p.imap_unordered(T.state_task, tasks, chunksize=2))
bad, frag_hits = Counter(), Counter()
for name, sha, ct, ver, texts in states:
    for fx, pf in fixes.items():
        for fname, ra in pf.items():
            if fname not in texts: continue
            v = up.get(fname, {}).get(T.normws(texts[fname]))
            if not v or v >= Z.RELEASE[fx]: continue
            if S.sem(texts[fname], ra["R"], ra["A"], ra["F"]) == "patched":
                bad[(Z.CVE[fx], fname)] += 1
                st = "\x01" + "\x01".join(S.norm_toks(texts[fname])) + "\x01"
                for fr in ra["F"]:
                    if S.present(fr, st): frag_hits[" ".join(fr)] += 1
print(bad.most_common()); print(frag_hits.most_common(6))
