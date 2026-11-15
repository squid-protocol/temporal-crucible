# Discovery findings, 2026-11-15 (exploratory; NOT confirmatory; discovery repos: curl, impacket, ripgrep, sqlmap, tigerbeetle)

Data: quarterly snapshots (`--every 3m`, engine history disabled): impacket 77 (2003-2026), ripgrep 43, sqlmap 71, tigerbeetle 25;
commons-lang scan unfinished at write time. Scripts in `analysis/`. Identity in the settle-in and growth tables = (file path followed
through git `-M50%` file renames, name, nth).

## 1. Rename / move detection (impacket, 47 snapshot pairs with dead and born functions)
Ground truth = source text: body from git at each commit, own name masked, 4-gram token shingles Jaccard >= 0.85, >= 12 tokens, unique names.
Truth pairs 2,196: 2,134 moves (same name, other file), 45 renames in the same file, 17 renames + move (62 renames). 60% of "deaths" in
these pairs are text-identical code that reappeared elsewhere; 2018-07 alone: 848 of 932 deaths.
| matcher | precision | recall moves | recall renames |
|---|---|---|---|
| SFS structural twins (name-blind, reciprocal best hit + ratio + 1% decoy FDR), dead vs born pools | 94% (638/680) | 30% | 11% (6/55) |
| lens distance + path + call sets (RRF), iterative call-set extension | 82% | 30% | 19-23% |
| mutual best inside the git-renamed file pair, lens distance + relative line order | 82% (302 accepted pairs had no text truth, unverified) | 84% | 66% (41/62) |
Why structure alone stalls: 89% of true pairs keep an identical measurement tuple, but only 33% have a unique match among born functions
(23% have 2-5 identical candidates, 33% have 6+). 87% of true moves are git file renames; 10% move across files without a file rename.
Limits: one Python repo; 62 renames; truth misses renamed-and-heavily-edited code; the layered fingerprint (call set + control-flow skeleton)
was approximated by call-name sets, not run as in the LAY study; no literal "match-extend-lattice" implementation was found in the repos.

## 2. What changes after birth (functions born after the first snapshot; 24,682 followed)
Share of survivors identical to their birth state in size/args/keyword counts (engine measurements, NOT source text): age 4 quarters
median 83% (impacket 84, ripgrep 86, sqlmap 82, tigerbeetle 51); age 8: 72% (72, 73, 78, 38). Callee set unchanged at 8: 84%. Archetype kept at 8: 95%.
Median LOC ratio at 4 quarters 1.00. Chance a survivor changes in a quarter: age 1 6-11% (tigerbeetle 24%), age 8 3% (tigerbeetle 18%).
Functions alive >= 9 quarters that never changed: impacket 45%, ripgrep 54%, sqlmap 51%, tigerbeetle 26%.
Callers: most functions are born with no resolved callers (55-65%), and 1-4% gain one within a year; mean callers 0.93 -> 0.98 (impacket) over a year.
Call-link recall is about half (GitGalaxy docs), so in-degree is a lower bound.

## 3. Repo-level growth (rename-aware identity)
Median quarter: births 0.8-1.1% of the population, deaths 0.0-0.1% (young tigerbeetle: 12% births per quarter).
Top 10% of quarters hold 45-71% of births and 70-82% of deaths in the three older repos (21% / 23% in tigerbeetle).
65-73% of births are in new files; 47-77% of deaths are whole files disappearing.

## 4. Rename detection redone with the NEW tools (doom-dna + popan main 3e2ade4; same impacket text truth)
Tools located: `doom-dna/followups/seed-and-extend/measure.py` (FGW reciprocal-best-hit seeding in `composition` mode, delta calibration,
3-hop call-graph extension, zero names) and `structural-fingerprint-scanner` in popan main (`blind.py`, `twins.py`, standardized
`keyword_mode`: presence / counts / smoothed_density / composition).
| matcher (keyword mode) | precision vs text truth | recall moves | recall renames |
|---|---|---|---|
| sfs twins, OLD worktree (unspecified mode, min 6 lines) | 94% | 30% | 11% |
| sfs twins, NEW (smoothed_density, min 10 lines; truth restricted to >= 10 lines: 1,300 moves, 40 renames) | 95% | 43% | 15% |
| extension only, all unchanged functions as anchors (composition), 6 hops | 27% | 22% | 51% (31/61) |
| git file renames + in-file mutual best (structure + line order) | 82% | 84% | 66% |
Full Seed-and-Extend (FGW seeding) timing: 15 s at n=552, ~100 s at n=1,135, roughly cubic: a 6,000-function snapshot would take hours.
It was designed for ~1-2k function ports (`--max-funcs 15000`), so it is not usable as-is on whole snapshots of a large repo.
Extension alone fails on mass moves (few unchanged neighbours to vote); it does find half the renames but with low precision.
Not run: the DOOM-style cross-language sweep itself, `sfs timeline`, or the horizontal-transfer tooling.

## 5. Cascade and the lineage ledger (sqlmap, ripgrep, tigerbeetle, impacket; quarterly snapshots; scripts in analysis/, ledgers in ledger/)
Cascade stages: certain identity (same path, name, count) -> name in the git-mapped file -> unique name among dead/born -> in-file
structure + order -> sfs twins -> call-graph extension (anchors = everything linked so far, cos >= 0.9). Every function-instance gets a
lineage ID carried forward with the stage that linked it.
Rename recall on UNAMBIGUOUS truth (b claimed by exactly one dead function): sqlmap 90%, tigerbeetle 87%, impacket 89%, ripgrep 60% (n=10;
76 of ripgrep's 86 "renames" were interchangeable templated getters: many dead functions map to one new function after name masking).
Stage 1 does nearly all the work for renames; twins add 0-2 points, extension 0-5 with a precision cost.
LINK AUDIT (text similarity of the two bodies, strong >= 0.85 / weak < 0.5): name_in_mapped_file 78-93% strong; in_file_structure 18-48% strong,
25-70% weak (no distance threshold: any mutual best in a file pool was linked); twin mixed; call_graph_extension 0-9% strong, 78-95% weak (mostly false).
Design consequence: structure proposes, source text verifies; do not link on extension.
Effect of identity rule (naive path+name -> A names+git file context -> B A + text-verified structure -> C everything):
deaths sqlmap 2582 -> 1407 -> 1113 -> 852; ripgrep 3150 -> 1228 -> 1132 -> 900; tigerbeetle 4375 -> 3341 -> 2642 -> 1438; impacket 4993 -> 1745 -> 1120 -> 846.
Median lifetime (quarters) naive -> B: sqlmap 24 -> 41, ripgrep 12 -> 19, tigerbeetle 4 -> 6, impacket 16 -> 44. Births in brand-new files barely move (69-84% -> 71-76%).
So naive path+name identity overcounts deaths by 40-78% (rule B vs naive) in all four repos; earlier survival/hazard/settle-in numbers computed under naive identity are biased.
Not done: chain-level accuracy, splits/merges/extractions, head-to-head vs git log -L / CodeShovel (different granularity), dense sampling, git-independent file matching.

## 6. Quality experiments (ledger v2), 2026-11-15
Comment text (GitGalaxy docstring field: 17-44% of functions >= 3 lines have >= 4 words) as INDEPENDENT evidence against the body-text verdict:
links with body similarity >= 0.85 agree on comments 99%, 0.7-0.85 97%, 0.5-0.7 91%, 0.3-0.5 74%, < 0.3 26%. By stage (links with comments): name_in_mapped_file 99%,
twin 83%, name_unique 82%, in_file_structure 68%, call_graph_extension 27% (body strong 1%) -> extension is mostly false and is dropped.
Ledger v2 = structure proposes (comment-aware tie-breaking), body text OR comments verify (body >= 0.5 or comment Jaccard >= 0.5), extension dropped.
Recall on unambiguous truth: renames sqlmap 96%, tigerbeetle 91%, impacket 80%, ripgrep 70% (n=10); moves 97-100% (name-defined, partly circular).
Comments rescue only 4-30 links per repo (the ambiguous ones); totals barely move vs v1 (deaths sqlmap 1089 v 1113, tigerbeetle 2613 v 2642, impacket 1145 v 1120, ripgrep 1114 v 1132).
Sampling density (impacket 2018, 14 monthly snapshots, chain vs one jump over the year incl. the 2018-07 reorg): same successor for 98.1% of 3,857 functions, 1.8% gone in both,
3 disagreements; 2 lineages born and gone inside the window. Quarterly is enough for identity here.
Splits/merges/extractions/inlinings (text containment >= 0.7, same git-mapped file only), among the births/deaths the ledger leaves unlinked:
sqlmap 1/1/7/2, ripgrep 1/1/13/2, tigerbeetle 10/14/61/4, impacket 51/49/17/0 -> explains 0.3-1.6% of unlinked births and 0.4-5.1% of unlinked deaths.
Not done: synteny disambiguation (comments + in-file order only), chain-level accuracy, git-independent file matching, cross-file splits/merges, head-to-head vs git log -L / CodeShovel.

## 7. How repos move, on the v2 lineage ledger (quarterly; sqlmap, ripgrep, tigerbeetle (6 y, fast), impacket; analysis/movement.py)
GROWTH: median quarter births 0.7 / 0.3 / 10.5 / 1.2 % of population (tigerbeetle young), true deaths 0.1 / 0.0 / 4.2 / 0.0 %, moves+renames 0.07 / 0.05 / 3.0 / 0.16 %.
Top 10% of quarters hold: births 55/70/21/47%, deaths 69/85/26/73%, moves+renames 83/92/23/78% (event-driven in mature repos, steady in the young one).
BIRTHS: 66-73% in new files, 27-33% added to existing files, 0-2% split/extracted from a function. DEATHS: whole file removed 47-77%, deleted from a surviving file 23-52%,
merged/inlined 0-4%, split 0-1%.
SURVIVAL (born after start): median life 41 / 19 / 6 / 44 quarters; 68-86% still alive at the end; death chance per quarter at ages 1/2/4/8: sqlmap 1.5/1.2/0.4/2.3%, ripgrep 1.8/0.8/1.6/0.6%,
tigerbeetle 5.4/6.5/3.8/1.2%, impacket 0.6/0.6/0.5/0.4%.
SETTLING IN (engine measurement tuple identical to birth): after 1/2/4/8 quarters: sqlmap 91/88/83/79, ripgrep 96/93/89/73, tigerbeetle 83/74/59/46, impacket 93/91/87/80 %.
Chance of change in a quarter at age 1/4/8: 9/5/3, 4/2/5, 17/16/14, 7/3/2 %. Never changed over >= 9 quarters: 60 / 56 / 41 / 63 %.
WIRING: mean callers at birth -> 4 quarters later: 1.52->1.57, 0.69->0.69, 1.38->1.63, 1.13->1.28; born uncalled, gain a caller within a year: 1 / 0 / 4 / 2 %.
Top-1% hubs still top-5% a year later: lineage 98/94/80/98% vs naive identity 96/80/76/93%.
Caveats: 4 repos; "unchanged" = same measurements, not same text; call-link recall about half; ledger rename recall 70-96%, so a few renames are still counted as death + birth;
cause labels for split/merge/extract use same-file text containment only.

## 8. Keywords over time, 7 repos (sqlmap, ripgrep, tigerbeetle, impacket + C: redis, libgit2, curl; quarterly; analysis/kw_split.py, kw_report.py)
Density per kLOC, yearly curves, slope per year. Direction counts across 7 repos (rising/falling): print 2/5, bailout 2/5, branch 1/6, flux 1/6, io 2/5, def_test 6/1, def_safety 3/4, safety_neg 3/4, pointers 4/3, casts 3/4.
Print falls in 5 of 7 (curl 8.8 -> 2.1, redis 10.2 -> 6.9, tigerbeetle 6.0 -> 2.0); the exceptions are the two Python tools (sqlmap, impacket). Safety does NOT rise everywhere:
def_safety rises in curl 4.5->15.5, redis 11.3->31.8, sqlmap 9.4->32.6 and falls in libgit2, tigerbeetle, ripgrep, impacket; safety_neg falls in curl 11.9->2.2.
Turnover vs rewriting (density change over the life, whole repo vs inside surviving code): curl print repo -6.7 / survivors -12.4 (old code had print removed, retrofit R 0.31);
curl and libgit2 retrofit leaders are alloc, cleanup, print (R 0.22-0.31) = the families registered as predicted-high in TURN-H6; pointers in all three C repos change by turnover
(retrofit R 0.03-0.08; redis repo +108 vs survivors -107, libgit2 -216 vs -9, curl +81 vs +4): new code differs from old, old code is rarely rewritten.
Survivors carry 2-20% of line movement (curl 2%, libgit2 2%, ripgrep 2%, sqlmap 20%).
Caveats: 7 repos, 3 of them C; density change inside survivors is a summed pair-to-pair figure, not a clean total; tigerbeetle has an empty first snapshot (no repo-level figure).

## 9. Tree-sitter: what changes inside surviving functions (C: libgit2, redis, curl; analysis/ts_edits.py, ts_report.py)
Method: each ledger-linked function's text at the two commits (git, start_line+loc), parsed with tree-sitter-c; edits classified by node-type, callee and signature deltas. C/.h only.
Text changes in 5.2% (libgit2), 5.7% (redis), 18.3% (curl) of function-quarters; 4-12% of those are comments/whitespace only. Of code edits: signature changed 15-22%; guard (if) added 11-22% vs removed 6-8%;
cast added 3-9%; goto 2%; alloc/free call changed 5-10%; #if changed 2-9%; print call added/removed < 2%.
Pointer syntax (* and &) changes in 22-25% of code edits; in those, a guard changed in 43-51%, NULL use changed in 25-34%, signature in 26-33%, alloc/free in 10-16%; pointer use rose in 63-66%.
Most-added/removed calls are API migrations, not logic: libgit2 git_buf_* -> git_str_*, assert -> GIT_ASSERT_ARG, giterr_set -> git_error_set, git_oid_fromstr -> git_oid_from_string;
curl free/malloc/strdup/Curl_safefree -> curlx_free/curlx_calloc/curlx_safefree, fprintf/printf -> curl_mfprintf, + DEBUGASSERT; redis redisAssert -> serverAssert, redisLog -> serverLog, dict iterator API swap.
By era: curl print-call removal 3.0% of code edits in the 2000s -> 0.4% in 2015s; libgit2 guard-added 17% (2010s) -> 7% (2020s).
Caveats: edits are function-quarter diffs (several edits fold into one); "pointer syntax" in the first table includes field access (-> and .), the narrower figures in the pointer paragraph exclude it; pointer use rising may track function growth;
unchanged text is skipped, so reformat-only edits count as comments/whitespace only; calls are by name only, with no resolution of macros.

## 10. Mass-migration sweeps and tree-sitter for Python / Rust / Zig (analysis/ts_edits2.py, sweeps.py)
Sweep = the same call/macro removed or added in >= max(10, 1%) of a quarter's code-edited functions. Migration = an old name removed and a new name added in the same functions (co-occurrence >= 40% of the smaller side).
Share of code edits inside a sweep: libgit2 44%, tigerbeetle 38%, impacket 27%, sqlmap 22%, redis 22%, curl 21% (36% in the 2025s, 4% in the 2000s), ripgrep 4%.
Sweeps are one-quarter events: nearly every migration lands in a single quarter (a few take two). Examples: libgit2 git_buf_free -> git_buf_dispose (757 functions, 2018-07), then -> git_str_dispose (719, 2021-10), assert -> GIT_ASSERT_ARG (539, 2021-01);
curl free -> curlx_free (384, 2025 Q4), fprintf -> curl_mfprintf (329 over 2025 Q2-Q4); redis redisLog -> serverLog (116, 2015 Q3); sqlmap logger.warn -> logger.warning (291, 2022-07), range -> xrange (2012), Python-2-to-3 style moves;
impacket ''.join -> b''.join (2019), datetime.utcnow -> now (2025); tigerbeetle camelCase -> snake_case (isSet -> is_set, constSlice -> const_slice, 2023-2025) and interface_call -> call (173, 2025-10).
Chains: one name is migrated more than once (libgit2 git_buf_free -> dispose -> git_str_dispose).
Organic edits (outside sweeps) change signatures more often (libgit2 20% vs 9% in sweeps; impacket 14% vs 4%) and add guards (libgit2 14% vs 8%). In curl, print/log calls are added or removed in 6-7% of sweep edits and under 1% of organic edits.
Caveats: sweep threshold is a discovery choice; call names are by text, macros unresolved; Zig/Rust/Python grammars via tree-sitter-language-pack with function slices from the engine's start_line/loc; ripgrep has too few events to say much.

## 11. KW-4 measured: sweeps explain the retrofit (C: libgit2, redis, curl; analysis/kw4.py)
H6 retrofit share R_f = |survivor drift| / (births + deaths + |drift|); H6 gap = mean R over {alloc, cleanup, print, safety_neg, io} minus mean R over {branch, pointers, args, macros, def_safety}.
Re-computed with the edits that fall inside a sweep (same call/macro changed in >= max(10, 1%) of a quarter's code-edited functions) removed from the survivor drift:
curl gap +0.196 -> -0.026 (alloc 0.28 -> 0.02, print 0.31 -> 0.01, cleanup 0.26 -> 0.06); libgit2 +0.081 -> -0.003 (alloc 0.22 -> 0.02, cleanup 0.22 -> 0.01).
redis never showed the gap (-0.032 before, -0.011 after), so it does not test the idea. 7,000 of 33,665 curl code edits and 9,300 of 21,200 libgit2 edits are sweep edits.
Reading: the predicted-high families look "retrofitted" because a few quarters rename or swap allocation, cleanup and print wrappers across many functions; outside those quarters they are no more rewritten than branches or pointers.
Caveats: 3 C repos, one of them curl (discovery only); sweep membership comes from tree-sitter call names, the retrofit shares from engine keyword counts; sweep thresholds are discovery choices.

## 12. Held-out check of the lineage ledger (packaged sfs ledger; 6 repos never used in the analyses above; analysis/heldout_eval.py)
Repos (quarterly): expat, libxml2 (C), scapy, sphinx (Python), commons-io (Java), prometheus (Go). LAWS-panel repos are not in the local pool, so none was touched.
Truth = function text (4-token shingles, own name masked, comments stripped) matched across dead and born functions, similarity >= 0.85, many-to-one pairs dropped; independent of the structure and comment evidence the ledger proposes with.
MOVES (same name, different file): right 7,056 of 7,132 = 98.9%; wrong 8 (0.11%); missed 68 (1.0%).
RENAMES (new name): right 711 of 842 = 84.4%; wrong 50 (5.9%); missed 81 (9.6%). By repo: expat 100% (7), scapy 89%, commons-io 86% (16 wrong), sphinx 89%, prometheus 91%, libxml2 50% (28 wrong).
Where the wrong renames are: libxml2's 28 wrong renames are 27 from one quarter (2003-07, SAX.c split into SAX2.c and legacy.c): the old name (startElement) survives as a thin wrapper in legacy.c, so the ledger followed the name and its copied comment while the text truth follows the code (xmlSAX2StartElement).
commons-io: 14 of 16 wrong are in_file_structure links between look-alike JUnit test methods in the same file (testSkip vs testCopyLarge_Skip). Both are failures of the same kind: near-identical siblings. Excluding the one libxml2 quarter, wrong renames are 22 of 758 (2.9%).
Evidence behind accepted structure-proposed links (name_unique, in_file_structure, twin): body and comments agree 1-51%, body only 19-99%, comments only 0-30% (libxml2 30%, commons-io 10%, prometheus 7%, sphinx 3%, scapy 1%, expat 0%).
Samples accepted on comments alone read as real continuations (xmlAddDocEntity xml_entities.c -> entities.c, render_partial builder.py -> html.py), where the body was refactored.
Chain vs direct jump (quarterly chain vs one direct link, same start function): over 1 y same function 78-99.9%, disagree 0-0.8%; over 2 y disagree 0-1.1%; over 4 y disagree 0-2.0%. The rest is "both gone" (functions that really died) or "chain only"
(0.1-7%: the chain finds the descendant a single long jump cannot). Errors do not accumulate fast: the chain is at least as complete as the direct jump.
Reading: for the registered study the ledger is good enough to correct the identity bias (moves are near-perfect), but renames carry ~3-6% wrong links, concentrated in near-duplicate siblings (test methods, API-wrapper splits). The LAWS unit files exclude tests, which removes most of the commons-io-type errors.
Caveats: thresholds were not set before looking at these numbers, so no pass/fail is claimed; text truth under-counts true renames where the body was rewritten; six repos.
