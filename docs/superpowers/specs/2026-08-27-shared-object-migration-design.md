# Shared Object Migration Design

## Goal

Keep Batch, Codex/Agent, GUI persistence, and DSC features while removing
entry-point-specific analysis and persistence duplication. Every migrated route
must produce or consume the shared `ComputeRun` contract.

## Migration order

1. Batch uses `ComputeRunService` and persists its public run projection.
2. GUI history/persistence stores and restores the same run projection while
   retaining legacy rows for read-only compatibility.
3. Codex/Agent workflow embeds the shared run projection in its step result and
   stops reconstructing provider-only result objects.
4. DSC `thermal_program.v1` converts multi-program exports and attaches to the
   same route without changing existing Avrami qualification.
5. Remove duplicate producers only after all consumer matrices and the six
   sample replay pass.

## Compatibility rule

Legacy provider outputs remain an adapter detail (`legacy_result`) during
migration. They are not a second public persistence contract. Old stored rows
are read through compatibility projection but new runs write the shared
ComputeRun fields first.

## Non-goals

No deletion before migration evidence, no raw data changes, no automatic
scientific publication decisions, and no forced vendor parser implementation.
