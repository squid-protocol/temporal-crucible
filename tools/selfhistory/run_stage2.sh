#!/bin/bash
cd /srv/storage_16tb/projects/gitgalaxy-history
while ps -eo args | awk '$2=="dense_timing.py" && $3=="run" {f=1} END{exit !f}'; do sleep 20; done
echo "pilot finished; starting stage 2 $(date)" > speed/stage2.start
python3 sens_pass.py > speed/sens.out 2>&1
echo STAGE2DONE >> speed/sens.out
