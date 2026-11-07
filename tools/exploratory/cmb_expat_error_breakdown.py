"""Exploratory (after CMB prepare): direction and concentration of line/SEM-2 errors on expat verbatim truth."""
import sys, pathlib
from collections import Counter
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import cmb_eval as C
libs, states, units = C.build_units()
ev = [u for u in units if u["lib"] == "expat" and u["truth"]]
for m in ("line", "sem2"):
    w = [u for u in ev if u[m] in ("patched", "unpatched") and u[m] != u["truth"]]
    print(m, "wrong by (called, truth):", Counter((u[m], u["truth"]) for u in w))
    c = Counter(u["fix"] for u in w); tot = Counter(u["fix"] for u in ev)
    print("  top fixes:", [(f, libs["expat"]["fixes"][f]["label"][:30], n, tot[f]) for f, n in c.most_common(6)])
    print("  fixes with >=1 wrong:", len(c), "of", len(libs["expat"]["fixes"]))
