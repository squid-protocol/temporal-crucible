"""LAWS M3: source files per language and the exclusions. Needs linguist's two lists in the cache (fetched on first use)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_units as U  # noqa: E402


@pytest.fixture(scope="module")
def ex():
    try:
        return U.Excluder()
    except OSError as e:  # offline with an empty cache
        pytest.skip(f"linguist lists not available: {e}")


def test_each_language_owns_its_extensions_and_a_header_follows_its_directory():
    assert [U.language_of(p) for p in ("a/b.c", "x.go", "S.java", "m.py", "a.tsx", "P.cs", "l.rs", "k.kts", "i.php")] == [
        "c", "go", "java", "python", "jsts", "csharp", "rust", "kotlin", "php"]
    assert U.language_of("src/db.cc") == "cpp" and U.language_of("README.md") is None
    assert U.language_of("src/db.h") == "c" and U.language_of("src/db.h", {"src": "cpp"}) == "cpp"


@pytest.mark.parametrize("path", ["pkg/store_test.go", "tests/unit/a.py", "lib/test_io.py", "lib/io_test.py",
                                  "src/test/java/org/x/A.java", "core/FooTest.java", "core/FooTests.java",
                                  "web/a.test.ts", "web/a.spec.js", "app/__tests__/b.js", "Testing/x.c"])
def test_test_code_is_recognised(path, ex):
    assert U.is_test(path) and ex.why(path) == "test"


@pytest.mark.parametrize("path", ["src/latest.c", "pkg/contest/run.go", "core/Attestation.java", "lib/testify.py",
                                  "src/main/java/org/x/A.java", "protest/a.rs"])
def test_names_that_only_contain_test_are_units(path, ex):
    assert not U.is_test(path) and ex.why(path) is None


def test_vendored_documentation_generated_and_example_paths_are_excluded(ex):
    assert ex.why("vendor/github.com/x/y.go") == "vendored" and ex.why("third_party/z/a.c") == "vendored"
    assert ex.why("node_modules/left-pad/index.js") == "vendored"
    assert ex.why("docs/conf.py") == "documentation"  # linguist's documentation list is rule (i), before (iv)
    assert ex.why("api/v1/types.pb.go") == "generated" and ex.why("proto/a_pb2.py") == "generated"
    assert ex.why("src/parser.c", generated=True) == "generated" and ex.why("src/parser.c") is None
    assert ex.why("pkg/examples/hello/main.go") == "example" and ex.why("bench/run.rs") == "example"
    assert ex.why("examples/hello/main.go") == "documentation"  # a top-level examples/ is already on linguist's list
    assert U.is_test("x/testdata/in.go") and ex.why("x/testdata/in.go") == "vendored"  # so is testdata/: out either way
    assert ex.why("cmd/server/main.go") is None


def test_gitattributes_of_the_snapshot_add_and_remove_exclusions():
    try:
        ex = U.Excluder({".gitattributes": "# c\nsrc/gen/** linguist-generated\n*.tab.c linguist-generated=true\n"
                                           "extlib/* linguist-vendored\nvendor/ours/** -linguist-vendored\n",
                         "lib/.gitattributes": "big/*.c linguist-vendored\n"})
    except OSError as e:
        pytest.skip(f"linguist lists not available: {e}")
    assert ex.why("src/gen/a/b.c") == "generated" and ex.why("deep/dir/gram.tab.c") == "generated"
    assert ex.why("extlib/z.c") == "vendored" and ex.why("extlib/sub/z.c") is None  # `*` does not cross a directory
    assert ex.why("vendor/ours/a.go") is None and ex.why("vendor/theirs/a.go") == "vendored"  # the repo's own override
    assert ex.why("lib/big/x.c") == "vendored" and ex.why("big/x.c") is None  # relative to its .gitattributes


def test_the_linguist_lists_are_the_pinned_ones(tmp_path, monkeypatch):
    monkeypatch.setenv("LAWS_LINGUIST_DIR", str(tmp_path))
    (tmp_path / "vendor.yml").write_text("- (^|/)vendor/\n")
    with pytest.raises(RuntimeError, match="sha256 differs"):
        U.linguist_patterns("vendor.yml")


def test_sa3_opt_in_tutorial_exclusions_preserve_default_units():
    try:
        ex_default = U.Excluder()
        ex_sa3 = U.Excluder(include_tutorials=True)
    except OSError as e:
        pytest.skip(f"linguist lists not available: {e}")
    assert ex_default.why("tutorials/hist/fillrandom.C") is None
    assert ex_sa3.why("tutorials/hist/fillrandom.C") == "example"
    assert ex_sa3.why("sub/tutorial/demo.py") == "example"


def test_sa3_opt_in_link_extraction_and_cascade_trailer_tiers(tmp_path, monkeypatch):
    import sqlite3
    import hist_meta as HM
    import label_cascade as LC

    msg_jira = ("LANG-1234: Fix NumberUtils overflow", "Fixes LANG-1234 when parsing hex.")
    msg_bpo = ("bpo-41234: fix crash", "Resolves bpo-41234\n\nFixes: 1a2b3c4d5e\nReported-by: Alice <a@b.c>")
    assert [k for _, k, _ in HM.extract_links("s1", *msg_jira, sa3_links=False)] == []
    links_jira = HM.extract_links("s1", *msg_jira, sa3_links=True)
    assert ("s1", "issue_fix", "LANG-1234") in links_jira

    links_bpo_default = HM.extract_links("s2", *msg_bpo, sa3_links=False)
    assert ("s2", "issue_fix", "41234") not in links_bpo_default
    assert ("s2", "trailer:fixes", "1a2b3c4d5e") in links_bpo_default
    links_bpo_sa3 = HM.extract_links("s2", *msg_bpo, sa3_links=True)
    assert ("s2", "issue_fix", "41234") in links_bpo_sa3
    assert ("s2", "issue_fix", "1a2b3c4d5e") in links_bpo_sa3

    # Verify tiers_for routes Fixes:/Bug:/Reported-by: trailers to T5 by default, and T2 under sa3_tiers=True
    (tmp_path / "history").mkdir()
    (tmp_path / "meta").mkdir()
    hdb = sqlite3.connect(tmp_path / "history" / "demo.db")
    hdb.executescript("""
        CREATE TABLE commit_ (sha TEXT, ct INT, author TEXT, bot INT, merge INT, fix INT, subject TEXT);
        CREATE TABLE touch (sha TEXT, path TEXT);
        INSERT INTO commit_ VALUES ('c_fix_trailer', 100, 'a', 0, 0, 0, ' silence warning ');
        INSERT INTO commit_ VALUES ('c_closes_trailer', 101, 'a', 0, 0, 0, ' merge pr ');
    """)
    hdb.commit(); hdb.close()
    mdb = sqlite3.connect(tmp_path / "meta" / "demo.db")
    mdb.executescript("""
        CREATE TABLE link (sha TEXT, kind TEXT, value TEXT);
        INSERT INTO link VALUES ('c_fix_trailer', 'trailer:fixes', 'deadbeef');
        INSERT INTO link VALUES ('c_closes_trailer', 'trailer:closes', '#42');
    """)
    mdb.commit(); mdb.close()
    monkeypatch.setattr(LC, "STUDY", tmp_path)

    tiers_def, _ = LC.tiers_for("demo", sa3_tiers=False)
    assert tiers_def["c_fix_trailer"] == "T5_bareref"
    assert tiers_def["c_closes_trailer"] == "T5_bareref"

    tiers_sa3, _ = LC.tiers_for("demo", sa3_tiers=True)
    assert tiers_sa3["c_fix_trailer"] == "T2_fixref"
    assert tiers_sa3["c_closes_trailer"] == "T5_bareref"
