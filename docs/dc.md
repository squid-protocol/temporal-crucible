# DC-2 (DC-H1..H2) — danger comments at birth vs whole-life first CVE fix (SCORED)

- births with comment info 43,233; with ≥ 1 comment line 18,816; danger-commented 2,182 (12% of commented)

| claim | result | verdict |
|---|---|---|
| **DC-H1** danger-commented vs plain-commented → first CVE fix rate | rate ratio **1.45** [1.08, 1.89]; first-CVE events 144 / 523 | **SUPPORTED: the authors' words were right** |
| **DC-H2** CVE-specific (÷ other-fix rate ratio) | **1.30** (lo 0.95); other-fix 1.12 | **not supported** |

## Descriptive

- regression 1.01; extrinsic 1.20
- commented vs uncommented (all births): CVE rate ratio 1.08
- most frequent danger words among CVE-hit functions: must be 39, do not 28, security 17, assume 16, trusted 13, must not 12, warning 12, overflow 10, validation 10, xxx 6
- curl: CVE rate ratio 1.29 (events 73 / 247)
- openssl: CVE rate ratio 1.59 (events 52 / 173)
- ndpi: CVE rate ratio 1.59 (events 10 / 58)
- harfbuzz: CVE rate ratio 1.81 (events 9 / 45)

Runtime 190s · seed 2982.
