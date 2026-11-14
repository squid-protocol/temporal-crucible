# PLACEBO ONLY: a file is scored with ANOTHER file's value, never its own.
import sys, hashlib, numpy as np
sys.path.insert(0,'tools')
import sa3_stats as S, sa3_score as SC
rng=np.random.default_rng(7)
repos=[r for r in SC.scored_repos() if r['HP']['clears_floor'] and r['drawn']]
h=lambda p:hashlib.sha1(p.encode()).hexdigest()
def shift(x,order,rng,block):
    out=x.copy()
    for s in range(0,len(order),block):
        blk=order[s:s+block]
        if len(blk)>1: out[blk]=x[np.roll(blk,int(rng.integers(1,len(blk))))]
    return out
data=[SC.load(r['repo'],True) for r in repos]
same=[]
for d in data:
    o=sorted(range(d['n']),key=lambda i:(d['loc'][i],d['paths'][i]))
    dr=lambda i:d['paths'][i].rsplit('/',1)[0]
    same.append(np.mean([dr(o[i])==dr(o[i+1]) for i in range(len(o)-1)]))
print('share of LOC-adjacent files in the same directory, mean over repos: %.3f'%np.mean(same))
for p in ('struct_branch','in_degree'):
    res={}
    for name,key,block in (('path ties, block 4',lambda d,i:(d['loc'][i],d['paths'][i]),4),('hash ties, block 4',lambda d,i:(d['loc'][i],h(d['paths'][i])),4),
                           ('hash ties, block 32',lambda d,i:(d['loc'][i],h(d['paths'][i])),32),('whole band shuffled',None,0)):
        vals=[]
        for d in data:
            y=d['y']['HP']; x=np.nan_to_num(d['x'][p]); des=S.Design(d['loc'],y,d['band'],d['k'])
            v=[]
            for _ in range(30):
                if key is None:
                    xp=x.copy()
                    for j in range(d['k']):
                        m=np.flatnonzero(d['band']==j); xp[m]=x[rng.permutation(m)]
                else:
                    order=np.asarray(sorted(range(d['n']),key=lambda i:key(d,i))); xp=shift(x,order,rng,block)
                v.append(des.effect(xp))
            vals.append(np.nanmean(v))
        res[name]=np.mean(vals)
    print(f"{p:<16}"+"   ".join(f"{k}: {v:+.4f}" for k,v in res.items()),flush=True)
