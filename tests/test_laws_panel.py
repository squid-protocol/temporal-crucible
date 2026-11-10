"""LAWS defect panel: file-years, outcomes through renames, prior-year controls and file-graph metrics."""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import laws_history as HI  # noqa: E402
import laws_net as N  # noqa: E402
import laws_panel as P  # noqa: E402
import laws_units as U  # noqa: E402
from test_laws_net import SCHEMA as NET_SCHEMA  # noqa: E402

DAY = 86400
T0 = 1_500_000_000  # a fixed epoch for the first yearly snapshot


def iso(t):
    import datetime as dt
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat()


@pytest.fixture
def dbs(tmp_path):
    try:
        U.Excluder()
    except OSError as e:
        pytest.skip(f"linguist lists not available: {e}")
    net, hist = tmp_path / "net.db", tmp_path / "hist.db"
    c = sqlite3.connect(net)
    for s in NET_SCHEMA:
        c.execute(s)
    files = {"src/a.go": 1, "src/b.go": 2, "src/c.go": 3, "src/d.go": 4}
    for y in range(4):  # yearly snapshots at T0, +1y, +2y, +3y
        sha, t = f"s{y}", T0 + y * 365 * DAY
        c.execute("INSERT INTO walk VALUES (?, ?, 'r', ?)", (f"{2017 + y}-10-01T00:00:00+00:00", sha, iso(t)))
        c.execute("INSERT INTO snap VALUES (?, 'r', ?, ?, 0, 'e', 't')", (sha, iso(t), f"{2017 + y}-10-01T00:00:00+00:00"))
        for path, k in files.items():
            if path == "src/d.go" and y >= 2:
                continue  # d is gone from the third snapshot on
            name = "src/core.go" if path == "src/a.go" and y >= 2 else path  # a is renamed between y1 and y2
            fid = 100 * y + k
            c.execute("INSERT INTO file VALUES (?, ?, ?, 'go', 50, ?, 0)", (fid, sha, name, 40 + k))
            c.executemany("INSERT INTO func VALUES (?, ?, ?, ?, 1, 9, NULL, 0, '0')",
                          [(1000 * y + 10 * k + j, sha, fid, f"f{k}_{j}") for j in range(2)])
        fn = lambda k, j: 1000 * y + 10 * k + j  # noqa: E731
        edges = [(fn(1, 0), fn(2, 0)), (fn(2, 0), fn(1, 0)), (fn(3, 0), fn(2, 0)), (fn(3, 1), fn(2, 0)), (fn(1, 1), fn(1, 0))]
        if y < 2:
            edges.append((fn(4, 0), fn(3, 0)))
        c.executemany("INSERT INTO edge VALUES (?, ?, ?, 'file', 'call')", [(sha, a, b) for a, b in edges])
    c.commit()
    h = sqlite3.connect(hist)
    for s in HI.SCHEMA:
        h.execute(s)
    y1 = T0 + 365 * DAY
    commits = [("c0", T0 - 10 * DAY, "ann", 0, 0), ("c1", y1 - 200 * DAY, "ann", 0, 1), ("c2", y1 - 100 * DAY, "bob", 0, 0),
               ("c3", y1 - 50 * DAY, "bot", 1, 0), ("c4", y1 - 400 * DAY, "cy", 0, 1),  # before the prior year of y1
               ("c5", y1 + 30 * DAY, "ann", 0, 0), ("c6", y1 + 200 * DAY, "ann", 0, 1),  # a fix on a AFTER its rename
               ("c7", y1 + 300 * DAY, "bob", 0, 0),  # deletes d
               ("c8", y1 + 800 * DAY, "ann", 0, 1), ("c9", T0 + 4 * 365 * DAY, "ann", 0, 0)]
    h.executemany("INSERT INTO commit_ VALUES (?, ?, ?, ?, 0, ?, 0, 1, 's')", commits)
    touch = [("c0", 1, "src/a.go"), ("c0", 2, "src/b.go"), ("c0", 3, "src/c.go"), ("c0", 4, "src/d.go"),
             ("c1", 1, "src/a.go"), ("c1", 2, "src/b.go"), ("c2", 1, "src/a.go"), ("c2", 2, "src/b.go"),
             ("c3", 1, "src/a.go"), ("c3", 2, "src/b.go"), ("c4", 1, "src/a.go"),
             ("c5", 1, "src/core.go"), ("c6", 1, "src/core.go"), ("c7", 4, "src/d.go"), ("c8", 3, "src/c.go")]
    h.executemany("INSERT INTO touch VALUES (?, ?, ?, 'M')", touch)
    h.executemany("INSERT INTO lineage VALUES (?, ?, ?, ?)",
                  [(1, "src/a.go", T0 - 10 * DAY, y1 + 30 * DAY), (1, "src/core.go", y1 + 30 * DAY, None),
                   (2, "src/b.go", T0 - 10 * DAY, None), (3, "src/c.go", T0 - 10 * DAY, None),
                   (4, "src/d.go", T0 - 10 * DAY, y1 + 300 * DAY)])
    h.executemany("INSERT INTO meta VALUES (?, ?)", [("last_ct", str(T0 + 4 * 365 * DAY)), ("unit", "non-merge commit")])
    h.commit()
    return net, hist


def test_file_years_start_a_year_in_and_stop_where_the_window_would_run_past_the_labels(dbs):
    rows, s = P.file_years(*dbs, "go")
    assert s["snapshots_yearly"] == 4 and s["snapshots_used"] == 3  # the first snapshot has no prior year
    assert sorted({r["year"] for r in rows}) == [2018, 2019, 2020] and s["rows"] == 4 + 3 + 3


def test_a_fix_after_a_rename_is_the_outcome_of_the_file_under_its_old_name(dbs):
    rows, s = P.file_years(*dbs, "go")
    y1 = {r["path"]: r for r in rows if r["year"] == 2018}
    assert y1["src/a.go"]["outcome"] == 1 and y1["src/a.go"]["fix_commit"] == "c6"  # c6 touched src/core.go
    assert y1["src/b.go"]["outcome"] == 0 and y1["src/c.go"]["outcome"] == 0  # c8 is 800 days later
    assert y1["src/d.go"] == {**y1["src/d.go"], "outcome": 0, "deleted": 1} and s["deleted_in_window"] == 1


def test_controls_count_the_prior_year_without_bots(dbs):
    rows, _ = P.file_years(*dbs, "go")
    a = next(r for r in rows if r["year"] == 2018 and r["path"] == "src/a.go")
    assert (a["churn"], a["prior_fixes"], a["authors"]) == (2, 1, 2)  # c1 and c2; c3 is a bot, c4 is too old
    assert a["coupled"] == 0  # a and b changed together twice (the bot's commit is not counted): below three
    assert a["loc"] == 41 and a["functions"] == 2


def test_file_graph_metrics(dbs):
    con = sqlite3.connect(dbs[0])
    sha, date, _ = N.yearly(N.snapshots(con))[1]
    fg = P.file_graph(N.network(con, sha, date, "go"))
    assert fg["src/b.go"] == {"k_max": 3, "k_mean": 1.5, "callers": 2, "callees": 1, "scc": 2, "functions": 2}
    assert fg["src/a.go"]["scc"] == 2 and fg["src/c.go"]["scc"] == 1 and fg["src/d.go"]["callees"] == 1
    rows, s = P.file_years(*dbs, "go")
    y1 = {r["path"]: r for r in rows if r["year"] == 2018}
    assert y1["src/a.go"]["in_cycle"] == 0 and y1["src/a.go"]["giant"] == 1  # 2 of 4 files: above the 20% cap of 1
