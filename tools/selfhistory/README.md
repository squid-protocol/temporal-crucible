# selfhistory: temporal scans and engine-speed runs of GitGalaxy on itself (exploratory instruments)

Stdlib-only. Not part of the CI `verify` job (it compiles only top-level `tools/*.py`). Hypotheses: `docs/self_hypotheses_draft.md`
(unregistered draft). Data from the first run: `docs/self_speed/`.

| script | what it does |
|---|---|
| `history_scan.py picks` / `daily` | one full scan per US-Eastern day (last first-parent commit of the day) of a GitGalaxy clone, from a real git checkout (never `git archive`: the scanner scans a checkout and an archive extract differently, e.g. it drops `pyproject.toml` from the archive). Resumable. Needs a private bare mirror `mirror.git` beside the script: `git clone --bare --no-local <clone> mirror.git` (a shallow source clone makes per-scan clones cost ~45 s, hence worktrees of the mirror). |
| `compare_dbs.py A.db B.db` | table-by-table comparison of two snapshot DBs (ids mapped to file paths); verdict identical / structure_equal / STRUCTURE_DIFFERS. Used to check delta scans against full scans. |
| `speed_probe.py slots` / `run` | runs each sampled commit's OWN engine on pinned targets with `--file-speed --splicing-speed`, records wall seconds, CPU seconds, stage and per-regex timings, files mapped. Checks provenance (fails if any module loads from the live checkout), detects each engine's supported flags, and redirects the March-2026 engines' hard-coded output directory in throwaway worktrees. |
| `speed_report.py` | median over repeats per slot and target, spread, per-stage table. |

Environment overrides: `GG_REPO` (GitGalaxy clone with history), `GG_PY` (python with the engine dependencies). Targets are
pinned checkouts under `targets/` (keyword-rosetta, cics-crucible, language-crucible at fixed refs).

Known limits: use CPU seconds, not wall seconds (wall repeats at ~18% median spread on a loaded box, CPU at ~1%); the engine's file
screen changes over time, so compare per mapped file; the 2026-05-26 engine prints no `PIPELINE_SUCCESS` line (pipeline seconds blank);
engines before 2026-07-27 have no stage timers; the delta-chain driver is not included (delta scans differ from full scans until
gitgalaxy PR #8775 lands).
