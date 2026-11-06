# XC label-precision audit (binding gate: ≥ 0.70 per class × repo)

Seeded random samples (seed 2982, 30 per class × repo), judged by the author from subject + harvester reason.
**Regression** is correct only if a recent change broke something, or it is a revert. **Extrinsic** is correct only if the subject names an environment change (platform/OS/arch, named compiler, C standard, libc, toolchain, or a dependency version/API). **Latent** is correct only if the commit is a plausible fix of the reported defect.

## Round 1 (rules v1, tool commit e23b3db)

### curl · regression — 26/30 = 0.87 → PASS

- ✓ `f54a4aa9a3` imap: avoid freeing constant string
- ✓ `9afd97022e` smtp: Fixed dot stuffing being performed when no new data read
- ✗ `53b4dfe405` examples: delete unused includes
- ✗ `29b3b1ae6d` wolfssl: fix cipher list, skip 5.8.4 regression
- ✓ `c2c8948190` Curl_http_connect: detect HTTPS properly after CONNECT
- ✓ `e7512e78c2` tool_operate: repair --rate
- ✓ `797b21068e` ssh: add two missing state names
- ✓ `93b0d907d5` Revert "Proxy-Connection: stop sending this header by default"
- ✓ `fe880475ed` url: Fixed memory leak in setstropt_userpwd()
- ✗ `ac57e69b58` strdup: do Curl_strndup without strncpy
- ✓ `e65187e188` ngtcp2: fix picky compiler warnings with wolfSSL for QUIC
- ✓ `e251e858b9` vtls: fix missing multissl version info
- ✓ `8a4ce7d0f5` smtp: Fixed inappropriate free of the scratch buffer
- ✓ `6a095da1f3` transfer: avoid calling the read callback again after EOF
- ✓ `40f3c18e6a` curl: set CURLOPT_NEW_FILE_PERMS if requested
- ✓ `b8e0fe19ec` vtls: provide curl_global_sslset() even in non-SSL builds
- ✓ `5f6b9244ce` macos: fix Apple SDK bug workaround for non-macOS targets
- ✓ `30daac9f2f` cli_hx_download: fix compiler warnings about format strings
- ✗ `82ba603da4` content_encoding: make Curl_all_content_encodings allocless
- ✓ `e7de80e8ce` tls: fix compile issues on old-linux CI
- ✓ `f8af8606a5` http_negotiate_sspi: Fixed endless unauthorized loop in commit 6bc76194e8
- ✓ `416ecc1584` url: Fixed crash when no username or password supplied for proxy
- ✓ `6512e93be1` tool: Fixed incorrect return code with --version from commit c10bf9bb36
- ✓ `cbbccb8b3a` mbedtls: re-enable an error check
- ✓ `11ab3f8918` win32: Fix compilation warnings from commit 40c921f8b8
- ✓ `72c14bd6f0` ftp.c: fix ftp active connects which got broken with commit fdf157abdf
- ✓ `d9abebc7ee` Revert "url: a short host name + port is not a scheme"
- ✓ `17162dcb27` build: fix libssh2 + `CURL_DISABLE_DIGEST_AUTH` + `CURL_DISABLE_AWS`
- ✓ `7433a6eb3f` urldata: restore bitfield to unsigned int
- ✓ `1027d52e7d` schannel: when importing PFX, disable key persistence

### curl · extrinsic — 10/30 = 0.33 → FAIL (withheld; amendment 1)

- ✗ `f7ef60c13f` fix compiler warning: external definition with no prior declaration
- ✓ `9e80356dd5` Luck Call made win32 password prompting support backspace
- ✗ `57119495da` curl tool: fix compiler warning
- ✗ `2cd0c2d244` conncache: fix compiler warning
- ✓ `c688166066` check for and require tld.h to be present before libidn usage is activated in the build, since libid
- ✓ `ea94afe318` ldap: silence potential unused variable warning (OS400)
- ✗ `7a83e1d1d4` quiche: make POSTFIELDS posts work
- ✗ `989e6dffc5` mbedtls: fix build with disabled proxy support
- ✗ `ad388a7d37` tool_getparam.h: Fixed compilation warning
- ✗ `e9ffa9a3b8` Fixed a few memory leaks in OOM conditions. Made libssh2 logging more verbose when debugging is enab
- ✗ `e547bfa933` - Rob Crittenden brought a fix for the NSS layer that makes libcurl no longer   always fire up a new
- ✗ `8a7d58378b` fix compiler warning
- ✗ `6a0ed81e67` Fix compiler warning
- ✓ `40b6206085` test3026: add support for Windows using native Win32 threads
- ✓ `b9cd73c76d` Fix GnuTLS compile warning. Risking breakage with some older version of GnuTLS?
- ✓ `5f53c9d94a` lib: Fix AIX build failure
- ✓ `3317160c19` Fixed sample to compile for Windows platform.
- ✗ `835e4cb1d5` asyn-ares: fix data race warning
- ✗ `ebadeff0ca` fix compiler warning: zero used for undefined preprocessing identifier
- ✗ `fc77790bcd` nss: fix a bug in handling of CURLOPT_CAPATH
- ✗ `4146ce8267` bug report #508235 identified a non-working Location: following, and this little fix seems to correc
- ✗ `64f328c787` Add support for using nettle instead of gcrypt as gnutls backend
- ✗ `d1e7d9197b` libssh2: add SHA256 fingerprint support
- ✓ `11ea10355a` mbedtls: PSA can be used independently of TLS 1.3 (avoid runtime errors)
- ✗ `71f8fdee81` curl_sasl.c: Fixed compilation warning when cyptography is disabled
- ✗ `dd576194ce` tool_getparam.h: fix compiler error
- ✗ `15f832d1c2` fix compiler warning
- ✗ `74f911d463` krb5: fix compiler warning
- ✓ `0ffec4272a` the missing part of Gisle Vanem's connect-timeout fix for win32
- ✓ `fd49ba6c18` another lame change in an attempt to fix the moot gcc 3.4 warning

### curl · latent — 30/30 = 1.00 → PASS

- ✓ `9c91ec7781` idn: switch to libidn2 use and IDNA2008 support
- ✓ `686d54baf1` idn: tweak buffer use when converting with macidn
- ✓ `3da249e1f0` gsasl: fix potential double free
- ✓ `ec9cc725d5` ftp: CURLOPT_FTP_SKIP_PASV_IP by default
- ✓ `247d890da8` TLS: switch off SSL session id when client cert is used
- ✓ `81f151c912` header_callback: strip off file path separated with backslashes
- ✓ `af32cd3859` http: prevent custom Authorization headers in redirects
- ✓ `9069838b30` security:read_data fix bad realloc()
- ✓ `55e1875729` http_proxy: restore the protocol pointer on error
- ✓ `600a8cded4` url: make the updated credentials URL-encoded in the URL
- ✓ `a86efdd7ca` url: fix connection reuse for starttls protocols
- ✓ `73b65e94f3` fopen: create short(er) temporary file name
- ✓ `f3a24d7916` Curl_auth_create_plain_message: fix too-large-input-check
- ✓ `8ef147c436` ftp,imap,pop3,smtp: reject STARTTLS server response pipelining
- ✓ `5c7da89d40` nss: return error if seemingly stuck in a cert loop
- ✓ `50c7f17e50` SMB: rangecheck values read off incoming packet
- ✓ `d9d0167278` openssl: make the OCSP verification verify the certificate id
- ✓ `39ce47f219` telnet: check sscanf() for correct number of matches
- ✓ `ea71c3b6b6` openldap: handle Curl_sasl_continue() returns better
- ✓ `7b9613fa9b` ngtcp2: fail handshake directly
- ✓ `48d7064a49` cookie: apply limits
- ✓ `27959ecce7` x509asn1: unittests and fixes for gtime2str
- ✓ `5c225384b8` url: detect proxy changes read from environment
- ✓ `914aaab915` urlapi: reject percent-decoding host name into separator bytes
- ✓ `a64e3e5993` setopt: when POST is set, reset the 'upload' field
- ✓ `b09c8ee157` vtls: add 'isproxy' argument to Curl_ssl_get/addsessionid()
- ✓ `39d1976b7f` ldap: call ldap_init() before setting the options
- ✓ `4f20188ac6` smb/telnet: do not free the protocol struct in *_done()
- ✓ `8732ec40db` aprintf: detect wrap-around when growing allocation
- ✓ `0e120c5b92` netrc: 'default' with no credentials is not a match

### ndpi · regression — 23/30 = 0.77 → PASS

- ✓ `b1f2f44a96` Fix export of TLS info. See cb7bd3890623c11d660301 (#3162)
- ✓ `79653f99e0` Internal gcrypt: fix memory leak
- ✓ `4f72b954da` Undoes 2155dd9 that breaks ntopng Travis
- ✓ `3047e286c0` Fix insert of ip addresses into patricia tree(s) (#1895)
- ✓ `ff8e1e197e` Fix syslog heap overflow introduced in 09fbe0a64a11b08a35435f516e9a19f7e0c20d7c. (#1579)
- ✗ `adbba69988` Removed false positives from CoAP protocol Improved DNS detection Added misisng default DropBox port
- ✓ `1e19b689c4` minor fix for https://github.com/ntop/nDPI/commit/0f94a46f868e6818790b0c278121c081a63c9eeb
- ✓ `59993e294e` EthernetIP: add missing initialization (#1448)
- ✓ `81ca06b0c7` websocket: `ndpi_set_detected_protocol()` should be called only once
- ✓ `739dfc54b0` Kerberos: fix Undefined-shift error (#1516)
- ✗ `43bf9df219` Improved testing application Removed warning from the quic dissector Travis now runs regression test
- ✗ `4a6c525db8` Improved fuzz_ndpi_reader which supports now SMP/MT w/o race-coniditions.
- ✓ `7f510c10fe` Fix double free after b19bfa1e207a8d4972bfc701fde5d5c014f95383
- ✗ `54d23c2632` dns: support an opt-in custom detection port (#3232)
- ✗ `d6701e8979` Build ndpiReader and run regression tests.
- ✓ `6e9dce357b` Added ndpi_guess_undetected_protocol_v4() to restore logic that was removed in https://github.com/nt
- ✓ `456bc2a52c` Tls out of order (#2561)
- ✓ `399be12585` Small fixes after API cleanup done in c63446e59 (#2449)
- ✓ `a772e18977` Fix a warning (#1125)
- ✓ `ac7a3669da` Fix value of `ndpi_protocol->protocol_by_ip`
- ✗ `2619729661` fuzz: improve per-fuzzer introspector statistics (#2970)
- ✓ `b24f5c4c0a` Fix memory leak about purged/expired flows
- ✓ `56b6c7ed93` Fixed thread crash caused by commit 29cd6ef9942188633b79b5c1fe62360f048a6450
- ✓ `333a6d60e8` TLS: fix a heap-buffer-overflow (#1356)
- ✗ `214a2e5356` SIP: export metadata via json (#2630)
- ✓ `441e43c167` Revert the revert of 2155dd9 after fixing ntopng Travis
- ✓ `b40732d8a5` Fix an harmless memory leak
- ✓ `fea3991ad1` Fix some invalid memory reads (#1350)
- ✓ `2b4321b5c3` Fixes invalid NDPI_MAX_SUPPORTED_PROTOCOLS
- ✓ `398ad8e5ff` Fix for #1230 (#1235)

### ndpi · extrinsic — 12/30 = 0.40 → FAIL (withheld; amendment 1)

- ✗ `efc5630378` Fix compilation warning
- ✗ `929cbbb7fc` Add compiler warnings and fix them
- ✓ `50006516b3` Custom rules: fixes for Windows (#2130)
- ✗ `2134f83948` Warning fixes
- ✓ `bac82eeb8e` Avoid c99 complains about function prototypes
- ✗ `e44834e0c5` Fixed warning
- ✗ `70536876f2` Fix strin truncation warning. Replace `strncpy` with `memcpy` as the length is always known. (#2954)
- ✓ `e1efee8594` Added check for searching JSON-C in home directory if not installed Fixed type
- ✗ `c9ae313bd8` Warning fix
- ✗ `ec2e9db2e5` fuzz: fix a warning
- ✗ `42fcb011ad` Warning fix
- ✓ `736a80f9ce` Fix libgcrypt(-light/-internal) compile error. (#1465)
- ✗ `cf07c92538` Dropbox and apple improvements Fixed warning
- ✗ `5100cc0eae` Added checks for missing protocol initialization Fixed missing LOG_ERR initialization Fixed logging 
- ✓ `6b4814401c` Fix domain encoding (in `ndpi_encode_domain()`) on big-endian systems (#3110)
- ✓ `68c7159a72` fix(tests/unit): fix MinGW build in serializeProtoUnitTest (#3161)
- ✓ `3e4ab39b52` Add support for LTO and Gold linker (#1812)
- ✓ `32d02836f0` fixed syntax for gcc compiler
- ✗ `fb74785282` Fix some warnings about unused variables/functions (#1160)
- ✗ `d398b0aba6` Simplified makefile Fixed warning
- ✓ `a173d3e98f` configure: fix usage of libgpg-error with `--with-local-libgcrypt` (#1472)
- ✗ `93f01e614f` Added new functions defined in #279 for exporiting them in shared libs Disabked some search dissecto
- ✓ `c345b3c7af` EthernetIP: fix integer conversion on big-endian archs (#1477)
- ✗ `95f4d0b852` Fix a warning
- ✗ `197a9a6cfc` Extend CodeQL configuration and fix two warnings (#1816)
- ✗ `dd8be1fcb1` Fix some warnings reported by CODESonar (#2227)
- ✗ `54517d8e04` Fix a warning and restore a unit test result (#2379)
- ✗ `25a4569e67` Fix undefined behavior (detected by gcc):
- ✓ `174cd739db` Fix warnings on OpenWrt CCs, caused by the memcpy builtin. (#1741)
- ✓ `3d21c33409` Compilation fix when JSON-C is not present

### ndpi · latent — 21/30 = 0.70 → PASS

- ✓ `ddb9aa0f95` TLS: fix parsing of certificate elements (#1910)
- ✓ `90e08b3568` Fixes #845
- ✓ `59a9bdeb55` SoftEtehr: fix a heap-buffer overflow (#1705)
- ✗ `312dc424bd` Added NDPI_PROTOCOL_NTOP assert and removed percentage comparison (#2460)
- ✗ `de16fd35aa` Hangout: avoid useless lookups in the protocol tree (#1755)
- ✓ `c7efd0892f` Fixed buffer overflow in amazon video dissector
- ✓ `226a9abf22` Additional memory bounds checks
- ✓ `7051acc0b5` Fixed off-by-one error in Kerberos protocol.
- ✓ `9f050fa0a6` TLS, H323, examples: fix some memory errors (#1414)
- ✗ `8dbd591053` Waring fix
- ✗ `46d96e7f32` Added checks for DGA detection
- ✗ `5424d14424` DNS: another fix about the relationship between FPC and subclassification (#2709)
- ✓ `98f2d3a73c` Adds bound check for IRC
- ✗ `634457615c` Updated TLS support
- ✓ `e9195589d2` Checks enough data for UDP header
- ✓ `8b6a00f84b` SoftEther: fix heap-buffer-overflow (#1691)
- ✓ `4f370fe7c4` Adds netbios bound check
- ✓ `37abe0daea` Added boundary check
- ✓ `c4f50b2cda` HTTP: fix heap-buffer-overflow error (#1564)
- ✓ `c793e16050` Added extra TLS memory boundary checks
- ✗ `29d9c2d2c8` Reworked HTTP header processing workflow
- ✓ `d5005f584c` Raknet: fix heap-buffer-overflow (#1531)
- ✗ `6cbc8d1471` fuzz: fuzz loading of external protocols lists (#2897)
- ✗ `34ad06fef5` Compilation fix
- ✓ `241af016e9` Added check for spotify payload lenght
- ✓ `4976d93d4e` Fix buffer overread in ndpi_search_setup_capwap
- ✓ `8dcaa5c0e1` DNS: fix TTL check and sync unit test results (#1594)
- ✓ `96f8942f75` reader_util: fix parsing of IPv6 extension headers (#1453)
- ✓ `b0bf66c436` Added offset check in kerberos dissector
- ✓ `2aec630202` Fix use of uninitialized value in TLS

### openssl · regression — 22/30 = 0.73 → PASS

- ✓ `c50fd0f959` Fix BN error reporting
- ✓ `8ca8fc4804` Fix compile failure
- ✗ `5cd1792016` Deprecate SPT threading support on NonStop.
- ✓ `32a33dae78` ssl_do_config(): Check for NULL name argument
- ✓ `c517ac4c3f` Revert "Modify test/afalgtest to fail if the afalg engine couldn't be loaded"
- ✓ `b8f1c116a3` Don't free the BIGNUM passed to BN_mpi2bn
- ✓ `1dccccf333` Fix enable-weak-ssl-ciphers
- ✓ `6f13c02b7f` srtpkdf: cipher is written twice with the same value
- ✗ `9d856e4d7f` Avoid needless casting away of const in X509_VERIFY_PARAM_get1_ip_asc
- ✓ `f1b17245b6` Revert "fips: add no digested option to FIPS provider"
- ✓ `854ea3aa93` quic_channel.c: avoid clipping in ack_delay_exponent/disable_active_migration setters
- ✓ `47bbaa5b60` Revert "OPENSSL_NO_xxx cleanup: RFC3779"
- ✓ `ed371b8cba` Revert "Reduce stack usage in tls13_hkdf_expand"
- ✓ `582e2ed271` Revert "Reuse strndup(), simplify code"
- ✓ `927e704e8c` Partially Revert "Remove curve448 architecture specific files"
- ✓ `f6a103133a` Revert "Avoid duplication."
- ✗ `63ae847679` x509_vfy: remove redundant stack allocation
- ✓ `8419baf312` Fix winstore provider to work with recent decoder changes
- ✗ `80b7e49c27` Use mmap for pkeyutl -rawin and dgst one-shot input
- ✗ `50e34aaba3` test/ectest.c: add regression test for RT#4284.
- ✗ `3d3a147a81` test: DTLS 1.3 forged DTLSPlaintext alert regression tests
- ✓ `f6d3359d65` apps/cmp.c: Fix bug on -path option introduced in commit 3c9d6266ed85
- ✓ `f690ef151c` s390x assembly pack: fix various aes modes performance regression
- ✓ `c4fa1f7fc0` Fix regression with session cache use by clients
- ✓ `b250fc7be7` Deprecate SHA and MD5 again.
- ✗ `df05f155a6` Fix some style nits in commit eee8a40
- ✓ `f7d1d2a479` Fix enable-sctp
- ✗ `b73a574325` crypto/idea/i_cfb64.c: condition 'n < 0' can never be met after doing 'n = n & 0x07'
- ✓ `29864f2b0f` Fix P-384 curve on lower-than-P9 PPC64 targets
- ✓ `686cf15e9d` Fix merge error

### openssl · extrinsic — 9/30 = 0.30 → FAIL (withheld; amendment 1)

- ✓ `c063f2c5ec` Various Win32 related fixed. Make no-krb5 work in mkdef.pl .
- ✓ `856f2aa7be` test/pkcs12_api_test.c: fix failure on MinGW
- ✗ `4f98cbabde` avoid compiler warning
- ✓ `27fa9d33e1` Fix builds on riscv64 using musl
- ✗ `c06648f7f0` Fix C code generate by 'openssl dsaparam -C'.
- ✗ `b50e1bd3c3` In Message-ID: <003201bfb332$14a07520$0801a8c0@janm.transactionsite.com>, "Jan Mikkelsen" <janm@tran
- ✗ `111a6e2a23` Fix multiple ; warning.
- ✗ `69d1d5e6ce` Fix ASN1 warnings.
- ✓ `9362638b08` print SSL session, fix build warnings on OpenBSD.
- ✗ `e1a4814cd4` fix formatting so that the file can be view with any tab-width
- ✗ `807fd8bc09` Fix stub definitions for no-deprecated config
- ✓ `3bfd99bfbb` [Forgotten commits?] Changes to have OpenSSL compile on OS/2. Contributed by "Brian Havard" <brianh@
- ✗ `f920c5b590` Fix signed/unsigned warnings.
- ✗ `decdb980de` Fix deprecation inconsisteny w.r.t. CRYPTO_mem_debug_{push,pop}()
- ✗ `4d49b68504` Crypto: Add deprecation compatibility declarations for SHA* message digest functions
- ✗ `8c040c086c` Fix some memory leaks in the openssl app
- ✓ `e7a68985d5` fix compilation on Solaris
- ✓ `5951e840d9` Fix no-ocsp on Windows (and probably VMS)
- ✓ `7fd1ca723a` Support session information on FreeBSD.
- ✗ `7daf0efad9` Fix warning.
- ✗ `45106caab7` fix signed/unsigned comparison warnings
- ✓ `3327c8d6f3` Fix aix compile error in cmp_ctx_test.c
- ✗ `f43cb3f809` Fix a "defined but not used" warning when enabling ssl-trace
- ✗ `e8f48dbacc` Add missing semicolon to make compiler happy, and switch back from MemCheck_start() to CRYPTO_mem_ct
- ✗ `e774adb593` Fix --strict-warnings build
- ✗ `c0455cbb18` Fix escaping when using the -subj option of "openssl req", document 'hidden' -nameopt support. (Robe
- ✗ `af1cb47e65` fix warnings
- ✗ `d62bf89cbb` Fix more shadowed variable warnings
- ✗ `e9eda23ae6` Fix warnings and various issues.
- ✗ `b3f3407850` Use new common flags and fix resulting warnings.

### openssl · latent — 27/30 = 0.90 → PASS

- ✓ `c426c281cf` Do not ignore empty associated data with AES-SIV mode
- ✓ `91f7361f47` Reject excessively large primes in DH key generation.
- ✓ `5741d29a5f` Check the tag on EVP_Cipher() finalize: Poly1305 and OCB AEADs
- ✓ `2c57351ccd` dtls: reset init_off before retransmitting a message
- ✓ `c46ecc3a55` Sanity check record length before skipping explicit IV in TLS 1.2, 1.1 and DTLS to fix DoS attack.
- ✓ `b8e5bb958e` Handle signature_algorithms_cert extension in key-only context
- ✓ `1716003376` Fix DTLS anonymous EC(DH) denial of service
- ✓ `70428eada9` Check that we have enough padding characters.
- ✓ `9cb177301f` Fix memory issues in BIO_*printf functions
- ✓ `ec061bf8ff` Make DH_check_pub_key() and DH_generate_key() safer yet
- ✓ `88f2a4cf9c` CVE-2010-4180 fix (from OpenSSL_1_0_0-stable)
- ✗ `3dd814ac4d` Fix SRTP compile issues for windows
- ✓ `ea8fc4c345` Verify ASN1 object's types before attempting to access them as a particular type
- ✓ `53b78f2a49` Check return code of UTF8_putc
- ✗ `98d132cf6a` Add a macro for testing assertion in both debug and production builds
- ✓ `6028c0654e` Report truncation in oneshot `openssl dgst -sign`
- ✓ `f297baaa11` ec: make ossl_ec_scalar_mul_ladder() scalar padding constant time
- ✓ `84f73f79af` Check the received uncompressed certificate length to prevent excessive pre-decompression allocation
- ✓ `48c054fec3` Excessive allocation of memory in dtls1_preprocess_fragment()
- ✓ `36cf45ef3b` Correctly calculate the length of SM2 plaintext given the ciphertext
- ✓ `feba02f391` Fix crash in dtls1_get_record whilst in the listen state where you get two separate reads performed 
- ✓ `b48310627d` Don't try and verify signatures if key is NULL (CVE-2013-0166) Add additional check to catch this in
- ✗ `e194fe8f47` From HEAD:
- ✓ `b79aa05e3b` Avoid PKCS #1 v1.5 signature attack discovered by Daniel Bleichenbacher (CVE-2006-4339)
- ✓ `248385c606` Follow on from CVE-2014-3571. This fixes the code that was the original source of the crash due to p
- ✓ `ee6243f394` Avoid dangling ptrs in header and data params for PEM_read_bio_ex
- ✓ `684400ce19` Fix various certificate fingerprint issues.
- ✓ `3244aa4b9d` Avoid possible buffer overflow in buf2hex conversion
- ✓ `1cbf663a6c` sanity check
- ✓ `40e48e5458` Elliptic curve scalar multiplication with timing attack defenses

