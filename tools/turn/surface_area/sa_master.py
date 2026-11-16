"""Population check on the v2.12.0 master database: up to 300 random code files per repo, 643 repos; same descriptive tests as sa_describe.py."""
import sys, sqlite3, pickle, pandas as pd, numpy as np
sys.path.insert(0,".")
import sa_load as L
DB="/srv/storage_16tb/projects/gitgalaxy-population-analyses/data/master_db_v2.12.0-b64f42bf.db"
con=sqlite3.connect(f"file:{DB}?mode=ro",uri=True)
cols=[r[1] for r in con.execute("PRAGMA table_info(file_data)")]; a=cols.index("struct_branch"); z=cols.index("arch_sys_config"); sig=cols[a:z+1]
want=["repo_name"]+[c for c in L.BASE+L.RISK+sig+["raw_churn_freq","ownership_entropy","silo_risk","ai_threat_score"] if c in cols]
q=f"SELECT {','.join(want)} FROM (SELECT {','.join(want)}, row_number() OVER (PARTITION BY repo_name ORDER BY random()) rn FROM file_data WHERE function_count>=1) WHERE rn<=300"
df=pd.read_sql_query(q,con); df=df.rename(columns={"repo_name":"repo"}); df["snap"]=0; df["nsnap"]=1
print(df.shape, df.repo.nunique(),"repos"); pickle.dump((df,sig),open("sa_master.pkl","wb"))
