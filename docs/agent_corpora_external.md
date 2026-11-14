# External agent-heavy corpora, and what they do to our finding (2026-11-13)

A research agent measured 14 candidate repos directly from commit metadata (bare clones, `--since=2024-06-01`,
classified by agent marker in author email + name + body). Its numbers are measurements, not vendor claims.

## First: a threat to our own measurement, checked and survived

**The squash trap.** In squash-merge repos ~99% of commits end in `(#1234)` — the *PR* number, not an issue.
A naive issue-citation counter reports ~99% linking for humans, agents and dependabot alike.

**gitgalaxy is squash-merged** — 6,080 of 6,631 commits end in a bare `(#N)`. But `agent_vs_human.py`'s regex
is `(?:part of|fixes|closes|resolves)\s+#(\d+)`: it **requires a semantic verb** before the number, and a
trailing `(#1234)` has none. So the 73%/4% split is genuine semantic linking and is not a squash artefact.
Checked rather than assumed, and the measurement stands.

## But the external repos correct the interpretation

Our claim was "agent commits are far more linkable". Across five external repos it **does not generalise**:

| repo | agent | agent vs human link | agent vs human fix-word |
|---|---|---|---|
| **grafana/grafana** (n=1,150) | Claude Code | **19.6% vs 3.4%** | **12.9% vs 16.0%** |
| dotnet/runtime (n=3,584) | Copilot | 28.0% vs 13.1% | 23.7% vs 21.8% — **parity** |
| dotnet/maui (n=1,057) | Copilot | 30.3% vs 24.1% | 38.2% vs 42.7% |
| **browser-use** (n=642) | Claude | 3.1% vs 1.2% | **41.4% vs 21.7% — reversed** |
| **aider** (n=3,149) | aider | **0.4% vs 1.4%** | 15.9% vs 21.4% |
| tdd-guard (n=573) | Claude Code | **3.7% vs 13.5%** | 20.9% vs 21.9% |

**aider is the control that kills the strong reading.** Agents there link issues 0.4% of the time — *less*
than humans. tdd-guard is the same. So **agent authorship by itself does not produce issue links.** The
linking comes from the project's PR and CI workflow, which agents follow because they are told to. gitgalaxy
has a house `Part of #N` rule; aider does not; the agents behave accordingly.

**Only grafana reproduces our pattern in both directions** — more linking, fewer fix words — and it is the
one large sample where the agent is Claude Code specifically. **dotnet/runtime shows fix-word parity** and
**browser-use shows the reverse**, so the fix-keyword half of our finding is the weaker half.

## Revised claim

Not *"agent commits are more linkable and less keyword-legible."*

**"Where a project's workflow creates issue links, agents follow that convention far more reliably than
humans do; where it does not, they do not link at all. The fix-keyword gap does not replicate consistently."**

That is a smaller claim and a better one: it locates the mechanism in the *convention*, not the model — and
it keeps the practical consequence intact, because a labelling pipeline still gets more link signal from an
agent-heavy repo **that has a linking convention**.

## Our human 4% is a property of this repo, not of humans

Rath et al., *Traceability in the Wild* (ICSE 2018, pp. 834–845): **"on average only 60% of the commits were
linked to specific issues"** across six OSS projects, with large per-project disparity. Our 4% human rate is
far below that range and should be reported as a repo property.

## Corpora worth using

- **dotnet/runtime + dotnet/maui** — primary external replication: large, genuinely mixed (17–26% agent),
  both arms under identical conventions. MIT.
- **grafana/grafana** — the Claude-Code-specific replication, n=1,150. AGPL-3.0; note it if message text is
  redistributed.
- **aider, tdd-guard, browser-use** — negative controls that break the claim. Include them or a reviewer will.
- **AIDev** (HF `hao-li/AIDev`, Zenodo 10.5281/zenodo.16919272, CC BY 4.0) — 1.7M agent commit messages with
  an explicit `agent` column and 100,050 PR→issue links. **No human control arm**; mine one from the same
  repos.
- **CommitChronicle** (JetBrains, 10.7M commits, pre-agentic) — a clean human baseline for keyword recall.
- **Bot ground truth** (BIMAN, Zenodo 10.5281/zenodo.3610206) — to strip dependabot from the human arm, which
  is 4–13% of commits in half the sample and has near-zero fix words.

**Not useful**: SWE-bench / SWE-Gym / SWE-smith / Nemotron — all derived from *human* PRs or synthetic bugs,
none contains agent commit messages pushed to real repos. DevGPT is chat-assisted human work.

## Prior-work warning — acts on the registration rule

**MSR 2026's entire mining challenge is AIDev**, and accepted papers already compare developer vs agent PRs.
Closest head-to-head: **Pham & Ghaleb, "Code Change Characteristics and Description Alignment: Agentic versus
Human Pull Requests" (MSR 2026, arXiv:2601.17627)** — 33,596 agent vs 6,618 human PRs; agent *commit*
messages align better with the diff (0.72 vs 0.68), agent *PR* descriptions align worse. **It measures
semantic alignment, not issue-reference or fix-keyword rate**, so our question is still open — but a full
prior-work sweep is required before any registration here.

**Also load-bearing**: Robbes et al., *Agentic Much?* (arXiv:2601.18341) identifies agents **by their message
conventions**. If agent conventions shift, that detection method degrades — a validity threat to the whole
adoption literature, and a point worth making.

## Unverified, carried forward

microsoft/vscode has 2,224 agent PRs by search but the clone failed twice — no commit-level numbers. Agent
shares are **lower bounds** (Codex mostly does not sign; inline completions leave no trace). The AIDev row
counts came via a delegated reading and should be re-checked before quoting.
