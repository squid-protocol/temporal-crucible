import multiprocessing as mp, time
import tree_sitter_language_pack as t
F = '/srv/storage_16tb/projects/temporal-crucible-pool/kw_scan/crucible/data/cobol/cobrix/test1_copybook.cob'
raw = open(F, 'rb').read()
def run(): t.get_parser('cobol').parse(raw)
for which in ('parse',):
    p = mp.get_context('fork').Process(target=run); s = time.time(); p.start(); p.join(30)
    print('tree-sitter cobol parse alive after 30 s:', p.is_alive(), f'({time.time()-s:.1f}s)')
    if p.is_alive(): p.kill()
