# AI Preprocessing GUI Confirmation and Transaction Design

## Goal

Expose preprocessing decisions in the existing AI tuning flow while keeping
scientific decision logic in the preprocessing/orchestration services. A user
must be able to inspect a proposed change, explicitly confirm it, recover from
a failed rerun, and undo a successfully applied change. Automatic decisions
must remain auditable and reversible.

## Scope and non-goals

This slice covers the GUI-facing decision view model and transactional apply,
rerun, rollback, undo, and scoped experience persistence for preprocessing
reports.

It does not change preprocessing algorithms, candidate generation, policy
promotion, publication figures, Unified Tables, GUI streamlining, or the
superseded Editor/Export reconciliation.

## Architecture

### Decision view model

`polynexus/gui/preprocess_decision_service.py` will convert an untrusted report
mapping into an immutable `PreprocessUIDecision`. It will:

- distinguish `auto_apply`, `confirm`, `shadow`, and `keep_original` modes;
- select evidence by `selected_candidate_id`, with a deterministic fallback;
- expose only protected metrics, reason codes, selected config, and button
  capabilities;
- default malformed or incomplete reports to `keep_original` with apply and
  undo disabled.

This service will not apply configs, inspect technique-specific engine state, or
make scientific decisions.

### Transaction service

`polynexus/gui/preprocess_transaction_service.py` will own GUI transaction
state through explicit callbacks supplied by the window layer:

- capture current values for keys in the selected config;
- retain the previous result object and proposed experience payload;
- apply only the selected preprocessing config and invoke one rerun;
- finalize experience persistence only after a successful rerun callback;
- restore config/result and discard the proposal on rerun failure;
- undo the last applied transaction, rerun, and revoke its experience only after
  successful undo.

The service will not mutate the core engine directly. The GUI mixin remains a
thin adapter for widgets, tabs, logging, and existing run callbacks.

## Data flow

```text
orchestrator report
        |
        v
PreprocessUIDecision -- inspect/confirm/undo --> TransactionService
                                                    |
                              snapshot <-----------+-----------> apply
                                                    |
                                             rerun callback
                                         / success       \ failure
                                        v                 v
                              persist experience     restore snapshot
```

For `request_confirmation`, the dialog's accepted action starts a pending
transaction. For `auto_accept`, the report may already represent a committed
core decision; the GUI path must still expose undo and must not create a second
core commit. For `shadow` and `keep_original`, the dialog is informational and
cannot apply a config.

## Error handling and safety

- Missing or malformed selected config: no transaction starts.
- Missing widget/config key: that key is excluded from the GUI snapshot and the
  service reports the transaction as non-applicable rather than guessing.
- Apply or rerun exception: restore the captured config and result; do not
  persist positive experience.
- Experience persistence failure after a successful rerun: keep the applied
  result, record the persistence failure through the existing logger, and do
  not claim that experience was stored.
- Undo rerun failure: restore the applied config/result and retain the applied
  experience state.
- No operation may import or modify Editor/Export state.

## Verification

Add focused tests for:

- all four view-model modes and selected-evidence matching;
- confirmation apply pending until rerun success;
- failed apply/rerun restoring config and result without experience;
- successful undo revoking experience only after undo rerun success;
- malformed reports disabling apply and undo;
- existing MainWindow AI tuning and run-error regressions.

Run the focused GUI/preprocessing matrix, `python -m compileall` on changed
modules, and `git diff --check`. Human review is required for transaction and
scientific-audit semantics before merge.

## Decision

Use separate pure services plus a thin GUI adapter. This preserves the
repository boundary that GUI code consumes reports/view models while core and
orchestration services own scientific and audit semantics.
