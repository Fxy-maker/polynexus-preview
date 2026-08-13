# Focused Testing Matrix

Default to the narrowest test set that proves the task. Pytest uses the
external managed test root and `ephemeral` retention by default; successful
temporary directories are removed promptly. Do not run the full matrix merely
because a focused task changes Python files.

| Changed boundary | Required focused tests | Add only when applicable |
| --- | --- | --- |
| Canonical source/template | Canonical template and affected adapter tests | Project replay/package test |
| Analysis/provider result | Provider regression and public result-contract test | Canonical replay if input conversion changed |
| Project orchestration | Discovery/workflow/package/provenance tests | CLI and GUI DTO consumer tests when their contract changes |
| Evidence, metrics, ARS, export | Package/provenance test plus ARS/export consumer test | GUI evidence-view or dialog test when its DTO changes |
| GUI/view model | Focused widget or adapter test | Producer contract test if it reads a changed shared DTO |
| Shared project/run/chart/export object | Producer test and each affected entry-point consumer test | Read-only real-data smoke only when automated fixtures are insufficient |
| Architecture/schema/security/performance/scientific semantics | Focused tests above | Structured task verifier and human review before merge |
| Release/integration | Relevant focused matrix | `verify.py --changed --types --full --boundary` and explicit human review |

Use `-q -p no:cacheprovider` for ordinary focused runs. On failure, inspect the
failure tail and repair the specific defect; do not expand into an unrelated
full-suite investigation. Set `POLYNEXUS_TEST_RETENTION=review` only when a
person needs the artifacts, and `evidence` only for a deliberate audit record.
