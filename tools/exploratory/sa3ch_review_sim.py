"""Synthetic only. SA3-CH: latent work intensity drives both structural change and later fixes; no causal role for change."""
import sys, json, warnings, numpy as np
warnings.simplefilter("ignore")
from scipy.stats import rankdata, spearmanr, t as tdist
MIX=[(317,85),(319,30),(352,77),(452,142),(485,74),(523,40),(807,379),(903,52),(1058,47),(1316,109),(1676,155),(2419,961),(2758,76),(3386,112),(5734,159),(6000,100)]  # 16 drawn floor-clearing repos (n, HP positives); freebsd capped at 6000 files
def bands_of(loc,k):
    o=np.argsort(loc,kind="stable"); b=np.empty(len(loc),int); b[o]=(np.arange(len(loc))*k)//len(loc); return b
def grp(k): return np.where(k==0,0,np.where(k==1,1,np.where(k<=3,2,3)))
def bauc(x,y,loc,st,extra=None,cal=1.5,floor=True):
    tot={'gt':[0.0,0],'lt':[0.0,0],'eq':[0.0,0]}
    for s in np.unique(st[y==1]):
        m=st==s; yy=y[m]
        if yy.all(): continue
        xp,lp=x[m][yy==1],loc[m][yy==1]; xn,ln=x[m][yy==0],loc[m][yy==0]
        ratio=lp[:,None]/ln[None,:]; ok=(ratio<=cal)&(ratio>=1/cal)
        if extra is not None:
            for e,c2 in extra:
                r2=(e[m][yy==1][:,None]+1)/(e[m][yy==0][None,:]+1); ok&=(r2<=c2)&(r2>=1/c2)
        conc=(xp[:,None]>xn[None,:])+0.5*(xp[:,None]==xn[None,:])
        for nm,mask in (('gt',ok&(ratio>1)),('lt',ok&(ratio<1)),('eq',ok&(ratio==1))):
            tot[nm][0]+=conc[mask].sum(); tot[nm][1]+=mask.sum()
    n=sum(v[1] for v in tot.values())
    if floor and (n<100 or tot['gt'][1]<25 or tot['lt'][1]<25): return np.nan,n
    if tot['gt'][1]==0 or tot['lt'][1]==0: return np.nan,n
    we=tot['eq'][1]/n; ce=tot['eq'][0]/tot['eq'][1] if tot['eq'][1] else 0.5
    return (1-we)*0.5*(tot['gt'][0]/tot['gt'][1]+tot['lt'][0]/tot['lt'][1])+we*ce - 0.5, n
def resid_stat(x,y,st,covs):
    num=den=0.0
    for s in np.unique(st[y==1]):
        m=st==s; yy=y[m]; p=yy.sum(); n=len(yy)-p
        if p==0 or n==0: continue
        u=rankdata(x[m])/len(yy)
        X=np.column_stack([np.ones(len(yy))]+[c[m] for c in covs])
        if len(yy)>X.shape[1]+1 and np.ptp(u)>0:
            beta,*_=np.linalg.lstsq(X,u,rcond=None); r=u-X@beta
        else: r=u-u.mean()
        rr=rankdata(r); num+=rr[yy==1].sum()-p*(p+1)/2; den+=p*n
    return num/den-0.5 if den else np.nan
def make(rng,n,pos,scen,inst,theta=0.0,rho=0.7):
    lg=rng.normal(5,1.2,n); loc=np.exp(lg)
    w=rng.normal(0,1,n); phi=rng.normal(0,1,n)
    k=rng.poisson(np.exp(0.35+0.5*(lg-5)+1.1*w))
    c=np.where(k>0,k*np.exp(2.3+0.5*phi+0.5*rng.normal(0,1,n)),0.0)       # lines changed in the prior year
    lam=0.035*c**0.8
    if inst=="A": lam=lam+0.06                                             # callers elsewhere can change it
    d=(rng.poisson(0.78*lam)-rng.poisson(0.22*lam)).astype(float)
    if inst=="C":                                                          # a mostly-switch score: rare 0<->~50 flips plus small moves among edited non-zero files
        on=rng.random(n)<0.35; flip=(rng.random(n)<1-np.exp(-0.0015*c))
        small=np.where(on&(k>0),rng.normal(0,1.5,n)*(1-np.exp(-0.01*c)),0.0)
        d=np.where(flip,np.where(on,-50.0,50.0)+rng.normal(0,5,n),small)
    wf=rho*w+np.sqrt(1-rho**2)*rng.normal(0,1,n)
    base=np.exp(0.6*(lg-5)+1.0*wf)
    zc=np.log1p(c); zc=(zc-zc.mean())/zc.std()
    zd=np.where(d>0,1.0,np.where(d<0,-1.0,0.0))
    fixmult=np.exp((0.5*zc if scen=="newcode" else 0.0)+theta*zd)
    pfix=0.12
    # calibrate scale to the positive count
    grid=np.geomspace(1e-4,200,80); got=[(1-np.exp(-s*base*pfix*fixmult)).mean() for s in grid]
    s=np.interp(pos/n,got,grid)
    hp=(rng.poisson(s*base*pfix*fixmult)>0).astype(int)
    other=rng.poisson(s*base*(1-pfix))
    ctl=[(rng.binomial(other,pfix/(1-pfix))>0).astype(int) for _ in range(3)]
    return loc,lg,k,c,d,hp,ctl
def repo_stats(rng,n,pos,scen,inst,theta):
    loc,lg,k,c,d,hp,ctl=make(rng,n,pos,scen,inst,theta)
    nb=10 if n>=300 else 5
    b=bands_of(loc,nb); g=grp(k); st=b*4+g
    lk=np.log1p(k); lc=np.log1p(c)
    preds={"delta":d,"absdelta":np.abs(d),"lines":c,"commits":k.astype(float)}
    out={}
    for nm,x in preds.items():
        for oc,ys in (("hp",[hp]),("ctl",ctl)):
            P=np.nanmean([bauc(x,y,loc,st)[0] for y in ys]) if True else None
            R=np.nanmean([resid_stat(x,y,st,[lg,lk]) for y in ys])
            out[(nm,oc,"P")]=P; out[(nm,oc,"R")]=R
            if nm in("delta","absdelta"):
                out[(nm,oc,"R+lines")]=np.nanmean([resid_stat(x,y,st,[lg,lk,lc]) for y in ys])
                out[(nm,oc,"P+cal")]=np.nanmean([bauc(x,y,loc,st,extra=[(k,1.5),(c,2.0)])[0] for y in ys])
            if nm=="delta":
                out[(nm,oc,"P_bandonly")]=np.nanmean([bauc(x,y,loc,b)[0] for y in ys])
    out["pairs"]=bauc(d,hp,loc,st,floor=False)[1]; out["pairs_cal"]=bauc(d,hp,loc,st,extra=[(k,1.5),(c,2.0)],floor=False)[1]
    out["nz"]=(d!=0).mean(); out["nz4"]=(d[g==3]!=0).mean(); out["nz0"]=(d[g==0]!=0).mean() if (g==0).any() else np.nan
    out["sp_abs_k_4"]=spearmanr(np.abs(d[g==3]),k[g==3])[0]; out["g"]=[(g==j).mean() for j in range(4)]
    return out
def study(rng,scen,inst,theta,reps,mix=MIX):
    res={}
    diag=[]
    for _ in range(reps):
        per=[repo_stats(rng,n,p,scen,inst,theta) for n,p in mix]
        diag.append([np.mean([r["nz"] for r in per]),np.mean([r["nz4"] for r in per]),np.nanmean([r["nz0"] for r in per]),np.mean([r["sp_abs_k_4"] for r in per]),np.median([r["pairs"] for r in per]),np.median([r["pairs_cal"] for r in per])])
        keys=[kk for kk in per[0] if isinstance(kk,tuple)]
        for kk in keys:
            v=np.array([r[kk] for r in per]); ok=~np.isnan(v); v=v[ok]
            if len(v)<3: continue
            m,se=v.mean(),v.std(ddof=1)/np.sqrt(len(v)); q=tdist.ppf(1-0.0125/2,len(v)-1)
            res.setdefault(kk,[]).append((m,m-q*se>0,m+q*se<0,len(v),v.std(ddof=1)))
        for nm in ("delta","absdelta","lines","commits"):
            for stt in ("P","R","R+lines","P+cal"):
                if (nm,"hp",stt) not in per[0]: continue
                a=np.array([r[(nm,"hp",stt)] for r in per]); c2=np.array([r[(nm,"ctl",stt)] for r in per]); dd=a-c2; dd=dd[~np.isnan(dd)]
                if len(dd)<3: continue
                m,se=dd.mean(),dd.std(ddof=1)/np.sqrt(len(dd)); q=tdist.ppf(0.975,len(dd)-1)
                res.setdefault((nm,"spec",stt),[]).append((m,m-q*se>0,m+q*se<0,len(dd),dd.std(ddof=1)))
    dg=np.mean(diag,0)
    print(f"\n== scenario={scen} instrument={inst} theta={theta} reps={reps}: nz share {dg[0]:.2f} (4+ {dg[1]:.2f}, untouched {dg[2]:.2f}); spearman(|d|,k) in 4+ {dg[3]:.2f}; median eligible pairs/repo {dg[4]:.0f} (with activity calipers {dg[5]:.0f})")
    print(f"{'predictor':<10}{'outc':<6}{'stat':<11}{'mean':>8}{'supp':>6}{'contra':>7}{'repos':>6}{'sd_repo':>8}")
    for kk in sorted(res):
        a=np.array(res[kk]); print(f"{kk[0]:<10}{kk[1]:<6}{kk[2]:<11}{a[:,0].mean():>+8.4f}{a[:,1].mean():>6.2f}{a[:,2].mean():>7.2f}{a[:,3].mean():>6.1f}{a[:,4].mean():>8.4f}",flush=True)
    # joint reading: primary supported AND residualised supported
    for nm in ("delta","absdelta"):
        P=np.array(res[(nm,"hp","P")])[:,1]; R=np.array(res[(nm,"hp","R")])[:,1]; sp=np.array(res[(nm,"spec","P")])[:,1]
        print(f"  {nm}: primary&residualised both 'supported' {np.mean(P*R):.2f}; supported AND 'defect-specific' {np.mean(P*R*sp):.2f}")
if __name__=="__main__":
    rng=np.random.default_rng(int(sys.argv[4]) if len(sys.argv)>4 else 11)
    scen,inst,theta,reps=sys.argv[1],sys.argv[2],float(sys.argv[3]),int(sys.argv[5]) if len(sys.argv)>5 else 40
    study(rng,scen,inst,theta,reps)
