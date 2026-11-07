# WH-H1..H3 — where + how for silent CVE-fix detection (SCORED; aggregates only)

- commits 19,088; silent CVE fixes 451; ordinary fixes 17,392; base rate 2.53%

| model | held-out AUC |
|---|---:|
| SIZE | 0.507 |
| WHERE | 0.720 |
| HOW | 0.569 |
| WHERE+HOW | 0.681 |

| claim | result | verdict |
|---|---|---|
| **WH-H1** location adds to the signature | WHERE+HOW − HOW = +0.111 (lo +0.079) | **SUPPORTED** |
| **WH-H2** the signature adds to location | WHERE+HOW − WHERE = -0.039 (lo -0.076) | **not supported** |
| **WH-H3** usable: top-10% enrichment | **2.93×** (lo 2.37) | **SUPPORTED** |

Precision in the top fraction (WHERE+HOW) vs base rate 2.53%: top 1% 11.2% (4.4×), top 5% 9.0% (3.5×), top 10% 7.4% (2.9×)

Per held-out repo AUC (SIZE / WHERE / HOW / WHERE+HOW):
- curl: 0.525 / 0.734 / 0.583 / 0.686
- openssl: 0.579 / 0.690 / 0.573 / 0.664
- ndpi: 0.499 / 0.662 / 0.571 / 0.648
- harfbuzz: 0.480 / 0.688 / 0.557 / 0.663
- unlabelled ordinary fixes above the median silent CVE fix: **4,084** (private)

Runtime 171s · seed 2982.
