"""Unit tests for tools/graph_roles.py (tc#171). Stdlib unittest, synthetic DB.

Run: python -m unittest discover -s tests -v
"""
import pathlib
import sqlite3
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import graph_roles as gr

P, C = "parent_sha", "child_sha"


def make_db(snapshots: dict, with_edge_table: bool = True) -> sqlite3.Connection:
    """snapshots: {sha: {"files": {path: (betweenness, pagerank, loc)}, "edges": [(src, dst)]}}.

    popularity / import_count are derived from the edge list, as the engine does.
    """
    con = sqlite3.connect(":memory:")
    con.execute("""CREATE TABLE file_data (id INTEGER PRIMARY KEY AUTOINCREMENT, repo_name TEXT,
        commit_hash TEXT, file_path TEXT, popularity INTEGER, import_count INTEGER,
        betweenness_score REAL, pagerank_score REAL, total_loc INTEGER)""")
    if with_edge_table:
        con.execute("""CREATE TABLE edge_data (id INTEGER PRIMARY KEY AUTOINCREMENT, repo_name TEXT,
            commit_hash TEXT, src_file_id INTEGER, dst_file_id INTEGER,
            edge_kind TEXT DEFAULT 'import')""")
    for sha, snap in snapshots.items():
        edges = snap.get("edges", [])
        ids = {}
        for path, (btw, pr, loc) in snap["files"].items():
            indeg = sum(1 for _, d in edges if d == path)
            outdeg = sum(1 for s, _ in edges if s == path)
            cur = con.execute(
                "INSERT INTO file_data (repo_name, commit_hash, file_path, popularity, import_count,"
                " betweenness_score, pagerank_score, total_loc) VALUES ('r',?,?,?,?,?,?,?)",
                (sha, path, indeg, outdeg, btw, pr, loc))
            ids[path] = cur.lastrowid
        if with_edge_table:
            for s, d in edges:
                con.execute("INSERT INTO edge_data (repo_name, commit_hash, src_file_id, dst_file_id)"
                            " VALUES ('r',?,?,?)", (sha, ids[s], ids[d]))
    return con


# Parent: setup.h is included by everything; core.c is a hub; main.c orchestrates.
PARENT = {
    "files": {
        "setup.h": (0.0, 0.3, 50), "core.c": (0.4, 0.2, 400), "main.c": (0.0, 0.1, 300),
        "a.c": (0.0, 0.05, 100), "b.c": (0.0, 0.05, 100), "old_util.c": (0.0, 0.05, 80),
        "lonely.c": (None, 0.01, 20), "gone.c": (0.0, 0.01, 30),
    },
    "edges": [
        ("core.c", "setup.h"), ("main.c", "setup.h"), ("a.c", "setup.h"), ("b.c", "setup.h"),
        ("old_util.c", "setup.h"), ("gone.c", "setup.h"),
        ("main.c", "core.c"), ("a.c", "core.c"), ("b.c", "core.c"),
        ("main.c", "a.c"), ("main.c", "b.c"), ("main.c", "old_util.c"),
    ],
}
# Child: old_util.c renamed to util.c; gone.c deleted; new.c added and imports core.c
# (an existing hub); a.c drops its core.c import; util.c gains an importer (b.c).
CHILD = {
    "files": {
        "setup.h": (0.0, 0.3, 50), "core.c": (0.4, 0.25, 420), "main.c": (0.0, 0.1, 310),
        "a.c": (0.0, 0.05, 90), "b.c": (0.0, 0.05, 100), "util.c": (0.1, 0.06, 80),
        "lonely.c": (None, 0.01, 20), "new.c": (0.0, 0.01, 40),
    },
    "edges": [
        ("core.c", "setup.h"), ("main.c", "setup.h"), ("a.c", "setup.h"), ("b.c", "setup.h"),
        ("util.c", "setup.h"), ("new.c", "setup.h"),
        ("main.c", "core.c"), ("b.c", "core.c"), ("new.c", "core.c"),
        ("main.c", "a.c"), ("main.c", "b.c"), ("main.c", "util.c"), ("b.c", "util.c"),
    ],
}
RENAMES = {"old_util.c": "util.c"}


class NearestRank(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(gr.nearest_rank([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.9), 9)
        self.assertEqual(gr.nearest_rank([5], 0.9), 5)
        self.assertEqual(gr.nearest_rank([], 0.9), float("inf"))


class Roles(unittest.TestCase):
    def setUp(self):
        self.con = make_db({P: PARENT, C: CHILD})
        self.snap = gr.assign_roles(gr.load_snapshot(self.con, P), pct=0.75)

    def test_roles(self):
        r = self.snap.roles
        # in-degrees: setup.h 6, core.c 3, a/b/old_util 1, others 0 -> p75 cutoff = 1
        self.assertEqual(self.snap.thresholds["in"], 1)
        self.assertEqual(r["setup.h"], "hub")
        # out-degrees 0,0,1,1,1,2,2,5 -> p75 cutoff 2: core.c (out 1) is not an orchestrator
        self.assertEqual(self.snap.thresholds["out"], 2)
        self.assertEqual(r["core.c"], "bridge+hub")
        self.assertIn("orchestrator", r["main.c"].split("+"))
        self.assertEqual(r["lonely.c"], "isolate")  # betweenness None never makes a bridge

    def test_spoke_and_other_at_strict_cutoff(self):
        snap = gr.assign_roles(gr.load_snapshot(self.con, P), pct=0.99)
        # p99: only the top in/out/btw values qualify
        self.assertEqual(snap.roles["setup.h"], "hub")
        self.assertEqual(snap.roles["main.c"], "orchestrator")
        self.assertEqual(snap.roles["core.c"], "bridge")
        self.assertEqual(snap.roles["old_util.c"], "spoke")  # in 1, out 1
        self.assertEqual(snap.roles["gone.c"], "spoke")  # in 0, out 1

    def test_universal(self):
        # 6 files import something: default frac 0.25 -> bar 1.5 (setup.h 6, core.c 3); at 0.75 the bar is 4.5
        self.assertEqual(self.snap.universal, {"setup.h", "core.c"})
        strict = gr.assign_roles(gr.load_snapshot(self.con, P), pct=0.75, universal_frac=0.75)
        self.assertEqual(strict.universal, {"setup.h"})


class Deltas(unittest.TestCase):
    def setUp(self):
        self.con = make_db({P: PARENT, C: CHILD})

    def run_compare(self, renames=RENAMES):
        res = gr.compare(self.con, P, C, renames=renames, pct=0.99)
        return {r["path"]: r for r in res["files"]}, res["summary"]

    def test_rename_join_and_status(self):
        rows, s = self.run_compare()
        self.assertEqual(rows["util.c"]["old_path"], "old_util.c")
        self.assertTrue(rows["util.c"]["renamed"])
        self.assertEqual(rows["util.c"]["status"], "persisted")
        self.assertEqual(rows["gone.c"]["status"], "removed")
        self.assertEqual(rows["new.c"]["status"], "added")
        self.assertNotIn("old_util.c", rows)
        self.assertEqual((s["n_persisted"], s["n_added"], s["n_removed"]), (7, 1, 1))

    def test_edge_diffs_rename_aware(self):
        rows, s = self.run_compare()
        self.assertTrue(s["edges_available"])
        # added: new.c->setup.h, new.c->core.c, b.c->util.c ; removed: gone.c->setup.h, a.c->core.c
        self.assertEqual(s["edges_added"], 3)
        self.assertEqual(s["edges_removed"], 2)
        self.assertEqual(rows["util.c"]["in_edges_added"], 1)
        self.assertEqual(rows["util.c"]["out_edges_added"], 0)  # rename did not re-add util->setup
        self.assertEqual(rows["a.c"]["out_edges_removed"], 1)
        self.assertEqual(rows["core.c"]["d_in"], 0)  # lost a.c, gained new.c

    def test_new_edges_to_hubs(self):
        rows, s = self.run_compare()
        # parent hub at p99 is setup.h only: new.c->setup.h counts, new.c->core.c does not
        self.assertEqual(rows["new.c"]["new_out_edges_to_hubs"], 1)
        self.assertEqual(s["new_edges_to_hubs"], 1)

    def test_without_renames_counts_remove_plus_add(self):
        rows, s = self.run_compare(renames={})
        self.assertEqual(rows["old_util.c"]["status"], "removed")
        self.assertEqual(rows["util.c"]["status"], "added")
        self.assertGreater(s["edges_added"], 3)

    def test_role_transition(self):
        rows, s = self.run_compare()
        u = rows["util.c"]
        self.assertEqual((u["role_before"], u["role_after"]), ("spoke", "other"))
        self.assertTrue(u["role_changed"])
        self.assertEqual(u["transition"], "spoke->other")
        self.assertEqual(s["transitions"].get("spoke->other"), 1)
        self.assertFalse(rows["new.c"]["role_changed"])  # added files never "change"


class DegreeSource(unittest.TestCase):
    """popularity is the engine's stem-resolved tally, not the import graph's in-degree."""

    def skew_popularity(self, con):
        con.execute("UPDATE file_data SET popularity = 99 WHERE file_path = 'a.c'")

    def test_edges_override_columns(self):
        con = make_db({P: PARENT, C: CHILD})
        self.skew_popularity(con)
        snap = gr.load_snapshot(con, P)
        self.assertEqual(snap.degree_source, "edge_data")
        self.assertEqual(snap.nodes["a.c"]["in"], 1)  # main.c -> a.c only
        self.assertEqual(snap.nodes["main.c"]["out"], 5)
        res = gr.compare(con, P, C, renames=RENAMES)
        self.assertEqual(res["summary"]["degree_source"], ["edge_data", "edge_data"])

    def test_columns_without_edges(self):
        con = make_db({P: PARENT, C: CHILD}, with_edge_table=False)
        self.skew_popularity(con)
        snap = gr.load_snapshot(con, P)
        self.assertEqual(snap.degree_source, "file_data")
        self.assertEqual(snap.nodes["a.c"]["in"], 99)

    def test_d_in_matches_edge_diff(self):
        res = gr.compare(make_db({P: PARENT, C: CHILD}), P, C, renames=RENAMES)
        for r in res["files"]:
            if r["status"] == "persisted":
                self.assertEqual(r["d_in"], r["in_edges_added"] - r["in_edges_removed"], r["path"])
                self.assertEqual(r["d_out"], r["out_edges_added"] - r["out_edges_removed"], r["path"])


class NoEdges(unittest.TestCase):
    def test_node_metrics_without_edge_table(self):
        con = make_db({P: PARENT, C: CHILD}, with_edge_table=False)
        res = gr.compare(con, P, C, renames=RENAMES)
        s = res["summary"]
        self.assertFalse(s["edges_available"])
        self.assertIsNone(s["edges_added"])
        row = next(r for r in res["files"] if r["path"] == "core.c")
        self.assertIsNone(row["out_edges_added"])
        self.assertEqual(row["d_in"], 0)

    def test_missing_commit(self):
        con = make_db({P: PARENT})
        self.assertIsNone(gr.compare(con, P, C))


if __name__ == "__main__":
    unittest.main()
