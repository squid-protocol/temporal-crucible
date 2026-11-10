"""hunk_grammar._strip_c_comments: blanks orphaned `*` comment-continuation lines, keeps pointer-write code."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
hg = pytest.importorskip("hunk_grammar")  # needs GITGALAXY_PATH (engine checkout)


@pytest.mark.parametrize("line", [
    "*done = TRUE;", "  *size = mb_used*1024;", "*++start = *next;", "*(void **)user = base;",
    "**argv = 0;", "*p++;", "    * factor;",
])
def test_pointer_code_lines_survive(line):
    assert hg._strip_c_comments(line).strip() == line.strip()


@pytest.mark.parametrize("line", [
    " * if the handle is closed, for each easy handle do", " *", " */", "** sqlite style prose",
    "****************************", " *  else return default",
])
def test_orphaned_comment_continuations_are_blanked(line):
    assert hg._strip_c_comments(line).strip() == ""


def test_whole_comments_still_go_via_prism():
    assert hg._strip_c_comments("/* if for while */ x = 1;").strip() == "x = 1;"
