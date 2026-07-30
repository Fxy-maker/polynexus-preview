# Joint AI Boundary Design

## Decision

Joint is a deterministic cross-technique report and validation surface. It
does not call an AI provider. The report must say so explicitly and identify
the deterministic rule-based report as its fallback. If a future provider is
added and fails, the contract is to retain source runs, evidence weights, and
WARN/ERROR conflict rows rather than rescue or promote them.

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

This is status/provenance only. It does not change the existing `summary`,
`issue_count`, `error_count`, `warning_count`, or `recommended_review_targets`.
