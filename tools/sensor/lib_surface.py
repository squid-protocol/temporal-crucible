#!/usr/bin/env python3
"""Library surface (prototype): which files lean on a library, which of its API names they use, and how that changed between two scans.

    python tools/sensor/lib_surface.py DB                         libraries the repo includes (files, API-looking names)
    python tools/sensor/lib_surface.py DB --lib openssl [--top N] coupled files, most coupled first (where work on the library lands)
    python tools/sensor/lib_surface.py DB_BEFORE DB_AFTER --lib openssl   surface change: API names added/dropped, files newly or no longer coupled

Reads scan databases (file_data.raw_imports, fcall_external, total_loc), read-only. Library profiles are the registered LIB table
(docs/lib_hypotheses.md) converted to scan fields. No risk claim: coupling says where work on the library tends to land, not that it is risky."""
import argparse, collections, json, re, sqlite3, sys

# name -> (include regex on the imported path, API-name regex on the called name)   [registered LIB table, docs/lib_hypotheses.md]
LIBS = {
    "openssl": (r"^openssl/", r"^(?:SSL|SSL_CTX|EVP|X509|BIO|ERR|PEM|RSA|EC_KEY|BN|OPENSSL)_\w+$"),
    "zlib": (r"^zlib\.h$", r"^(?:inflate|deflate)\w*$"),
    "libssh2": (r"^libssh2", r"^libssh2_\w+$"),
    "nghttp2": (r"^nghttp2/", r"^nghttp2_\w+$"),
    "c-ares": (r"^ares\.h$", r"^ares_\w+$"),
    "wolfssl": (r"^wolfssl/", r"^wolfSSL_\w+$"),
    "mbedtls": (r"^mbedtls/", r"^mbedtls_\w+$"),
    "gnutls": (r"^gnutls/", r"^gnutls_\w+$"),
    "libidn2": (r"^idn2\.h$", r"^idn2_\w+$"),
    "bzip2": (r"^bzlib\.h$", r"^BZ2_\w+$"),
    "xz": (r"^lzma\.h$", r"^lzma_\w+$"),
    "zstd": (r"^zstd\.h$", r"^ZSTD_\w+$"),
    "lz4": (r"^lz4", r"^LZ4\w*_\w+$"),
    "libpcap": (r"^pcap", r"^pcap_\w+$"),
    "freetype": (r"^(?:ft2build\.h|freetype/)", r"^FT_\w+$"),
    "icu": (r"^unicode/", r"^(?:u|ubrk|uscript|unorm2?)_\w+$"),
    "coretext": (r"^CoreText", r"^CT\w+$"),
    "uniscribe": (r"^usp10\.h$", r"^Script\w+$"),
    "graphite": (r"^graphite2/", r"^gr_\w+$"),
    "glib": (r"^glib", r"^g_\w+$"),
}
EXTS = (".c", ".h", ".cc", ".hh", ".cpp", ".hpp")

def load(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        files = {r[0]: (r[1], max(r[2] or 0, 1), json.loads(r[3] or "[]")) for r in con.execute("select id,file_path,total_loc,raw_imports from file_data")}
        ext = collections.defaultdict(dict)
        if con.execute("select 1 from sqlite_master where name='fcall_external'").fetchone():
            for fid, callee, n in con.execute("select src_file_id,callee,callers from fcall_external"): ext[fid][callee] = n
        return files, ext
    finally: con.close()

def coupling(db, lib, exts=EXTS):
    inc, api = (re.compile(x) for x in LIBS[lib]); files, ext = load(db); out = {}
    for fid, (path, loc, imports) in files.items():
        if not path.endswith(exts): continue
        incs = [i for i in imports if inc.search(i)]
        names = {c: n for c, n in ext.get(fid, {}).items() if api.search(c)}
        if incs or names:
            sites = len(incs) + sum(names.values())
            out[path] = {"loc": loc, "includes": incs, "names": names, "sites": sites, "density": sites / loc}
    return out

def libraries(db, top=15):
    files, ext = load(db); local = {p.rsplit("/", 1)[-1] for p, _, _ in files.values()}
    cnt = collections.Counter(); fl = collections.defaultdict(set)
    for fid, (path, _, imports) in files.items():
        for i in imports:
            if i.rsplit("/", 1)[-1] in local or i.startswith((".", "..")): continue
            key = i.split("/")[0] if "/" in i else i
            if key.startswith(("sys", "linux", "netinet", "arpa", "bits")) or key in ("stdio.h", "stdlib.h", "string.h", "stdint.h", "errno.h", "limits.h", "time.h", "unistd.h", "ctype.h", "assert.h", "stdarg.h", "stddef.h", "fcntl.h", "signal.h", "stdbool.h", "netdb.h", "poll.h", "inttypes.h", "locale.h", "math.h", "setjmp.h"): continue
            fl[key].add(path)
    return sorted(((k, len(v)) for k, v in fl.items()), key=lambda x: -x[1])[:top]

def diff(a, b, lib):
    ca, cb = coupling(a, lib), coupling(b, lib)
    na = collections.Counter(); nb = collections.Counter()
    for v in ca.values(): na.update(v["names"])
    for v in cb.values(): nb.update(v["names"])
    return {"names_added": sorted(set(nb) - set(na)), "names_dropped": sorted(set(na) - set(nb)),
            "names_more": sorted(((n, na[n], nb[n]) for n in set(na) & set(nb) if nb[n] > na[n]), key=lambda x: x[1] - x[2])[:10],
            "files_newly_coupled": sorted(set(cb) - set(ca)), "files_no_longer_coupled": sorted(set(ca) - set(cb)),
            "files_a": len(ca), "files_b": len(cb), "sites_a": sum(v["sites"] for v in ca.values()), "sites_b": sum(v["sites"] for v in cb.values()),
            "distinct_names_a": len(na), "distinct_names_b": len(nb)}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("db", nargs="+"); ap.add_argument("--lib"); ap.add_argument("--top", type=int, default=10); a = ap.parse_args()
    if a.lib and a.lib not in LIBS: sys.exit(f"unknown library {a.lib}; known: {', '.join(LIBS)}")
    if len(a.db) == 2:
        if not a.lib: sys.exit("--lib is required to diff two scans")
        d = diff(a.db[0], a.db[1], a.lib)
        print(f"SURFACE CHANGE {a.lib}: files {d['files_a']} -> {d['files_b']}, call+include sites {d['sites_a']} -> {d['sites_b']}, distinct API names {d['distinct_names_a']} -> {d['distinct_names_b']}")
        for k in ("names_added", "names_dropped"): print(f"  {k} ({len(d[k])}): " + ", ".join(d[k][:a.top]))
        print(f"  files newly coupled ({len(d['files_newly_coupled'])}): " + ", ".join(d["files_newly_coupled"][:a.top]))
        print(f"  files no longer coupled ({len(d['files_no_longer_coupled'])}): " + ", ".join(d["files_no_longer_coupled"][:a.top]))
    elif a.lib:
        c = coupling(a.db[0], a.lib); rows = sorted(c.items(), key=lambda kv: (-kv[1]["density"], kv[0]))
        print(f"LIBRARY SURFACE {a.lib}: {len(c)} coupled files, {sum(v['sites'] for v in c.values())} sites, {len({n for v in c.values() for n in v['names']})} distinct API names")
        for p, v in rows[:a.top]: print(f"  {p:48s} {v['sites']:4d} sites / {v['loc']:5d} lines = {v['density']:.3f}   {len(v['names'])} names")
    else:
        print("Libraries included by more than one file and not part of this repo (first path component):")
        for k, n in libraries(a.db[0]): print(f"  {k:28s} {n:4d} files" + ("   [profile: " + k + "]" if k in LIBS else ""))
if __name__ == "__main__": main()
