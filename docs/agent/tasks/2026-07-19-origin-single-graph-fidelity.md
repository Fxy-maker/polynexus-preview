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

- A native export of the SAXS waterfall creates one Origin Graph, not one graph
  window per series.
- All five series are present in that Graph.
- The Origin Y axis is logarithmic when the source object document declares a
  logarithmic Y axis; linear axes remain linear.
- Static and fallback export paths remain unchanged.
- Focused tests, ChartEditor regression tests, Ruff, compileall, diff checks,
  and a real OriginPro smoke export pass.

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
