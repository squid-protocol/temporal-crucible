#!/bin/bash
cd /srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2/surface_area
declare -A N=( [curl]=109 [libgit2]=69 [redis]=72 [libxml2]=114 [prometheus]=57 [sphinx]=78 [ripgrep]=43 )
for r in "$@"; do idx=$(python3 -c "n=${N[$r]}; print(' '.join(str(i) for i in sorted(set(list(range(0,n,4))+[n-1]))))"); python3 hist_scan.py $r $idx >> hist_$r.log 2>&1; done
