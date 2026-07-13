# Agent Task

## Goal

Integrate WAXS static, temperature/time, and in-situ strain publication figure
packs from the current `main` line. Reuse the shared FigureDefinition,
manifest, publisher, editor, and publication-audit lifecycle while keeping
WAXS evidence gates explicit and traceable.

## Non-goals

- Do not change WAXS fitting, background correction, orientation, anisotropy,
  lattice-strain, or temperature/strain analysis algorithms.
- Do not include Unified Tables, DSC, GUI streamlining, Editor/Export, or AI
  preprocessing changes.
- Do not promote missing or unreliable evidence to Main.

## Acceptance criteria

- Static, temperature/time, and strain modes dispatch only to their active
  provider and publish manifest-backed editable figures.
- Selected detector/orientation/sequence evidence is finite, traceable, and
  never inferred by the figure layer.
- Main/SI/Diagnostics roles, no-Main reasons, omitted evidence, and asset audit
  metadata are preserved in the manifest.
- Valid strain 2D patterns use editable `image_grid` objects; invalid or absent
  2D evidence degrades to a 1D Main pack.
- WAXS ready assets include Preview, PNG, PDF, SVG, and 600-DPI TIFF outputs.

## Affected boundaries

- Analysis engine, result/schema projection, persistence, export/reporting,
  evaluation, and documentation/tooling.
- GUI and CLI contracts remain unchanged; they consume the shared lifecycle.

## Verification

```powershell
python scripts/quality_gate.py
python -m pytest -q tests/test_waxs_figure_provider.py tests/test_waxs_publication_cutover.py tests/test_waxs_publication_static_provider.py tests/test_waxs_publication_strain_provider.py tests/test_waxs_publication_temperature_provider.py tests/test_figure_image_grid.py tests/eval/test_waxs_publication_real_data.py
git diff --check
```

## Review checkpoint

- Human scientific review required: evidence gates, detector snapshot,
  orientation/strain semantics, and publication export audit.
- One atomic PR: `codex/waxs-publication-packs-v2`.
