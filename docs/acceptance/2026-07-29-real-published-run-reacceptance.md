# Real published-run reacceptance

The current checkout completed the real published-run walkthrough after the
NMR solid-C assignment-column update.

## Evidence

```text
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus_real_walkthrough_current_20260730'
python -m pytest -q tests/test_real_published_run_walkthrough.py -vv
15 passed, 11 warnings in 384.37s (0:06:24), exit code 0
```

Coverage includes DSC standard/isothermal/non-isothermal; SAXS static,
temperature, and strain; WAXS static/temperature/strain plus full-2D strain;
IR standard and temperature-2D; and NMR liquid H/C and solid H/C. Each case
exercises the shared publication, Manifest/Gallery, Editor/project export, and
History restore lifecycle.

The no-`--changed` task verifier passed task/memory checks, Pyright with zero
diagnostics, quality `287`, preprocessing `106`, and whitespace. The current
scoped changed-file verifier also passed with exit code `0`; Ruff reports no
finding in the SAXS files. An earlier attempt stopped at three `E741` findings
before the current checkout was rechecked and is retained only as historical
evidence.

Fresh scoped changed-file recheck on 2026-07-30 returned exit code `0`: task
and memory checks, Ruff, compile, type baseline, quality `287`, preprocessing
`106`, and whitespace all passed.

## Boundaries

The warnings are retained as evidence, including DSC polynomial conditioning
and missing DejaVu glyphs. SAXS temperature and DSC non-isothermal diagnostic /
publication-role limitations remain scientific review signals. This evidence
does not close the full/boundary timeout, IR vendor semantics, Joint conflict
interpretation, solid-C assignment review, or final human release approval.
