# Daily Task: Origin single-graph fidelity

## Goal

Make ChartEditor's native Origin export produce one Origin Graph containing
all mapped series, with axis scale semantics matching the source object figure.
For the current SAXS waterfall, the five curves must share one graph and the Y
axis must remain logarithmic rather than collapsing lower-intensity curves onto
the linear-axis baseline.

## Non-goals

- Do not change scientific data values, analysis algorithms, or figure-document
  semantics.
- Do not remove the COM/LabTalk or Origin-compatible package fallbacks.
- Do not close or kill a user-owned Origin process during verification.

## Affected boundaries

- [x] OriginPro facade and native graph construction
- [x] Origin figure-document mapping
- [x] Origin adapter regression tests
- [ ] Analysis algorithms
- [ ] GUI layout
- [ ] Remote deployment or push

## Acceptance criteria

- [x] A native export of the SAXS waterfall creates one Origin Graph, not one
  graph window per series.
- [x] All five series are present in that Graph.
- [x] The Origin Y axis is logarithmic when the source object document declares
  a logarithmic Y axis; linear axes remain linear.
- [x] Static and fallback export paths remain unchanged.
- [x] Focused tests, ChartEditor regression tests, Ruff, compileall, diff
  checks, and a real OriginPro smoke export pass.

## Verification

```powershell
pytest tests/test_originpro_adapter.py tests/test_origin_mapping.py -q
pytest tests/test_chart_editor.py -q
ruff check polynexus/origin/originpro_adapter.py tests/test_originpro_adapter.py
python -m compileall -q polynexus/origin tests/test_originpro_adapter.py
git diff --check
```

The repository-prescribed `python scripts/verify.py --changed --types` command
must also be attempted and reported if the script remains unavailable.

## Evidence

- `python -m pytest tests/test_originpro_adapter.py tests/test_origin_mapping.py -q` -> `16 passed`.
- The follow-up label-display regression extends the focused suite to `18 passed`.
- `python -m pytest tests/test_chart_editor.py -q` -> `238 passed`.
- `python -m ruff check polynexus/origin/originpro_adapter.py polynexus/origin/mapping.py tests/test_originpro_adapter.py tests/test_origin_mapping.py` -> passed.
- `python -m compileall -q polynexus/origin tests/test_originpro_adapter.py tests/test_origin_mapping.py` -> passed.
- `git diff --check` -> passed.
- Both prescribed verifier invocations were attempted and failed because
  `D:\PolyNexus\scripts\verify.py` is absent.
- Live OriginPro smoke returned `success/originpro`. In the same OriginPro
  process, the exported project contained one Graph with five plots, Y scale
  `log10`, five document colors, five `0.8`-point line widths, five source
  worksheets, the five sample names as Y-column labels, and readable Unicode
  axis labels (`I (a.u.)` and `q (nm⁻¹)`).
