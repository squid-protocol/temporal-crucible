"""Load function-level columns from the population DB into a pickle: sizes, args, call-out names, keyword signals, with language and repo."""
import json
import pickle
import sqlite3
import sys

import numpy as np
import pandas as pd

D = "/srv/storage_16tb/projects/gitgalaxy-population-analyses/data/master_db_v2.9.0.db"
OUT = "/tmp/gitgalaxy-scratch/claude/pop_fn.pkl"
con = sqlite3.connect(f"file:{D}?mode=ro", uri=True)
cols = [r[1] for r in con.execute("pragma table_info(function_data)")]
sig = [c for c in cols if c.startswith(("struct_", "state_", "def_", "arch_", "threat_", "sec_", "lit_", "llm_")) or c in ("bitwise_ops", "lazy_evaluation", "vectorized_math", "ml_traditional", "dl_frameworks")]
sel = ", ".join(f"f.{c}" for c in sig)
q = f"SELECT f.id, f.file_id, f.func_name, f.complexity, f.loc, f.args, f.keyword_density, f.is_public, f.calls_out_to, fi.language, fi.repo_name, {sel} FROM function_data f JOIN file_data fi ON fi.id = f.file_id WHERE f.loc > 0"
rows = []
cur = con.execute(q)
names = [d[0] for d in cur.description]
n = 0
while True:
    chunk = cur.fetchmany(500000)
    if not chunk:
        break
    rows.append(pd.DataFrame(chunk, columns=names))
    n += len(chunk)
    print(n, file=sys.stderr, flush=True)
df = pd.concat(rows, ignore_index=True)
del rows


def parse(s):
    if not s or s == "[]":
        return ()
    try:
        return tuple(json.loads(s))
    except Exception:
        return ()


calls = df["calls_out_to"].map(parse)
df["n_callees"] = calls.map(lambda t: len(set(t)))
df["calls"] = calls
df = df.drop(columns=["calls_out_to"])
for c in sig + ["complexity", "loc", "args", "keyword_density"]:
    df[c] = pd.to_numeric(df[c], errors="coerce").astype("float32")
pickle.dump((df, sig), open(OUT, "wb"), protocol=4)
print("rows", len(df), "signals", len(sig))
