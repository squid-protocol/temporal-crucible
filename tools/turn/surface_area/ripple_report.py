import pickle, glob, numpy as np, warnings; warnings.filterwarnings("ignore")
from scipy.stats import spearmanr, rankdata
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
R=[];SW=[];off=0
for f in sorted(glob.glob("rt_*.pkl")):
    for n,v in pickle.load(open(f,"rb")).items():
        r=v["rows"]
        if len(r)==0: continue
        r=r.copy(); r[:,0]+=off; off+=len(v["sweeps"])+1; R.append(r); SW+=v["sweeps"]
X=np.vstack(R); print(f"{len(SW)} sweeps (>= 10 functions swept), {len(X):,} candidate functions, {int(X[:,7].sum()):,} follow-on edits")
d1,d2,sf,ln,fi,api,y,g=X[:,1],X[:,2],X[:,3],X[:,4],X[:,5],X[:,6],X[:,7],X[:,0]
print("\nA. SHARE OF FUNCTIONS EDITED (not as part of a sweep) IN THE SWEEP QUARTER OR THE NEXT")
for lab,m in (("callers of swept functions (1 hop)",d1==1),("callers of callers (2 hops)",(d2==1)),("same file as a swept function, not a caller",(sf==1)&(d1==0)&(d2==0)),("everything else (random sample)",(sf==0)&(d1==0)&(d2==0))):
    print(f"  {lab:48s} {100*y[m].mean():5.1f}%  (n={int(m.sum()):,})")
def fit(cols,Xs,ys):
    m=LogisticRegression(max_iter=800,C=1e4).fit(Xs[:,cols],ys); return m
base=[2,3,4]    # samefile, size, fan-in
M=np.column_stack([d1,d2,sf,ln,fi,api]); names=["caller_1hop","caller_2hop","same_file","log_size","log_fanin","api_exposure_rank"]
m=fit(list(range(6)),M,y); print("\nB. ODDS RATIOS (pooled; bootstrap over sweeps for 95% interval)")
rng=np.random.default_rng(2982); ids=np.unique(g); by={i:np.flatnonzero(g==i) for i in ids}; bs=[]
for _ in range(60):
    pick=rng.choice(ids,len(ids)); idx=np.concatenate([by[i] for i in pick]); bs.append(LogisticRegression(max_iter=500,C=1e4).fit(M[idx],y[idx]).coef_[0])
bs=np.array(bs)
for k,nm in enumerate(names): print(f"  {nm:18s} OR {np.exp(m.coef_[0][k]):6.2f} [{np.exp(np.percentile(bs[:,k],2.5)):.2f},{np.exp(np.percentile(bs[:,k],97.5)):.2f}]")
print("\nC. DOES MEASURED REACH BEAT THE FILE-LEVEL api_exposure SCORE?  AUC for a follow-on edit, 5-fold grouped by sweep")
def cv(cols):
    p=np.zeros(len(y))
    for tr,te in GroupKFold(5).split(M,y,g): p[te]=LogisticRegression(max_iter=500,C=1e4).fit(M[tr][:,cols],y[tr]).predict_proba(M[te][:,cols])[:,1]
    r=rankdata(p); n1=y.sum(); return (r[y==1].sum()-n1*(n1+1)/2)/(n1*(len(y)-n1))
for lab,cols in (("size, fan-in, same file",[2,3,4]),("+ api_exposure rank (file score)",[2,3,4,5]),("+ measured reach (callers 1 and 2 hops)",[0,1,2,3,4]),("+ both",[0,1,2,3,4,5])): print(f"  {lab:42s} {cv(cols):.3f}")
S=np.array([[s[2],s[3],s[4],s[5],s[6]] for s in SW],float)
print("\nD. SWEEP LEVEL (swept functions n, 1-hop callers, 2-hop callers, files holding callers, callers edited)")
print(f"  median swept {np.median(S[:,0]):.0f}, 1-hop callers {np.median(S[:,1]):.0f}, 2-hop callers {np.median(S[:,2]):.0f}, caller files {np.median(S[:,3]):.0f}; median share of 1-hop callers edited {100*np.median(S[:,4]/np.maximum(S[:,1],1)):.1f}%")
print(f"  Spearman: swept size vs 1-hop callers {spearmanr(S[:,0],S[:,1]).statistic:+.2f}; 1-hop callers vs callers edited {spearmanr(S[:,1],S[:,4]).statistic:+.2f}; swept size vs callers edited {spearmanr(S[:,0],S[:,4]).statistic:+.2f}")
