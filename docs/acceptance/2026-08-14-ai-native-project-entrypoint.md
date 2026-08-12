# AI-Native Project Entrypoint Acceptance

Date: 2026-08-14

`polynexus project-workflow analyze-project --project-root <project>
--question <question>` is the AI/ARS-facing entrypoint. It discovers raw files,
uses existing technique adapters, runs available analyses, and creates an
evidence package without requiring callers to orchestrate inspect/plan/run/
package or create an `AnalysisRequest` JSON file.

The returned JSON separates:

- `computation`: `passed`, `failed`, or `blocked`;
- `data_quality`: `passed`, `warning`, or `failed`;
- `publication`: `ready`, `review_required`, or `blocked`.

Raw reason codes, runs, evidence count, figures, tables, package path, and
messages remain available for Codex/ARS. The lower-level project workflow
commands are unchanged.

## Discovery behavior

- FTIR CSV/SPC-style sources can be recognized from header labels such as
  `Wavenumber` and `Absorbance` even if a project folder lacks an `IR` name.
- Same-stem `.spc`/`.spa` companion files are skipped when another same-stem
  file is present, preventing duplicate work; the summary records
  `duplicate_format_skipped`.

## Verification

- Unified project workflow matrix: `46 passed, 1 skipped`.
- `git diff --check`: passed.
- Structured verifier: required before checkpoint.

## Limits

The entrypoint does not infer sample/batch identity, suppress source-hash
checks, fix missing SAXS background calibration, or promote review-bound
evidence to manuscript conclusions.
