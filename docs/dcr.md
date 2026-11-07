# DCR-H1 — danger comments at birth, replicated on unseen repos (SCORED)

- per repo (quarterly snapshots, security-fix commits, commented births): libxml2 112/41/5,649, libexif 88/11/95, file 141/29/269, libtiff 109/2/582, libpng 63/1/828
- commented births 7,423; danger-commented 1,180 (16%)

| claim | result | verdict |
|---|---|---|
| **DCR-H1** danger-commented vs plain-commented → first CVE fix rate | rate ratio **1.13** [0.48, 3.08] (99%); first-CVE events 17 / 58 | **not supported** |

- descriptive inverse-variance pooled with DC-2 (1.45): **1.42**
- libxml2: rate ratio 0.88 (events 12 / 49)
- libexif: rate ratio 0.00 (events 0 / 1)
- file: rate ratio 1.81 (events 3 / 7)
- libtiff: rate ratio 14.47 (events 2 / 1)
- libpng: rate ratio inf (events 0 / 0)

Runtime 40s · seed 2982.
