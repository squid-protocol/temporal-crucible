#!/usr/bin/env python3
"""Generate a control repository: a synthetic git repository whose truth is planted and written down.

    python tools/control_repo/generate.py --out DIR --seed N [--language python|c] [--files 400]
            [--effect NAME=BETA ...] [--mutation NAME ...] [--years 4] [--profile small|default]
    python tools/control_repo/generate.py --list-mutations

Writes DIR/repo/ (a normal, full, non-bare git repository, branch `main`, working tree checked out) and
DIR/manifest.json (the truth; see manifest.py). See README.md for what the repository contains.

How it works: `history.plan` builds the whole history in memory (files, logical commits, planted properties,
realised truth). `mutations.MutationSet.delivery` decides how each logical commit reaches `main` (directly, as
a branch merged by a merge commit, or squashed). `write_repo` writes those commits with one `git fast-import`
process, asking it for each commit's hash as it goes (`get-mark`), so that later messages ("This reverts commit
<hash>", "Fixes: <hash>") can name earlier commits. Every git call runs in a fixed, private environment
(`git_env`): fixed identity and dates come from the plan, TZ=UTC, GIT_CONFIG_NOSYSTEM=1, a private HOME and XDG
config directory, no inherited GIT_* variables, and `-c gc.auto=0`. Same arguments -> same commit hashes.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import history as hi  # noqa: E402
import manifest as mf  # noqa: E402
import mutations as mm  # noqa: E402

PLACEHOLDER = re.compile(r"\{\{H(12|40):(\w+)\}\}")


# ------------------------------------------------------------------------------------------------ git
def git_env(home: str, ceiling: str) -> dict:
    """The complete environment of every git call: nothing inherited except PATH. `ceiling` stops git from
    ever discovering a repository above the generated one (GIT_CEILING_DIRECTORIES)."""
    return {
        "GIT_CEILING_DIRECTORIES": ceiling,
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": home,
        "XDG_CONFIG_HOME": os.path.join(home, ".config"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.path.join(home, ".gitconfig"),
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "TZ": "UTC",
        "LC_ALL": "C",
        "LANG": "C",
        # identity for any call that would need one; every commit sets its own author and committer explicitly
        "GIT_AUTHOR_NAME": "Control Generator", "GIT_AUTHOR_EMAIL": "generator@example.invalid",
        "GIT_COMMITTER_NAME": "Control Generator", "GIT_COMMITTER_EMAIL": "generator@example.invalid",
        "GIT_AUTHOR_DATE": f"{hi.T0} +0000", "GIT_COMMITTER_DATE": f"{hi.T0} +0000",
    }


def git(args, cwd, env, **kw):
    """Run one git command with gc disabled, in `cwd`, failing loudly."""
    return subprocess.run(["git", "-c", "gc.auto=0", "-c", "maintenance.auto=false", *args], cwd=cwd, env=env,
                          check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)


def split_ident(ident: str):
    name, email = ident.rsplit(" <", 1)
    return name, email.rstrip(">")


class FastImport:
    """One `git fast-import` process. `commit` writes a commit and returns its hash (via `get-mark`)."""

    def __init__(self, repo, env, errlog):
        self.rfd, wfd = os.pipe()
        self.err = open(errlog, "wb")
        self.proc = subprocess.Popen(
            ["git", "-c", "gc.auto=0", "-c", "maintenance.auto=false", "fast-import", "--quiet", "--done",
             f"--cat-blob-fd={wfd}"],
            cwd=repo, env=env, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self.err, pass_fds=(wfd,))
        os.close(wfd)
        self.reader = os.fdopen(self.rfd, "rb")
        self.mark = 0
        self.marks = {}                               # hash -> mark

    def _data(self, payload: bytes) -> bytes:
        return b"data %d\n" % len(payload) + payload + b"\n"

    def commit(self, ref, author, committer, when, message, parents, changes) -> str:
        """`changes`: list of (path, text or None). Returns the new commit's 40-hex hash."""
        self.mark += 1
        an, ae = split_ident(author)
        cn, ce = split_ident(committer)
        out = [b"commit %s\n" % ref.encode(), b"mark :%d\n" % self.mark,
               b"author %s <%s> %d +0000\n" % (an.encode(), ae.encode(), when),
               b"committer %s <%s> %d +0000\n" % (cn.encode(), ce.encode(), when),
               self._data(message.encode("utf-8"))]
        if parents:                                   # parents by mark: the pack is not readable until done
            out.append(b"from :%d\n" % self.marks[parents[0]])
            for p in parents[1:]:
                out.append(b"merge :%d\n" % self.marks[p])
        for path, text in changes:
            if text is None:
                out.append(b"D %s\n" % path.encode())
            else:
                out.append(b"M 100644 inline %s\n" % path.encode())
                out.append(self._data(text.encode("utf-8")))
        out.append(b"\n")
        out.append(b"get-mark :%d\n" % self.mark)
        self.proc.stdin.write(b"".join(out))
        self.proc.stdin.flush()
        line = self.reader.readline().decode().strip()
        if not re.fullmatch(r"[0-9a-f]{40}", line):
            self.err.flush()
            with open(self.err.name, encoding="utf-8", errors="replace") as fh:
                detail = fh.read()[-2000:]
            raise RuntimeError(f"fast-import did not return a hash for mark {self.mark}: {line!r}\n{detail}")
        self.marks[line] = self.mark
        return line

    def close(self):
        self.proc.stdin.write(b"done\n")
        self.proc.stdin.close()
        rc = self.proc.wait()
        self.reader.close()
        self.err.close()
        if rc != 0:
            raise RuntimeError(f"git fast-import failed (exit {rc}); see {self.err.name}")


# ------------------------------------------------------------------------------------------ the writer
def resolve(message: str, hash_of: dict) -> str:
    """Fill {{H40:lid}} / {{H12:lid}} placeholders with the delivered hash of an earlier logical commit."""
    def sub(m):
        h = hash_of.get(m.group(2))
        if h is None:
            raise RuntimeError(f"message names commit {m.group(2)} before it was written")
        return h[:int(m.group(1))]
    return PLACEHOLDER.sub(sub, message)


def net_changes(before: dict, after: dict):
    """Paths whose content differs between two trees (path -> text), as (path, text or None), sorted."""
    out = []
    for p in sorted(set(before) | set(after)):
        if before.get(p) != after.get(p):
            out.append((p, after.get(p)))
    return out


def write_repo(plan, units, repo, workdir):
    """Write the delivery `units` into a new repository at `repo`. Returns the realised commit records, in the
    order written (chronological; a merge's branch commits precede the merge)."""
    cfg = plan.cfg
    mut = plan.mutation_set
    home = os.path.join(workdir, "home")
    os.makedirs(os.path.join(home, ".config"), exist_ok=True)
    env = git_env(home, os.path.dirname(os.path.abspath(repo)))
    os.makedirs(repo)
    git(["-c", "init.defaultBranch=main", "init", "-q", "."], repo, env)
    git(["config", "gc.auto", "0"], repo, env)
    fi = FastImport(repo, env, os.path.join(workdir, "fast-import.err"))
    entries = {e.lid: e for e in plan.entries}
    hash_of = {}                     # logical id -> hash of the commit that carries it
    realised = []
    main_tip, main_tree = None, {}
    n_merge = 0

    def record(kind, h, lids, when, author, message, changes, parents, extra=None):
        fid_of = {}
        for lid in lids:
            fid_of.update(entries[lid].path_fid)
        paths_by_id = {}
        for path, text in changes:
            fid = fid_of[path]
            if text is not None or fid not in paths_by_id:     # a rename: keep the new path
                paths_by_id[fid] = path
        r = {"hash": h, "kind": kind, "lids": list(lids), "time": when, "time_iso": mf.iso(when),
             "author": author, "parents": list(parents), "message": message,
             "paths": [p for p, _t in changes], "file_ids": sorted(paths_by_id), "paths_by_id": paths_by_id}
        r.update(extra or {})
        realised.append(r)
        return r

    for unit in units:
        group = unit["entries"]
        if unit["kind"] == "direct":
            e = group[0]
            msg = resolve(e.message, hash_of)
            changes = sorted(e.changes.items())
            parents = [main_tip] if main_tip else []
            h = fi.commit("refs/heads/main", e.author, e.author, e.time, msg, parents, changes)
            for p, t in changes:
                if t is None:
                    main_tree.pop(p, None)
                else:
                    main_tree[p] = t
            main_tip = h
            hash_of[e.lid] = h
            record("direct", h, [e.lid], e.time, e.author, msg, changes, parents)
        elif unit["kind"] == "squash":
            tree = dict(main_tree)
            for e in group:
                for p, t in e.changes.items():
                    if t is None:
                        tree.pop(p, None)
                    else:
                        tree[p] = t
            changes = net_changes(main_tree, tree)
            msgs = [resolve(e.message, hash_of) for e in group]
            msg = msgs[0] if len(msgs) == 1 else "\n\n".join(
                [msgs[0].split("\n")[0]] + [f"* {m}" for m in msgs])
            when = group[-1].time + 1
            author = group[0].author
            parents = [main_tip]
            h = fi.commit("refs/heads/main", author, author, when, msg, parents, changes)
            main_tip, main_tree = h, tree
            for e in group:
                hash_of[e.lid] = h
            record("squash", h, [e.lid for e in group], when, author, msg, changes, parents)
        else:                                              # merge: a branch off main, then a merge commit
            n_merge += 1
            tip, tree = main_tip, dict(main_tree)
            side_records = []
            for e in group:
                msg = resolve(e.message, hash_of)
                changes = sorted(e.changes.items())
                h = fi.commit("refs/control/branch", e.author, e.author, e.time, msg, [tip], changes)
                for p, t in changes:
                    if t is None:
                        tree.pop(p, None)
                    else:
                        tree[p] = t
                side_records.append(record("side", h, [e.lid], e.time, e.author, msg, changes, [tip]))
                tip = h
                hash_of[e.lid] = h
            changes = net_changes(main_tree, tree)
            author = mut.merge_author(cfg, n_merge)
            when = group[-1].time + 1
            topic = "import-upstream" if unit.get("huge") else f"topic-{n_merge}"
            msg = f"Merge branch '{topic}'"
            parents = [main_tip, tip]
            h = fi.commit("refs/heads/main", author, author, when, msg, parents, changes)
            main_tip, main_tree = h, tree
            record("merge", h, [e.lid for e in group], when, author, msg, changes, parents,
                   {"brought": [e.lid for e in group], "huge": bool(unit.get("huge"))})
            for s in side_records:
                s["merge"] = h
    fi.close()
    if n_merge:
        git(["update-ref", "-d", "refs/control/branch"], repo, env)
    git(["reset", "-q", "--hard", "main"], repo, env)
    # cross-check the recorded parents against git itself
    out = git(["rev-list", "--parents", "main"], repo, env).stdout.decode().split("\n")
    parents = {}
    for line in out:
        if line.strip():
            h, *ps = line.split()
            parents[h] = ps
    for r in realised:
        if parents.get(r["hash"]) != r["parents"]:
            raise RuntimeError(f"commit {r['hash']}: git has parents {parents.get(r['hash'])}, "
                               f"recorded {r['parents']}")
    return realised, env


def first_parent_commit_of(realised, lid):
    """The first-parent (non-branch) commit that carries logical commit `lid`."""
    for r in realised:
        if r["kind"] != "side" and lid in r["lids"]:
            return r
    raise KeyError(lid)


# ---------------------------------------------------------------------------------------------- driver
def parse_effects(items):
    out = {}
    for it in items or []:
        if "=" not in it:
            raise SystemExit(f"--effect wants NAME=BETA, got {it!r}")
        k, v = it.split("=", 1)
        out[k.strip()] = float(v)
    return out


def make_config(seed, language="python", files=None, effects=None, mutations=(), years=4.0, profile="default"):
    return hi.Config(seed=seed, language=language, files=files, years=years, profile=profile,
                     effects=dict(effects or {}), mutations=tuple(mutations or ()))


def build_plan(cfg):
    """The in-memory history and its delivery, without writing git. Returns (plan, units)."""
    mut = mm.MutationSet(cfg.mutations)
    p = hi.plan(cfg, mut)
    units = mut.delivery(cfg, p.entries, p.snap_lid, p.prior_lid)
    return p, units


HERE_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate(out_dir, cfg) -> dict:
    """Generate DIR/repo and DIR/manifest.json. Returns the manifest."""
    out_dir = os.path.abspath(out_dir)
    if os.path.commonpath([out_dir, HERE_REPO]) == HERE_REPO:
        raise SystemExit(f"--out {out_dir} is inside the repository that holds the generator; use a directory "
                         f"outside it")
    repo = os.path.join(out_dir, "repo")
    if os.path.exists(repo) and os.listdir(repo):
        raise SystemExit(f"{repo} exists and is not empty; refusing to write over it")
    if os.path.exists(repo):
        os.rmdir(repo)
    os.makedirs(out_dir, exist_ok=True)
    p, units = build_plan(cfg)
    work = tempfile.mkdtemp(prefix=".gen-", dir=out_dir)
    try:
        realised, _env = write_repo(p, units, repo, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    snap = first_parent_commit_of(realised, p.snap_lid)
    prior = first_parent_commit_of(realised, p.prior_lid)
    m = mf.build(p, realised, snap["hash"], prior["hash"])
    mf.write(os.path.join(out_dir, "manifest.json"), m)
    return m


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--language", choices=["python", "c"], default="python")
    ap.add_argument("--files", type=int, default=None, help="number of files (default: the profile's)")
    ap.add_argument("--effect", action="append", default=[], metavar="NAME=BETA",
                    help=f"planted effect; names: {', '.join(hi.EFFECT_NAMES)} (C also: "
                         f"{', '.join(hi.C_EFFECT_NAMES)})")
    ap.add_argument("--mutation", action="append", default=[], metavar="NAME")
    ap.add_argument("--years", type=float, default=4.0)
    ap.add_argument("--profile", choices=sorted(hi.PROFILES), default="default")
    ap.add_argument("--list-mutations", action="store_true")
    a = ap.parse_args(argv)
    if a.list_mutations:
        print(mm.list_mutations())
        return 0
    if a.out is None or a.seed is None:
        ap.error("--out and --seed are required")
    try:
        cfg = make_config(a.seed, a.language, a.files, parse_effects(a.effect), a.mutation, a.years, a.profile)
        mm.MutationSet(cfg.mutations)                 # unknown or conflicting names fail here, as usage errors
    except ValueError as exc:
        ap.error(str(exc))
    t0 = time.time()
    m = generate(a.out, cfg)
    print(f"wrote {os.path.join(os.path.abspath(a.out), 'repo')} and manifest.json: "
          f"{m['counts']['unit_files_at_snapshot']} unit files at the snapshot, "
          f"{m['counts']['realised_commits']} commits, snapshot {m['points']['snapshot']['hash'][:12]}, "
          f"{time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
