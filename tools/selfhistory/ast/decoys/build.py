#!/usr/bin/env python3
"""Decoy matrix, step 1: build variant folders. For each rosetta language and each token family (menu keywords), two variants of the language's folder:
code (the keyword as a bare line = positive control) and comment (the same keyword after the language's own comment marker). Plus an unmodified baseline."""
import glob, json, os, re, shutil, sys
ROS = "/srv/storage_16tb/projects/gitgalaxy-history/targets/keyword-rosetta"
OUT = sys.argv[1]
COMMENT_STREAM = {"dead_code", "spec_exposure", "fragile_debt", "planned_debt", "doc", "ownership"}
STRUCT = {"structural_boundaries", "func_start", "class_start", "args", "calls_out", "import", "api", "closures", "comprehensions", "decorators", "generics", "macros"}
WORD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
manifest = {}
for d in sorted(glob.glob(f"{ROS}/data/*")):
    lang = os.path.basename(d)
    menu_p = f"{ROS}/docs/menus/{lang}.json"
    mains = glob.glob(f"{d}/main.*")
    if not (os.path.exists(menu_p) and mains and os.path.exists(f"{d}/expected_signals.json")):
        continue
    main = mains[0]; mname = os.path.basename(main)
    text = open(main, errors="surrogateescape").read(); lines = text.split("\n")
    idx = marker = None
    suffix = ""
    for i, l in enumerate(lines):
        j = l.lower().find("decoy:")
        prefix = l[:j] if j >= 0 else ""
        # a real line-comment marker comes right before `decoy:`; the "Graph Decoy" cluster is prose inside a block comment, not a marker
        if 0 < j <= 6 and prefix.strip() and "graph" not in prefix.lower() and not any(ch.isalnum() for ch in prefix.strip()[3:]):
            idx, marker = i, prefix
            end = l.rstrip()
            suffix = next((c for c in (" */", "*/", " -->", "-->", " *)") if end.endswith(c.strip())), "")
            suffix = (" " + suffix.strip()) if suffix else ""
            break
    if idx is None:
        continue
    menu = json.load(open(menu_p))
    fams = {}
    for fam, v in menu.items():
        if fam in COMMENT_STREAM or fam in STRUCT:
            continue
        kws = [k for k in v.get("keywords", []) if WORD.match(k)]
        if kws:
            fams[fam] = kws[0]
    # the language's own string decoy line (it lives in one of the four probe files), cloned with the family keyword as the literal's content
    str_idx = str_re = str_file = str_lines = None
    for fpath in sorted(glob.glob(f"{d}/[abcm]*.*")):
        if os.path.basename(fpath).split(".")[0] not in ("main", "a", "b", "c"):
            continue
        flines = open(fpath, errors="surrogateescape").read().split("\n")
        for i, l in enumerate(flines):
            if "decoy" in l.lower() and not l.strip().startswith(marker.strip()):
                m_ = re.search(r"([\"'])([^\"']*decoy[^\"']*)\1", l, re.I)
                if m_:
                    str_idx, str_re, str_file, str_lines = i, m_, os.path.basename(fpath), flines
                    break
        if str_idx is not None:
            break
    def string_line(kw):
        l, m_ = str_lines[str_idx], str_re
        return l[: m_.start(2)] + kw + l[m_.end(2) :]
    def write(tag, payload, at=None, to_string=False):
        dst = f"{OUT}/{lang}__{tag}"
        shutil.copytree(d, dst)
        if payload is not None:
            src_lines, fname = (str_lines, str_file) if to_string else (lines, mname)
            at = (str_idx if to_string else idx) if at is None else at
            new = src_lines[: at + 1] + [payload] + src_lines[at + 1 :]
            open(f"{dst}/{fname}", "w", errors="surrogateescape").write("\n".join(new))
    write("base", None)
    for fam, kw in fams.items():
        write(f"{fam}__code", kw)
        write(f"{fam}__comment", marker + kw + suffix)
        if str_idx is not None:
            write(f"{fam}__string", string_line(kw), to_string=True)
    manifest[lang] = {"main": mname, "marker": marker, "suffix": suffix, "has_string": str_idx is not None, "string_file": str_file, "families": fams}
json.dump(manifest, open(f"{OUT}/manifest.json", "w"), indent=1)
print("languages", len(manifest), "variant folders", sum(1 + 2 * len(v["families"]) for v in manifest.values()))
