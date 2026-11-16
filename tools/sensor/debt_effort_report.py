import pickle, pathlib, numpy as np, pandas as pd
from scipy.stats import spearmanr
HERE=pathlib.Path(__file__).resolve().parent; res=pickle.load(open(HERE/"debt_effort.pkl","rb"))
D=pd.DataFrame([r for rs in res for r in rs],columns=["repo","churn","fsize","c365","tlen","hint","bulk","age","marker"]); D["lchurn"]=np.log1p(D.churn)
print(f"{len(D):,} repaid markers in {D.repo.nunique()} repos; lines changed in that file by the repaying commit: median {D.churn.median():.0f}, 75th pct {D.churn.quantile(.75):.0f}, 90th pct {D.churn.quantile(.9):.0f}; {100*(D.churn<=2).mean():.0f}% were one- or two-line edits")
print("\nSpearman with the size of the repaying change in that file (within repo, median over repos [min,max])")
for c,lab in (("fsize","file size at the time (lines)"),("c365","file commits in the last year"),("tlen","marker text length"),("hint","scope words in the text (rewrite, refactor, support, implement, handle, all, proper, ...)"),("age","marker age at repayment (years)"),("bulk","other markers repaid in the same file in the same commit")):
    v=[spearmanr(g[c],g.lchurn).statistic for _,g in D.groupby("repo") if len(g)>50]; print(f"  {lab:85s} {np.median(v):+.2f} [{min(v):+.2f},{max(v):+.2f}]")
print("\nshare of repayments that were tiny (<= 5 lines changed in the file) by group")
for lab,m in (("file < 500 lines",D.fsize<500),("file 500-2000 lines",(D.fsize>=500)&(D.fsize<2000)),("file >= 2000 lines",D.fsize>=2000),("scope words present",D.hint==1),("no scope words",D.hint==0),("one marker repaid in the commit",D.bulk==1),("2+ markers repaid together",D.bulk>=2)):
    g=D[m]; print(f"  {lab:34s} n {len(g):5d}   tiny {100*(g.churn<=5).mean():4.0f}%   median change {g.churn.median():.0f} lines   90th pct {g.churn.quantile(.9):.0f}")
