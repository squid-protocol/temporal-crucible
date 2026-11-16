"""Mass-migration detector: the same call or macro removed/added in many functions in one quarter, and what remains once sweeps are set aside."""
import sys; sys.path.insert(0,"/srv/storage_16tb/projects/historical-call-graph-gif")
import sys, json, pickle, collections, numpy as np
B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"; SP="/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad"
PRINTISH={"print","println!","eprintln!","print!","eprint!","dbg!","std.debug.print","debug.print","printf","fprintf","curl_mfprintf","puts","perror"}
def labels(name):
    f=f"{B}/scan_{name}/snapshots.json"
    try: return [x["label"] for x in json.load(open(f))]
    except FileNotFoundError:
        picks,_=pickle.load(open(SP+"/rn_truth_impacket.pkl","rb")); return [p.label for p in picks]
def detect(events,min_fn=10,rel=0.01):
    by=collections.defaultdict(list)
    for i,e in enumerate(events):
        if e["code"]: by[e["s"]].append(i)
    migr=[]; one=[]; insweep=set()
    for s,idx in by.items():
        N=len(idx); thr=max(min_fn,int(rel*N)); fa=collections.Counter(); fr=collections.Counter()
        for i in idx:
            for k in events[i]["add"]: fa[k]+=1
            for k in events[i]["rem"]: fr[k]+=1
        X={k for k,v in fr.items() if v>=thr}; Y={k for k,v in fa.items() if v>=thr}
        co=collections.Counter()
        for i in idx:
            e=events[i]; xs=[k for k in e["rem"] if k in X]; ys=[k for k in e["add"] if k in Y]
            for x in xs:
                for y in ys:
                    if x!=y: co[(x,y)]+=1
        usedx=set(); usedy=set(); mig=[]
        for (x,y),c in co.most_common():
            if x in usedx or y in usedy: continue
            if c>=max(8,0.4*min(fr[x],fa[y])): mig.append((x,y,c)); usedx.add(x); usedy.add(y)
        for x,y,c in mig: migr.append(dict(s=s,old=x,new=y,n=c,nold=fr[x],nnew=fa[y]))
        for k in X-usedx: one.append(dict(s=s,kind="removal",name=k,n=fr[k]))
        for k in Y-usedy: one.append(dict(s=s,kind="adoption",name=k,n=fa[k]))
        sx=X; sy=Y
        for i in idx:
            e=events[i]
            if any(k in sx for k in e["rem"]) or any(k in sy for k in e["add"]): insweep.add(i)
    return migr,one,insweep
def guards(e): return sum(v for k,v in e["d"].items() if k.startswith("if_") or k=="if_statement")
def show(path):
    R=pickle.load(open(path,"rb"))
    for name,r in R.items():
        ev=r["events"]; lab=labels(name); code=[i for i,e in enumerate(ev) if e["code"]]
        migr,one,ins=detect(ev); org=[i for i in code if i not in ins]
        print(f"\n== {name}: {len(code):,} code edits; in a sweep (same call/macro changed in >= 10 functions that quarter): {100*len(ins)/len(code):.1f}%; quarters with a sweep: {len({m['s'] for m in migr}|{o['s'] for o in one})}")
        agg=collections.defaultdict(lambda:dict(n=0,qs=[]))
        for m in migr: a=agg[(m["old"],m["new"])]; a["n"]+=m["n"]; a["qs"].append(m["s"])
        top=sorted(agg.items(),key=lambda kv:-kv[1]["n"])[:7]
        print(f"   {len(migr)} migration-quarters; {len(agg)} distinct old->new pairs. Largest:")
        for (x,y),a in top: print(f"     {x} -> {y}: {a['n']} functions over {len(set(a['qs']))} quarter(s), {lab[min(a['qs'])+1]} .. {lab[max(a['qs'])+1]}")
        ad=collections.defaultdict(int); rm=collections.defaultdict(int)
        for o in one: (ad if o["kind"]=="adoption" else rm)[o["name"]]+=o["n"]
        print("   adoptions with no old name removed: "+", ".join(f"{k} ({v})" for k,v in sorted(ad.items(),key=lambda kv:-kv[1])[:5]))
        print("   removals with no replacement: "+", ".join(f"{k} ({v})" for k,v in sorted(rm.items(),key=lambda kv:-kv[1])[:5]))
        def sh(f,ids): return f"{100*np.mean([bool(f(ev[i])) for i in ids]):.1f}%" if ids else "-"
        sw=[i for i in code if i in ins]
        print(f"   what the edits are        {'in sweeps':>10s} {'organic':>10s}")
        for lab_,f in (("signature changed",lambda e:e["sig"]),("guard added",lambda e:guards(e)>0),("guard removed",lambda e:guards(e)<0),("grew (net lines up)",lambda e:e["dloc"]>0),
                       ("print/log call added",lambda e:any(k in PRINTISH for k in e["add"])),("print/log call removed",lambda e:any(k in PRINTISH for k in e["rem"]))):
            print(f"     {lab_:24s}{sh(f,sw):>10s} {sh(f,org):>10s}")
        by=collections.Counter(ev[i]["year"]//5*5 for i in ins); tot=collections.Counter(ev[i]["year"]//5*5 for i in code)
        print("   share of code edits in sweeps by era: "+", ".join(f"{y}s {100*by[y]/tot[y]:.0f}%" for y in sorted(tot) if tot[y]>=200))
if __name__=="__main__":
    for p in sys.argv[1:]: show(p)
