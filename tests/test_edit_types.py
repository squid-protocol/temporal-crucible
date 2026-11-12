"""Unit tests for tools/edit_types.py (ETYP). Stdlib unittest; skipped when tree-sitter is absent.

Run: python -m unittest tests.test_edit_types -v
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import edit_types as et

try:
    import tree_sitter_language_pack  # noqa: F401
    HAVE_TS = True
except ImportError:
    HAVE_TS = False


def labels(before: str, after: str) -> set:
    fa, _ = et.functions_in(before.encode())
    fb, _ = et.functions_in(after.encode())
    return et.classify(et.features(fa["f"]), et.features(fb["f"]))


BASE = "int f(struct s *p, int n) { int r = 0; if (n) r = g(p, n); return r; }"


class Taxonomy(unittest.TestCase):
    def test_every_label_has_one_family_and_priority_covers_them(self):
        self.assertEqual(len(et.LABELS), len(set(et.LABELS)))
        self.assertEqual(set(et.PRIORITY), set(et.FAMILIES))
        self.assertEqual(et.primary({"COMMENT", "CALL_ADD", "BRANCH_ADD"}), "STRUCTURE")
        self.assertEqual(et.primary({"COMMENT"}), "COSMETIC")

    def test_the_tool_reads_no_outcome(self):
        """Outcome-blind by construction: no fix label, event file or commit message is ever read."""
        src = pathlib.Path(et.__file__).read_text()
        for word in ("fixlike", "events/", "EVENTS_DIR", "%s", "%B", "--grep"):
            self.assertNotIn(word, src.split('"""', 2)[2], word)


@unittest.skipUnless(HAVE_TS, "tree-sitter-language-pack not installed")
class Classify(unittest.TestCase):
    def test_whitespace_and_comment_only(self):
        self.assertEqual(labels(BASE, BASE.replace("{ int", "{\n  int")), {"FORMAT"})
        self.assertEqual(labels(BASE, BASE.replace("return r;", "/* done */ return r;")), {"COMMENT"})

    def test_local_rename_is_naming_but_a_callee_swap_is_wiring(self):
        self.assertEqual(labels(BASE, "int f(struct s *p, int n) { int rc = 0; if (n) rc = g(p, n); return rc; }"), {"RENAME_LOCAL"})
        self.assertEqual(labels(BASE, BASE.replace("g(p, n)", "h(p, n)")), {"CALL_RETARGET"})

    def test_guard_added(self):
        got = labels(BASE, BASE.replace("int r = 0;", "int r = 0; if (!p) return -1;"))
        self.assertTrue({"BRANCH_ADD", "EXIT_CHANGE"} <= got, got)
        self.assertEqual(et.primary(got), "STRUCTURE")

    def test_in_place_edits(self):
        self.assertEqual(labels(BASE, BASE.replace("if (n)", "if (n > 1)")), {"COND_EDIT", "OPERATOR", "NUM_LITERAL"})
        self.assertEqual(labels(BASE, BASE.replace("g(p, n)", "g(p, n, 0)")), {"ARG_ARITY", "NUM_LITERAL"})
        self.assertEqual(labels(BASE, BASE.replace("g(p, n)", "g(p, 4)")), {"ARG_VALUE", "NUM_LITERAL"})
        self.assertEqual(labels(BASE, BASE.replace("int r = 0", "long r = 0")), {"TYPE"})

    def test_token_kind_labels_do_not_fire_as_byproducts_of_an_added_statement(self):
        got = labels(BASE, BASE.replace("return r;", "p->count = n + 1; return r;"))
        self.assertEqual(got, {"STMT_ADD"})

    def test_signature_and_call_units(self):
        self.assertIn("SIGNATURE", labels(BASE, BASE.replace("int n)", "int n, int flags)")))
        self.assertEqual(labels(BASE, BASE.replace("return r;", "log_it(r); return r;")), {"CALL_ADD", "STMT_ADD"})

    def test_a_name_defined_twice_is_skipped_not_guessed(self):
        found, dup = et.functions_in(b"int f(void){return 1;}\nint f(void){return 2;}\nint g(void){return 0;}")
        self.assertEqual(set(found), {"g"})
        self.assertEqual(dup, {"f"})

    def test_classification_is_deterministic(self):
        after = BASE.replace("if (n)", "if (n && p)")
        self.assertEqual(labels(BASE, after), labels(BASE, after))


if __name__ == "__main__":
    unittest.main()
