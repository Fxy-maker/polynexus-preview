# PolyNexus

PolyNexus is a multi-technique polymer characterization platform for local data analysis, plotting, reporting, sample tracking, and AI-assisted parameter tuning.

The project currently centers on a desktop GUI built with `PySide6`, plus a CLI for single-file analysis, batch processing, and AI tuning workflows.

## Supported Techniques

- `DSC` - Differential Scanning Calorimetry
- `IR` - Infrared Spectroscopy
- `WAXS` - Wide-Angle X-ray Scattering
- `SAXS` - Small-Angle X-ray Scattering
- `NMR` - Nuclear Magnetic Resonance

## Quick Start

### 1. Install

```bash
pip install -e .
```

### 2. Launch the GUI

```bash
polynexus --gui
```

or:

```bash
polynexus-gui
```

### Development GUI and worktrees

The desktop shortcut uses `D:\PolyNexus` as the single canonical GUI runtime
worktree. Create or switch GUI development branches in that directory, then
close and reopen the GUI after switching; a running Python process does not
hot-reload a different Git checkout.

```powershell
Set-Location D:\PolyNexus
git switch -c codex/gui-launch-validation
& .\Python\pythoncore-3.14-64\python.exe .\scripts\launch_gui.py --diagnose
```

The diagnostic output shows the source root, branch, commit, interpreter, and
imported package path. Isolated worktrees are not selected automatically. To
inspect one explicitly, run its local launcher with
`--worktree <path> --diagnose`; this does not change the desktop shortcut.

### 3. Run CLI analysis

Examples:

```bash
polynexus saxs data.edf
polynexus waxs sample.raw -o output_dir
polynexus dsc curve.csv
```

### 4. Batch processing

```bash
polynexus batch ./data --technique saxs --workers 4
```

### 5. AI-assisted tuning

```bash
polynexus ai-tune --technique waxs --file sample.edf --polymer PA6
```

## Main Capabilities

- Single-technique analysis for common polymer characterization workflows
- GUI-based result inspection and figure preview
- Chart editing and export helpers
- Sample and batch history backed by SQLite
- Cross-technique joint analysis workspace
- AI-assisted parameter tuning with run history
- Optional OriginLab export with newer Python, legacy COM/LabTalk, and no-Origin fallback paths

## Optional OriginLab Export

OriginLab integration is optional and Windows-only. The native editor and
export paths work without Origin installed.

To enable the COM compatibility path, install the optional bridge:

```bash
pip install -e ".[origin]"
```

When the Chart Editor's `Export to Origin` action is used, PolyNexus selects
the highest-priority available adapter:

1. the installed high-level `originpro` integration;
2. COM plus bounded LabTalk commands;
3. an `Origin_Export` package containing CSV data, JSON metadata, import script,
   and PNG/SVG/PDF visual assets.

Editable Origin output is loss-aware. For unsupported artists, transforms, or
annotations, use the included SVG/PDF/PNG assets for visual fidelity. PolyNexus
never requires Origin at startup and never writes `.opju` files as raw bytes;
Origin itself performs native project saves.

## Project Structure

```text
polynexus/
|- core/        Analysis engines and technique-specific pipelines
|- data/        Sample database, polymer data, and local records
|- export/      Report and parameter export helpers
|- gui/         Main window, widgets, themes, and i18n
|- plotting/    Shared plotting styles and scientific figure helpers
|- readers/     File readers for supported instrument formats
|- utils/       Configuration and logging utilities

llm/            LLM client integration
rag/            Retrieval and advisory components
scripts/        Utility and evaluation scripts
tests/          Automated tests
docs/           Planning, baselines, acceptance notes, and maintenance docs
```

Documentation starts at `docs/README.md`. Current planning notes live under `docs/plans`, baseline ledgers under `docs/baselines`, acceptance and handoff notes under `docs/acceptance`, and patch bundles under `docs/patch-bundles`.

## Common Entry Points

- `polynexus --gui`
  Open the desktop application.

- `polynexus <technique> <input>`
  Run one analysis from the command line.

- `polynexus batch <input_dir> --technique <name>`
  Run batch analysis over a directory.

- `polynexus ai-tune ...`
  Run AI-assisted parameter tuning and persist a report.

## Development

Install development dependencies:

```bash
pip install -e .[dev]
```

Run tests:

```bash
pytest
```

Pytest temporary files are stored outside the repository on the current project
drive, normally under `D:\PolyNexus-test-runs`. Override this with the
`POLYNEXUS_TEST_ROOT` environment variable, or pass an explicit
`--basetemp <path>` for a specialized run. Review and clean stale test runs
with the dry-run-first commands:

```powershell
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
python scripts/test_storage.py clean --older-than-hours 24 --apply
```

The cleanup command never removes test source, real datasets, worktrees, or
directories referenced by a running test process.

## Notes

- The repository currently contains real test data, generated outputs, and working drafts side by side with source code.
- The GUI and localization layer are under active cleanup, so some pages may still contain inconsistent wording or unfinished flows.
