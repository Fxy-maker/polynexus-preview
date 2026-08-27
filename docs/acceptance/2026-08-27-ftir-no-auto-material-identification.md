# FTIR No-Auto-Material Identification — Acceptance

When no material hint is supplied, the IR provider no longer selects PA6/PEEK
or another polymer from its built-in peak database. Generic peaks and metrics
remain available; explicit `polymer_name` still enables scoped assignments and
band indices.

Verification: `7 passed` in focused IR tests. One historical
orchestrator fixture remains blocked by an unrelated ambiguous canonical table
mapping and is not caused by this change.
