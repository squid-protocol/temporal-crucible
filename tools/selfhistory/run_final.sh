#!/bin/bash
cd /srv/storage_16tb/projects/gitgalaxy-history
until [ -f speed/PASS2_DONE ]; do sleep 30; done
nice -n 19 final/run_all.sh > final/out/run_all.log 2>&1
date > final/FINAL_DONE
