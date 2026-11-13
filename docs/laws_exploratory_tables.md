# LAWS exploratory tables (development repos only; descriptive)

8 repos, 5 languages. `clears` = the whole 95% interval is past the registered margin in the registered direction.


## LAW-1 heavy tails (margin 0.0)

| repo | language | effect | SE | 95% interval | verdict | note |
|---|---|---|---|---|---|---|
| libgit2 | c | +0.1836 | 0.0413 | +0.103, +0.265 | **clears** | x_min 2, tail 48% of nodes, GOF p 0.603, strength strong |
| libxml2 | c | +0.0618 | 0.0334 | -0.004, +0.127 | **straddles** | x_min 10, tail 8% of nodes, GOF p 0.291, strength strong |
| postgres | c | +0.2634 | 0.0237 | +0.217, +0.310 | **clears** | x_min 3, tail 32% of nodes, GOF p 0.492, strength weak |
| redis | c | +0.1688 | 0.0259 | +0.118, +0.220 | **clears** | x_min 5, tail 17% of nodes, GOF p 0.401, strength strong |
| prometheus | go | +0.0877 | 0.0175 | +0.053, +0.122 | **clears** | x_min 2, tail 40% of nodes, GOF p 0.444, strength weak |
| commons-lang | java | +0.1132 | 0.0583 | -0.001, +0.228 | **straddles** | x_min 3, tail 23% of nodes, GOF p 0.265, strength strong |
| sphinx | python | +0.0999 | 0.0181 | +0.064, +0.135 | **clears** | x_min 1, tail 100% of nodes, GOF p 0.012, strength none |
| ripgrep | rust | +0.0497 | 0.0177 | +0.015, +0.084 | **clears** | x_min 3, tail 33% of nodes, GOF p 0.056, strength none |

## LAW-2 preferential attachment (margin 0.0)

| repo | language | effect | SE | 95% interval | verdict | note |
|---|---|---|---|---|---|---|
| libgit2 | c | +1.3097 | 0.0301 | +1.251, +1.369 | **clears** |  |
| libxml2 | c | +1.2721 | 0.0374 | +1.199, +1.345 | **clears** |  |
| postgres | c | +1.4108 | 0.0240 | +1.364, +1.458 | **clears** |  |
| redis | c | +1.4025 | 0.0288 | +1.346, +1.459 | **clears** |  |
| prometheus | go | +1.4921 | 0.1680 | +1.163, +1.821 | **clears** |  |
| commons-lang | java | +1.2367 | 0.0663 | +1.107, +1.367 | **clears** |  |
| sphinx | python | +1.7876 | 0.0775 | +1.636, +1.939 | **clears** |  |
| ripgrep | rust | +1.1566 | 0.1515 | +0.860, +1.454 | **clears** |  |

## LAW-3 hub persistence (margin 0.0)

| repo | language | effect | SE | 95% interval | verdict | note |
|---|---|---|---|---|---|---|
| libgit2 | c | +0.0126 | 0.0110 | -0.009, +0.034 | **straddles** | observed 0.876 vs null 0.864 |
| libxml2 | c | -0.0058 | 0.0052 | -0.016, +0.005 | **straddles** | observed 0.964 vs null 0.969 |
| postgres | c | +0.0098 | 0.0055 | -0.001, +0.021 | **straddles** | observed 0.952 vs null 0.942 |
| redis | c | — | — | — | **not evaluable** | ceiling: the null does not move (mean SD 0.0007 < 0.005) |
| prometheus | go | +0.0443 | 0.0305 | -0.015, +0.104 | **straddles** | observed 0.990 vs null 0.946 |
| commons-lang | java | +0.0003 | 0.0025 | -0.004, +0.005 | **straddles** | observed 0.951 vs null 0.950 |
| sphinx | python | +0.1244 | 0.0439 | +0.038, +0.210 | **clears** | observed 0.894 vs null 0.770 |
| ripgrep | rust | — | — | — | **not evaluable** | fewer than 3 five-year pairs with 10 hubs |

## LAW-4 centralisation (margin 0.0)

| repo | language | effect | SE | 95% interval | verdict | note |
|---|---|---|---|---|---|---|
| libgit2 | c | +0.0036 | 0.0009 | +0.002, +0.005 | **clears** | Gini 0.625 vs replay 0.622 |
| libxml2 | c | +0.0258 | 0.0032 | +0.020, +0.032 | **clears** | Gini 0.581 vs replay 0.556 |
| postgres | c | +0.0012 | 0.0008 | -0.000, +0.003 | **straddles** | Gini 0.754 vs replay 0.753 |
| redis | c | +0.0293 | 0.0026 | +0.024, +0.035 | **clears** | Gini 0.655 vs replay 0.625 |
| prometheus | go | +0.0149 | 0.0030 | +0.009, +0.021 | **clears** | Gini 0.439 vs replay 0.424 |
| commons-lang | java | +0.0249 | 0.0030 | +0.019, +0.031 | **clears** | Gini 0.475 vs replay 0.450 |
| sphinx | python | -0.0050 | 0.0055 | -0.016, +0.006 | **straddles** | Gini 0.512 vs replay 0.517 |
| ripgrep | rust | -0.0013 | 0.0019 | -0.005, +0.002 | **straddles** | Gini 0.568 vs replay 0.570 |

## LAW-6 in-cycle defects (margin 0.0)

| repo | language | effect | SE | 95% interval | verdict | note |
|---|---|---|---|---|---|---|
| libgit2 | c | -0.3498 | 0.2188 | -0.779, +0.079 | **straddles** |  |
| libxml2 | c | — | — | — | **not evaluable** | in-cycle share 0.001 outside 0.05-0.8 |
| postgres | c | +0.0917 | 0.0877 | -0.080, +0.264 | **straddles** |  |
| redis | c | — | — | — | **not evaluable** | in-cycle share 0.020 outside 0.05-0.8 |
| prometheus | go | -0.0025 | 0.1705 | -0.337, +0.332 | **straddles** |  |
| commons-lang | java | -0.0191 | 0.1709 | -0.354, +0.316 | **straddles** |  |
| sphinx | python | -0.3926 | 0.2647 | -0.911, +0.126 | **straddles** |  |
| ripgrep | rust | +0.3927 | 0.3032 | -0.202, +0.987 | **straddles** |  |

## LAW-8 network metrics add to prediction (margin 0.02)

| repo | language | effect | SE | 95% interval | verdict | note |
|---|---|---|---|---|---|---|
| libgit2 | c | +0.0026 | 0.0184 | -0.034, +0.039 | **straddles** | AUC 0.786 -> 0.758 |
| libxml2 | c | +0.0224 | 0.0081 | +0.007, +0.038 | **straddles** | AUC 0.843 -> 0.858 |
| postgres | c | +0.0046 | 0.0013 | +0.002, +0.007 | **opposite** | AUC 0.801 -> 0.805 |
| redis | c | +0.0053 | 0.0087 | -0.012, +0.022 | **straddles** | AUC 0.861 -> 0.869 |
| prometheus | go | -0.0006 | 0.0071 | -0.014, +0.013 | **opposite** | AUC 0.863 -> 0.865 |
| commons-lang | java | +0.0011 | 0.0128 | -0.024, +0.026 | **straddles** | AUC 0.757 -> 0.755 |
| sphinx | python | -0.0067 | 0.0044 | -0.015, +0.002 | **opposite** | AUC 0.806 -> 0.806 |
| ripgrep | rust | — | — | — | **not evaluable** | fewer than 3 test years with 3 training years and 10 positives |

## LAW-5 decay (descriptive; registered direction is modularity DOWN)

| repo | language | modularity slope/yr | SE | propagation-cost slope | predicted direction? |
|---|---|---|---|---|---|
| libgit2 | c | +0.0020 | 0.0009 | -0.01086 | **NO** |
| libxml2 | c | +0.0019 | 0.0004 | +0.00016 | **NO** |
| postgres | c | -0.0017 | 0.0014 | -0.00438 | **NO** |
| redis | c | +0.0003 | 0.0004 | +0.00285 | **NO** |
| prometheus | go | -0.0035 | 0.0052 | -0.00181 | **NO** |
| commons-lang | java | +0.0001 | 0.0069 | -0.00002 | **NO** |
| sphinx | python | -0.0112 | 0.0048 | -0.00052 | **NO** |
| ripgrep | rust | -0.0016 | 0.0024 | +0.00128 | YES |

## LAW-7 size confound (AME before and after adjustment)

| repo | metric | unadjusted AME | adjusted AME | shrinkage | effect vs margin 0.5 | SE |
|---|---|---|---|---|---|---|
| libgit2 | coupling | 0.0668 | 0.0020 | 97% | 0.971 | 0.151 |
| libxml2 | coupling | 0.2360 | 0.1001 | 58% | 0.576 | 0.085 |
| postgres | coupling | 0.2103 | 0.0547 | 74% | 0.740 | 0.045 |
| postgres | in_cycle | 0.1256 | 0.0069 | 95% | 0.945 | 0.150 |
| redis | coupling | 0.3627 | 0.1485 | 59% | 0.591 | 0.063 |
| prometheus | coupling | 0.2052 | 0.0516 | 75% | 0.749 | 0.077 |
| prometheus | in_cycle | 0.3541 | 0.0632 | 82% | 0.822 | 0.067 |
| commons-lang | k_mean | 0.0381 | 0.0177 | 53% | 0.534 | 0.198 |
| commons-lang | coupling | 0.1131 | 0.0349 | 69% | 0.691 | 0.076 |
| commons-lang | in_cycle | 0.2390 | 0.0508 | 79% | 0.787 | 0.091 |
| sphinx | k_mean | 0.0318 | 0.0190 | 40% | 0.403 | 1.382 |
| sphinx | coupling | 0.1344 | 0.0655 | 51% | 0.513 | 0.107 |
| sphinx | in_cycle | 0.1610 | 0.0520 | 68% | 0.677 | 0.301 |
| ripgrep | coupling | 0.0840 | 0.0122 | 85% | 0.854 | 0.449 |
| ripgrep | in_cycle | 0.1876 | 0.0669 | 64% | 0.644 | 0.240 |

## Coverage sensitivity — the same laws with 44% of resolved call edges removed

Edges kept: 55.6%. A law whose number barely moves is reporting the CODE; one that swings is reporting the EXTRACTOR.

| law | repos | median |change| | worst |change| | reading |
|---|---|---|---|---|
| LAW-1 heavy tails | 8 | 11% | 26% | **sensitive — treat with care** |
| LAW-2 preferential attachment | 8 | 5% | 10% | **robust to coverage** |
| LAW-3 hub persistence | 4 | 46% | 157% | **coverage-dominated — not usable compile-free** |
| LAW-4 centralisation | 8 | 25% | 1093% | **coverage-dominated — not usable compile-free** |
