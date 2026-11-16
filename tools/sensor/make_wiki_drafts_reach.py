#!/usr/bin/env python3
"""Wiki draft for the reach sensor: revised 08-14 (anchored edits vs origin/main) + patch. python tools/sensor/make_wiki_drafts_reach.py"""
import subprocess, pathlib, difflib
V6="/srv/storage_16tb/projects/gitgalaxy/v6"; OUT=pathlib.Path(__file__).resolve().parents[2]/"docs/sensor-overhaul/wiki-drafts"
n="08-14-api-exposure.md"; o=subprocess.run(["git","-C",V6,"show",f"origin/main:docs/wiki/{n}"],capture_output=True,text=True).stdout; t=o
def edit(a,b,mode="after"):
    global t; assert a in t,a[:60]; t=t.replace(a,a+b if mode=="after" else b+a,1)
RES="> **Research notes:** temporal-crucible, branch `sensor-overhaul`, `docs/sensor-overhaul/sensors/reach.md` and `reach_validity_output.txt`. Exploratory: seven repositories (curl, libgit2, redis, libxml2, prometheus, sphinx, ripgrep), one snapshot each; the history-aware outcome tests cover three."
edit("- Cannot evaluate the semantic complexity of the exported API (e.g., exposing one massive god-object is scored lower in volume than exposing 10 tiny pure functions).","\n- Measures how much a file **offers** (export keywords against private ones), not how much other code **uses** it. The only use-based term is the popularity multiplier (0.2 for no inbound dependents, up to 2.0), which is capped and enters the product, so a heavily used file with few export keywords scores low.\n- C-family public/private conventions are weak signals: header files declare the API but define few functions, so the ratio is computed on the wrong file.")
edit("## Related Components","""## Measured Behavior (exploratory, 2026-11)
"""+RES+"""

- **The call graph is a sound measure of use.** Per function, the engine's cross-file callers agree with a plain text search for outside users at Spearman +0.74 to +0.92 (curl +0.88, libgit2 +0.90, redis +0.90, libxml2 +0.80, prometheus +0.92, sphinx +0.76, ripgrep +0.74). Precision is 1.00 (median: every caller the engine lists is real); recall is about half (median 0.33 to 1.00), because calls to functions the engine cannot resolve (standard library, macros) are not recorded, and the engine finds no outside caller for 10-42% of functions the text says are used elsewhere.
- **Per file, "caller files" counted from those edges** tracks the text-search reach at +0.63 to +0.91 (curl +0.87, libgit2 +0.90, redis +0.91, libxml2 +0.90), better than `pagerank_score` (+0.38 to +0.87) and much better than `import_count` (+0.20 to +0.61).
- **Header files are the exception.** A header declares an interface and defines few functions, so call-based reach is blind to it (Spearman with the number of files that `#include` it: -0.18 to +0.23). The engine's own measures reach +0.38 to +0.71 (`pagerank_score`) and are inconsistent across repositories. An include count, which the engine does not persist, is the right measure for headers.
- **Relation to later fixes (descriptive).** Reach is one of two simple signals that add to code size for ranking later fixes (+0.018, +0.016 and +0.012 AUC on curl, libxml2, libgit2). Files with recent activity and high reach had later-fix rates 2.1, 2.0 and 2.6 times the active-file average; high-reach files with no recent activity were at 0.6 to 1.0 times: quiet foundations are not where fixes land.

**Design direction.** The proposed [Reach sensor](08-26-reach-sensor.md) reports reach as caller counts (files, functions, one hop out) from the call graph, include counts for headers, a "not measured" state for files the graph cannot see, and keeps public-surface counts as context; a migration-scope report lists who is affected by renaming or removing a function.

""","before")
(OUT/"pages"/n).write_text(t)
d="".join(difflib.unified_diff(o.splitlines(True),t.splitlines(True),fromfile=f"a/docs/wiki/{n}",tofile=f"b/docs/wiki/{n}")); (OUT/"patches"/(n[:-3]+".patch")).write_text(d); print(n,"ok")
