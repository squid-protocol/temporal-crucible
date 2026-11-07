import re, sys, sqlite3, pathlib, collections, json
sys.path.insert(0, '/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/kwp/tools')
import kw_eval as K
from gitgalaxy.standards.language_standards import LANGUAGE_DEFINITIONS as LD
from gitgalaxy.recorders import record_keeper as RK
G = pathlib.Path(RK.__file__).parents[2]
src = open(RK.__file__).read()
m = dict(re.findall(r'"([a-z_0-9]+)": "([a-z_0-9]+)"', src))
D = '/srv/storage_16tb/projects/gitgalaxy-population-analyses/data/master_db_v2.12.0-b64f42bf.db'
con = sqlite3.connect(f'file:{D}?mode=ro', uri=True)
cols = [c[1] for c in con.execute('PRAGMA table_info(function_data)')]
sig = [c for c in cols if c not in K.NON_SIGNAL and c not in K.STYLE]
col2rule = {v: k for k, v in m.items() if v in sig}
prev = dict(zip(sig, con.execute('SELECT ' + ', '.join(f'AVG(COALESCE({c},0) > 0)' for c in sig) + ' FROM function_data').fetchone()))
LANGS = ['c', 'cpp', 'python', 'typescript', 'javascript', 'java', 'go', 'rust', 'php', 'cobol']
CR = pathlib.Path('/srv/storage_16tb/projects/temporal-crucible-pool/kw_scan/crucible/data')
from gitgalaxy.core.prism import Prism
from gitgalaxy.standards.gitgalaxy_config import LEXICAL_FAMILY_HEURISTICS
PR = Prism(LEXICAL_FAMILY_HEURISTICS, LD)
texts = {l: [] for l in LANGS}
ext = {'c': ('.c', '.h'), 'cpp': ('.cpp', '.cc', '.hpp'), 'python': ('.py',), 'typescript': ('.ts',), 'javascript': ('.js',),
       'java': ('.java',), 'go': ('.go',), 'rust': ('.rs',), 'php': ('.php',), 'cobol': ('.cbl', '.cob', '.cpy')}
for l, es in ext.items():
    for f in sorted(CR.rglob('*')):
        if f.suffix.lower() in es and f.is_file() and f.stat().st_size < 400_000:
            raw = f.read_text(errors='replace')
            try:
                texts[l].append(PR.split_streams(raw, l)['code_stream'])
            except Exception:
                pass
        if len(texts[l]) >= 40: break
out = []
for c in sig:
    rule = col2rule.get(c, '?')
    contract = G / 'docs' / f'{rule}_rule_contract.md'
    intent = ''
    if contract.exists():
        lines = [x.strip() for x in contract.read_text().splitlines() if x.strip() and not x.startswith('#')]
        intent = (lines[0] if lines else '')[:160]
    tops = {}
    for l in LANGS:
        rk = LD.get(l, {}).get('rules', {}).get(rule)
        if not hasattr(rk, 'finditer'): continue
        cnt = collections.Counter()
        for t in texts[l]:
            for mm in rk.finditer(t):
                s = ' '.join(mm.group(0).split())[:28].lower()
                if s: cnt[s] += 1
        if cnt: tops[l] = cnt.most_common(4)
    out.append({'column': c, 'rule': rule, 'prevalence': prev[c], 'contract': intent, 'tops': tops})
json.dump(out, open('/home/joe/.claude/jobs/159daf19/tmp/signal_audit_codestream.json', 'w'), indent=1)
for o in out:
    t = '; '.join(f"{l}: " + ', '.join(f"{s}" for s, _ in v[:3]) for l, v in list(o['tops'].items())[:4])
    print(f"{o['column']:26s} ← {o['rule']:26s} {o['prevalence']:6.1%} | {t[:150]}")
