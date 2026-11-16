# Library surface outside C: registration (2026-11-16, before any non-C scan or statistic)

**Question.** In languages whose imports name the library (Go, Python, Java, Rust), does a file's import coupling to a library predict where that library's work lands (the LIB-H1 recipe), with no hand-written API-name list?

**What has been looked at.** The C results (`lib_surface_eval_output.txt`: scan-based coupling +0.389 over size on 19 units; includes only +0.253). The import string formats in sphinx and ripgrep scans (dotted module, `crate::path`). **Never computed:** any import coupling, any library-named commit count or any statistic for these four repositories.

## Repositories and libraries (fixed now)
Quarterly walks that exist: prometheus (Go, 55 snapshots), sphinx (Python, 75), commons-lang (Java, 97), ripgrep (Rust, 33). A library is an **import prefix** (regex on the scan's import string); the **subject names** pick the outcome commits (word boundary, case-insensitive). Libraries come from each repo's manifest at its head, not from any result.

| repo | library | import prefix | subject names |
|---|---|---|---|
| prometheus | k8s | `^k8s\.io/` | kubernetes, k8s |
| prometheus | aws | `^github\.com/aws/` | aws, ec2, lightsail |
| prometheus | azure | `^github\.com/Azure/` | azure |
| prometheus | consul | `^github\.com/hashicorp/consul` | consul |
| prometheus | grpc | `^google\.golang\.org/grpc` | grpc |
| prometheus | kingpin | `^github\.com/alecthomas/kingpin` | kingpin |
| prometheus | fsnotify | `^github\.com/fsnotify/` | fsnotify |
| prometheus | opentelemetry | `^go\.opentelemetry\.io/` | otel, opentelemetry |
| prometheus | docker | `^github\.com/(?:docker\|moby)/` | docker, swarm |
| prometheus | openstack | `^github\.com/gophercloud/` | openstack |
| sphinx | docutils | `^docutils(?:\.\|$)` | docutils |
| sphinx | jinja2 | `^jinja2(?:\.\|$)` | jinja |
| sphinx | pygments | `^pygments(?:\.\|$)` | pygments |
| sphinx | babel | `^babel(?:\.\|$)` | babel |
| sphinx | requests | `^requests(?:\.\|$)` | requests |
| sphinx | alabaster | `^alabaster(?:\.\|$)` | alabaster |
| sphinx | imagesize | `^imagesize` | imagesize |
| sphinx | snowballstemmer | `^snowballstemmer` | snowball |
| sphinx | sphinxcontrib | `^sphinxcontrib` | sphinxcontrib |
| sphinx | pytest | `^pytest(?:\.\|$)` | pytest |
| commons-lang | junit | `^org\.junit` | junit |
| commons-lang | easymock | `^org\.easymock` | easymock |
| commons-lang | mockito | `^org\.mockito` | mockito |
| commons-lang | hamcrest | `^org\.hamcrest` | hamcrest |
| commons-lang | jmh | `^org\.openjdk\.jmh` | jmh |
| commons-lang | commons-text | `^org\.apache\.commons\.text` | commons.text, commons-text |
| ripgrep | serde | `^serde(?:_\w+)?(?:::\|$)` | serde |
| ripgrep | termcolor | `^termcolor(?:::\|$)` | termcolor |
| ripgrep | bstr | `^bstr(?:::\|$)` | bstr |
| ripgrep | anyhow | `^anyhow(?:::\|$)` | anyhow |
| ripgrep | memchr | `^memchr(?:::\|$)` | memchr |
| ripgrep | pcre2 | `^pcre2(?:::\|$)` | pcre2 |
| ripgrep | crossbeam | `^crossbeam` | crossbeam |
| ripgrep | walkdir | `^walkdir(?:::\|$)` | walkdir |
| ripgrep | encoding_rs | `^encoding_rs` | encoding |
| ripgrep | regex | `^regex(?:::\|$)` | regex |

Candidate files: the language's extension (`.go`, `.py`, `.java`, `.rs`); size = `total_loc`. A (repo, library) unit is evaluable with at least 20 snapshots that have library work.

## Measures (as LIB)
**Sensor score** S(file) = number of the file's import entries matching the prefix, divided by the file's lines; no API names (calls in these languages are bare names). **Outcome** D-work = a non-merge commit touching 1 to 50 candidate-extension files whose subject names the library; a file is positive at snapshot t if such a commit within (t, t+180 d] touches it. Metric recall@20 (whole files by descending score, ties by smaller size then path, while cumulative lines are at most 20% of the snapshot).

## Hypotheses
* **LANG-H1:** import coupling to D minus the stronger size order, recall@20. SUPPORTED if the across-unit mean is positive and the lower bound of the within-unit snapshot bootstrap at alpha 0.0033 is above 0.
* **LANG-H2:** import coupling to D minus the mean of the other libraries' coupling (placebo), same rule.
* **LANG-H3:** import coupling to D minus a file-name lookup (path contains a subject name).
* Descriptive: per language and per unit; units not evaluable are listed. No outcome claim.

**What would count as failure:** H1 not supported in a language (reported per language as well as pooled). A null is reported as a null.
