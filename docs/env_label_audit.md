# ENV label-precision audit (binding gate ≥ 0.70; no amendment allowed)

Seed 2982, 30 per class × repo, XC audit rules.

## harfbuzz · extrinsic — 28/30 = 0.93 → PASS

- ✓ `cc3f4e00aa` silence gcc
- ✓ `79eb0f7486` [GSUB] Fix build on GCC < 7
- ✓ `45e55f7080` [indic] Fix clang everything
- ✓ `26a963b9cb` [wince] Try to fix some stuff on Windows CE
- ✓ `9c80cbc87f` Fix build on clang after previous commit
- ✓ `e7737b41d7` Add sanitizer reference_table, also fix clang build
- ✗ `c124252df5` [algs] Add support for little-endian int types
- ✓ `60022ecced` Fix -Wcast-function-type warnings in util/ with gcc 4.8
- ✓ `76c4873e8c` Support branch prediction helpers on clang compiles (#491)
- ✓ `d6ddb232fc` FIX: -Wextra-semi-stmt in Clang9
- ✗ `865b6971ad` [subset] Add a test for OS/2 fixes during subsetting.
- ✓ `f63d960c4e` Fix a MSVC warning re __has_builtin
- ✓ `b96af03c20` Fix build with --coretext on iOS
- ✓ `708403e7f3` Fix warnings with old glib
- ✓ `51b584880e` [pragma] Silence MSVC unknown-pragma warning
- ✓ `3238cb744b` [GPOS] Fix build on GCC < 7
- ✓ `e9f9c0d81c` [sanitize] Reorder condition to silence bogus gcc warning
- ✓ `946477fa54` [font] Fix a MSVC "error"
- ✓ `499029644f` [gsub] Fix clang's semicolon complains
- ✓ `29e25550ce` Fix gcc warning
- ✓ `679b900e9b` [meta] Fix gcc4 trait implementation
- ✓ `c306410cab` Bug 77732 - Fix unused typedef warning for ASSERT_STATIC with GCC 4.8
- ✓ `cd4d7664e1` [test] Avoid Windows small macro in raster paint test
- ✓ `365f27ab5b` Work around older compilers
- ✓ `4d27bb8746` hb-ot-shape-complex-arabic.cc: Fix build on Visual Studio
- ✓ `a4446b10bf` Fix build for C89 compilers
- ✓ `1ae265888e` Fix gcc warning
- ✓ `5aaef7d43a` [gpu] Fix M_PI for MinGW cross-compilation
- ✓ `c69f02784a` Fix sign-compare error on 32-bit systems
- ✓ `82438c6ad5` Fix #pragma message for MSVC.

## harfbuzz · regression — 23/30 = 0.77 → PASS

- ✓ `c986ca15a6` Improve overflow avoidance
- ✓ `8795ccedd6` Revert "[SimpleGlyph] Avoid branches in read_points"
- ✓ `57886e2162` [test] Enable tests fixed by 461cd5a which was regressed by b986fea
- ✓ `2e7021da7d` Revert "Minor" - revert moving extern "C" definitions in-function
- ✗ `c9a8620c00` [graph] Keep the Coverage range count of class_def_size_estimator_t incremental
- ✓ `b80b97b549` Revert "Remove unused hb-iter.hh"
- ✗ `199cae8b28` [buffer] Document message callback lifetime across reset (#6354)
- ✓ `6dd80faf0d` Fix FixedVersion::to_int()
- ✓ `923a8f520a` Fix up 5de83fab947e23cc729d69f8d44a28311298af9d
- ✓ `ec925ece05` [khmer] Reinstate a pause after basic features
- ✓ `82d19c08fc` Revert "[glyf/Composite] Remove phantom points when not needed anymore"
- ✓ `41369b6617` Revert "[subset/cff1] Optimize writing of consecutive names"
- ✓ `e90213868b` Revert "collect_unicodes() to check gid < num_glyphs with cmap 12"
- ✓ `52c15b053a` Revert "[ragel] Switch to -T1 output instead of -F1"
- ✓ `8e7e29a691` [bit-set] Revert clear() change -- can't touch Null singleton
- ✓ `f19ca24a8e` Revert "Revert "Require numerator and denominator in auto fraction""
- ✓ `61486746d3` Revert "[indic] Clear syllables before presentation features"
- ✓ `82b3e8af69` Revert "[aat] Allow disable feature ranges"
- ✓ `80cd92326f` [Indic] Only apply basic features per-syllable
- ✗ `4aebec5702` [subset/cff1] Bound preprocessing map lookups for output gaps (#6481)
- ✓ `38fa032330` Revert "[subset/loca] Build in the serializer memory"
- ✗ `fc4d42ff99` [ft] Add API to notify that hb_font_t changed
- ✓ `f20f4c20bc` [raster] Fix background color and stride handling (#6310)
- ✓ `f18ff5a84d` [OTLayout] Return correct value from recursion
- ✗ `c8e9f14fd3` [repacker] Reject link positions that wrap near UINT_MAX
- ✗ `b1316bce52` [uniscribe] Read font directories from the sanitized original (#6488)
- ✓ `ddcedece1d` Revert "[gpu] Add fullscreen toggle (F key) to D3D11 demo"
- ✓ `f2a3680fab` Revert "[gsubgpos] Limit (Chain)ContextFormat3 for consistency"
- ✗ `b732218126` [paint] Clip sweep-gradient tiles to 0..2π in hb_paint_sweep_gradient_tiles
- ✓ `21deab2bdc` Fixed inifinite loop introduced in 7403e055cd1463f

## libarchive · extrinsic — 25/30 = 0.83 → PASS

- ✓ `c98c7a69e3` Fix build failure with -Wcast-qual GCC option since it happend on FreeBSD current.
- ✓ `8a5460e778` Fix a handling of an empty gname in ustar on Windows. It cased a conversion error when the gname had
- ✓ `54b8eee623` Work around Borland C's broken _open() implementation.
- ✓ `2c3795fa72` Fix warnings on Visual Studio.
- ✓ `c9b68f41c0` Enable bsdtar -s option on Windows with libregex and fix the problem which appeared from enabling th
- ✓ `bbddb0c9dd` windows: Remove pre Windows XP support code
- ✓ `125047fc67` Chuck Wilson's fixes for Cygwin and MinGW builds.
- ✓ `6fdcded351` Fix the build failure of libarchive_test on Visual Studio.
- ✓ `99f2e6de63` Merge r1220 from trunk: Testsuite fixes for cygwin-1.5 * configure.ac: Detect cygwin-1.7. * tar/test
- ✓ `ef3f9c45d5` Fix MSVC zstd conversion from size_t to int warnings (#2467)
- ✗ `85c48957c1` Merge r195389 from FreeBSD-CURRENT:  Rework the numeric uid/gid support for the -R option.
- ✓ `433f74b08f` Fix build failure with -Wextra -Wunused GCC options since it happend on FreeBSD current.
- ✓ `ebef6c495e` Limit #pragma GCC to GCC-compatible cmopilers
- ✓ `52dfe43a80` Fix Windows path when writing zip entries (#2309)
- ✓ `908bb5b39f` fixes to build by Open Watcom toolchain
- ✓ `f40faa6edb` Unbreak build on mingw.
- ✓ `5da00ad75b` fix build with LibreSSL 2.7
- ✓ `852c005bbf` Fix build failure with -Wcast-qual GCC option since it happend on FreeBSD current.
- ✗ `80bdb4b402` Mark this as 2.6.901a - as of this point, FreeBSD-CURRENT is in sync with libarchive.googlecode.com 
- ✓ `4c0b3618a4` Fixes Windows compile issue (#2538)
- ✓ `386412e24e` unzip: disable build on Windows
- ✓ `f52ffa63d7` Add custom _dosmaperr() implementation (copied from PostgreSQL) and use it instead of the undocument
- ✓ `f2d99edb1d` Fix MSVC C4706 warning in lafe_fnmatch.c
- ✗ `c7d6d08b97` Switch directory traversals code in bsdtar from tar/tree.[ch] to the new one in libarchive library. 
- ✗ `b5fce10e32` 7zip: Fix out-of-bounds access on ELF 64-bit header
- ✓ `e0f0abf092` Fix size_t and ssize_t defaults on Borland
- ✓ `f64286f4d8` Avoid failing some libarchive_test on Windows and some platforms, whose the size of off_t is four by
- ✗ `bb0d99a771` Merge various test framework improvements across the various test harnesses.  In particular, there h
- ✓ `1f6cdd4625` Fix a few clang nitpicks (#2447)
- ✓ `640c9feced` fix mingw windows build issue

## libarchive · regression — 13/30 = 0.43 → FAIL → withheld

- ✓ `e60f73cea6` cpio: Fix newc aspect of test_basic
- ✗ `a2a73a8f14` Add regression test for zisofs 32-bit heap overflow
- ✗ `67421348b3` Issue 185:  Include the contributed Zip in the regression test, include this and another recently ad
- ✓ `355f7cb849` bsdunzip_test: Set umask before asserting permissions
- ✓ `e6c9668f32` Add a check to archive_read_filter_consume to reject any attempts to move the file pointer by a nega
- ✓ `d4fa1de0ad` test: Fix off-by-one in bounds check
- ✓ `1e58dd0af5` archive_crc32: fix master-only AArch64 regression
- ✗ `82d44c4042` pax: handle all-slash pathnames in USTAR name splitting
- ✗ `b2e715a26e` zip: Decode Unix extra-field timestamps as signed
- ✗ `91c146e87d` read_data_into_fd: Fix spurious "Seek error" for trailing holes
- ✗ `515380e7e5` read: Add multi-volume regression test
- ✓ `62c8caf661` Revert "zip: update AppleDouble support for directories (#2100)"
- ✓ `aac59c1bd5` Partially revert "Merge pull request #2679 from AZero13/error"
- ✗ `7148eab4e1` iso9660: add test for Rock Ridge CL/RE relocation cycle
- ✓ `ed9baeebd8` Issue 686: Keep retrying until buffer is big enough
- ✗ `8ff7849b88` rar5: compress edata_size regression fixture (review: @DHowett)
- ✗ `549ed3b8cd` rar5: add regression test for oversized EX_UOWNER owner name
- ✗ `496ae9bcaf` test: add RAR5 extra field size underflow regression test
- ✓ `d047f00352` tar: fix master-only regression in sparse error reporting
- ✗ `27e7500cf3` rar5: raise the signature bid above the seekable Zip bidder's
- ✓ `dea03d6e00` Revert "Wait for the process instead of busy wait loop"
- ✓ `79b06edf6e` archive_read: don't poison archive when seek is unsupported (fixes #3323)
- ✗ `3f17e0061b` tar: do not dereference a NULL error string in safe_fputs()
- ✗ `1f2da75fb3` cpio: reject oversized pathnames before read-ahead
- ✓ `52ca91f512` Fix a part of a commit 221f63f2f8. The double free bug Clang Static Anlyzer(trunk) claimed of was th
- ✓ `95b3c5441f` Revert "xar: fix bad seek in move_reading_point()"
- ✗ `a57c3d21db` cab: Handle ARCHIVE_EOF of lzx_read_pre_tree
- ✗ `b55059597b` xar: Add fflag regression test
- ✗ `2b6e17a259` rar5: add regression test for 2-byte varint in EX_REDIR target size
- ✗ `42aae58a53` rar5: Add test for truncated HTIME extra records

Notes: harfbuzz `OS/2` is the font table, not the OS. Most libarchive 'regression word' hits add *regression test* fixtures; they fix nothing.
