# SC stage 1 — discovery screen: file metrics × fix class (EXPLORATORY; selection rule per sc_protocol.md)

- repos curl / nDPI / openssl; 448 candidate forms, **225** pass the entry rule
- D = within-bin AUC(candidate) − within-bin AUC(total_loc), 50 size bins; R = recall@20 lift over the stronger size order

## Passing candidates per class (D and R same sign and > 0 on all three repos), ranked by min R

### latent: 0 pass

| candidate | dir | D curl / nDPI / openssl | R curl / nDPI / openssl |
|---|---|---|---|

### extrinsic: 1 pass

| candidate | dir | D curl / nDPI / openssl | R curl / nDPI / openssl |
|---|---|---|---|
| `platform_cond /line` | + | +0.114 / +0.024 / +0.109 | +0.119 / +0.048 / +0.133 |

### regression: 2 pass

| candidate | dir | D curl / nDPI / openssl | R curl / nDPI / openssl |
|---|---|---|---|
| `raw_churn_freq /line` | + | +0.112 / +0.152 / +0.138 | +0.014 / +0.200 / +0.128 |
| `change_entropy /line` | + | +0.107 / +0.140 / +0.150 | +0.013 / +0.150 / +0.145 |

### other-fix: 2 pass

| candidate | dir | D curl / nDPI / openssl | R curl / nDPI / openssl |
|---|---|---|---|
| `risk_churn /line` | + | +0.089 / +0.139 / +0.126 | +0.027 / +0.136 / +0.103 |
| `pct_vec_churn /line` | + | +0.068 / +0.121 / +0.102 | +0.025 / +0.088 / +0.018 |

## Frozen for stage 2 (top 5 per class after the |ρ| ≤ 0.8 de-duplication)

```json
{
 "latent": [],
 "extrinsic": [
  {
   "candidate": "platform_cond /line",
   "direction": "higher = review first"
  }
 ],
 "regression": [
  {
   "candidate": "raw_churn_freq /line",
   "direction": "higher = review first"
  }
 ],
 "other-fix": [
  {
   "candidate": "risk_churn /line",
   "direction": "higher = review first"
  },
  {
   "candidate": "pct_vec_churn /line",
   "direction": "higher = review first"
  }
 ]
}
```

**Instrument check (P per line recovered for extrinsic): PASS**

Runtime 104s.
