import ast,sqlite3,json,collections,sys,os
import numpy as np
from scipy.stats import spearmanr
ROOT="gscan/trees/new"
PAIRS={ # GitGalaxy column -> oracle feature
 "struct_branch":"branch","complexity":"branch","struct_args":"args","struct_closures":"closures","struct_comprehensions":"comps","struct_decorators":"decorators",
 "arch_io":"io","arch_regex":"regex","state_print_hits":"print","arch_time":"time","arch_serialization":"serial","threat_eval_exec":"exec",
 "state_bailout_hits":"raise","state_halt_hits":"exit","def_telemetry":"telemetry","arch_concurrency":"threads","def_sync_locks":"locks","state_cast_hits":"cast",
 "bitwise_ops":"bitwise","arch_globals":"globals","lazy_evaluation":"yield","arch_import":"imports","def_cleanup":"cleanup","is_documented":"doc","arch_events":"events","arch_api":"api","def_safety":"safety","state_danger":"danger"}
IO_ATTR={"read","write","readlines","read_text","write_text","read_bytes","write_bytes","mkdir","unlink","listdir","glob","rglob","copyfile","rmtree","makedirs","iterdir","readline","writelines"}
RX={"search","match","fullmatch","finditer","findall","sub","subn","compile"}
TIME={"time","perf_counter","monotonic","sleep","now","utcnow","strftime","strptime","timedelta","process_time","perf_counter_ns","time_ns"}
SER={"dumps","loads","dump","load","pack","unpack","pickle","safe_load","safe_dump","to_json","from_json","tobytes","frombuffer"}
EX={"eval","exec","system","popen","Popen","run","check_output","check_call","call"}
LOG={"debug","info","warning","error","exception","critical","log","warn"}
THR={"Thread","Lock","RLock","Pool","Process","ThreadPoolExecutor","ProcessPoolExecutor","Queue","Event","Semaphore","submit","imap","imap_unordered","map_async","apply_async"}
CAST={"int","str","float","bool","bytes","list","dict","set","tuple","cast","bytearray"}
def oracle(fn,names):
    c=collections.Counter(); seen=collections.defaultdict(collections.Counter)
    def add(k,n=1,tok=None):
        c[k]+=n
        if tok: seen[k][tok]+=1
    for n in ast.walk(fn):
        if isinstance(n,(ast.If,ast.For,ast.While,ast.AsyncFor,ast.IfExp,ast.ExceptHandler,ast.Assert)): c["branch"]+=1
        if isinstance(n,ast.BoolOp): c["branch"]+=len(n.values)-1
        if isinstance(n,ast.comprehension): c["branch"]+=len(n.ifs)
        if n is not fn and isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)): c["closures"]+=1
        if isinstance(n,(ast.ListComp,ast.SetComp,ast.DictComp,ast.GeneratorExp)): c["comps"]+=1
        if isinstance(n,(ast.Yield,ast.YieldFrom,ast.GeneratorExp)): c["yield"]+=1
        if isinstance(n,ast.Raise): c["raise"]+=1
        if isinstance(n,(ast.With,ast.AsyncWith)): c["cleanup"]+=1
        if isinstance(n,ast.Try) and n.finalbody: c["cleanup"]+=1
        if isinstance(n,ast.Try): c["safety"]+=len(n.handlers)
        if isinstance(n,(ast.Global,ast.Nonlocal)): c["globals"]+=1
        if isinstance(n,(ast.Import,ast.ImportFrom)): c["imports"]+=1
        if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.BitAnd,ast.BitOr,ast.BitXor,ast.LShift,ast.RShift)): c["bitwise"]+=1
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.Invert): c["bitwise"]+=1
        if isinstance(n,ast.Call):
            f=n.func; nm=f.attr if isinstance(f,ast.Attribute) else getattr(f,"id",None); base=getattr(getattr(f,"value",None),"id",None)
            if nm is None: continue
            if nm=="print": add("print",1,nm)
            if nm=="open" or nm in IO_ATTR: add("io",1,nm)
            if base=="re" or nm in RX-{"compile","sub","match","search"} or (nm in("sub","match","search","compile") and base in("re",None) and not isinstance(f,ast.Attribute)) or (nm in("match","search","sub","fullmatch","finditer","findall") and isinstance(f,ast.Attribute)): add("regex",1,nm)
            if nm in TIME or base in("time","datetime"): add("time",1,nm)
            if nm in SER or base in("json","pickle","yaml","struct"): add("serial",1,nm)
            if nm in EX or base in("subprocess",): add("exec",1,nm)
            if nm=="exit" or (nm=="_exit"): add("exit",1,nm)
            if nm in LOG and base in("logger","logging","log","LOG","self","_log","_logger"): add("telemetry",1,nm)
            if nm in THR or base in("threading","multiprocessing"): add("threads",1,nm); 
            if nm in("acquire","release","Lock","RLock","Semaphore"): add("locks",1,nm)
            if nm in CAST and isinstance(f,ast.Name): add("cast",1,nm)
            if nm in("getenv","get") and "environ" in ast.dump(f): add("danger",1,"environ")
            if nm in("register","connect","emit","on","listen","subscribe","add_listener","trigger","dispatch"): add("events",1,nm)
            add("calls",1,nm)
        if isinstance(n,ast.Attribute) and n.attr=="environ": add("danger",1,"environ")
    for d in fn.decorator_list: add("decorators",1,ast.unparse(d)[:30])
    a=fn.args; c["args"]=len(a.posonlyargs+a.args+a.kwonlyargs)+(1 if a.vararg else 0)+(1 if a.kwarg else 0)
    c["doc"]=1 if ast.get_docstring(fn) else 0
    c["api"]=0
    return c,seen
db=sqlite3.connect("file:gscan/trees/new/new_galaxy_master.db?mode=ro",uri=True)
cols=sorted(set(PAIRS)); 
q="select f.file_path,u.func_name,u.start_line,"+",".join("u."+k for k in cols)+" from function_data u join file_data f on f.id=u.file_id"
cache={}; recs=[]
for row in db.execute(q):
    fp=row[0].replace("\\","/"); parts=fp.split("/")
    if "new" in parts: parts=parts[parts.index("new")+1:]
    path=os.path.join(ROOT,*parts)
    if not path.endswith(".py"): continue
    if path not in cache:
        try: cache[path]=ast.parse(open(path,errors="replace").read())
        except Exception: cache[path]=None
    t=cache[path]
    if t is None: continue
    idx=cache.get(path+"#i")
    if idx is None:
        idx={}
        for n in ast.walk(t):
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
                idx[(n.name,n.lineno)]=n
                if n.decorator_list: idx[(n.name,n.decorator_list[0].lineno)]=n
        cache[path+"#i"]=idx
    fn=idx.get((row[1],row[2]))
    if fn is None: continue
    o,seen=oracle(fn,None)
    recs.append((dict(zip(cols,row[3:])),o,seen,parts[-1]))
print("python functions matched to ast:",len(recs))
out=[]
for col,orc in PAIRS.items():
    g=np.array([r[0][col] or 0 for r in recs],float); o=np.array([r[1].get(orc,0) for r in recs],float)
    gp,op=g>0,o>0
    rec=(gp&op).sum()/max(op.sum(),1); prec=(gp&op).sum()/max(gp.sum(),1)
    rho=spearmanr(g,o)[0] if g.std()>0 and o.std()>0 else float("nan")
    miss=collections.Counter()
    for r in recs:
        if r[1].get(orc,0)>0 and not (r[0][col] or 0)>0: miss.update(r[2].get(orc,{}))
    out.append(dict(col=col,oracle=orc,n_oracle=int(op.sum()),n_family=int(gp.sum()),recall=round(rec,3),precision=round(prec,3),rho=None if rho!=rho else round(rho,3),missed_top=miss.most_common(8)))
json.dump(out,open("family_oracle_results.json","w"),indent=1)
print(f'{"family":24s}{"oracle":11s}{"oracle>0":>9s}{"fam>0":>8s}{"recall":>8s}{"prec":>7s}{"rho":>7s}  top tokens in functions the family missed')
for r in out: print(f'{r["col"]:24s}{r["oracle"]:11s}{r["n_oracle"]:9d}{r["n_family"]:8d}{r["recall"]:8.2f}{r["precision"]:7.2f}{(r["rho"] if r["rho"] is not None else float("nan")):7.2f}  {r["missed_top"][:5]}')
