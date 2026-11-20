#!/bin/bash
# Runs the final analysis in order on ONE input snapshot. Read-only on speed/, evo/, gh/, dbs/. Exit 0 when all five scripts succeed
# (even if refinement is partial); stops at the first failing script and exits 1 (previous outputs are deleted first, so report.py never sees stale JSON).
cd "$(dirname "$0")" || exit 1
export OMP_NUM_THREADS=1
OUT=${FINAL_OUT:-$(pwd)/out}; export FINAL_OUT=$OUT
mkdir -p "$OUT/figures"
rm -f "$OUT"/*.md "$OUT"/*.json "$OUT"/*.csv "$OUT"/*.err "$OUT"/figures/*.png
export FINAL_SNAP_DIR="$OUT/snapshot"
nice -n 19 /usr/bin/python3 -c "import common; common.take_snapshot('$FINAL_SNAP_DIR'); print('snapshot', common.snapshot_hash())" || { echo "snapshot: FAILED"; exit 1; }
for s in steps_table mechanisms persistence figures report; do
  msg=$(nice -n 19 /usr/bin/python3 $s.py 2>"$OUT/$s.err"); rc=$?
  if [ $rc -ne 0 ]; then echo "$s: FAILED rc=$rc (see $OUT/$s.err)"; tail -3 "$OUT/$s.err"; exit 1; fi
  echo "$s: $(echo "$msg" | tail -1)"; rm -f "$OUT/$s.err"
done
exit 0
