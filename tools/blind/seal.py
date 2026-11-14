"""The seal: SHA-256 hashes of everything the unblinding and gate jobs depend on (blinding_spec.md, step 1).

    python tools/blind/seal.py --study STUDY_DIR        write STUDY_DIR/seal.json (refuses to overwrite)
    python tools/blind/seal.py --study STUDY_DIR --verify

seal.json, version 1 (DECISIONS.md 11):

    {"seal_version": 1, "algorithm": "sha256", "created": ISO time,
     "code":  {"tools/blind/<file>.py": hex, ...,      every .py file in tools/blind/ (scorer registry,
                                                       statistics, label builder, crypto, scramble, jobs),
               "<each path in study.json's sealed_code>": hex}   [review finding 2] every other module the
                                                       study's scorer and gates load, listed explicitly,
                                                       paths relative to the repository root
     "study": {"study.json": hex,                      the specification: scorer, parameters, declared
                                                       outputs, gates, key fingerprint
               "<each path in study.json's sealed_documents>": hex,   definitions, power statement, review
                                                       record, ...
               "scans/<repo>.json": hex, ...           every input table (scan)
               "labels/<repo>.enc": hex, ...}}         every encrypted label file

Each hash is SHA-256 over the file's bytes. The seal hash is SHA-256 over seal.json's bytes. Verification
recomputes every listed hash and also fails if a file is missing, or if tools/blind/, scans/ or labels/ holds
a .py / .json / .enc file the seal does not list (an added input or module is a change too).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import secrets
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SEAL_VERSION = 1


class SealError(Exception):
    pass


def write_atomic(path, data: bytes):
    """Write `data` to a temporary name in the same directory and rename it over `path` (review finding 4).
    The temporary file holds exactly what the final file will; it is removed if anything fails."""
    d, base = os.path.split(os.path.abspath(path))
    tmp = os.path.join(d, f".{base}.tmp-{os.getpid()}-{secrets.token_hex(4)}")
    try:
        with open(tmp, "xb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _code_files(study, code_dir=HERE):
    """The job's own code (every .py file in its directory, keyed tools/blind/<name>) and every path listed in
    study.json's `sealed_code` (relative to the repository root)."""
    out = {f"tools/blind/{n}": os.path.join(code_dir, n) for n in sorted(os.listdir(code_dir)) if n.endswith(".py")}
    root = os.path.dirname(os.path.dirname(code_dir))
    for rel in study.get("sealed_code", []):
        norm = os.path.normpath(rel)
        if os.path.isabs(norm) or norm.startswith(".."):
            raise SealError(f"sealed code path {rel!r} must be relative to the repository root, inside it")
        out[norm] = os.path.join(root, norm)
    return out


def _study_files(study_dir, study):
    out = {"study.json": os.path.join(study_dir, "study.json")}
    for doc in study.get("sealed_documents", []):
        norm = os.path.normpath(doc)
        if os.path.isabs(norm) or norm.startswith(".."):
            raise SealError(f"sealed document {doc!r} must be a path inside the study directory")
        out[norm] = os.path.join(study_dir, norm)
    for sub, suffix in (("scans", ".json"), ("labels", ".enc")):
        d = os.path.join(study_dir, sub)
        if os.path.isdir(d):
            for n in sorted(os.listdir(d)):
                if n.endswith(suffix):
                    out[f"{sub}/{n}"] = os.path.join(d, n)
    for repo in study["repos"]:
        for need in (f"scans/{repo}.json", f"labels/{repo}.enc"):
            if need not in out:
                raise SealError(f"study names repo {repo!r} but {need} is missing")
    return out


def load_study(study_dir):
    with open(os.path.join(study_dir, "study.json")) as fh:
        return json.load(fh)


def make_seal(study_dir, now=None):
    path = os.path.join(study_dir, "seal.json")
    if os.path.exists(path):
        raise SealError(f"{path} exists; a study is sealed once")
    study = load_study(study_dir)
    seal = {"seal_version": SEAL_VERSION, "algorithm": "sha256",
            "created": (now or datetime.datetime.now().astimezone()).isoformat(timespec="seconds"),
            "code": {k: sha256_file(p) for k, p in _code_files(study).items()},
            "study": {k: sha256_file(p) for k, p in _study_files(study_dir, study).items()}}
    data = (json.dumps(seal, indent=1, sort_keys=True) + "\n").encode("ascii")
    write_atomic(path, data)
    return hashlib.sha256(data).hexdigest()


def verify_seal(study_dir):
    """Returns the seal hash, or raises SealError naming the first mismatch (a path, never content)."""
    path = os.path.join(study_dir, "seal.json")
    if not os.path.exists(path):
        raise SealError("no seal.json: the study is not sealed")
    with open(path, "rb") as fh:
        data = fh.read()
    seal = json.loads(data)
    if seal.get("seal_version") != SEAL_VERSION or seal.get("algorithm") != "sha256":
        raise SealError("unsupported seal version or algorithm")
    study = load_study(study_dir)
    for part, current in (("code", _code_files(study)), ("study", _study_files(study_dir, study))):
        listed = seal.get(part) or {}
        extra = sorted(set(current) - set(listed))
        if extra:
            raise SealError(f"seal mismatch: {extra[0]} is present but not sealed")
        for rel in sorted(listed):
            p = current.get(rel)
            if p is None or not os.path.exists(p):
                raise SealError(f"seal mismatch: {rel} is sealed but missing")
            if sha256_file(p) != listed[rel]:
                raise SealError(f"seal mismatch: {rel} has changed since the seal")
    return hashlib.sha256(data).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--study", required=True)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args(argv)
    try:
        h = verify_seal(a.study) if a.verify else make_seal(a.study)
    except SealError as exc:
        print(f"seal: {exc}", file=sys.stderr)
        return 2
    print(f"seal {'verified' if a.verify else 'written'}: {h}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
