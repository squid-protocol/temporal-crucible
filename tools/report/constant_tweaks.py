#!/usr/bin/env python3
"""What share of code edits only change numeric constants (parameter tuning)? A hunk is a constant tweak when its removed and added lines are identical after every numeric literal is replaced by N
and whitespace is ignored, and the raw lines differ. Reported per hunk and per commit (a commit counts when it has at least one hunk and ALL its code hunks are tweaks).
    python tools/report/constant_tweaks.py REPO LANG [--since-first-parent]"""
import re
import subprocess
import sys
sys.path.insert(0, __import__("pathlib").Path(__file__).parent.as_posix())
import evolution_report as ER  # noqa: E402

NUM = re.compile(r"(?<![\w.])(?:0[xX][0-9a-fA-F]+|\d+\.?\d*(?:[eEdD][+-]?\d+)?|\.\d+(?:[eEdD][+-]?\d+)?)(?:_\w+|[fFlLuU]*)(?![\w])")


def norm(lines):
    return re.sub(r"\s+", "", NUM.sub("N", "\n".join(lines)))


def main():
    repo, lang = sys.argv[1], sys.argv[2]
    exts = ER.EXTS[lang]
    cm = ER.COMMENT[lang]
    proc = subprocess.Popen(["git", "-c", "core.quotepath=off", "-C", repo, "log", "--no-merges", "-p", "-U0", "--no-color", "--format=\x1dC %H", "--", *[f"*{e}" for e in exts]], stdout=subprocess.PIPE, text=True, errors="replace")
    hunks = tweaks = 0
    commits = commits_all_tweak = commits_any = 0
    cur_rem, cur_add, in_hunk = [], [], False
    state = {"h": 0, "t": 0}

    def flush():
        if not in_hunk or not (cur_rem or cur_add):
            return
        rem = [l for l in cur_rem if not cm.match(l)]
        add = [l for l in cur_add if not cm.match(l)]
        if not rem and not add:
            return
        state["h"] += 1
        if rem and add and "\n".join(rem) != "\n".join(add) and norm(rem) == norm(add):
            state["t"] += 1

    sha_open = False
    for line in proc.stdout:
        if line.startswith("\x1dC "):
            flush()
            if sha_open and state["h"]:
                commits += 1
                commits_all_tweak += state["h"] == state["t"]
                commits_any += state["t"] > 0
            hunks += state["h"]; tweaks += state["t"]
            state["h"] = state["t"] = 0
            cur_rem, cur_add, in_hunk, sha_open = [], [], False, True
        elif line.startswith("@@"):
            flush()
            cur_rem, cur_add, in_hunk = [], [], True
        elif in_hunk and line.startswith("-") and not line.startswith("---"):
            cur_rem.append(line[1:].rstrip("\n"))
        elif in_hunk and line.startswith("+") and not line.startswith("+++"):
            cur_add.append(line[1:].rstrip("\n"))
        elif line.startswith("diff --git"):
            flush()
            cur_rem, cur_add, in_hunk = [], [], False
    flush()
    if sha_open and state["h"]:
        commits += 1
        commits_all_tweak += state["h"] == state["t"]
        commits_any += state["t"] > 0
    hunks += state["h"]; tweaks += state["t"]
    proc.stdout.close(); proc.wait()
    print(f"{repo.rstrip('/').split('/')[-1]:10s} code hunks {hunks:8,}  constant-only {tweaks / max(hunks, 1) * 100:5.1f}%   commits with code {commits:6,}  ALL hunks constant-only {commits_all_tweak / max(commits, 1) * 100:5.1f}%  any {commits_any / max(commits, 1) * 100:5.1f}%")


if __name__ == "__main__":
    main()
