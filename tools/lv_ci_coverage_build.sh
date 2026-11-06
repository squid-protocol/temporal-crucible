#!/usr/bin/env bash
# LV-H4 CI-coverage recipe (pilot 2026-11-06). Run inside ubuntu:22.04 with the snapshot tree at /src (read-only) and /out writable:
#   git -C <pool>/ndpi archive <sha> | tar -x -C <dir>
#   docker run --rm -v <dir>:/src:ro -v <out>:/out -v $PWD/tools/lv_ci_coverage_build.sh:/build.sh:ro ubuntu:22.04 bash /build.sh
# Writes /out/ci_coverage.json (gcovr per-file summary) and /out/tests.log.
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null && apt-get install -y -qq build-essential autoconf automake libtool pkg-config libpcap-dev libjson-c-dev git gcovr python3 >/dev/null
cp -r /src /work && cd /work
./autogen.sh --with-only-libndpi >/dev/null 2>&1 || ./autogen.sh >/dev/null 2>&1 || true
[ -f Makefile ] || ./configure >/dev/null
make clean >/dev/null 2>&1 || true
./configure CFLAGS="--coverage -O0 -g" LDFLAGS="--coverage" >/dev/null
make -j6 >/dev/null 2>&1
echo BUILD_OK
cd tests && (timeout 1500 ./do.sh > /out/tests.log 2>&1 || timeout 1500 ./do-unit.sh >> /out/tests.log 2>&1 || true)
cd /work && gcovr -r . --json-summary /out/ci_coverage.json --filter src/ >/dev/null 2>&1 && echo GCOV_OK
