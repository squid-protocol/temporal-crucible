#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Canonical row bytes, the table hash, and the one-file-per-build writer (tables_spec.md "Storage"). Pure.

A row is one JSON object, UTF-8, keys in the schema's column order, no spaces:
  - str   a JSON string. A path that is not valid UTF-8 is held in Python as a str decoded with
          `surrogateescape` (each undecodable byte b is the lone surrogate U+DC00+b); every lone surrogate is
          written as the six-character JSON escape \\udcXX, so the line stays valid UTF-8 and reading it back
          (json.loads, then .encode("utf-8", "surrogateescape")) gives the original bytes.
  - int   a JSON integer; a real with no fractional part is accepted and written as the integer.
  - bool  0 or 1.
  - real  the string of float.hex(); -0.0 is written as 0.0; NaN and infinities are refused (missing is null).
  - None  null.
Rows are sorted by the bytes of their key columns (UTF-8 with surrogateescape), compared column by column; two
rows with the same key are refused. A table defined outside schema.TABLES (the comparison scorer's tables,
tools/compare/tables.py) passes its definition as `spec`; there a key column may also be "int", which sorts as a
number (so position 10 comes after position 2). Tables of schema.TABLES have string keys only, so their bytes and
hashes are what they were. The hash is SHA-256 over the rows' bytes, each followed by a newline, which
is also exactly the file's content.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import schema as S

_SURR = re.compile("[\ud800-\udfff]")


class CanonError(ValueError):
    pass


def jstr(s: str) -> str:
    out = json.dumps(s, ensure_ascii=False)
    return _SURR.sub(lambda m: "\\u%04x" % ord(m.group(0)), out)


def value(typ: str, v, where: str = "") -> str:
    if v is None:
        return "null"
    if typ == "str":
        if not isinstance(v, str):
            raise CanonError(f"{where}: {v!r} is not a string")
        return jstr(v)
    if typ == "bool":
        if isinstance(v, (bool, int, float)) and v in (0, 1):
            return "1" if v else "0"
        raise CanonError(f"{where}: {v!r} is not 0/1")
    if typ == "int":
        if isinstance(v, bool):
            return "1" if v else "0"
        if isinstance(v, float):
            if not v.is_integer():
                raise CanonError(f"{where}: {v!r} is not a whole number")
            v = int(v)
        if not isinstance(v, int):
            raise CanonError(f"{where}: {v!r} is not an integer")
        return str(v)
    if typ == "real":
        if isinstance(v, str) or not isinstance(v, (int, float)):
            raise CanonError(f"{where}: {v!r} is not a number")
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            raise CanonError(f"{where}: {v!r} is not finite (write a missing value as null)")
        if f == 0.0:
            f = 0.0                                   # -0.0 and 0.0 are one value
        return jstr(f.hex())
    raise CanonError(f"{where}: unknown type {typ}")


def _def(table: str, spec: dict | None) -> dict:
    return S.TABLES[table] if spec is None else spec


def row_bytes(table: str, row: dict, spec: dict | None = None) -> bytes:
    t_ = _def(table, spec)
    cols = t_["columns"]
    names = [c for c, _ in cols]
    if set(row) != set(names):
        raise CanonError(f"{table}: row columns {sorted(row)} are not the schema's {names}")
    for k in t_["key"]:
        if row[k] is None:
            raise CanonError(f"{table}: key column {k} is null in {row!r}")
    return ("{" + ",".join(f"{jstr(c)}:{value(t, row[c], f'{table}.{c}')}" for c, t in cols) + "}").encode("utf-8")


def _key_part(table: str, k: str, typ: str, v):
    if typ == "int":                                  # a whole-number key sorts as a number
        if isinstance(v, bool) or not isinstance(v, int):
            raise CanonError(f"{table}: key column {k} is not an integer")
        return v
    return v.encode("utf-8", "surrogateescape")


def key_of(table: str, row: dict, spec: dict | None = None) -> tuple:
    t_ = _def(table, spec)
    if spec is None:                                  # schema.TABLES: every key column is a string
        return tuple(row[k].encode("utf-8", "surrogateescape") for k in t_["key"])
    types = dict(t_["columns"])
    return tuple(_key_part(table, k, types[k], row[k]) for k in t_["key"])


def table_bytes(table: str, rows, spec: dict | None = None) -> bytes:
    rows = list(rows)
    keyed = sorted(((key_of(table, r, spec), row_bytes(table, r, spec)) for r in rows), key=lambda kv: kv[0])
    for (a, _), (b, _) in zip(keyed, keyed[1:]):
        if a == b:
            raise CanonError(f"{table}: two rows with key "
                             f"{tuple(x.decode('utf-8', 'surrogateescape') if isinstance(x, bytes) else x for x in a)}")
    return b"".join(rb + b"\n" for _, rb in keyed)


def table_hash(table: str, rows, spec: dict | None = None) -> str:
    return hashlib.sha256(table_bytes(table, rows, spec)).hexdigest()


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_bytes().decode("utf-8").splitlines() if line]


def write_table(out_dir: Path, table: str, rows, spec: dict | None = None) -> dict:
    """Write `<table>.<first 16 hex of the hash>.jsonl` (under protected/ for a protected table). A file of that
    name that already exists is never written over: identical content is accepted, anything else refused."""
    t_ = _def(table, spec)
    data = table_bytes(table, rows, spec)
    h = hashlib.sha256(data).hexdigest()
    d = Path(out_dir) / ("protected" if t_["protected"] else "")
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{table}.{h[:16]}.jsonl"
    if f.exists():
        if f.read_bytes() != data:
            raise CanonError(f"{f} exists with other content; refused to write over it")
    else:
        tmp = f.with_name(f.name + ".partial")
        tmp.write_bytes(data)
        tmp.rename(f)
    return {"file": str(f.relative_to(out_dir)), "hash": h, "rows": data.count(b"\n"),
            "schema_version": t_["version"], "protected": t_["protected"]}
