exec(open("r2.py").read().split('print("commits"')[0].replace('rows.append(dict(sv=sv','rows.append(dict(sv=sv'))
import statistics
rows=[r for r in rows if r["A"]!="unclear"]
def pct(f,R): return round(100*sum(1 for r in R if f(r))/max(len(R),1))
feat={ "loop depth down":lambda r:r["ast"]["max_loop_depth"]<0,"loops added":lambda r:r["ast"]["loops"]>0,"guards added":lambda r:r["ast"]["guards"]>0,
 "try/except added":lambda r:r["ast"]["try"]>0,"regex literal touched (calls/len)":lambda r:r["ast"]["re_calls"]!=0 or r["ast"]["rx_len"]!=0,
 "set-literal 'in' added":lambda r:r["ast"]["in_set_lit"]>0,"new constants":lambda r:r["ast"]["consts_added"]>0,"hints added":lambda r:r["ast"]["annotated"]>0,
 "nodes shrank >10%":lambda r:r["size"]["n_new"]<0.9*r["size"]["n_old"],"nodes grew >10%":lambda r:r["size"]["n_new"]>1.1*r["size"]["n_old"],
 "node change <=5% (in place)":lambda r:abs(r["size"]["dn"])<=0.05*max(r["size"]["n_old"],1),"new callee/calls added":lambda r:r["ast"]["distinct_callees"]>0}
print("share of commits (%) whose pooled ast delta shows the feature, by PR-text primary intent")
labs=["fix","feature","refactor","perf","other"]
print(f'{"":36s}'+"".join(f"{l:>10s}" for l in labs)); print(f'{"commits":36s}'+"".join(f"{sum(r['A']==l for r in rows):>10d}" for l in labs))
for name,f in feat.items(): print(f"{name:36s}"+"".join(f"{pct(f,[r for r in rows if r['A']==l]):>10d}" for l in labs))
print("\nmedian node delta by intent:",{l:int(statistics.median([r['size']['dn'] for r in rows if r['A']==l] or [0])) for l in labs})
print("median structure-view LOC delta (GitGalaxy):",{l:round(statistics.median([r['sv'][1] for r in rows if r['A']==l] or [0]),1) for l in labs})
print("median structure-view complexity delta:",{l:round(statistics.median([r['sv'][0] for r in rows if r['A']==l] or [0]),1) for l in labs})
# perf commits listing
print("\nperf-labelled commits (PR text), first 12: subject | node delta | loop depth | in_set | consts | regex")
for r in [r for r in rows if r["A"]=="perf"][:12]:
    print(f" {C[r['k']]['subject'][:70]:70s} | {r['size']['dn']:+5d} | {r['ast']['max_loop_depth']:+.0f} | {r['ast']['in_set_lit']:+.0f} | {r['ast']['consts_added']} | {r['ast']['re_calls']:+.0f}")
# clustering
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score
keys=AST+["type_l1","consts_added"]
M=np.array([[np.sign(r["ast"][k])*np.log1p(abs(r["ast"][k])) for k in keys] for r in rows]); M=StandardScaler().fit_transform(M)
best=None
for k in range(3,9):
    labs_=[KMeans(k,n_init=5,random_state=s).fit_predict(M) for s in range(5)]
    ari=np.mean([adjusted_rand_score(labs_[0],labs_[i]) for i in range(1,5)]); sil=silhouette_score(M,labs_[0])
    print(f"k={k} stability(ARI)={ari:.2f} silhouette={sil:.2f}")
print("\n--- k=3 clusters (stable) ---")
km=KMeans(3,n_init=10,random_state=0).fit(M); cl=km.labels_
for c in range(3):
    R=[r for r,l in zip(rows,cl) if l==c]
    print(f"cluster {c}: n={len(R)} median node delta {int(statistics.median(r['size']['dn'] for r in R))}, median events {statistics.median(r['size']['nev'] for r in R)}, intent mix {dict(collections.Counter(r['A'] for r in R).most_common(3))}")
    for r in random.Random(3).sample(R,min(5,len(R))): print("    ",C[r['k']]['subject'][:90])
