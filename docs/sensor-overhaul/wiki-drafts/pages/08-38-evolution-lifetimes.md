> **Status: design and prototype, not shipped.** Draft for GitGalaxy's `docs/wiki/`, written 2026-11-19 against the evolution-report prototype (`tools/report/evolution_report.py`). Exploratory unless a line says otherwise.

# Evolution report: function lifetimes

How long functions last, read from their presence in the quarterly scans. A function is identified by its file and name; one that moves or is renamed counts as a death and a birth, so lifetimes are lower bounds.

## What the report shows
- **Median age of today's functions**, counted from their first scan (or the first scan of the project).
- **Survival curves** (Kaplan-Meier, which handles functions that are still alive): the share still present after a number of years, for functions **born during the scans** and for those **already there at the first scan** (their true age is unknown, which is why the two are kept apart).
- **Half-life** of a new function when the curve reaches 50%.
- **Longest-lived functions that have since gone**, and the **largest functions present since the first scan**.

## Reading it
If 93% of new functions are still there after a year and 77% after five, most new code is kept; a steep first-year drop means churn in recent work. A large share of today's code older than the scan window shows a stable core.

## Limits
- Quarterly scans: a function born and removed within one quarter is never seen.
- Identity is (file, name): a moved file looks like many deaths and births. The growth chart's "moved" bars show how much of this there is.
- The first scan is not the first commit: functions already there have unknown true age.

## What to do about it
Treat very long-lived large functions as the load-bearing core: change them carefully. Treat functions that die within a year as a sign of experiments or rewrites; if that is most of new code, expect churn.
