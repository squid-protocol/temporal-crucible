#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""CMB-H1..H3 (docs/cmb_hypotheses.md): zlib + expat; SEM-2 vs closest-version (CV) vs version string; blind audit.

    SFS_SRC=... <engine venv>/bin/python tools/cmb_eval.py prepare   # units, H1, private audit packets (no verdicts)
    SFS_SRC=... <engine venv>/bin/python tools/cmb_eval.py score     # after blind labels are hash-locked
"""
from __future__ import annotations

import json
import multiprocessing
import pathlib
import random
import re
import statistics
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import sem_eval as S  # noqa: E402
import vz_eval as Z  # noqa: E402
import vzt_eval as T  # noqa: E402
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402

PRIV = POOL_DIR / "vz_private"
HIST = POOL_DIR / "vzt_hist"
EXPAT = POOL_DIR / "expat"
EFILES = ("xmlparse.c", "xmlrole.c", "xmltok.c", "xmltok_impl.c", "xmltok_ns.c")
EHOSTS = {"cpython": (HIST / "cpython", ["Modules/expat"]), "cmake-expat": (HIST / "cmake", ["Utilities/cmexpat/lib"]),
          "vtk": (HIST / "vtk", ["ThirdParty/expat/vtkexpat/lib"]), "itk": (HIST / "itk", ["Modules/ThirdParty/Expat/src/itkexpat/lib"]),
          "poco": (HIST / "poco", ["XML/src", "dependencies/expat/src"]), "android-expat": (HIST / "android-expat", ["expat/lib", "lib"])}
SEED, CAP = 2985, 30
git = T.git


def stem(p):
    return re.sub(r"\.(c|cpp|cc)$", ".c", p.rsplit("/", 1)[-1])


def vt(s):
    return tuple(int(x) for x in s.split("."))


# ---------------------------------------------------------------- expat fixes
def expat_fixes():
    txt = (EXPAT / "expat" / "Changes").read_text(errors="replace")
    merges = {}
    for l in git(EXPAT, "log", "--merges", "--first-parent", "--format=%H %s", "HEAD").splitlines():
        m = re.search(r"Merge pull request #(\d+)", l)
        if m:
            merges.setdefault(int(m.group(1)), l.split()[0])
    items = []
    for b in re.split(r"\n(?=Release \d)", txt):
        m = re.match(r"Release (\d+\.\d+\.\d+)", b)
        if not m or "Security fixes:" not in b:
            continue
        s = re.split(r"\n\s*(?:Bug fixes|Other changes|Special thanks):", b.split("Security fixes:", 1)[1])[0]
        for it in re.split(r"\n(?=\s*#\d)", s):
            head = it.strip().split("--")[0]
            prs = [int(x) for x in re.findall(r"#(\d+)", head)]
            cves = sorted(set(re.findall(r"CVE-\d{4}-\d+", head)))
            if cves and prs and all(p in merges for p in prs):
                items.append({"release": vt(m.group(1)), "cves": cves, "text": " ".join(it.split())[:400], "merges": [merges[p] for p in prs]})
    return items


def fix_functions_generic(repo, parent, sha, keep):
    """{(path, name): {R, A, pre, post}} via tree-sitter only (no engine fallback for expat; noted)."""
    hunks, cur, h = defaultdict(list), None, None
    for ln in git(repo, "diff", "-U0", "--no-color", "--no-renames", parent, sha).splitlines():
        m = Z.U.FILE_HDR.match(ln)
        if m:
            cur = m.group(1) if m.group(1) and keep(m.group(1)) else None
            continue
        if not cur:
            continue
        mh = Z.HUNK.match(ln)
        if mh:
            h = {"s": max(int(mh.group(1)), 1), "R": [], "A": []}
            hunks[cur].append(h)
        elif h is not None and ln[:1] in "+-" and not ln.startswith(("+++", "---")):
            (h["R"] if ln[0] == "-" else h["A"]).append(Z.U.norm(ln[1:]))
    out = {}
    for path, hs in hunks.items():
        pre = [x for x in Z.U.spans(git(repo, "show", f"{parent}:{path}", text=False), "c") if not Z.MACROISH.match(x[2])]
        post = {nm: body for _a, _b, nm, body in Z.U.spans(git(repo, "show", f"{sha}:{path}", text=False), "c")}
        for hh in hs:
            hit = next(((nm, body) for a, b, nm, body in pre if a <= hh["s"] <= b), None)
            if hit is None:
                continue
            nm, body = hit
            d = out.setdefault((path, nm), {"R": set(), "A": set(), "pre": body, "post": post.get(nm, "")})
            d["R"].update(x for x in hh["R"] if Z.code_line(x))
            d["A"].update(x for x in hh["A"] if Z.code_line(x))
    return out


def per_file(funcs):
    pf = defaultdict(lambda: {"R": set(), "A": set(), "F": set(), "pre": {}})
    for (path, nm), d in funcs.items():
        k = stem(path)
        pf[k]["R"] |= d["R"]
        pf[k]["A"] |= d["A"]
        pre = "\x01" + "\x01".join(S.norm_toks(d["pre"])) + "\x01"
        pf[k]["F"] |= {x for x in S.fragments(d["A"]) if not S.present(x, pre)}
        pf[k]["pre"][nm] = d["pre"]
    return dict(pf)


def libraries():
    libs = {}
    # zlib
    zf = {}
    for f in Z.FIXES:
        es = Z.engine_spans(Z.OUT / f"zlib@{f[:9]}^" / f"zlib@{f[:9]}^_galaxy_master.db")
        zf[f[:9]] = {"release": Z.RELEASE[f[:9]], "label": Z.CVE[f[:9]],
                     "text": f"{Z.CVE[f[:9]]}: " + git(Z.ZLIB, "show", "-s", "--format=%s", f).strip(),
                     "files": per_file(Z.fix_functions(f, es)), "diff": {stem(p): git(Z.ZLIB, "show", "--format=", f, "--", p)
                                                                       for p in git(Z.ZLIB, "show", "--format=", "--name-only", f).split() if p.endswith(".c")}}
    zhosts = {n: (r, [p] if p else [""]) for n, (r, p, _h) in T.HOSTS.items()}
    libs["zlib"] = {"fixes": zf, "hosts": zhosts, "files": T.FILES, "up": T.upstream()[0]}
    # expat
    ef = {}
    for it in expat_fixes():
        funcs = {}
        diffs = defaultdict(str)
        for m in it["merges"]:
            for k, v in fix_functions_generic(EXPAT, f"{m}^1", m, lambda p: p.startswith("expat/lib/") and p.endswith(".c")).items():
                if k in funcs:
                    funcs[k]["R"] |= v["R"]
                    funcs[k]["A"] |= v["A"]
                else:
                    funcs[k] = v
            for p in git(EXPAT, "diff", "--name-only", f"{m}^1", m, "--", "expat/lib").split():
                if p.endswith(".c"):
                    diffs[stem(p)] += git(EXPAT, "diff", f"{m}^1", m, "--", p)
        if funcs:
            key = it["merges"][0][:9]
            ef[key] = {"release": it["release"], "label": ",".join(it["cves"]), "text": it["text"], "files": per_file(funcs), "diff": dict(diffs)}
    up = defaultdict(dict)
    for t in sorted(git(EXPAT, "tag").split()):
        m = re.fullmatch(r"R_(\d+)_(\d+)_(\d+)", t)
        if not m:
            continue
        v = tuple(int(x) for x in m.groups())
        for f in EFILES:
            txt = git(EXPAT, "show", f"{t}:expat/lib/{f}") or git(EXPAT, "show", f"{t}:lib/{f}")
            if txt:
                up[f].setdefault(T.normws(txt), v)
    libs["expat"] = {"fixes": ef, "hosts": EHOSTS, "files": EFILES, "up": dict(up)}
    return libs


# ---------------------------------------------------------------- host states
def states_of(lib, name, cfg):
    repo, paths = cfg
    head = "HEAD"
    spec = []
    for p in paths:
        for f in lib["files"]:
            spec.append(f":(glob){p + '/' if p else ''}**/{f}")
            if f.endswith(".c"):
                spec.append(f":(glob){p + '/' if p else ''}**/{f[:-2]}.cpp")
    out, seen = [], None
    for line in git(repo, "log", "--first-parent", "--format=%H %ct", head, "--", *spec).splitlines()[::-1]:
        sha, ct = line.split()
        trees = "|".join(git(repo, "rev-parse", f"{sha}:{p}").strip() if p else git(repo, "rev-parse", f"{sha}^{{tree}}").strip() for p in paths)
        if trees != seen:
            out.append((sha, int(ct)))
            seen = trees
    return out


def state_files(task):
    libname, name, repo, paths, files, sha, ct = task
    ls = git(repo, "ls-tree", "-r", "--name-only", sha, "--", *[p or "." for p in paths]).splitlines()
    pick = {}
    for f in files:
        c = sorted((p for p in ls if stem(p) == f and "/test" not in p and "/contrib/" not in p), key=len)
        if c:
            pick[f] = c[0]
    texts = {f: git(repo, "show", f"{sha}:{p}") for f, p in pick.items()}
    ver = None
    if libname == "zlib":
        for p in sorted(x for x in ls if x.rsplit("/", 1)[-1] in ("zlib.h", "zlib.h.in", "zlib-ng.h.in")):
            m = re.search(r'define ZLIB_VERSION "([^"]+)"', git(repo, "show", f"{sha}:{p}"))
            if m:
                ver = T.vtuple(m.group(1))
                break
    else:
        hs = [x for x in git(repo, "ls-tree", "-r", "--name-only", sha).splitlines() if x.endswith("/expat.h") or x == "expat.h"]
        base = (paths[0] or "").split("/")
        hs.sort(key=lambda x: -sum(1 for a, b in zip(x.split("/"), base) if a == b))
        for p in hs[:3]:
            t = git(repo, "show", f"{sha}:{p}")
            mm = [re.search(rf"define XML_{k}_VERSION (\d+)", t) for k in ("MAJOR", "MINOR", "MICRO")]
            if all(mm):
                ver = tuple(int(x.group(1)) for x in mm)
                break
    return libname, name, sha, ct, ver, texts


def cv_verdict(up_f, text, rel):
    lines = {T.Z.U.norm(x) for x in text.splitlines() if T.Z.U.norm(x)}
    lines = {x for x in lines if Z.code_line(x)}
    best = None
    for norm_txt, v in up_f.items():
        ul = {x for x in (T.Z.U.norm(y) for y in norm_txt.splitlines()) if Z.code_line(x)}
        j = len(lines & ul) / max(len(lines | ul), 1)
        if best is None or (j, v) > best:
            best = (j, v)
    if not best or best[0] < 0.5:
        return None, None
    return ("patched" if best[1] >= rel else "unpatched"), best[1]


def build_units():
    t0 = time.time()
    libs = libraries()
    print({k: len(v["fixes"]) for k, v in libs.items()}, f"fixes ({time.time() - t0:.0f}s)", flush=True)
    tasks = []
    for ln, lib in libs.items():
        for name, cfg in lib["hosts"].items():
            st = states_of(lib, name, cfg)
            print(f"  {ln}/{name}: {len(st)} states", flush=True)
            tasks += [(ln, name, cfg[0], cfg[1], lib["files"], s, c) for s, c in st]
    with multiprocessing.get_context("fork").Pool(8) as p:
        states = list(p.imap_unordered(state_files, tasks, chunksize=2))
    units = []
    for ln, name, sha, ct, ver, texts in states:
        lib = libs[ln]
        for fk, fx in lib["fixes"].items():
            rel = fx["release"]
            for fname, ra in fx["files"].items():
                if fname not in texts or not (ra["R"] or ra["A"]):
                    continue
                txt = texts[fname]
                verb = lib["up"].get(fname, {}).get(T.normws(txt))
                cvv, cvrel = cv_verdict(lib["up"].get(fname, {}), txt, rel)
                units.append({"lib": ln, "host": name, "sha": sha[:12], "ct": ct, "fix": fk, "label": fx["label"], "file": fname,
                              "sem2": S.sem(txt, ra["R"], ra["A"], ra["F"]), "line": T.check(txt, ra["R"], ra["A"]),
                              "cv": cvv, "cv_release": list(cvrel) if cvrel else None,
                              "ver": None if not ver else ("patched" if ver >= rel else "unpatched"),
                              "truth": None if not verb else ("patched" if verb >= rel else "unpatched")})
    return libs, states, units


def fn_excerpt(text, names):
    sp = Z.U.spans(text.encode(), "c")
    got = [body for _a, _b, nm, body in sp if nm in names]
    return "\n\n".join(got)[:12000] if got else text[:6000]


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "prepare"
    t0 = time.time()
    libs, states, units = build_units()
    L = ["# CMB-H1..H3 — zlib + expat; SEM-2 vs closest-version (SCORED; aggregates only)", "",
         f"- fixes: zlib {len(libs['zlib']['fixes'])}, expat {len(libs['expat']['fixes'])}; host states {len(states):,}; units {len(units):,}"]
    # H1 (expat verbatim)
    ev = [u for u in units if u["lib"] == "expat" and u["truth"]]
    wrong = sum(u["sem2"] in ("patched", "unpatched") and u["sem2"] != u["truth"] for u in ev)
    up99 = 1 - T.wilson(len(ev) - wrong, len(ev)) if ev else float("nan")
    v1 = "not evaluable" if len(ev) < 100 else ("SUPPORTED" if wrong / len(ev) <= 0.01 and up99 <= 0.02 else "not supported")
    # audit sample: SEM-2 vs CV both decided and disagree, non-verbatim
    rnd = random.Random(SEED)
    sample = []
    for ln in libs:
        d = [u for u in units if u["lib"] == ln and not u["truth"] and u["sem2"] in ("patched", "unpatched") and u["cv"] and u["sem2"] != u["cv"]]
        d.sort(key=lambda u: (u["host"], u["sha"], u["fix"], u["file"]))
        sample += rnd.sample(d, CAP) if len(d) > CAP else d
    if mode == "prepare":
        packets = []
        stmap = {(s[0], s[1], s[2][:12]): s for s in states}
        for i, u in enumerate(sample):
            fx = libs[u["lib"]]["fixes"][u["fix"]]
            texts = stmap[(u["lib"], u["host"], u["sha"])][5]
            names = set(fx["files"][u["file"]]["pre"])
            packets.append({"id": i, "library": u["lib"], "vulnerability": fx["text"], "file": u["file"],
                            "upstream_fix_diff": fx["diff"].get(u["file"], "")[:15000],
                            "host_code_of_changed_functions": fn_excerpt(texts[u["file"]], names)})
        (PRIV / "cmb_audit_packets.json").write_text(json.dumps(packets, indent=1))
        (PRIV / "cmb_audit_keys.json").write_text(json.dumps(sample, indent=1))
        print(f"audit packets {len(packets)} (zlib {sum(u['lib'] == 'zlib' for u in sample)}, expat {sum(u['lib'] == 'expat' for u in sample)})")
    L += ["", "| claim | result | verdict |", "|---|---|---|",
          f"| **CMB-H1** SEM-2 no new errors on expat verbatim truth | wrong {wrong} / {len(ev)}; Wilson 99% upper {up99:.2%} | **{v1}** |"]
    if mode == "score":
        lab = json.loads((PRIV / "cmb_audit_labels.json").read_text())
        keys = json.loads((PRIV / "cmb_audit_keys.json").read_text())
        sw = cw = n = 0
        for k, l in zip(keys, sorted(lab, key=lambda x: x["id"])):
            if l["label"] not in ("patched", "unpatched"):
                continue
            n += 1
            sw += k["sem2"] == l["label"]
            cw += k["cv"] == l["label"]
        from scipy.stats import binomtest
        disc_s, disc_c = sw, cw  # every audited unit is a disagreement, so exactly one method is right (or neither)
        p = binomtest(disc_s, disc_s + disc_c, 0.5, alternative="greater").pvalue if disc_s + disc_c else 1.0
        v2 = "not evaluable" if n < 10 else ("SUPPORTED" if disc_s > disc_c and p < 0.01 / 3 else "not supported")
        L.append(f"| **CMB-H2** SEM-2 beats closest-version (blind audit) | SEM-2 right {sw}/{n}, CV right {cw}/{n}; sign test p = {p:.2g} | **{v2}** |")
        L.append("| **CMB-H3** vs OSV-scanner | not run: executing the third-party binary needs owner approval | **not evaluable** |")
    L += ["", "## Per library and method (descriptive)", "", "| library | method | verbatim accuracy (decided) | wrong calls | coverage (all units) |", "|---|---|---:|---:|---:|"]
    for ln in libs:
        uu = [u for u in units if u["lib"] == ln]
        vv = [u for u in uu if u["truth"]]
        for m in ("sem2", "line", "cv", "ver"):
            dec = [u for u in vv if u[m] in ("patched", "unpatched")]
            ok = sum(u[m] == u["truth"] for u in dec)
            L.append(f"| {ln} | {m} | {ok}/{len(dec)} | {len(dec) - ok} | {sum(u[m] in ('patched', 'unpatched') for u in uu) / max(len(uu), 1):.0%} |")
    L += ["", f"- audit sample (SEM-2 vs CV disagreements, non-verbatim): {len(sample)} units; "
          + ", ".join(f"{ln} {sum(u['lib'] == ln for u in sample)}" for ln in libs),
          f"- non-verbatim SEM-2 × CV (both decided): {dict(Counter((u['lib'], u['sem2'], u['cv']) for u in units if not u['truth'] and u['sem2'] in ('patched', 'unpatched') and u['cv']))}",
          "", f"Runtime {time.time() - t0:.0f}s · seed {SEED}."]
    (DOCS_DIR / ("cmb.md" if mode == "score" else "cmb_prepare.md")).write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
