# Joint AI Context Fallback Provenance Design

## Decision

The current Joint report builder is the primary source of `ai_boundary`, but
the GUI/history compatibility adapter also constructs a report context for
legacy payloads that have `rows` and `validations` without `ai_context`. Those
synthetic clean and conflicted contexts must carry the same static boundary.

The boundary is status/provenance only. It must not alter existing summary,
issue count, severity, family, or review-target values.

## Payload

```json
{
  "ai_boundary": {
    "mode": "off",
    "provider_status": "not_configured",
    "fallback": "rule_based_report",
    "failure_policy": "preserve_source_evidence_and_diagnostic_status"
  }
}
```

No provider is introduced by this compatibility path.
