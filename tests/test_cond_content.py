"""Unit tests for tools/cond_content.py (ECOND). Stdlib unittest; skipped when tree-sitter is absent.

Run: python -m unittest tests.test_cond_content -v
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import cond_content as cc
import edit_types as et

try:
    import tree_sitter_language_pack  # noqa: F401
    HAVE_TS = True
except ImportError:
    HAVE_TS = False

BASE = "int f(char *p, int n) { int r = 0; if (n) r = g(p, n); return r; }"


def cols(after: str) -> list:
    fn = lambda src: et.functions_in(src.encode())[0]["f"]
    return cc.cond_features(fn(BASE), fn(after))


class Blind(unittest.TestCase):
    def test_walk_and_report_read_no_outcome(self):
        src = pathlib.Path(cc.__file__).read_text()
        blind = src.split("# ---------------------------------------------------------------------------------------------- join")[0]
        for word in ("etyp_fix", "load_events", "fixlike", "events/"):
            self.assertNotIn(word, blind.split('"""', 2)[2], word)


@unittest.skipUnless(HAVE_TS, "tree-sitter-language-pack not installed")
class Kinds(unittest.TestCase):
    def test_a_new_exiting_if_is_a_guard_with_its_kind(self):
        self.assertEqual(cols(BASE.replace("int r = 0;", "int r = 0; if (!p) return -1;")),
                         ["G:NEGATED", "GUARD_ADD", "NEGATED"])
        self.assertEqual(cols(BASE.replace("int r = 0;", "int r = 0; if (p == NULL) { log(); return -1; }")),
                         ["G:NULL_CMP", "GUARD_ADD", "NULL_CMP"])

    def test_a_new_non_exiting_if_is_an_action(self):
        self.assertEqual(cols(BASE.replace("return r;", "if (n > MAX_N) n = MAX_N; return r;")),
                         ["ACTION_IF_ADD", "REL_CONST"])
        self.assertEqual(cols(BASE.replace("return r;", "if (n < r) r = n; return r;")),
                         ["ACTION_IF_ADD", "REL_VAR"])

    def test_an_edited_condition_is_not_an_added_branch(self):
        self.assertEqual(cols(BASE.replace("if (n)", "if (n > 1)")), ["REL_CONST"])
        self.assertEqual(cols(BASE.replace("if (n)", "if (n && p[0] != 0)")),
                         ["COND_NARROW", "TRUTHY", "ZERO_CMP"])

    def test_a_call_inside_a_leaf_is_flagged(self):
        got = cols(BASE.replace("int r = 0;", 'int r = 0; if (strcmp(p, "x") == 0) goto out;'))
        self.assertEqual(got, ["CALL", "G:CALL", "G:ZERO_CMP", "GUARD_ADD", "ZERO_CMP"])

    def test_an_edited_guard_beside_an_added_action_is_not_an_added_guard(self):
        """Review finding 6: both labels used to fire once the total if count grew."""
        w = lambda body: "int f(int a,int b){ %s return 0; }" % body
        fn = lambda src: et.functions_in(src.encode())[0]["f"]
        got = cc.cond_features(fn(w("if (a) return 1;")), fn(w("if (a > 2) return 1; if (b) g();")))
        self.assertIn("ACTION_IF_ADD", got)
        self.assertNotIn("GUARD_ADD", got)
        got = cc.cond_features(fn(w("if (a) g();")), fn(w("if (!b) return 1; g();")))
        self.assertEqual(got, ["G:NEGATED", "GUARD_ADD", "NEGATED"])

    def test_narrowing_needs_an_old_condition_that_went_away(self):
        w = lambda body: "int f(int a,int b,int n){ %s return 0; }" % body
        fn = lambda src: et.functions_in(src.encode())[0]["f"]
        self.assertIn("COND_NARROW", cc.cond_features(fn(w("if (a && b) g();")), fn(w("if (a && b && n) g();"))))
        self.assertNotIn("COND_NARROW", cc.cond_features(fn(w("if (a) g();")),
                                                         fn(w("if (a) g(); while (a && b) h();"))))

    def test_constant_expressions_null_casts_and_masked_zero_tests(self):
        self.assertEqual(cols(BASE.replace("return r;", "if (n > MAX_N - 1) n = 0; return r;")),
                         ["ACTION_IF_ADD", "REL_CONST"])
        self.assertEqual(cols(BASE.replace("return r;", "if (p == (char *)0) n = 0; return r;")),
                         ["ACTION_IF_ADD", "NULL_CMP"])
        self.assertEqual(cols(BASE.replace("return r;", "if ((n & FLAG) == 0) n = 0; return r;")),
                         ["ACTION_IF_ADD", "BITTEST"])
        self.assertEqual(cols(BASE.replace("return r;", "if (n == r) n = 0; return r;")),
                         ["ACTION_IF_ADD", "VAR_CMP"])

    def test_an_untouched_condition_yields_nothing(self):
        self.assertEqual(cols(BASE.replace("return r;", "r++; return r;")), [])


if __name__ == "__main__":
    unittest.main()
