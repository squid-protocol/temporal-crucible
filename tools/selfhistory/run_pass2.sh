#!/bin/bash
cd /srv/storage_16tb/projects/gitgalaxy-history
until [ -f speed/PASS_DONE ]; do sleep 30; done
nice -n 0 python3 refine_candidates_v2.py > speed/refine_pass2.out 2>&1
date > speed/PASS2_DONE
