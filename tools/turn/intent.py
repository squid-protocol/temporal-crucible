import sys, re, json, pickle, collections, subprocess
sys.path.insert(0,"/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad")
import sweeps as S
B=S.B; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"; SPD=S.SP
SRC={"libgit2":"ts_edits_c2.pkl","redis":"ts_edits_c2.pkl","curl":"ts_edits_c2.pkl","expat":"ts_edits_ho_c.pkl","libxml2":"ts_edits_ho_c.pkl","scapy":"ts_edits_ho_py.pkl","sphinx":"ts_edits_ho_py.pkl","commons-io":"ts_edits_ho_jg.pkl","prometheus":"ts_edits_ho_jg.pkl","sqlmap":"ts_edits_lang.pkl","ripgrep":"ts_edits_lang.pkl","tigerbeetle":"ts_edits_lang.pkl","impacket":"ts_edits_imp.pkl"}
STD={"free","malloc","calloc","realloc","strdup","printf","fprintf","sprintf","snprintf","puts","assert","strcpy","strcat","memcpy","range","xrange","str","unicode","type","len","isinstance","print","ord","chr","open"}
def norm(s): return re.sub(r"[^a-z0-9]","",s.lower())
def intent(o,n):
    ob=o.split(".")[-1].split("::")[-1]; nb=n.split(".")[-1].split("::")[-1]
    if norm(ob)==norm(nb) and ob!=nb: return "naming convention / case change"
    if re.match(r"(assert|expect|require|fail|check|Equals?|Ok|NoError|cl_)",ob,re.I) or re.match(r"(assert|expect|require|fail|check|Equals?|Ok|NoError|cl_)",nb,re.I): return "test / assertion framework"
    if ob in STD and nb not in STD and (ob in nb or True): return "stdlib -> project wrapper or safer call"
    if nb.endswith(ob) or nb.startswith(ob) or ob in nb or nb in ob: return "wrapper / namespace / version suffix"
    p=0
    while p<min(len(ob),len(nb)) and ob[p]==nb[p]: p+=1
    if p>=4: return "API rename (shared prefix)"
    return "other / needs context"
def _report():
    tot=collections.Counter(); per={}
    for n,f in SRC.items():
        try: ev=pickle.load(open(f"{SPD}/{f}","rb"))[n]["events"]
        except Exception as e: continue
        migr,_,_=S.detect(ev); c=collections.Counter(intent(m["old"],m["new"]) for m in migr); per[n]=(c,len(migr)); tot+=c
    print("INTENT OF MIGRATIONS BY SIMPLE RULES (old name -> new name only; no commit text)")
    for k,v in tot.most_common(): print(f"  {k:42s} {v:4d}  {100*v/sum(tot.values()):4.0f}%")
    print("  total migrations:",sum(tot.values()))
    # commit subjects for notable migrations
    notable=[("libgit2","git_buf_free","git_buf_dispose"),("libgit2","assert","GIT_ASSERT_ARG"),("libgit2","giterr_set","git_error_set"),("curl","free","curlx_free"),("curl","fprintf","curl_mfprintf"),("redis","redisLog","serverLog"),("scapy","xrange","range"),("scapy","ord","orb"),("sqlmap","logger.warn","logger.warning"),("prometheus","Equals","Equal"),("tigerbeetle","isSet","is_set"),("impacket","datetime.datetime.utcnow","datetime.datetime.now")]
    print("\nWHAT THE COMMITS SAY (git log -S old-name in the sweep quarter)")
    for n,o,nw in notable:
        ev=pickle.load(open(f"{SPD}/{SRC[n]}","rb"))[n]["events"]; migr,_,_=S.detect(ev); m=[x for x in migr if x["old"]==o and x["new"]==nw]
        if not m: continue
        m=max(m,key=lambda x:x["n"]); 
        try: sn=json.load(open(f"{B}/scan_{n}/snapshots.json")); a,b=sn[m["s"]]["commit"],sn[m["s"]+1]["commit"]
        except Exception: continue
        r=subprocess.run(["git","-C",f"{POOL}/{n}","log","-S"+o.split(".")[-1],"--format=%s","-n","200",f"{a}..{b}"],capture_output=True,text=True,errors="replace",timeout=60).stdout.splitlines()
        cnt=collections.Counter(re.sub(r"[0-9a-f]{7,}|#\d+","",x)[:80] for x in r)
        print(f"  {n}: {o} -> {nw} ({m['n']} functions): "+" | ".join(f"{s}" for s,_ in cnt.most_common(3)))
if __name__=='__main__': _report()
