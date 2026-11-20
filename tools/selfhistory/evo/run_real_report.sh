#!/bin/bash
# The epic-#8715 evolution report generator (temporal-crucible branch sensor-overhaul, tools/report/evolution_report.py, commit 371cce8 or later) run on GitGalaxy itself.
# Prereqs: a git repo/mirror whose HEAD is the scanned tip, and a snapshots.json (label, date, commit, db) of the daily scans: monthly picks (eight months is too short for its quarterly grid).
# engine-only scans = daily scan DBs filtered to engine code (tools/selfhistory/evo/make_artifact.py makes the filtered copies); whole-repo = the unfiltered scans.
W=/path/to/temporal-crucible/.claude/worktrees/sensor-overhaul
python3 $W/tools/report/evolution_report.py --repo MIRROR.git --name gitgalaxy-engine --lang python --out OUT --scans snapshots_engine.json --cache CACHE --blame 2500
