# Agent-authored vs human-authored commits (2026-11-13)

If the fix label is unreliable because *announcement is a human convention*, then commits written by an agent
under a documented convention should behave differently. gitgalaxy is a repository whose history is
overwhelmingly agent-authored, so the question is directly testable.

`tools/agent_vs_human.py` over 6,631 non-merge commits on `origin/main`:

| group | commits | says a fix word | **cites an issue** |
|---|---|---|---|
| **agent** (Claude trailer) | 4,124 (62%) | 0.183 | **73%** |
| **human** | 2,507 (38%) | 0.118 | **4%** |

## The headline, and it is not what I expected

**Agent commits are far more LINKABLE and far less KEYWORD-LEGIBLE.**

They cite an issue **73% of the time against 4% for humans** — an 18× difference, and issue-citation is the
strongest label tier we have. But on the ground-truth leg, of **82 agent commits citing an issue labelled a
bug, only 7 use a fix word — recall 0.085.** For comparison, human-written commits in curl sit at 0.41–0.57.

The reason is visible in the subjects. An agent writes:

```
Harness: a template store's extra region instances are seeded and dumped per instance (Part of #7965)
det/CICS: record READ events for READ TOKEN and a refused READ (Part of #7965)
```

Precise, descriptive, issue-linked — and containing no fix word at all.

**So the problem does not solve itself as agents write more code. It changes shape.** Keyword labelling gets
*worse* on agent-authored history; link-based labelling gets dramatically better. Any pipeline that leans on
message keywords will degrade as agent authorship rises, while a cascade that ranks structured links first
will improve. That is an argument for the cascade independent of anything measured earlier today.

## A methodological finding: agent announcement variance is not measurable this way

τ, the between-author announcement spread, is **undefined for the agent group** — not because agents are
consistent, but because **agent commits are authored under the maintainer's git identity** with a trailer
marking the agent. The author variable collapses to one person. Human commits in the same repo give
τ = 1.69, the largest in any repo measured today.

So "agents have lower announcement variance" **cannot be concluded from this data**, and I am not concluding
it. Testing it needs a corpus where agent commits carry distinct author identities.

## Limits, which are serious

- **54 issues resolved, 18 labelled a bug, 82 agent commits citing them.** Small.
- **The human comparison is empty on the ground-truth leg**: zero human commits cite a bug-labelled issue,
  because humans here barely cite issues at all. So the recall contrast is agent-vs-curl, not agent-vs-human
  *in the same repo* — a weaker design than intended.
- **gitgalaxy is idiosyncratic**: one maintainer, agent commits under his identity, and a house convention
  (`Part of #N`) that most projects do not share. Generalising needs external agent-heavy repos, which is
  being researched separately.
- **The fix-word rate difference (0.183 vs 0.118) is not interpretable on its own** — agents and humans here
  do different work, so a rate difference need not be a convention difference.

## What this changes

1. **The cascade is the right architecture, and more so over time.** Rank links above keywords, because the
   link signal is strengthening and the keyword signal is weakening.
2. **"Does the problem solve itself?" — no.** Keyword-based labelling of agent-written history is *worse*
   than of human-written history, measured.
3. **Our correction machinery has a shelf life in one direction only**: the announcement-propensity model is
   about human convention and will matter less as agent share rises; the link-resolution work matters more.
