"""LAWS history: fix labels, bots, renames and merge units, on a small git repository built for the test."""
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_history as HI  # noqa: E402
import laws_units as U  # noqa: E402


def git(repo, *a, author="Ann <ann@x.org>", date="2020-01-01T00:00:00"):
    name, email = author.rsplit(" <", 1)
    env = {"GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email.rstrip(">"), "GIT_COMMITTER_NAME": name,
           "GIT_COMMITTER_EMAIL": email.rstrip(">"), "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date,
           "PATH": "/usr/bin:/bin", "HOME": str(repo)}
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, env=env, check=True).stdout


@pytest.fixture
def repo(tmp_path):
    try:
        U.Excluder()
    except OSError as e:
        pytest.skip(f"linguist lists not available: {e}")
    r = tmp_path / "r"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    day = iter(f"2020-01-{d:02d}T00:00:00" for d in range(1, 29))

    def commit(msg, files, author="Ann <ann@x.org>", rm=()):
        for path, text in files.items():
            (r / path).parent.mkdir(parents=True, exist_ok=True)
            (r / path).write_text(text)
        git(r, "add", "-A")
        for path in rm:
            git(r, "rm", "-q", path)
        git(r, "commit", "-q", "--allow-empty", "-m", msg, author=author, date=next(day))

    body = "package a\n" + "\n".join(f"func f{i}() {{}}" for i in range(30)) + "\n"
    commit("add a and b", {"pkg/a.go": body, "pkg/b.go": body.replace("f", "g"), "README.md": "x"})
    commit("Fix crash in a", {"pkg/a.go": body + "// 1\n"})
    commit("feature: more\n\nFixes #12", {"pkg/b.go": body.replace("f", "g") + "// 1\n"})  # closes an issue of unknown type
    commit("fix typo in the readme", {"README.md": "y"})  # no unit source file
    commit("fix lint", {"pkg/a.go": body + "// 2\n"}, author="dependabot[bot] <bot@x.org>")
    git(r, "mv", "pkg/a.go", "pkg/core.go")
    commit("move a to core", {})
    commit("bug: wrong result after the move", {"pkg/core.go": body + "// 3\n"}, author="Bob <bob@x.org>")
    commit("fix the test", {"pkg/core_test.go": "package a\n"})  # a test file is not a unit
    commit("drop b", {}, rm=("pkg/b.go",))
    commit("b again", {"pkg/b.go": "package a\nfunc z() {}\n"})
    return r


def load(repo, tmp_path):
    db = tmp_path / "h.db"
    meta = HI.harvest(repo, "go", db)
    return meta, sqlite3.connect(db)


def test_fix_labels_follow_the_amended_rules(repo, tmp_path):
    meta, con = load(repo, tmp_path)
    rows = {s: (fix, kw, bot, n) for s, fix, kw, bot, n in con.execute("SELECT subject, fix, keyword, bot, n_units FROM commit_")}
    assert rows["Fix crash in a"] == (1, 1, 0, 1) and rows["bug: wrong result after the move"] == (1, 1, 0, 1)
    assert rows["feature: more"][:2] == (0, 0)  # "Fixes #12" alone is not a fix keyword
    assert rows["fix typo in the readme"] == (0, 1, 0, 0) and rows["fix the test"] == (0, 1, 0, 0)  # no unit file
    assert rows["fix lint"] == (0, 1, 1, 1)  # a bot
    assert meta["fixes"] == 2 and meta["commits"] == 10 and meta["unit"] == "non-merge commit"


def test_a_fix_after_a_rename_belongs_to_the_file_that_was_there_before(repo, tmp_path):
    _, con = load(repo, tmp_path)
    a = con.execute("SELECT file FROM lineage WHERE path = 'pkg/a.go'").fetchone()[0]
    assert [p for (p,) in con.execute("SELECT path FROM lineage WHERE file = ? ORDER BY since", (a,))] == ["pkg/a.go", "pkg/core.go"]
    fixes = con.execute("SELECT COUNT(*) FROM touch t JOIN commit_ c ON c.sha = t.sha WHERE t.file = ? AND c.fix = 1", (a,)).fetchone()[0]
    assert fixes == 2  # the one before the move and the one after


def test_a_path_that_is_deleted_and_added_again_is_a_new_file(repo, tmp_path):
    _, con = load(repo, tmp_path)
    rows = con.execute("SELECT file, since, until FROM lineage WHERE path = 'pkg/b.go' ORDER BY since").fetchall()
    assert len(rows) == 2 and rows[0][0] != rows[1][0] and rows[0][2] is not None and rows[1][2] is None


def test_fixes_keyword_phrases():
    assert HI.is_fix_message("Fix overflow in parser") and HI.is_fix_message("correct a leak\n\nCloses #4")
    assert not HI.is_fix_message("Add retries\n\nFixes #77") and not HI.is_fix_message("Resolves: https://github.com/a/b/issues/9")
    assert not HI.is_fix_message("prefix the names") and HI.is_fix_message("fixes: #5 and fixes the crash")


def test_merges_are_units_only_where_the_repo_merges(repo, tmp_path):
    git(repo, "checkout", "-q", "-b", "topic")
    for i in range(6):
        (repo / "pkg/b.go").write_text(f"package a\nfunc z{i}() {{}}\n")
        git(repo, "commit", "-q", "-am", f"work {i}", date=f"2020-02-{i + 1:02d}T00:00:00")
        git(repo, "checkout", "-q", "main")
        git(repo, "merge", "-q", "--no-ff", "topic", "-m", f"Merge: fix crash {i}", date=f"2020-02-{i + 1:02d}T12:00:00")
        git(repo, "checkout", "-q", "topic")
    git(repo, "checkout", "-q", "main")
    meta, con = load(repo, tmp_path)
    assert meta["merges"] == 6 and meta["merge_share"] >= 0.30 and "merges included" in meta["unit"]
    assert con.execute("SELECT COUNT(*) FROM commit_ WHERE merge = 1 AND fix = 1").fetchone()[0] == 6
    assert con.execute("SELECT COUNT(*) FROM commit_ WHERE subject LIKE 'work %'").fetchone()[0] == 0  # not on the first-parent walk


def test_below_the_merge_threshold_the_commits_inside_a_merged_branch_are_the_units(repo, tmp_path):
    git(repo, "checkout", "-q", "-b", "topic")
    (repo / "pkg/b.go").write_text("package a\nfunc z9() {}\n")
    git(repo, "commit", "-q", "-am", "fix a crash on the branch", date="2020-03-01T00:00:00")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "topic", "-m", "Merge topic", date="2020-03-02T00:00:00")
    meta, con = load(repo, tmp_path)
    assert meta["merges"] == 1 and meta["unit"] == "non-merge commit"
    assert con.execute("SELECT fix FROM commit_ WHERE subject = 'fix a crash on the branch'").fetchone() == (1,)
    assert con.execute("SELECT COUNT(*) FROM commit_ WHERE merge = 1").fetchone()[0] == 0  # merges are not on this walk
