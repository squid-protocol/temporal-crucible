"""Tests of the SA3 harness (tools/harness/, docs/process/harness_spec.md).

The four sandbox tests run first and need no engine. They never open, list or stat the study directory,
/nvme-data, the clone pool or ~/.blind from outside the sandbox: every look at those paths happens inside it.
The end-to-end test runs one small control repository through the pipeline (inside the sandbox) and is skipped,
with the reason, when the engine export or tree_sitter_language_pack 1.20.0 is not available.

WORK is always under pytest's tmp_path.
"""
from __future__ import annotations

import importlib.metadata as md
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "tools" / "harness"
sys.path.insert(0, str(HARNESS))
import sandbox as SB  # noqa: E402


@pytest.fixture
def work(tmp_path):
    w = SB.prepare(tmp_path / "work")
    dst = w / "tree" / "tools" / "harness"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HARNESS / "sandbox.py", dst / "sandbox.py")
    return w


def inside_py(work: Path, code: str) -> subprocess.CompletedProcess:
    """Run a Python snippet inside the sandbox, through the guard."""
    return SB.run(["/usr/bin/python3", "-I", "-B", "-c", code], work, timeout=120)


def listing(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*")}


# ------------------------------------------------------------------------------------ 1. the study path
def test_1_study_path_write_lands_in_work_study(work):
    before = listing(work)
    p = inside_py(work, f"open({str(SB.PILOT / 'probe.txt')!r}, 'w').write('inside')\n"
                        f"import os; print(sorted(os.listdir({str(SB.PILOT)!r})))")
    assert p.returncode == 0, p.stderr
    assert (work / "study" / "probe.txt").read_text() == "inside"
    assert listing(work) - before == {"study/probe.txt"}, "the write landed somewhere besides WORK/study"
    assert json.loads(p.stdout.strip().replace("'", '"')) == ["probe.txt"]   # the study path IS WORK/study


# ------------------------------------------------------------------------- 2. nothing outside WORK writes
PROBE = "harness_write_probe"
TARGETS = ["/etc", "/usr", "/var/tmp", "/srv/storage_16tb", str(SB.PROJECTS), str(SB.LAWS), str(SB.ENGINE),
           str(SB.WORKTREE), str(SB.WORKTREE / "tools"), str(SB.POOL_REAL), "/nvme-data", str(SB.HOME),
           str(SB.HOME / ".blind"), str(SB.HOME / ".ssh"), str(SB.HOME / ".claude"), str(SB.USER_SITE), "/tmp",
           "/dev", "/run/user/1000", "/var/lib/docker"]


def test_2_writes_outside_work_fail(work):
    code = ("import json, os\nres = {}\n"
            f"for d in {TARGETS!r}:\n"
            f"    p = os.path.join(d, {PROBE!r})\n"
            "    try:\n"
            "        os.makedirs(d, exist_ok=True)\n"
            "        open(p, 'w').write('x'); res[d] = 'WROTE'\n"
            "    except OSError as e:\n"
            "        res[d] = type(e).__name__\n"
            f"open({str(work / 'ok.txt')!r}, 'w').write('ok')\n"
            "print(json.dumps(res))")
    p = inside_py(work, code)
    assert p.returncode == 0, p.stderr
    res = json.loads(p.stdout)
    wrote = [d for d, r in res.items() if r == "WROTE"]
    assert not wrote, f"writes succeeded outside WORK: {wrote}"
    assert (work / "ok.txt").read_text() == "ok"          # WORK itself is writable
    # outside, look only at paths that are not hidden data roots
    for d in ("/etc", "/usr", "/var/tmp", "/srv/storage_16tb", str(SB.WORKTREE), str(SB.WORKTREE / "tools"), "/tmp"):
        assert not os.path.exists(os.path.join(d, PROBE)), d


# -------------------------------------------------------------- 3. hidden data, no network (seen from inside)
def test_3_corpus_blind_pool_hidden_and_no_network(work):
    code = f"""
import json, os, socket
r = {{}}
r['nvme'] = os.listdir('/nvme-data')
r['blind'] = os.path.exists({str(SB.HOME / '.blind')!r})
r['home'] = sorted(os.listdir({str(SB.HOME)!r}))
r['ssh'] = os.path.exists({str(SB.HOME / '.ssh')!r})
r['pool'] = os.path.exists({str(SB.POOL_REAL)!r})
r['laws'] = sorted(os.listdir({str(SB.LAWS)!r}))
r['claude'] = sorted(os.listdir({str(SB.HOME / '.claude')!r})) if os.path.exists({str(SB.HOME / '.claude')!r}) else []
r['worktree'] = os.path.exists({str(SB.WORKTREE)!r})
r['pilot'] = sorted(os.listdir({str(SB.PILOT)!r}))
net = []
for host, port in (('1.1.1.1', 443), ('140.82.112.3', 443), ('192.168.1.1', 80)):
    s = socket.socket(); s.settimeout(3)
    try:
        s.connect((host, port)); net.append('CONNECTED ' + host)
    except OSError as e:
        net.append(type(e).__name__)
    finally:
        s.close()
try:
    socket.getaddrinfo('github.com', 443); net.append('RESOLVED')
except OSError as e:
    net.append(type(e).__name__)
r['net'] = net
r['ifaces'] = [l.split(':')[0].strip() for l in open('/proc/net/dev').readlines()[2:]]
print(json.dumps(r))
"""
    p = inside_py(work, code)
    assert p.returncode == 0, p.stderr
    r = json.loads(p.stdout)
    assert r["nvme"] == [], r["nvme"]
    assert set(r["home"]) <= {".local", ".claude"}, r["home"]                # the home directory is hidden
    assert not r["blind"] and not r["ssh"] and not r["pool"] and not r["worktree"]
    assert r["laws"] == sorted(["pilot", SB.ENGINE.name])        # the rest of laws-study is hidden
    assert r["claude"] == (["jobs"] if str(work).startswith(str(SB.HOME / ".claude")) else [])   # only WORK's path
    assert r["pilot"] == []                                      # a fresh WORK/study, not the real study
    assert not any(x.startswith(("CONNECTED", "RESOLVED")) for x in r["net"]), r["net"]
    assert r["ifaces"] == ["lo"]


# ------------------------------------------------------------------------------ 4. the guard in the runner
def test_4_guard_refuses_outside_the_sandbox(work, tmp_path):
    marker = work / "marker"
    # the CLI guard, outside: the command must not run
    p = subprocess.run([sys.executable, "-B", str(HARNESS / "sandbox.py"), "exec", "--work", str(work), "--",
                        "/usr/bin/touch", str(marker)], capture_output=True, text=True)
    assert p.returncode == 3 and "refused" in p.stderr
    assert not marker.exists()
    # the library guard, outside
    with pytest.raises(SB.SandboxError):
        SB.assert_inside(work)
    # the runner's stage function, called with the sandbox switched off, refuses before running anything
    import run as R
    with pytest.raises(SB.SandboxError):
        R.stage(R.Ctx.for_test(work), "probe", ["/usr/bin/touch", str(marker)], sandboxed=False)
    assert not marker.exists()
    # inside the sandbox the same guard lets the command run
    p = SB.run(["/usr/bin/touch", str(marker)], work, timeout=60)
    assert p.returncode == 0, p.stderr
    assert marker.exists()
    # inside a sandbox built for another WORK, the guard refuses this WORK (its study is not the bound one)
    other = SB.prepare(tmp_path / "other")
    (other / "tree" / "tools" / "harness").mkdir(parents=True)
    shutil.copyfile(HARNESS / "sandbox.py", other / "tree" / "tools" / "harness" / "sandbox.py")
    env = SB.sandbox_env(other)
    argv = SB.bwrap_argv(other, env, other) + ["/usr/bin/python3", "-I", "-B", str(work / "tree/tools/harness/sandbox.py"),
                                                "exec", "--work", str(work), "--", "/usr/bin/true"]
    # `work` is not bound in that sandbox at all, so the guard script itself is unreachable: either way, refused
    p = subprocess.run(argv, capture_output=True, text=True)
    assert p.returncode != 0
    # the WORK check refuses a WORK inside the repository or a data root (string test only: nothing is opened)
    for bad in (SB.WORKTREE / "x", SB.PILOT / "x", Path("/nvme-data/x"), SB.HOME / ".blind" / "x"):
        with pytest.raises(SB.SandboxError):
            SB.check_work(bad)


# -------------------------------------------- 5. one end-to-end run (default profile, both routes, ~20 s)
def _e2e_skip_reason() -> str | None:
    if not Path(SB.BWRAP).exists():
        return "bwrap not installed"
    try:
        if md.version("tree_sitter_language_pack") != "1.20.0":
            return "tree_sitter_language_pack is not 1.20.0 in this interpreter"
    except md.PackageNotFoundError:
        return "tree_sitter_language_pack not installed"
    if not (Path.home() / SB.LINGUIST_SUB / "vendor.yml").is_file():
        return "linguist cache absent (laws_units would fetch it; there is no network in the sandbox)"
    return None


def test_5_end_to_end_small(tmp_path):
    why = _e2e_skip_reason()
    if why:
        pytest.skip(why)
    # whether the engine export is present is decided INSIDE the sandbox (it is under laws-study, which the
    # builder never looks at from outside)
    w = SB.prepare(tmp_path / "probe")
    (w / "tree/tools/harness").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HARNESS / "sandbox.py", w / "tree/tools/harness/sandbox.py")
    p = inside_py(w, f"import os; print(os.path.isdir({str(SB.ENGINE / 'gitgalaxy')!r}))")
    if p.stdout.strip() != "True":
        pytest.skip("engine export not present")
    ctrl = tmp_path / "ctrl"
    subprocess.run([sys.executable, "-B", str(ROOT / "tools/control_repo/generate.py"), "--out", str(ctrl),
                    "--seed", "3", "--years", "10"],
                   check=True, capture_output=True, cwd=str(tmp_path))
    out = tmp_path / "work"
    p = subprocess.run([sys.executable, "-B", str(HARNESS / "run.py"), "--control", str(ctrl), "--work", str(out),
                        "--name", "e2e"], capture_output=True, text=True, timeout=1800)
    assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-3000:]
    table = json.loads((out / "report" / "e2e.json").read_text())
    rows = {r["rule"]: r for r in table["rows"]}
    for r in table["rows"]:                                   # a row is never empty
        assert r["verdict"] in ("agree", "differ", "undecided in the manifest", "not run"), r
        assert r["pipeline"] not in (None, "") and r["manifest"] not in (None, ""), r
    assert table["summary"]["not_run"] == 0, table["summary"]   # both routes ran to the probe
    manifest = json.loads((ctrl / "manifest.json").read_text())
    probe = json.loads((out / "manifest" / "probe.json").read_text())
    assert probe["scan_side"]["snapshot"] == manifest["points"]["snapshot"]["hash"]   # the handed-in snapshot was scanned
    own = json.loads((out / "own" / "probe.json").read_text())
    lift = json.loads((out / "own" / "tree" / "docs" / "mod1" / f"lift_{table['repo']}.json").read_text())
    assert own["scan_side"]["snapshot"] == lift["snapshot"]    # route own scanned the pipeline's own choice
    nest = json.loads((out / "manifest" / "study" / "sa3_nesting" / f"{table['repo']}.json").read_text())
    assert nest["measured"] == len(probe["universe"]) and nest["not_measured"] == 0   # the grammar cache is reachable
    assert len(table["rows"]) == 22                             # Python: 16 rules, the effect row per property
    assert rows["window"]["verdict"] in ("agree", "differ")
    assert "universe" in rows and "HP qualifying commits" in rows
