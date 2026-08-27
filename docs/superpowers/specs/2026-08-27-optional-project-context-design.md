# Optional Project Context Design

## Decision

PolyNexus will not maintain a material database. Codex/ARS may place a small `.polynexus/project-context.json` in a project, or pass an equivalent mapping through the shared compute API. The context is optional and advisory: it supplies explicit parameters, never scientific conclusions.

## Contract

```json
{
  "schema": "project-context.v1",
  "material": {"name": "PA6", "phase": "alpha"},
  "techniques": {
    "dsc": {
      "reference_enthalpy_Jg": 230.0,
      "reference_enthalpy_source": "user/literature citation"
    }
  }
}
```

Only the schema, mapping types, finite numeric values, and positive reference enthalpy are validated. Unknown keys are preserved for AI context but ignored by deterministic providers until a provider explicitly consumes them.

## Data flow

`project-context.json` (optional) → `ProjectContext` loader → `ComputeRunService` → immutable `AnalysisPlan.project_context` and hash → provider-specific parameter projection → deterministic result. Missing context uses no material fallback. Values that require context become `unknown`/`unavailable` while independent metrics continue.

## Error handling

Malformed JSON, wrong schema, or invalid values return `needs_input` with `project_context_invalid`; providers are not called. A missing file is equivalent to empty context, not an error. Context is never inferred from a filename.

## Compatibility

The new argument is optional, so existing GUI, CLI, Batch, and Agent/Codex callers keep their current signatures. Discovery is explicit through `project_context` or a project root/path; direct single-file use does not search arbitrary parent directories.

## Scientific boundary

The context records parameter source and hash for reproducibility. It does not certify sample identity, batch membership, literature correctness, or publication eligibility. Human/ARS review remains required.
