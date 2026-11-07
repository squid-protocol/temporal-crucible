import multiprocessing as mp, pathlib, sqlite3, collections, sys
sys.path.insert(0, '/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/fort/tools')
R = pathlib.Path('/srv/storage_16tb/projects/temporal-crucible-pool/kw_scan/crucible/data')
con = sqlite3.connect('file:/srv/storage_16tb/projects/temporal-crucible-pool/kw_scan/data_galaxy_master.db?mode=ro', uri=True)
files = [r[0] for r in con.execute("select file_path from file_data where language='cobol' order by total_loc desc")]
def work(path, q):
    import cmt_gate as G, tree_sitter_language_pack as t
    from gitgalaxy.core.prism import Prism
    from gitgalaxy.standards.gitgalaxy_config import LEXICAL_FAMILY_HEURISTICS as LH
    from gitgalaxy.standards.language_standards import LANGUAGE_DEFINITIONS as LD
    raw = (R / path).read_bytes(); txt = raw.decode('utf-8', 'replace')
    pos = Prism(LH, LD).split_positional_comment_stream(txt, 'cobol').split('\n')
    eng = {i for i, l in enumerate(pos) if l.strip()}
    ref = G.ts_comment_lines(t.get_parser('cobol'), raw)
    lines = txt.split('\n')
    miss = [lines[i] for i in sorted(ref - eng) if i < len(lines)]
    import re
    def kind(l):
        u = l.rstrip("\r")
        if re.match(r"^\s*(PROCESS|CBL)\b", u, re.I): return "compiler directive (PROCESS/CBL)"
        if len(u) > 72 and u[72:].strip(): return "text in cols 73-80 (identification area)"
        if not u.strip(): return "blank line"
        if re.match(r"^.{7}\s*(AUTHOR|INSTALLATION|DATE-WRITTEN|DATE-COMPILED|SECURITY|REMARKS)\b", u, re.I): return "ID-division comment-entry header"
        return "ordinary code/data line"
    q.put(("K", [kind(l) for l in miss]))
    q.put((path, len(eng), len(ref), len(eng & ref), miss[:4]))
q = mp.get_context('fork').Queue(); done = 0
kinds = collections.Counter()
for path in files[:40]:
    p = mp.get_context('fork').Process(target=work, args=(path, q)); p.start(); p.join(15)
    if p.is_alive(): p.kill(); continue
    if q.empty(): continue
    first = q.get()
    if first[0] == 'K':
        kinds.update(first[1]); first = q.get()
    done += 1
tot=sum(kinds.values()); print('files',done,'missed lines',tot); [print(f'  {k}: {v} ({v/tot:.0%})') for k,v in kinds.most_common()]
