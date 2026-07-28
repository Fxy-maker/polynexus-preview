# Real published-run lifecycle walkthrough

The fresh current-checkout command:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_real_walkthrough_current_20260730'
python -m pytest -q tests/test_real_published_run_walkthrough.py
```

returned:

```text
15 passed, 11 warnings in 361.98s (0:06:01)
WALKTHROUGH_EXIT_CODE=0
```

It covered DSC standard/isothermal/non-isothermal, SAXS static/temperature/
strain, WAXS static/temperature/strain-2D, IR standard/temperature-2D, and
NMR liquid H/C plus solid H/C. The matrix exercises engine output, figure run
manifest, active Gallery, Editor selection, export bundle, and provenance
recovery.

The warnings are existing DSC polynomial-conditioning and missing DejaVu Sans
CJK glyph warnings. This is lifecycle evidence only: scientific validity,
vendor mapping/ROI semantics, solid-C assignment policy, Joint conflict
interpretation, restarted-GUI visual review, and release approval remain open.
Test-storage cleanup remains dry-run only.
