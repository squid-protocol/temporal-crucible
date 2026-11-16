#!/bin/bash
# Scan one quarterly snapshot with the engine that writes fcall_external; keep only the scan database.
#   libsurface_scan.sh REPO IDX SHA
set -u
REPO=$1; IDX=$2; SHA=$3
ENGINE=/srv/storage_16tb/projects/gitgalaxy-worktrees/sensors-fcall-external
OUT=/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2/libsurface/$REPO
POOL=/srv/storage_16tb/projects/temporal-crucible-pool
DEST=$OUT/$(printf %03d $IDX)_${SHA:0:8}.db
mkdir -p $OUT; [ -s "$DEST" ] && exit 0
T=$(mktemp -d /srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2/libsurface/tmp.XXXXXX); trap 'rm -rf $T' EXIT
mkdir $T/s && git -C $POOL/$REPO archive $SHA | tar -x -C $T/s || exit 1
( cd $T && source /srv/storage_16tb/projects/gitgalaxy/venvs/selfscan/bin/activate && PYTHONPATH=$ENGINE GITGALAXY_LICENSE_KEY=COMMUNITY_FREE_TIER timeout 900 python -m gitgalaxy.galaxyscope s/ > scan.log 2>&1 )
[ -s $T/s_galaxy_master.db ] && mv $T/s_galaxy_master.db $DEST || echo "FAILED $REPO $IDX $SHA" >> $OUT/failed.txt
