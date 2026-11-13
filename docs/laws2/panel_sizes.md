Panel size per law, from laws_run_all8.json (8 repos: commons-lang(java), prometheus(go), sphinx(python), libgit2(c), libxml2(c), postgres(c), redis(c), ripgrep(rust))

| law | repos used | mean effect | between-repo SD | tau | median SE | target half-width | **repos per language** |
|---|---|---|---|---|---|---|---|
| LAW-1 heavy tails | 8 | +0.1285 | 0.0720 | 0.0643 | 0.0248 | 0.0643 | **5** |
| LAW-2 preferential attachment | 8 | +1.3835 | 0.1953 | 0.1732 | 0.0518 | 0.6917 | **2** |
| LAW-3 hub persistence | 6 | +0.0309 | 0.0489 | 0.0434 | 0.0082 | 0.0155 | **32** |
| LAW-4 centralisation | 8 | +0.0117 | 0.0137 | 0.0134 | 0.0028 | 0.0058 | **22** |
| LAW-6 in-cycle defects | 6 | -0.0466 | 0.2920 | 0.1983 | 0.1949 | 0.0233 | **>400** |
| LAW-8 network metrics in prediction | 7 | +0.0041 | 0.0090 | 0.0000 | 0.0081 | 0.0021 | **61** |

Order of magnitude, not a result: tau is estimated from very few repos and mixes between-repo with between-language variation. Recompute from the pilot of the study it sizes.
