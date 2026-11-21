#!/bin/bash
cd /srv/storage_16tb/projects/gitgalaxy-history
sha() { python3 speed_probe.py slots | grep "'$1'" | grep -o "'sha': '[0-9a-f]*'" | cut -d"'" -f4; }
echo "=== B2: 2026-10-02 -> 2026-10-18, language-crucible CPU 288 -> 65 (down), threshold 176" > join/bisect_b2.out
python3 bisect_cost.py $(sha s08) $(sha s09) language-crucible 176 --down >> join/bisect_b2.out 2>&1
echo "=== B3: 2026-07-27 -> 2026-08-13, language-crucible CPU 130 -> 176 (up), threshold 153" > join/bisect_b3.out
python3 bisect_cost.py $(sha s04) $(sha s05) language-crucible 153 >> join/bisect_b3.out 2>&1
echo "=== B4: 2026-11-04 -> 2026-11-20, language-crucible CPU 68 -> 96 (up), threshold 82" > join/bisect_b4.out
python3 bisect_cost.py $(sha s10) $(sha s11) language-crucible 82 >> join/bisect_b4.out 2>&1
echo ALLDONE > join/bisects.done
