"""AIAT-P scorer: the pure functions, the frozen prompt, and the reuse of the registered label rule."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import aiat_eval as ae  # noqa: E402
import fixlike_v2  # noqa: E402


def test_the_prompt_is_frozen_and_hashed():
    # The hash is recorded in every sample and checked before scoring, so a silent prompt edit
    # cannot mix two instruments in one score file. If this test fails the prompt changed:
    # that needs an amendment, not a new expected value.
    assert ae.prompt_sha() == "f80fa47dadb7fdf0f9ed5448944f876c9d16f971b3e5a7293cc860e9c0fc16f2"
    assert "no version history" in ae.PROMPT and "same effort on every file" in ae.PROMPT


def test_frozen_inputs_match_the_registration():
    assert ae.SNAPSHOT["curl"] == "032b15c4342e8eddb51fbe089a9d8ba3ee2070fb"
    assert ae.SNAPSHOT["ndpi"] == "7b43393d8a36cf71b61f582093b1185c4ed0b0b9"
    assert ae.SEED == 2982
    # the auditor's cutoff must precede the 2026-06-01 snapshot; the contrast model is the one
    # whose cutoff does not, and it exists only for AIAT-P3.
    assert ae.AUDITOR_MODEL == "claude-opus-5" and ae.CONTRAST_MODEL != ae.AUDITOR_MODEL


def test_recall_at_budget_counts_positives_inside_a_line_budget():
    # 10 files of 10 lines each: a 20% budget admits 2 files.
    items = [(0.9, 10, 1), (0.8, 10, 1), (0.7, 10, 0)] + [(0.1, 10, 0)] * 7
    assert ae.recall_at_budget(items, 0.20) == 1.0           # both positives ranked top
    flipped = [(0.1, 10, 1), (0.2, 10, 1)] + [(0.9, 10, 0)] * 8
    assert ae.recall_at_budget(flipped, 0.20) == 0.0         # positives ranked last


def test_recall_at_budget_respects_size_a_big_file_eats_the_budget():
    # One 100-line positive cannot fit in a 20%-of-200-lines budget; ten 10-line files can.
    items = [(0.9, 100, 1)] + [(0.5, 10, 0)] * 10
    assert ae.recall_at_budget(items, 0.20) == 0.0
    assert math.isnan(ae.recall_at_budget([], 0.20))
    assert math.isnan(ae.recall_at_budget([(0.5, 10, 0)], 0.20))  # no positives


def test_spearman_handles_monotone_ties_and_short_input():
    assert ae.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert ae.spearman([1, 2, 3, 4], [40, 30, 20, 10]) == -1.0
    assert abs(ae.spearman([1, 1, 2, 2], [5, 5, 9, 9]) - 1.0) < 1e-9   # tied ranks averaged
    assert math.isnan(ae.spearman([1, 2], [2, 1]))                      # n < 3


def test_stratify_spreads_files_over_equal_count_bins():
    locs = {f"f{i}": i for i in range(100)}
    st = ae.stratify(locs, bins=10)
    assert sorted(set(st.values())) == list(range(10))
    assert st["f0"] == 0 and st["f99"] == 9
    assert all(sum(1 for v in st.values() if v == b) == 10 for b in range(10))


def test_draw_sample_is_seeded_and_covers_every_stratum():
    paths = [f"f{i}" for i in range(100)]
    st = ae.stratify({p: int(p[1:]) for p in paths}, bins=10)
    a = ae.draw_sample(paths, st, 30, seed=2982)
    b = ae.draw_sample(paths, st, 30, seed=2982)
    assert a == b and len(a) == 30                       # reproducible
    assert a != ae.draw_sample(paths, st, 30, seed=7)    # and actually seeded
    assert len({st[p] for p in a}) == 10                 # every stratum represented


def test_the_outcome_rule_is_the_registered_one_not_a_copy():
    # v3c's operative rule is the fix word in the SUBJECT. If this module ever grew its own
    # regex, these would diverge; they cannot, because window_fix_files calls drop_reason.
    ev = {"class": fixlike_v2.AUDITED_CLASS, "subject": "add http/3 support", "c_files": ["lib/x.c"]}
    assert fixlike_v2.drop_reason(ev, rules="v3c").startswith("C:")
    ev["subject"] = "fix a crash in the http/3 parser"
    assert fixlike_v2.drop_reason(ev, rules="v3c") is None
    assert "fixlike_v2" in Path(ae.__file__).read_text()


def test_parse_tolerates_prose_around_the_json_and_rejects_junk():
    assert ae._parse('{"p": 0.3, "why": "tricky pointer arithmetic"}')["p"] == 0.3
    assert ae._parse('Here you go:\n{"p": 0.75, "why": "parser"}\nhope that helps')["p"] == 0.75
    assert ae._parse("no json at all") is None
    assert ae._parse('{"why": "missing p"}') is None
    assert ae._parse('{"p": "not a number", "why": "x"}') is None


def test_oversized_files_are_recorded_not_truncated():
    # Truncating would silently change the instrument for exactly the files most likely to be
    # fixed, so the tool records them as oversized and leaves them unscored.
    assert ae.MAX_FILE_BYTES >= 100_000
    assert "never truncated" in Path(ae.__file__).read_text()


# ---------------------------------------------------------------- anonymiser v2 (2026-11-13)
import importlib.util  # noqa: E402

import pytest  # noqa: E402

# Only the anonymiser needs tree-sitter; a module-level importorskip would skip the tests above too.
needs_ts = pytest.mark.skipif(importlib.util.find_spec("tree_sitter_language_pack") is None,
                              reason="tree-sitter-language-pack not installed")

SRC = """#include <stdio.h>
#include <sys/socket.h>
#include <curl/curl.h>
#include "urldata.h"
#define CURL_MAX_LEN (CURLMAX - 1)
#error "upgrade your libcurl"
static struct sockaddr *__CurlISocket = NULL;
int __attribute__((unused)) Curl_go(struct Curl_easy *data) { /* curl */ return strlen(data->name); }
"""


@needs_ts
def test_v1_is_unchanged_and_still_leaks_what_it_leaked():
    out = ae.anonymise(SRC)
    assert out == ae.anonymise(SRC, 1)
    # the leaks v2 closes: <...> includes, #define / #error bodies, and project names starting with __
    assert "<curl/curl.h>" in out and "libcurl" in out and "CURLMAX" in out and "__CurlISocket" in out


@needs_ts
def test_v2_rewrites_project_includes_and_keeps_system_ones():
    out = ae.anonymise(SRC, 2)
    assert "<stdio.h>" in out and "<sys/socket.h>" in out
    assert "<curl/curl.h>" not in out and "<h0.h>" in out
    assert '#include "s"' in out


@needs_ts
def test_v2_reaches_into_macro_bodies_and_project_reserved_names():
    out = ae.anonymise(SRC, 2)
    assert "curl" not in out.lower()
    assert "__attribute__" in out and "strlen" in out and "return" in out
    # one table for code and macro bodies: the same name gets the same token everywhere
    name = ae.anonymise("#define A (CURLMAX - 1)\nint f(void) { return CURLMAX; }\n", 2)
    tokens = [t for t in name.replace("(", " ").replace(")", " ").replace(";", " ").split() if t.startswith("fn")]
    assert len(set(tokens) - {"fn0", "fn1"}) <= 1 and name.count(tokens[-1]) >= 2


def test_score_tags_never_share_a_file():
    class A:
        model, anon, anon_version = "claude-opus-5", False, 0
    a = A()
    assert ae.tag(a) == "claude-opus-5"
    a.anon = True
    assert ae.tag(a) == "claude-opus-5-anon"
    a.anon_version = 2
    assert ae.tag(a) == "claude-opus-5-anon2"
