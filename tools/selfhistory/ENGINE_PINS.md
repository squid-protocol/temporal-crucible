# Engine identity per instrument (recorded 2026-11-20 after the first independent review)
- Structure scans (`dbs/`, `dbs_events/`, `history_scan.py`, `events_probe.py structure`): the `galaxyscope` on PATH = editable install resolving to the worktree
  /srv/storage_16tb/projects/gitgalaxy-worktrees/engine-main at commit fc8dd712510579907f736ff84a4c09146df21e76 (2026-11-16 22:23 UTC), clean `gitgalaxy/` tree when checked on 2026-11-20.
  This is a living worktree, not a pinned copy; whether it moved during the scans cannot be proven, only that its HEAD is older than the scans.
  The repo snapshots are of the scan day's commit; the SCANNER is the same engine for all of them (not the scan day's engine).
- Speed runs (`speed_probe.py`, `events_probe.py time`, `dense_timing.py`, `bisect_cost.py`): each commit's OWN engine from a detached worktree of `mirror.git`, run with the shared selfscan venv python and PYTHONPATH set to that worktree.
  Provenance check flags only modules loaded from the v6 checkout at entry-module import time; lazy imports in worker processes are not checked.
- delta scans: not used.
