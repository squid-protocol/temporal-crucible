# LABEL CARD — fix-label precision per repo, and the rule that binds on it

**The rule.** No study may use a fix label whose precision on that repo is unpublished. A label
below the **0.70** gate is reported as descriptive, or not used as an outcome at all.
`tools/label_card.py --assert <repo> <label>` is how a tool checks before it runs.

**Source.** docs/otherfix_audit.md (CGR eight: round 1 2026-11-11, confirmatory round same doc); docs/otherfix_audit_pilot.md (curl, nDPI, openssl, 2026-11-13)

**Transfer.** docs/fixlabel_transfer.md: 98-100% of the LAWS history-DB `fix` set appears in xc's events for seven of eight repos (ripgrep 72%), so the precision measured on xc's pipeline carries to the LAWS flag with a stated basis rather than an assumption.

| repo | lang | raw precision | n | fit? | v3c precision | n | fit? |
|---|---|---|---|---|---|---|---|
| libxml2 | c | **0.80** | 30 | ✓ | **0.86** | 22 | ✓ |
| postgres | c | **0.77** | 30 | ✓ | **0.74** | 19 | ✓ |
| redis | c | **0.73** | 30 | ✓ | **0.75** | 16 | ✓ |
| ndpi | c | **0.67** | 30 | ✗ | **0.68** | 25 | ✗ |
| libgit2 | c | **0.63** | 30 | ✗ | **0.60** | 15 | ✗ |
| curl | c | **0.63** | 30 | ✗ | **0.80** | 25 | ✓ |
| sphinx | python | **0.60** | 30 | ✗ | **0.78** | 23 | ✓ |
| openssl | c | **0.50** | 30 | ✗ | **0.80** | 25 | ✓ |
| prometheus | go | **0.40** | 30 | ✗ | **0.83** | 12 | ✓ |
| commons-lang | java | **0.27** | 30 | ✗ | **0.70** | 20 | ✓ |
| ripgrep | rust | **0.27** | 30 | ✗ | **0.82** | 11 | ✓ |

**3 of 11 repos** clear the gate on the raw label; **9 of 11** on v3c.

## What this card already changed

HR-1 reported recidivism beating size at pooled **+0.082** using the raw label. The two repos
carrying its largest lifts are the two with the **worst** precision here — commons-lang at **0.27**,
where nearly three in four 'fix' commits do not repair behaviour. Under v3c, commons-lang reverses
(+0.143 → −0.015) and the pooled result falls to **+0.009**, below its own registered bar.
The audit predated the run by two days. Nothing required reading it. That is what this card fixes.

## Known gaps

- **libgit2 fails both labels** (0.63 raw, 0.60 v3c) and is the one repo HR could not evaluate at all.
  It needs a better label before it can carry an outcome.
- Precision is measured **from the commit subject**. A label validated against the diff would be
  stronger and nobody has paid for one.
- Recall is known only on the tuning set (v3c keeps ~81% of real fixes there) and is **not**
  separately measured on the confirmatory sample. A study whose claim depends on recall must say so.
