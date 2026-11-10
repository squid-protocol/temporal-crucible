"""The fix-label audit: the prompts come from the committed document, the draw is seeded and disjoint, and
recall is reweighted by the pool sizes rather than read off the sample."""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_audit as A  # noqa: E402


@pytest.fixture
def history(tmp_path: Path) -> Path:
    db = tmp_path / "h.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE commit_ (sha TEXT PRIMARY KEY, ct INTEGER, author TEXT, bot INTEGER, merge INTEGER, "
                "fix INTEGER, keyword INTEGER, n_units INTEGER, subject TEXT)")
    rows = []
    for i in range(400):
        fix = 1 if i < 120 else 0
        rows.append((f"{i:040x}", 1_600_000_000 + i, "a <a@b.c>", 0, 0, fix, fix, 1, f"commit {i}"))
    for i in range(400, 420):  # a bot, and a commit touching no unit source file: neither is drawable
        rows.append((f"{i:040x}", 1_600_000_000 + i, "dependabot[bot] <b@b.c>", 1, 0, 0, 0, 0, "bump"))
    con.executemany("INSERT INTO commit_ VALUES (?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    con.close()
    return db


def test_the_prompts_are_read_from_the_committed_document_with_its_hash():
    p = A.prompts()
    assert len(p["sha256"]) == 64
    assert "BUG FIX" in p["system"] and "JSON only" in p["system"]
    assert "{message}" in p["A"] and "{diff}" in p["A"] and "{files}" in p["A"]
    assert "{files}" not in p["B"] and "{n_files}" not in p["B"]  # rater B sees no file list
    assert "{message}" in p["B"] and "{diff}" in p["B"]


def test_the_prompt_loader_fails_loudly_on_a_missing_heading(tmp_path: Path):
    bad = tmp_path / "laws_audit.md"
    bad.write_text("## Prompt: system\n\n```\nhello\n```\n")
    with pytest.raises(SystemExit, match="rater A user message"):
        A.prompts(bad)


def test_the_draw_is_seeded_disjoint_and_excludes_what_the_rule_could_not_label(history: Path):
    s = A.draw(history, seed=A.SEED)
    assert s["pool_sizes"] == {"fix": 120, "not-fix": 280}  # the bot and no-unit-file commits are not in a pool
    assert {k: len(v) for k, v in s["strata"].items()} == {"fix": 50, "not-fix": 50, "recall": 50}
    assert not set(s["strata"]["not-fix"]) & set(s["strata"]["recall"])  # the recall pool is disjoint
    assert s == A.draw(history, seed=A.SEED)                            # seeded: the same draw twice
    assert A.draw(history, seed=A.SEED + 1)["strata"]["fix"] != s["strata"]["fix"]


def test_a_thin_pool_takes_everything_it_has(history: Path):
    s = A.draw(history, per=200)
    assert len(s["strata"]["fix"]) == 120                 # the whole fix pool, not 200
    assert len(s["strata"]["not-fix"]) + len(s["strata"]["recall"]) == 280


def test_kappa_is_one_on_agreement_and_zero_at_chance():
    assert A.kappa(["fix"] * 10, ["fix"] * 10) != A.kappa(["fix"] * 10, ["fix"] * 10)  # one category: undefined
    a = ["fix", "fix", "not-fix", "not-fix"]
    assert A.kappa(a, a) == pytest.approx(1.0)
    assert A.kappa(a, ["fix", "not-fix", "fix", "not-fix"]) == pytest.approx(0.0)


def labels(precision: float, fn_share: float, n: int = 50) -> dict:
    out = {}
    for stratum, share in (("fix", precision), ("not-fix", 1 - 0.9), ("recall", fn_share)):
        for i in range(n):
            lab = "fix" if i < round(share * n) else "not-fix"
            out[f"{stratum}:{i}"] = {"stratum": stratum, "A": lab, "B": lab}
    return out


def test_recall_is_reweighted_by_the_pool_sizes_not_the_sample():
    # the rule calls 120 commits fixes and 280 not; 90% of its fixes are real, and 10% of the not-fix pool are
    # fixes it missed -> TP = 108, FN = 28, recall = 108 / 136 = 0.794, which no sample share equals
    r = A.rates(labels(0.9, 0.1), {"fix": 120, "not-fix": 280}, "A")
    assert r["precision"] == pytest.approx(0.9)
    assert r["false_negative_share"] == pytest.approx(0.1)
    assert r["recall"] == pytest.approx(108 / 136, abs=1e-3)
    assert r["recall"] != pytest.approx(0.9)  # not the precision, and not 1 - 0.1
    # a bigger not-fix pool holds more missed fixes, so the same shares mean a worse recall
    assert A.rates(labels(0.9, 0.1), {"fix": 120, "not-fix": 2800}, "A")["recall"] < r["recall"]


def test_score_spans_both_raters_and_flags_a_prompt_edited_after_the_labels():
    lab = labels(0.9, 0.1)
    lab["fix:0"]["B"] = "not-fix"  # one disagreement
    for v in lab.values():
        v["prompt_sha256"] = "deadbeef"
    rec = A.score(lab, {"fix": 120, "not-fix": 280}, doc_sha="cafe")
    assert rec["rated_by_both"] == 150 and 0 < rec["kappa"] < 1
    assert rec["precision"]["low"] < rec["precision"]["high"]  # the two raters span an interval
    assert rec["prompt_mismatch"] == ["deadbeef"]
    for v in lab.values():
        v["prompt_sha256"] = "cafe"
    assert A.score(lab, {"fix": 120, "not-fix": 280}, doc_sha="cafe")["prompt_mismatch"] is None
