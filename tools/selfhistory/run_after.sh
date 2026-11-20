#!/bin/bash
cd /srv/storage_16tb/projects/gitgalaxy-history
until grep -q STAGE2DONE speed/sens.out 2>/dev/null; do sleep 60; done
python3 detect_steps.py > speed/detect1.out 2>&1
cp speed/steps_detected.md speed/steps_detected_before_refine.md
python3 refine_candidates.py > speed/refine.out 2>&1
python3 detect_steps.py > speed/detect2.out 2>&1
date > speed/PASS_DONE
