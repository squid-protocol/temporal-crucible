import pickle, glob, numpy as np, warnings; warnings.filterwarnings("ignore")
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import roc_auc_score
F={}
for f in glob.glob("af_*.pkl"): F.update(pickle.load(open(f,"rb")))
LAB={"raw":(10,13),"v3c":(11,14),"reg":(12,15)}; KINDS=["tweak","swap","signature","grow","shrink","rewrite"]
def feats(R,lab,kind):
    pc,_=LAB[lab]; cols=[np.log1p(R[:,3])]
    if kind in("arch","arch+prior"): cols+=[np.log1p(R[:,4+k]) for k in range(6)]
    if kind in("prior","arch+prior"): cols.append(np.log1p(R[:,pc]))
    return np.column_stack(cols)
def fit_pred(Rtr,Rte,lab,kind):
    _,oc=LAB[lab]; m=PoissonRegressor(alpha=1e-3,max_iter=500).fit(feats(Rtr,lab,kind),Rtr[:,oc]/Rtr[:,2],sample_weight=Rtr[:,2])
    return m.predict(feats(Rte,lab,kind))*Rte[:,2],m
def metrics(R,mu,lab):
    _,oc=LAB[lab]; y=R[:,oc]; auc=roc_auc_score(y>0,mu) if (y>0).any() and (y==0).any() else np.nan
    o=np.argsort(-(mu/R[:,2])); cs=np.cumsum(R[o,2]); k=cs<=0.2*cs[-1]; rec=y[o][k].sum()/max(y.sum(),1); return auc,rec
rng=np.random.default_rng(2982); out={}
print("FORWARD-IN-TIME TEST (train on the earlier half of each repo's file-years, test on the later half).  AUC and recall at a 20%-of-lines review budget.")
for lab in ("raw","v3c","reg"):
    print(f"\n=== label: {lab}")
    print(f"  {'repo':8s} {'test fixes':>10s} | code-only: churn  +edit kinds   gain [95% CI]        | with prior fixes: +prior  +kinds  gain [95% CI]")
    G={"auc_code":[], "auc_prior":[], "rec_code":[], "rec_prior":[]}
    for n,R in F.items():
        cut=np.median(R[:,1]); tr=R[R[:,1]<=cut]; te=R[R[:,1]>cut]
        res={}
        for kind in ("churn","arch","prior","arch+prior"):
            mu,_=fit_pred(tr,te,lab,kind); res[kind]=(mu,)+metrics(te,mu,lab)
        files=np.unique(te[:,0]); byf={f:np.flatnonzero(te[:,0]==f) for f in files}
        def delta(a,b,which):
            d=[]
            for _ in range(150):
                idx=np.concatenate([byf[f] for f in rng.choice(files,len(files))]); d.append(metrics(te[idx],res[a][0][idx],lab)[which]-metrics(te[idx],res[b][0][idx],lab)[which])
            return np.percentile(d,2.5),np.percentile(d,97.5)
        dc=delta("arch","churn",0); dp=delta("arch+prior","prior",0)
        G["auc_code"].append(res["arch"][1]-res["churn"][1]); G["auc_prior"].append(res["arch+prior"][1]-res["prior"][1]); G["rec_code"].append(res["arch"][2]-res["churn"][2]); G["rec_prior"].append(res["arch+prior"][2]-res["prior"][2])
        ycol=LAB[lab][1]
        print(f"  {n:8s} {int(te[:,ycol].sum()):10d} |   AUC {res['churn'][1]:.3f}  {res['arch'][1]:.3f}  {res['arch'][1]-res['churn'][1]:+.3f} [{dc[0]:+.3f},{dc[1]:+.3f}]  |   AUC {res['prior'][1]:.3f}  {res['arch+prior'][1]:.3f}  {res['arch+prior'][1]-res['prior'][1]:+.3f} [{dp[0]:+.3f},{dp[1]:+.3f}]")
        print(f"  {'':8s} {'':10s} |   rec {res['churn'][2]:.3f}  {res['arch'][2]:.3f}  {res['arch'][2]-res['churn'][2]:+.3f}                 |   rec {res['prior'][2]:.3f}  {res['arch+prior'][2]:.3f}  {res['arch+prior'][2]-res['prior'][2]:+.3f}")
    print(f"  mean gain over repos: AUC code-only {np.mean(G['auc_code']):+.3f}, with prior fixes {np.mean(G['auc_prior']):+.3f};  recall@20% code-only {np.mean(G['rec_code']):+.3f}, with prior {np.mean(G['rec_prior']):+.3f}")
print("\nFITTED EDIT-KIND TERMS (rate ratio per log unit; code-only model, v3c label, all file-years)")
for n,R in F.items():
    _,m=fit_pred(R,R,"v3c","arch"); c=np.exp(m.coef_); print(f"  {n:8s} churn {c[0]:.2f} | "+"  ".join(f"{k} {v:.2f}" for k,v in zip(KINDS,c[1:])))
