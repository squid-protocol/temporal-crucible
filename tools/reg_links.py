#!/usr/bin/env python3
"""REG: resolve XC regression events to the commit they repair (docs/reg_hypotheses.md). Labels only, no predictors.

    python tools/reg_links.py --repo curl     -> events/curl_reg_links.json
"""
import argparse, json, pathlib, re, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import POOL_DIR, REPO_ROOT  # noqa: E402

def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout

ap = argparse.ArgumentParser(); ap.add_argument("--repo", required=True); a = ap.parse_args()
repo = POOL_DIR / a.repo
links, skipped = [], {"regression word only": 0, "unresolved": 0}
for e in json.loads((REPO_ROOT / "events" / f"{a.repo}_xc.json").read_text())["events"]:
    if e["class"] != "regression":
        continue
    target = None
    if e["why"].startswith("references "):
        target = _git(repo, "rev-parse", "-q", "--verify", e["why"].split()[1] + "^{commit}").strip()
        how = "sha-reference"
    elif e["why"] == "revert":
        m = re.search(r"This reverts commit ([0-9a-f]{7,40})", _git(repo, "show", "-s", "--format=%B", e["sha"]))
        if m:
            target = _git(repo, "rev-parse", "-q", "--verify", m.group(1) + "^{commit}").strip()
        how = "revert"
    else:
        skipped["regression word only"] += 1
        continue
    if not target:
        skipped["unresolved"] += 1
        continue
    tsub = _git(repo, "show", "-s", "--format=%ct%x1f%s", target).strip().split("\x1f", 1)
    links.append({"fix": e["sha"], "fix_ct": e["ct"], "fix_subject": e["subject"], "how": how,
                  "inducing": target, "inducing_ct": int(tsub[0]), "inducing_subject": tsub[1] if len(tsub) > 1 else ""})
(REPO_ROOT / "events" / f"{a.repo}_reg_links.json").write_text(json.dumps({"repo": a.repo, "skipped": skipped, "links": links}, indent=1))
print(a.repo, len(links), "links;", skipped)
