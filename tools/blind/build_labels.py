"""Label builder for a blinded study (blinding_spec.md, build phase A).

    python tools/blind/build_labels.py --manifest DIR/manifest.json --repo NAME --labels-dir LABELS
            [--pub keys/blind_pub.pem] [--k 20] [--replace]

Label table in (held in memory), and out into LABELS/:

    NAME.enc                  the true label table, encrypted to the public key (crypt.py)
    NAME.scrambled.json       k copies permuted within the LOC band only (scramble.py, [r3]), only if the 2%
                              rule releases them. No option writes directory-preserving copies.
    NAME.marginals.json       per outcome: files, positive files, qualifying commits, largest commit's share,
                              ambiguous commits -- nothing that names a file
    NAME.scramble_report.json the band-only cell report (file table only) and the release decision (DECISIONS.md 9 says what each output can and cannot reveal)

There is no option, flag or code path that writes plaintext labels. The builder refuses to run if a
plaintext label file for the same repo sits in LABELS (see plaintext_label_files).

Phase A reads the tables from a control repository's manifest.json (`table_from_manifest`); the stored tables
will supply the same shapes through `build()` later. The file table is the snapshot's unit files (path at the
snapshot, loc at the snapshot); the label table has one outcome, "HP", whose positives are the snapshot unit
files touched by commits with `counted: true`; commits with `counted: null` are left out and counted in the
marginals as ambiguous.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import scramble  # noqa: E402
import seal as sealmod  # noqa: E402


def load_crypt():
    """tools/blind/crypt.py under the module name `blind_crypt` (Python 3.12 still has a stdlib `crypt`, so a
    plain `import crypt` could pick up the wrong module)."""
    name = "blind_crypt"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, "crypt.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


crypt = load_crypt()

REPO_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$")
OUTPUT_SUFFIXES = (".enc", ".scrambled.json", ".marginals.json", ".scramble_report.json")
LABEL_SCHEMA = 1


class BuildError(Exception):
    pass


# ------------------------------------------------------------------------------------------------- inputs
def _require(obj, key, where):
    if not isinstance(obj, dict) or key not in obj:
        raise BuildError(f"manifest lacks the field {where}{key}; refusing to build labels from it")
    return obj[key]


def table_from_manifest(manifest):
    """(file_table, label_table) from a control repository's manifest, any schema >= 2 that carries the fields
    read here (DECISIONS.md 23): files[].is_unit, files[].path_at_snapshot, files[].properties.snapshot.loc
    (for unit files present at the snapshot), expected_labels[].counted and expected_labels[].positives[]
    .path_at_snapshot. A missing field is refused by name. In memory only. The schema number is carried in
    the label table as `source_schema` and written to the marginals."""
    schema = manifest.get("schema_version") if isinstance(manifest, dict) else None
    if not isinstance(schema, int) or schema < 2:
        raise BuildError(f"manifest schema {schema!r}; this reads schema 2 or later")
    for i, f in enumerate(_require(manifest, "files", "")):
        _require(f, "is_unit", f"files[{i}].")
        _require(f, "path_at_snapshot", f"files[{i}].")
        if f["is_unit"] and f["path_at_snapshot"]:
            snap = _require(_require(f, "properties", f"files[{i}]."), "snapshot", f"files[{i}].properties.")
            if snap is not None:
                _require(snap, "loc", f"files[{i}].properties.snapshot.")
    for i, e in enumerate(_require(manifest, "expected_labels", "")):
        _require(e, "counted", f"expected_labels[{i}].")
        if e["counted"] is True:
            for j, p in enumerate(_require(e, "positives", f"expected_labels[{i}].")):
                _require(p, "path_at_snapshot", f"expected_labels[{i}].positives[{j}].")
    file_table = []
    for f in manifest["files"]:
        snap = (f.get("properties") or {}).get("snapshot")
        if f.get("is_unit") and f.get("path_at_snapshot") and snap:
            file_table.append({"path": f["path_at_snapshot"], "loc": int(snap["loc"])})
    file_table.sort(key=lambda r: r["path"])
    counted = [e for e in manifest["expected_labels"] if e["counted"] is True]
    ambiguous = sum(1 for e in manifest["expected_labels"] if e["counted"] is None)
    positives = sorted({p["path_at_snapshot"] for e in counted for p in e["positives"]})
    largest = max((len({p["path_at_snapshot"] for p in e["positives"]}) for e in counted), default=0)
    label_table = {
        "schema": LABEL_SCHEMA,
        "source_schema": schema,
        "rows": [{"outcome": "HP", "path": p} for p in positives],
        "outcomes": {"HP": {"qualifying_commits": len(counted),
                            "largest_commit_share": (largest / len(positives)) if positives else 0.0,
                            "ambiguous_commits": ambiguous}},
    }
    return file_table, label_table


# ------------------------------------------------------------------------------------------------- guards
def plaintext_label_files(labels_dir, repo):
    """Entries in labels_dir that look like a plaintext label file for `repo`: the name `repo` itself, any
    `repo.*` that is not one of the builder's four outputs, and `repo_labels*` / `repo-labels*` /
    `repo_outcomes*` / `repo-outcomes*`. Repo names cannot contain '.', so `repo.` names belong to this repo."""
    if not os.path.isdir(labels_dir):
        return []
    own = {repo + s for s in OUTPUT_SUFFIXES}
    hits = []
    for name in sorted(os.listdir(labels_dir)):
        if name in own:
            continue
        low = name.lower()
        rl = repo.lower()
        if (low == rl or low.startswith(rl + ".")
                or any(low.startswith(rl + sep + w) for sep in "_-" for w in ("label", "outcome", "positive"))):
            hits.append(name)
    return hits


def _check_tables(repo, file_table, label_table):
    if not REPO_NAME.match(repo):
        raise BuildError("repo name must match [A-Za-z0-9][A-Za-z0-9_-]* (no '.')")
    paths = [r["path"] for r in file_table]
    if len(set(paths)) != len(paths) or not paths:
        raise BuildError("file table is empty or has duplicate paths")
    known = set(paths)
    outcomes = label_table.get("outcomes") or {}
    if not outcomes:
        raise BuildError("label table names no outcome")
    bad = sum(1 for row in label_table["rows"] if row["path"] not in known or row["outcome"] not in outcomes)
    if bad:
        raise BuildError(f"{bad} label row(s) name a path outside the file table or an undeclared outcome")
    if label_table.get("scrambled"):
        raise BuildError("refusing to encrypt a table marked scrambled as true labels")


def _write(path, data: bytes):
    sealmod.write_atomic(path, data)


def _dump(obj) -> bytes:
    return (json.dumps(obj, indent=1, sort_keys=True) + "\n").encode("ascii")


# ------------------------------------------------------------------------------------------------- build
def build(repo, file_table, label_table, labels_dir, public_key_path=crypt.DEFAULT_PUBLIC_KEY,
          k=scramble.DEFAULT_K, replace=False):
    """Write the four outputs. Returns the public summary (what was written to the report and marginals);
    nothing returned or printed names a positive file."""
    _check_tables(repo, file_table, label_table)
    if not os.path.isdir(labels_dir):
        os.makedirs(labels_dir)
    found = plaintext_label_files(labels_dir, repo)
    if found:
        raise BuildError(f"refusing to run: {len(found)} file(s) in {labels_dir} look like plaintext labels for "
                         f"{repo} ({', '.join(found)}); remove them first")
    targets = [os.path.join(labels_dir, repo + s) for s in OUTPUT_SUFFIXES]
    if not replace and any(os.path.exists(t) for t in targets):
        raise BuildError(f"outputs for {repo} already exist in {labels_dir}; pass --replace to rebuild")
    if k < 2:
        raise BuildError("k must be at least 2")
    pub = crypt.load_public_key(public_key_path)

    report = {"repo": repo, "cell_rule": scramble.CELL_RULE, "k": k,
              "cells": scramble.cell_report(scramble.released_cells(file_table)), "outcomes": {}}
    marginals = {"repo": repo, "n_files": len(file_table), "outcomes": {},
                 "source_manifest_schema": label_table.get("source_schema")}
    copies_by_outcome = {}
    released = True
    for name in sorted(label_table["outcomes"]):
        pos = [row["path"] for row in label_table["rows"] if row["outcome"] == name]
        copies, part, _measures = scramble.scramble_outcome(file_table, pos, k)
        report["outcomes"][name] = part
        meta = label_table["outcomes"][name]
        marginals["outcomes"][name] = {"n_positive_files": len(pos),
                                       "qualifying_commits": meta.get("qualifying_commits"),
                                       "largest_commit_share": meta.get("largest_commit_share"),
                                       "ambiguous_commits": meta.get("ambiguous_commits")}
        if copies is None:
            released = False
        copies_by_outcome[name] = copies
    report["released"] = released
    if not released:
        report["reason"] = ("scrambles withheld: " + "; ".join(
            f"{n}: {p['reason']}" for n, p in report["outcomes"].items() if not p["released"]))

    enc = crypt.encrypt_table(dict(label_table, repo=repo), pub, repo)
    _write(targets[0], enc)
    if not released and os.path.exists(targets[1]):
        os.remove(targets[1])             # a rebuild that withholds must not leave older copies behind
    if released:
        copies_out = []
        for i in range(k):
            rows = sorted(({"outcome": n, "path": p} for n in copies_by_outcome for p in copies_by_outcome[n][i]),
                          key=lambda r: (r["outcome"], r["path"]))
            copies_out.append({"scrambled": True, "schema": LABEL_SCHEMA, "repo": repo, "copy": i,
                               "rows": rows, "outcomes": label_table["outcomes"]})
        _write(targets[1], _dump({"scrambled": True, "format": "tc-blind-scrambled", "version": 1,
                                  "repo": repo, "k": k, "cell_rule": scramble.CELL_RULE,
                                  "copies": copies_out}))
    _write(targets[2], _dump(marginals))
    _write(targets[3], _dump(report))
    return {"report": report, "marginals": marginals}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--manifest", required=True, help="a control repository's manifest.json (phase A input)")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--labels-dir", required=True)
    ap.add_argument("--pub", default=crypt.DEFAULT_PUBLIC_KEY)
    ap.add_argument("--k", type=int, default=scramble.DEFAULT_K)
    ap.add_argument("--replace", action="store_true", help="rebuild outputs that already exist")
    a = ap.parse_args(argv)
    labels_dir = os.path.abspath(a.labels_dir)
    man = os.path.abspath(a.manifest)
    if os.path.commonpath([man, labels_dir]) == labels_dir:
        print("refusing to run: the input (which holds plaintext labels) is inside the labels directory",
              file=sys.stderr)
        return 2
    with open(man) as fh:
        file_table, label_table = table_from_manifest(json.load(fh))
    try:
        out = build(a.repo, file_table, label_table, labels_dir, a.pub, a.k, a.replace)
    except (BuildError, crypt.BlindCryptoError) as exc:
        print(f"refusing to run: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {a.repo}.enc, {a.repo}.marginals.json, {a.repo}.scramble_report.json"
          + (f", {a.repo}.scrambled.json ({a.k} copies)" if out["report"]["released"]
             else " -- scrambles NOT released, see the report")
          + f" in {labels_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
