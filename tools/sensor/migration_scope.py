#!/usr/bin/env python3
"""Migration scope and progress report (first product of the reach sensor).
    python tools/sensor/migration_scope.py REPO OLD NEW SNAPSHOT [FOLLOW]   e.g.  libgit2 git_buf_free git_buf_dispose 34 9
Uses the quarterly scan databases in turn_v2/scan_<repo>/.work. SNAPSHOT is the snapshot BEFORE the migration."""
import sys, sqlite3, json, collections, pathlib
B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"
repo,old,new,s0=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4]); follow=int(sys.argv[5]) if len(sys.argv)>5 else 8
sn=json.load(open(f"{B}/scan_{repo}/snapshots.json")); db=lambda i: sqlite3.connect(f"file:{B}/scan_{repo}/.work/snap_{i:03d}_galaxy_master.db?mode=ro",uri=True)
def callers(con,name):
    fid=[r[0] for r in con.execute("select id from function_data where func_name=?",(name,))]
    if not fid: return {},set()
    q=",".join("?"*len(fid)); rows=con.execute(f"select distinct e.src_func_id, f.func_name, f.loc, fi.file_path, e.src_file_id from fcall_data e join function_data f on f.id=e.src_func_id join file_data fi on fi.id=e.src_file_id where e.dst_func_id in ({q})",fid).fetchall()
    return {r[0]:r[1:] for r in rows},set(fid)
con=db(s0); C,_=callers(con,old); N0,_=callers(con,new)
byfile=collections.defaultdict(list)
for fid,(fn,loc,path,_) in C.items(): byfile[path].append((fn,loc or 0))
indeg=collections.Counter(r[0] for r in con.execute("select dst_func_id from fcall_data where dst_func_id is not null"))
ids=set(C); two=set()
for (src,dst) in con.execute("select src_func_id,dst_func_id from fcall_data where dst_func_id is not null"):
    if dst in ids and src not in ids: two.add(src)
print(f"MIGRATION SCOPE: {old} -> {new}   ({repo}, snapshot {s0} = {sn[s0]['label']}, before the migration)")
print(f"  functions that call {old}: {len(C)} in {len(byfile)} files; total size of those functions {sum(v[2] for v in C.values()) if False else sum(l for fs in byfile.values() for _,l in fs):,} lines; functions already calling {new}: {len(N0)}")
import re
tst=lambda p: bool(re.search(r"(^|/)(tests?|examples?|fuzz\w*|docs?)(/|$)",p))
nt=sum(1 for fs_p,fs in byfile.items() if tst(fs_p) for _ in fs); print(f"  of those callers: {len(C)-nt} in source files, {nt} in tests/examples/docs")
print(f"  functions that depend on the callers (one more hop, ripple): {len(two)}")
print(f"  files holding the most callers:")
for p,fs in sorted(byfile.items(),key=lambda kv:-len(kv[1]))[:6]: print(f"    {p:46s} {len(fs):3d} callers, {sum(l for _,l in fs):5d} lines")
top=sorted(C.items(),key=lambda kv:-indeg[kv[0]])[:5]; print("  most depended-on callers (touch these carefully):  "+", ".join(f"{v[0]} ({indeg[k]} callers)" for k,v in top))
print(f"\nPROGRESS (snapshot, label, functions still calling {old}, functions calling {new}, share of the original callers still on {old}):")
last=None
for i in range(s0,min(s0+follow+1,len(sn))):
    c=db(i); co,_=callers(c,old); cn,_=callers(c,new); print(f"  {i:3d} {sn[i]['label']:8s} {len(co):5d} {len(cn):5d}   {100*len(co)/max(len(C),1):5.1f}%"); last=(i,co)
i,co=last; nts=sum(1 for v in co.values() if tst(v[2])); print(f"\nSTRAGGLERS at snapshot {i} ({sn[i]['label']}): {len(co)} functions still call {old} ({nts} of them in tests/examples/docs, {len(co)-nts} in source): a plateau of callers in tests usually means the old name is still the public API, not unfinished work. By file:")
bf=collections.defaultdict(list)
for fid,(fn,loc,path,_) in co.items(): bf[path].append(fn)
for p,fs in sorted(bf.items(),key=lambda kv:-len(kv[1]))[:6]: print(f"    {p:46s} {len(fs):3d}  e.g. {', '.join(fs[:2])}")
