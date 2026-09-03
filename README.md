# PolyNexus

> Research Preview — Apache-2.0

PolyNexus is an AI-oriented polymer research workbench that users can also
operate independently. Codex/AI and the user interface work on the same
projects, analysis runs, charts, evidence packages, and exports.

It combines deterministic multi-technique polymer characterization with a
PySide6 desktop GUI and CLI/project-workflow entry points. AI can understand a
research question, organize inputs, propose methods, and request work; the
Core performs calculation, retains source/parameter provenance, and exposes
shared scientific result objects. AI does not replace the Core as the source of
numerical results.

This repository is a research preview, not a claim that every workflow or
technique is publication-validated. See [the open-source guide](docs/OPEN_SOURCE.md)
for the capability maturity boundary, release checklist, and data-rights rules.

## Core Technique Families

- `DSC` - Differential Scanning Calorimetry
- `IR` - Infrared Spectroscopy
- `WAXS` - Wide-Angle X-ray Scattering
- `SAXS` - Small-Angle X-ray Scattering
- `NMR` - Nuclear Magnetic Resonance

Coverage varies by input type and workflow. The runtime catalog distinguishes
`available`, `experimental`, and `unsupported` capabilities. In particular,
several N-D routes are experimental; DMA/DMTA, rheology, TGA/DTG, SEC/GPC, and
mechanics are planned/unsupported rather than executable providers.

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

## Local Codex GUI Automation

PolyNexus can expose its main GUI analysis workflow to Codex through a local
MCP server. Install the optional automation dependency on each computer that
will use it:

```powershell
pip install -e ".[automation]"
```

Then register `polynexus-mcp` as a stdio MCP server in that computer's Codex
configuration:

```toml
[mcp_servers.polynexus]
command = "polynexus-mcp"
args = []
```

Restart Codex after saving the configuration. The server starts a separate, visible PolyNexus window and
provides only these actions: launch, import one local file, choose a technique,
run, wait for completion, read the result, capture the window, and close the
dedicated session.

The automation listener exists only for that dedicated session, binds to
`127.0.0.1` with a random per-session secret, and is not created by ordinary
`polynexus --gui` launches. It never accepts LAN/Internet connections or
controls an already-open user window. Configure the same local stdio command
again after installing PolyNexus on another computer; there is no shared or
remote service to deploy.

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
`--basetemp <path>` for a specialized run. The storage tool also reports
historical `C:\TempPolyNexus*` directories on Windows (or roots listed in
`POLYNEXUS_LEGACY_TEST_ROOTS`, separated by `;`). Review and clean stale test
runs with the dry-run-first commands:

```powershell
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
python scripts/test_storage.py clean --older-than-hours 24 --apply
```

The cleanup command is dry-run by default. It never removes test source, real
datasets, worktrees, protected paths, or directories referenced by a running
test process. Add `--legacy-root <path>` when an old test-output root needs to
be inspected explicitly.

### Test storage retention

Ordinary pytest runs use the `ephemeral` profile and delete a successful
agent-owned basetemp as soon as pytest has released it. Failed or interrupted
ephemeral runs remain for 24 hours. Select a longer-lived profile per run when
the output needs inspection:

```powershell
$env:POLYNEXUS_TEST_RETENTION="review"
pytest tests/test_gui_route.py

$env:POLYNEXUS_TEST_RETENTION="evidence"
pytest tests/test_release_acceptance.py
```

`review` retains output for 7 days; `evidence` retains it permanently. Existing
directories without a manifest are classified as `legacy`: their test result
is never guessed from the directory name, and the janitor applies a 24-hour
cooldown. If the target volume falls below 10% free space, failed or
interrupted ephemeral runs and known test-class legacy directories older than
two hours may be cleaned. Known legacy names are limited to matrix/pytest test
patterns; archive, review, evidence, baseline, and unknown paths stay
protected. Live PIDs, running manifests, cleanup-pending runs, tracked paths,
symlinks, and protected roots also stay protected.

The immediate deletion path is restricted to the exact run directory created
by pytest. Scheduled deletion is always dry-run first and requires the
explicit `--apply` flag. Do not use `--apply` for the first legacy migration
until the concrete JSON inventory has been reviewed; source files, real data,
worktrees, and evidence paths remain protected.

Emergency cleanup is evaluated when each report or clean plan is built, so a
volume that becomes nearly full does not have to wait for a later pytest
finalization event. Use `report --json` first and inspect `emergency`,
`emergency_eligible_bytes`, `reason`, and `failures` before applying.

## Research-preview limitations

- Scientific results require appropriate calibration, method selection, and
  expert interpretation for the actual material and experiment.
- Some GUI wording and workflows remain under active refinement.
- Use only data you have the right to process and redistribute. Do not include
  personal measurement data, generated evidence packages, local databases,
  logs, or credentials in a contribution or public release.

## Contributing and license

PolyNexus is licensed under [Apache-2.0](LICENSE). Read
[CONTRIBUTING.md](CONTRIBUTING.md) before contributing code, templates, sample
data, or adapters.
