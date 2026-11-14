"""Tests of the blinding tools (tools/blind/), build phase A of docs/process/blinding_spec.md.

Every key here is a THROWAWAY key pair generated inside the test (pytest's tmp_path); the owner's private key
is never read or named. The only real key material read is the committed public key keys/blind_pub.pem, to
check that a table can be encrypted to it and that a throwaway key cannot open the result.

Labels never appear in test output: comparisons of label content go through digests, and the jobs' captured
output is checked for file paths.

Control repositories are generated under pytest's temporary directory with tools/control_repo/generate.py
(about 3 s each; eight default-profile repositories with --years 10). Runtime: see tools/blind/DECISIONS.md.
"""
from __future__ import annotations

import collections
import getpass
import hashlib
import math
import inspect
import json
import os
import random
import shutil
import statistics
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BLIND = ROOT / "tools" / "blind"
GENERATE = ROOT / "tools" / "control_repo" / "generate.py"
PUBLIC_KEY = ROOT / "keys" / "blind_pub.pem"
sys.path.insert(0, str(BLIND))

import build_labels  # noqa: E402
import jobcore  # noqa: E402
import registry  # noqa: E402
import scramble  # noqa: E402
import seal as sealmod  # noqa: E402
import score  # noqa: E402
import gates  # noqa: E402

crypt = build_labels.load_crypt()

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402

MEASURE = "branches"


# ------------------------------------------------------------------------------------------------- helpers
def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def throwaway_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def write_public(key, path):
    path.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,
                                                   serialization.PublicFormat.SubjectPublicKeyInfo))
    return path


def write_private_unencrypted(key, path):
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption()))
    return path


class Manifest(dict):
    """A manifest whose repr names nothing (pytest prints fixture values in tracebacks)."""
    def __repr__(self):
        return "<control-repository manifest>"


def generate(out, seed, *extra):
    subprocess.run([sys.executable, "-B", str(GENERATE), "--out", str(out), "--seed", str(seed), *extra],
                   check=True, capture_output=True)
    return Manifest(json.loads((out / "manifest.json").read_text()))


def truth_from_manifest(m):
    """Independent of build_labels: (scan rows with the measure, true positive paths)."""
    files = [{"path": f["path_at_snapshot"], "loc": f["properties"]["snapshot"]["loc"],
              "measures": {MEASURE: f["properties"]["snapshot"]["density"][MEASURE]}}
             for f in m["files"] if f["is_unit"] and f["path_at_snapshot"] and f["properties"]["snapshot"]]
    pos = sorted({p["path_at_snapshot"] for e in m["expected_labels"] if e["counted"] is True
                  for p in e["positives"]})
    return files, pos


def stat(files, pos):
    return registry.within_decile_rank_corr(files, pos, lambda r: r["measures"][MEASURE])[0]


def listing(d):
    return sorted(str(p.relative_to(d)) for p in Path(d).rglob("*") if p.is_file())


class WriteRecorder:
    """Records every open-for-writing (path only) while active, through an audit hook."""
    def __init__(self):
        self.active = False
        self.paths = []
        self.renames = []
        sys.addaudithook(self._hook)

    def _hook(self, event, args):
        if not self.active:
            return
        if event == "open":
            mode = args[1] if len(args) > 1 else None
            flags = args[2] if len(args) > 2 else None
            if (isinstance(mode, str) and any(c in mode for c in "wax+")) or \
                    (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)):
                self.paths.append(str(args[0]))
        elif event == "os.rename":
            self.renames.append((str(args[0]), str(args[1])))
        elif event in ("tempfile.mkstemp", "tempfile.mkdtemp", "os.mkdir", "os.remove"):
            self.paths.append(f"{event}:{args[0]}")


RECORDER = WriteRecorder()


# ------------------------------------------------------------------------------------------------- fixtures
R3_SEEDS = range(1, 9)


@pytest.fixture(scope="module")
def r3_repos(tmp_path_factory):
    """[r3] Eight default-profile control repositories, seeds 1-8, --years 10, planted branch-density effect
    (beta 1.0)."""
    out = {}
    for s in R3_SEEDS:
        out[s] = generate(tmp_path_factory.mktemp(f"r3seed{s}"), s, "--years", "10", "--effect", f"{MEASURE}=1.0")
    return out


@pytest.fixture(scope="module")
def planted(r3_repos):
    """Seed 1 of the r3 set."""
    return r3_repos[1]


@pytest.fixture(scope="module")
def key():
    return throwaway_key()


@pytest.fixture(scope="module")
def other_key():
    return throwaway_key()


def make_study(base, manifest, key, repo="ctl", tamper_table=None):
    """A sealed study directory for a control repository, labels built with a throwaway public key."""
    study = base / "study"
    (study / "scans").mkdir(parents=True)
    pub = write_public(key, base / "pub.pem")
    file_table, label_table = build_labels.table_from_manifest(manifest)
    if tamper_table:
        label_table = tamper_table(label_table)
    files, _pos = truth_from_manifest(manifest)
    (study / "scans" / f"{repo}.json").write_text(json.dumps({"repo": repo, "files": files}))
    build_labels.build(repo, file_table, label_table, str(study / "labels"), str(pub))
    (study / "spec.md").write_text("registration text\n")
    (study / "study.json").write_text(json.dumps({
        "study_id": "test-study", "repos": [repo], "key_fingerprint": crypt.fingerprint(key.public_key()),
        "scorer": {"name": "reference_within_decile_rank_corr", "params": {"outcome": "HP", "measure": MEASURE},
                   "outputs": [f"{repo}.rho", f"{repo}.n_files", f"{repo}.n_positive", f"{repo}.n_deciles_used"]},
        "gates": [{"name": "size", "gate": "reference_size_surrogate", "params": {"outcome": "HP"},
                   "outputs": [f"{repo}.size_rho"]},
                  {"name": "placebo", "gate": "reference_hash_placebo", "params": {"outcome": "HP"},
                   "outputs": [f"{repo}.placebo_rho"]},
                  {"name": "null_spread", "gate": "reference_null_spread",
                   "params": {"outcome": "HP", "measure": MEASURE, "k": 20},
                   "outputs": [f"{repo}.band_only_mean", f"{repo}.band_only_sd", f"{repo}.directory_mean",
                               f"{repo}.directory_sd", f"{repo}.directory_cells"]}],
        "sealed_documents": ["spec.md"]}, indent=1))
    sealmod.make_seal(str(study))
    return study


# ================================================================================================= crypt
TABLE = {"schema": 1, "repo": "t", "rows": [{"outcome": "HP", "path": f"src/a/f{i}.py"} for i in range(30)],
         "outcomes": {"HP": {"qualifying_commits": 12, "largest_commit_share": 0.1, "ambiguous_commits": 0}}}


def test_round_trip_header_and_fresh_randomness(key):
    pub = key.public_key()
    a = crypt.encrypt_table(TABLE, pub, "t")
    b = crypt.encrypt_table(TABLE, pub, "t")
    assert a != b, "two encryptions of the same table must differ"
    ha, hb = json.loads(a), json.loads(b)
    assert ha["nonce"] != hb["nonce"] and ha["wrapped_key"] != hb["wrapped_key"] and ha["ciphertext"] != hb["ciphertext"]
    assert ha["format"] == "tc-blind-labels" and ha["version"] == 1 and ha["repo"] == "t"
    assert ha["key_fingerprint"] == crypt.fingerprint(pub)
    assert "src/a" not in a.decode()
    assert digest(crypt.decrypt_table(a, key)) == digest(TABLE)
    assert digest(crypt.decrypt_table(b, key)) == digest(TABLE)


def test_padding_hides_table_size(key):
    small = dict(TABLE, rows=TABLE["rows"][:2])
    assert len(crypt.encrypt_table(small, key.public_key(), "t")) == len(crypt.encrypt_table(TABLE, key.public_key(), "t"))


def test_other_key_refused(key, other_key):
    blob = crypt.encrypt_table(TABLE, key.public_key(), "t")
    with pytest.raises(crypt.BlindCryptoError, match="different public key"):
        crypt.decrypt_table(blob, other_key)
    # a header forged to carry the other key's fingerprint passes the fingerprint check but not the crypto
    forged = json.loads(blob)
    forged["key_fingerprint"] = crypt.fingerprint(other_key.public_key())
    with pytest.raises(crypt.BlindCryptoError):
        crypt.decrypt_table(json.dumps(forged).encode(), other_key)


@pytest.mark.parametrize("field", ["ciphertext", "nonce", "wrapped_key"])
def test_any_modification_detected(key, field):
    blob = json.loads(crypt.encrypt_table(TABLE, key.public_key(), "t"))
    raw = bytearray(__import__("base64").b64decode(blob[field]))
    for pos in (0, len(raw) // 2, len(raw) - 1):
        bad = bytearray(raw)
        bad[pos] ^= 0x01
        mod = dict(blob, **{field: __import__("base64").b64encode(bytes(bad)).decode()})
        with pytest.raises(crypt.BlindCryptoError):
            crypt.decrypt_table(json.dumps(mod).encode(), key)


def test_header_modification_detected(key):
    blob = json.loads(crypt.encrypt_table(TABLE, key.public_key(), "t"))
    with pytest.raises(crypt.BlindCryptoError, match="modified"):
        crypt.decrypt_table(json.dumps(dict(blob, repo="other")).encode(), key)
    with pytest.raises(crypt.BlindCryptoError, match="version"):
        crypt.decrypt_table(json.dumps(dict(blob, version=2)).encode(), key)
    truncated = dict(blob, ciphertext=blob["ciphertext"][:-8])
    with pytest.raises(crypt.BlindCryptoError):
        crypt.decrypt_table(json.dumps(truncated).encode(), key)


def test_committed_public_key(key):
    pub = crypt.load_public_key(str(PUBLIC_KEY))
    assert pub.key_size == 4096
    assert crypt.fingerprint(pub).startswith("8b222bdc37b28697")      # as keys/README.md states
    blob = crypt.encrypt_table(TABLE, pub, "t")
    assert json.loads(blob)["key_fingerprint"] == crypt.fingerprint(pub)
    with pytest.raises(crypt.BlindCryptoError):
        crypt.decrypt_table(blob, key)


def test_owner_path_prompts_and_refuses_unprotected_keys(tmp_path, key, monkeypatch):
    plain = write_private_unencrypted(key, tmp_path / "plain.pem")
    with pytest.raises(crypt.BlindCryptoError, match="not passphrase-protected"):
        crypt.owner_private_key(str(plain))
    test_pass = b"throwaway-test-passphrase"            # a fixed TEST passphrase on a throwaway key
    enc = tmp_path / "enc.pem"
    enc.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                      serialization.BestAvailableEncryption(test_pass)))
    monkeypatch.setattr(crypt, "_prompt_passphrase", lambda: test_pass)
    loaded = crypt.owner_private_key(str(enc))
    assert crypt.fingerprint(loaded.public_key()) == crypt.fingerprint(key.public_key())
    monkeypatch.setattr(crypt, "_prompt_passphrase", lambda: b"wrong")
    with pytest.raises(crypt.BlindCryptoError, match="wrong passphrase") as ei:
        crypt.owner_private_key(str(enc))
    assert "wrong" not in str(ei.value).replace("wrong passphrase", "")


def test_owner_path_reads_openssl_genpkey_format(tmp_path, monkeypatch):
    """The owner's key is made by `openssl genpkey ... -aes-256-cbc` (spec, one-time setup). A throwaway key
    made the same way, with a fixed test passphrase, must load through the owner path."""
    if shutil.which("openssl") is None:
        pytest.skip("no openssl")
    k = tmp_path / "throwaway_key.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-aes-256-cbc",
                    "-pass", "pass:throwaway-test-passphrase", "-out", str(k)], check=True, capture_output=True)
    monkeypatch.setattr(crypt, "_prompt_passphrase", lambda: b"throwaway-test-passphrase")
    loaded = crypt.owner_private_key(str(k))
    blob = crypt.encrypt_table(TABLE, loaded.public_key(), "t")
    assert digest(crypt.decrypt_table(blob, loaded)) == digest(TABLE)


def test_prompt_never_falls_back_to_stdin(monkeypatch):
    def fake_getpass(prompt=""):
        warnings.warn("no tty", getpass.GetPassWarning)
        return "from-stdin"
    monkeypatch.setattr(getpass, "getpass", fake_getpass)
    with pytest.raises(crypt.BlindCryptoError, match="no terminal"):
        crypt._prompt_passphrase()


def test_no_passphrase_on_command_line_or_environment():
    for mod in (crypt, jobcore, score, gates):
        src = inspect.getsource(mod)
        assert "os.environ" not in src and "getenv" not in src, f"{mod.__name__} reads the environment"
    with pytest.raises(SystemExit):
        score.main(["--study", "x", "--key", "k", "--passphrase", "p"])
    with pytest.raises(SystemExit):
        gates.main(["--study", "x", "--key", "k", "--password", "p"])


def test_cli_without_terminal_refuses(tmp_path, planted, key):
    """The owner path run without a controlling terminal (new session) must refuse, never read stdin."""
    study = make_study(tmp_path, planted, key)
    enc = tmp_path / "enc.pem"
    enc.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                      serialization.BestAvailableEncryption(b"throwaway-test-passphrase")))
    p = subprocess.run([sys.executable, "-B", str(BLIND / "score.py"), "--study", str(study), "--key", str(enc)],
                       input=b"throwaway-test-passphrase\n", capture_output=True, start_new_session=True)
    assert p.returncode == 2 and b"no terminal" in p.stderr
    assert not (study / "result" / "result.json").exists()
    plain = write_private_unencrypted(key, tmp_path / "plain.pem")
    p = subprocess.run([sys.executable, "-B", str(BLIND / "score.py"), "--study", str(study), "--key", str(plain)],
                       capture_output=True, start_new_session=True, stdin=subprocess.DEVNULL)
    assert p.returncode == 2 and b"not passphrase-protected" in p.stderr
    assert not (study / "result").exists() or listing(study / "result") == []


# ================================================================================================= build_labels
def test_build_writes_only_ciphertext_and_non_identifying_outputs(tmp_path, planted, key):
    pub = write_public(key, tmp_path / "pub.pem")
    file_table, label_table = build_labels.table_from_manifest(planted)
    labels = tmp_path / "labels"
    labels.mkdir()
    RECORDER.paths = []
    RECORDER.active = True
    try:
        build_labels.build("ctl", file_table, label_table, str(labels), str(pub))
    finally:
        RECORDER.active = False
    finals = sorted(str(labels / f"ctl{s}") for s in build_labels.OUTPUT_SUFFIXES)
    # every write goes to a temporary name in the labels directory that is then renamed onto one output
    assert sorted(dst for _src, dst in RECORDER.renames) == finals
    assert sorted(RECORDER.paths) == sorted(src for src, _dst in RECORDER.renames), \
        "the builder opened something other than its four outputs' temporary names for writing"
    assert all(os.path.dirname(src) == str(labels) and os.path.basename(src).startswith(".")
               for src, _dst in RECORDER.renames)
    assert listing(labels) == sorted(f"ctl{s}" for s in build_labels.OUTPUT_SUFFIXES)
    paths = [r["path"] for r in file_table]
    basenames = {p.rsplit("/", 1)[1] for p in paths}
    enc = (labels / "ctl.enc").read_text()
    assert not any(p in enc for p in paths)
    for name in ("ctl.marginals.json", "ctl.scramble_report.json"):
        text = (labels / name).read_text()
        assert "src/" not in text and not any(b in text for b in basenames), f"{name} names a file"
        strings = []

        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    strings.append(k)
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
            elif isinstance(o, str):
                strings.append(o)
        walk(json.loads(text))
        assert not any("/" in s for s in strings if s not in (scramble.CELL_RULE,))
    assert digest(crypt.decrypt_table((labels / "ctl.enc").read_bytes(), key)) == digest(dict(label_table, repo="ctl"))
    s = json.loads((labels / "ctl.scrambled.json").read_text())
    assert s["scrambled"] is True and len(s["copies"]) == 20 and all(c["scrambled"] for c in s["copies"])


def test_report_cells_do_not_depend_on_labels(tmp_path, planted, key):
    """The cell report is computed from the file table alone: two different label tables give the same cell
    report; only the release decision can differ, and no dense-cell count is written [r3]."""
    pub = write_public(key, tmp_path / "pub.pem")
    file_table, label_table = build_labels.table_from_manifest(planted)
    other = dict(label_table, rows=[{"outcome": "HP", "path": r["path"]}
                                    for r in random.Random(5).sample(file_table, len(label_table["rows"]))])
    build_labels.build("a", file_table, label_table, str(tmp_path / "l1"), str(pub))
    build_labels.build("a", file_table, other, str(tmp_path / "l2"), str(pub))
    r1 = json.loads((tmp_path / "l1" / "a.scramble_report.json").read_text())
    r2 = json.loads((tmp_path / "l2" / "a.scramble_report.json").read_text())
    assert r1["cells"] == r2["cells"]
    assert set(r1["outcomes"]["HP"]) <= {"released", "share_true_positives_positive_in_all_copies", "reason"}
    assert "band only" in r1["cell_rule"] and r1["cells"]["null_is_size_only"] is True


@pytest.mark.parametrize("name", ["ctl.json", "ctl.labels.csv", "ctl_labels.json", "ctl-outcomes.tsv", "ctl",
                                  "ctl.positives.txt", "CTL.JSON"])
def test_builder_refuses_beside_plaintext_labels(tmp_path, key, name):
    pub = write_public(key, tmp_path / "pub.pem")
    labels = tmp_path / "labels"
    labels.mkdir()
    (labels / name).write_text("x")
    ft = [{"path": f"src/d/f{i}.py", "loc": 10 + i} for i in range(40)]
    lt = {"schema": 1, "rows": [{"outcome": "HP", "path": "src/d/f3.py"}], "outcomes": {"HP": {}}}
    with pytest.raises(build_labels.BuildError, match="plaintext"):
        build_labels.build("ctl", ft, lt, str(labels), str(pub))
    assert listing(labels) == [name]


def test_builder_ignores_other_repos_files_and_has_no_plaintext_option(tmp_path, key, planted):
    pub = write_public(key, tmp_path / "pub.pem")
    labels = tmp_path / "labels"
    labels.mkdir()
    for n in ("ctl2.enc", "ctl_b.scrambled.json", "other.json"):
        (labels / n).write_text("x")
    ft, lt = build_labels.table_from_manifest(planted)
    build_labels.build("ctl", ft, lt, str(labels), str(pub))
    with pytest.raises(build_labels.BuildError, match="already exist"):
        build_labels.build("ctl", ft, lt, str(labels), str(pub))
    p = subprocess.run([sys.executable, "-B", str(BLIND / "build_labels.py"), "--help"], capture_output=True, text=True)
    opts = {w for w in p.stdout.split() if w.startswith("--")}
    assert opts <= {"--manifest", "--repo", "--labels-dir", "--pub", "--k", "--replace", "--help"}
    # an input file that holds plaintext labels may not sit inside the labels directory
    (labels / "manifest.json").write_text(json.dumps(planted))
    p = subprocess.run([sys.executable, "-B", str(BLIND / "build_labels.py"), "--manifest", str(labels / "manifest.json"),
                        "--repo", "zz", "--labels-dir", str(labels), "--pub", str(pub)], capture_output=True, text=True)
    assert p.returncode == 2 and "inside the labels directory" in p.stderr


def test_withheld_when_2pct_rule_fails(tmp_path, key):
    """Ten files, one per LOC band: every cell is its whole band, so a positive keeps its label in every copy.
    The scrambles must be withheld and the reason written."""
    pub = write_public(key, tmp_path / "pub.pem")
    ft = [{"path": f"src/d{i % 3}/f{i}.py", "loc": 10 * (i + 1)} for i in range(10)]
    lt = {"schema": 1, "rows": [{"outcome": "HP", "path": "src/d1/f4.py"}],
          "outcomes": {"HP": {"qualifying_commits": 1, "largest_commit_share": 1.0, "ambiguous_commits": 0}}}
    build_labels.build("tiny", ft, lt, str(tmp_path / "labels"), str(pub))
    assert not (tmp_path / "labels" / "tiny.scrambled.json").exists()
    rep = json.loads((tmp_path / "labels" / "tiny.scramble_report.json").read_text())
    assert rep["released"] is False and "not released" in rep["reason"]
    assert rep["outcomes"]["HP"]["share_true_positives_positive_in_all_copies"] == 1.0
    assert (tmp_path / "labels" / "tiny.enc").exists()


# ================================================================================================= scramble
def test_cells_follow_rules_1_and_2(planted):
    ft, _lt = build_labels.table_from_manifest(planted)
    band = scramble.loc_bands(ft)
    cells = scramble.cells_from_file_table(ft, scramble.R2_MIN_CELL)
    members = [p for v in cells.values() for p in v]
    assert sorted(members) == sorted(r["path"] for r in ft), "cells must partition the file table"
    band_size = {}
    for r in ft:
        band_size[band[r["path"]]] = band_size.get(band[r["path"]], 0) + 1
    for (b, d), v in cells.items():
        assert all(band[p] == b for p in v), "a cell lies inside one LOC band"
        assert all(d == "" or p.startswith(d + "/") for p in v), "a cell's directory is an ancestor of its files"
        assert len(v) >= scramble.R2_MIN_CELL or len(v) == band_size[b], "a cell under 8 files must be its whole band"
    assert len(set(band.values())) == 10
    # file table only: order and extra columns do not matter
    shuffled = [dict(r, extra=random.random()) for r in random.Random(3).sample(ft, len(ft))]
    assert scramble.cells_from_file_table(shuffled, scramble.R2_MIN_CELL) == cells
    assert list(inspect.signature(scramble.cells_from_file_table).parameters) == ["file_table", "min_cell"]
    # merging only shortens directories: a cell at full depth exists where a directory has >= 8 files in a band
    full = scramble.cells_first_version(ft)
    # (unless its band's remainder was too small and the whole band became one cell)
    whole_band = {b for (b, d) in cells if d == "" and len(cells[(b, d)]) == band_size[b]}
    kept = 0
    for k, v in full.items():
        if len(v) >= scramble.R2_MIN_CELL and k[0] not in whole_band:
            assert k in cells and set(v) <= set(cells[k])
            kept += 1
    assert kept > 0


def test_dense_cells_merge_up_once():
    ft = ([{"path": f"src/a/x/f{i}.py", "loc": 100} for i in range(10)]
          + [{"path": f"src/a/y/g{i}.py", "loc": 100} for i in range(10)]
          + [{"path": f"src/b/h{i}.py", "loc": 100} for i in range(10)])
    base = scramble.cells_from_file_table(ft, 8)
    assert set(base) == {(0, "src/a/x"), (0, "src/a/y"), (0, "src/b")}
    pos = [f"src/a/x/f{i}.py" for i in range(9)]                   # 90% of src/a/x
    final, merges, unmergeable = scramble.merge_dense(base, pos)
    assert merges == 1 and unmergeable == 0
    assert set(final) == {(0, "src/a"), (0, "src/b")} and len(final[(0, "src/a")]) == 20
    # a dense cell that is already the band alone cannot go higher; it is counted
    final2, m2, u2 = scramble.merge_dense({(0, ""): [r["path"] for r in ft]}, [r["path"] for r in ft][:28])
    assert m2 == 0 and u2 == 1
    # the directory-preserving cells of the gates job apply the same rule (minimum 8 here, to see it)
    assert set(scramble.directory_cells(ft, pos, min_cell=8)) == {(0, "src/a"), (0, "src/b")}
    # and the released report carries no label-derived count [r3]
    _c, part, _m = scramble.scramble_outcome(ft, pos, 20)
    assert set(part) <= {"released", "share_true_positives_positive_in_all_copies", "reason"}


def test_permutation_preserves_cell_counts_and_copies_are_independent(planted):
    ft, lt = build_labels.table_from_manifest(planted)
    pos = [r["path"] for r in lt["rows"]]
    cells = scramble.released_cells(ft)
    k = 20
    copies = scramble.scramble(cells, pos, k)
    assert len(copies) == k
    pset = set(pos)
    for c in copies:
        cs = set(c)
        assert len(cs) == len(c) == len(pos)
        for v in cells.values():
            assert sum(p in cs for p in v) == sum(p in pset for p in v), "positives per cell must be preserved"
    assert len({tuple(c) for c in copies}) == k
    # independence: mean pairwise overlap matches its expectation under independent uniform draws per cell
    expected = sum(sum(p in pset for p in v) ** 2 / len(v) for v in cells.values())
    overlaps = [len(set(copies[i]) & set(copies[j])) for i in range(k) for j in range(i + 1, k)]
    assert abs(statistics.fmean(overlaps) - expected) < 0.1 * expected
    # and a copy is no closer to the truth than chance
    to_truth = statistics.fmean(len(set(c) & pset) for c in copies)
    assert abs(to_truth - expected) < 0.15 * expected


def test_permutation_is_unseeded_and_unstored(planted):
    ft, lt = build_labels.table_from_manifest(planted)
    pos = [r["path"] for r in lt["rows"]]
    cells = scramble.released_cells(ft)
    random.seed(0)
    a = scramble.scramble(cells, pos, 3)
    random.seed(0)
    b = scramble.scramble(cells, pos, 3)
    assert a != b, "the global random seed must not reach the permutation"
    assert "seed" not in inspect.signature(scramble.scramble).parameters
    src = inspect.getsource(scramble)
    assert "SystemRandom()" in src and "random.Random(" not in src and ".seed(" not in src
    RECORDER.paths = []
    RECORDER.active = True
    try:
        scramble.scramble_outcome(ft, pos, 20)
    finally:
        RECORDER.active = False
    assert RECORDER.paths == [], "the scramble writes nothing"


def test_scramble_breaks_a_planted_association():
    """Synthetic: within one large cell the flag is a function of the measure; after scrambling the statistic
    is near zero while the margins hold."""
    ft = [{"path": f"src/m/f{i:03d}.py", "loc": 100, "measures": {"x": i}} for i in range(200)]
    pos = [r["path"] for r in ft if r["measures"]["x"] >= 150]
    true = registry.within_decile_rank_corr(ft, pos, lambda r: r["measures"]["x"])[0]
    cells = scramble.released_cells(ft)
    copies = scramble.scramble(cells, pos, 50)
    vals = [registry.within_decile_rank_corr(ft, c, lambda r: r["measures"]["x"])[0] for c in copies]
    assert true > 0.7 and abs(statistics.fmean(vals)) < 0.05
    assert abs(registry.expected_under_scramble(ft, cells, pos, lambda r: r["measures"]["x"])) < 1e-12


# ------------------------------------------------------------------------------------------------- the leak
def leak(files, pos, cells, k=20):
    copies = scramble.scramble(cells, pos, k)
    m = scramble.leak_measures(cells, pos, copies)
    true = stat(files, pos)
    exp = registry.expected_under_scramble(files, cells, pos, lambda r: r["measures"][MEASURE])
    return m, true, exp, copies


def test_r3_band_only_null_and_the_leaks_it_replaces(r3_repos):
    """[r3] Over 8 control repositories with a planted effect, for the released (band-only) copies:
    - the exact expected effect on scrambled labels is under 5% of the true one in every repository;
    - the mean over repositories of the effect on the 20 released copies, as a share of the true one, is within
      three standard errors of zero (the standard error from the copies' own spread; DECISIONS.md 24);
    - no file is in a cell with no positives unless its whole band has none;
    - under 2% of true positives are positive in all 20 copies (rule 5).
    The Revision 2 cells (minimum 8) fail the 5% rule in at least one repository, and the first version's cells
    (band x full directory) fail both the 5% rule and the 2% rule in every repository."""
    ratios, variances, r2_exact = [], [], []
    for s, m in sorted(r3_repos.items()):
        files, pos = truth_from_manifest(m)
        ft = [{"path": r["path"], "loc": r["loc"]} for r in files]
        pset = set(pos)
        true = stat(files, pos)
        assert true > 0.05, f"seed {s}: the planted effect must be visible"
        band = scramble.released_cells(ft)
        m_band, _t, e_band, copies = leak(files, pos, band)
        assert abs(e_band / true) < 0.05, f"seed {s}"
        assert abs(e_band) < 1e-12, f"seed {s}: zero by algebra (DECISIONS.md 24)"
        assert m_band["share_positives_in_all_copies"] < scramble.ALL_COPIES_LIMIT, f"seed {s}"
        bands = scramble.loc_bands(ft)
        for (b, _d), v in band.items():
            if not any(p in pset for p in v):
                assert not any(bands[p] == b and p in pset for p in bands), f"seed {s}"
        vals = [stat(files, c) for c in copies]
        ratios.append(statistics.fmean(vals) / true)
        variances.append(statistics.variance(vals) / len(vals) / true ** 2)
        r2 = scramble.merge_dense(scramble.cells_from_file_table(ft, scramble.R2_MIN_CELL), pos)[0]
        r2_exact.append(registry.expected_under_scramble(files, r2, pos, lambda r: r["measures"][MEASURE]) / true)
        m1, _t, e1, _c = leak(files, pos, scramble.cells_first_version(ft))
        assert m1["share_positives_in_all_copies"] >= scramble.ALL_COPIES_LIMIT and e1 / true >= 0.05, f"seed {s}"
    mean = statistics.fmean(ratios)
    se = math.sqrt(sum(variances)) / len(ratios)
    assert abs(mean) < 3 * se
    assert any(abs(r) >= 0.05 for r in r2_exact), "the Revision 2 cells must be seen to leak"


def test_released_copies_are_band_only(tmp_path, planted, key):
    """What build_labels releases keeps each band's count of positives and nothing finer: across copies the
    count in a band is constant, while counts per (band, directory) vary."""
    pub = write_public(key, tmp_path / "pub.pem")
    ft, lt = build_labels.table_from_manifest(planted)
    build_labels.build("ctl", ft, lt, str(tmp_path / "labels"), str(pub))
    s = json.loads((tmp_path / "labels" / "ctl.scrambled.json").read_text())
    assert "band only" in s["cell_rule"]
    bands = scramble.loc_bands(ft)
    per_band, per_dir = [], []
    for c in s["copies"]:
        paths = [r["path"] for r in c["rows"]]
        per_band.append(sorted(collections.Counter(bands[p] for p in paths).items()))
        per_dir.append(sorted(collections.Counter((bands[p], p.rsplit("/", 1)[0]) for p in paths).items()))
    assert len({tuple(x) for x in per_band}) == 1
    assert len({tuple(x) for x in per_dir}) > 1


def test_gate_null_spread_is_declared_scalars_only(tmp_path, planted, key):
    """[r3] The directory-preserving scramble exists only inside the gates job: the gate writes five declared
    scalars per repo; no copy reaches disk."""
    study = make_study(tmp_path, planted, key)
    before = listing(study)
    RECORDER.paths, RECORDER.renames = [], []
    RECORDER.active = True
    try:
        assert gates.run(str(study), private_key=key) == 0
    finally:
        RECORDER.active = False
    assert sorted(set(listing(study)) - set(before)) == ["result/gates.json", "result/gates_unblinding.json"]
    assert {os.path.basename(d) for _s, d in RECORDER.renames} == {"gates.json", "gates_unblinding.json"}
    out = json.loads((study / "result" / "gates.json").read_text())["gates"]["null_spread"]["outputs"]
    assert set(out) == {"ctl.band_only_mean", "ctl.band_only_sd", "ctl.directory_mean", "ctl.directory_sd",
                        "ctl.directory_cells"}
    assert all(isinstance(v, (int, float)) for v in out.values())
    assert out["ctl.band_only_sd"] > 0 and out["ctl.directory_sd"] > 0
    # the builder has no way to write directory-preserving copies
    src = inspect.getsource(build_labels)
    assert "directory_cells" not in src and "cells_from_file_table" not in src and "merge_dense" not in src


def test_directory_cells_keep_directories_when_large_enough():
    ft = [{"path": f"src/{d}/f{i}.py", "loc": 100} for d in ("a", "b", "c") for i in range(25)]
    cells = scramble.directory_cells(ft, [f"src/a/f{i}.py" for i in range(5)])
    assert set(cells) == {(0, "src/a"), (0, "src/b"), (0, "src/c")}
    small = [{"path": f"src/{d}/f{i}.py", "loc": 100} for d in ("a", "b", "c") for i in range(15)]
    assert set(scramble.directory_cells(small, [])) == {(0, "src")}      # 45 files: no need to go higher


def test_write_atomic_leaves_no_partial_file(tmp_path, monkeypatch):
    p = tmp_path / "out.json"
    sealmod.write_atomic(str(p), b"old")
    def boom(_fd):
        raise OSError("disk full")
    monkeypatch.setattr(os, "fsync", boom)
    with pytest.raises(OSError):
        sealmod.write_atomic(str(p), b"new content")
    assert p.read_bytes() == b"old" and listing(tmp_path) == ["out.json"]


# ================================================================================================= the jobs
def direct(manifest):
    files, pos = truth_from_manifest(manifest)
    return stat(files, pos), files, pos


def test_end_to_end_equals_manifest(tmp_path, planted, key, capfd):
    study = make_study(tmp_path, planted, key)
    before = listing(study)
    assert score.run(str(study), private_key=key) == 0
    after = listing(study)
    assert sorted(set(after) - set(before)) == ["result/result.json", "result/unblinding.json"]
    res = json.loads((study / "result" / "result.json").read_text())
    rho, files, pos = direct(planted)
    assert set(res["outputs"]) == {"ctl.rho", "ctl.n_files", "ctl.n_positive", "ctl.n_deciles_used"}
    assert res["outputs"]["ctl.rho"] == rho and repr(res["outputs"]["ctl.rho"]) == repr(rho)
    assert res["outputs"]["ctl.n_files"] == len(files) and res["outputs"]["ctl.n_positive"] == len(pos)
    led = json.loads((study / "result" / "unblinding.json").read_text())
    seal_hash = hashlib.sha256((study / "seal.json").read_bytes()).hexdigest()
    assert len(led) == 1 and led[0]["status"] == "completed" and led[0]["seal_hash"] == seal_hash
    assert led[0]["who"] and led[0]["time"] and led[0]["rerun_reason"] is None
    assert res["seal_hash"] == seal_hash
    out = capfd.readouterr()
    leaked = "src/" in out.out + out.err
    assert not leaked
    receipt = (f"score seal {seal_hash} time {led[0]['time']} result/result.json sha256 "
               f"{hashlib.sha256((study / 'result' / 'result.json').read_bytes()).hexdigest()}")
    assert led[0]["receipt"] == receipt and receipt in out.out
    # second run refused; nothing changes
    snap = {p: (study / p).read_bytes() for p in after}
    with pytest.raises(jobcore.JobError, match="--rerun"):
        score.run(str(study), private_key=key)
    assert {p: (study / p).read_bytes() for p in listing(study)} == snap
    with pytest.raises(jobcore.JobError, match="reason"):
        score.run(str(study), private_key=key, rerun="  ")
    # rerun with a reason: recorded, the earlier result kept
    assert score.run(str(study), private_key=key, rerun="test of the rerun path") == 0
    led = json.loads((study / "result" / "unblinding.json").read_text())
    assert [e["rerun_reason"] for e in led] == [None, "test of the rerun path"]
    assert (study / "result" / "result.superseded-0.json").exists()
    assert json.loads((study / "result" / "result.json").read_text())["outputs"]["ctl.rho"] == rho


def test_gates_job(tmp_path, planted, key):
    study = make_study(tmp_path, planted, key)
    assert gates.run(str(study), private_key=key) == 0
    g = json.loads((study / "result" / "gates.json").read_text())
    files, pos = truth_from_manifest(planted)
    assert g["gates"]["size"]["outputs"] == registry.gate_size_surrogate(
        {"ctl": {"files": files, "labels": {"rows": [{"outcome": "HP", "path": p} for p in pos]}}}, {"outcome": "HP"})
    assert set(g["gates"]) == {"size", "placebo", "null_spread"}
    assert listing(study / "result") == ["gates.json", "gates_unblinding.json"]
    with pytest.raises(jobcore.JobError, match="--rerun"):
        gates.run(str(study), private_key=key)
    # the score job has its own ledger and still runs once
    assert score.run(str(study), private_key=key) == 0


def test_wrong_key_refused(tmp_path, planted, key, other_key):
    study = make_study(tmp_path, planted, key)
    with pytest.raises(jobcore.JobError, match="fingerprint"):
        score.run(str(study), private_key=other_key)
    assert not (study / "result").exists()


@pytest.mark.parametrize("what", ["enc", "scan", "study", "doc", "extra_scan", "extra_enc", "seal_missing"])
def test_broken_seal_stops_the_job(tmp_path, planted, key, what):
    study = make_study(tmp_path, planted, key)
    if what == "enc":
        p = study / "labels" / "ctl.enc"
        b = json.loads(p.read_text())
        b["nonce"] = b["nonce"][::-1]
        p.write_text(json.dumps(b))
    elif what == "scan":
        p = study / "scans" / "ctl.json"
        s = json.loads(p.read_text())
        s["files"][0]["loc"] += 1
        p.write_text(json.dumps(s))
    elif what == "study":
        p = study / "study.json"
        s = json.loads(p.read_text())
        s["scorer"]["params"]["measure"] = "other"
        p.write_text(json.dumps(s))
    elif what == "doc":
        (study / "spec.md").write_text("changed\n")
    elif what == "extra_scan":
        (study / "scans" / "more.json").write_text("{}")
    elif what == "extra_enc":
        shutil.copy(study / "labels" / "ctl.enc", study / "labels" / "copy.enc")
    elif what == "seal_missing":
        (study / "seal.json").unlink()
    with pytest.raises(jobcore.JobError, match="stop"):
        score.run(str(study), private_key=key)
    with pytest.raises(jobcore.JobError, match="stop"):
        gates.run(str(study), private_key=key)
    assert not (study / "result").exists()


DRIVER = r"""
import sys, json
sys.path.insert(0, sys.argv[1])
import score, jobcore
from cryptography.hazmat.primitives import serialization
key = serialization.load_pem_private_key(open(sys.argv[3], 'rb').read(), password=None)  # throwaway test key
try:
    print("rc", score.run(sys.argv[2], private_key=key))
except jobcore.JobError as exc:
    print("refused", exc)
"""


def test_changed_scorer_stops_the_job(tmp_path, planted, key):
    """A copy of tools/blind is sealed, its scorer registry is then edited, and the copy's own job must stop.
    (The real tools/blind is never modified.)"""
    code = tmp_path / "copy" / "tools" / "blind"
    code.mkdir(parents=True)
    for p in BLIND.glob("*.py"):
        shutil.copy(p, code / p.name)
    study = tmp_path / "study"
    base = tmp_path / "base"
    base.mkdir()
    s = make_study(base, planted, key)
    shutil.copytree(s, study)
    (study / "seal.json").unlink()
    keyfile = write_private_unencrypted(key, tmp_path / "throwaway.pem")
    seal_cmd = f"import sys; sys.path.insert(0, {str(code)!r}); import seal; seal.make_seal({str(study)!r})"
    subprocess.run([sys.executable, "-B", "-c", seal_cmd], check=True)
    with open(code / "registry.py", "a") as fh:
        fh.write("\n# edited after the seal\n")
    p = subprocess.run([sys.executable, "-B", "-c", DRIVER, str(code), str(study), str(keyfile)],
                       capture_output=True, text=True)
    assert "refused stop: seal mismatch: tools/blind/registry.py has changed" in p.stdout, p.stderr[-500:]
    assert not (study / "result").exists()
    # unedited, the copy runs
    shutil.copy(BLIND / "registry.py", code / "registry.py")
    p = subprocess.run([sys.executable, "-B", "-c", DRIVER, str(code), str(study), str(keyfile)],
                       capture_output=True, text=True)
    assert "rc 0" in p.stdout, p.stderr[-500:]


def test_sealed_code_outside_tools_blind(tmp_path, planted, key):
    """[review finding 2] study.json lists extra code paths (relative to the repository root); the seal hashes
    them, and changing one, or removing it, stops the job. Done on a copy of the tree under tmp_path."""
    root = tmp_path / "copy"
    code = root / "tools" / "blind"
    code.mkdir(parents=True)
    for p in BLIND.glob("*.py"):
        shutil.copy(p, code / p.name)
    (root / "tools" / "study_scorer_helper.py").write_text("FACTOR = 1\n")
    base = tmp_path / "base"
    base.mkdir()
    study = tmp_path / "study"
    shutil.copytree(make_study(base, planted, key), study)
    (study / "seal.json").unlink()
    spec = json.loads((study / "study.json").read_text())
    spec["sealed_code"] = ["tools/study_scorer_helper.py"]
    (study / "study.json").write_text(json.dumps(spec))
    keyfile = write_private_unencrypted(key, tmp_path / "throwaway.pem")
    seal_cmd = f"import sys; sys.path.insert(0, {str(code)!r}); import seal; seal.make_seal({str(study)!r})"
    subprocess.run([sys.executable, "-B", "-c", seal_cmd], check=True)
    assert "tools/study_scorer_helper.py" in json.loads((study / "seal.json").read_text())["code"]
    (root / "tools" / "study_scorer_helper.py").write_text("FACTOR = 2\n")
    p = subprocess.run([sys.executable, "-B", "-c", DRIVER, str(code), str(study), str(keyfile)],
                       capture_output=True, text=True)
    assert "seal mismatch: tools/study_scorer_helper.py has changed" in p.stdout, p.stderr[-500:]
    (root / "tools" / "study_scorer_helper.py").unlink()
    p = subprocess.run([sys.executable, "-B", "-c", DRIVER, str(code), str(study), str(keyfile)],
                       capture_output=True, text=True)
    assert "tools/study_scorer_helper.py is sealed but missing" in p.stdout, p.stderr[-500:]
    assert not (study / "result").exists()
    with pytest.raises(sealmod.SealError):
        spec["sealed_code"] = ["../outside.py"]
        (study / "study.json").write_text(json.dumps(spec))
        sealmod.verify_seal(str(study))


# ------------------------------------------------------------------------------------------------- guard
def _ok(data, params):
    return registry.reference_scorer(data, params)


def bad_extra(data, params):
    out = _ok(data, params)
    for r in data["ctl"]["labels"]["rows"][:3]:
        out[r["path"]] = 1                       # per-file outputs joined to outcomes
    return out


def bad_list(data, params):
    out = _ok(data, params)
    out["ctl.rho"] = [r["path"] for r in data["ctl"]["labels"]["rows"]]
    return out


def bad_long_string(data, params):
    out = _ok(data, params)
    out["ctl.rho"] = ",".join(r["path"] for r in data["ctl"]["labels"]["rows"])
    return out


def make_writer(target):
    def bad_write(data, params):
        with open(target, "w") as fh:
            fh.write("\n".join(r["path"] for r in data["ctl"]["labels"]["rows"]))
        return _ok(data, params)
    return bad_write


def make_os_writer(target):
    def bad_os_write(data, params):
        fd = os.open(target, os.O_WRONLY | os.O_CREAT, 0o600)
        os.write(fd, b"x")
        os.close(fd)
        return _ok(data, params)
    return bad_os_write


def bad_print(data, params):
    print(data["ctl"]["labels"]["rows"][0]["path"])
    return _ok(data, params)


def bad_fd_write(data, params):
    os.write(1, data["ctl"]["labels"]["rows"][0]["path"].encode())
    return _ok(data, params)


def bad_subprocess(data, params):
    subprocess.run(["true"])
    return _ok(data, params)


def bad_raise(data, params):
    raise KeyError(data["ctl"]["labels"]["rows"][0]["path"])


def make_swallower(target):
    def bad_swallow(data, params):
        try:
            with open(target, "w") as fh:
                fh.write("x")
        except Exception:
            pass
        return _ok(data, params)
    return bad_swallow


def bad_stderr_logging(data, params):
    import logging
    logging.getLogger("x").error("positive: %s", data["ctl"]["labels"]["rows"][0]["path"])
    return _ok(data, params)


@pytest.mark.parametrize("name", ["extra", "list", "long_string", "write", "os_write", "print", "fd_write",
                                  "subprocess", "raise", "swallow", "logging"])
def test_scorer_cannot_output_more_than_declared(tmp_path, planted, key, monkeypatch, capfd, name):
    study = make_study(tmp_path, planted, key)
    target = tmp_path / "leak.txt"
    fn = {"extra": bad_extra, "list": bad_list, "long_string": bad_long_string, "write": make_writer(target),
          "os_write": make_os_writer(target), "print": bad_print, "fd_write": bad_fd_write,
          "subprocess": bad_subprocess, "raise": bad_raise, "swallow": make_swallower(target),
          "logging": bad_stderr_logging}[name]
    monkeypatch.setitem(registry.SCORERS, "reference_within_decile_rank_corr", fn)
    before = listing(study)
    rc = score.run(str(study), private_key=key)
    assert rc == 3
    assert not target.exists(), "the scorer's write must be blocked"
    assert sorted(set(listing(study)) - set(before)) == ["result/unblinding.json"]
    led = json.loads((study / "result" / "unblinding.json").read_text())
    assert len(led) == 1 and led[0]["status"].startswith("stopped:")
    out = capfd.readouterr()
    leaked = "src/" in out.out + out.err + json.dumps(led)
    assert not leaked, "nothing the scorer produced may reach the terminal or the ledger"
    # the stopped attempt counts as the run: a second needs --rerun
    monkeypatch.setitem(registry.SCORERS, "reference_within_decile_rank_corr", registry.reference_scorer)
    with pytest.raises(jobcore.JobError, match="--rerun"):
        score.run(str(study), private_key=key)


def test_scorer_runs_exactly_once(tmp_path, planted, key, monkeypatch):
    calls = []

    def counting(data, params):
        calls.append(1)
        return registry.reference_scorer(data, params)
    monkeypatch.setitem(registry.SCORERS, "reference_within_decile_rank_corr", counting)
    assert score.run(str(study := make_study(tmp_path, planted, key)), private_key=key) == 0
    assert len(calls) == 1
    with pytest.raises(jobcore.JobError):
        score.run(str(study), private_key=key)
    assert len(calls) == 1


def test_guard_is_off_outside_the_scorer(tmp_path):
    jobcore.guarded_call(lambda: 1)
    p = tmp_path / "after.txt"
    p.write_text("ok")                       # the hook stays installed but inactive
    assert p.read_text() == "ok"


# ------------------------------------------------------------------------------------------------- scrambled
def test_scorer_refuses_scrambled_input(tmp_path, planted, key):
    s = json.loads(json.dumps(build_labels.table_from_manifest(planted)[1]))

    def as_scrambled(t):
        return dict(t, scrambled=True)
    # the builder refuses to encrypt it ...
    with pytest.raises(build_labels.BuildError, match="scrambled"):
        make_study(tmp_path / "a", planted, key, tamper_table=as_scrambled)
    # ... and if such a file is encrypted by other means and sealed, the job refuses it
    study = make_study(tmp_path, planted, key)
    blob = crypt.encrypt_table(dict(s, repo="ctl", scrambled=True), key.public_key(), "ctl")
    (study / "labels" / "ctl.enc").write_bytes(blob)
    (study / "seal.json").unlink()
    sealmod.make_seal(str(study))
    with pytest.raises(jobcore.ScrambledInput):
        score.run(str(study), private_key=key)
    assert not (study / "result" / "result.json").exists()
    # the wrapper every scorer call goes through refuses it too
    data = {"ctl": {"files": [], "labels": {"scrambled": True, "rows": []}}}
    with pytest.raises(jobcore.ScrambledInput):
        jobcore.call_scorer(registry.reference_scorer, data, {}, [], dry_run=False)


def test_dry_run_stamps_every_output(tmp_path, planted, key, capfd):
    study = make_study(tmp_path, planted, key)
    before = listing(study)
    assert score.run(str(study), dry_run=True) == 0
    assert gates.run(str(study), dry_run=True) == 0
    new = sorted(set(listing(study)) - set(before))
    assert new == ["dry_run/gates.NOT_A_RESULT.json", "dry_run/score.NOT_A_RESULT.json"]
    d = json.loads((study / "dry_run" / "score.NOT_A_RESULT.json").read_text())
    assert d["stamp"] == "NOT A RESULT" and d["k"] == 20 and d["seal"].startswith("sealed ")
    assert all(c["stamp"] == "NOT A RESULT" for c in d["copies"])
    assert d["spread"] and all(v["stamp"] == "NOT A RESULT" for v in d["spread"].values())
    # the null on scrambled labels is centred near zero compared with the true effect
    rho, _f, _p = direct(planted)
    assert abs(d["spread"]["scorer/ctl.rho"]["mean"]) < abs(rho)
    # a dry run is not a run
    assert score.run(str(study), private_key=key) == 0
    capfd.readouterr()


def test_cli_dry_run_and_refusals(tmp_path, planted, key):
    study = make_study(tmp_path, planted, key)
    p = subprocess.run([sys.executable, "-B", str(BLIND / "score.py"), "--study", str(study), "--dry-run"],
                       capture_output=True, text=True, start_new_session=True, stdin=subprocess.DEVNULL)
    assert p.returncode == 0 and "NOT A RESULT" in p.stdout
    p = subprocess.run([sys.executable, "-B", str(BLIND / "score.py"), "--study", str(study)],
                       capture_output=True, text=True, start_new_session=True, stdin=subprocess.DEVNULL)
    assert p.returncode == 2 and "--key" in p.stderr
    p = subprocess.run([sys.executable, "-B", str(BLIND / "score.py"), "--study", str(study), "--dry-run",
                        "--rerun", "x"], capture_output=True, text=True, start_new_session=True,
                       stdin=subprocess.DEVNULL)
    assert p.returncode == 2
    assert not (study / "result").exists()
