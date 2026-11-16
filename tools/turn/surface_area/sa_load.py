"""Load file-level surface-area (risk_*) vectors and the engine's keyword-family columns from the 13 repos' scan databases."""
import sys, glob, json, sqlite3, pickle, numpy as np, pandas as pd
B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"
REPOS=["curl","redis","libgit2","impacket","sqlmap","ripgrep","tigerbeetle","expat","libxml2","scapy","sphinx","commons-io","prometheus"]
RISK=["risk_cognitive_load","risk_safety_score","risk_tech_debt","risk_verification","risk_api_exposure","risk_concurrency","risk_state_flux","risk_dead_code","risk_spec_match","risk_stability","risk_churn","risk_documentation","risk_secrets_risk"]
BASE=["file_path","language","directory_group","file_archetype","ecosystem_role","total_loc","coding_loc","doc_loc","function_count","avg_func_complexity","max_func_complexity","func_complexity_gini","pagerank_score","normalized_blast_radius","import_count","internal_dependency_links","popularity","control_flow_ratio","encapsulation_ratio","structural_mass"]
def load(name,every=8):
    dbs=sorted(glob.glob(f"{B}/scan_{name}/.work/snap_*_galaxy_master.db")); idx=sorted(set(list(range(0,len(dbs),every))+[len(dbs)-1])); out=[]
    for i in idx:
        con=sqlite3.connect(f"file:{dbs[i]}?mode=ro",uri=True)
        cols=[r[1] for r in con.execute("PRAGMA table_info(file_data)")]
        a=cols.index("struct_branch"); z=cols.index("arch_sys_config"); sig=cols[a:z+1]
        want=[c for c in BASE+RISK+sig if c in cols]
        df=pd.read_sql_query(f"SELECT {','.join(want)} FROM file_data WHERE function_count>=1",con); con.close()
        for c in df.columns:
            if df[c].dtype==object and c not in("file_path","language","directory_group","file_archetype","ecosystem_role"): df[c]=pd.to_numeric(df[c],errors="coerce")
        df["snap"]=i; df["nsnap"]=len(dbs); df["repo"]=name; out.append(df)
    return pd.concat(out,ignore_index=True),sig
if __name__=="__main__":
    frames=[]; sig=None
    for n in REPOS:
        df,s=load(n); frames.append(df); sig=s; print(n,df.shape,flush=True)
    D=pd.concat(frames,ignore_index=True); pickle.dump((D,sig),open("sa_files.pkl","wb")); print(D.shape)
