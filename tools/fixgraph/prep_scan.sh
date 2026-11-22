#!/bin/bash
# usage: prep_scan.sh <lang> <name>
S=${FIXGRAPH_WORK:-/tmp/fixgraph-work}
lang=$1; n=$2
rm -rf $S/src/$n; mkdir -p $S/src/$n
(cd $S/repos/$n && git archive HEAD | tar -x -C $S/src/$n)
find $S/src/$n -type d \( -name test -o -name tests -o -name t -o -name testdata -o -name testsuite -o -name fuzz -o -name fuzzers -o -name docs -o -name doc -o -name Documentation -o -name deps -o -name external -o -name vendor -o -name third_party -o -name contrib -o -name examples -o -name ci -o -name benchmark -o -name benchmarks -o -name android -o -name '*-tests' -o -name '*-testlib' -o -name integration-tests \) -prune -exec rm -rf {} + 2>/dev/null
[ "$lang" = Go ] && find $S/src/$n -name '*_test.go' -delete
[ "$lang" = Java ] && find $S/src/$n -type d -path '*/src/test' -prune -exec rm -rf {} + 2>/dev/null
mkdir -p $S/scan2
GITGALAXY_DISABLE_GIT_HISTORY=1 timeout 1500 galaxyscope $S/src/$n --output $S/scan2/$n > $S/scan2/$n.log 2>&1
echo "$lang $n exit=$? $(find $S/src/$n -type f | wc -l) files; $(grep -E 'PIPELINE_SUCCESS' $S/scan2/$n.log | sed 's/.*PIPELINE_SUCCESS: //')" >> $S/ext_scan.txt
