"""LAWS networks: nodes, identities, confident edges and exclusions, on a hand-built laws_build database."""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_net as N  # noqa: E402
import laws_units as U  # noqa: E402

SCHEMA = ["CREATE TABLE walk (boundary TEXT PRIMARY KEY, commit_hash TEXT, ref TEXT, date TEXT)",
          "CREATE TABLE snap (commit_hash TEXT, ref TEXT, date TEXT, boundary TEXT, rc INTEGER, engine TEXT, scanned_at TEXT)",
          "CREATE TABLE file (id INTEGER PRIMARY KEY, commit_hash TEXT, path TEXT, language TEXT, total_loc INTEGER, coding_loc INTEGER, generated INTEGER)",
          "CREATE TABLE attrs (commit_hash TEXT, path TEXT, text TEXT)",
          "CREATE TABLE func (id INTEGER PRIMARY KEY, commit_hash TEXT, file_id INTEGER, name TEXT, start_line INTEGER, loc INTEGER, class_name TEXT, n_calls_out INTEGER, signature TEXT)",
          "CREATE TABLE edge (commit_hash TEXT, src INTEGER, dst INTEGER, step TEXT, kind TEXT)",
          "CREATE TABLE unresolved (commit_hash TEXT, step TEXT, kind TEXT, n INTEGER)"]


@pytest.fixture
def con():
    try:
        U.Excluder()
    except OSError as e:
        pytest.skip(f"linguist lists not available: {e}")
    c = sqlite3.connect(":memory:")
    for s in SCHEMA:
        c.execute(s)
    c.executemany("INSERT INTO snap VALUES (?, 'r', ?, ?, ?, 'e', 't')",
                  [("s1", "2020-09-30", "2020-10-01T00:00:00+00:00", 0), ("s2", "2021-06-30", "2021-07-01T00:00:00+00:00", 0),
                   ("bad", "2021-09-30", "2021-10-01T00:00:00+00:00", 1)])
    c.executemany("INSERT INTO walk VALUES (?, ?, 'r', ?)",
                  [("2020-10-01T00:00:00+00:00", "s1", "2020-09-30"), ("2021-01-01T00:00:00+00:00", "s1", "2020-09-30"),
                   ("2021-07-01T00:00:00+00:00", "s2", "2021-06-30"), ("2021-10-01T00:00:00+00:00", "bad", "2021-09-30"),
                   ("2022-10-01T00:00:00+00:00", "s2", "2021-06-30")])
    files = [(1, "src/a.go", 0), (2, "src/b.go", 0), (3, "src/a_test.go", 0), (4, "vendor/x/v.go", 0), (5, "src/gen.go", 1),
             (6, "src/tool.py", 0), (7, "internal/own.go", 0)]
    c.executemany("INSERT INTO file VALUES (?, 's1', ?, 'go', 10, 10, ?)", files)
    c.execute("INSERT INTO attrs VALUES ('s1', '.gitattributes', 'internal/own.go linguist-generated\n')")
    funcs = [(1, 1, "Run", 10, None), (2, 1, "String", 5, "A"), (3, 1, "String", 4, "B"), (4, 2, "help", 6, None),
             (5, 2, "tiny", 2, None), (6, 3, "TestRun", 9, None), (7, 4, "Vend", 9, None), (8, 5, "Gen", 9, None),
             (9, 6, "py", 9, None), (10, 7, "Own", 9, None), (11, 2, "help", 3, None)]
    c.executemany("INSERT INTO func VALUES (?, 's1', ?, ?, 1, ?, ?, 0, '1')", funcs)
    edges = [(1, 4, "file"), (1, 11, "file"), (1, 2, "receiver"), (2, 3, "typed"), (4, 4, "file"), (6, 1, "import"),
             (1, 7, "import"), (1, 5, "file"), (4, 11, "unique"), (3, 1, "tie")]
    c.executemany("INSERT INTO edge VALUES ('s1', ?, ?, ?, 'call')", edges)
    c.execute("INSERT INTO edge VALUES ('s1', 2, 1, 'class', 'reference')")
    c.execute("INSERT INTO unresolved VALUES ('s1', 'tie', 'call', 4)")
    return c


def test_nodes_are_unit_functions_of_the_language_by_path_class_and_name(con):
    net = N.network(con, "s1", "2020-09-30", "go")
    assert set(net.nodes) == {("src/a.go", "", "Run"), ("src/a.go", "A", "String"), ("src/a.go", "B", "String"),
                              ("src/b.go", "", "help")}  # tiny (loc 2), the test, vendored, generated and .py are out
    assert net.nodes[("src/b.go", "", "help")] == {"loc": 9, "n": 2, "file": "src/b.go", "test": False}  # two merged
    assert net.profile["functions"] == 5 and net.profile["merged_share"] == 0.2
    assert net.profile["files"] == {"unit": 2, "test": 1, "vendored": 1, "generated": 2}


def test_edges_are_confident_call_links_between_nodes(con):
    net = N.network(con, "s1", "2020-09-30", "go")
    run, help_ = ("src/a.go", "", "Run"), ("src/b.go", "", "help")
    assert net.edges == {(run, help_), (("src/a.go", "A", "String"), ("src/a.go", "B", "String"))}
    # not edges: the receiver and tie links (ambiguous), a self-loop, a link between two merged functions, links to
    # or from files outside the unit set, a `reference`
    assert net.profile["links_confident"] == 3 and net.profile["links_ambiguous_not_used"] == 2
    assert net.profile["links_unresolved"] == 4 and net.in_degree()[help_] == 1


def test_tests_as_callers_adds_their_edges_but_never_makes_them_targets(con):
    net = N.network(con, "s1", "2020-09-30", "go", tests_as_callers=True)
    t = ("src/a_test.go", "", "TestRun")
    assert net.nodes[t]["test"] and (t, ("src/a.go", "", "Run")) in net.edges
    assert not any(d == t for _, d in net.edges)


def test_only_successful_scans_are_snapshots_and_the_yearly_one_is_the_october_boundary(con):
    snaps = N.snapshots(con)
    assert [s[0] for s in snaps] == ["s1", "s1", "s2", "s2"]  # a quiet quarter repeats its commit; the failed scan is out
    assert [(s[0], s[2][:10]) for s in N.yearly(snaps)] == [("s1", "2020-10-01"), ("s2", "2022-10-01")]


def test_overloads_are_separate_nodes_only_in_the_languages_that_overload(con):
    con.execute("INSERT INTO file VALUES (20, 's1', 'src/J.java', 'java', 9, 9, 0)")
    con.executemany("INSERT INTO func VALUES (?, 's1', 20, 'join', 1, 9, 'S', 0, ?)",
                    [(30, '["int[]","char"]'), (31, '["List","char"]'), (32, '["List","char"]')])
    java = N.network(con, "s1", "2020-09-30", "java")
    assert set(java.nodes) == {("src/J.java", "S", 'join(["int[]","char"])'), ("src/J.java", "S", 'join(["List","char"])')}
    assert java.profile["functions"] == 3 and java.profile["merged_share"] == pytest.approx(1 / 3, abs=1e-4)
    go = N.network(con, "s1", "2020-09-30", "go")  # Go does not overload: a signature is not part of who a function is
    assert ("src/a.go", "", "Run") in go.nodes and not any("(" in n[2] for n in go.nodes)
