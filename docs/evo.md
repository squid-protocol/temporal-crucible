# SIG + CPL — the keyword mix and the coupling surface over time (SCORED)

## Part 1 — SIG: the keyword mix over time

| claim | result | verdict |
|---|---|---|
| **SIG-H1** a project has a stable keyword fingerprint (nearest-neighbour, other eras ≥ 5 y away) | accuracy **95.9%** over 390 snapshots (chance 20%) | **SUPPORTED** |
| **SIG-H2** the mix changes in spurts (top-10% quarters' share of drift) | curl 0.75 / ndpi 0.45 / openssl 0.84 / harfbuzz 0.89 / libarchive 0.88 | **SUPPORTED** |
| **SIG-H3** files keep their keyword profile (cosine, t vs t + 1 y) | median **1.000**, lo 1.000 | **SUPPORTED** |

Largest-drift quarters (descriptive):

- **curl 2025-12** (JSD 0.0045): fam_mutation +0.021, fam_memory -0.014 · files: `lib/curlx/strerr.c` (new, Δ130); `lib/strerror.c` (changed, Δ126); `lib/url.c` (changed, Δ115)
- **curl 2025-06** (JSD 0.0039): fam_debt -0.016, fam_guards +0.014 · files: `tests/libtest/Makefile.inc` (changed, Δ862); `lib/vtls/sectransp.c` (gone, Δ793); `lib/vtls/bearssl.c` (gone, Δ334)
- **curl 2001-03** (JSD 0.0020): fam_danger -0.007, fam_guards +0.006 · files: `lib/transfer.c` (new, Δ283); `lib/highlevel.c` (gone, Δ242); `src/hugehelp.c` (gone, Δ140)
- **ndpi 2015-08** (JSD 0.0016): fam_connectivity +0.026, fam_mutation -0.024 · files: `src/lib/ndpi_main.c` (changed, Δ258); `src/lib/protocols/oscar.c` (changed, Δ40); `src/lib/protocols/starcraft.c` (new, Δ29)
- **ndpi 2017-06** (JSD 0.0015): fam_dead_code -0.009, fam_connectivity -0.006 · files: `example/ndpiReader.c` (changed, Δ485); `example/uthash.h` (new, Δ351); `src/lib/protocols/SOMEIP.c` (new, Δ60)
- **ndpi 2017-12** (JSD 0.0014): fam_dead_code -0.016, fam_mutation +0.012 · files: `example/ndpiReader.c` (changed, Δ114); `example/ndpi_util.c` (changed, Δ49); `src/lib/protocols/btlib.c` (changed, Δ46)
- **openssl 1999-06** (JSD 0.0060): fam_connectivity -0.030, fam_dead_code +0.020 · files: `crypto/des/destest.c` (new, Δ378); `apps/sc.c` (gone, Δ295); `crypto/x509/x509.h` (changed, Δ259)
- **openssl 2017-06** (JSD 0.0026): fam_debt -0.012, fam_guards +0.006 · files: `crypto/ec/curve25519.c` (changed, Δ964); `crypto/engine/eng_cryptodev.c` (gone, Δ681); `demos/engines/e_chil.c` (gone, Δ423)
- **openssl 2000-12** (JSD 0.0013): fam_guards +0.023, fam_mutation -0.018 · files: `crypto/ec/ec_point.c` (new, Δ443); `demos/tunala/tunala.c` (new, Δ428); `crypto/rijndael/rd_fst.c` (new, Δ427)
- **harfbuzz 2011-06** (JSD 0.0299): fam_mutation +0.073, fam_connectivity -0.044 · files: `test/test-buffer.c` (new, Δ214); `src/hb-common.h` (changed, Δ214); `src/hb-view.cc` (new, Δ193)
- **harfbuzz 2013-09** (JSD 0.0090): fam_docs +0.022, fam_mutation -0.013 · files: `src/hb-old.cc` (gone, Δ106); `src/hb-font.cc` (changed, Δ101); `src/hb-uniscribe.cc` (changed, Δ95)
- **harfbuzz 2026-03** (JSD 0.0071): fam_mutation +0.036, fam_guards -0.034 · files: `src/hb-raster-paint.cc` (new, Δ985); `src/hb-raster-draw.cc` (new, Δ532); `util/gpu/web/hb-gpu-web-webgpu.cc` (new, Δ505)
- **libarchive 2009-06** (JSD 0.0079): fam_guards +0.028, fam_io -0.021 · files: `libarchive/archive_entry.c` (new, Δ850); `libarchive/archive_read_support_format_tar.c` (new, Δ838); `libarchive/archive_write_disk.c` (new, Δ768)
- **libarchive 2009-03** (JSD 0.0024): fam_mutation +0.037, fam_guards -0.030 · files: `cpio/cpio_windows.c` (new, Δ473); `contrib/untar.c` (new, Δ87); `cpio/test/main.c` (changed, Δ71)
- **libarchive 2011-06** (JSD 0.0010): fam_threat +0.003, fam_guards +0.003 · files: `libarchive/archive_write_disk.c` (gone, Δ929); `libarchive/archive_write_disk_posix.c` (new, Δ876); `libarchive/archive_write_disk_windows.c` (new, Δ830)

## Part 2 — CPL: the coupling surface over time

| claim | median ρ | units in direction | sign-test p | verdict |
|---|---:|---:|---:|---|
| **CPL-H1** coupling centralises with age (ρ time, concentration > 0) | -0.26 | 10/22 | 0.7383 | **not supported** |
| **CPL-H2** coupling's footprint shrinks as a share (ρ time, spread < 0) | -0.22 | 16/23 | 0.0466 | **not supported** |
| **CPL-H3** concentrated coupling → later work touches fewer files (ρ conc, files < 0) | -0.13 | 6/9 | 0.2539 | **not supported** |

| repo | unit | snapshots | ρ(time, conc) | conc first → last | ρ(time, spread) | spread first → last | ρ(conc, files per later commit) (n) |
|---|---|---:|---:|---|---:|---|---|
| curl | openssl | 105 | +0.41 | 0.62 → 0.88 | -0.22 | 13.2% → 2.4% | -0.22 (85) |
| curl | zlib | 49 | +0.67 | 0.74 → 0.81 | -1.00 | 0.6% → 0.3% | +nan (2) |
| curl | libssh2 | 77 | +0.49 | 0.95 → 0.97 | -0.94 | 1.1% → 0.3% | +nan (33) |
| curl | nghttp2 | 32 | -0.56 | 0.89 → 0.66 | +0.08 | 0.6% → 0.5% | +nan (1) |
| curl | c-ares | 62 | +0.85 | 0.33 → 0.44 | -0.86 | 16.0% → 1.1% | -0.30 (29) |
| curl | wolfssl | 17 | +0.39 | 0.86 → 0.84 | +0.04 | 0.8% → 0.7% | +nan (17) |
| curl | mbedtls | 34 | -0.27 | 0.91 → 0.93 | +0.15 | 0.5% → 0.6% | +nan (24) |
| curl | gnutls | 41 | -0.54 | 0.98 → 0.87 | -0.21 | 0.7% → 0.6% | +0.21 (24) |
| curl | platform | 105 | +0.53 | 0.36 → 0.43 | -0.68 | 33.8% → 19.3% | +0.01 (98) |
| libarchive | openssl | 47 | -0.45 | 0.62 → 0.50 | -0.22 | 1.1% → 1.0% | +nan (2) |
| libarchive | zlib | 72 | -0.26 | 0.32 → 0.24 | -0.09 | 2.1% → 2.4% | -0.13 (11) |
| libarchive | bzip2 | 66 | -0.58 | 0.39 → 0.27 | +0.59 | 1.1% → 1.6% | +nan (6) |
| libarchive | xz | 66 | -0.63 | 0.50 → 0.30 | +0.60 | 1.1% → 1.7% | -0.42 (13) |
| libarchive | zstd | 35 | -0.73 | 0.50 → 0.25 | +0.71 | 0.5% → 1.1% | -0.54 (11) |
| libarchive | platform | 72 | -0.36 | 0.28 → 0.43 | -0.28 | 11.1% → 23.6% | -0.09 (52) |
| ndpi | libpcap | 39 | -0.71 | 0.89 → 0.57 | +0.69 | 1.8% → 3.4% | +nan (3) |
| ndpi | platform | 43 | +0.74 | 0.32 → 0.49 | -0.02 | 14.8% → 12.9% | +nan (8) |
| harfbuzz | freetype | 53 | -0.65 | 0.69 → 0.49 | -0.87 | 5.8% → 1.4% | +nan (5) |
| harfbuzz | coretext | 6 | -0.65 | 0.67 → 0.34 | -0.12 | 0.6% → 0.6% | +nan (3) |
| harfbuzz | directwrite | 5 | +0.87 | 0.33 → 0.36 | -0.97 | 1.1% → 0.9% | +nan (2) |
| harfbuzz | graphite | 12 | +nan | 0.57 → 0.57 | -1.00 | 0.6% → 0.5% | +nan (1) |
| harfbuzz | glib | 62 | +0.84 | 0.36 → 0.54 | -0.68 | 7.8% → 13.6% | +nan (8) |
| harfbuzz | platform | 60 | +0.34 | 0.69 → 0.54 | -0.83 | 6.1% → 4.0% | +0.21 (28) |

Runtime 102s · seed 2982. Note: SIG-H3's bootstrap uses 1,000 rounds over snapshot pairs.
