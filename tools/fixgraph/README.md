# tools/fixgraph: call-graph position vs fix history (exploratory archive)

Scripts behind `docs/fix_radius_orchestrators.md`. **Exception to "every tool is stdlib-only":** these need `numpy` and `networkx` (Poisson regression, rank correlations, bootstrap, graph traversal). They live in a subdirectory so `python -m py_compile tools/*.py` in CI does not cover them, and CI does not run them. Gitgalaxy issue #8958 asks for a stdlib-only rewrite as a committed tool; this directory is the record of what was run, not that tool.

## Layout the scripts expect (`FIXGRAPH_WORK`, default `/tmp/fixgraph-work`)

```
$FIXGRAPH_WORK/repos/<name>/      shallow clone: git clone --shallow-since=2021-01-01 --no-tags <url>
$FIXGRAPH_WORK/src/<name>/        git archive HEAD, with test, doc, vendored, example and benchmark directories removed
$FIXGRAPH_WORK/scan/<name>/       galaxyscope output (wave 1 scripts: study.py, correlate*.py)
$FIXGRAPH_WORK/scan2/<name>/      galaxyscope output (study2.py, and study.py with SCAN=scan2)
```

Scan with `GITGALAXY_DISABLE_GIT_HISTORY=1 galaxyscope <src/name> --output <scan/name>`. `prep_scan.sh <lang> <name>` does the archive, pruning and scan for one repo (`ext_repos.txt` lists the 22 wave-2 repositories with their language). The study was run on gitgalaxy 981e9ec; rerunning on another engine version changes the graph, so record the version.

## Scripts

| script | what it did |
|---|---|
| `correlate.py` | wave 1 first pass: file-level and function-level correlations with fix touches (partial on LOC, complexity), top-5% enrichment, cycle membership, co-change distance against a repo-wide null |
| `correlate2.py` | adds the co-change distance distribution and chain depth and height against fix touches |
| `correlate3.py` | fan-in buckets and ripple (callers changed in the same commit) |
| `correlate4.py` | fan-in x fan-out quadrants with a Poisson size baseline |
| `correlate5.py` | lifecycle-named functions and a path test (the lifecycle result was later withdrawn) |
| `study.py` | wave 1 final: three label definitions (`orig`, `B`, `D`), time halves, producer and consumer classes, pooled; the fresh-repo test |
| `study2.py` | wave 2: C, Go and Java, language-aware function attribution (git's `golang` and `java` diff drivers), a directory-matched null for the fix radius, a percentile orchestrator definition, random-effects pooling |

`python study2.py B` and `python study2.py D` read `ext_repos.txt` from the work directory. Do not rerun the scripts on a repository and read the output as a registered result: see the write-up for the label and checklist status.

Outputs from the runs are in `docs/fix_radius_orchestrators/results/` (`res_*` wave 1 first pass, `res2_*`, `res3_*`, `res4_*`, `res5_*` the later wave 1 passes, `r2_*` the wave 1 rerun after the engine update, `ext_B.txt` and `ext_D_pooled.txt` wave 2).
