# NM-G — untested function metrics vs which function a fix touches, at equal size (SCORED)

- FREC's events and candidates; scored = later-half events; strata = `loc` tertiles within each event
- events: curl 435, ndpi 51; entered: **3** → two-sided α = 0.01/3 = 0.0033; failed entry: is_public, is_documented

| metric | curl lift [CI] (n events) | nDPI lift [CI] (n) | verdict |
|---|---|---|---|
| `func_fan_in` | +0.003 [-0.033, +0.039] (408) | +0.011 [-0.085, +0.113] (47) | no signal |
| `func_fan_out` | +0.132 [+0.090, +0.169] (408) | +0.143 [+0.029, +0.263] (47) | **SIGNAL** (higher = more often fixed) |
| `func_pagerank` | +0.005 [-0.031, +0.045] (408) | -0.033 [-0.152, +0.089] (47) | no signal |

Runtime 36s · bootstrap 5000 rounds over events, seed 2982.
