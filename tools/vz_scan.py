#!/usr/bin/env python3
"""VZ scans (docs/vz_hypotheses.md): madler/zlib at each fix parent, and each host's vendored zlib path."""
import multiprocessing, pathlib, shutil, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import POOL_DIR  # noqa: E402
from run_batch_parallel import SCAN_ENV  # noqa: E402
BIN = "/srv/storage_16tb/projects/gitgalaxy-worktrees/tc-asof-da852aa54/.venv-tc/bin/galaxyscope-tc"
FIXES = ["eff308af425b67093bab25f80f1ae950166bece", "1eb7682f845ac9e9bf9ae35bbfb3bad5dacbd91d", "5c44459c3b28a9bd3283aaceab7c615f8020c531",
         "6a043145ca6e9c55184013841a67b2fef87e44c0", "9aaec95e82117c1cb0f9624264c3618fc380cecb", "e54e1299404101a5a9d0cf5e45512b543967f958",
         "d1d577490c15a0c6862473d7576352a9f18ef811"]
H = POOL_DIR / "vz_hosts"
HOSTS = {"zlib-ng": H / "zlib-ng", "chromium-zlib": H / "chromium-zlib", "mysql": H / "mysql/extra/zlib/zlib-1.3.2",
         "mongo": H / "mongo/src/third_party/zlib", "assimp": H / "assimp/contrib/zlib",
         "openjdk": H / "openjdk/src/java.base/share/native/libzip/zlib", "qtbase": H / "qtbase/src/3rdparty/zlib",
         "cmake": H / "cmake/Utilities/cmzlib", "rsync": H / "rsync/zlib", "mariadb": H / "mariadb/zlib",
         "godot": H / "godot/thirdparty/zlib", "libgit2": POOL_DIR / "libgit2/deps/zlib"}
OUT = POOL_DIR / "vz_scans"


def scan(task):
    name, src_kind, src = task
    dest = OUT / name
    db = dest / f"{name}_galaxy_master.db"
    if db.exists():
        return name, "done"
    shutil.rmtree(dest, ignore_errors=True)
    tgt = dest / name
    tgt.mkdir(parents=True)
    if src_kind == "git":
        tar = subprocess.run(["git", "-C", str(POOL_DIR / "zlib"), "archive", src], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(tgt)], input=tar, check=True)
    else:
        shutil.copytree(src, tgt, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))
    r = subprocess.run([BIN, str(tgt), "--db-only", "--spec-alignment"], cwd=dest,
                       env={**SCAN_ENV, "GALAXYSCOPE_MAX_WORKERS": "2"}, capture_output=True, text=True)
    dbs = sorted(dest.rglob("*_galaxy_master.db"))
    if dbs:
        dbs[0].rename(db)
    return name, f"rc={r.returncode} db={'yes' if dbs else 'NO'}"


if __name__ == "__main__":
    tasks = [(f"zlib@{f[:9]}^", "git", f + "^") for f in FIXES] + [(n, "dir", p) for n, p in HOSTS.items()]
    with multiprocessing.Pool(4) as p:
        for name, st in p.imap_unordered(scan, tasks):
            print(name, st, flush=True)
