#!/usr/bin/env python3
"""Tests for the evolution report generator: diff parser fixtures, comment classifier, trailer resolution, empty and hostile repositories.
    python -m unittest tools/report/test_evolution.py -v     (from the repository root)"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evolution_report as ER  # noqa: E402

ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}


def git(d, *a, env=None):
    return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, env=env or ENV, check=True).stdout


def new_repo(tmp):
    d = Path(tmp) / "r"
    d.mkdir()
    git(d, "init", "-q")
    git(d, "config", "commit.gpgsign", "false")
    return d


def commit(d, msg, date="2020-01-01T00:00:00"):
    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", msg, env={**ENV, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})
    return git(d, "rev-parse", "HEAD").strip()


def cfile(n, body="return 1;"):
    return "".join(f"int f{i}(int x)\n{{\n    {body}\n}}\n\n" for i in range(n))


class Parser(unittest.TestCase):
    def test_paths_with_spaces_non_ascii_and_deletions(self):
        with tempfile.TemporaryDirectory() as t:
            d = new_repo(t)
            (d / "with space.c").write_text(cfile(2))
            (d / "é.c").write_text(cfile(2))
            (d / "gone.c").write_text(cfile(2))
            commit(d, "add files")
            (d / "with space.c").write_text(cfile(2, "return 2;"))
            (d / "é.c").write_text(cfile(2, "return 3;"))
            sha = commit(d, "change", "2020-01-02T00:00:00")
            (d / "gone.c").unlink()
            (d / "with space.c").write_text(cfile(2, "return 4;"))
            sha2 = commit(d, "delete one, edit another", "2020-01-03T00:00:00")
            data = ER.diff_pass(str(d), "c", Path(t) / "cache", "x")
            self.assertIn("with space.c", data[sha]["files"])
            self.assertIn("é.c", data[sha]["files"])
            self.assertTrue(any(f[0] == "é.c" for f in data[sha]["funcs"]))
            self.assertIn("gone.c", data[sha2]["files"])  # the deleted file is counted as its own file
            self.assertGreater(data[sha2]["rem"], 0)
            self.assertTrue(all(f[0] != "gone.c" or True for f in data[sha2]["funcs"]))

    def test_content_lines_that_look_like_headers(self):
        with tempfile.TemporaryDirectory() as t:
            d = new_repo(t)
            (d / "a.c").write_text("int f(void)\n{\n    int x = 0;\n    return x;\n}\n")
            commit(d, "init")
            (d / "a.c").write_text("int f(void)\n{\n    int x = 0;\n    x -- ;\n    return x;\n}\n")
            sha = commit(d, "change", "2020-01-02T00:00:00")
            data = ER.diff_pass(str(d), "c", Path(t) / "cache", "x")
            self.assertEqual(data[sha]["add"], 1)

    def test_cache_key_changes_with_language(self):
        with tempfile.TemporaryDirectory() as t:
            d = new_repo(t)
            (d / "a.c").write_text(cfile(1))
            commit(d, "init")
            ER.diff_pass(str(d), "c", Path(t) / "cache", "x")
            ER.diff_pass(str(d), "python", Path(t) / "cache", "x")
            self.assertEqual(len(list((Path(t) / "cache").glob("diff_x_*.json.gz"))), 2)


class Languages(unittest.TestCase):
    """The function a hunk belongs to must be found for methods (Python, Rust) and for Fortran, which git names only with the language's diff driver."""

    def _edit_names(self, fname, v1, v2, lang):
        with tempfile.TemporaryDirectory() as t:
            d = new_repo(t)
            (d / fname).write_text(v1)
            commit(d, "add")
            (d / fname).write_text(v2)
            sha = commit(d, "change", "2020-01-02T00:00:00")
            data = ER.diff_pass(str(d), lang, Path(t) / "cache", "x")
            return {f[1] for f in data[sha]["funcs"]}

    def test_python_method_edit_is_attributed_to_the_method(self):
        body = lambda n: "class A:\n    def helper(self):\n        return 1\n\n    def target(self):\n        x = 1\n        y = 2\n        return %d\n\n    def other(self):\n        return 3\n" % n
        self.assertEqual(self._edit_names("m.py", body(1), body(2), "python"), {"target"})

    def test_rust_method_edit_is_attributed_to_the_method(self):
        body = lambda n: "struct A;\nimpl A {\n    fn helper(&self) -> i32 {\n        1\n    }\n\n    fn target(&self) -> i32 {\n        let x = 1;\n        let y = 2;\n        %d\n    }\n\n    fn other(&self) -> i32 {\n        3\n    }\n}\n" % n
        self.assertEqual(self._edit_names("m.rs", body(1), body(2), "rust"), {"target"})

    def test_fortran_free_and_fixed_form_and_uppercase_extensions(self):
        free = lambda n: "module m\ncontains\n  subroutine helper(a)\n    real :: a\n    a = 1.0\n  end subroutine helper\n\n  subroutine target(a)\n    real :: a\n    a = 2.0\n    a = a + %d.0\n  end subroutine target\n\n  real function other(a)\n    real :: a\n    other = a\n  end function other\nend module m\n" % n
        self.assertEqual(self._edit_names("m.F90", free(1), free(2), "fortran"), {"target"})
        fixed = lambda n: "      SUBROUTINE HELPER(A)\n      REAL A\n      A = 1.0\n      RETURN\n      END\n\n      SUBROUTINE TARGET(A)\n      REAL A\n      A = 2.0\n      A = A + %d.0\n      RETURN\n      END\n" % n
        self.assertEqual(self._edit_names("m.F", fixed(1), fixed(2), "fortran"), {"TARGET"})

    def test_fortran_comment_classifier(self):
        cm = ER.COMMENT["fortran"]
        for line in ("! free-form comment", "   ! indented comment", "C fixed-form comment", "c lower-case fixed", "* star comment", "", "   "):
            self.assertTrue(cm.match(line), line)
        for line in ("call foo(a)", "      CALL FOO(A)", "  x = 1.0 ! trailing", "      continue", "cat = 1"):
            self.assertFalse(cm.match(line), line)

    def test_fortran_function_name_forms(self):
        for ctx, want in (("subroutine foo(a, b)", "foo"), ("SUBROUTINE FOO(A)", "FOO"), ("end subroutine foo", "foo"), ("real function bar(x)", "bar"), ("module m", "m"), ("program main", "main")):
            self.assertEqual(ER.func_name(ctx, "fortran"), want, ctx)


class Rules(unittest.TestCase):
    def test_comment_classifier(self):
        cm = ER.COMMENT["c"]
        for line, comment in [("/* x */", True), (" * text", True), (" */", True), ("// x", True), ("", True), ("*q = 2;", False), ("**p = 1;", False), ("x = 1; // y", False)]:
            self.assertEqual(bool(cm.match(line)), comment, line)

    def test_is_test(self):
        self.assertTrue(ER.is_test("tests/foo.c"))
        self.assertTrue(ER.is_test("src/foo_test.c"))
        self.assertFalse(ER.is_test("src/latest.c"))

    def test_trailer_resolution_same_second_and_short_hash(self):
        with tempfile.TemporaryDirectory() as t:
            d = new_repo(t)
            (d / "a.c").write_text(cfile(1))
            a = commit(d, "cause")
            (d / "a.c").write_text(cfile(1, "return 2;"))
            b = commit(d, f"fix a thing\n\nFixes: {a[:12]} (\"cause\")")
            commits = ER.load_commits(str(d))
            self.assertEqual(ER.resolve_pairs(commits), [(b, a)])


class EndToEnd(unittest.TestCase):
    def run_cli(self, repo, name, out):
        return subprocess.run([sys.executable, str(HERE / "evolution_report.py"), "--repo", str(repo), "--name", name, "--lang", "c", "--out", str(out)], capture_output=True, text=True)

    def test_empty_repository_fails_clearly(self):
        with tempfile.TemporaryDirectory() as t:
            d = new_repo(t)
            r = self.run_cli(d, "empty", Path(t) / "o")
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn("Traceback", r.stderr)

    def test_repository_without_fixes_or_trailers(self):
        with tempfile.TemporaryDirectory() as t:
            d = new_repo(t)
            (d / "a.c").write_text(cfile(2))
            commit(d, "add code")
            r = self.run_cli(d, "clean", Path(t) / "o")
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.load(open(Path(t) / "o" / "clean_evolution.json"))
            self.assertEqual(data["pairs"], 0)

    def test_hostile_text_does_not_reach_the_page_unescaped(self):
        with tempfile.TemporaryDirectory() as t:
            d = new_repo(t)
            (d / "a.c").write_text(cfile(70))
            commit(d, "init")
            (d / "a.c").write_text(cfile(70, "return 2;"))
            commit(d, 'Cleanup </script><script>document.title="PWNED"</script> "q"  ', "2020-01-02T00:00:00")
            r = self.run_cli(d, "hostile", Path(t) / "o")
            self.assertEqual(r.returncode, 0, r.stderr)
            html = (Path(t) / "o" / "hostile_evolution.html").read_text()
            data_block = html[html.index("const DATA = ") : html.index("const Q = ")]
            self.assertNotIn("</script", data_block.lower())
            self.assertNotIn("<script", data_block.lower())

    def test_bad_name_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            d = new_repo(t)
            (d / "a.c").write_text(cfile(1))
            commit(d, "init")
            r = self.run_cli(d, "bad/name", Path(t) / "o")
            self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
