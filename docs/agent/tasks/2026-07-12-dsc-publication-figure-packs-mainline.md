# Agent Task

## Goal

From the current `main`, integrate DSC publication figure packs for standard,
isothermal, and non-isothermal modes. Reuse the shared figure lifecycle,
publication audit, manifest, renderer, and editor contracts while keeping DSC
scientific calculations unchanged.

## Non-goals

- Do not merge or revive legacy PR #9 or its unrelated Unified Tables work.
- Do not change DSC peak finding, baseline correction, integration,
  crystallinity, or kinetics algorithms.
- Do not modify WAXS, SAXS, GUI streamlining, Editor/Export, or AI preprocessing.
- Do not promote missing or unreliable evidence to a publication-ready Main
  figure.

## Affected boundaries

- Analysis engine: DSC figure-definition projection and mode dispatch.
- Result/schema contract: publication roles, evidence reasons, and manifests.
- Persistence/export: shared manifest-backed editable assets.
- Evaluation/documentation: focused and real-data acceptance evidence.

## Acceptance criteria

- [ ] Each DSC mode dispatches only to its own provider and produces deterministic
  Main/SI/Diagnostics definitions.
- [ ] Main eligibility is evidence-gated; omitted evidence and rejection reasons
  remain traceable in SI or Diagnostics and never become fabricated conclusions.
- [ ] Published definitions produce one manifest-backed revision with editable
  document, preview, SVG, PNG, PDF, and 600-DPI TIFF assets when ready.
- [ ] Standard, isothermal, and non-isothermal real-data cases cover ready,
  downgrade, diagnostic-veto, missing-evidence, and failure paths.
- [ ] No provider recomputes scientific parameters; providers consume completed
  analysis results and existing shared contracts.

## Implementation plan

1. Create a clean DSC branch from the latest `main` and import only the DSC
   design, plan, and task card; keep the historical DSC worktree as a reference.
2. Add immutable DSC result views and evidence gates, then implement separate
   standard, isothermal, and non-isothermal FigureDefinition providers with
   focused red-green tests.
3. Route `DSCEngine` through the mode dispatcher and manifest-backed publisher;
   preserve the old sequence builder only as an explicit compatibility entry.
4. Add the DSC-only 600-DPI TIFF publication profile and panel-label contract
   needed by the existing shared audit, while preserving the default profile.
5. Run real-data acceptance, full DSC/shared-figure regressions, agent gates,
   CI, and human DSC scientific/publication review before merge.

## Verification

```powershell
python scripts/task_check.py --task docs/agent/tasks/2026-07-12-dsc-publication-figure-packs-mainline.md
python -m pytest tests/test_dsc_publication_cutover.py tests/test_dsc_publication_standard_provider.py tests/test_dsc_publication_isothermal_provider.py tests/test_dsc_publication_nonisothermal_provider.py -q
python -m pytest tests/eval/test_dsc_publication_real_data.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-12-dsc-publication-figure-packs-mainline.md --changed
python scripts/verify.py --changed --types
git diff --check
```

## Tooling note

The local `scripts/task_check.py` and `scripts/verify.py` agent assets are
currently untracked in `D:\PolyNexus` and are not part of the production
branch. When validating this card, invoke those local tools with this worktree
as the working directory if available, and report that provenance explicitly;
the branch-owned test results and GitHub CI remain the authoritative production
evidence.

## Risks and compatibility

- Scientific semantics must remain in DSC analysis services; figure providers
  only project already-emitted evidence.
- The old DSC worktree contains unrelated historical changes, so only the
  DSC-specific provider and test changes may be selectively reused.
- If a gate fails, retain an auditable SI/Diagnostics reason and leave the
  previous published revision intact.

## Review checkpoint

- Human review required: yes.
- Reviewer focus: DSC scientific semantics, evidence gates, publication audit,
  and export asset consistency.
- One atomic PR from a branch based on the latest `main`.
