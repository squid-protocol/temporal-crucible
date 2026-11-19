> **Status: design and prototype, not shipped.** Draft for GitGalaxy's `docs/wiki/`, written 2026-11-19 against the evolution-report prototype (`tools/report/evolution_report.py`). Exploratory unless a line says otherwise.

# Evolution report: where it stands now

A short list of facts about the repository as it is today, each read directly from the data (no model and no prediction), plus two lists of hubs. The same facts are available as JSON, so an assistant or a script can use them.

## The facts
Size and languages, the largest directories, the last twelve months of activity (commits, authors, edits, sweeps, fixes, and the change on the year before), the median age of the code, the most-called and most central functions, a former hub, the largest function, the most repaired function, comment habits, and the long-run mix of work. A building / maturing / maintenance label is **not** computed yet: it needs thresholds calibrated on a reference set of projects.

## Two ways to rank a hub
- **Most called (callers):** how many functions call it. Easy to explain.
- **Most central (PageRank):** its importance in the call graph; it also counts callers that are themselves important, so it can pick out a function with few callers that sits at a junction. The two lists often differ; the report says how many of the top ten appear in both.

## Measured behavior (exploratory)
- Hubs are a stable skeleton: in most repositories the top 1% by callers are still in the top 5% a year later (80 to 98% in our earlier study, with identity tracked across renames). Here the report prints the repository's own figure, counting removed functions as gone.
- Hubs grow richer as new code calls them, and a function born with no callers usually still has none a year later (95 to 100%).
- Hubs change more than other files, not less; files in call cycles or with heavy coupling get more later fixes beyond size, churn and their own fix history.

## Limits
- Call-graph accuracy depends on the language: checked against libclang for C (hubs, ranks and coupling agree); sensitive to overloaded names in Java; Go and Python not evaluated yet; Rust records about a third of resolvable calls. The report prints this next to the lists.
- Identity is (file, name); a moved or renamed function looks like a removed one, so persistence is a lower bound.
- Function names come from the scanner; macros that wrap calls (such as logging macros) can hide or move a hub (a function that was called from thousands of sites can drop when callers switch to a macro).

## What to do about it
Read the hub lists as "load-bearing code": changes there reach many callers, and the report's repeat-spot and repair figures show whether they also get repaired often. A former hub is a place where callers have moved on; check what replaced it.
