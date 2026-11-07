# EXPLORATORY — draft family trees of function fingerprints (population DB v2.12.0-b64f42bf)

- top 200 signatures cover **49.7%** of 6,936,799 functions (loc ≥ 3); function-weighted, so OS-scale repos weigh heavily — repo counts are shown beside every node.
- labels are engine display names (gitgalaxy#8009); signals and rules as of engine `b64f42bf` (before the #8010/#8011/#8016 fixes).

## Tree 2 — families (similarity clustering)

| family | share | shapes | always (≥ 90%) | often (40–90%) | languages | repos (largest) | tests | archetypes |
|---|---:|---:|---|---|---|---|---:|---|
| F7 | 17.5% | 62 | Calls & Signatures With Arguments, Function Declarations, Structural Keywords | Public / Exported Surface, State Mutation, Branches & Conditionals | python 27%, c 25%, php 10%, javascript 7% | 504 (linux 8%) | 30% | Parameter Forwarders 32%, Compute Cores 18%, Interface Declarations 14% |
| F8 | 15.8% | 63 | Calls & Signatures With Arguments, Function Declarations, Structural Keywords | Private Scope, State Mutation, Pointers & Addressing, Branches & Conditionals | c 57%, cpp 24%, python 4%, csharp 3% | 356 (linux 34%) | 6% | Encapsulated Accessors 26%, C Struct Operations 21%, Stateful Encapsulated Methods 19% |
| F6 | 4.7% | 17 | Calls & Signatures With Arguments, Function Declarations, Structural Keywords | — | javascript 26%, cpp 17%, typescript 16%, kotlin 10% | 429 (kotlin 10%) | 31% | Parameter Forwarders 43%, Interface Declarations 30%, Callbacks & Closures 17% |
| F3 | 3.3% | 17 | Calls & Signatures With Arguments, Decorators, Annotations & Attributes, Function Declarations | Public / Exported Surface, Test Assertions, Structural Keywords | java 49%, rust 18%, csharp 17%, dart 6% | 172 (kotlin 27%) | 53% | Annotated & Test Methods 88%, State Mutators 4%, Generic / Templated Code 3% |
| F5 | 2.5% | 10 | Function Declarations, Structural Keywords | — | cpp 59%, ruby 18%, cobol 7%, assembly 4% | 260 (haiku 11%) | 17% | Interface Declarations 62%, Parameter Forwarders 17%, I/O & Config Routines 15% |
| F11 | 2.1% | 8 | Calls & Signatures With Arguments, Function Declarations | State Mutation | javascript 22%, csharp 20%, typescript 10%, cpp 9% | 396 (runtime 15%) | 32% | State Mutators 49%, Parameter Forwarders 25%, Callbacks & Closures 9% |
| F12 | 1.2% | 6 | Calls & Signatures With Arguments, Function Declarations | — | javascript 27%, cpp 20%, dart 16%, rust 11% | 295 (sdk 16%) | 34% | State Mutators 85%, Callbacks & Closures 7%, I/O & Config Routines 6% |
| F10 | 1.0% | 5 | Pointers & Addressing, Calls & Signatures With Arguments, Function Declarations | Public / Exported Surface | rust 85%, cpp 7%, zig 4%, csharp 2% | 112 (rust 29%) | 14% | State Mutators 85%, Annotated & Test Methods 7%, Generic / Templated Code 6% |
| F9 | 0.7% | 4 | Calls & Signatures With Arguments, Function Declarations, Generics & Type Parameters | Pointers & Addressing, Structural Keywords | rust 46%, typescript 11%, python 10%, kotlin 10% | 237 (rust 19%) | 24% | Generic / Templated Code 95%, Many-Argument Workhorses 2%, State Mutators 1% |
| F1 | 0.4% | 2 | Function Declarations | — | cpp 32%, c 14%, assembly 14%, makefile 13% | 252 (freebsd-src 26%) | 17% | I/O & Config Routines 77%, State Mutators 22%, Many-Argument Workhorses 1% |
| F2 | 0.4% | 3 | Test Assertions, Function Declarations | Calls & Signatures With Arguments, Structural Keywords | cpp 39%, groovy 20%, kotlin 11%, c 7% | 150 (gradle 18%) | 57% | State Mutators 52%, Interface Declarations 20%, I/O & Config Routines 14% |
| F14 | 0.1% | 1 | — | — | shell 89%, scheme 6%, groovy 1%, python 1% | 28 (freebsd-src 74%) | 77% | I/O & Config Routines 97%, State Mutators 2%, Many-Argument Workhorses 1% |
| F13 | 0.1% | 1 | Calls & Signatures With Arguments | — | typescript 64%, groovy 33%, shell 2%, cpp 0% | 74 (gradle 33%) | 21% | State Mutators 57%, I/O & Config Routines 43%, Many-Argument Workhorses 0% |
| F4 | 0.1% | 1 | Public / Exported Surface, File & Network I/O, Regex & String Matching, Bitwise Operations, Test Assertions, Unsafe Constructs, Calls & Signatures With Arguments, Decorators, Annotations & Attributes, Function Declarations, Structural Keywords | — | java 100% | 1 (kotlin 100%) | 71% | Annotated & Test Methods 100% |

## Tree 1 — growth (each shape under its most common sub-shape; edge = signals added)

- 1 root(s); 196 of 199 edges add exactly one signal (98%).

- **{}** — #163: 0.07% · 28 repos (top 74%) · shell/scheme/groovy · 5 lines · tests 77%
    - **+ Function Declarations** — #39: 0.36% · 251 repos (top 31%) · cpp/c/makefile · 10 lines · tests 19%
        - **+ Structural Keywords** — #14: 0.79% · 201 repos (top 15%) · cpp/ruby/assembly · 5 lines · tests 23%
            - **+ Calls & Signatures With Arguments** — #1: 2.55% · 386 repos (top 9%) · javascript/cpp/typescript · 5 lines · tests 35%
                - **+ Public / Exported Surface** — #2: 2.46% · 318 repos (top 10%) · php/python/java · 6 lines · tests 23%
                    - **+ State Mutation** — #5: 1.22% · 294 repos (top 14%) · python/php/csharp · 8 lines · tests 35%
                        - **+ Test Assertions** — #8: 0.98% · 151 repos (top 11%) · python/php/java · 15 lines · tests 95%
                            - **+ Defensive Checks** — #35: 0.40% · 115 repos (top 22%) · python/php/java · 13 lines · tests 99%
                                - **+ Generics & Type Parameters** — #66: 0.19% · 58 repos (top 68%) · python/java/rust · 16 lines · tests 100%
                                    - **+ Async & Concurrency** — #65: 0.20% · 11 repos (top 97%) · python/dart · 29 lines · tests 100%
                                - **+ Branches & Conditionals** — #105: 0.11% · 114 repos (top 16%) · python/go/php · 21 lines · tests 95%
                            - **+ Branches & Conditionals** — #59: 0.23% · 133 repos (top 18%) · python/php/go · 18 lines · tests 93%
                            - **+ Manual Memory Allocation** — #81: 0.15% · 20 repos (top 37%) · php/go/rust · 17 lines · tests 99%
                            - **+ Decorators, Annotations & Attributes** — #116: 0.10% · 53 repos (top 35%) · csharp/java/php · 21 lines · tests 91%
                            - **+ Explicit Casts & Conversions** — #151: 0.08% · 94 repos (top 15%) · python/php/solidity · 23 lines · tests 97%
                            - **+ Generics & Type Parameters** — #199: 0.06% · 70 repos (top 27%) · python/java/rust · 15 lines · tests 98%
                        - **+ Branches & Conditionals** — #12: 0.79% · 283 repos (top 9%) · python/php/c · 17 lines · tests 14%
                            - **+ Pointers & Addressing** — #13: 0.79% · 129 repos (top 24%) · c/go/zig · 30 lines · tests 2%
                                - **+ Class / Struct Declarations** — #26: 0.48% · 40 repos (top 63%) · c/zig/cpp · 30 lines · tests 2%
                                    - **+ Bitwise Operations** — #107: 0.11% · 29 repos (top 57%) · c/cpp · 48 lines · tests 1%
                                    - **+ Immutability** — #110: 0.10% · 32 repos (top 64%) · c · 33 lines · tests 1%
                                    - **+ Metaprogramming** — #137: 0.08% · 17 repos (top 77%) · c · 57 lines · tests 1%
                                - **+ Immutability** — #69: 0.19% · 69 repos (top 29%) · c/go/cpp · 27 lines · tests 1%
                                - **+ Bitwise Operations** — #73: 0.17% · 70 repos (top 21%) · c/zig/rust · 46 lines · tests 1%
                                - **+ Defensive Checks** — #113: 0.10% · 102 repos (top 18%) · c/zig/go · 29 lines · tests 2%
                                - **+ Unsafe Constructs** — #182: 0.07% · 73 repos (top 35%) · c/zig/rust · 46 lines · tests 1%
                            - **+ Defensive Checks** — #64: 0.20% · 207 repos (top 18%) · php/python/csharp · 23 lines · tests 10%
                            - **+ Generics & Type Parameters** — #86: 0.15% · 173 repos (top 16%) · python/csharp/java · 17 lines · tests 9%
                            - **+ Unsafe Constructs** — #130: 0.09% · 179 repos (top 10%) · python/java/php · 20 lines · tests 19%
                            - **+ Explicit Casts & Conversions** — #139: 0.08% · 173 repos (top 10%) · python/php/csharp · 26 lines · tests 15%
                            - **+ Error Exits** — #153: 0.08% · 165 repos (top 17%) · python/csharp/java · 25 lines · tests 12%
                        - **+ Pointers & Addressing** — #56: 0.26% · 118 repos (top 19%) · c/go/rust · 10 lines · tests 3%
                            - **+ Class / Struct Declarations** — #142: 0.08% · 31 repos (top 55%) · c/zig/cpp · 14 lines · tests 3%
                            - **+ Closures & Lambdas** — #183: 0.07% · 13 repos (top 88%) · go/rust/swift · 5 lines · tests 4%
                        - **+ Generics & Type Parameters** — #88: 0.14% · 163 repos (top 18%) · python/java/csharp · 10 lines · tests 31%
                        - **+ Decorators, Annotations & Attributes** — #154: 0.08% · 87 repos (top 28%) · java/python/swift · 8 lines · tests 30%
                        - **+ Manual Memory Allocation** — #179: 0.07% · 45 repos (top 39%) · php/rust/perl · 13 lines · tests 83%
                    - **+ Pointers & Addressing** — #11: 0.83% · 138 repos (top 23%) · c/go/zig · 6 lines · tests 3%
                        - **+ Branches & Conditionals** — #44: 0.33% · 117 repos (top 27%) · c/zig/rust · 13 lines · tests 2%
                            - **+ Class / Struct Declarations** — #112: 0.10% · 29 repos (top 76%) · c/zig/cpp · 15 lines · tests 1%
                            - **+ Defensive Checks** — #157: 0.08% · 86 repos (top 22%) · zig/go/c · 15 lines · tests 2%
                        - **+ Immutability** — #75: 0.17% · 74 repos (top 37%) · c/rust/fortran · 6 lines · tests 2%
                        - **+ Closures & Lambdas** — #89: 0.14% · 26 repos (top 46%) · go/rust/swift · 4 lines · tests 5%
                        - **+ Class / Struct Declarations** — #99: 0.12% · 31 repos (top 71%) · c/zig/swift · 8 lines · tests 2%
                    - **+ Branches & Conditionals** — #18: 0.57% · 279 repos (top 14%) · python/csharp/c · 10 lines · tests 20%
                        - **+ Defensive Checks** — #95: 0.12% · 204 repos (top 11%) · python/csharp/php · 11 lines · tests 13%
                        - **+ Generics & Type Parameters** — #96: 0.12% · 169 repos (top 21%) · python/csharp/typescript · 10 lines · tests 13%
                        - **+ Test Assertions** — #190: 0.06% · 128 repos (top 11%) · python/go/php · 13 lines · tests 72%
                    - **+ Decorators, Annotations & Attributes** — #21: 0.53% · 97 repos (top 29%) · java/csharp/swift · 5 lines · tests 23%
                        - **+ Test Assertions** — #9: 0.95% · 66 repos (top 81%) · java/csharp/php · 6 lines · tests 68%
                            - **+ Closures & Lambdas, Generics & Type Parameters** — #135: 0.09% · 13 repos (top 75%) · csharp/java/scala · 13 lines · tests 82%
                            - **+ Async & Concurrency, Class / Struct Declarations, Closures & Lambdas** — #197: 0.06% · 2 repos (top 100%) · csharp · 15 lines · tests 16%
                            - **+ File & Network I/O, Regex & String Matching, Bitwise Operations, Unsafe Constructs** — #200: 0.06% · 1 repos (top 100%) · java · 4 lines · tests 71%
                        - **+ Generics & Type Parameters** — #115: 0.10% · 58 repos (top 38%) · java/swift/csharp · 5 lines · tests 20%
                        - **+ Private Scope** — #165: 0.07% · 51 repos (top 44%) · java/kotlin/csharp · 5 lines · tests 29%
                    - **+ Generics & Type Parameters** — #29: 0.45% · 204 repos (top 24%) · python/java/csharp · 6 lines · tests 19%
                        - **+ Async & Concurrency** — #133: 0.09% · 61 repos (top 75%) · python/dart/csharp · 6 lines · tests 25%
                    - **+ Test Assertions** — #38: 0.36% · 169 repos (top 11%) · python/php/java · 9 lines · tests 92%
                    - **+ Closures & Lambdas** — #67: 0.19% · 120 repos (top 44%) · go/csharp/php · 4 lines · tests 15%
                    - **+ Private Scope** — #106: 0.11% · 90 repos (top 36%) · csharp/java/php · 5 lines · tests 14%
                    - **+ Async & Concurrency** — #111: 0.10% · 100 repos (top 59%) · dart/php/csharp · 8 lines · tests 81%
                        - **+ Class / Struct Declarations** — #164: 0.07% · 9 repos (top 100%) · dart/swift/python · 13 lines · tests 100%
                    - **+ Defensive Checks** — #140: 0.08% · 161 repos (top 22%) · python/csharp/php · 8 lines · tests 32%
                    - **+ Unsafe Constructs** — #148: 0.08% · 150 repos (top 12%) · python/java/c · 7 lines · tests 35%
                        - **+ Explicit Casts & Conversions** — #101: 0.11% · 55 repos (top 85%) · java/zig/c · 4 lines · tests 1%
                    - **+ Explicit Casts & Conversions** — #192: 0.06% · 157 repos (top 18%) · python/csharp/php · 6 lines · tests 28%
                - **+ Private Scope** — #7: 1.01% · 227 repos (top 14%) · c/java/php · 6 lines · tests 20%
                    - **+ Pointers & Addressing** — #4: 1.26% · 89 repos (top 57%) · c/go/csharp · 6 lines · tests 3%
                        - **+ Class / Struct Declarations** — #23: 0.50% · 22 repos (top 84%) · c/go/java · 9 lines · tests 2%
                            - **+ Branches & Conditionals** — #43: 0.34% · 25 repos (top 84%) · c · 16 lines · tests 1%
                            - **+ State Mutation** — #53: 0.28% · 29 repos (top 73%) · c/go · 14 lines · tests 5%
                        - **+ Branches & Conditionals** — #25: 0.48% · 78 repos (top 55%) · c/go/csharp · 13 lines · tests 2%
                            - **+ Immutability** — #85: 0.15% · 50 repos (top 47%) · c/cpp/csharp · 13 lines · tests 4%
                        - **+ State Mutation** — #47: 0.31% · 73 repos (top 44%) · c/go/csharp · 12 lines · tests 5%
                            - **+ Bitwise Operations** — #123: 0.09% · 37 repos (top 65%) · c/csharp/solidity · 14 lines · tests 1%
                        - **+ Immutability** — #62: 0.21% · 54 repos (top 50%) · c/csharp/go · 6 lines · tests 5%
                    - **+ Branches & Conditionals** — #32: 0.41% · 206 repos (top 18%) · c/csharp/python · 11 lines · tests 8%
                        - **+ Defensive Checks** — #109: 0.10% · 152 repos (top 18%) · csharp/dart/go · 13 lines · tests 9%
                    - **+ State Mutation** — #45: 0.33% · 218 repos (top 20%) · python/php/c · 10 lines · tests 34%
                        - **+ Generics & Type Parameters** — #177: 0.07% · 110 repos (top 52%) · python/java/csharp · 10 lines · tests 13%
                        - **+ Manual Memory Allocation** — #194: 0.06% · 22 repos (top 76%) · php/go/embedded_python · 15 lines · tests 96%
                    - **+ Generics & Type Parameters** — #150: 0.08% · 120 repos (top 18%) · python/java/csharp · 8 lines · tests 28%
                    - **+ Closures & Lambdas** — #178: 0.07% · 71 repos (top 40%) · java/go/csharp · 5 lines · tests 26%
                    - **+ Bitwise Operations** — #198: 0.06% · 88 repos (top 44%) · c/go/php · 5 lines · tests 9%
                - **+ Branches & Conditionals** — #10: 0.89% · 325 repos (top 8%) · typescript/javascript/cpp · 11 lines · tests 22%
                    - **+ State Mutation** — #17: 0.60% · 342 repos (top 8%) · javascript/cpp/typescript · 18 lines · tests 21%
                        - **+ Private Scope** — #20: 0.54% · 224 repos (top 15%) · python/c/php · 17 lines · tests 9%
                            - **+ Pointers & Addressing** — #6: 1.06% · 84 repos (top 39%) · c/go/csharp · 26 lines · tests 2%
                                - **+ Class / Struct Declarations** — #3: 1.43% · 40 repos (top 77%) · c/go/cpp · 30 lines · tests 1%
                                    - **+ Bitwise Operations** — #33: 0.41% · 22 repos (top 76%) · c · 46 lines · tests 0%
                                        - **+ Immutability** — #169: 0.07% · 21 repos (top 80%) · c · 57 lines · tests 1%
                                        - **+ Metaprogramming** — #171: 0.07% · 11 repos (top 82%) · c · 84 lines · tests 0%
                                    - **+ Immutability** — #55: 0.27% · 27 repos (top 76%) · c/cpp · 36 lines · tests 2%
                                        - **+ Defensive Checks** — #172: 0.07% · 29 repos (top 72%) · c · 35 lines · tests 3%
                                    - **+ Metaprogramming** — #60: 0.22% · 16 repos (top 85%) · c · 57 lines · tests 1%
                                    - **+ Defensive Checks** — #168: 0.07% · 27 repos (top 59%) · c/go · 37 lines · tests 4%
                                - **+ Bitwise Operations** — #49: 0.30% · 56 repos (top 55%) · c/go/csharp · 36 lines · tests 1%
                                    - **+ Immutability** — #185: 0.06% · 47 repos (top 44%) · c/go/cpp · 41 lines · tests 1%
                                - **+ Immutability** — #51: 0.29% · 59 repos (top 34%) · c/go/csharp · 27 lines · tests 4%
                                    - **+ Defensive Checks** — #161: 0.07% · 48 repos (top 35%) · c/go/csharp · 30 lines · tests 5%
                                - **+ Defensive Checks** — #114: 0.10% · 66 repos (top 25%) · c/go/csharp · 31 lines · tests 5%
                                - **+ Unsafe Constructs** — #147: 0.08% · 53 repos (top 33%) · c/go/solidity · 38 lines · tests 2%
                                - **+ Metaprogramming** — #173: 0.07% · 37 repos (top 47%) · c/go/csharp · 47 lines · tests 6%
                            - **+ Defensive Checks** — #92: 0.13% · 155 repos (top 16%) · php/python/csharp · 24 lines · tests 9%
                            - **+ Generics & Type Parameters** — #122: 0.09% · 136 repos (top 23%) · python/csharp/java · 18 lines · tests 9%
                        - **+ Pointers & Addressing** — #30: 0.45% · 118 repos (top 15%) · cpp/rust/c · 27 lines · tests 3%
                            - **+ Immutability** — #28: 0.45% · 67 repos (top 21%) · cpp/c/objective-c · 31 lines · tests 2%
                                - **+ Explicit Casts & Conversions** — #80: 0.15% · 45 repos (top 32%) · cpp/objective-c/c · 50 lines · tests 2%
                                    - **+ Defensive Checks** — #195: 0.06% · 33 repos (top 56%) · cpp/c/go · 69 lines · tests 1%
                                - **+ Defensive Checks** — #158: 0.08% · 44 repos (top 53%) · cpp/c/rust · 41 lines · tests 1%
                            - **+ Explicit Casts & Conversions** — #103: 0.11% · 69 repos (top 25%) · cpp/assembly/rust · 36 lines · tests 2%
                            - **+ Defensive Checks** — #143: 0.08% · 89 repos (top 36%) · cpp/zig/rust · 33 lines · tests 1%
                        - **+ Defensive Checks** — #57: 0.26% · 264 repos (top 14%) · javascript/typescript/dart · 24 lines · tests 21%
                            - **+ Closures & Lambdas** — #94: 0.12% · 153 repos (top 20%) · javascript/typescript/dart · 29 lines · tests 18%
                        - **+ Closures & Lambdas** — #74: 0.17% · 185 repos (top 19%) · javascript/typescript/ruby · 17 lines · tests 21%
                        - **+ Immutability** — #160: 0.07% · 80 repos (top 18%) · cpp/typescript/objective-c · 23 lines · tests 6%
                    - **+ Pointers & Addressing** — #40: 0.35% · 121 repos (top 17%) · cpp/rust/assembly · 14 lines · tests 4%
                        - **+ Generics & Type Parameters** — #126: 0.09% · 73 repos (top 28%) · rust/cpp/swift · 14 lines · tests 7%
                        - **+ Defensive Checks** — #155: 0.08% · 88 repos (top 26%) · cpp/zig/rust · 17 lines · tests 3%
                        - **+ Explicit Casts & Conversions** — #162: 0.07% · 68 repos (top 27%) · cpp/assembly/rust · 18 lines · tests 1%
                    - **+ Defensive Checks** — #41: 0.35% · 256 repos (top 10%) · javascript/typescript/dart · 11 lines · tests 18%
                        - **+ Closures & Lambdas** — #108: 0.10% · 156 repos (top 14%) · javascript/typescript/kotlin · 12 lines · tests 21%
                    - **+ Closures & Lambdas** — #42: 0.35% · 185 repos (top 45%) · javascript/typescript/kotlin · 7 lines · tests 14%
                    - **+ Immutability** — #91: 0.13% · 86 repos (top 15%) · cpp/typescript/ada · 12 lines · tests 3%
                    - **+ Error Exits** — #102: 0.11% · 173 repos (top 60%) · kotlin/typescript/javascript · 10 lines · tests 17%
                    - **+ Generics & Type Parameters** — #129: 0.09% · 175 repos (top 11%) · typescript/rust/kotlin · 12 lines · tests 25%
                    - **+ Decorators, Annotations & Attributes** — #191: 0.06% · 72 repos (top 43%) · rust/dart/swift · 10 lines · tests 17%
                - **+ State Mutation** — #16: 0.69% · 324 repos (top 9%) · cpp/python/javascript · 7 lines · tests 30%
                    - **+ Pointers & Addressing** — #79: 0.16% · 103 repos (top 18%) · cpp/rust/c · 9 lines · tests 7%
                    - **+ Closures & Lambdas** — #93: 0.13% · 160 repos (top 19%) · javascript/typescript/ruby · 8 lines · tests 38%
                    - **+ Generics & Type Parameters** — #132: 0.09% · 167 repos (top 13%) · python/kotlin/typescript · 10 lines · tests 27%
                - **+ Pointers & Addressing** — #19: 0.57% · 125 repos (top 16%) · cpp/rust/assembly · 7 lines · tests 7%
                    - **+ Immutability** — #24: 0.50% · 61 repos (top 32%) · cpp/c/rust · 5 lines · tests 2%
                        - **+ Branches & Conditionals** — #37: 0.37% · 61 repos (top 34%) · cpp/c/objective-c · 14 lines · tests 1%
                            - **+ Explicit Casts & Conversions** — #127: 0.09% · 42 repos (top 47%) · cpp/objective-c/c · 20 lines · tests 0%
                            - **+ Public / Exported Surface** — #134: 0.09% · 57 repos (top 29%) · c/rust/objective-c · 13 lines · tests 1%
                            - **+ Defensive Checks** — #186: 0.06% · 35 repos (top 58%) · cpp/c/rust · 15 lines · tests 1%
                        - **+ State Mutation** — #125: 0.09% · 48 repos (top 27%) · cpp/c/objective-c · 8 lines · tests 3%
                    - **+ Generics & Type Parameters** — #76: 0.17% · 80 repos (top 31%) · rust/cpp/c · 6 lines · tests 15%
                    - **+ Explicit Casts & Conversions** — #193: 0.06% · 64 repos (top 26%) · cpp/assembly/rust · 8 lines · tests 3%
                - **+ Closures & Lambdas** — #22: 0.52% · 206 repos (top 27%) · javascript/typescript/dart · 5 lines · tests 39%
                - **+ Immutability** — #50: 0.30% · 105 repos (top 13%) · cpp/typescript/dart · 5 lines · tests 6%
                - **+ Generics & Type Parameters** — #52: 0.29% · 220 repos (top 18%) · typescript/kotlin/rust · 6 lines · tests 32%
                    - **+ Decorators, Annotations & Attributes** — #119: 0.10% · 45 repos (top 38%) · rust/dart/csharp · 6 lines · tests 28%
                - **+ Decorators, Annotations & Attributes** — #58: 0.26% · 86 repos (top 27%) · rust/dart/groovy · 7 lines · tests 32%
                    - **+ Test Assertions** — #34: 0.41% · 65 repos (top 17%) · rust/java/kotlin · 12 lines · tests 61%
                        - **+ Unsafe Constructs** — #131: 0.09% · 52 repos (top 25%) · rust/java/kotlin · 21 lines · tests 37%
                        - **+ State Mutation** — #136: 0.09% · 51 repos (top 20%) · java/kotlin/rust · 17 lines · tests 74%
                        - **+ Closures & Lambdas** — #167: 0.07% · 32 repos (top 77%) · java/rust/kotlin · 10 lines · tests 94%
                - **+ Async & Concurrency** — #68: 0.19% · 125 repos (top 20%) · typescript/javascript/dart · 7 lines · tests 54%
                - **+ Test Assertions** — #70: 0.19% · 107 repos (top 37%) · groovy/kotlin/cpp · 13 lines · tests 60%
                - **+ Error Exits** — #82: 0.15% · 99 repos (top 89%) · kotlin/typescript/python · 5 lines · tests 13%
                - **+ Defensive Checks** — #104: 0.11% · 172 repos (top 14%) · javascript/cpp/typescript · 8 lines · tests 32%
                - **+ UI Components** — #146: 0.08% · 61 repos (top 36%) · javascript/typescript/dart · 8 lines · tests 31%
                - **+ Explicit Casts & Conversions** — #159: 0.08% · 158 repos (top 10%) · cpp/typescript/javascript · 6 lines · tests 21%
                - **+ Unsafe Constructs** — #174: 0.07% · 181 repos (top 11%) · typescript/cpp/javascript · 7 lines · tests 34%
                - **+ Metaprogramming** — #180: 0.07% · 137 repos (top 35%) · javascript/kotlin/python · 6 lines · tests 26%
            - **+ Immutability** — #36: 0.40% · 55 repos (top 21%) · cpp/objective-c/c · 4 lines · tests 2%
                - **+ Pointers & Addressing** — #78: 0.16% · 52 repos (top 24%) · cpp/c/objective-c · 5 lines · tests 2%
                    - **+ Branches & Conditionals** — #118: 0.10% · 42 repos (top 25%) · cpp/objective-c/c · 10 lines · tests 1%
                - **+ Branches & Conditionals** — #138: 0.08% · 46 repos (top 24%) · cpp/objective-c/c · 9 lines · tests 2%
            - **+ State Mutation** — #54: 0.28% · 157 repos (top 32%) · cobol/cpp/ruby · 7 lines · tests 41%
                - **+ Branches & Conditionals** — #63: 0.21% · 147 repos (top 32%) · cobol/ruby/cpp · 16 lines · tests 38%
                    - **+ Pointers & Addressing** — #98: 0.12% · 68 repos (top 27%) · cpp/abap/c · 20 lines · tests 4%
                        - **+ Immutability** — #170: 0.07% · 46 repos (top 22%) · cpp/c/abap · 24 lines · tests 3%
            - **+ Branches & Conditionals** — #72: 0.18% · 134 repos (top 17%) · ruby/cpp/assembly · 9 lines · tests 6%
                - **+ Pointers & Addressing** — #124: 0.09% · 62 repos (top 18%) · cpp/assembly/c · 11 lines · tests 2%
            - **+ Pointers & Addressing** — #83: 0.15% · 69 repos (top 16%) · cpp/assembly/c · 7 lines · tests 4%
            - **+ Global State** — #121: 0.10% · 57 repos (top 87%) · cpp/assembly/ruby · 6 lines · tests 1%
            - **+ Unsafe Constructs** — #189: 0.06% · 46 repos (top 85%) · cobol/assembly/cpp · 4 lines · tests 87%
        - **+ Calls & Signatures With Arguments** — #15: 0.77% · 241 repos (top 20%) · javascript/cpp/dart · 6 lines · tests 40%
            - **+ Pointers & Addressing** — #27: 0.46% · 99 repos (top 20%) · rust/cpp/zig · 5 lines · tests 16%
                - **+ Public / Exported Surface** — #61: 0.21% · 82 repos (top 21%) · rust/zig/c · 4 lines · tests 7%
                    - **+ Decorators, Annotations & Attributes** — #77: 0.16% · 41 repos (top 57%) · rust/csharp · 6 lines · tests 20%
                    - **+ Generics & Type Parameters** — #181: 0.07% · 50 repos (top 32%) · rust/zig/dart · 5 lines · tests 5%
                - **+ Generics & Type Parameters** — #90: 0.14% · 50 repos (top 35%) · rust/zig/go · 5 lines · tests 17%
                - **+ Decorators, Annotations & Attributes** — #144: 0.08% · 37 repos (top 46%) · rust/csharp/cpp · 5 lines · tests 11%
                - **+ Branches & Conditionals** — #149: 0.08% · 77 repos (top 24%) · rust/cpp/zig · 12 lines · tests 13%
            - **+ State Mutation** — #31: 0.41% · 227 repos (top 11%) · javascript/typescript/dart · 6 lines · tests 35%
                - **+ Public / Exported Surface** — #48: 0.31% · 105 repos (top 46%) · csharp/java/typescript · 6 lines · tests 31%
                    - **+ Private Scope** — #196: 0.06% · 50 repos (top 59%) · csharp/java/rust · 6 lines · tests 5%
                - **+ Branches & Conditionals** — #120: 0.10% · 176 repos (top 8%) · javascript/typescript/cpp · 14 lines · tests 26%
                - **+ Private Scope** — #175: 0.07% · 85 repos (top 30%) · csharp/java/typescript · 6 lines · tests 15%
                - **+ Closures & Lambdas** — #176: 0.07% · 102 repos (top 27%) · javascript/html/dart · 6 lines · tests 29%
            - **+ Public / Exported Surface** — #46: 0.33% · 132 repos (top 35%) · csharp/java/c · 5 lines · tests 30%
                - **+ Decorators, Annotations & Attributes** — #188: 0.06% · 35 repos (top 41%) · csharp/rust/java · 7 lines · tests 55%
            - **+ Decorators, Annotations & Attributes** — #84: 0.15% · 39 repos (top 66%) · dart/rust/groovy · 6 lines · tests 29%
                - **+ Test Assertions** — #156: 0.08% · 50 repos (top 23%) · rust/dart/groovy · 10 lines · tests 38%
                    - **+ Public / Exported Surface** — #71: 0.18% · 18 repos (top 89%) · csharp/scala/rust · 10 lines · tests 97%
            - **+ Test Assertions** — #87: 0.15% · 89 repos (top 26%) · cpp/javascript/rust · 10 lines · tests 56%
            - **+ Private Scope** — #97: 0.12% · 84 repos (top 26%) · csharp/go/java · 5 lines · tests 21%
            - **+ Branches & Conditionals** — #100: 0.11% · 188 repos (top 10%) · javascript/typescript/cpp · 9 lines · tests 33%
            - **+ Closures & Lambdas** — #128: 0.09% · 107 repos (top 18%) · javascript/dart/html · 5 lines · tests 39%
            - **+ Immutability** — #184: 0.07% · 56 repos (top 23%) · cpp/dart/typescript · 9 lines · tests 11%
        - **+ State Mutation** — #141: 0.08% · 92 repos (top 42%) · cobol/cpp/kotlin · 7 lines · tests 52%
        - **+ Bitwise Operations** — #145: 0.08% · 48 repos (top 50%) · cpp/assembly/objective-c · 5 lines · tests 7%
        - **+ Test Assertions** — #152: 0.08% · 61 repos (top 43%) · cpp/c/shell · 7 lines · tests 50%
    - **+ Calls & Signatures With Arguments** — #166: 0.07% · 74 repos (top 33%) · typescript/groovy/shell · 7 lines · tests 21%
        - **+ Structural Keywords** — #117: 0.10% · 92 repos (top 9%) · typescript/php/cpp · 5 lines · tests 33%
            - **+ Closures & Lambdas** — #187: 0.06% · 67 repos (top 16%) · typescript/cpp/php · 5 lines · tests 17%
