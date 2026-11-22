#!/bin/bash
# Unit tests, then an end-to-end run on a scratch COPY of the inputs with a fake refined_pass2.jsonl (the real speed/ is only read).
cd "$(dirname "$0")" || exit 1
export OMP_NUM_THREADS=1
nice -n 19 /usr/bin/python3 -m unittest discover -s tests -p 'test_*.py' 2>&1 | tail -15 || exit 1
rc=${PIPESTATUS[0]}
[ $rc -ne 0 ] && { echo "unit tests FAILED"; exit 1; }
S=$(mktemp -d /tmp/final_e2e.XXXXXX); mkdir -p "$S/speed"
for f in dense.jsonl sens.jsonl steps_detected.json refined.jsonl; do cp ../speed/$f "$S/speed/"; done
/usr/bin/python3 - "$S/speed" <<'PY'
import json, sys
d = sys.argv[1]
rows = [json.loads(l) for l in open(d + "/refined.jsonl")]
u = next(r for r in rows if r["class"] == "UNCONFIRMED")
open(d + "/refined_pass2.jsonl", "w").write(json.dumps({**u, "class": "LOCALISED", "dcpu_raw": u["dcpu"], "pass1_class": "UNCONFIRMED", "boundary_rel": 0.5, "down": False}) + "\n")
PY
FINAL_SPEED_DIR="$S/speed" FINAL_OUT="$S/out" ./run_all.sh || { echo "e2e with pass 2 FAILED"; exit 1; }
grep -m1 "changed class" "$S/out/sensitivity_report.md" | cut -c1-260
rm -f "$S/speed/refined_pass2.jsonl"
FINAL_SPEED_DIR="$S/speed" FINAL_OUT="$S/out2" ./run_all.sh >/dev/null || { echo "e2e without pass 2 FAILED"; exit 1; }
echo "e2e scratch runs OK (with and without pass 2)"; rm -rf "$S"
exit 0
