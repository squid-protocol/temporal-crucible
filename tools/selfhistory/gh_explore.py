#!/usr/bin/env python3
"""Explore GitGalaxy's PRs, issues and labels for repair-radius label quality (exploratory). Needs gh (read-only) and a local mirror.
Step 1: gh api --paginate "repos/squid-protocol/gitgalaxy/issues?state=all&per_page=100&sort=created&direction=asc" --jq '.[] | {n:.number,title:.title,state:.state,reason:.state_reason,user:.user.login,utype:.user.type,created:.created_at,closed:.closed_at,labels:[.labels[].name],pr:(.pull_request!=null),merged:(.pull_request.merged_at),comments:.comments,assoc:.author_association,body:((.body//"")[0:4000])}' > gh/items.jsonl
Step 2: git --git-dir=mirror.git log --first-parent --no-renames --name-only --format='@@%H%x09%s' <tip> > gh/commit_files.txt
Step 3: this script's analyses (link keywords, causal wording, deterministic PR kinds, epic parents, locatable bug issues); see docs/self_evolution/pr_issue_labeling_exploration.md for the numbers."""
