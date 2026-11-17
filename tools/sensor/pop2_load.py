"""Load function-level columns from the v2.12.0 population DB (engine-resolved fan-in/fan-out) into a pickle; count callee names per language on the way."""
import collections, json, pickle, sqlite3, sys
import pandas as pd
D = "/srv/storage_16tb/projects/gitgalaxy-population-analyses/data/master_db_v2.12.0-b64f42bf.db"
con = sqlite3.connect(f"file:{D}?mode=ro", uri=True)
cols = [r[1] for r in con.execute("pragma table_info(function_data)")]
sig = [c for c in cols if c.startswith(("struct_", "state_", "def_", "arch_", "threat_", "sec_", "lit_", "llm_")) or c in ("bitwise_ops", "lazy_evaluation", "vectorized_math", "ml_traditional", "dl_frameworks")]
sel = ", ".join(f"f.{c}" for c in sig)
q = f"SELECT f.id, f.func_name, f.complexity, f.loc, f.args, f.is_public, f.func_pagerank, f.func_fan_in, f.func_fan_out, f.calls_out_to, fi.language, fi.repo_name, {sel} FROM function_data f JOIN file_data fi ON fi.id = f.file_id WHERE f.loc > 0"
cur = con.execute(q); names = [d[0] for d in cur.description]
parts, n = [], 0
names_by_lang = collections.defaultdict(collections.Counter)
ci = names.index("calls_out_to"); li = names.index("language")
while True:
    chunk = cur.fetchmany(400000)
    if not chunk: break
    nc = []
    for r in chunk:
        s = r[ci]
        try: t = set(json.loads(s)) if s and s != "[]" else ()
        except Exception: t = ()
        nc.append(len(t)); names_by_lang[r[li]].update(t)
    d = pd.DataFrame(chunk, columns=names).drop(columns=["calls_out_to"]); d["n_callees"] = nc
    for c in sig + ["complexity", "loc", "args", "func_pagerank", "func_fan_in", "func_fan_out"]:
        d[c] = pd.to_numeric(d[c], errors="coerce").astype("float32")
    parts.append(d); n += len(chunk); print(n, file=sys.stderr, flush=True)
df = pd.concat(parts, ignore_index=True)
top = {l: c.most_common(40) for l, c in names_by_lang.items() if sum(c.values()) > 200000}
pickle.dump((df, sig, top), open("/tmp/gitgalaxy-scratch/claude/pop2_fn.pkl", "wb"), protocol=4)
print("rows", len(df))
