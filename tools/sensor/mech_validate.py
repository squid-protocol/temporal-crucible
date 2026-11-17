#!/usr/bin/env python3
"""Validate the mechanical-swap detector (mech_detect.py, the code `change_report.py` runs) against the sweep study's quarter-level ground truth.

    python tools/sensor/mech_validate.py REPO [REPO ...]       (venv with numpy; the study's event pickles and snapshots must exist)

Ground truth: tools/turn/sweeps.py `detect()` over the repository's function-edit events, per quarter: a migration (old call -> new call) is a sweep when the
call is removed / added in at least max(10, 1%) of the quarter's code-edited functions and the two co-occur. Under test: for every non-merge commit that
touches source files, the per-commit detector (a one-call-for-one-call line swap seen 5 or more times in the commit).

Reported per repository:
  precision  flagged (commit, swap) pairs that are a ground-truth migration of that commit's quarter
  purity     lines of flagged swaps that are a pure substitution (the old line with old->new equals the new line): the change really is mechanical
  recall     lines of ground-truth migrations (any commit, any repeat count) that sit in a commit where the detector flags that same swap (circular: the occurrences are found
             with the detector's own pairing); and the independent version, against the study's own function count per migration
  mechanical share of all changed source lines the detector would call mechanical (the study measures 4-44% of in-place edits at function level)"""
import bisect
import collections
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "turn"))
import mech_detect as MD  # noqa: E402
import sweep_audit as SA  # noqa: E402  (its module level only defines helpers and paths)

LOOSE = "--loose" in sys.argv
if LOOSE:
    sys.argv.remove("--loose")
COOC = "--cooc" in sys.argv
if COOC:
    sys.argv.remove("--cooc")
EXT = {"libgit2": (".c", ".h"), "redis": (".c", ".h"), "curl": (".c", ".h"), "libxml2": (".c", ".h"), "prometheus": (".go",), "ripgrep": (".rs",), "sphinx": (".py",)}
HUNK = re.compile(r"^@@ ")


def quarter_pairs(name):
    ev = SA.pickle.load(open(f"{SA.SP}/{SA.PKL[name]}", "rb"))[name]["events"]
    migr, _one, _ = SA.S.detect(ev)
    pairs = collections.defaultdict(set)
    size = {}
    for m in migr:
        pair = (SA.norm(m["old"]), SA.norm(m["new"]))
        pairs[m["s"]].add(pair)
        size[(m["s"], pair)] = max(size.get((m["s"], pair), 0), m["n"])  # the study's count of functions that removed the old call and added the new one
    return pairs, size


def commits(repo, exts, t0, t1):
    """Yield (sha, ct, hunks) for every non-merge commit in (t0, t1] with its source-file hunks as (path, removed, added)."""
    cmd = ["git", "-C", repo, "log", "--no-merges", "-p", "-U0", "--no-color", "--format=%x00%H%x1f%ct", f"--since={t0}", f"--until={t1}", "--"] + [f"*{e}" for e in exts]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, errors="replace")
    sha = ct = None
    hunks = []
    cur = None
    for line in proc.stdout:
        if line.startswith("\x00"):
            if sha is not None:
                yield sha, ct, hunks
            head = line[1:].rstrip("\n").split("\x1f")
            sha, ct, hunks, cur = head[0], int(head[1]), [], None
        elif line.startswith("+++ b/"):
            cur = line[6:].rstrip("\n")
        elif line.startswith("+++ /dev/null"):
            cur = None
        elif HUNK.match(line) and cur:
            hunks.append((cur, [], []))
        elif cur and hunks and line.startswith("+") and not line.startswith("+++"):
            hunks[-1][2].append(line[1:].rstrip("\n"))
        elif cur and hunks and line.startswith("-") and not line.startswith("---"):
            hunks[-1][1].append(line[1:].rstrip("\n"))
    if sha is not None:
        yield sha, ct, hunks


def run(name):
    repo = f"{SA.POOL}/{name}"
    sn = json.load(open(f"{SA.B}/scan_{name}/snapshots.json"))
    ct = [int(subprocess.run(["git", "-C", repo, "show", "-s", "--format=%ct", x["commit"]], capture_output=True, text=True).stdout.strip()) for x in sn]
    truth, size = quarter_pairs(name)
    seen = collections.Counter()  # (quarter, swap) -> occurrences in commits where the detector flags it
    seen_any = collections.Counter()  # (quarter, swap) -> occurrences at any repeat count, in any commit
    R = collections.Counter()
    flagged_examples = collections.Counter()
    for sha, t, hunks in commits(repo, EXT[name], ct[0], ct[-1]):
        s = bisect.bisect_left(ct, t) - 1
        if s < 0 or s >= len(ct) - 1:
            continue
        counts, big, lines = MD.swaps_cooc(hunks) if COOC else MD.swaps(hunks, loose=LOOSE)
        R["commits"] += 1
        changed = sum(len(r) + len(a) for _p, r, a in hunks)
        R["changed_lines"] += changed
        q = truth.get(s, set())
        # ground-truth swap occurrences in this commit (any repeat count): the lines a perfect per-commit view could see
        for pair, n in counts.items():
            if pair in q:
                seen_any[(s, pair)] += n
                R["truth_occurrences"] += n
                R["truth_lines"] += 2 * n
                if pair in big:
                    R["truth_caught_lines"] += 2 * n
        if big:
            R["flagged_commits"] += 1
            for pair, n in big.items():
                R["flagged_pairs"] += 1
                R["flagged_lines"] += 2 * n
                if pair in q:
                    R["flagged_pairs_in_truth"] += 1
                    seen[(s, pair)] += n
                else:
                    flagged_examples[(pair, name, sha[:10])] = n
            for pair, lx, ly in lines:
                R["flagged_occurrences"] += 1
                if MD.is_pure(lx, ly, *pair):
                    R["flagged_pure"] += 1
    # independent recall: of the functions the study says each migration touched, how many occurrences the per-commit detector flagged
    ratios = sorted(seen.get(k, 0) / v for k, v in size.items() if v)
    R["migrations"] = len(ratios)
    R["mig_missed"] = sum(1 for r in ratios if r == 0)
    R["mig_half"] = sum(1 for r in ratios if r >= 0.5)
    R["mig_90"] = sum(1 for r in ratios if r >= 0.9)
    missed = [k for k, v in size.items() if v and seen.get(k, 0) == 0]
    R["missed"] = len(missed)
    R["missed_spread"] = sum(1 for k in missed if seen_any.get(k, 0) >= 0.5 * size[k])  # the pairing sees at least half of it, below the 5-per-commit threshold
    R["missed_unseen"] = sum(1 for k in missed if seen_any.get(k, 0) < 0.5 * size[k])  # the pairing never sees most of it (multi-call lines, unequal hunks)
    R["study_functions"] = sum(size.values())
    R["flagged_in_migrations"] = sum(seen.values())
    return R, flagged_examples


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "n/a"


def main():
    names = sys.argv[1:]
    tot = collections.Counter()
    for name in names:
        R, ex = run(name)
        tot.update(R)
        print(f"{name}: {R['commits']} commits, {R['changed_lines']} changed source lines; study ground truth {sum(len(v) for v in quarter_pairs(name)[0].values())} migration pairs over its quarters")
        print(f"  detector flags {R['flagged_commits']} commits ({R['flagged_pairs']} swaps, {R['flagged_lines']} lines = {pct(R['flagged_lines'], R['changed_lines'])} of all changed lines)")
        print(f"  precision {pct(R['flagged_pairs_in_truth'], R['flagged_pairs'])} of flagged swaps are a ground-truth migration of that quarter; purity {pct(R['flagged_pure'], R['flagged_occurrences'])} of flagged lines are a pure substitution")
        print(f"  recall    {pct(R['truth_caught_lines'], R['truth_lines'])} of ground-truth migration lines sit in a commit where the same swap is flagged ({R['truth_occurrences']} occurrences in all) [circular: counted with the detector's own pairing; see below]")
        print(f"  recall vs the study's own counts: {R['migrations']} migrations; detector flagged at least half of the functions the study counts for {pct(R['mig_half'], R['migrations'])}, at least 90% for {pct(R['mig_90'], R['migrations'])}, nothing at all for {pct(R['mig_missed'], R['migrations'])} (flagged {R['flagged_in_migrations']} occurrences against {R['study_functions']} functions)")
        top = sorted(ex.items(), key=lambda kv: -kv[1])[:4]
        if top:
            print("  flagged but not a quarter sweep (largest): " + "; ".join(f"{p[0]} -> {p[1]} x{n} ({sha})" for ((p, _n, sha), n) in top))
    print(f"POOLED over {', '.join(names)}: precision {pct(tot['flagged_pairs_in_truth'], tot['flagged_pairs'])}, purity {pct(tot['flagged_pure'], tot['flagged_occurrences'])}, "
          f"mechanical share of changed lines {pct(tot['flagged_lines'], tot['changed_lines'])}; of {tot['migrations']} study migrations the detector flagged >=50% for {pct(tot['mig_half'], tot['migrations'])}, "
          f">=90% for {pct(tot['mig_90'], tot['migrations'])}, nothing for {pct(tot['mig_missed'], tot['migrations'])}; of the {tot['missed']} missed, {tot['missed_spread']} are visible to the pairing "
          f"but spread below 5 per commit and {tot['missed_unseen']} are mostly invisible to it")


if __name__ == "__main__":
    main()
