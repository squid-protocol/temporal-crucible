# REG inducing-link audit (binding gate ≥ 0.70)

Seed 2982, 30 links per repo. A link is correct if the fix repairs or reverts the linked commit. Build, warning and behaviour breakage all count; follow-ups that only tidy up (style, refactor, feature extension) and revert-of-revert chains do not.

## curl — 23/30 = 0.77 → PASS (829 links)

- ✗ `e53523fef0` FIX: CI: move Azure jobs to GHA, fix fallouts, sshserver, runtests tweaks ← IND `bc72a78a11`: GHA/windows: enable HTTPS tests with stunnel
- ✗ `9fc4b2c78c` FIX: tool: move tool_ftruncate64 to tool_util.c ← IND `00bef95946`: tool_operate: don't truncate the etag save file by default
- ✓ `65405459d5` FIX: getparam: make --ftp-ssl work again ← IND `9e4e527735`: tool_getparam: switch to an enum for every option
- ✓ `3588df9478` FIX: ws: fix and extend CURLWS_CONT handling ← IND `fa3d1e7d43`: ws: corrected curlws_cont to reflect its documented purpose
- ✗ `e59540139a` FIX: cleanup: remove DOT_CHAR completely ← IND `f9c7ba9096`: netrc: make the code try ".netrc" on Windows as well
- ✓ `d439830621` FIX: curl tool: fix some OOM handling - f4853db5 follow-up ← IND `f4853db5e6`: curl tool: fix some OOM handling
- ✓ `18a45a51ba` FIX: http_aws_sigv4: fix scan-build "value stored to 'ret' is never read" ← IND `495d09810a`: aws_sigv4: fall back to UNSIGNED-PAYLOAD for sign_as_s3
- ✓ `80d93799a6` FIX: asyn-thread: fix mutex refs and unused variable in no-`HAVE_GETADDRINFO` builds ← IND `074048ae80`: asyn-thread: avoid the separate 'struct resdata' alloc
- ✓ `ad3fdbc0a4` FIX: smtp: Fix compiler warning ← IND `73cbd21b5e`: smtp: Moved parsing of url path into separate function
- ✗ `9863599d69` FIX: lib: introduce `CURL_ACCEPT()` ← IND `3bb5e58c10`: memory: make function overrides work reliably in unity build
- ✓ `4f42150d04` FIX: sendf: change Curl_read_plain to wrap Curl_recv_plain (take 2) ← IND `12e1def51a`: sendf: change Curl_read_plain to wrap Curl_recv_plain
- ✓ `61c92c7850` FIX: connect.c: Fixed compilation warning from commit 332e8d6164 ← IND `332e8d6164`: win32: Used centralised verify windows version function
- ✓ `a3d5b199f9` FIX: openssl: acknowledge SRP disabling in configure properly ← IND `68a5132474`: TLS: fix SRP detection by using the proper #ifdefs
- ✗ `6ee9e4bd47` FIX: cleanup: s/curl_debug/curl_dbg_debug in comments and docs ← IND `f3e0f071b1`: docs: Markdown and misc improvements [ci skip]
- ✓ `981e8f9b88` FIX: limit-rate: fix compiler warning ← IND `72a0f6251a`: limit-rate: kick in even before "limit" data has been receiv
- ✓ `942896fdd1` FIX: mbedtls: properly cleanup the thread-shared entropy ← IND `8b1d229835`: mbedtls: free the entropy when threaded
- ✓ `558dffe306` FIX: lib583: fix enum mixup ← IND `17fcdf6a31`: lib: fix -Wassign-enum warnings
- ✗ `454395ba1e` FIX: curl_osslq: fix missing include of url.h ← IND `4ccf3a31f5`: ngtcp2: fix coverity warning about result handling
- ✓ `e49efce12f` FIX: synctime: fix use of uninitialized buffer on non-Windows ← IND `b714c674f3`: synctime: tidy up, make it work on all platforms
- ✗ `c8d24d4e77` FIX: c-hyper: CONNECT respones are not server responses ← IND `d31915a8db`: test265: Use "connection: keep-alive" response header
- ✓ `d04bab8873` FIX: http: removed self assignment ← IND `b0143a2a33`: read_callback: move to SessionHandle from connectdata
- ✓ `272613df02` FIX: Revert "curl/system.h: fix compilation with gcc on AIX PPC and IA64 HP-UX" ← IND `c97648b550`: curl/system.h: fix compilation with gcc on AIX PPC and IA64 
- ✓ `78cef06847` FIX: openssl: Revert to less sensitivity for SYSCALL errors ← IND `0ab38f5fd6`: openssl: use strerror on SSL_ERROR_SYSCALL
- ✓ `3c3db98b6f` FIX: unit1612: fixed the inclusion and compilation of the HMAC unit test ← IND `3f74e5e604`: hmac: Added a unit test for the HMAC hash generation
- ✓ `1d4202ade6` FIX: url: Fix parsing for when 'file' is the default protocol ← IND `346340808c`: URL-parser: for file://[host]/ URLs, the [host] must be loca
- ✓ `528b284e4b` FIX: udpateconninfo: mark variable unused ← IND `e91e481612`: libcurl: #ifdef away more code for disabled features/protoco
- ✓ `9873431c6f` FIX: darwinssl: fix typo in variable name ← IND `6448f98c18`: vtls: add options to specify range of enabled TLS versions
- ✓ `a17f041bea` FIX: lib: fix variable undeclared error caused by `infof` changes ← IND `dac293cfb7`: lib: apache style infof and trace macros/functions
- ✓ `b1d08d295f` FIX: http: set content length earlier ← IND `8a16e54c0c`: http: ignore content-length if any transfer-encoding is used
- ✓ `273e9afcc8` FIX: sasl.c: Fix to avoid warnings introduced in commit d9ca9e9869e8 ← IND `d9ca9e9869`: sasl: Moved ntlm authentication message handling from smtp.c

## openssl — 26/30 = 0.87 → PASS (305 links)

- ✓ `d21db261c1` FIX: quic: fix off-by-one in QUIC_MAX_MAX_ACK_DELAY ← IND `35dc6c353b`: QUIC: Make more transport parameters configurable
- ✗ `869506ded6` FIX: ssl/statem/extensions_clnt.c: superfluous NULL check in tls_construct_ctos_psk() ← IND `ade10c5dbf`: ECH client side
- ✓ `4ad2d3ac0e` FIX: Revert "RT3425: constant-time evp_enc" ← IND `4aac102f75`: RT3425: constant-time evp_enc
- ✓ `223e0020e4` FIX: x_attrib: fix a memory leak ← IND `be5adfd6e3`: Support subjectDirectoryAttributes and associatedInformation
- ✓ `ab612a9baf` FIX: test/asn1_string_test.c: allocate tmpstring properly in asn1_string_new_not_owne ← IND `68c0321e90`: Provide ASN1_STRING_new_not_owned()
- ✓ `ebd8df0ed8` FIX: Fix build-break; 'make update' ← IND `bbd86bf542`: mem functions cleanup
- ✓ `c83eda8c22` FIX: Fix session tickets ← IND `9ceb2426b0`: PACKETise ClientHello processing
- ✓ `686cf15e9d` FIX: Fix merge error ← IND `6140f03653`: Add some new cipher ctrl constants
- ✓ `7de4770234` FIX: Revert "EdDSA: disallow verification from a pregenerated hash when in FIPS" ← IND `2d759937e2`: EdDSA: disallow verification from a pregenerated hash when i
- ✗ `df05f155a6` FIX: Fix some style nits in commit eee8a40 ← IND `eee8a40aa5`: Make the s_server command listen on IPv6 only when requested
- ✓ `979dc53001` FIX: s390x: Fix s390x_sha3_absorb() when no data is processed by KIMD ← IND `25f5d7b85f`: s390x: support CPACF sha3/shake performance improvements
- ✓ `c517ac4c3f` FIX: Revert "Modify test/afalgtest to fail if the afalg engine couldn't be loaded" ← IND `227a1e3f45`: Modify test/afalgtest to fail if the afalg engine couldn't b
- ✓ `c14003578a` FIX: Revert "fipsinstall: add ed_no_verify_digested option" ← IND `70b6d57fd9`: fipsinstall: add ed_no_verify_digested option
- ✓ `71c16698fa` FIX: Remove incorrect code inadvertently introduced through commit 59669b6ab. ← IND `59669b6abf`: Remove instances in libssl of the constant 28 (for size of I
- ✓ `5e34d64760` FIX: Fix the return value of OBJ_create ← IND `88a1fbb8d1`: reduce lock contention when adding objects to ADDED_OBJ hash
- ✓ `3206bb7082` FIX: Revert "fips: remove redundant RSA encrypt/decrypt KAT" ← IND `635bf4946a`: fips: remove redundant RSA encrypt/decrypt KAT
- ✓ `a21f77dbc9` FIX: crypto/evp: fix double free of tmp_keymgmt in sig/kem/asym init ← IND `ecb4757b37`: crypto/evp/m_sigver.c: fix potential double free on error pa
- ✓ `55a0adf220` FIX: x509_store: fix unreliable value of objs inside the second locked section ← IND `04589b59ef`: x509store: reduce lock contention in X509_STORE
- ✓ `29864f2b0f` FIX: Fix P-384 curve on lower-than-P9 PPC64 targets ← IND `85cabd9495`: Fix Minerva timing side-channel signal for P-384 curve on PP
- ✓ `6f13c02b7f` FIX: srtpkdf: cipher is written twice with the same value ← IND `5b310281af`: SRTP: Fixup settable input limits and test them.
- ✓ `c845ff070d` FIX: Revert "Don't allow an empty Subject when creating a Certificate" ← IND `e505f1e868`: Don't allow an empty Subject when creating a Certificate
- ✓ `d7e8f6f781` FIX: Fix potential memory leak on failure of dsa_gen_init() ← IND `47a80fd203`: pkeyutl.c: Avoid freeing pkey at multiple places
- ✓ `f219a1b048` FIX: Revert "RT4526: Call TerminateProcess, not ExitProcess" ← IND `9c1a9ccf65`: RT4526: Call TerminateProcess, not ExitProcess
- ✗ `327261c076` FIX: test/threadstest.c: Add checks for CRYPTO_THREAD_lock_new() ← IND `5f8b812931`: Add locking to atomic operations in rw/rcu tests
- ✓ `58eeb4350c` FIX: pkcs12: Do not forcibly load the config file ← IND `21f7a09ca2`: Convert jdkTrustedKeyUsage to be a pkcs12 cmd line option
- ✓ `b47b665016` FIX: Revert "Add VMS version of app_dirname()" ← IND `215a6730f1`: Add VMS version of app_dirname()
- ✓ `0f9fdefeb0` FIX: Fix an ENGINE leak in asn1_item_digest_with_libctx ← IND `6725682d77`: Add X509 related libctx changes.
- ✗ `653a770678` FIX: APPS: dgst: Support properties when signing ← IND `30b2c3592e`: APPS: dsaparam, gendsa: Support setting properties
- ✓ `bb78552ee1` FIX: Revert "Fix clang compile time error" ← IND `1608d658af`: Fix clang compile time error
- ✓ `11ed851db0` FIX: Fix and simplify error handling in (RSA/EC_kmeth)_new_method() ← IND `2bbf0baa95`: Add checks on CRYPTO_new_ex_data return value... with some a

## harfbuzz — 26/30 = 0.87 → PASS (271 links)

- ✗ `f253f06cf3` FIX: [fuzz] Add another fixed case ← IND `d383603976`: Limit OT::Lookup subtables (#2219)
- ✗ `8aae9a0e0d` FIX: Reapply "[gpu] Add fullscreen toggle (F key) to D3D11 demo" ← IND `ddcedece1d`: Revert "[gpu] Add fullscreen toggle (F key) to D3D11 demo"
- ✓ `4a93576bca` FIX: Revert "[map] Speedup for int types" ← IND `c1b75f5ff0`: [map] Speedup for int types
- ✓ `2764a61691` FIX: Revert "[gsubgpos] Use swap instead of move" ← IND `8a17cc4ecf`: [gsubgpos] Use swap instead of move
- ✓ `bdd8873fd8` FIX: Revert "[Indic] don't apply 'calt' by default in Indic shaper" ← IND `952121007c`: [Indic] don't apply 'calt' by default in Indic shaper
- ✓ `e6409d3905` FIX: Revert "[layout] Use a cache for main input ClassDef of (Chain)ContextLookups" ← IND `57d1c08739`: [layout] Use a cache for main input ClassDef of (Chain)Conte
- ✓ `6b72a4ddb0` FIX: Revert "[sanitize] Simplify(?) check_range" ← IND `af0b1ef8a7`: [sanitize] Simplify(?) check_range
- ✓ `858a022358` FIX: Revert "[cff] Optimize writing out Index offsets" ← IND `78ba23c587`: [cff] Optimize writing out Index offsets
- ✓ `9c27fe625f` FIX: Revert "[doc] Fix a couple of gtk-doc warnings" ← IND `ed42b2fcb5`: [doc] Fix a couple of gtk-doc warnings
- ✓ `e1cb3b155a` FIX: Revert "[aat] Remove set-digest" ← IND `832f199607`: [aat] Remove set-digest
- ✓ `dd8598c1c7` FIX: [test] Pass closure to hb_font_set_glyph_func() ← IND `c335fd7986`: In trampoline implementation of get_glyph(), don't destroy u
- ✓ `7c561dacc3` FIX: [myanmar] Fix unsafe usage of FLAG_SAFE() ← IND `f559c63307`: [indic] Implement Consonent_With_Stacker
- ✓ `5e4e21fce4` FIX: Revert "[Indic] Refactoring" ← IND `0831061efb`: [Indic] Refactoring
- ✗ `361a438658` FIX: Revert "Revert "[hb-directwrite] Don't load dwrit.dll dynamically"" ← IND `ecbe224743`: Revert "[hb-directwrite] Don't load dwrit.dll dynamically"
- ✓ `f5c32f8704` FIX: Revert "[VARC] Another long shot" ← IND `582af96b00`: [VARC] Another long shot
- ✓ `a98e4068e7` FIX: Revert "Hide symbols in hb-iter" ← IND `98f14c4cdb`: Hide symbols in hb-iter
- ✓ `2be836c151` FIX: Revert "[instancer] Preallocate coordinate maps from alloc pool as well" ← IND `3f71afe760`: [instancer] Preallocate coordinate maps from alloc pool as w
- ✓ `17c80035ad` FIX: Revert "[cplusplus] Internally allow using hb_unique_ptr with hb_free()" ← IND `b5f621b08d`: [cplusplus] Internally allow using hb_unique_ptr with hb_fre
- ✓ `d0163afb7b` FIX: Revert "Add operator char * to the naked array types as well" ← IND `db889c182e`: Add operator char * to the naked array types as well
- ✓ `39cf8e21be` FIX: [number] Add overflow checks used to be done in parse_bcd ← IND `1083df8b80`: Use hb_parse_double in CFF::dict_opset_t::parse_bcd
- ✓ `d00b88737e` FIX: Revert "[subset/closure] Batch recursions in scheduled stages" ← IND `f2aaeeb301`: [subset/closure] Batch recursions in scheduled stages
- ✓ `6a7a38521f` FIX: Revert "[aat] Support feature ranges" ← IND `1b7994cb3a`: [aat] Support feature ranges
- ✓ `73ee9c346f` FIX: Revert "[sanitize] Only check trailing edge of ranges" ← IND `e4856cf809`: [sanitize] Only check trailing edge of ranges
- ✓ `7d23e642a2` FIX: Revert "[aat] Remove dead code" ← IND `bf36f5c3a4`: [aat] Remove dead code
- ✓ `1d66cdcf77` FIX: Better fix for MSVC 2008 ← IND `b4c6113032`: Try fixing MSVC 2008 build
- ✓ `2dbd3d29d6` FIX: Fix hide-ignorables if font doesn't have space glyph ← IND `82b521aeb7`: Rewrite hide_default_ignorables
- ✓ `5eb7e7f646` FIX: Revert "[vector] Simplify Sort" and "More of the same" ← IND `de0b9a4664`: [vector] More of the same
- ✗ `b36b100ef1` FIX: [var] Remove byte_data_t; use hb_bytes_t ← IND `5690840ceb`: [map] Another try at fixing archaic clang
- ✓ `a973b5ce86` FIX: [GSUB] Further adjustments to mark-attachment vs ligation interaction ← IND `d1d69ec52e`: [GSUB] Don't ligate glyphs attached to different components 
- ✓ `0c70bc7f32` FIX: [skippy-iter] Fix two logic errors ← IND `42681bdb55`: [gsubgpos] No logic-change minor rewrite

## ndpi — 23/30 = 0.77 → PASS (57 links)

- ✓ `bb978907e6` FIX: STUN: fix detection of Google Voip apps (#2031) ← IND `2c7fb91794`: Hangout: detect Hangout/Duo/GoogleMeet/... in the STUN code 
- ✓ `81e42b748e` FIX: RTP: fix detection over TCP (#2462) ← IND `6127e04900`: support rtp/rtcp over tcp (#2422) (#2457)
- ✓ `4ff1bf29df` FIX: TLS: fix use-of-uninitialized-value error (#1573) ← IND `9040bc74c9`: TLS: fix stack-buffer-overflow error (#1567)
- ✓ `3047e286c0` FIX: Fix insert of ip addresses into patricia tree(s) (#1895) ← IND `d0b46dcf88`: Enhanced custom port definition and improved error reporting
- ✓ `ff8e1e197e` FIX: Fix syslog heap overflow introduced in 09fbe0a64a11b08a35435f516e9a19f7e0c20d7c. ← IND `09fbe0a64a`: Fixed syslog false positives. (#1577)
- ✗ `b24f5c4c0a` FIX: Fix memory leak about purged/expired flows ← IND `1a62f4c799`: Added ndpi_bin_XXX API Added packet lenght distribution bins
- ✓ `1e19b689c4` FIX: minor fix for https://github.com/ntop/nDPI/commit/0f94a46f868e6818790b0c278121c0 ← IND `0f94a46f86`: Merge branch 'mkfsn-bjnp-protocol' into dev
- ✓ `5e8c1ebbb7` FIX: fuzz: fix memory allocation failure logic (#1867) ← IND `29be01ef3a`: Add some fuzzers to test algorithms and data structures (#18
- ✓ `8db8c8ae34` FIX: Fix QUIC log and remove SoulSeek leftovers after b97dc6ba (#1351) ← IND `b97dc6baa4`: Removed outdated (and broken) soulseek dissector
- ✓ `7f510c10fe` FIX: Fix double free after b19bfa1e207a8d4972bfc701fde5d5c014f95383 ← IND `b19bfa1e20`: Fixes leaks in ndpi_add_host_url_subprotocol
- ✗ `441e43c167` FIX: Revert the revert of 2155dd9 after fixing ntopng Travis ← IND `4f72b954da`: Undoes 2155dd9 that breaks ntopng Travis
- ✓ `4f72b954da` FIX: Undoes 2155dd9 that breaks ntopng Travis ← IND `2155dd9153`: Add libcache to installed headers and removed relative impor
- ✓ `8da5f42fa0` FIX: Changed ndpi_ssl_version2str function call in ndpiSimpleIntegration. ← IND `23c0721538`: Fixed race condition in ndpi_ssl_version2str() caused by sta
- ✓ `57b8969a3d` FIX: Fix setting of flow risks on 32 bit machines (#1251) ← IND `19a29e1e22`: TLS Risks - Certificate Validity Too Long (#1239)
- ✓ `c0c9f649ed` FIX: Fix/restore some public defines (#2734) ← IND `6899f6c17c`: Added defines
- ✗ `79653f99e0` FIX: Internal gcrypt: fix memory leak ← IND `ef99eb674e`: Improved AES-NI presence check on Linux
- ✓ `49ed06a618` FIX: Revert "QUIC: refactoring" ← IND `50afd07f28`: QUIC: refactoring
- ✓ `399be12585` FIX: Small fixes after API cleanup done in c63446e59 (#2449) ← IND `c63446e592`: Cleaned up API
- ✗ `2619729661` FIX: fuzz: improve per-fuzzer introspector statistics (#2970) ← IND `f2bccee04e`: fuzz: an attempt to get better introspector stats (#2968)
- ✗ `b190dab6bc` FIX: Improve handling of HTTP-Proxy and HTTP-Connect (#1673) ← IND `938e89ca33`: Reimplemented 1kxun application protocol. (#1585)
- ✓ `59993e294e` FIX: EthernetIP: add missing initialization (#1448) ← IND `1e1cfb89d2`: Added EthernetIP dissector
- ✓ `333a6d60e8` FIX: TLS: fix a heap-buffer-overflow (#1356) ← IND `c3d1c69722`: Fixed heap-buffer-overflow in TLS dissector
- ✗ `214a2e5356` FIX: SIP: export metadata via json (#2630) ← IND `1bda2bf414`: SIP: extract some basic metadata
- ✓ `456bc2a52c` FIX: Tls out of order (#2561) ← IND `eb15b22e77`: Added fix for handling Server Hello before CLient Hello
- ✓ `b1f2f44a96` FIX: Fix export of TLS info. See cb7bd3890623c11d660301 (#3162) ← IND `cb7bd38906`: Extended quic dump
- ✓ `2b4321b5c3` FIX: Fixes invalid NDPI_MAX_SUPPORTED_PROTOCOLS ← IND `c77ec63ed8`: Added VidTO streaming service
- ✓ `d323bc77c2` FIX: Revert "nDPI fingerprint: we always calculate it at `internal_giveup()`" ← IND `096539c477`: nDPI fingerprint: we always calculate it at `internal_giveup
- ✓ `ac7a3669da` FIX: Fix value of `ndpi_protocol->protocol_by_ip` ← IND `a7c2734b38`: Remove classification "by-ip" from protocol stack (#1743)
- ✗ `5bb5bec477` FIX: Remove `struct ndpi_id_struct` (#1427) ← IND `91bb77a880`: A final(?) effort to reduce memory usage per flow (#1389)
- ✓ `947896ad7d` FIX: Fix configure script (after fb85dac9) (#1381) ← IND `fb85dac905`: Configure improvements Fixed invalid anomaly detection in rr

