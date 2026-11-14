# PLACEBO ONLY: every value scored here is a block-permuted (shuffled) predictor. No real predictor meets an outcome.
import sys, json, numpy as np
sys.path.insert(0,'tools')
import sa3_stats as S, sa3_score as SC
rng=np.random.default_rng(5)
repos=[r for r in SC.scored_repos() if r['HP']['clears_floor'] and r['drawn']]
NB=4
def rb_effect(loc,y,band,k,x,cal=1.5):
    # ratio-balanced: pairs binned by |ln(LOC ratio)|; within each bin the 'positive larger' and 'positive smaller'
    # sides get equal weight; bins weighted by the smaller side's pair count
    s=np.zeros((NB,2)); t=np.zeros((NB,2)); se=te=0.0
    for j in range(k):
        idx=np.flatnonzero(band==j); p=idx[y[idx]==1]; q=idx[y[idx]==0]
        if not len(p) or not len(q): continue
        lr=np.log(loc[p])[:,None]-np.log(loc[q])[None,:]
        conc=(x[p][:,None]>x[q][None,:])+0.5*(x[p][:,None]==x[q][None,:])
        a=np.abs(lr); ok=a<=np.log(cal)
        eq=ok&(lr==0); se+=conc[eq].sum(); te+=eq.sum()
        b=np.minimum((a/np.log(cal)*NB).astype(int),NB-1)
        for i in range(NB):
            for side,m in ((0,ok&(lr>0)&(b==i)),(1,ok&(lr<0)&(b==i))):
                s[i,side]+=conc[m].sum(); t[i,side]+=m.sum()
    w=np.minimum(t[:,0],t[:,1]); good=w>0
    if not good.any(): return np.nan
    c=0.5*(s[good,0]/t[good,0]+s[good,1]/t[good,1])
    main=(c*w[good]).sum()/w[good].sum()
    tot=t.sum()+te; we=te/tot if tot else 0
    return (1-we)*main+we*(se/te if te else 0.5)-0.5
out={}
for p in SC.PRIMARIES+['struct_branch_per_loc']:
    acc={k:[] for k in ('bauc','resid','ratio_bal','cal1.25','cal1.15')}
    for r in repos:
        d=SC.load(r['repo'],True); y=d['y']['HP']; x=np.nan_to_num(d['x'][p]); loc=d['loc']
        des=S.Design(loc,y,d['band'],d['k']); d125=S.Design(loc,y,d['band'],d['k'],1.25); d115=S.Design(loc,y,d['band'],d['k'],1.15)
        v={k:[] for k in acc}
        for _ in range(40):
            xp=S.block_permute(x,loc,d['paths'],rng)
            v['bauc'].append(des.effect(xp)); v['resid'].append(S.residual_effect(xp,y,d['band'],d['k'],[d['lg']]))
            v['ratio_bal'].append(rb_effect(loc,y,d['band'],d['k'],xp)); v['cal1.25'].append(d125.effect(xp)); v['cal1.15'].append(d115.effect(xp))
        for k in acc: acc[k].append(np.nanmean(v[k]))
    out[p]={k:round(float(np.nanmean(a)),4) for k,a in acc.items()}
    print(f"{p:<28}"+"  ".join(f"{k} {v:+.4f}" for k,v in out[p].items()),flush=True)
