> **Status: design and prototype, not shipped.** Draft for GitGalaxy's `docs/wiki/`, written 2026-11-19 against the evolution-report prototype. Exploratory unless a line says otherwise.

# Evolution report: kinds of functions

GitGalaxy gives every function a **type** (its "function archetype") from a structural signature: how many decisions per line, how many arguments, how pointer- or struct-heavy it is, and so on. The report shows what a code base is made of, how the mix changed, and whether functions keep their type.

## The types
The engine's current set has 14 named types, for example **Compute Cores** (dense algorithmic logic), **C Struct Operations** (data-structure logic on structs and pointers), **Many-Argument Workhorses** (large procedural functions), **Parameter Forwarders** (thin glue that forwards to other code), **Encapsulated Accessors** (getters and setters), **Defensive Guards** (validation and error handling) and **Interface Declarations**. Definitions live in `gitgalaxy/standards/analysis_lens.py` (`FUNCTION_ARCHETYPE_DEFINITIONS`) and are printed in the report. Scans made by an older engine can carry older names (for example "Stateful Encapsulated Methods"); the report marks them.

## What the report shows
- The mix today, with meanings.
- The mix over time (top eight types, the rest grouped).
- Retention: of the functions present at both ends of a one-year window, the share that kept their type, split by whether the function was edited during the window. For files, the same with the file's composition label (named after the function type that dominates the file).
- The most common changes of type.

## Measured behavior (exploratory unless noted)
- A label is deterministic: an unchanged function always gets the same type (checked on millions of pairs in curl: 1.0000).
- Small edits keep the type (98% under edits of up to 5% of a file); larger rewrites change it (about 70% kept above 20%).
- Over a year, about 88% of edited functions keep their type, and shape change slows with age (about 0.46 times as often for older functions).

## Limits
- The engine's labels can change with a retrain; the report shows what the scan stored.
- File-level cluster archetypes (`file_cluster_N`) have no readable names and are not shown; repo-level labels are withheld by the engine when validation fails ("Unvalidated").
- Type is a description of structure; it does not say whether a function is risky.

## What to do about it
A shift in the mix (for example more Parameter Forwarders and fewer Compute Cores) shows where the code moved from logic to glue. A type that changes after an edit marks a rewrite of what the function does.
