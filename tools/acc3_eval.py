#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""ACC-3 (docs/acc3_hypotheses.md): Go only; ACC-2's scorer with the callgraph template {{posn .Caller}}."""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import acc2_eval as B  # noqa: E402
import acc_eval as A  # noqa: E402


def go(study, repo, env):
    root = (study / "repos" / repo).resolve()
    fmt = "{{posn .Caller}}\t{{posn .Callee}}\t{{.Caller.Name}}\t{{.Callee.Name}}"
    out = {}
    for algo in ("static", "cha"):
        p = subprocess.run(["callgraph", f"-algo={algo}", f"-format={fmt}", "./..."], cwd=root, env=env,
                           capture_output=True, text=True)
        es = set()
        for line in p.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) != 4:
                continue

            def pos(s):
                m = re.match(r"(.*):(\d+):\d+$", s)
                if not m:
                    return None
                try:
                    return str(Path(m.group(1)).resolve().relative_to(root)), int(m.group(2))
                except ValueError:
                    return None
            a, b = pos(parts[0]), pos(parts[1])
            if a and b:
                es.add(((a[0], parts[2], a[1]), (b[0], parts[3], b[1])))
        out[algo], out[algo + "_rc"] = es, p.returncode
    return {"direct": out["static"], "dynamic": out["cha"] - out["static"], "rc": [out["static_rc"], out["cha_rc"]], "err": ""}


B._go = go
B.REPOS = {"prometheus": "go"}
if __name__ == "__main__":
    sys.exit(B.main())
