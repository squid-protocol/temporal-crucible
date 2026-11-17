#!/usr/bin/env python3
"""Diff-aware change report: what did this change do to the file-level picture? (prototype)
    python tools/sensor/change_report.py REPO COMMIT [--scan]
Without --scan: size and roles, mechanical share, debt balance and the 'while you are here' markers. With --scan: also scans the commit and its parent with the
engine (history-aware, main engine) to report the reach and the size/complexity change of the functions the commit actually touched."""
import sys, re, os, json, sqlite3, argparse, subprocess, pathlib, collections, bisect, warnings
import numpy as np
warnings.filterwarnings("ignore")
HERE=pathlib.Path(__file__).resolve().parent; sys.path.insert(0,str(HERE)); sys.path.insert(0,str(HERE.parent))
import debt_trial as DT, debt_lifecycle as DL, mech_detect as MD
SA="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2/surface_area"; ENG=f"{SA}/engine_main"; YEAR=DL.YEAR
CALL=re.compile(r"([A-Za-z_]\w*)\s*\("); KW={"if","while","for","switch","sizeof","return","defined"}; HUNK=re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
tst=lambda p: bool(re.search(r"(^|/)(tests?|examples?|fuzz\w*|docs?)(/|$)",p))
ap=argparse.ArgumentParser(); ap.add_argument("repo"); ap.add_argument("commit"); ap.add_argument("--scan",action="store_true"); a=ap.parse_args()
repo=DL.POOL_DIR/a.repo; g=lambda *x: DL.git(repo,*x)
full=g("rev-parse",a.commit).strip(); head=g("show","-s","--format=%H%n%an%n%ct%n%s",full).splitlines(); T=int(head[2]); parent=g("rev-parse",full+"^").strip()
diff=g("show","-U0","--format=","--no-color","-M",full)
files=collections.OrderedDict(); cur=None; added=collections.defaultdict(list); removed=collections.defaultdict(list); hunks=collections.defaultdict(list); hl=[]
for ln in diff.splitlines():
    if ln.startswith("+++ b/"): cur=ln[6:]; files[cur]=[0,0]
    elif ln.startswith("+++ /dev/null"): cur=None
    elif ln.startswith("@@") and cur:
        m=HUNK.match(ln)
        if m: hunks[cur].append((int(m.group(3)),int(m.group(4)) if m.group(4) is not None else 1)); hl.append((cur,[],[]))
    elif cur and ln.startswith("+") and not ln.startswith("+++"): files[cur][0]+=1; added[cur].append(ln[1:]); hl[-1][2].append(ln[1:]) if hl else None
    elif cur and ln.startswith("-") and not ln.startswith("---"): files[cur][1]+=1; removed[cur].append(ln[1:]); hl[-1][1].append(ln[1:]) if hl else None
src_files=[p for p in files if not tst(p) and p.endswith((".c",".h",".cc",".cpp",".hpp"))]
tot=sum(a_+d for a_,d in files.values()); st=sum(sum(files[p]) for p in src_files)
print(f"CHANGE {full[:10]}  {head[3][:90]}\n  author {head[1]}; {len(files)} files, {tot} lines changed ({st} in {len(src_files)} source files, {tot-st} in tests/docs/other)")
# mechanical share: (old call -> new call) pairs repeated across equal-size hunks
pairs,big,_=MD.swaps(hl); mech_lines=MD.mechanical_lines(big)
print("MECHANICAL SHARE")
if big: print(f"  repeated swaps found: "+", ".join(f"{x} -> {y} x{n}" for (x,y),n in sorted(big.items(),key=lambda kv:-kv[1])[:4])+f"; about {100*min(mech_lines,tot)/max(tot,1):.0f}% of the changed lines belong to them")
else: print("  no repeated call swaps (5 or more): the change is organic")
# debt balance and while-you-are-here
_,items,head_ct,_,_,_=DT.track2(a.repo); au,ev,ph=DT.hist(repo)
add_d=[(p,DL.debt_line(l)) for p in src_files for l in added[p] if DL.debt_line(l)]; rem_d=[(p,DL.debt_line(l)) for p in src_files for l in removed[p] if DL.debt_line(l)]
print("DEBT BALANCE")
print(f"  markers added by this change: {len(add_d)}; removed: {len(rem_d)}"+("".join(f"\n    + {p}: {d[0]} {d[1][:70]}" for p,d in add_d[:3]))+("".join(f"\n    - {p}: {d[0]} {d[1][:70]}" for p,d in rem_d[:3])))
for it in items: it["fid"]=DT.pid(ph,it["path"],it["start"])
by=collections.defaultdict(list)
for it in items:
    if it["fid"] is not None: by[it["fid"]].append(it)
closed=sorted((i["end"],(i["end"]-i["start"])/YEAR) for i in items if i["end"] is not None and not i.get("file_deleted")); ends=[c[0] for c in closed]; k=bisect.bisect_right(ends,T); p90=float(np.percentile([c[1] for c in closed[:k]],90)) if k>=20 else float("nan")
sur=[]
for p in src_files:
    n=sum(files[p]); fi=DT.pid(ph,p,T)
    for it in by.get(fi,[]):
        if it["start"]<T and (it["end"] is None or it["end"]>=T) and it.get("end_sha")!=full:
            age=(T-it["start"])/YEAR; sur.append((int(it["author"]==head[1] or False),it["author"],age,age>p90,p90,p,it,n))
mine=[x for x in sur if x[1]==g("show","-s","--format=%ae",full).strip().lower()]
rule_fires=st>=50
print(f"  'while you are here' (fires on source changes of 50+ lines: this one has {st}): "+("YES" if rule_fires else "no, change too small to prompt")+f"; open markers in the touched files: {len(sur)}, of them written by this author: {len(mine)}")
if rule_fires:
    for x in sorted(sur,key=lambda x:(-(x[1]==g('show','-s','--format=%ae',full).strip().lower()),-x[2]))[:3]: print(f"    {x[5]}: {x[6]['marker'].upper()} open {x[2]:.1f} y{' (fossil)' if x[3] else ''}{', written by this author' if x[1]==g('show','-s','--format=%ae',full).strip().lower() else ''} | {x[6]['text'][:60]}")
print(f"    (back-test: among markers surfaced by this rule, 3.4% were repaid in that same commit, against 1.3% when every marker is shown; see while_here_output.txt)")
# reach of touched functions
if a.scan and src_files:
    W=pathlib.Path(SA)/"hist"/"changes"; W.mkdir(parents=True,exist_ok=True)
    def scan(commit,tag):
        db=W/f"wt_{tag}_galaxy_master.db"
        if db.exists(): return db
        wt=W/f"wt_{tag}"; subprocess.run(["git","-C",str(repo),"worktree","add","--detach","-f",str(wt),commit],capture_output=True,check=True)
        env=dict(os.environ); env["GITGALAXY_HISTORY_ASOF"]="1"; env["PYTHONPATH"]=ENG
        subprocess.run([sys.executable,"-c","import sys; sys.argv=['galaxyscope',sys.argv[1],'--db-only']; from gitgalaxy.galaxyscope import main; sys.exit(main())",str(wt)],cwd=W,env=env,capture_output=True)
        subprocess.run(["git","-C",str(repo),"worktree","remove","--force",str(wt)],capture_output=True); return db
    dc,dp=scan(full,full[:8]+"c"),scan(parent,full[:8]+"p")
    C=sqlite3.connect(f"file:{dc}?mode=ro",uri=True); P=sqlite3.connect(f"file:{dp}?mode=ro",uri=True)
    q="select f.id,f.func_name,f.start_line,f.loc,f.complexity,fi.file_path from function_data f join file_data fi on fi.id=f.file_id"
    cf=C.execute(q).fetchall(); pf={(r[5],r[1]):r for r in P.execute(q).fetchall()}
    callers=collections.defaultdict(set); cfiles=collections.defaultdict(set)
    for sfn,sfile,dfn in C.execute("select src_func_id,src_file_id,dst_func_id from fcall_data where dst_func_id is not null"): callers[dfn].add(sfn); cfiles[dfn].add(sfile)
    touched=[]
    for r in cf:
        fid,name,st_,loc,cx,path=r
        if path in hunks and st_ and any(not(c+max(d,1)-1<st_ or c>st_+(loc or 1)-1) for c,d in hunks[path]):
            before=pf.get((path,name)); c1=callers.get(fid,set()); two=set()
            for x in c1: two|=callers.get(x,set())
            touched.append((len(c1),len(cfiles.get(fid,())),len(two-c1-{fid}),name,path,(loc or 0)-(before[3] or 0) if before else None,(cx or 0)-(before[4] or 0) if before else None,before is None,fid))
    print("REACH OF WHAT CHANGED (engine scan of the commit and its parent)")
    print(f"  functions touched: {len(touched)} ({sum(1 for t in touched if t[7])} new); with 10+ callers: {sum(1 for t in touched if t[0]>=10)}; distinct callers affected: {len(set().union(*[callers.get(t[8],set()) for t in touched]) if touched else set())}")
    for t in sorted(touched,reverse=True)[:6]: print(f"    {t[3]:34s} {t[4][:30]:30s} callers {t[0]:4d} in {t[1]:3d} files, {t[2]:4d} more one hop out | size {('new' if t[7] else f'{t[5]:+d} lines')}, complexity {('' if t[7] else f'{t[6]:+d}')}")
