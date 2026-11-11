# COM-H3 instrument check: `dead_code` over the fix-event panel (EXPLORATORY)

**Status: exploratory, instrument check, no hypothesis.** Wave A (`docs/comment_wave_a.md`, COM-E3) found the C-family `dead_code` rule (`state_graveyard`) about 4% precise on one curl snapshot; gitgalaxy#8255 gave its keyword arm a code shape. This re-measures it over every C/C++ file version touched by a fix event (`chg_eval.fix_events`, parent commit; tests/docs/fuzz/scripts excluded) in curl, openssl, harfbuzz, ndpi, libarchive. No fix class is read or reported. Script: `tools/dead_code_panel.py`.

- events 25,268; distinct file blobs scanned 46,829; scan failures 0

## Matches before and after #8255

| repo | blobs | matches (old rule) | matches (fixed rule) | distinct comments (old) | distinct (fixed) |
|---|---:|---:|---:|---:|---:|
| curl | 14,646 | 6,844 | 4,299 | 201 | 115 |
| openssl | 18,342 | 5,858 | 5,353 | 367 | 319 |
| harfbuzz | 7,252 | 694 | 648 | 113 | 108 |
| ndpi | 2,745 | 10,236 | 10,038 | 455 | 444 |
| libarchive | 3,844 | 1,157 | 1,157 | 91 | 91 |
| all | 46,829 | 24,789 | 21,495 | 1,227 | 1,077 |

A distinct comment is one (repo, file path, comment text); the same comment in many versions of a file counts once. Precision is estimated over distinct comments.

## Precision of the fixed rule (hand-judged random sample, seed 2982)

| repo | judged | code | proto | annotation | example | prose | dead-code precision (code + proto) [95% Wilson] | strict (code only) |
|---|---:|---:|---:|---:|---:|---:|---|---|
| curl | 40 | 28 | 4 | 8 | 0 | 0 | **80%** [65%, 90%] | 70% |
| openssl | 40 | 32 | 4 | 2 | 0 | 2 | **90%** [77%, 96%] | 80% |
| harfbuzz | 40 | 39 | 0 | 1 | 0 | 0 | **98%** [87%, 100%] | 98% |
| ndpi | 40 | 37 | 2 | 1 | 0 | 0 | **98%** [87%, 100%] | 92% |
| libarchive | 40 | 40 | 0 | 0 | 0 | 0 | **100%** [91%, 100%] | 100% |
| pooled sample | 200 | 176 | 10 | 12 | 0 | 2 | **93%** [89%, 96%] | 88% |

- Panel-wide estimate (each repo's precision weighted by its distinct fixed-rule comments): **94%** dead-code, 88% strict.
- Labels: `code` commented-out statement / declaration / control line; `proto` commented-out prototype or declaration note (dead code by Wave A's definition); `annotation` code text used as an end-of-block or else-branch label; `example` code shown on purpose in a doc or usage comment; `prose` natural language. The labelled sheet is `docs/dead_code_panel_sheet.tsv`.

## Fixed-rule matches judged not dead code

- curl `lib/ftp.c`:2736 (annotation): `/* if(ftpcode) */`
- curl `lib/highlevel.c`:522 (annotation): `/* if (! header and data to read ) */`
- curl `lib/highlevel.c`:523 (annotation): `/* if( read from socket ) */`
- curl `lib/netrc.c`:169 (annotation): `/* while (tok) */`
- curl `lib/transfer.c`:507 (annotation): `/* if (! header and data to read ) */`
- curl `lib/transfer.c`:665 (annotation): `/* if(! header and data to read ) */`
- curl `lib/transfer.c`:2698 (annotation): `/* if(k->getheader || !data->set.opt_no_body) */`
- curl `src/tool_getparam.c`:2968 (annotation): `/* if(ARGTYPE(a->desc) == ARG_STRG) */`
- openssl `crypto/rsa/rsa_sp800_56b_check.c`:221 (prose): `/* return LCM(p-1, q-1) */`
- openssl `crypto/x509/x509name.c`:206 (annotation): `/* if (set >= 0) */`
- openssl `ssl/quic/qlog.c`:114 (prose): `/* strlen("client" / "server"); strlen(".sqlog"); _; separator; _; NUL */`
- openssl `ssl/ssl_asn1.c`:426 (annotation): `/* if (ssl_version>>8 == SSL2_VERSION_MAJOR) */`
- harfbuzz `src/OT/Layout/GPOS.hh`:101 (annotation): `/*if (type & GPOS_impl::ATTACH_TYPE_MARK)*/`
- ndpi `src/lib/third_party/src/ndpi_patricia.c`:78 (annotation): `/* if(family == AF_MAC) */`

## Reading

- **The fixed rule is usable for COM-H3.** About 93% of sampled distinct matches are commented-out code or
  prototype notes, and every repo is at 80% or above. Wave A's 4% was a curl artefact: curl annotates `#include`s
  with `/* for foo() */`. That pattern is gone after #8255, and it barely exists elsewhere.
- **#8255 changed panel-wide counts only modestly** (matches −13%, distinct comments −12%). Outside curl's include
  notes, most matches were already real commented-out code.
- **The remaining false positives are one pattern: block labels.** These are `} /* if(ftpcode) */` and
  `else /* if(x) */`: code text used to label a branch, 12 of 200 (8 in curl). There is a narrow engine follow-up:
  skip a match whose comment opens right after `}` or `else` on the same line.
- **What COM-H3 would count is mostly disabled statements and debug output.** About a third of the real dead code in
  the sample (59 of 176) is commented-out `printf` / `DEBUG` / `qDebug` tracing. A COM-H3 registration should say
  whether that counts, or report it separately.
- **Scope caveat.** The `tests/` exclusion is root-level only. libarchive keeps its tests in `libarchive/test/`, so
  23 of its 40 sampled rows are commented-out test asserts (262 of 21,495 panel matches). COM-H3 should exclude
  `*/test/` paths.
- **COM-H3 does not need re-scans.** The quarterly scan DBs predate #8200, so `state_graveyard` is 0 at function
  grain there. But this check shows the rule can run directly on git blobs (Prism positional stream + the engine
  rule), as DC and DCS do for comments, in under a minute for the whole panel.
