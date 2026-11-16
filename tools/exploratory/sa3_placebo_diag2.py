# PLACEBO ONLY. Compare two shuffles of the real predictor among size-adjacent files:
#   perm   a random permutation within blocks of 4 (each file keeps its OWN value 1 time in 4)
#   shift  a cyclic shift within blocks of 4 by 1..3 places (no file ever keeps its own value)
import sys, numpy as np
sys.path.insert(0,'tools')
import sa3_stats as S, sa3_score as SC
rng=np.random.default_rng(6)
repos=[r for r in SC.scored_repos() if r['HP']['clears_floor'] and r['drawn']]
def shift(x,loc,paths,rng,block=4):
    out=x.copy(); order=np.asarray(sorted(range(len(x)),key=lambda i:(loc[i],paths[i])))
    for s in range(0,len(order),block):
        blk=order[s:s+block]
        if len(blk)>1: out[blk]=x[np.roll(blk,int(rng.integers(1,len(blk))))]
    return out
data=[SC.load(r['repo'],True) for r in repos]
for p in SC.PRIMARIES:
    a={'perm':[], 'shift':[], 'kept_perm':[], 'kept_shift':[]}
    for d in data:
        y=d['y']['HP']; x=np.nan_to_num(d['x'][p]); loc=d['loc']; des=S.Design(loc,y,d['band'],d['k'])
        v1,v2=[],[]
        for _ in range(40):
            v1.append(des.effect(S.block_permute(x,loc,d['paths'],rng))); v2.append(des.effect(shift(x,loc,d['paths'],rng)))
        a['perm'].append(np.nanmean(v1)); a['shift'].append(np.nanmean(v2))
    print(f"{p:<26} random permutation {np.mean(a['perm']):+.4f}   cyclic shift (never own value) {np.mean(a['shift']):+.4f}",flush=True)
