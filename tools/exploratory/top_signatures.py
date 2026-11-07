#!/usr/bin/env python3
"""EXPLORATORY: profile the most common exact signal-presence signatures ("fingerprints") in the population DB:
which signals, languages, repos, archetypes, size, test share, common names, and real examples.

    python tools/exploratory/top_signatures.py --pop <db> [--top 5]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import kw_eval as K  # noqa: E402
from _engine import DOCS_DIR  # noqa: E402
from out_eval import FLAG_T, code  # noqa: E402

SEED = 2982


def rows(pop, sig, extra):
    con = sqlite3.connect(f"file:{pop}?mode=ro", uri=True)
    cur = con.execute(f"SELECT {extra}, {', '.join('(COALESCE(f.' + c + ',0) > 0)' for c in sig)} "
                      "FROM function_data f JOIN file_data fd ON f.file_id = fd.id WHERE f.loc >= 3")
    while True:
        b = cur.fetchmany(250_000)
        if not b:
            break
        yield b
    con.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pop", required=True)
    ap.add_argument("--top", type=int, default=5)
    a = ap.parse_args()
    con = sqlite3.connect(f"file:{a.pop}?mode=ro", uri=True)
    cols = [c[1] for c in con.execute("PRAGMA table_info(function_data)")]
    con.close()
    sig = [c for c in cols if c not in K.NON_SIGNAL and c not in K.STYLE]
    cnt = Counter()
    total = 0
    for b in rows(a.pop, sig, "1"):
        for r in b:
            cnt[r[1:]] += 1
        total += len(b)
        print(f"  pass 1: {total:,}", flush=True)
    top = [k for k, _ in cnt.most_common(a.top)]
    tset = {k: i for i, k in enumerate(top)}
    st = [defaultdict(Counter) for _ in top]
    locs = [[] for _ in top]
    samples = [[] for _ in top]
    seen = [0] * len(top)
    rnd = random.Random(SEED)
    n = 0
    for b in rows(a.pop, sig, "fd.language, fd.repo_name, fd.file_path, f.func_name, f.start_line, f.loc, f.func_archetype"):
        for r in b:
            i = tset.get(r[7:])
            if i is None:
                continue
            lang, repo, path, name, start, loc, arch = r[:7]
            s = st[i]
            s["lang"][lang] += 1
            s["repo"][repo] += 1
            s["arch"][arch or "?"] += 1
            s["test"][bool(FLAG_T.search(path or ""))] += 1
            base = re.sub(r"\d+", "#", (name or "").split("::")[-1].split(".")[-1].lower())
            s["name"][base] += 1
            locs[i].append(loc)
            seen[i] += 1
            if len(samples[i]) < 400:
                samples[i].append((lang, repo, path, name, start, loc))
            else:
                j = rnd.randrange(seen[i])
                if j < 400:
                    samples[i][j] = (lang, repo, path, name, start, loc)
        n += len(b)
        print(f"  pass 2: {n:,}", flush=True)
    L = ["# EXPLORATORY — the most common function fingerprints (exact signal-presence signatures), population DB v2.12.0-b64f42bf", "",
         f"- functions (loc ≥ 3): {total:,}; distinct signatures {len(cnt):,}; top {a.top} cover {sum(cnt[k] for k in top) / total:.1%}", ""]
    out = []
    for i, k in enumerate(top):
        present = [sig[j] for j, v in enumerate(k) if v]
        s = st[i]
        lc = np.array(locs[i])
        nrepo = len(s["repo"])
        top_repo_share = s["repo"].most_common(1)[0][1] / seen[i]
        ex = []
        langs_done = set()
        for smp in samples[i]:
            if len(ex) >= 6:
                break
            if smp[0] in langs_done and len(langs_done) < 4:
                continue
            c = code(smp[1], smp[2], smp[4], smp[5])
            if c:
                ex.append((smp, c))
                langs_done.add(smp[0])
        L += [f"## #{i + 1}: {{{', '.join(present) or '(no signals)'}}}", "",
              f"- **{seen[i]:,} functions ({seen[i] / total:.1%})** in **{nrepo} repos**; largest single repo holds {top_repo_share:.0%}",
              f"- size: median {np.median(lc):.0f} lines (IQR {np.percentile(lc, 25):.0f}–{np.percentile(lc, 75):.0f})",
              f"- in test paths: {s['test'][True] / seen[i]:.0%}",
              "- languages: " + ", ".join(f"{l} {c / seen[i]:.0%}" for l, c in s["lang"].most_common(8)),
              "- archetypes: " + ", ".join(f"{x} {c / seen[i]:.0%}" for x, c in s["arch"].most_common(5)),
              "- most common names: " + ", ".join(f"`{x}` {c:,}" for x, c in s["name"].most_common(12)),
              "", "Examples:", ""]
        for smp, c in ex:
            snippet = "\n".join(c.split("\n")[:8])
            L += [f"- {smp[0]} · {smp[1]} · `{smp[3]}` ({smp[5]} lines)", "", "```", snippet, "```", ""]
        out.append({"signals": present, "n": seen[i], "repos": nrepo, "langs": s["lang"].most_common(10),
                    "arch": s["arch"].most_common(8), "names": s["name"].most_common(25), "median_loc": float(np.median(lc))})
    (DOCS_DIR / "top_signatures_exploratory.md").write_text("\n".join(L) + "\n")
    (DOCS_DIR / "top_signatures_exploratory.json").write_text(json.dumps(out, indent=1))
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
