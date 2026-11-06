# KF gate G2 — regex construct counts vs tree-sitter-c (head snapshots)

Per C file (`.c`/`.h`): exposure = count > 0. Agreement = share of files where regex and tree-sitter agree on exposure. Line-level counts are compared too (regex counts matching *lines*; tree-sitter counts *nodes*).

| repo | files | goto exposure agree | goto: regex-only / ts-only files | macro exposure agree | macro: regex-only / ts-only files |
|---|---:|---:|---|---:|---|
| ndpi | 431 | 100.00% | 0 / 0 | 100.00% | 0 / 0 |
| openssl | 2173 | 99.86% | 3 / 0 | 99.82% | 4 / 0 |
| curl | 1069 | 99.72% | 3 / 0 | 100.00% | 0 / 0 |
| libxml2 | 156 | 100.00% | 0 / 0 | 100.00% | 0 / 0 |
| libtiff | 148 | 98.65% | 2 / 0 | 100.00% | 0 / 0 |
| libpng | 102 | 98.04% | 2 / 0 | 99.02% | 1 / 0 |
| libexif | 83 | 100.00% | 0 / 0 | 100.00% | 0 / 0 |
| file | 61 | 100.00% | 0 / 0 | 98.36% | 1 / 0 |

**Pooled: goto 99.76%, macro 99.86% → G2 PASS** (gate ≥ 98% each)

Disagreement samples (read in source):

- openssl `crypto/pem/pem_local.h` goto regex-only: `goto legacy;                                                                 \`
- openssl `crypto/x509/v3_ncons.c` macro regex-only: `
#define IA5_OFFSET_LEN(`
- openssl `include/internal/packet.h` goto regex-only: `*      goto err;`
- openssl `providers/baseprov.c` macro regex-only: `#define STORE(`
- openssl `providers/implementations/include/prov/drbg.h` goto regex-only: `goto err;                   \`
- openssl `ssl/ech/ech_local.h` macro regex-only: `#define ECH_SAME_EXT(`
- openssl `ssl/quic/quic_local.h` macro regex-only: `
#define IMPLEMENT_quic_meth_func(`
- curl `lib/vssh/ssh.h` goto regex-only: `sshstate nextstate;         /* the state to goto after stopping */`
- curl `tests/libtest/first.h` goto regex-only: `goto test_cleanup;       \`
- curl `tests/libtest/unitcheck.h` goto regex-only: `goto unit_test_abort;                                           \`
- libtiff `test/test_signed_tags.c` goto regex-only: `b.) goto failure, if any failure is detected, which is not`
- libtiff `test/test_transferfunction_write_read.c` goto regex-only: `goto failure;                                                                             `
- libpng `contrib/tools/checksum-icc.c` macro regex-only: `#     define u16(`
- file `src/seccomp.c` macro regex-only: `
#define DENY_RULE(`
