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

## Notes

- The repository currently contains real test data, generated outputs, and working drafts side by side with source code.
- The GUI and localization layer are under active cleanup, so some pages may still contain inconsistent wording or unfinished flows.
