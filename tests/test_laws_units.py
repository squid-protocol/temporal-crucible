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
