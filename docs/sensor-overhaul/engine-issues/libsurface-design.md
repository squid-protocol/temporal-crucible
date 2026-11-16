# Design: `gitgalaxy libsurface` (engine command, not yet built)

**Status:** design, 2026-11-16. Research behind it: `sensors/library_surface.md` (prototype `tools/sensor/lib_surface.py`). Depends on #8530 (`fcall_external`, merged). Tracking issue to file when approved.

## What it does
A read-only post-scan command, like `gitgalaxy reach`, that opens a finished `*_galaxy_master.db` and answers three questions about libraries:
1. `gitgalaxy libsurface DB` : which external libraries does this repository use, and in how many files?
2. `gitgalaxy libsurface DB --lib NAME [--top N]` : which files lean on library NAME, and which of its API names do they use? (where work on the library lands)
3. `gitgalaxy libsurface DB_BEFORE DB_AFTER --lib NAME` : how did the surface change: API names added and dropped, files newly or no longer coupled.
Counts and lists only; no score, no risk claim. One scan serves 1 and 2; 3 needs two.

## Who defines a library (the question that shaped this)
Three layers, later wins; matching is by **name**, and an entry with `disable = true` removes an earlier one.
1. **Automatic discovery, no list.** Every import root is a library. Rule per language, applied to the scan's `raw_imports` and ignoring what is not external: Python the first dotted component (not in `sys.stdlib_module_names`); Go host plus owner plus repository for `github.com/x/y`, the first two components elsewhere, and a path with no dot in its first component is standard library; Rust the first `::` component (not `std`, `core`, `alloc`, `crate`, `self`, `super`); Java the package prefix (not `java.`, `javax.`); JS/TS the package name including scope; C-family the header's first directory, or the header file name when it has none, excluding headers that resolve to a file in the repository and a short list of C and POSIX standard headers. This alone gives view 1 and the import-based coupling of view 2, which was validated in Go (+0.395 over size), Python (+0.102), Java (one library) and C includes-only (+0.253).
2. **A shipped default table** (`gitgalaxy/tools/sensors/libraries.toml`) with the C-family function-name patterns that discovery cannot supply. Needed because libraries reached through a wrapper header are invisible to includes (C result: full +0.389, includes-only +0.253, fails the non-inferiority margin). It starts as the 20 validated profiles and grows by contribution.
3. **User and project overrides**: `$XDG_CONFIG_HOME/gitgalaxy/libraries.toml`, then `.gitgalaxy/libraries.toml` in the scanned repository, then `--libs FILE`.

```toml
[[library]]
name      = "openssl"
languages = ["c", "cpp"]                 # optional; default all
include   = ["openssl/*"]                # globs on the import or include string
calls     = ["SSL_*", "EVP_*", "X509_*"] # globs on a called external name (optional)
```
**Globs, not regexes**: a user-supplied pattern cannot hang the matcher (the engine's stance is ReDoS-proof matching), and `SSL_*` is easier to write than `^SSL_\w+$`. Matching uses `fnmatch.fnmatchcase`. **Keep names strict, discovery permissive:** a loose call pattern such as `g_*` attaches calls to the wrong library, which is where glib and c-ares already lose; a missed name only costs a little recall.

## Measure
Per file: sites = matching imports or includes + sum over matching external names of `callers` (from `fcall_external`); density = sites / `total_loc`. Coupled files ranked by density, ties by smaller size then path. Repository level: coupled files, sites, distinct API names. Diff: set differences of names and of coupled file paths between two scans; renames show as one file leaving and one joining (the diff says so).

## Validation required before it ships
1. The glob table must **reproduce the regex numbers**: re-run `tools/sensor/lib_surface_eval.py` with the converted table; expect +0.389 over size and -0.018 against the regexes on the 19 units, within rounding. Any unit that moves is reported (a few registered regexes use alternations that become several globs, e.g. `unorm2?_*`).
2. Discovery on a held-out repository the C table was not written for (not yet run).
3. The c-ares and glib weak units re-examined, not tuned on this test set.

## Slices (five hand-written files each at most)
1. `gitgalaxy/tools/sensors/libsurface.py`, `libraries.toml`, `cli.py`, `tests/tools/test_libsurface.py`, wiki page `08-25-library-surface.md` (5). Nav and index in a docs follow-up.
2. Persist per-header include counts (#8529) if the C include resolver cannot be improved; unrelated to this command.

## Open questions
* Rust: not evaluable on ripgrep (too few library-named commits); needs another repository before any Rust claim.
* C++ and Objective-C and Fortran probably have the wrapper-header problem too; untested.
* Should discovery respect the repository's manifest (`go.mod`, `pyproject.toml`, `Cargo.toml`) to tell vendored code from dependencies?
