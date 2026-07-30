# Current HEAD Non-SAXS Recheck Design

## Decision

Use separate recursive pytest shards for DSC/WAXS, IR, and NMR/Joint, then
run the current Windows Qt NMR route with the native platform explicitly set.
Keep SAXS excluded because it is being handled in another workstream.

## Boundary

The recheck proves current software regression and route construction. It does
not infer scientific semantics, approve publication roles, or close human
visual review. External basetemps keep test artifacts outside the repository.
