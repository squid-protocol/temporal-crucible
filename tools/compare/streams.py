#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The named random streams, `PU_named_streams` (docs/process/comparison_scorer_part2_spec.md, Revision 2,
section 3): each use of randomness gets its own generator

    numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence(2982, spawn_key=KEY)))

    a cell's block permutations      KEY = (r, 0, o, p)
    a repo's matched control         KEY = (r, 1)

r: the first 8 bytes of SHA-256 of the repo's name (the marginals row's `repo`, UTF-8), an unsigned big-endian
integer; o: the outcome's index in (HP, HP_allreverts, HP_revert, HP_cve, HP_fixref, KW); p: the predictor's
index in the reference's PREDICTORS order (derive.PREDICTORS, checked against the reference by
tests/test_compare.py test_2e). The bootstrap interval reseeds itself and uses no stream.

`NamedStreams` is part 1's scorer with its one hook, `stream`, returning these generators; nothing else of
part 1 changes. Test vectors are in DECISIONS.md (part 2, 4) and in tests/test_compare_part2.py.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
if "tools_compare__util" not in sys.modules:
    import importlib.util as _iu
    _s = _iu.spec_from_file_location("tools_compare__util", str(HERE / "_util.py"))
    _m = _iu.module_from_spec(_s)
    sys.modules["tools_compare__util"] = _m
    _s.loader.exec_module(_m)
U = sys.modules["tools_compare__util"]
SCO = U.sibling("scorer")
D = U.sibling("derive")

SEED = 2982
OUTCOMES = ("HP", "HP_allreverts", "HP_revert", "HP_cve", "HP_fixref", "KW")
PREDICTOR_ORDER = tuple(D.PREDICTORS)
PERM, CONTROL = 0, 1


def repo_int(name: str) -> int:
    return int.from_bytes(hashlib.sha256(name.encode("utf-8")).digest()[:8], "big")


def spawn_key(key: tuple) -> tuple[int, ...]:
    """the scorer's key -> the SeedSequence spawn key of section 3"""
    if key[0] == "perm":
        _k, repo, oc, p = key
        return (repo_int(repo), PERM, OUTCOMES.index(oc), PREDICTOR_ORDER.index(p))
    if key[0] == "control":
        _k, repo = key
        return (repo_int(repo), CONTROL)
    raise KeyError(key[0])


def generator(sk: tuple[int, ...]) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(SEED, spawn_key=sk)))


class NamedStreams(SCO.Scorer):
    """part 1 with named streams: every cell and every control draws from its own generator"""

    def stream(self, key: tuple, rng):
        return generator(spawn_key(key))


def vectors() -> dict:
    """the test vectors of DECISIONS.md: the first three draws (Generator.random) of two keys, as float.hex"""
    out = {}
    for key in (("perm", "bun", "HP", "struct_branch"), ("control", "bun"), ("perm", "django", "KW", "in_degree")):
        sk = spawn_key(key)
        out[repr(key)] = {"spawn_key": list(sk), "random3": [float(v).hex() for v in generator(sk).random(3)]}
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(vectors(), indent=1))
