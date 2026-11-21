import csv,json,subprocess,collections,random,bisect,datetime,sys
import numpy as np
from scipy.stats import spearmanr
H='/srv/storage_16tb/projects/gitgalaxy-history/'
G=['git','--git-dir='+H+'mirror.git']
TIP='7203d2555753ca2b29e180de3cb8d7845aca6a06'
LD='gitgalaxy/standards/language_standards/languages/'
fp=[l.split() for l in open('fp.txt')]
shas=[a for a,b in fp]; ts=[int(b) for a,b in fp]; idx={s:i for i,s in enumerate(shas)}
N=len(shas)
files=collections.defaultdict(set); cur=None
for l in open('files.txt'):
    l=l.strip()
    if l.startswith('@@'): cur=idx.get(l[2:]); continue
    if l and cur is not None: files[cur].add(l)
def kind(p):
    if p.startswith(LD) and p.endswith('.py') and not p.endswith('__init__.py'): return 'lang'
    if '/tests/' in p or '/tools/' in p or 'translator_tools' in p or p.startswith('gitgalaxy/tests'): return 'skip'
    return 'core'
langfiles=collections.defaultdict(list) # lang->sorted idx
corec=[0]*(N+1)
corelist=collections.defaultdict(list)
for i in range(N):
    c=0
    for p in files.get(i,()):
        k=kind(p)
        if k=='lang': langfiles[p[len(LD):-3]].append(i)
        elif k=='core': c=1; corelist[i].append(p)
    corec[i+1]=corec[i]+c
first_lang=min(min(v) for v in langfiles.values())
alllang_first=sorted({i for v in langfiles.values() for i in v})[0]
rows=list(csv.DictReader(open(H+'gh/ts_accuracy_history.csv')))
# map shas
miss=sorted({r['commit_sha'] for r in rows if r['commit_sha'] not in idx})
mapped={}
for s in miss:
    tt=[r['timestamp_utc'] for r in rows if r['commit_sha']==s][0]
    t=int(datetime.datetime.fromisoformat(tt.replace('Z','+00:00')).timestamp()); j=bisect.bisect_right(ts,t)-1; mapped[s]=max(j,0)
def ix(s): return idx[s] if s in idx else mapped[s]
def f(x):
    try: return float(x)
    except: return None
bylang=collections.defaultdict(list)
excl=collections.Counter()
for r in rows:
    i=ix(r['commit_sha'])
    if i is None: excl['sha unmappable']+=1; continue
    r['i']=i; r['found']=f(r['found_functions']); r['real']=f(r['real_functions']); r['rec']=f(r['func_recall_pct']);r['prec']=f(r['func_precision_pct'])
    r['lines']=None
    bylang[r['language']].append(r)
for l in bylang: bylang[l].sort(key=lambda r:(r['timestamp_utc']))
zero=[r for l in bylang for r in bylang[l] if not r['real']]
excl['rows real empty/0 (recall undefined)']=len(zero)
excl['  of which found_functions also 0']=sum(1 for r in zero if not r['found'])
# blob cache
bc={}
def blob_stats(i,lang):
    p=subprocess.run(G+['rev-parse','--verify','-q',f'{shas[i]}:{LD}{lang}.py'],capture_output=True,text=True)
    b=p.stdout.strip()
    if not b: return None
    if b not in bc:
        t=subprocess.run(G+['cat-file','blob',b],capture_output=True).stdout.decode('utf8','replace')
        bc[b]=(t.count('re.compile('),t.count('\n'))
    return bc[b]
steps=[];pairs=[]
for l,rs in bylang.items():
    for a,b in zip(rs,rs[1:]):
        i0,i1=a['i'],b['i']
        if i1<i0: continue
        d={'language':l,'c0':shas[i0][:10],'c1':shas[i1][:10],'i0':i0,'i1':i1,'win_len':i1-i0,'date1':b['timestamp_utc'][:10]}
        d['d_found']=b['found']-a['found']; d['rel_found']=(d['d_found']/a['found']) if a['found'] else None
        d['d_rec']=(b['rec']-a['rec']) if (a['rec'] is not None and b['rec'] is not None) else None
        d['d_prec']=(b['prec']-a['prec']) if (a['prec'] is not None and b['prec'] is not None) else None
        win=range(i0+1,i1+1)
        d['lang_commits']=[shas[k][:10] for k in langfiles.get(l,[]) if i0<k<=i1]
        d['core_commits']=sum(1 for k in win if corec[k+1]-corec[k])
        d['core_files']=sorted({p.split('/')[-1] for k in win for p in corelist.get(k,())})[:8]
        crit_rec=d['d_rec'] is not None and abs(d['d_rec'])>=1.0
        crit_f=(a['found']>0 and abs(d['d_found'])/a['found']>=0.05) or (a['found']==0 and b['found']>0)
        d['q_rec']=crit_rec; d['q_found']=crit_f; d['quality_step']=crit_rec or crit_f
        d['pre_langfile_era']=i1<alllang_first
        s0=blob_stats(i0,l); s1=blob_stats(i1,l)
        d['rules0']=s0[0] if s0 else None; d['rules1']=s1[0] if s1 else None
        d['lines1']=s1[1] if s1 else None
        d['d_rules']=(s1[0]-s0[0]) if (s0 and s1) else None
        pairs.append(d)
steps=[d for d in pairs if d['quality_step']]
out={'N_first_parent':N,'first_lang_file_idx':alllang_first,'first_lang_file_date':datetime.datetime.utcfromtimestamp(ts[alllang_first]).isoformat(),
 'rows_total':len(rows),'excluded':dict(excl),'shas_not_on_first_parent':len(miss),'mapped_by_date':len(mapped),'rows_on_mapped_shas':sum(1 for r in rows if r['commit_sha'] in mapped),
 'languages':len(bylang),'consecutive_pairs':len(pairs),'quality_steps':len(steps),
 'steps_recall_crit':sum(d['q_rec'] for d in pairs),'steps_found_crit':sum(d['q_found'] for d in pairs)}
# Q4a
def has(d): return len(d['lang_commits'])>0
withlang=sum(has(d) for d in steps)
out['Q4a_steps_with_langfile']=withlang; out['Q4a_share']=withlang/len(steps)
elig=[d for d in steps if not d['pre_langfile_era']]
out['Q4a_pre_langfile_era_steps']=len(steps)-len(elig)
out['Q4a_share_post_era']=sum(has(d) for d in elig)/len(elig) if elig else None
nolang=[d for d in steps if d['language'] not in langfiles]
out['Q4a_steps_language_without_rule_file']=len(nolang)
# length
wl=np.array([d['win_len'] for d in steps])
out['win_len_median']=float(np.median(wl)); out['win_len_p25_p75']=[float(np.percentile(wl,25)),float(np.percentile(wl,75))]
out['share_win_gt50']=float((wl>50).mean()); out['share_win_eq1']=float((wl==1).mean()); out['n_win_eq1']=int((wl==1).sum())
out['n_win_le0']=int((wl<=0).sum())
# single-commit windows with langfile
one=[d for d in steps if d['win_len']==1]
out['single_commit_windows_with_langfile']=sum(has(d) for d in one)
# permutation
rng=random.Random(1)
def langpref(l):
    arr=np.zeros(N+1,int)
    for k in langfiles.get(l,[]): arr[k+1]+=1
    return np.cumsum(arr)
lo=min(d['i0'] for d in pairs)  # first measured index
pre={l:langpref(l) for l in bylang}
def base(d,lo_):
    L=d['win_len']; P=pre[d['language']]
    starts=np.arange(lo_,N-L)  # window (s, s+L]
    if len(starts)==0: return None
    return float(np.mean((P[starts+L+1]-P[starts+1])>0))
bs=[base(d,lo) for d in steps]
out['perm_first_measured_idx']=lo
out['perm_exact_expected_share_all']=float(np.mean([b for b in bs if b is not None]))
# sampled permutations distribution
sh=[]
for _ in range(2000):
    c=0
    for d in steps:
        L=d['win_len']; P=pre[d['language']]; s=rng.randrange(lo,N-L)
        c+= (P[s+L+1]-P[s+1])>0
    sh.append(c/len(steps))
out['perm_share_mean']=float(np.mean(sh)); out['perm_share_p95']=float(np.percentile(sh,95)); out['perm_share_max']=float(max(sh))
out['perm_p_ge_observed']=float(np.mean([x>=out['Q4a_share'] for x in sh]))
# Q4b
percommit=collections.defaultdict(set); stepcommit=collections.defaultdict(set)
for l,rs in bylang.items():
    for r in rs: percommit[r['i']].add(l)
for d in steps: stepcommit[d['i1']].add(d['language'])
firsti=min(percommit)
big=[(i,len(v)) for i,v in percommit.items() if len(v)>=5]
out['measured_commits']=len(percommit); out['first_measured_commit_langs']=len(percommit[firsti])
out['Q4b_commits_ge5_rows_total']=len(big); out['Q4b_commits_ge5_rows_excl_first']=len([b for b in big if b[0]!=firsti])
big_s=[(i,len(v)) for i,v in stepcommit.items() if len(v)>=5]
out['Q4b_commits_ge5_quality_steps']=len(big_s)
def touch(i):
    ls=[p.split('/')[-1][:-3] for p in files.get(i,()) if kind(p)=='lang']
    return {'idx':i,'sha':shas[i][:10],'date':datetime.datetime.utcfromtimestamp(ts[i]).date().isoformat(),'n_files':len(files.get(i,())),'core_files':sorted(p.replace('gitgalaxy/','') for p in corelist.get(i,()))[:10],'n_core':len(corelist.get(i,())),'lang_files_touched':len(ls)}
big_detail=[]
for i,n in sorted(big):
    t=touch(i); t['n_lang_rows']=n; t['n_lang_quality_steps']=len(stepcommit.get(i,())); big_detail.append(t)
out['Q4b_detail']=big_detail
out['Q4b_with_core_touch']=sum(1 for t in big_detail if t['n_core']>0)
out['Q4b_big_step_commits_core_touch']=sum(1 for i,_ in big_s if corelist.get(i))
# steps whose window has core commit
out['steps_window_core_commit']=sum(d['core_commits']>0 for d in steps)
out['steps_window_lang_and_core']=sum(has(d) and d['core_commits']>0 for d in steps)
out['steps_window_lang_only']=sum(has(d) and d['core_commits']==0 for d in steps)
out['steps_window_core_only']=sum((not has(d)) and d['core_commits']>0 for d in steps)
out['steps_window_neither']=sum((not has(d)) and d['core_commits']==0 for d in steps)
out['steps_single_commit_candidate']=out['n_win_eq1']; out['steps_multi_commit']=len(steps)-out['n_win_eq1']
# needs localisation: window>1 and (lang and core both, or neither, or multiple lang commits)
need=[d for d in steps if d['win_len']>1 and not (has(d) and d['core_commits']==0 and len(d['lang_commits'])==1)]
out['needs_localisation_scan']=len(need)
# Q5
ev=json.load(open(H+'final/out/steps_table.json'))['events']
evok=[e for e in ev if shas[e['index']]==e['sha']]
out['events']=len(ev); out['events_index_matches_fp']=len(evok)
q5=[]
for e in ev:
    k=idx.get(e['sha'],e['index'])
    for d in steps:
        if d['i0']<k<=d['i1']:
            q5.append({'event':e['sha'][:10],'dir':e['direction'],'size_cpu':e['size_cpu'],'lang':d['language'],'win_len':d['win_len'],'d_found':d['d_found'],'d_rec':d['d_rec'],'event_is_end_commit':k==d['i1']})
out['Q5_events_in_any_step_window']=len({q['event'] for q in q5}); out['Q5_event_step_pairs']=len(q5)
out['Q5_events_before_first_measured']=sum(1 for e in ev if idx.get(e['sha'],e['index'])<=lo)
c=collections.Counter()
for q in q5:
    sq='found_up' if q['d_found']>0 else 'found_down' if q['d_found']<0 else 'found_flat'
    c[(q['dir'],sq)]+=1
out['Q5_dir_by_found_sign']={f'{a}|{b}':v for (a,b),v in c.items()}
c2=collections.Counter()
for q in q5:
    if q['d_rec'] is None: c2[(q['dir'],'rec_undefined')]+=1
    else: c2[(q['dir'],'rec_up' if q['d_rec']>0 else 'rec_down' if q['d_rec']<0 else 'rec_flat')]+=1
out['Q5_dir_by_recall_sign']={f'{a}|{b}':v for (a,b),v in c2.items()}
out['Q5_pairs_event_is_end_commit']=sum(q['event_is_end_commit'] for q in q5)
out['Q5_pairs_window_len1']=sum(q['win_len']==1 for q in q5)
out['Q5_pairs']=q5
# per event: net found sign among its windows
# Q6
def sp(x,y):
    if len(x)<3 or len(set(x))<2 or len(set(y))<2: return None
    r=spearmanr(x,y); return [float(r.statistic),float(r.pvalue),len(x)]
def q6(sel,tag):
    sel=[d for d in sel if d['d_rules'] is not None]
    o={'n':len(sel),'n_rules_changed':sum(d['d_rules']!=0 for d in sel)}
    o['pooled_found']=sp([d['d_rules'] for d in sel],[d['d_found'] for d in sel])
    s2=[d for d in sel if d['d_rec'] is not None]
    o['pooled_recall']=sp([d['d_rules'] for d in s2],[d['d_rec'] for d in s2])
    per=[];perr=[]
    for l in {d['language'] for d in sel}:
        s=[d for d in sel if d['language']==l]
        r=sp([d['d_rules'] for d in s],[d['d_found'] for d in s])
        if r: per.append(r[0])
        s=[d for d in s if d['d_rec'] is not None]
        r=sp([d['d_rules'] for d in s],[d['d_rec'] for d in s])
        if r: perr.append(r[0])
    o['within_lang_found_rho_median']=float(np.median(per)) if per else None; o['within_lang_found_n_langs']=len(per)
    o['within_lang_recall_rho_median']=float(np.median(perr)) if perr else None; o['within_lang_recall_n_langs']=len(perr)
    out['Q6_'+tag]=o
q6(steps,'quality_steps'); q6(pairs,'all_consecutive_pairs')
# demeaned within-language pooled (rank within language) on quality steps
# across languages at tip
tip=[]
for l,rs in bylang.items():
    r=rs[-1]; s=blob_stats(N-1,l)
    if s: tip.append({'language':l,'rules':s[0],'lines':s[1],'rec':r['rec'],'found':r['found'],'real':r['real']})
out['Q6_tip_languages_with_rule_file']=len(tip)
t2=[t for t in tip if t['rec'] is not None]
out['Q6_tip_n_recall']=len(t2)
out['Q6_tip_rules_vs_recall']=sp([t['rules'] for t in t2],[t['rec'] for t in t2])
out['Q6_tip_lines_vs_recall']=sp([t['lines'] for t in t2],[t['rec'] for t in t2])
out['Q6_tip_rules_vs_found']=sp([t['rules'] for t in tip],[t['found'] for t in tip])
out['Q6_tip_lines_vs_found']=sp([t['lines'] for t in tip],[t['found'] for t in tip])
out['Q6_tip_rules_vs_real_control']=sp([t['rules'] for t in tip],[t['real'] for t in tip])
out['langs_in_csv_without_rule_file']=sorted(l for l in bylang if l not in langfiles and not __import__('os').path.exists('/dev/null') or l not in langfiles)
# months and languages
mo=collections.Counter(d['date1'][:7] for d in steps); out['steps_by_month']=dict(sorted(mo.items()))
pl=collections.Counter(d['language'] for d in steps); out['steps_by_language']=dict(pl.most_common())
net={}
for l,rs in bylang.items():
    net[l]={'first_found':rs[0]['found'],'last_found':rs[-1]['found'],'net':rs[-1]['found']-rs[0]['found'],'first_rec':rs[0]['rec'],'last_rec':rs[-1]['rec']}
out['top_net_found_gain']=sorted(((l,v['net']) for l,v in net.items()),key=lambda x:-x[1])[:10]
out['net_found_total']=sum(v['net'] for v in net.values())
# attribution of positive delta
cat=collections.defaultdict(float); catn=collections.Counter(); neg=0.0
for d in pairs:
    if d['d_found']<=0: neg+=d['d_found']; continue
    bigc = d['i1'] in dict(big_s)
    if bigc: k='engine-wide (>=5-language commit)'
    elif has(d) and d['core_commits']==0: k='language-specific (lang file only in window)'
    elif d['core_commits']>0 and not has(d): k='engine-wide (core only in window)'
    elif has(d) and d['core_commits']>0: k='both in window (ambiguous)'
    else: k='neither (other files / unattributable)'
    cat[k]+=d['d_found']; catn[k]+=1
out['improvement_attribution_sum_positive_deltas']=dict(cat); out['improvement_attribution_n_pairs']=dict(catn); out['negative_deltas_sum']=neg
out['first_row_commit_excluded_from_improvement']=shas[firsti][:10]
# other series
other={}
for nme in ['call_resolution_history.csv','graph_coverage_history.csv','ground_truth_history.jsonl']:
    t=subprocess.run(G+['show',f'{TIP}:docs/self_scan/{nme}'],capture_output=True,text=True).stdout.splitlines()
    if nme.endswith('jsonl'): sh_={json.loads(x)['commit'] for x in t if x}
    else: sh_={x.split(',')[1] for x in t[1:] if x}
    ts_={r['commit_sha'] for r in rows}
    other[nme]={'lines':len(t),'distinct_commits':len(sh_),'also_in_ts_accuracy':len(sh_&ts_),'share_of_series_commits_in_ts':len(sh_&ts_)/len(sh_)}
out['other_series']=other
out['ts_distinct_commits']=len({r['commit_sha'] for r in rows})
# write
json.dump(out,open('results.json','w'),indent=1,default=str)
with open('quality_steps.csv','w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['language','c0','c1','i0','i1','win_len','date1','d_found','rel_found','d_rec','d_prec','q_rec','q_found','lang_file_commits_in_window','n_core_commits_in_window','core_files','rules0','rules1','d_rules','needs_localisation_scan'])
    nid={id(d) for d in need}
    for d in steps: w.writerow([d['language'],d['c0'],d['c1'],d['i0'],d['i1'],d['win_len'],d['date1'],d['d_found'],d['rel_found'],d['d_rec'],d['d_prec'],d['q_rec'],d['q_found'],';'.join(d['lang_commits']),d['core_commits'],';'.join(d['core_files']),d['rules0'],d['rules1'],d['d_rules'],id(d) in nid])
print('done')
# post-era base rate
el=[d for d in steps if not d['pre_langfile_era']]
b2=[base(d,alllang_first) for d in el]
o2=json.load(open('results.json'))
o2['perm_post_era_n']=len(el);o2['perm_post_era_exact_expected_share']=float(np.mean([b for b in b2 if b is not None]))
o2['perm_post_era_observed']=sum(has(d) for d in el)/len(el)
json.dump(o2,open('results.json','w'),indent=1,default=str)
print(o2['perm_post_era_n'],o2['perm_post_era_exact_expected_share'],o2['perm_post_era_observed'])
