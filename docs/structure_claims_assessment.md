# What label bias does to our STRUCTURAL claims (2026-11-13)

Everything measured today about label quality has been applied to the history predictors. This applies it to
the structural ones — and **the direction is opposite**, which changes how the programme's standing sentence
should read.

## The asymmetry

| claim family | where the label sits | effect of label noise |
|---|---|---|
| **history** (recidivism, entropy) | predictor **and** outcome both read off the label | errors are **correlated** → **inflation**, nulls are positive |
| **structure** (centrality, coupling, exposure) | predictor measured by the engine, independent of prose | errors are **independent** → **attenuation** toward the null |

Structure is measured from code; nobody's commit-writing habit changes a call graph. So structural
associations are not inflated by the labelling process — **they are shrunk by it.**

## How much is lost — measured

`tools/attenuation.py` plants a structural predictor with a known true lift over LOC, applies the measured
label error (sensitivity 0.41, specificity 0.83), and reports what survives:

| planted true lift | observed lift | **surviving fraction** |
|---|---|---|
| +0.255 | +0.079 | 31% |
| +0.121 | +0.036 | 30% |
| −0.036 | −0.015 | 43% |
| −0.160 | −0.051 | 32% |
| −0.286 | −0.080 | 28% |

**Roughly 30% of a real structural effect survives the trip through our label.** A true lift of +0.12 shows
up as +0.036. The fraction is stable across magnitudes and signs, which is what attenuation should look like.

## What this does to each kind of claim

**Our structural NULLS are weak evidence of absence — this is the big one.** "Aggregate structural exposure
= size", "centrality adds nothing", "new engine metrics add nothing": if a study could resolve an observed
lift of ~0.02–0.03, that corresponds to a **true** lift of **0.06–0.10**. For scale, the one history effect
we defended all day — curl's recidivism at **+0.071** — sits inside that band. **So "structure reduces to
size" is consistent with structural effects as large as the biggest effect we currently believe in.**

**TOST equivalence results are the most damaged.** An equivalence test declares "no bigger than Δ". Through
a 30%-transmitting label, an observed equivalence bound of Δ corresponds to a true bound of roughly **3Δ**.
Equivalence bounds set on the observed scale and interpreted on the true scale overstate the claim by about
three times.

**Positive structural findings are conservative, which is the safe direction.** Library-coupling surface
(shown on 21 repo×library pairs), platform-conditional density, fix-shaped grammar — attenuation means the
true effects are **larger** than reported, not smaller. Those claims are not threatened.

**Inverted findings survive best.** Centrality on small files reported AUC **0.26** — that is inverted, not
null. Attenuation pushes a statistic *toward* 0.5; it cannot manufacture inversion. That finding is robust.

**The LAWS structural results are untouched.** LAW-1 to LAW-5 never use a fix label — they are computed on
call graphs over time. LAW-2's survival and LAW-5's contradiction stand exactly as they did.

## The standing sentence has to change

It was: *history predicts, structure describes.*

Both halves are now weaker, for opposite reasons:

- **"History predicts"** was measured through correlated error that **inflates**. After correction only curl
  survives, at +0.071 and a ~1.2× margin.
- **"Structure describes"** was measured through independent error that **attenuates** by ~70%. The nulls
  that justify "describes" are too weak to carry it.

An honest replacement: **"history's advantage over size is smaller than we thought and survives in one repo;
structure's absence of advantage is not established, because our outcome transmits only about a third of any
real structural signal."**

## Caveats

- **Assumes error independent of structure.** Plausibly it is not: large, central, heavily-reviewed files may
  attract more announcement, which would make the error differential and could push either way. Untested, and
  it is the main threat to this analysis.
- One repo's file-size distribution (curl, 451 files in the frame).
- Sensitivity/specificity are the external benchmark's pooled figures; per-repo values vary and sphinx's
  anchor-measured recall of 0.10 would attenuate far harder than 0.41 does.

## What would fix it

Not a better structural metric — **a better outcome**. At sensitivity 0.75 (what a diff-reading model
reaches) rather than 0.41, the surviving fraction rises substantially and the same studies could resolve
effects three times smaller. **The structural nulls deserve a re-run against a better label before they are
believed**, and that is a stronger argument for the labelling work than anything on the history side.
