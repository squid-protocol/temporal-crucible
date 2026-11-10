"""The LAW-9 labels and fix sizes: URL aliasing, the two advisory signals, and sizes over unit source files only."""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_osv as O  # noqa: E402
import laws_units as U  # noqa: E402

FIXED = "a" * 40
OTHER_REPO = "b" * 40
REFERENCED = "c" * 40
WITHDRAWN = "d" * 40


def advisory(aid: str, repo: str | None, fixed: str | None, refs=(), withdrawn=False) -> dict:
    rec = {"id": aid, "schema_version": "1.9.0", "affected": [], "references": list(refs)}
    if withdrawn:
        rec["withdrawn"] = "2026-01-01T00:00:00Z"
    if repo is not None:
        events = [{"introduced": "0"}] + ([{"fixed": fixed}] if fixed else [])
        rec["affected"].append({"ranges": [{"type": "GIT", "repo": repo, "events": events}]})
    return rec


@pytest.fixture
def dump(tmp_path: Path) -> Path:
    z = tmp_path / "GIT.zip"
    records = [
        advisory("CVE-2020-1", "https://gitlab.gnome.org/GNOME/libxml2.git", FIXED),
        advisory("CVE-2020-2", "https://github.com/gnome/libxml2", FIXED),          # an alias names the same fix
        advisory("CVE-2020-3", "https://github.com/somebody/libxml2-fork", OTHER_REPO),  # a fork: not ours
        advisory("CVE-2020-4", None, None, refs=[{"type": "FIX",
                 "url": f"https://gitlab.gnome.org/GNOME/libxml2/-/commit/{REFERENCED}"}]),
        advisory("CVE-2020-5", "https://gitlab.gnome.org/GNOME/libxml2", WITHDRAWN, withdrawn=True),
        advisory("CVE-2020-6", "https://gitlab.gnome.org/GNOME/libxml2", None),     # no fix event yet
        advisory("CVE-2020-7", None, None, refs=[{"type": "WEB",
                 "url": "https://gitlab.gnome.org/GNOME/libxml2/-/commit/" + "e" * 40}]),  # not a FIX reference
    ]
    with zipfile.ZipFile(z, "w") as zf:
        for rec in records:
            zf.writestr(f"{rec['id']}.json", json.dumps(rec))
    return z


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "libxml2"
    (r / "src").mkdir(parents=True)
    (r / "tests").mkdir()
    (r / "doc").mkdir()
    git = lambda *a: subprocess.run(["git", "-C", str(r), *a], check=True, capture_output=True)  # noqa: E731
    subprocess.run(["git", "init", "-q", "-b", "main", str(r)], check=True, capture_output=True)
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "T")
    (r / "src" / "parser.c").write_text("int one(void)\n{\n    return 1;\n}\n\nint two(void)\n{\n    return 2;\n}\n")
    (r / "tests" / "runtest.c").write_text("int main(void) { return 0; }\n")
    (r / "doc" / "README.md").write_text("docs\n")
    git("add", "-A")
    git("commit", "-qm", "initial import")
    (r / "src" / "parser.c").write_text("int one(void)\n{\n    return 11;\n}\n\nint two(void)\n{\n    return 2;\n}\n")
    (r / "tests" / "runtest.c").write_text("int main(void) { return 1; }\n")
    (r / "doc" / "README.md").write_text("docs, fixed\n")
    git("add", "-A")
    git("commit", "-qm", "fix an overflow in the parser")
    return r


def test_url_normalisation_collapses_the_spellings_of_one_repo():
    forms = ["https://GitLab.Gnome.org/GNOME/libxml2.git", "git://gitlab.gnome.org/gnome/libxml2/",
             "git@gitlab.gnome.org:GNOME/libxml2.git", "https://gitlab.gnome.org/GNOME/libxml2?ref=main"]
    assert {O.normalise_url(f) for f in forms} == {"gitlab.gnome.org/gnome/libxml2"}


def test_the_alias_set_is_registered_not_guessed():
    assert O.repo_urls("libxml2") == ("gitlab.gnome.org/gnome/libxml2", "github.com/gnome/libxml2")
    assert "github.com/antirez/redis" in O.repo_urls("redis")  # the historical URL is the same repo
    assert O.repo_urls("libgit2", ("https://github.com/Mirror/libgit2.git",))[-1] == "github.com/mirror/libgit2"
    with pytest.raises(SystemExit, match="no registered OSV URL alias set"):
        O.repo_urls("a-repo-nobody-registered")


def test_labels_take_both_signals_and_nothing_else(dump: Path):
    got = O.labels([dump], O.repo_urls("libxml2"))
    assert set(got) == {FIXED, REFERENCED}                      # the fork, the withdrawn and the WEB ref are out
    assert got[FIXED]["advisories"] == ["CVE-2020-1", "CVE-2020-2"]  # two advisories, one fix commit
    assert got[FIXED]["signals"] == ["git-range"]
    assert got[REFERENCED]["signals"] == ["reference"] and got[REFERENCED]["advisories"] == ["CVE-2020-4"]


def test_resolve_keeps_only_commits_on_the_pinned_branch(repo: Path):
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-b", "side", "HEAD~1"], check=True, capture_output=True)
    (repo / "src" / "other.c").write_text("int three(void) { return 3; }\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "a release-branch fix"], check=True, capture_output=True)
    side = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "main"], check=True, capture_output=True)
    got = O.resolve(repo, [head, head[:10], side, "f" * 40])
    assert got[head] == head and got[head[:10]] == head          # an abbreviation resolves to the full sha
    assert got[side] is None and got["f" * 40] is None           # off the branch, and unknown


def test_fix_size_counts_only_unit_source_files_and_their_functions(repo: Path):
    assert U.language_of("src/parser.c") == "c"
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    size = O.fix_size(repo, head, "c", U.Excluder())
    assert size["files"] == 1          # the test .c file and the doc are not unit source files
    assert size["lines"] == 2          # one line added, one removed, in src/parser.c alone
    assert size["functions"] == 1 and size["hunks"] == 1
    assert O.fix_size(repo, head, "java", U.Excluder()) == {"files": 0, "functions": 0, "lines": 0, "hunks": 0}


def test_a_fix_inside_a_merged_branch_is_attributed_to_its_merge(repo: Path):
    """Where the walk is the first-parent chain, the merge is the walk unit the branch's fix belongs to."""
    git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)  # noqa: E731
    base = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    git("checkout", "-q", "-b", "pr")
    (repo / "src" / "parser.c").write_text("int one(void)\n{\n    return 42;\n}\n")
    git("add", "-A")
    git("commit", "-qm", "fix the overflow properly")
    inner = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    git("checkout", "-q", "main")
    git("merge", "-q", "--no-ff", "-m", "Merge pull request #7", "pr")
    merge = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    assert O.resolve(repo, [inner])[inner] == inner        # it IS an ancestor of HEAD
    assert inner != merge and O.mainline(repo, inner) == merge
    assert O.mainline(repo, base) != base                  # the base is behind the merge, not the merge itself


def test_a_release_branch_fix_is_found_through_its_cherry_pick(repo: Path):
    """OSV names the release-branch commit; the default branch carries a cherry-pick of it under another sha."""
    git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)  # noqa: E731
    git("checkout", "-q", "-b", "release-1.x", "HEAD~1")
    (repo / "src" / "uri.c").write_text("int uri(void)\n{\n    return 7;\n}\n")  # its own file: the pick must apply
    git("add", "-A")
    git("commit", "-qm", "fix CVE-2020-9 on the release branch")
    rel = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    git("checkout", "-q", "main")
    git("cherry-pick", "-x", rel)
    picked = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    assert O.resolve(repo, [rel])[rel] is None             # the release-branch commit is off the default branch
    picks = O.cherry_picks(repo)
    assert picks[rel] == picked and {k[:12]: v for k, v in picks.items()}[rel[:12]] == picked


def test_fix_size_survives_a_diff_that_is_not_utf8(repo: Path):
    """libxml2's history carries latin-1 bytes; a text=True subprocess raised UnicodeDecodeError on them."""
    git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)  # noqa: E731
    (repo / "src" / "enc.c").write_bytes(b"/* \xb7 latin-1 byte */\nint enc(void)\n{\n    return 1;\n}\n")
    git("add", "-A")
    git("commit", "-qm", "fix the encoding table")
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    size = O.fix_size(repo, head, "c", U.Excluder())
    assert size["files"] == 1 and size["lines"] == 5 and size["functions"] >= 1
